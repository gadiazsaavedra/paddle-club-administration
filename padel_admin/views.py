from datetime import datetime, date, time, timedelta
from enum import unique
import json
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
import random
from .models import (
    Jugadors,
    Reserva,
    Cobrament,
    Recepcionista,
    Pistes,
    Recepcionista,
    Tarifa,
)
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import logging
from decimal import Decimal, InvalidOperation, localcontext
from django.urls import reverse


def landing(request):
    if request.method == "POST":
        dni = request.POST.get("dni")
        contrasenya = request.POST.get("contrasenya")
        try:
            recepcionista = Recepcionista.objects.get(DNI=dni, contrasenya=contrasenya)
            response = redirect("lista_reserves")
            response.set_cookie("acceso", str(recepcionista.DNI))
            return response
        except Recepcionista.DoesNotExist:
            mensaje = "El DNI o password son incorrectos"
            return render(request, "landing.html", {"mensaje": mensaje})
        except MultipleObjectsReturned:
            mensaje = "Error: hay múltiples recepcionistas con ese DNI. Contacte al administrador."
            return render(request, "landing.html", {"mensaje": mensaje})
    else:
        return render(request, "landing.html")


def lista_reserves(request):
    acceso = request.COOKIES.get("acceso")
    if not acceso:
        mensaje = "Acceso denegado: no hay sesión activa."
        return render(request, "landing.html", {"mensaje": mensaje})

    # hores disponibles
    hora_min = time(hour=9, minute=0, second=0)
    hora_max = time(hour=21, minute=0, second=0)
    hours = []
    current_hour = hora_min
    while current_hour <= hora_max:
        hours.append(current_hour.strftime("%H:%M"))
        current_hour = (
            datetime.combine(datetime.min, current_hour) + timedelta(minutes=30)
        ).time()

    pistas_disponibles = Pistes.objects.all().order_by("numero")
    jugadores_registrados = Jugadors.objects.all().order_by("nom", "cognom")

    # --- FUNCIONES INTERNAS PARA CENTRALIZAR LÓGICA ---
    def obtener_fecha_y_reservas(fecha_str=None):
        if fecha_str:
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        else:
            fecha_obj = date.today()
        day = fecha_obj.strftime("%Y-%m-%d")
        reserves = Reserva.objects.filter(fecha=fecha_obj).order_by(
            "hora_inicio", "hora_inicio", "cancha"
        )
        return day, reserves

    def render_lista_reserves(request, contexto_extra=None):
        contexto = {
            "hours": hours,
            "pistas_disponibles": pistas_disponibles,
            "jugadores_registrados": jugadores_registrados,
        }
        if contexto_extra:
            contexto.update(contexto_extra)
        return render(request, "lista_reserves.html", contexto)

    # --- FIN FUNCIONES INTERNAS ---

    if request.method == "POST":
        # eliminar jugador
        if request.POST.get("_method") == "DELETE":
            jugador_id = request.POST.get("jugador_id")
            fecha = request.POST.get("data")
            try:
                jugador = Jugadors.objects.get(id_jugador=jugador_id)
                reserva = Reserva.objects.get(jugador=jugador, fecha=fecha)
                # Registrar histórico de cancelación antes de borrar
                from .models import HistoricoReserva

                HistoricoReserva.objects.create(
                    reserva=reserva,
                    jugador=jugador,
                    accion="cancelacion",
                    importe=None,
                    detalles="Reserva cancelada por el usuario o admin",
                )
                reserva.delete()
            except (Jugadors.DoesNotExist, Reserva.DoesNotExist):
                mensaje_error = "No se encontró el jugador o la reserva."
                day, reserves = obtener_fecha_y_reservas(fecha)
                return render_lista_reserves(
                    request,
                    {
                        "reserves": reserves,
                        "day": day,
                        "mensaje_error": mensaje_error,
                    },
                )
            day, reserves = obtener_fecha_y_reservas(fecha)
            return render_lista_reserves(request, {"reserves": reserves, "day": day})
        # AFEGIR RESERVA
        # Validar campos obligatorios
        required_fields = [
            ("fecha-2", request.POST.get("fecha-2")),
            ("horaInici", request.POST.get("horaInici")),
            ("horaFinalitzacio", request.POST.get("horaFinalitzacio")),
            ("Pista", request.POST.get("Pista")),
            ("cancha_numero", request.POST.get("cancha_numero")),
            ("jugador_select", request.POST.get("jugador_select")),
        ]
        missing = [name for name, value in required_fields if not value]
        if missing:
            mensaje_error = f"Faltan campos obligatorios: {', '.join(missing)}."
            day, reserves = obtener_fecha_y_reservas()
            return render_lista_reserves(
                request,
                {
                    "reserves": reserves,
                    "day": day,
                    "mensaje_error": mensaje_error,
                },
            )
        datos = obtener_datos_reserva_formulario(request, modo="recepcionista")
        reserva, error = crear_reserva_util(
            **datos, request=request, recepcionista_required=True
        )
        if error:
            day, reserves = obtener_fecha_y_reservas()
            return render_lista_reserves(
                request,
                {
                    "reserves": reserves,
                    "day": day,
                    "mensaje_error": error,
                },
            )

    fecha = request.GET.get("fecha")
    day, reserves = obtener_fecha_y_reservas(fecha)
    # Para mostrar importe estimado en el formulario de reserva
    importe_estimado = None
    if (
        request.method == "GET"
        and request.GET.get("fecha")
        and request.GET.get("hora")
        and request.GET.get("horaFinalitzacio")
    ):
        try:
            fecha_str = request.GET.get("fecha")
            hora_inicio_str = request.GET.get("hora")
            duracion = request.GET.get("horaFinalitzacio")
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M").time()
            hora_fin = calcular_hora_fin(hora_inicio, duracion)
            tarifa = obtener_tarifa_para_reserva(fecha_obj, hora_inicio, hora_fin)
            if tarifa:
                dt_inicio = datetime.combine(fecha_obj, hora_inicio)
                dt_fin = datetime.combine(fecha_obj, hora_fin)
                duracion_horas = (dt_fin - dt_inicio).total_seconds() / 3600
                importe_estimado = round(float(tarifa.precio) * duracion_horas, 2)
        except Exception as e:
            logging.exception(e)
            importe_estimado = None
    mensaje_exito = None
    if request.method == "POST" and not missing:
        mensaje_exito = "Reserva creada exitosamente."
    return render_lista_reserves(
        request,
        {
            "reserves": reserves,
            "day": day,
            "importe_estimado": importe_estimado,
            "mensaje_exito": mensaje_exito,
        },
    )


def lista_jugadors(request):
    acceso = request.COOKIES.get("acceso")
    if not acceso:
        mensaje = "Accés denegat: no hay sesión activa."
        return render(request, "landing.html", {"mensaje": mensaje})

    search_query = request.GET.get("search")

    if request.method == "POST":
        if request.POST.get("_method") == "DELETE":
            jugador_id = request.POST.get("jugador_id")
            jugador = Jugadors.objects.filter(id_jugador=jugador_id)
            jugador.delete()
            return redirect("lista_jugadors")

        if request.POST.get("_method") == "PATCH":
            jugador_id = request.POST.get("id_jugador")
            nom = request.POST.get("nom")
            cognom = request.POST.get("cognom")
            email = request.POST.get("email")
            telefon = request.POST.get("telefon")
            nivell = request.POST.get("nivell")

            jugador = Jugadors.objects.get(id_jugador=jugador_id)
            # actualitzem valors necessaris
            if nom:
                jugador.nom = nom
            if cognom:
                jugador.cognom = cognom
            if email:
                jugador.email = email
            if telefon:
                jugador.telefon = telefon
            if nivell:
                jugador.nivell = nivell
            jugador.save()

        # Procesar los datos del formulario
        nom = request.POST.get("nom")
        cognom = request.POST.get("cognom")
        email = request.POST.get("email")
        telefon = request.POST.get("telefon")
        nivell = request.POST.get("nivell")
        contrasenya = str(nom)
        foto = request.FILES.get("foto")
        id_jugador = random.randrange(10000, 100000)
        try:
            player = Jugadors.objects.get(id_jugador=id_jugador)
            id_jugador = random.randrange(10000, 100000)
            jugador = Jugadors(
                id_jugador=id_jugador,
                nom=nom,
                cognom=cognom,
                email=email,
                telefon=telefon,
                nivell=nivell,
                contrasenya=contrasenya,
                foto=foto,
            )
            jugador.save()
        except Jugadors.DoesNotExist:
            jugador = Jugadors(
                id_jugador=id_jugador,
                nom=nom,
                cognom=cognom,
                email=email,
                telefon=telefon,
                nivell=nivell,
                contrasenya=contrasenya,
                foto=foto,
            )
            jugador.save()

    jugadors_list = Jugadors.objects.all()

    if search_query:
        jugadors_list = jugadors_list.filter(
            nom__icontains=search_query
        ) | jugadors_list.filter(cognom__icontains=search_query)

    paginator = Paginator(jugadors_list, 100)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
    }

    return render(request, "lista_jugadors.html", context)


def obtener_datos_cobro_formulario(request):
    """Extrae los datos necesarios para registrar un cobro desde el request."""
    # En este caso, el importe se calcula, pero si en el futuro se permite ingresar importe manual, aquí se puede extraer
    return {}


def registrar_cobro_util(reserva, jugador, data, request):
    """Centraliza la lógica de cálculo, validación y registro de cobros. Devuelve (cobrament, importe_final, error_message)"""
    acceso = request.COOKIES.get("acceso")
    if not acceso:
        return None, None, "No hay sesión de recepcionista activa."
    try:
        rec = Recepcionista.objects.get(DNI=acceso)
    except Recepcionista.DoesNotExist:
        return None, None, "Recepcionista no encontrado. Inicie sesión nuevamente."
    # Calcular importe según tarifa y duración
    tarifa = obtener_tarifa_para_reserva(
        reserva.fecha, reserva.hora_inicio, reserva.hora_fin
    )
    try:
        if not tarifa or tarifa.precio in (None, ""):
            importe = Decimal("0.00")
        else:
            precio_str = str(tarifa.precio).replace(" ", "").replace(",", ".")
            precio_decimal = Decimal(precio_str)
            dt_inicio = datetime.combine(reserva.fecha, reserva.hora_inicio)
            dt_fin = datetime.combine(reserva.fecha, reserva.hora_fin)
            duracion_horas = Decimal(
                str((dt_fin - dt_inicio).total_seconds())
            ) / Decimal("3600")
            importe = precio_decimal * duracion_horas
            if not importe.is_finite() or importe < 0:
                return (
                    None,
                    None,
                    "Importe no válido (NaN/Infinito/Negativo). Verifique la tarifa.",
                )
            partes = str(importe).split(".")
            if len(partes[0]) > 8:
                return None, None, "Importe demasiado grande para el campo."
            try:
                importe = importe.quantize(Decimal("0.01"), rounding="ROUND_FLOOR")
            except Exception:
                return (
                    None,
                    None,
                    "Error crítico al redondear el importe. No se pudo registrar el cobro.",
                )
    except (InvalidOperation, TypeError, ValueError) as e:
        return (
            None,
            None,
            f"Error al calcular el importe: {str(e)}. Verifique la tarifa configurada.",
        )
    if abs(importe) >= Decimal("1000000.01"):
        return (
            None,
            None,
            f"El importe final ({importe}) excede el máximo permitido de 1,000,000.00.",
        )
    if importe == Decimal("0.00"):
        return (
            None,
            None,
            "No se puede registrar el cobro porque el importe es 0. Verifique la tarifa configurada.",
        )
    # Limite de 4 personas por reserva (si aplica)
    if Cobrament.objects.filter(reserva=reserva).count() >= 4:
        return None, None, "Limite de 4 persones en la cancha."
    # Ya pagó
    if Cobrament.objects.filter(reserva=reserva, jugador=jugador).exists():
        return None, None, "El jugador ya pagó esta reserva."
    # Registrar cobro y en histórico
    try:
        cobrament = Cobrament.objects.create(
            reserva=reserva,
            jugador=jugador,
            data=data,
            importe=importe,
            recepcionista=rec,
        )
        from .models import HistoricoReserva

        HistoricoReserva.objects.create(
            reserva=reserva,
            jugador=jugador,
            accion="pago",
            importe=importe,
            detalles=f"Pago registrado por {jugador.nom} {jugador.cognom}",
        )
        return cobrament, importe, None
    except Exception as e:
        return (
            None,
            None,
            f"Error al guardar el cobro: {str(e)}. Importe ({importe}) inválido.",
        )


def lista_cobraments(request, data, id_jugador):
    acceso = request.COOKIES.get("acceso")
    if not acceso:
        mensaje = "Acceso Denegado: no hay sesión activa."
        return render(request, "landing.html", {"mensaje": mensaje})
    try:
        jugador = Jugadors.objects.get(id_jugador=id_jugador)
        reserva = Reserva.objects.get(fecha=data, jugador=jugador)
    except (Jugadors.DoesNotExist, Reserva.DoesNotExist):
        mensaje = "No se encontró el jugador o la reserva."
        return render(request, "lista_cobraments.html", {"mensaje": mensaje})
    ya_pago = Cobrament.objects.filter(reserva=reserva, jugador=jugador).exists()
    if request.method == "POST":
        # Usar función utilitaria para registrar cobro (centraliza cálculo y validación)
        cobrament, importe_final, error = registrar_cobro_util(
            reserva, jugador, data, request
        )
        if error:
            return render(
                request,
                "lista_cobraments.html",
                {
                    "mensaje": error,
                    "jugador": jugador,
                    "reserva": reserva,
                    "importe": importe_final if importe_final is not None else 0,
                    "ya_pago": ya_pago,
                },
            )
        mensaje2 = (
            f"{jugador.nom} {jugador.cognom} ha realizado un pago de {importe_final} $"
        )
        return render(
            request,
            "lista_cobraments.html",
            {
                "mensaje2": mensaje2,
                "importe": importe_final,
                "jugador": jugador,
                "reserva": reserva,
                "ya_pago": True,
            },
        )
    # GET: mostrar importe estimado (sin registrar cobro)
    # Usar la misma lógica de cálculo que en registrar_cobro_util para mostrar importe estimado
    tarifa = obtener_tarifa_para_reserva(
        reserva.fecha, reserva.hora_inicio, reserva.hora_fin
    )
    try:
        if not tarifa or tarifa.precio in (None, ""):
            importe = Decimal("0.00")
        else:
            precio_str = str(tarifa.precio).replace(" ", "").replace(",", ".")
            precio_decimal = Decimal(precio_str)
            dt_inicio = datetime.combine(reserva.fecha, reserva.hora_inicio)
            dt_fin = datetime.combine(reserva.fecha, reserva.hora_fin)
            duracion_horas = Decimal(
                str((dt_fin - dt_inicio).total_seconds())
            ) / Decimal("3600")
            importe = precio_decimal * duracion_horas
            if not importe.is_finite() or importe < 0:
                importe = Decimal("0.00")
            else:
                importe = importe.quantize(Decimal("0.01"), rounding="ROUND_FLOOR")
    except Exception:
        importe = Decimal("0.00")
    return render(
        request,
        "lista_cobraments.html",
        {
            "jugador": jugador,
            "reserva": reserva,
            "importe": importe,
            "ya_pago": ya_pago,
        },
    )


def logout(request):
    response = redirect(
        "landing"
    )  # Redirige a la página de inicio de sesión o cualquier otra página después de hacer logout
    response.delete_cookie("acceso")  # Elimina la cookie 'recepcionista_id'
    return response


def calendario_canchas(request):
    # Obtener fecha actual o la seleccionada
    fecha_str = request.GET.get("fecha")
    if fecha_str:
        fecha_actual = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    else:
        fecha_actual = datetime.now().date()

    # Generar fechas para la semana
    inicio_semana = fecha_actual - timedelta(days=fecha_actual.weekday())
    fechas_semana = [inicio_semana + timedelta(days=i) for i in range(7)]

    # Obtener todas las canchas
    canchas = Pistes.objects.all().order_by("numero")

    # Horas disponibles (9:00 a 21:00)
    horas = []
    hora_actual = datetime.strptime("09:00", "%H:%M").time()
    hora_fin = datetime.strptime("21:00", "%H:%M").time()

    while hora_actual <= hora_fin:
        horas.append(hora_actual)
        dt = datetime.combine(datetime.today(), hora_actual)
        dt = dt + timedelta(minutes=30)
        hora_actual = dt.time()

    # Obtener todas las reservas para la semana
    reservas = Reserva.objects.filter(
        fecha__gte=fechas_semana[0], fecha__lte=fechas_semana[6]
    )
    # Obtener todos los cobros de reservas de la semana
    cobros = Cobrament.objects.filter(reserva__in=reservas)
    reservas_pagadas_ids = set(cobros.values_list("reserva_id", flat=True))

    calendario_cancha_filas = []
    for cancha in canchas:
        filas = []
        for hora in horas:
            estados = []
            for i, fecha in enumerate(fechas_semana):
                reserva = reservas.filter(
                    cancha=cancha, fecha=fecha, hora_inicio__lte=hora, hora_fin__gt=hora
                ).first()
                if reserva:
                    if reserva.id in reservas_pagadas_ids:
                        estados.append(
                            (
                                "pagado",
                                fecha,
                                reserva.jugador.nom,
                                reserva.jugador.cognom,
                            )
                        )
                    else:
                        estados.append(
                            (
                                "ocupado",
                                fecha,
                                reserva.jugador.nom,
                                reserva.jugador.cognom,
                            )
                        )
                else:
                    estados.append(("disponible", fecha, "", ""))
            filas.append({"hora": hora, "estados": estados})
        calendario_cancha_filas.append((cancha, filas))

    context = {
        "canchas": canchas,
        "fechas_semana": fechas_semana,
        "horas": horas,
        "calendario_cancha_filas": calendario_cancha_filas,
        "fecha_actual": fecha_actual,
    }

    return render(request, "calendario_canchas.html", context)


@csrf_exempt
def reservar_cancha(request):
    if request.method == "POST":
        datos = obtener_datos_reserva_formulario(request, modo="jugador")
        reserva, error = crear_reserva_util(
            **datos, request=request, recepcionista_required=False
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Reserva creada exitosamente.")
    return redirect("calendario_canchas")


def crear_reserva(request):
    if request.method == "POST":
        datos = obtener_datos_reserva_formulario(request, modo="jugador")
        reserva, error = crear_reserva_util(
            **datos, request=request, recepcionista_required=True
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Reserva creada exitosamente.")
    return redirect("calendario_canchas")


def perfil_jugador(request):
    jugador_id = request.COOKIES.get("jugador_id")
    if not jugador_id:
        return redirect("landing")
    try:
        jugador = Jugadors.objects.get(id_jugador=jugador_id)
    except Jugadors.DoesNotExist:
        messages.error(
            request, "El jugador no existe o no ha iniciado sesión correctamente."
        )
        return redirect("landing")
    reservas = Reserva.objects.filter(jugador=jugador).order_by(
        "-fecha", "-hora_inicio"
    )
    total_reservas = reservas.count()
    total_horas = sum(
        [
            (
                datetime.combine(r.fecha, r.hora_fin)
                - datetime.combine(r.fecha, r.hora_inicio)
            ).total_seconds()
            / 3600
            for r in reservas
        ]
    )
    canchas_usadas = (
        reservas.values("cancha__numero", "cancha__tipo").distinct().count()
    )
    if request.method == "POST":
        jugador.nom = request.POST.get("nom")
        jugador.cognom = request.POST.get("cognom")
        jugador.email = request.POST.get("email")
        jugador.telefon = request.POST.get("telefon")
        jugador.nivell = request.POST.get("nivell")
        if request.FILES.get("foto"):
            jugador.foto = request.FILES.get("foto")
        jugador.save()
    context = {
        "jugador": jugador,
        "reservas": reservas,
        "total_reservas": total_reservas,
        "total_horas": total_horas,
        "canchas_usadas": canchas_usadas,
    }
    return render(request, "perfil_jugador.html", context)


def obtener_tarifa_para_reserva(fecha, hora_inicio, hora_fin):
    # fecha: date, hora_inicio/hora_fin: time
    dia_semana = fecha.weekday()  # 0=Lunes
    # Buscar tarifa que cubra el rango horario
    tarifa = (
        Tarifa.objects.filter(
            dia_semana=dia_semana, hora_inicio__lte=hora_inicio, hora_fin__gte=hora_fin
        )
        .order_by("hora_inicio")
        .first()
    )
    return tarifa


def calcular_hora_fin(hora_inicio, duracion):
    if duracion == "30":
        return (
            datetime.combine(datetime.min, hora_inicio) + timedelta(minutes=30)
        ).time()
    elif duracion == "60":
        return (datetime.combine(datetime.min, hora_inicio) + timedelta(hours=1)).time()
    elif duracion == "90":
        return (
            datetime.combine(datetime.min, hora_inicio) + timedelta(hours=1, minutes=30)
        ).time()
    else:
        return (
            datetime.combine(datetime.min, hora_inicio) + timedelta(minutes=30)
        ).time()


def obtener_datos_reserva_formulario(request, modo="recepcionista"):
    """Extrae y valida los datos del formulario para crear una reserva."""
    if modo == "recepcionista":
        jugador_select = request.POST.get("jugador_select")
        if jugador_select:
            partes = jugador_select.split("|", 1)
            jugador_nom = partes[0].strip()
            jugador_cognom = partes[1].strip() if len(partes) > 1 else ""
        else:
            jugador_nom = request.POST.get("jugador_nom", "").strip()
            jugador_cognom = request.POST.get("jugador_cognom", "").strip()
        fecha = request.POST.get("fecha-2")
        hora_inicio_str = request.POST.get("horaInici")
        duracion = request.POST.get("horaFinalitzacio")
        type_cancha = request.POST.get("Pista")
        cancha_numero = request.POST.get("cancha_numero")
    else:
        # Para modo jugador (crear_reserva y reservar_cancha)
        jugador_nom = request.POST.get("jugador_nom", "").strip()
        jugador_cognom = request.POST.get("jugador_cognom", "").strip()
        fecha = request.POST.get("fecha")
        hora_inicio_str = request.POST.get("hora_inicio")
        duracion = request.POST.get("duracion")
        type_cancha = request.POST.get("cancha_tipo")
        cancha_numero = request.POST.get("cancha_id")
    return {
        "jugador_nom": jugador_nom,
        "jugador_cognom": jugador_cognom,
        "fecha": fecha,
        "hora_inicio_str": hora_inicio_str,
        "duracion": duracion,
        "type_cancha": type_cancha,
        "cancha_numero": cancha_numero,
    }


def crear_reserva_util(
    jugador_nom,
    jugador_cognom,
    fecha,
    hora_inicio_str,
    duracion,
    type_cancha,
    cancha_numero,
    request,
    recepcionista_required=True,
):
    """Centraliza la lógica de validación y creación de reservas. Devuelve (reserva, error_message)"""
    try:
        jugador = Jugadors.objects.get(nom=jugador_nom, cognom=jugador_cognom)
    except Jugadors.DoesNotExist:
        return None, "El jugador no existe."
    try:
        hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M").time()
    except Exception:
        return None, "Hora de inicio inválida."
    hora_fin = calcular_hora_fin(hora_inicio, duracion)
    try:
        cancha = Pistes.objects.get(numero=cancha_numero, tipo=type_cancha)
    except Pistes.DoesNotExist:
        return None, "La cancha seleccionada no existe o no es del tipo elegido."
    # Validar solapamiento
    if Reserva.objects.filter(
        cancha=cancha,
        fecha=fecha,
        hora_inicio__lt=hora_fin,
        hora_fin__gt=hora_inicio,
    ).exists():
        return None, "La cancha ya está reservada en ese horario."
    if Reserva.objects.filter(
        jugador=jugador,
        fecha=fecha,
        hora_inicio__lt=hora_fin,
        hora_fin__gt=hora_inicio,
    ).exists():
        return None, "El jugador ya tiene una reserva que se solapa con este horario."
    recepcionista = None
    if recepcionista_required:
        acceso = request.COOKIES.get("acceso")
        if not acceso:
            return None, "No hay sesión de recepcionista activa."
        try:
            recepcionista = Recepcionista.objects.get(DNI=acceso)
        except Recepcionista.DoesNotExist:
            return None, "Recepcionista no encontrado. Inicie sesión nuevamente."
    reserva = Reserva(
        jugador=jugador,
        fecha=fecha,
        cancha=cancha,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        recepcionista=recepcionista,
    )
    reserva.save()
    return reserva, None


def editar_cobro_util(cobrament, nuevo_importe, request):
    """Centraliza la lógica de validación y edición de cobros. Devuelve (cobrament_editado, error_message)"""
    acceso = request.COOKIES.get("acceso")
    if not acceso:
        return None, "No hay sesión de recepcionista activa."
    try:
        rec = Recepcionista.objects.get(DNI=acceso)
    except Recepcionista.DoesNotExist:
        return None, "Recepcionista no encontrado. Inicie sesión nuevamente."
    try:
        nuevo_importe = Decimal(str(nuevo_importe))
        if not nuevo_importe.is_finite() or nuevo_importe < 0:
            return None, "Importe no válido (NaN/Infinito/Negativo)."
        if abs(nuevo_importe) >= Decimal("1000000.01"):
            return (
                None,
                f"El importe final ({nuevo_importe}) excede el máximo permitido de 1,000,000.00.",
            )
        nuevo_importe = nuevo_importe.quantize(Decimal("0.01"), rounding="ROUND_FLOOR")
    except Exception as e:
        return None, f"Error al validar el importe: {str(e)}."
    try:
        importe_anterior = cobrament.importe
        cobrament.importe = nuevo_importe
        cobrament.recepcionista = rec
        cobrament.save()
        from .models import HistoricoReserva

        HistoricoReserva.objects.create(
            reserva=cobrament.reserva,
            jugador=cobrament.jugador,
            accion="edicion_pago",
            importe=nuevo_importe,
            detalles=f"Edición de cobro: de {importe_anterior} a {nuevo_importe} por {rec.nombre if hasattr(rec, 'nombre') else rec.DNI}",
        )
        return cobrament, None
    except Exception as e:
        return None, f"Error al editar el cobro: {str(e)}."


def eliminar_cobro_util(cobrament, request):
    """Centraliza la lógica de eliminación de cobros y registro en histórico. Devuelve (True, error_message)"""
    acceso = request.COOKIES.get("acceso")
    if not acceso:
        return False, "No hay sesión de recepcionista activa."
    try:
        rec = Recepcionista.objects.get(DNI=acceso)
    except Recepcionista.DoesNotExist:
        return False, "Recepcionista no encontrado. Inicie sesión nuevamente."
    try:
        from .models import HistoricoReserva

        HistoricoReserva.objects.create(
            reserva=cobrament.reserva,
            jugador=cobrament.jugador,
            accion="eliminacion_pago",
            importe=cobrament.importe,
            detalles=f"Cobro eliminado por {rec.nombre if hasattr(rec, 'nombre') else rec.DNI}",
        )
        cobrament.delete()
        return True, None
    except Exception as e:
        return False, f"Error al eliminar el cobro: {str(e)}."


def editar_cobro(request, id_cobro):
    try:
        cobrament = Cobrament.objects.get(id=id_cobro)
    except Cobrament.DoesNotExist:
        return render(
            request, "lista_cobraments.html", {"mensaje": "Cobro no encontrado."}
        )
    if request.method == "POST":
        nuevo_importe = request.POST.get("nuevo_importe")
        cobrament_editado, error = editar_cobro_util(cobrament, nuevo_importe, request)
        if error:
            return render(
                request, "editar_cobro.html", {"mensaje": error, "cobrament": cobrament}
            )
        return redirect(
            reverse(
                "lista_cobraments",
                kwargs={
                    "data": cobrament.reserva.fecha,
                    "id_jugador": cobrament.jugador.id_jugador,
                },
            )
        )
    return render(request, "editar_cobro.html", {"cobrament": cobrament})


def eliminar_cobro(request, id_cobro):
    try:
        cobrament = Cobrament.objects.get(id=id_cobro)
    except Cobrament.DoesNotExist:
        return render(
            request, "lista_cobraments.html", {"mensaje": "Cobro no encontrado."}
        )
    if request.method == "POST":
        ok, error = eliminar_cobro_util(cobrament, request)
        if error:
            return render(
                request,
                "eliminar_cobro.html",
                {"mensaje": error, "cobrament": cobrament},
            )
        return redirect(
            reverse(
                "lista_cobraments",
                kwargs={
                    "data": cobrament.reserva.fecha,
                    "id_jugador": cobrament.jugador.id_jugador,
                },
            )
        )
    return render(request, "eliminar_cobro.html", {"cobrament": cobrament})

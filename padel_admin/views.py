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
    totals = Cobrament.objects.filter(reserva=reserva)
    ya_pago = Cobrament.objects.filter(reserva=reserva, jugador=jugador).exists()
    importe = None
    if reserva:
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
                    raise InvalidOperation("Importe no válido")
                partes = str(importe).split(".")
                if len(partes[0]) > 8:
                    raise InvalidOperation("Importe demasiado grande para el campo.")
                # Redondear hacia abajo (floor) a entero para mostrar, pero guardar con dos decimales
                try:
                    importe_floor = importe.to_integral_value(rounding="ROUND_FLOOR")
                except Exception as e:
                    logging.error(f"Error al redondear importe_floor: {e}")
                    importe_floor = Decimal("0.00")
                try:
                    # Asegura que importe sea Decimal válido y no NaN/infinito
                    if not isinstance(importe, Decimal):
                        importe = Decimal(str(importe))
                    if not importe.is_finite() or importe.is_nan():
                        importe = Decimal("0.00")
                    else:
                        # Cuantiza solo si tiene parte decimal
                        importe = importe.quantize(Decimal("0.01"))
                except Exception as e:
                    logging.error(f"Error al cuantizar importe: {e}")
                    importe = Decimal("0.00")
        except (InvalidOperation, TypeError, ValueError) as e:
            mensaje = f"Error al calcular el importe: {str(e)}. Verifique la tarifa configurada."
            return render(
                request,
                "lista_cobraments.html",
                {
                    "mensaje": mensaje,
                    "jugador": jugador,
                    "reserva": reserva,
                    "importe": 0,
                    "ya_pago": ya_pago,
                },
            )
    if request.method == "POST":
        if totals.count() != 4:
            if ya_pago:
                mensaje = "El jugador ya pagó esta reserva."
                return render(
                    request,
                    "lista_cobraments.html",
                    {
                        "mensaje": mensaje,
                        "jugador": jugador,
                        "reserva": reserva,
                        "importe": (
                            importe_floor if "importe_floor" in locals() else importe
                        ),
                        "ya_pago": ya_pago,
                    },
                )
            try:
                rec = Recepcionista.objects.get(DNI=acceso)
            except Recepcionista.DoesNotExist:
                mensaje = "Recepcionista no encontrado. Inicie sesión nuevamente."
                return render(request, "landing.html", {"mensaje": mensaje})

            # --- Start of Refactored Importe Validation ---
            # Ensure importe is a Decimal and finite.
            if not isinstance(importe, Decimal):
                try:
                    temp_importe_str = str(importe)
                    if (
                        temp_importe_str.lower() == "none"
                    ):  # Handle if importe was Python None then str()
                        logging.warning(
                            f"Importe was 'None' string, attempting to treat as 0 for cobro {reserva.id} by {jugador.id_jugador}"
                        )
                        importe = Decimal("0.00")
                    else:
                        importe = Decimal(temp_importe_str)
                except InvalidOperation:
                    logging.error(
                        f"Importe '{importe}' could not be converted to Decimal for cobro {reserva.id} by {jugador.id_jugador}."
                    )
                    # If conversion fails, it's a critical issue with the calculated importe.
                    mensaje = f"Error crítico: El valor del importe ({importe}) no es un número decimal válido. No se puede registrar el cobro."
                    return render(
                        request,
                        "lista_cobraments.html",
                        {
                            "mensaje": mensaje,
                            "jugador": jugador,
                            "reserva": reserva,
                            "importe": Decimal("0.00"),
                            "ya_pago": ya_pago,
                        },
                    )

            if not importe.is_finite():
                logging.warning(
                    f"Importe is non-finite ({importe}) before saving cobro {reserva.id} by {jugador.id_jugador}. Cobro prevented."
                )
                mensaje = f"Error: El importe calculado ({importe}) es inválido (NaN/Infinito). No se puede registrar el cobro. Verifique la tarifa."
                return render(
                    request,
                    "lista_cobraments.html",
                    {
                        "mensaje": mensaje,
                        "jugador": jugador,
                        "reserva": reserva,
                        "importe": Decimal(
                            "0.00"
                        ),  # Display 0.00 or a representation of the error
                        "ya_pago": ya_pago,
                    },
                )

            # At this point, importe is a finite Decimal. Now quantize.
            try:
                importe = importe.quantize(Decimal("0.01"), rounding="ROUND_FLOOR")
            except InvalidOperation:
                # This should not happen if importe is finite, but as a safeguard:
                logging.error(
                    f"CRITICAL: InvalidOperation during quantize of finite importe {importe} for cobro {reserva.id} by {jugador.id_jugador}."
                )
                mensaje = "Error crítico al redondear el importe. No se pudo registrar el cobro."
                return render(
                    request,
                    "lista_cobraments.html",
                    {
                        "mensaje": mensaje,
                        "jugador": jugador,
                        "reserva": reserva,
                        "importe": importe,  # Show the problematic importe
                        "ya_pago": ya_pago,
                    },
                )

            # Check model constraints for Cobrament.importe (max_digits=4, decimal_places=2)
            # Ahora permitimos hasta 1,000,000.00
            if abs(importe) >= Decimal("1000000.01"):
                mensaje = f"El importe final ({importe}) excede el máximo permitido de 1,000,000.00."
                return render(
                    request,
                    "lista_cobraments.html",
                    {
                        "mensaje": mensaje,
                        "jugador": jugador,
                        "reserva": reserva,
                        "importe": importe,
                        "ya_pago": ya_pago,
                    },
                )

            if importe == Decimal(
                "0.00"
            ):  # This check was present in your original code
                mensaje = "No se puede registrar el cobro porque el importe es 0. Verifique la tarifa configurada."
                return render(
                    request,
                    "lista_cobraments.html",
                    {
                        "mensaje": mensaje,
                        "jugador": jugador,
                        "reserva": reserva,
                        "importe": importe,
                        "ya_pago": ya_pago,  # ya_pago should likely be False or its current state
                    },
                )
            # --- End of Refactored Importe Validation ---

            try:
                cobrament = Cobrament.objects.create(
                    reserva=reserva,
                    jugador=jugador,
                    data=data,
                    importe=importe,
                    recepcionista=rec,
                )
                # Registrar histórico de pago
                from .models import HistoricoReserva

                HistoricoReserva.objects.create(
                    reserva=reserva,
                    jugador=jugador,
                    accion="pago",
                    importe=importe,
                    detalles=f"Pago registrado por {jugador.nom} {jugador.cognom}",
                )
                # .create() already saves, no need for cobrament.save() here
            except Exception as e:
                logging.error(f"Error al guardar el cobro: {e}")
                mensaje = f"Error al guardar el cobro: {str(e)}. Importe ({importe}) inválido."
                return render(
                    request,
                    "lista_cobraments.html",
                    {
                        "mensaje": mensaje,
                        "jugador": jugador,
                        "reserva": reserva,
                        "importe": importe,
                        "ya_pago": False,
                    },
                )
            mensaje2 = (
                jugador.nom
                + " "
                + jugador.cognom
                + " ha realizado un pago de "
                + str(importe_floor if "importe_floor" in locals() else importe)
                + " $"
            )
            return render(
                request,
                "lista_cobraments.html",
                {
                    "mensaje2": mensaje2,
                    "importe": (
                        importe_floor if "importe_floor" in locals() else importe
                    ),
                    "jugador": jugador,
                    "reserva": reserva,
                    "ya_pago": True,
                },
            )
        else:
            mensaje = "Limite de 4 persones en la cancha."
            return render(
                request,
                "lista_cobraments.html",
                {
                    "mensaje": mensaje,
                    "jugador": jugador,
                    "reserva": reserva,
                    "importe": importe,
                    "ya_pago": ya_pago,
                },
            )
    return render(
        request,
        "lista_cobraments.html",
        {
            "jugador": jugador,
            "reserva": reserva,
            "importe": importe_floor if "importe_floor" in locals() else importe,
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

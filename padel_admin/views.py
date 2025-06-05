from datetime import datetime, date, time, timedelta
from enum import unique
import json
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
import random, uuid  # Importar uuid si se usa para id_jugador
from decimal import (
    Decimal,
    InvalidOperation,
)  # Asegúrate que ConfiguracionGlobal esté aquí
from .models import (
    Jugadors,
    Reserva,
    Cobrament,
    Recepcionista,
    Pistes,
    ConfiguracionGlobal,
)
from django.db.models import Sum, Q
from django.conf import settings
import os
from django.core.exceptions import MultipleObjectsReturned

# TODO: Reemplazar con el sistema de autenticación de Django


def landing(request):
    if request.method == "POST":
        dni = request.POST.get("dni")
        contrasenya = request.POST.get("contrasenya")

        try:
            # ALERTA DE SEGURIDAD: Comparación de contraseña en texto plano.
            recepcionista = Recepcionista.objects.get(DNI=dni, contrasenya=contrasenya)
            response = redirect("lista_reserves")
            response.set_cookie(
                "acceso", str(recepcionista.DNI)
            )  # Establecer cookie de acceso
            return response
        except:
            mensaje = "El DNI o la contrasenya són incorrectes"
            return render(request, "landing.html", {"mensaje": mensaje})

    else:
        return render(request, "landing.html")


def lista_reserves(request):
    # TODO: Usar @login_required y sistema de autenticación de Django
    acceso = request.COOKIES.get("acceso")
    if acceso:
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

        if request.method == "POST":
            # eliminar jugador
            if request.POST.get("_method") == "DELETE":
                jugador_id = request.POST.get("jugador_id")
                data = request.POST.get("data")
                jugador = Jugadors.objects.get(id_jugador=jugador_id)
                reserva = Reserva.objects.get(jugador=jugador, data=data)
                reserva.delete()
                reserves = Reserva.objects.filter(data=data).order_by(
                    "horaInici", "horaFinalitzacio", "pista"
                )
                fecha = datetime.strptime(data, "%Y-%m-%d").date()
                day = fecha.strftime("%Y-%m-%d")
                return render(
                    request,
                    "lista_reserves.html",
                    {"reserves": reserves, "day": day, "hours": hours},
                )

            # AFEGIR RESERVA
            fecha2 = request.POST.get("fecha-2")
            hora_inici_str = request.POST.get("horaInici")
            hora_inici = datetime.strptime(hora_inici_str, "%H:%M").time()
            duracio = request.POST.get("horaFinalitzacio")
            type_pista = request.POST.get("Pista")
            jugador_nom = request.POST.get("jugador_nom")
            jugador_cognom = request.POST.get("jugador_cognom")
            # transformem duracio en hora de finalitzacio
            if duracio == "30":
                hora_finalitzacio = (
                    datetime.combine(datetime.min, hora_inici) + timedelta(minutes=30)
                ).time()
            elif duracio == "60":
                hora_finalitzacio = (
                    datetime.combine(datetime.min, hora_inici) + timedelta(hours=1)
                ).time()
            else:
                hora_finalitzacio = (
                    datetime.combine(datetime.min, hora_inici)
                    + timedelta(hours=1, minutes=30)
                ).time()
            # obtenim el jugador
            try:
                jugador = Jugadors.objects.get(nom=jugador_nom, cognom=jugador_cognom)
            except Jugadors.DoesNotExist:
                mensaje_error = "El jugador introducido no existe."
                fecha = date.today()
                day = fecha.strftime("%Y-%m-%d")
                reserves = Reserva.objects.filter(data=fecha).order_by(
                    "horaInici", "horaFinalitzacio", "pista"
                )
                return render(
                    request,
                    "lista_reserves.html",
                    {
                        "reserves": reserves,
                        "day": day,
                        "hours": hours,
                        "mensaje_error": mensaje_error,
                    },
                )
            except MultipleObjectsReturned:
                mensaje_error = "Hay más de un jugador con ese nombre y apellido."
                fecha = date.today()
                day = fecha.strftime("%Y-%m-%d")
                reserves = Reserva.objects.filter(data=fecha).order_by(
                    "horaInici", "horaFinalitzacio", "pista"
                )
                return render(
                    request,
                    "lista_reserves.html",
                    {
                        "reserves": reserves,
                        "day": day,
                        "hours": hours,
                        "mensaje_error": mensaje_error,
                    },
                )
            try:
                # consultem que eljugador no hagi fet reserves al mateix dia
                reserva_feta = Reserva.objects.get(jugador=jugador, data=fecha2)
                mensaje_error = "El jugador ya ha realizado una reserva en esta fecha."
                fecha = date.today()
                day = fecha.strftime("%Y-%m-%d")
                reserves = Reserva.objects.filter(data=fecha).order_by(
                    "horaInici", "horaFinalitzacio", "pista"
                )
                return render(
                    request,
                    "lista_reserves.html",
                    {
                        "reserves": reserves,
                        "day": day,
                        "hours": hours,
                        "mensaje_error": mensaje_error,
                    },
                )
            except:
                print("correcte")
            # consultem les pistes ocupades i li assignem una lliure
            # --- INICIO CORRECCIÓN LÓGICA DISPONIBILIDAD PISTA ---
            pistas_del_tipo_solicitado = Pistes.objects.filter(tipus=type_pista)
            pistas_disponibles_en_horario = []

            for pista_candidata in pistas_del_tipo_solicitado:
                reservas_solapadas = Reserva.objects.filter(
                    pista=pista_candidata,
                    data=fecha2,
                    horaInici__lt=hora_finalitzacio,
                    horaFinalitzacio__gt=hora_inici,
                ).exists()
                if not reservas_solapadas:
                    pistas_disponibles_en_horario.append(pista_candidata)

            if not pistas_disponibles_en_horario:
                mensaje_error = (
                    f"No hay pistas del tipo {type_pista} disponibles "
                    f"para el horario de {hora_inici_str} a {hora_finalitzacio.strftime('%H:%M')} en la fecha {fecha2}. "
                    "Por favor, intente otro horario o tipo de pista."
                )
                # Re-renderizar con el error, manteniendo la fecha seleccionada si es posible
                try:
                    fecha_render = datetime.strptime(fecha2, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    fecha_render = date.today()  # Fallback

                day_render = fecha_render.strftime("%Y-%m-%d")
                reserves_render = Reserva.objects.filter(data=fecha_render).order_by(
                    "horaInici", "horaFinalitzacio", "pista"
                )
                return render(
                    request,
                    "lista_reserves.html",
                    {
                        "reserves": reserves_render,
                        "day": day_render,
                        "hours": hours,
                        "mensaje_error": mensaje_error,
                    },
                )

            pista_ = random.choice(pistas_disponibles_en_horario)
            # --- FIN CORRECCIÓN LÓGICA DISPONIBILIDAD PISTA ---

            # recollim recepcionista que realitza reserva a través de cookie
            rec = Recepcionista.objects.get(DNI=request.COOKIES.get("acceso"))
            # guardem reserva
            Reserva.objects.create(
                jugador=jugador,
                data=fecha2,
                pista=pista_,
                horaInici=hora_inici,
                horaFinalitzacio=hora_finalitzacio,
                recepcionista=rec,
            )

        fecha = request.GET.get("fecha")
        if fecha:
            fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
            reserves = Reserva.objects.filter(data=fecha).order_by(
                "horaInici", "horaFinalitzacio", "pista"
            )
            day = fecha.strftime("%Y-%m-%d")
        else:
            fecha = date.today()
            day = fecha.strftime("%Y-%m-%d")
            reserves = Reserva.objects.filter(data=fecha).order_by(
                "horaInici", "horaFinalitzacio", "pista"
            )
        return render(
            request,
            "lista_reserves.html",
            {"reserves": reserves, "day": day, "hours": hours},
        )
    else:
        mensaje = "Accés denegat"
        return render(request, "landing.html", {"mensaje": mensaje})


def lista_jugadors(request):
    # TODO: Usar @login_required y sistema de autenticación de Django
    acceso = request.COOKIES.get("acceso")
    if acceso:
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
            # ALERTA DE SEGURIDAD: Contraseña es el nombre y se guarda en texto plano.
            # TODO: Implementar hashing de contraseña y un método seguro para establecerla.
            # contrasenya = make_password(request.POST.get("contrasenya_segura"))
            contrasenya_temporal_insegura = str(nom)

            # Generación de id_jugador - Necesita ser más robusta o usar UUID/AutoField
            # Esta es una solución temporal y poco eficiente para evitar colisiones simples.
            # Para producción, se recomienda UUID o una estrategia de generación de ID más sólida.
            id_generado = False
            intentos = 0
            new_id_jugador = None
            while not id_generado and intentos < 100:  # Limitar intentos
                # Considerar usar algo más único si es CharField, o cambiar a AutoField/UUIDField
                temp_id = str(
                    random.randint(10000, 999999)
                )  # Aumentar rango si es necesario
                if not Jugadors.objects.filter(id_jugador=temp_id).exists():
                    new_id_jugador = temp_id
                    id_generado = True
                intentos += 1

            if new_id_jugador:
                Jugadors.objects.create(
                    id_jugador=new_id_jugador,
                    nom=nom,
                    cognom=cognom,
                    email=email,
                    telefon=telefon,
                    nivell=nivell,
                    contrasenya=contrasenya_temporal_insegura,  # Usar contraseña hasheada
                )
            else:
                # TODO: Manejar el caso en que no se pudo generar un ID único (muy improbable con rango grande, pero posible)
                # Podrías usar messages.error(request, "No se pudo generar un ID único para el jugador.")
                pass

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
    else:
        mensaje = "Accés denegat"
        return render(request, "landing.html", {"mensaje": mensaje})


def lista_cobraments(request, data, id_jugador):
    # TODO: Usar @login_required y sistema de autenticación de Django
    acceso = request.COOKIES.get("acceso")
    if acceso:
        # identificar reserva
        jugador = Jugadors.objects.get(id_jugador=id_jugador)
        reserva = Reserva.objects.get(data=data, jugador=jugador)

        totals = Cobrament.objects.filter(reserva=reserva)

        # Obtener precio de la hora desde la configuración (modelo ConfiguracionGlobal)
        # precio_config = ConfiguracionGlobal.objects.get(clave="PRECIO_HORA_CANCHA")
        # preu_hora = Decimal(precio_config.valor)

        if request.method == "POST":
            if totals.count() != 4:
                jugador_nom = request.POST.get("jugador-nom")
                jugador_cognom = request.POST.get("jugador-cognom")

                try:
                    jugador = Jugadors.objects.get(
                        nom=jugador_nom, cognom=jugador_cognom
                    )
                except Jugadors.DoesNotExist:
                    # TODO: Usar django.contrib.messages
                    mensaje_error = "Jugador introduït inexistent a la base de dades."
                    return render(
                        request,
                        "lista_cobraments.html",
                        {
                            "mensaje_error": mensaje_error,
                            "reserva": reserva,
                            "jugador_reserva": jugador,
                            "data_reserva": data,
                            "totals": totals,
                        },
                    )
                except MultipleObjectsReturned:
                    mensaje_error = "Hay más de un jugador con ese nombre y apellido."
                    return render(
                        request,
                        "lista_cobraments.html",
                        {
                            "mensaje_error": mensaje_error,
                            "reserva": reserva,
                            "jugador_reserva": jugador,
                            "data_reserva": data,
                            "totals": totals,
                        },
                    )

                try:
                    existeix_cobrament = Cobrament.objects.get(
                        reserva=reserva, jugador=jugador
                    )
                    mensaje_error = (
                        "Este jugador ya ha realizado un pago para esta reserva."
                    )
                    return render(
                        request,
                        "lista_cobraments.html",
                        {
                            "mensaje_error": mensaje_error,
                            "reserva": reserva,
                            "jugador_reserva": jugador,
                            "data_reserva": data,
                            "totals": totals,
                        },
                    )
                except Cobrament.DoesNotExist:
                    pass  # Es correcto que no exista, seguimos con el proceso

                try:
                    # LEER PRECIO DESDE settings.py (TEMPORAL - MEJOR DESDE MODELO CONFIG)
                    precio_str = (
                        str(settings.PRECIO_HORA_CANCHA)
                        .strip()
                        .replace(",", ".")
                        .replace('"', "")
                    )
                    preu_hora = Decimal(precio_str)
                    if preu_hora <= 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError, TypeError):
                    mensaje_error = (
                        "El precio de la hora no es válido. Revise la configuración."
                    )
                    return render(
                        request,
                        "lista_cobraments.html",
                        {
                            "mensaje_error": mensaje_error,
                            "reserva": reserva,
                            "jugador_reserva": jugador,
                            "data_reserva": data,
                            "totals": totals,
                        },
                    )

                hora_inicio = datetime.strptime(
                    reserva.horaInici.strftime("%H:%M:%S"), "%H:%M:%S"
                )
                hora_final = datetime.strptime(
                    reserva.horaFinalitzacio.strftime("%H:%M:%S"), "%H:%M:%S"
                )

                diferencia_tiempo = hora_final - hora_inicio
                diferencia_segundos = Decimal(str(diferencia_tiempo.total_seconds()))
                diferencia_horas = diferencia_segundos / Decimal("3600")

                try:
                    importe = (preu_hora * diferencia_horas).quantize(Decimal("0.01"))
                except (InvalidOperation, ValueError, TypeError):
                    mensaje_error = "Error al calcular el importe. Revise los valores de precio y duración."
                    return render(
                        request,
                        "lista_cobraments.html",
                        {
                            "mensaje_error": mensaje_error,
                            "reserva": reserva,
                            "jugador_reserva": jugador,
                            "data_reserva": data,
                            "totals": totals,
                        },
                    )

                # recollim recepcionista que realitza reserva a través de cookie
                rec = Recepcionista.objects.get(DNI=request.COOKIES.get("acceso"))
                cobrament = Cobrament.objects.create(
                    reserva=reserva,
                    jugador=jugador,
                    data=data,
                    importe=importe,
                    recepcionista=rec,
                )
                cobrament.save()

                mensaje_exito = (
                    jugador_nom
                    + " "
                    + jugador_cognom
                    + " ha realizado un pago de $"
                    + str(int(importe))
                )
                # Actualizar 'totals' después de crear el nuevo cobro
                totals = Cobrament.objects.filter(reserva=reserva)
                return render(
                    request,
                    "lista_cobraments.html",
                    {
                        "mensaje_exito": mensaje_exito,
                        "reserva": reserva,
                        "jugador_reserva": jugador,
                        "data_reserva": data,
                        "totals": totals,
                    },
                )
            else:
                mensaje_error = (
                    "Límit de 4 pagaments per reserva assolit (un per jugador)."
                )
                return render(
                    request,
                    "lista_cobraments.html",
                    {
                        "mensaje_error": mensaje_error,
                        "reserva": reserva,
                        "jugador_reserva": jugador,
                        "data_reserva": data,
                        "totals": totals,
                    },
                )

        # Para el método GET o si no es POST
        return render(
            request,
            "lista_cobraments.html",
            {
                "reserva": reserva,
                "jugador_reserva": jugador,
                "data_reserva": data,
                "totals": totals,
            },
        )
    else:
        mensaje = "Accés denegat"
        return render(request, "landing.html", {"mensaje": mensaje})


def historial_cobros(request):
    # TODO: Usar @login_required y sistema de autenticación de Django
    acceso = request.COOKIES.get("acceso")
    if acceso:
        # Obtener parámetros de filtrado
        fecha_desde = request.GET.get("fecha_desde")
        fecha_hasta = request.GET.get("fecha_hasta")
        jugador = request.GET.get("jugador")

        # Consulta base
        cobros = Cobrament.objects.all().order_by("-data")

        # Aplicar filtros si existen
        if fecha_desde:
            fecha_desde = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
            cobros = cobros.filter(data__gte=fecha_desde)
        else:
            fecha_desde = date.today() - timedelta(days=30)  # Por defecto, último mes
            cobros = cobros.filter(data__gte=fecha_desde)

        if fecha_hasta:
            fecha_hasta = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
            cobros = cobros.filter(data__lte=fecha_hasta)
        else:
            fecha_hasta = date.today()

        if jugador:
            cobros = cobros.filter(
                Q(jugador__nom__icontains=jugador)
                | Q(jugador__cognom__icontains=jugador)
            )

        # Calcular total
        total_importe = cobros.aggregate(total=Sum("importe"))["total"]
        if total_importe is None:
            total_importe = 0

        # Paginación
        paginator = Paginator(cobros, 20)  # 20 cobros por página
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "cobros": page_obj,
            "page_obj": page_obj,
            "total_importe": total_importe,  # Mantener como Decimal para formato en plantilla
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "jugador": jugador,
        }

        return render(request, "historial_cobros.html", context)
    else:
        mensaje = "Accés denegat"
        return render(request, "landing.html", {"mensaje": mensaje})


def configuracion(request):
    # TODO: Usar @login_required y sistema de autenticación de Django
    acceso = request.COOKIES.get("acceso")
    if acceso:
        mensaje_exito = None
        mensaje_error = None

        # Clave para el precio en el modelo ConfiguracionGlobal
        PRECIO_KEY = "PRECIO_HORA_CANCHA"

        if request.method == "POST":
            nuevo_precio_str = request.POST.get("precio_hora")
            if nuevo_precio_str:
                try:
                    # Elimina espacios y reemplaza comas por puntos
                    nuevo_precio_str_limpio = nuevo_precio_str.strip().replace(",", ".")
                    nuevo_precio_decimal = Decimal(nuevo_precio_str_limpio)

                    if nuevo_precio_decimal > 0:
                        # Guardar en el modelo ConfiguracionGlobal
                        config_precio, created = (
                            ConfiguracionGlobal.objects.update_or_create(
                                clave=PRECIO_KEY,
                                defaults={"valor": str(nuevo_precio_decimal)},
                            )
                        )
                        mensaje_exito = f"El precio se ha actualizado correctamente a ${nuevo_precio_decimal} por hora."
                    else:
                        mensaje_error = "El precio debe ser un número positivo."
                except InvalidOperation:
                    mensaje_error = "El precio introducido no es válido. Usa solo números y punto decimal."
                except Exception as e:  # Captura otras posibles excepciones
                    mensaje_error = f"Error inesperado: {e}"

        # Obtener el precio actual del modelo ConfiguracionGlobal
        try:
            precio_actual_obj = ConfiguracionGlobal.objects.get(clave=PRECIO_KEY)
            precio_actual = Decimal(precio_actual_obj.valor)
        except ConfiguracionGlobal.DoesNotExist:
            precio_actual = Decimal(
                settings.PRECIO_HORA_CANCHA
            )  # Fallback a settings si no existe en DB
            mensaje_error = (
                mensaje_error
                or "Precio no configurado en la base de datos, usando valor por defecto."
            )
        except InvalidOperation:
            precio_actual = Decimal(settings.PRECIO_HORA_CANCHA)  # Fallback
            mensaje_error = (
                mensaje_error
                or "Valor de precio en base de datos no es un decimal válido."
            )

        context = {
            "precio_actual": precio_actual,
            "mensaje_exito": mensaje_exito,
            "mensaje_error": mensaje_error,
        }

        return render(request, "configuracion.html", context)
    else:
        mensaje = "Accés denegat"
        return render(request, "landing.html", {"mensaje": mensaje})


def logout(request):
    response = redirect(
        "landing"
    )  # Redirige a la página de inicio de sesión o cualquier otra página después de hacer logout
    response.delete_cookie("acceso")  # Elimina la cookie 'recepcionista_id'
    return response

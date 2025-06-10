from datetime import datetime, date, time, timedelta
from enum import unique
import json
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
import random
from .models import Jugadors, Reserva, Cobrament, Recepcionista, Pistes, Recepcionista
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned


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

    if request.method == "POST":
        # eliminar jugador
        if request.POST.get("_method") == "DELETE":
            jugador_id = request.POST.get("jugador_id")
            fecha = request.POST.get("data")
            try:
                jugador = Jugadors.objects.get(id_jugador=jugador_id)
                reserva = Reserva.objects.get(jugador=jugador, fecha=fecha)
                reserva.delete()
            except (Jugadors.DoesNotExist, Reserva.DoesNotExist):
                mensaje_error = "No se encontró el jugador o la reserva."
                fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
                day = fecha_obj.strftime("%Y-%m-%d")
                reserves = Reserva.objects.filter(fecha=fecha_obj).order_by(
                    "hora_inicio", "hora_inicio", "cancha"
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
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            day = fecha_obj.strftime("%Y-%m-%d")
            reserves = Reserva.objects.filter(fecha=fecha_obj).order_by(
                "hora_inicio", "hora_inicio", "cancha"
            )
            return render(
                request,
                "lista_reserves.html",
                {"reserves": reserves, "day": day, "hours": hours},
            )
        # AFEGIR RESERVA
        fecha2 = request.POST.get("fecha-2")
        hora_inicio_str = request.POST.get("horaInici")
        hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M").time()
        duracio = request.POST.get("horaFinalitzacio")
        type_cancha = request.POST.get("Pista")
        cancha_numero = request.POST.get("cancha_numero")
        jugador_nom = request.POST.get("jugador_nom")
        jugador_cognom = request.POST.get("jugador_cognom")
        # transformem duracio en hora de finalitzacio
        if duracio == "30":
            hora_fin = (
                datetime.combine(datetime.min, hora_inicio) + timedelta(minutes=30)
            ).time()
        elif duracio == "60":
            hora_fin = (
                datetime.combine(datetime.min, hora_inicio) + timedelta(hours=1)
            ).time()
        else:
            hora_fin = (
                datetime.combine(datetime.min, hora_inicio)
                + timedelta(hours=1, minutes=30)
            ).time()
        # obtenim el jugador
        try:
            jugador = Jugadors.objects.get(nom=jugador_nom, cognom=jugador_cognom)
        except Jugadors.DoesNotExist:
            mensaje_error = "El jugador no existe."
            fecha = date.today()
            day = fecha.strftime("%Y-%m-%d")
            reserves = Reserva.objects.filter(fecha=fecha).order_by(
                "hora_inicio", "hora_inicio", "cancha"
            )
            return render(
                request,
                "lista_reserves.html",
                {
                    "reserves": reserves,
                    "day": day,
                    "hours": hours,
                    "pistas_disponibles": pistas_disponibles,
                    "mensaje_error": mensaje_error,
                },
            )
        try:
            reserva_feta = Reserva.objects.get(jugador=jugador, fecha=fecha2)
            mensaje_error = "El jugador ya tiene una reserva en este dia."
            fecha = date.today()
            day = fecha.strftime("%Y-%m-%d")
            reserves = Reserva.objects.filter(fecha=fecha).order_by(
                "hora_inicio", "hora_inicio", "cancha"
            )
            return render(
                request,
                "lista_reserves.html",
                {
                    "reserves": reserves,
                    "day": day,
                    "hours": hours,
                    "pistas_disponibles": pistas_disponibles,
                    "mensaje_error": mensaje_error,
                },
            )
        except Reserva.DoesNotExist:
            pass
        # Selección de cancha por número
        if not cancha_numero:
            mensaje_error = "Debes seleccionar un número de cancha."
            fecha = date.today()
            day = fecha.strftime("%Y-%m-%d")
            reserves = Reserva.objects.filter(fecha=fecha).order_by(
                "hora_inicio", "hora_inicio", "cancha"
            )
            return render(
                request,
                "lista_reserves.html",
                {
                    "reserves": reserves,
                    "day": day,
                    "hours": hours,
                    "pistas_disponibles": pistas_disponibles,
                    "mensaje_error": mensaje_error,
                },
            )
        try:
            cancha_ = Pistes.objects.get(numero=cancha_numero, tipo=type_cancha)
        except Pistes.DoesNotExist:
            mensaje_error = "La cancha seleccionada no existe o no es del tipo elegido."
            fecha = date.today()
            day = fecha.strftime("%Y-%m-%d")
            reserves = Reserva.objects.filter(fecha=fecha).order_by(
                "hora_inicio", "hora_inicio", "cancha"
            )
            return render(
                request,
                "lista_reserves.html",
                {
                    "reserves": reserves,
                    "day": day,
                    "hours": hours,
                    "pistas_disponibles": pistas_disponibles,
                    "mensaje_error": mensaje_error,
                },
            )
        try:
            rec = Recepcionista.objects.get(DNI=acceso)
        except Recepcionista.DoesNotExist:
            mensaje_error = "Recepcionista no encontrado. Inicie sesión nuevamente."
            return render(request, "landing.html", {"mensaje": mensaje_error})
        reserva = Reserva(
            jugador=jugador,
            fecha=fecha2,
            cancha=cancha_,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            recepcionista=rec,
        )
        reserva.save()

    fecha = request.GET.get("fecha")
    if fecha:
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
        reserves = Reserva.objects.filter(fecha=fecha_obj).order_by(
            "hora_inicio", "hora_inicio", "cancha"
        )
        day = fecha_obj.strftime("%Y-%m-%d")
    else:
        fecha = date.today()
        day = fecha.strftime("%Y-%m-%d")
        reserves = Reserva.objects.filter(fecha=fecha).order_by(
            "hora_inicio", "hora_inicio", "cancha"
        )
    return render(
        request,
        "lista_reserves.html",
        {
            "reserves": reserves,
            "day": day,
            "hours": hours,
            "pistas_disponibles": pistas_disponibles,
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
    if request.method == "POST":
        if totals.count() != 4:
            jugador_nom = request.POST.get("jugador-nom")
            jugador_cognom = request.POST.get("jugador-cognom")
            try:
                jugador = Jugadors.objects.get(nom=jugador_nom, cognom=jugador_cognom)
            except Jugadors.DoesNotExist:
                mensaje = "Jugador inexistente en la base de datos."
                return render(request, "lista_cobraments.html", {"mensaje": mensaje})
            try:
                existeix_cobrament = Cobrament.objects.get(
                    reserva=reserva, jugador=jugador
                )
                mensaje = "El jugador ya pago esta reserva."
                return render(request, "lista_cobraments.html", {"mensaje": mensaje})
            except Cobrament.DoesNotExist:
                preu_hora = 10
                hora_inicio = datetime.strptime(
                    reserva.hora_inicio.strftime("%H:%M:%S"), "%H:%M:%S"
                )
                hora_final = datetime.strptime(
                    reserva.hora_fin.strftime("%H:%M:%S"), "%H:%M:%S"
                )
                diferencia_tiempo = hora_final - hora_inicio
                diferencia_horas = int(diferencia_tiempo.total_seconds() / 3600)
                diferencia_minutos = int(
                    (diferencia_tiempo.total_seconds() % 3600) / 60
                )
                diferencia_horas += round(diferencia_minutos / 60, 2)
                importe = preu_hora * diferencia_horas
                try:
                    rec = Recepcionista.objects.get(DNI=acceso)
                except Recepcionista.DoesNotExist:
                    mensaje = "Recepcionista no encontrado. Inicie sesión nuevamente."
                    return render(request, "landing.html", {"mensaje": mensaje})
                cobrament = Cobrament.objects.create(
                    reserva=reserva,
                    jugador=jugador,
                    data=data,
                    importe=importe,
                    recepcionista=rec,
                )
                cobrament.save()
                mensaje2 = (
                    jugador_nom
                    + " "
                    + jugador_cognom
                    + " ha realizado un pago de "
                    + str(importe)
                    + " $"
                )
                return render(
                    request,
                    "lista_cobraments.html",
                    {"mensaje2": mensaje2, "importe": importe},
                )
        else:
            mensaje = "Limite de 4 persones en la cancha."
            return render(request, "lista_cobraments.html", {"mensaje": mensaje})
    return render(request, "lista_cobraments.html")


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
                    estados.append(
                        (True, fecha, reserva.jugador.nom, reserva.jugador.cognom)
                    )
                else:
                    estados.append((False, fecha, "", ""))
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
        cancha_id = request.POST.get("cancha_id")
        cancha_tipo = request.POST.get("cancha_tipo")
        fecha = request.POST.get("fecha")
        hora_inicio = request.POST.get("hora_inicio")
        jugador_id = request.COOKIES.get("jugador_id")
        if not jugador_id:
            return redirect("calendario_canchas")
        try:
            jugador = Jugadors.objects.get(id_jugador=jugador_id)
        except Jugadors.DoesNotExist:
            messages.error(
                request, "El jugador no existe o no ha iniciado sesión correctamente."
            )
            return redirect("calendario_canchas")
        try:
            cancha = Pistes.objects.get(numero=cancha_id, tipo=cancha_tipo)
        except Pistes.DoesNotExist:
            messages.error(
                request, "La cancha seleccionada no existe o no es del tipo elegido."
            )
            return redirect("calendario_canchas")
        hora_inicio_obj = datetime.strptime(hora_inicio, "%H:%M:%S").time()
        hora_fin_obj = (
            datetime.combine(date.today(), hora_inicio_obj) + timedelta(minutes=30)
        ).time()
        # Validar que no haya solapamiento
        if Reserva.objects.filter(
            cancha=cancha,
            fecha=fecha,
            hora_inicio__lt=hora_fin_obj,
            hora_fin__gt=hora_inicio_obj,
        ).exists():
            messages.error(request, "La cancha ya está reservada en ese horario.")
            return redirect("calendario_canchas")
        Reserva.objects.create(
            jugador=jugador,
            fecha=fecha,
            cancha=cancha,
            hora_inicio=hora_inicio_obj,
            hora_fin=hora_fin_obj,
            recepcionista=None,
        )
        messages.success(request, "Reserva creada exitosamente.")
        return redirect("calendario_canchas")


def crear_reserva(request):
    if request.method == "POST":
        cancha_id = request.POST.get("cancha_id")
        fecha = request.POST.get("fecha")
        hora_inicio_str = request.POST.get("hora_inicio")
        duracion = int(request.POST.get("duracion"))
        jugador_nom = request.POST.get("jugador_nom")
        jugador_cognom = request.POST.get("jugador_cognom")
        hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M").time()
        dt = datetime.combine(datetime.today(), hora_inicio)
        dt = dt + timedelta(minutes=duracion)
        hora_fin = dt.time()
        try:
            jugador = Jugadors.objects.get(nom=jugador_nom, cognom=jugador_cognom)
            cancha = Pistes.objects.get(numero=cancha_id)
            if Reserva.objects.filter(
                cancha=cancha,
                fecha=fecha,
                hora_inicio__lt=hora_fin,
                hora_fin__gt=hora_inicio,
            ).exists():
                messages.error(request, "La cancha ya está reservada en ese horario.")
                return redirect("calendario_canchas")
            acceso = request.COOKIES.get("acceso")
            if not acceso:
                messages.error(request, "No hay sesión de recepcionista activa.")
                return redirect("landing")
            recepcionista = Recepcionista.objects.get(DNI=acceso)
            reserva = Reserva(
                jugador=jugador,
                fecha=fecha,
                cancha=cancha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                recepcionista=recepcionista,
            )
            reserva.save()
            messages.success(request, "Reserva creada exitosamente.")
        except Jugadors.DoesNotExist:
            messages.error(request, "El jugador no existe.")
        except Pistes.DoesNotExist:
            messages.error(request, "La cancha no existe.")
        except Recepcionista.DoesNotExist:
            messages.error(
                request, "Recepcionista no encontrado. Inicie sesión nuevamente."
            )
        except Exception as e:
            messages.error(request, f"Error al crear la reserva: {str(e)}")
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

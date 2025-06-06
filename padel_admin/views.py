from datetime import datetime, date, time, timedelta
from enum import unique
import json
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
import random
from .models import Jugadors, Reserva, Cobrament, Recepcionista, Pistes, Recepcionista


def landing(request):
    if request.method == "POST":
        dni = request.POST.get("dni")
        contrasenya = request.POST.get("contrasenya")

        try:
            recepcionista = Recepcionista.objects.get(DNI=dni, contrasenya=contrasenya)
            response = redirect("lista_reserves")
            response.set_cookie(
                "acceso", str(recepcionista.DNI)
            )  # Establecer cookie de acceso
            return response
        except:
            mensaje = "El DNI o password son incorrectos"
            return render(request, "landing.html", {"mensaje": mensaje})

    else:
        return render(request, "landing.html")


def lista_reserves(request):
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
            except:
                mensaje_error = "El jugador no existe."
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
                # consultem que eljugador no hagi fet reservas al mateix dia
                reserva_feta = Reserva.objects.get(jugador=jugador, data=fecha2)
                mensaje_error = "El jugador ya tiene una reserva en este dia."
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
            pista = Pistes.objects.filter(tipus=type_pista)
            if pista.count() > 0:
                pista_ = random.choice(pista)
            else:
                mensaje_error = (
                    "No hay canchas disponibles del tipo "
                    + type_pista
                    + ". Por favor, contacte con el administrador."
                )
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

            # recollim recepcionista que realitza reserva a través de cookie
            rec = Recepcionista.objects.get(DNI=request.COOKIES.get("acceso"))
            # guardem reserva
            reserva = Reserva(
                jugador=jugador,
                data=fecha2,
                pista=pista_,
                horaInici=hora_inici,
                horaFinalitzacio=hora_finalitzacio,
                recepcionista=rec,
            )
            reserva.save()

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
            contrasenya = str(nom)

            # ens assegurem que id es unic i guardem jugador
            id_jugador = random.randrange(10000, 100000)
            try:
                player = Jugadors.objects.get(id_jugador=id_jugador)
                print(player)
                id_jugador = random.randrange(10000, 100000)
                jugador = Jugadors(
                    id_jugador=id_jugador,
                    nom=nom,
                    cognom=cognom,
                    email=email,
                    telefon=telefon,
                    nivell=nivell,
                    contrasenya=contrasenya,
                )
                jugador.save()
            except:
                jugador = Jugadors(
                    id_jugador=id_jugador,
                    nom=nom,
                    cognom=cognom,
                    email=email,
                    telefon=telefon,
                    nivell=nivell,
                    contrasenya=contrasenya,
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
    else:
        mensaje = "Accés denegat"
        return render(request, "landing.html", {"mensaje": mensaje})


def lista_cobraments(request, data, id_jugador):
    acceso = request.COOKIES.get("acceso")
    if acceso:
        # identificar reserva
        jugador = Jugadors.objects.get(id_jugador=id_jugador)
        reserva = Reserva.objects.get(data=data, jugador=jugador)

        totals = Cobrament.objects.filter(reserva=reserva)

        if request.method == "POST":
            if totals.count() != 4:
                jugador_nom = request.POST.get("jugador-nom")
                jugador_cognom = request.POST.get("jugador-cognom")

                try:
                    jugador = Jugadors.objects.get(
                        nom=jugador_nom, cognom=jugador_cognom
                    )
                except:
                    mensaje = "Jugador inexistente en la base de datos."
                    return render(
                        request, "lista_cobraments.html", {"mensaje": mensaje}
                    )

                try:
                    existeix_cobrament = Cobrament.objects.get(
                        reserva=reserva, jugador=jugador
                    )
                    mensaje = "El jugador ya pago esta reserva."
                    return render(
                        request, "lista_cobraments.html", {"mensaje": mensaje}
                    )

                except:
                    preu_hora = 10
                    # ---- calcul preu ----------------------------------
                    hora_inicio = datetime.strptime(
                        reserva.horaInici.strftime("%H:%M:%S"), "%H:%M:%S"
                    )
                    hora_final = datetime.strptime(
                        reserva.horaFinalitzacio.strftime("%H:%M:%S"), "%H:%M:%S"
                    )

                    diferencia_tiempo = hora_final - hora_inicio
                    diferencia_horas = int(diferencia_tiempo.total_seconds() / 3600)
                    diferencia_minutos = int(
                        (diferencia_tiempo.total_seconds() % 3600) / 60
                    )
                    diferencia_horas += round(diferencia_minutos / 60, 2)
                    importe = preu_hora * diferencia_horas

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

                    mensaje2 = (
                        jugador_nom
                        + " "
                        + jugador_cognom
                        + " ha realizado un pago de "
                        + str(importe)
                        + " $"
                    )
                    return render(
                        request, "lista_cobraments.html", {"mensaje2": mensaje2}
                    )
            else:
                mensaje = "Limite de 4 personas en la cancha."
                return render(request, "lista_cobraments.html", {"mensaje": mensaje})
        return render(request, "lista_cobraments.html")
    else:
        mensaje = "Acceso Denegado"
        return render(request, "landing.html", {"mensaje": mensaje})


def logout(request):
    response = redirect(
        "landing"
    )  # Redirige a la página de inicio de sesión o cualquier otra página después de hacer logout
    response.delete_cookie("acceso")  # Elimina la cookie 'recepcionista_id'
    return response

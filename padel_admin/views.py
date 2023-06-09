from datetime import datetime, date, time, timedelta
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
import random
from .models import Jugadors, Reserva, Cobrament, Recepcionista, Pistes, Recepcionista

def landing(request):
    if request.method == 'POST':
        dni = request.POST.get('dni')
        contrasenya = request.POST.get('contrasenya')
        
        recepcionista = Recepcionista.objects.get(DNI=dni, contrasenya=contrasenya)

        if recepcionista:
            response = redirect('lista_jugadors')
            response.set_cookie('acceso', str(recepcionista.DNI))  # Establecer cookie de acceso
            return response
        else:
            mensaje = 'El DNI o la contrasenya son incorrectes'
            return render(request, 'landing.html', {'mensaje': mensaje})

    else:
        return render(request, 'landing.html')

def lista_reserves(request):
    acceso = request.COOKIES.get('acceso')
    if acceso:
        # hores disponibles
        hora_min = time(hour=9, minute=0, second=0)
        hora_max = time(hour=21, minute=0, second=0)
        hours = []
        current_hour = hora_min
        while current_hour <= hora_max:
            hours.append(current_hour.strftime('%H:%M'))
            current_hour = (datetime.combine(datetime.min, current_hour) + timedelta(minutes=30)).time()
        
        if request.method == 'POST':
            # eliminar jugador
            if request.POST.get('_method') == 'DELETE':
                jugador_id = request.POST.get('jugador_id')
                data = request.POST.get('data')
                jugador = Jugadors.objects.get(id_jugador=jugador_id)
                reserva = Reserva.objects.get(jugador=jugador, data=data)
                reserva.delete()
                reserves = Reserva.objects.filter(data=data).order_by('horaInici', 'horaFinalitzacio','pista')
                fecha = datetime.strptime(data, '%Y-%m-%d').date()
                day = fecha.strftime('%Y-%m-%d')
                return render(request, 'lista_reserves.html', {'reserves': reserves, 'day': day, 'hours': hours})
            
            # AFEGIR RESERVA
            fecha2 = request.POST.get('fecha-2')
            hora_inici_str = request.POST.get('horaInici')
            hora_inici = datetime.strptime(hora_inici_str, '%H:%M').time()
            duracio = request.POST.get('horaFinalitzacio')
            type_pista = request.POST.get('Pista')
            jugador_nom = request.POST.get('jugador_nom')
            jugador_cognom = request.POST.get('jugador_cognom')
            # transformem duracio en hora de finalitzacio
            if duracio == '30':
                hora_finalitzacio = (datetime.combine(datetime.min, hora_inici) + timedelta(minutes=30)).time()
            elif duracio == '60':
                hora_finalitzacio = (datetime.combine(datetime.min, hora_inici) + timedelta(hours=1)).time()
            else:
                hora_finalitzacio = (datetime.combine(datetime.min, hora_inici) + timedelta(hours=1, minutes=30)).time()
            # obtenim el jugador
            jugador = Jugadors.objects.get(nom=jugador_nom, cognom=jugador_cognom)
            # consultem que eljugador no hagi fet reservas al mateix dia
            reserva_feta = Reserva.objects.get(jugador=jugador, data=fecha2)
            if reserva_feta:
                mensaje_error = "El jugador ja ha realitzat una reserva per aquest dia."
                fecha = date.today()
                day = fecha.strftime('%Y-%m-%d')
                reserves = Reserva.objects.filter(data=fecha).order_by('horaInici', 'horaFinalitzacio','pista')
                return render(request, 'lista_reserves.html', {'reserves': reserves, 'day': day, 'hours': hours, 'mensaje_error': mensaje_error})            
            # consultem les pistes ocupades i li assignem una lliure
            pista = Pistes.objects.filter(tipus=type_pista)
            if pista.count() != 50:
                if pista.count() != 0:
                    pista_disponible = False
                    while not pista_disponible:
                        pista_ = random.choice(pista)
                        # Verificar si la pista está ocupada en el momento deseado
                        reserva_existente = Reserva.objects.filter(pista=pista_, horaInici=hora_inici).exists()
                        if not reserva_existente:
                            pista_disponible = True
                else:
                    pista_ = random.choice(pista)
            else:
                mensaje_error = "Totes les pistes del tipus" + type_pista + "estan ocupades per aquesta hora"
                fecha = date.today()
                day = fecha.strftime('%Y-%m-%d')
                reserves = Reserva.objects.filter(data=fecha).order_by('horaInici', 'horaFinalitzacio','pista')
                return render(request, 'lista_reserves.html', {'reserves': reserves, 'day': day, 'hours': hours, 'mensaje_error': mensaje_error})    
            
            # recollim recepcionista que realitza reserva a través de cookie
            rec = Recepcionista.objects.get(DNI=request.COOKIES.get('acceso'))  
            # guardem reserva
            reserva = Reserva(jugador=jugador, data=fecha2 ,pista=pista_, horaInici=hora_inici, horaFinalitzacio=hora_finalitzacio, recepcionista=rec)
            reserva.save()

        fecha = request.GET.get('fecha')
        if fecha:
            fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
            reserves = Reserva.objects.filter(data=fecha).order_by('horaInici', 'horaFinalitzacio','pista')
            day = fecha.strftime('%Y-%m-%d')
        else:
            fecha = date.today()
            day = fecha.strftime('%Y-%m-%d')
            reserves = Reserva.objects.filter(data=fecha).order_by('horaInici', 'horaFinalitzacio','pista')
        return render(request, 'lista_reserves.html', {'reserves': reserves, 'day': day, 'hours': hours})
    else:
        mensaje = 'Accés denegat'
        return render(request, 'landing.html', {'mensaje': mensaje})



def lista_jugadors(request):
    acceso = request.COOKIES.get('acceso')
    if acceso:
        print(acceso)
        search_query = request.GET.get('search')
        
        if request.method == 'POST':
            if request.POST.get('_method') == 'DELETE':
                jugador_id = request.POST.get('jugador_id')
                jugador = Jugadors.objects.filter(id_jugador=jugador_id)
                jugador.delete()
                return redirect('lista_jugadors')
            
            # Procesar los datos del formulario
            nom = request.POST.get('nom')
            cognom = request.POST.get('cognom')
            email = request.POST.get('email')
            telefon = request.POST.get('telefon')
            nivell = request.POST.get('nivell')
            contrasenya = str(nom)

            jugador = Jugadors(nom=nom, cognom=cognom, email=email, telefon=telefon, nivell=nivell, contrasenya=contrasenya)
            jugador.save()
        
        jugadors_list = Jugadors.objects.all()
        
        if search_query:
            jugadors_list = jugadors_list.filter(nom__icontains=search_query) | jugadors_list.filter(cognom__icontains=search_query)
        
        paginator = Paginator(jugadors_list, 100)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'search_query': search_query,
        }
        
        return render(request, 'lista_jugadors.html', context)
    else:
        mensaje = 'Accés denegat'
        return render(request, 'landing.html', {'mensaje': mensaje})

def lista_cobraments(request):
    cobraments = Cobrament.objects.all()
    return render(request, 'lista_cobraments.html', {'cobraments': cobraments})

def logout(request):
    response = redirect('landing')  # Redirige a la página de inicio de sesión o cualquier otra página después de hacer logout
    response.delete_cookie('acceso')  # Elimina la cookie 'recepcionista_id'
    return response
from datetime import datetime
from django.shortcuts import render
from .models import Jugadors, Reserva

def landing(request):
    return render(request, 'landing.html')

def lista_reserves(request):
    fecha = request.GET.get('fecha')
    if fecha:
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
        reserves = Reserva.objects.filter(data=fecha)
    else:
        reserves = Reserva.objects.all()
    return render(request, 'lista_reserves.html', {'reserves': reserves})


def lista_jugadors(request):
    jugadors = Jugadors.objects.all()
    return render(request, 'lista_jugadors.html', {'jugadors': jugadors})
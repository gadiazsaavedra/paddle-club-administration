from django.shortcuts import render
from .models import HistoricoReserva, Jugadors, Reserva, Cobrament
from django.db.models import Sum


def estadisticas_reservas(request):
    # Jugadores que pagaron
    pagos = HistoricoReserva.objects.filter(accion="pago").select_related(
        "jugador", "reserva"
    )
    jugadores_pagaron = pagos.values_list(
        "jugador__nom", "jugador__cognom", "reserva__id"
    ).distinct()
    # Total cobrado
    total_cobrado = pagos.aggregate(total=Sum("importe"))["total"] or 0
    # Jugadores que cancelaron
    cancelaciones = HistoricoReserva.objects.filter(
        accion="cancelacion"
    ).select_related("jugador", "reserva")
    jugadores_cancelaron = cancelaciones.values_list(
        "jugador__nom", "jugador__cognom", "reserva__id"
    ).distinct()
    # Histórico completo
    historico = HistoricoReserva.objects.select_related("jugador", "reserva").order_by(
        "-fecha"
    )[:100]
    return render(
        request,
        "estadisticas_reservas.html",
        {
            "jugadores_pagaron": jugadores_pagaron,
            "total_cobrado": total_cobrado,
            "jugadores_cancelaron": jugadores_cancelaron,
            "historico": historico,
        },
    )

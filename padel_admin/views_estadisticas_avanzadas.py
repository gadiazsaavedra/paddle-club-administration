from django.shortcuts import render
from .models import (
    HistoricoReserva,
    Jugadors,
    Reserva,
    Cobrament,
    Pistes,
    ReservaRecurrente,
)
from django.db.models import Sum, Count, Q, F, Min, Max, DurationField
from django.db.models import ExpressionWrapper
from .utils import require_recepcionista


@require_recepcionista
def estadisticas_avanzadas(request):
    # 1. Ranking de jugadores más activos
    ranking_activos = (
        Reserva.objects.values("jugador__nom", "jugador__cognom")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )
    # 2. Ranking de jugadores con más cancelaciones
    ranking_cancelaciones = (
        HistoricoReserva.objects.filter(accion="cancelacion")
        .values("jugador__nom", "jugador__cognom")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )
    # 3. Porcentaje de ocupación de cada cancha
    total_dias = Reserva.objects.aggregate(min=Min("fecha"), max=Max("fecha"))
    dias = (
        (total_dias["max"] - total_dias["min"]).days + 1
        if total_dias["min"] and total_dias["max"]
        else 1
    )
    ocupacion_canchas = Pistes.objects.annotate(
        reservas=Count("reserva"), porcentaje=100 * Count("reserva") / dias
    ).values("numero", "tipo", "reservas", "porcentaje")
    # 4. Horarios/días con mayor demanda
    demanda_horarios = (
        Reserva.objects.values("hora_inicio")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )
    demanda_dias = (
        Reserva.objects.values("fecha")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )
    # 5. Ingresos por mes
    ingresos_mes = (
        HistoricoReserva.objects.filter(accion="pago")
        .annotate(mes=F("fecha__month"), anio=F("fecha__year"))
        .values("anio", "mes")
        .annotate(total=Sum("importe"))
        .order_by("-anio", "-mes")
    )
    # 6. Promedio de duración de reservas
    promedio_duracion = Reserva.objects.annotate(
        duracion=F("hora_fin") - F("hora_inicio")
    ).aggregate(
        promedio=ExpressionWrapper(
            Sum(F("hora_fin") - F("hora_inicio")) / Count("id"),
            output_field=DurationField(),
        )
    )[
        "promedio"
    ]
    # 7. Jugadores que nunca cancelaron
    jugadores_nunca_cancelaron = Jugadors.objects.exclude(
        id_jugador__in=HistoricoReserva.objects.filter(
            accion="cancelacion"
        ).values_list("jugador__id_jugador", flat=True)
    )
    # 8. Jugadores nuevos por mes
    jugadores_nuevos_mes = (
        Jugadors.objects.annotate(
            mes=F("fecha_alta__month"), anio=F("fecha_alta__year")
        )
        .values("anio", "mes")
        .annotate(total=Count("id_jugador"))
        .order_by("-anio", "-mes")
    )
    # 9. Pagos pendientes
    pagos_pendientes = Reserva.objects.annotate(pagos=Count("cobrament")).filter(
        pagos__lt=4
    )
    # 10. Comparativa uso canchas
    uso_canchas = (
        Reserva.objects.values("cancha__tipo")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    # 11. Tasa de cancelación
    total_reservas = Reserva.objects.count()
    total_cancelaciones = HistoricoReserva.objects.filter(accion="cancelacion").count()
    tasa_cancelacion = (
        (total_cancelaciones / total_reservas * 100) if total_reservas else 0
    )
    # 12. Evolución de ingresos
    ingresos_tiempo = (
        HistoricoReserva.objects.filter(accion="pago")
        .values("fecha__date")
        .annotate(total=Sum("importe"))
        .order_by("fecha__date")
    )
    # 13. Reservas recurrentes vs únicas
    total_recurrentes = ReservaRecurrente.objects.count()
    total_unicas = Reserva.objects.count() - total_recurrentes
    # 14. Jugadores con mayor gasto acumulado
    ranking_gasto = (
        HistoricoReserva.objects.filter(accion="pago")
        .values("jugador__nom", "jugador__cognom")
        .annotate(total=Sum("importe"))
        .order_by("-total")[:10]
    )
    # 15. Estadísticas por tipo de cancha
    estadisticas_tipo_cancha = (
        Reserva.objects.values("cancha__tipo")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    return render(
        request,
        "estadisticas_avanzadas.html",
        {
            "ranking_activos": ranking_activos,
            "ranking_cancelaciones": ranking_cancelaciones,
            "ocupacion_canchas": ocupacion_canchas,
            "demanda_horarios": demanda_horarios,
            "demanda_dias": demanda_dias,
            "ingresos_mes": ingresos_mes,
            "promedio_duracion": promedio_duracion,
            "jugadores_nunca_cancelaron": jugadores_nunca_cancelaron,
            "jugadores_nuevos_mes": jugadores_nuevos_mes,
            "pagos_pendientes": pagos_pendientes,
            "uso_canchas": uso_canchas,
            "tasa_cancelacion": tasa_cancelacion,
            "ingresos_tiempo": ingresos_tiempo,
            "total_recurrentes": total_recurrentes,
            "total_unicas": total_unicas,
            "ranking_gasto": ranking_gasto,
            "estadisticas_tipo_cancha": estadisticas_tipo_cancha,
        },
    )

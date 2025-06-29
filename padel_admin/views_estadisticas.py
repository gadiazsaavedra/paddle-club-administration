from django.shortcuts import render
from .models import HistoricoReserva, Jugadors, Reserva, Cobrament, Pistes
from django.db.models import Sum, Count, Q, F, Min, Max, DurationField
from datetime import datetime, timedelta
from django.db.models import ExpressionWrapper


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
    # Jugadores con devolución
    devoluciones = HistoricoReserva.objects.filter(accion="devolucion").select_related(
        "jugador", "reserva"
    )
    jugadores_devolvieron = devoluciones.values_list(
        "jugador__nom", "jugador__cognom", "reserva__id"
    ).distinct()
    # Histórico completo
    historico = HistoricoReserva.objects.select_related("jugador", "reserva").order_by(
        "-fecha"
    )[:100]

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
    from .models import ReservaRecurrente

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
    # Tabla resumen de jugadores, cobros, devoluciones, cancelaciones y cancha
    jugadores = Jugadors.objects.all().order_by("nom", "cognom")
    canchas = Pistes.objects.all().order_by("numero")
    tipos = Pistes.objects.values_list("tipo", flat=True).distinct()

    jugador_filtro = request.GET.get("jugador", "")
    cancha_filtro = request.GET.get("cancha", "")
    tipo_filtro = request.GET.get("tipo", "")

    resumen_qs = Reserva.objects.select_related("jugador", "cancha")
    if jugador_filtro:
        resumen_qs = resumen_qs.filter(jugador__id_jugador=jugador_filtro)
    if cancha_filtro:
        resumen_qs = resumen_qs.filter(cancha__numero=cancha_filtro)
    if tipo_filtro:
        resumen_qs = resumen_qs.filter(cancha__tipo=tipo_filtro)

    resumen = (
        resumen_qs.annotate(
            cobros=Count("cobrament", filter=Q(cobrament__isnull=False)),
            devoluciones=Count(
                "historicoreserva", filter=Q(historicoreserva__accion="devolucion")
            ),
            cancelaciones=Count(
                "historicoreserva", filter=Q(historicoreserva__accion="cancelacion")
            ),
        )
        .values(
            "jugador__nom",
            "jugador__cognom",
            "cancha__numero",
            "cancha__tipo",
            "cobros",
            "devoluciones",
            "cancelaciones",
        )
        .order_by("jugador__nom", "cancha__numero")
    )

    return render(
        request,
        "estadisticas_reservas.html",
        {
            "jugadores_pagaron": jugadores_pagaron,
            "total_cobrado": total_cobrado,
            "jugadores_cancelaron": jugadores_cancelaron,
            "jugadores_devolvieron": jugadores_devolvieron,
            "historico": historico,
            "resumen": resumen,
            "jugadores": jugadores,
            "canchas": canchas,
            "tipos": tipos,
            "jugador_filtro": jugador_filtro,
            "cancha_filtro": cancha_filtro,
            "tipo_filtro": tipo_filtro,
        },
    )

from functools import wraps
from django.shortcuts import get_object_or_404
from django.contrib import messages


def require_recepcionista(view_func):
    """Decorador para asegurar que hay sesión de recepcionista activa."""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        acceso = request.COOKIES.get("acceso")
        if not acceso:
            messages.error(request, "Acceso denegado: no hay sesión activa.")
            from django.shortcuts import render

            return render(request, "landing.html")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def get_jugador_or_404(id_jugador):
    from .models import Jugadors

    return get_object_or_404(Jugadors, id_jugador=id_jugador)


def get_reserva_or_404(**kwargs):
    from .models import Reserva

    return get_object_or_404(Reserva, **kwargs)


def handle_view_errors(view_func):
    """Decorador para capturar excepciones y mostrar mensajes de error amigables."""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")
            from django.shortcuts import render

            return render(request, "landing.html")

    return _wrapped_view


def validate_required_fields(request, required_fields):
    """Valida que los campos requeridos estén presentes en el request.POST."""
    missing = [name for name in required_fields if not request.POST.get(name)]
    return missing


def get_recepcionista_or_none(request):
    """Devuelve el recepcionista autenticado según la cookie, o None si no hay sesión válida."""
    from .models import Recepcionista

    acceso = request.COOKIES.get("acceso")
    if not acceso:
        return None
    try:
        return Recepcionista.objects.get(DNI=acceso)
    except Recepcionista.DoesNotExist:
        return None


def calcular_importe_reserva(reserva):
    """Calcula el importe de una reserva según la tarifa y duración."""
    from .models import Tarifa
    from decimal import Decimal, InvalidOperation
    from datetime import datetime

    tarifa = (
        Tarifa.objects.filter(
            dia_semana=reserva.fecha.weekday(),
            hora_inicio__lte=reserva.hora_inicio,
            hora_fin__gte=reserva.hora_fin,
        )
        .order_by("hora_inicio")
        .first()
    )
    if not tarifa or tarifa.precio in (None, ""):
        return Decimal("0.00")
    try:
        precio_decimal = Decimal(str(tarifa.precio).replace(" ", "").replace(",", "."))
        dt_inicio = datetime.combine(reserva.fecha, reserva.hora_inicio)
        dt_fin = datetime.combine(reserva.fecha, reserva.hora_fin)
        duracion_horas = Decimal(str((dt_fin - dt_inicio).total_seconds())) / Decimal(
            "3600"
        )
        importe = precio_decimal * duracion_horas
        if not importe.is_finite() or importe < 0:
            return Decimal("0.00")
        return importe.quantize(Decimal("0.01"))
    except (InvalidOperation, Exception):
        return Decimal("0.00")


def registrar_historico_reserva(reserva, jugador, accion, importe=None, detalles=None):
    """Registra una acción en el histórico de reservas de forma centralizada."""
    from .models import HistoricoReserva

    return HistoricoReserva.objects.create(
        reserva=reserva,
        jugador=jugador,
        accion=accion,
        importe=importe,
        detalles=detalles,
    )

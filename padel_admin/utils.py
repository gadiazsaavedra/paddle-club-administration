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

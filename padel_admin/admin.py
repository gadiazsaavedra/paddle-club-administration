from django.contrib import admin
from .models import (
    Jugadors,
    Soci,
    CobramentSoci,
    Pistes,
    Reserva,
    Cobrament,
    Recepcionista,
    ReservaRecurrente,
    Tarifa,
    HistoricoReserva,
)

# Register your models here.
admin.site.register(Jugadors)
admin.site.register(Soci)
admin.site.register(CobramentSoci)
admin.site.register(Pistes)
admin.site.register(Recepcionista)
admin.site.register(Reserva)
admin.site.register(Cobrament)
admin.site.register(Tarifa)
admin.site.register(HistoricoReserva)


@admin.register(ReservaRecurrente)
class ReservaRecurrenteAdmin(admin.ModelAdmin):
    list_display = (
        "jugador",
        "cancha",
        "dia_semana",
        "hora_inicio",
        "hora_fin",
        "fecha_inicio",
        "fecha_fin",
        "activa",
    )
    list_filter = ("cancha", "dia_semana", "activa")
    search_fields = ("jugador__nom", "jugador__cognom", "cancha__numero")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "jugador",
                    "cancha",
                    "dia_semana",
                    "hora_inicio",
                    "hora_fin",
                    "fecha_inicio",
                    "fecha_fin",
                    "notas",
                    "activa",
                )
            },
        ),
    )

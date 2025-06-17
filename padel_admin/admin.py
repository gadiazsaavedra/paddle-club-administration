from django.contrib import admin, messages
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
    Proveedor,
    Producto,
    IngresoStock,
    Venta,
    VentaDetalle,
    ConfiguracionSistema,
    MatchJuego,
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


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "contacto", "email", "telefono", "activo")
    search_fields = ("nombre", "contacto", "email", "telefono")
    list_filter = ("activo",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",  # Mostrar el código único en la lista
        "nombre",
        "categoria",
        "precio_venta",
        "stock_actual",
        "unidad_medida",
        "activo",
    )
    search_fields = ("nombre", "codigo")
    list_filter = ("categoria", "activo")


@admin.register(IngresoStock)
class IngresoStockAdmin(admin.ModelAdmin):
    list_display = ("producto", "proveedor", "fecha", "cantidad", "precio_compra")
    search_fields = ("producto__nombre", "proveedor__nombre")
    list_filter = ("producto", "proveedor", "fecha")
    date_hierarchy = "fecha"


class VentaDetalleInline(admin.TabularInline):
    model = VentaDetalle
    extra = 1


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "jugador", "total")
    search_fields = ("jugador__nom", "jugador__cognom")
    list_filter = ("fecha",)
    date_hierarchy = "fecha"
    inlines = [VentaDetalleInline]


@admin.register(VentaDetalle)
class VentaDetalleAdmin(admin.ModelAdmin):
    list_display = ("venta", "producto", "cantidad", "precio_unitario", "subtotal")
    search_fields = ("producto__nombre",)
    list_filter = ("producto",)


@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    list_display = ("matching_activo", "actualizado")
    actions = ["activar_matching", "desactivar_matching"]

    @admin.action(description="Activar matching automático")
    def activar_matching(self, request, queryset):
        queryset.update(matching_activo=True)
        self.message_user(request, "Matching activado.")

    @admin.action(description="Desactivar matching automático")
    def desactivar_matching(self, request, queryset):
        queryset.update(matching_activo=False)
        self.message_user(request, "Matching desactivado.")


@admin.register(MatchJuego)
class MatchJuegoAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "dia",
        "franja_horaria_inicio",
        "franja_horaria_fin",
        "nivel",
        "notificado",
        "fecha_creacion",
    )
    list_filter = ("notificado", "dia", "nivel")
    actions = ["notificar_jugadores"]

    def changelist_view(self, request, extra_context=None):
        pendientes = self.model.objects.filter(notificado=False).count()
        if pendientes > 0:
            messages.warning(
                request,
                f"¡Hay {pendientes} match(es) pendientes de notificación! Por favor, revisa y notifica a los jugadores.",
            )
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description="Notificar por email a los jugadores del match")
    def notificar_jugadores(self, request, queryset):
        from .models import notificar_jugadores_match

        for match in queryset.filter(notificado=False):
            notificar_jugadores_match(match)
        self.message_user(
            request, "Se notificó por email a los jugadores seleccionados."
        )

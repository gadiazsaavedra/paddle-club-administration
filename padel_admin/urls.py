from django.urls import path
from padel_admin.views_estadisticas import estadisticas_reservas
from padel_admin.views_estadisticas_avanzadas import estadisticas_avanzadas
from padel_admin import views

urlpatterns = [
    path("", views.home, name="home"),
    # ...existing url patterns...
]

urlpatterns += [
    path("estadisticas/", estadisticas_reservas, name="estadisticas_reservas"),
    path("editar-cobro/<int:id_cobro>/", views.editar_cobro, name="editar_cobro"),
    path("eliminar-cobro/<int:id_cobro>/", views.eliminar_cobro, name="eliminar_cobro"),
    path("ajax/reservar/", views.ajax_reservar_cancha, name="ajax_reservar_cancha"),
    path(
        "estadisticas_avanzadas/", estadisticas_avanzadas, name="estadisticas_avanzadas"
    ),
    path("ventas/", views.ventas_lista, name="ventas_lista"),
    path("ventas/nueva/", views.venta_nueva, name="venta_nueva"),
    path("stock/", views.stock_lista, name="stock_lista"),
    path("stock/ingreso/", views.ingreso_stock, name="ingreso_stock"),
    path("resumen-caja/", views.resumen_caja, name="resumen_caja"),
]

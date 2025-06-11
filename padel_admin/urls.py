from django.urls import path
from padel_admin.views_estadisticas import estadisticas_reservas

urlpatterns = [
    # ...existing url patterns...
]

urlpatterns += [
    path("estadisticas/", estadisticas_reservas, name="estadisticas_reservas"),
]

from django.contrib import admin
from .models import Jugadors, Soci, CobramentSoci, Pistes, Reserva, Cobrament, Recepcionista

# Register your models here.
admin.site.register(Jugadors)
admin.site.register(Soci)
admin.site.register(CobramentSoci)
admin.site.register(Pistes)
admin.site.register(Recepcionista)
admin.site.register(Reserva)
admin.site.register(Cobrament)
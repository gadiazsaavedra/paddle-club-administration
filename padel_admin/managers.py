from django.db import models
from django.db.models import Q
from datetime import date


class ReservaQuerySet(models.QuerySet):
    def pagadas(self):
        return self.filter(cobrament__isnull=False).distinct()

    def disponibles(self):
        return self.exclude(cobrament__isnull=False)

    def para_jugador(self, jugador):
        return self.filter(jugador=jugador)

    def para_fecha(self, fecha):
        return self.filter(fecha=fecha)


class CobramentQuerySet(models.QuerySet):
    def para_reserva(self, reserva):
        return self.filter(reserva=reserva)

    def para_jugador(self, jugador):
        return self.filter(jugador=jugador)

    def pagados(self):
        return self.filter(importe__gt=0)


class ReservaManager(models.Manager):
    def get_queryset(self):
        return ReservaQuerySet(self.model, using=self._db)

    def pagadas(self):
        return self.get_queryset().pagadas()

    def disponibles(self):
        return self.get_queryset().disponibles()

    def para_jugador(self, jugador):
        return self.get_queryset().para_jugador(jugador)

    def para_fecha(self, fecha):
        return self.get_queryset().para_fecha(fecha)


class CobramentManager(models.Manager):
    def get_queryset(self):
        return CobramentQuerySet(self.model, using=self._db)

    def para_reserva(self, reserva):
        return self.get_queryset().para_reserva(reserva)

    def para_jugador(self, jugador):
        return self.get_queryset().para_jugador(jugador)

    def pagados(self):
        return self.get_queryset().pagados()

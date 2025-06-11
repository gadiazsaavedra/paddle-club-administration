from django.core.management.base import BaseCommand
from padel_admin.models import Tarifa
from datetime import time


class Command(BaseCommand):
    help = "Carga tarifas de ejemplo para todos los días y franjas horarias"

    def handle(self, *args, **kwargs):
        ejemplos = (
            [
                # Lunes a Viernes, 9:00-14:00, $20
                dict(
                    dia_semana=i,
                    hora_inicio=time(9, 0),
                    hora_fin=time(14, 0),
                    precio=20,
                )
                for i in range(0, 5)
            ]
            + [
                # Lunes a Viernes, 14:00-21:00, $30
                dict(
                    dia_semana=i,
                    hora_inicio=time(14, 0),
                    hora_fin=time(21, 0),
                    precio=30,
                )
                for i in range(0, 5)
            ]
            + [
                # Sábado y Domingo, 9:00-14:00, $35
                dict(
                    dia_semana=i,
                    hora_inicio=time(9, 0),
                    hora_fin=time(14, 0),
                    precio=35,
                )
                for i in [5, 6]
            ]
            + [
                # Sábado y Domingo, 14:00-21:00, $45
                dict(
                    dia_semana=i,
                    hora_inicio=time(14, 0),
                    hora_fin=time(21, 0),
                    precio=45,
                )
                for i in [5, 6]
            ]
        )
        count = 0
        for tarifa in ejemplos:
            obj, created = Tarifa.objects.get_or_create(**tarifa)
            if created:
                count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Tarifas de ejemplo cargadas correctamente ({count} nuevas)."
            )
        )

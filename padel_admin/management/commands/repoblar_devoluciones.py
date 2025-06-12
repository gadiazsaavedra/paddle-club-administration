from django.core.management.base import BaseCommand
from padel_admin.models import Cobrament, HistoricoReserva
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "Repuebla devoluciones históricas en HistoricoReserva para todos los cobros existentes."

    def handle(self, *args, **options):
        count = 0
        for cobro in Cobrament.objects.all():
            try:
                with transaction.atomic():
                    HistoricoReserva.objects.create(
                        reserva=cobro.reserva,
                        jugador=cobro.jugador,
                        accion="devolucion",
                        importe=cobro.importe,
                        detalles="Devolución histórica repoblada",
                        fecha=timezone.now(),
                    )
                    count += 1
            except Exception as e:
                self.stderr.write(f"Error: {e}")
        self.stdout.write(self.style.SUCCESS(f"Total devoluciones repobladas: {count}"))

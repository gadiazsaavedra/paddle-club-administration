from django.core.management.base import BaseCommand
from padel_admin.models import Pistes

class Command(BaseCommand):
    help = 'Crea pistas de paddle para el sistema'

    def handle(self, *args, **kwargs):
        # Crear pistas Indoor
        for i in range(1, 6):
            Pistes.objects.get_or_create(
                numero=i,
                tipus='Indoor'
            )
            self.stdout.write(self.style.SUCCESS(f'Pista Indoor {i} creada'))
        
        # Crear pistas Outdoor
        for i in range(6, 11):
            Pistes.objects.get_or_create(
                numero=i,
                tipus='Outdoor'
            )
            self.stdout.write(self.style.SUCCESS(f'Pista Outdoor {i} creada'))
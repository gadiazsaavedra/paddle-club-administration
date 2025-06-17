from django.core.management.base import BaseCommand
from padel_admin.models import buscar_y_crear_matches


class Command(BaseCommand):
    help = "Busca coincidencias y arma grupos de 4 jugadores para partidos."

    def handle(self, *args, **options):
        buscar_y_crear_matches()
        self.stdout.write(
            self.style.SUCCESS("Búsqueda y creación de matches completada.")
        )

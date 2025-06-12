import datetime
import random
import time
from faker import Faker
from datetime import datetime, date, timedelta, time
from django.core.management.base import BaseCommand
from dateutil.relativedelta import relativedelta
from padel_admin.models import (
    Jugadors,
    Soci,
    CobramentSoci,
    Pistes,
    Reserva,
    Cobrament,
    Recepcionista,
)

JUGADORES = 500
PISTES = 50
RECEPCIONISTES = 25
RESERVAS = 10  # reservas per jugador
PRECIO_BASE = 10  # preu base per jugar 1 hora

letras = "TRWAGMYFPDXBNJZSQVHLCKE"


class Command(BaseCommand):
    help = "generador de dades"

    def handle(self, *args, **kwargs):
        fake = Faker("es_ES")

        print("Adding jugadors...")
        jugadors_bulk = []
        for i in range(JUGADORES):
            id_jugador = fake.unique.random_number(digits=5)
            nom = fake.first_name()
            cognom = fake.last_name()
            nivell = random.randint(1, 6)
            telefon = fake.numerify(text="+34 #########")
            email = fake.email()
            contrasenya = fake.password(
                length=8, upper_case=False, digits=False, special_chars=False
            )
            jugadors_bulk.append(
                Jugadors(
                    id_jugador=id_jugador,
                    nom=nom,
                    cognom=cognom,
                    nivell=nivell,
                    telefon=telefon,
                    email=email,
                    contrasenya=contrasenya,
                )
            )
        Jugadors.objects.bulk_create(jugadors_bulk)
        jugadors = list(Jugadors.objects.all())
        print(len(jugadors), "jugadors added.")

        print("Adding socis...")
        socis_bulk = []
        for i in range(JUGADORES):
            id_jugador = fake.unique.random_number(digits=5)
            nom = fake.first_name()
            cognom = fake.last_name()
            nivell = random.randint(1, 6)
            telefon = fake.numerify(text="+34 #########")
            email = fake.unique.email()
            contrasenya = fake.password(
                length=8, upper_case=False, digits=False, special_chars=False
            )
            IBAN = fake.unique.iban()
            socis_bulk.append(
                Soci(
                    id_jugador=id_jugador,
                    nom=nom,
                    cognom=cognom,
                    nivell=nivell,
                    telefon=telefon,
                    email=email,
                    contrasenya=contrasenya,
                    IBAN=IBAN,
                )
            )
        Soci.objects.bulk_create(socis_bulk)
        socis = list(Soci.objects.all())
        print(len(socis), "socis added.")

        print("Adding cobrament_socis...")
        cobrament_socis_bulk = []
        socis_list = socis
        for i in range(3):
            for soci in socis_list:
                id_cobramentSoci = fake.unique.random_number(digits=5)
                data = fake.date_between(
                    start_date=date(2022, 1, 1), end_date=date.today()
                )
                data = data.replace(day=1) + relativedelta(months=1, days=-1)
                cobrament_socis_bulk.append(
                    CobramentSoci(
                        id_cobramentSoci=id_cobramentSoci, data=data, soci=soci
                    )
                )
        CobramentSoci.objects.bulk_create(cobrament_socis_bulk)
        print(len(cobrament_socis_bulk), "cobrament_socis added.")

        print("Adding pistes...")
        pistes_bulk = []
        for i in range(PISTES):
            numero = i
            tipus = fake.random_element(elements=("outdoor", "indoor"))
            pistes_bulk.append(Pistes(numero=numero, tipus=tipus))
        Pistes.objects.bulk_create(pistes_bulk)
        pistes = list(Pistes.objects.all())
        print(len(pistes), "pistes added.")

        print("Adding recepcionistes...")
        recepcionistes_bulk = []
        for i in range(RECEPCIONISTES):
            id = str(random.randint(10000000, 99999999)) + random.choice(letras)
            nom = fake.first_name()
            cognom = fake.last_name()
            email = fake.unique.email()
            contrasenya = fake.password(
                length=8, upper_case=False, digits=False, special_chars=False
            )
            telefon = fake.numerify(text="+34 #########")
            recepcionistes_bulk.append(
                Recepcionista(
                    DNI=id,
                    nom=nom,
                    cognom=cognom,
                    telefon=telefon,
                    email=email,
                    contrasenya=contrasenya,
                )
            )
        Recepcionista.objects.bulk_create(recepcionistes_bulk)
        recepcionistes = list(Recepcionista.objects.all())
        print(len(recepcionistes), "recepcionistes added.")

        print("Adding reserves...")
        reservas_bulk = []
        jugadors_list = jugadors
        for i in range(RESERVAS):
            for jug in jugadors_list:
                jugador = jug
                fecha = fake.date_between(
                    start_date=date(2023, 1, 1), end_date=date(2023, 12, 12)
                )
                if Reserva.objects.filter(fecha=fecha, jugador=jugador).exists():
                    continue
                hora_min = time(hour=9, minute=0, second=0)
                hora_max = time(hour=21, minute=0, second=0)
                minutos_inicio = 30 * random.randint(0, 23)
                hora_inicio = (
                    datetime.combine(datetime.today(), hora_min)
                    + timedelta(minutes=minutos_inicio)
                ).time()
                minutos_final = 30 * (random.randint(0, 2) + 1)
                hora_fin = (
                    datetime.combine(datetime.today(), hora_inicio)
                    + timedelta(minutes=minutos_final)
                ).time()
                if hora_fin > hora_max:
                    hora_fin = hora_max
                canchas = pistes
                cancha = random.choice(canchas)
                reservas_en_cancha = [
                    r for r in reservas_bulk if r.cancha == cancha and r.fecha == fecha
                ]
                solapada = False
                for reserv in reservas_en_cancha:
                    if (
                        reserv.hora_inicio <= hora_inicio <= reserv.hora_fin
                        or reserv.hora_inicio <= hora_fin <= reserv.hora_fin
                    ):
                        solapada = True
                        break
                if solapada:
                    continue
                recepcionista = random.choice(recepcionistes)
                reservas_bulk.append(
                    Reserva(
                        jugador=jugador,
                        fecha=fecha,
                        cancha=cancha,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        recepcionista=recepcionista,
                    )
                )
        Reserva.objects.bulk_create(reservas_bulk)
        print(len(reservas_bulk), "reserves added.")

        print("FAKE DATA CREATED")

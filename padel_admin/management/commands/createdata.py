import datetime
import random
import time
from faker import Faker
from datetime import datetime, date, timedelta, time
from django.core.management.base import BaseCommand
from padel_admin.models import Jugadors, Soci, CobramentSoci, Pistes, Reserva, Cobrament, Recepcionista

JUGADORES = 300
PISTES = 50
RECEPCIONISTES = 25
RESERVAS = 5 #reservas per jugador

letras = 'TRWAGMYFPDXBNJZSQVHLCKE'

class Command(BaseCommand):
  help = "generador de dades"

  def handle(self, *args, **kwargs):
    fake = Faker('es_ES')
    
    print("adding jugadors")
    # jugadors creation
    for i in range(JUGADORES):
       id_jugador = fake.unique.random_number(digits=5)
       nom = fake.first_name()
       cognom = fake.last_name()
       nivell = random.randint(1,6)
       telefon = fake.phone_number()
       email = fake.email()
       contrasenya = fake.password(length=8, upper_case=False, digits=False, special_chars=False)
       Jugadors.objects.create(
        id_jugador=id_jugador,
        nom=nom,
        cognom=cognom,
        nivell=nivell,
        telefon=telefon,
        email=email,
        contrasenya=contrasenya)
    jugadors = Jugadors.objects.all()
    print(jugadors.count(), "jugadors added.")

    print("adding socis")
    # socis creation
    for i in range(JUGADORES):
       id_jugador = fake.unique.random_number(digits=5)
       nom = fake.first_name()
       cognom = fake.last_name()
       nivell = random.randint(1,6)
       telefon = fake.phone_number()
       email = fake.unique.email()
       contrasenya = fake.password(length=8, upper_case=False, digits=False, special_chars=False)
       IBAN = fake.unique.iban()
       Soci.objects.create(
        id_jugador=id_jugador,
        nom=nom,
        cognom=cognom,
        nivell=nivell,
        telefon=telefon,
        email=email,
        contrasenya=contrasenya,
        IBAN=IBAN)
    socis = Soci.objects.all()
    print(socis.count(), "socis added.")

    print("adding conbrament_socis")
    # cobrament_socis creation
    socis_list = Soci.objects.all()
    for soci in socis_list:
       id_cobramentSoci = fake.unique.random_number(digits=5)
       # generate last day of the month
       data = fake.date_between(start_date=date(2022, 1, 1), end_date=date.today())
       soci = soci
       CobramentSoci.objects.create(
        id_cobramentSoci=id_cobramentSoci,
        data=data,
        soci=soci)
    cobrasocis = CobramentSoci.objects.all()
    print(cobrasocis.count(), "cobrament_socis added.")

    print("adding pistes")
    # pistes creation
    for i in range(PISTES):
       numero = i
       tipus = fake.random_element(elements=('outdoor', 'indoor'))
       Pistes.objects.create(
        numero=numero,
        tipus=tipus)
    pistes = Pistes.objects.all()
    print(pistes.count(), "pistes added.")

    print("adding recepcionistes")
    # recepcionistes creation
    for i in range(RECEPCIONISTES):
       id = random.randint(10000000,99999999)
       id = str(id) + random.choice(letras)
       nom = fake.first_name()
       cognom = fake.last_name()
       email = fake.unique.email()
       contrasenya = fake.password(length=8, upper_case=False, digits=False, special_chars=False)
       telefon = fake.phone_number()
       Recepcionista.objects.create(
        DNI=id,
        nom=nom,
        cognom=cognom,
        telefon=telefon,
        email=email,
        contrasenya=contrasenya)
    recepcionistes = Recepcionista.objects.all()
    print(recepcionistes.count(), "recepcionistes added.")

    print("adding reserves")
    # reserves creation
    jugadors_list = Jugadors.objects.all()
    for i in range(RESERVAS):
       for j in jugadors_list:
          jugador = j
          data = fake.date_between(start_date=date(2022, 1, 1), end_date=date.today())
          pista = random.choice(pistes)
          # ----------- hores -----------
          hora_min = time(hour=9, minute=0, second=0)
          hora_max = time(hour=21, minute=0, second=0)
          # Generamos una hora de inicio aleatoria
          minutos_inici = 30 * random.randint(0, 23)  # generamos un múltiplo de 30 entre 0 y 23
          horaInici = (datetime.combine(datetime.today(), hora_min) + timedelta(minutes=minutos_inici)).time()
          # Generamos una duración aleatoria para el turno
          minutos_final = 30 * (random.randint(0, 2) + 1)
          horaFinalitzacio = (datetime.combine(datetime.today(), horaInici) + timedelta(minutes=minutos_final)).time()
          # Si la hora de finalización es mayor que las 21:00, la ajustamos
          if horaFinalitzacio > hora_max:
             horaFinalitzacio = hora_max
          # -----------------------------
          recepcionista = random.choice(recepcionistes)
       Reserva.objects.create(
        jugador=jugador,
        data=data,
        pista=pista,
        horaInici=horaInici,
        horaFinalitzacio=horaFinalitzacio,
        recepcionista=recepcionista)
    reserves = Reserva.objects.all()
    print(reserves.count(), "reserves added.")

    print("adding cobrament")
    # recepcionistes creation
    for i in range(RECEPCIONISTES):
       id = random.randint(10000000,99999999)
       id = str(id) + random.choice(letras)
       nom = fake.first_name()
       cognom = fake.last_name()
       email = fake.unique.email()
       contrasenya = fake.password(length=8, upper_case=False, digits=False, special_chars=False)
       telefon = fake.phone_number()
       Recepcionista.objects.create(
        DNI=id,
        nom=nom,
        cognom=cognom,
        telefon=telefon,
        email=email,
        contrasenya=contrasenya)
    recepcionistes = Recepcionista.objects.all()
    print(recepcionistes.count(), "recepcionistes added.")

    print("FAKE DATA CREATED")
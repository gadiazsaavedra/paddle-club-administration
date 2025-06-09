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
        # jugadors creation
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
            Jugadors.objects.create(
                id_jugador=id_jugador,
                nom=nom,
                cognom=cognom,
                nivell=nivell,
                telefon=telefon,
                email=email,
                contrasenya=contrasenya,
            )
        jugadors = Jugadors.objects.all()
        print(jugadors.count(), "jugadors added.")

        print("Adding socis...")
        # socis creation
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
            Soci.objects.create(
                id_jugador=id_jugador,
                nom=nom,
                cognom=cognom,
                nivell=nivell,
                telefon=telefon,
                email=email,
                contrasenya=contrasenya,
                IBAN=IBAN,
            )
        socis = Soci.objects.all()
        print(socis.count(), "socis added.")

        print("Adding cobrament_socis...")
        # cobrament_socis creation
        socis_list = Soci.objects.all()
        # generem 3 cobraments_soci per soci
        for i in range(3):
            for soci in socis_list:
                id_cobramentSoci = fake.unique.random_number(digits=5)
                # generate last day of the month
                data = fake.date_between(
                    start_date=date(2022, 1, 1), end_date=date.today()
                )
                data = data.replace(day=1) + relativedelta(months=1, days=-1)
                soci = soci
                CobramentSoci.objects.create(
                    id_cobramentSoci=id_cobramentSoci, data=data, soci=soci
                )
            cobrasocis = CobramentSoci.objects.all()
        print(cobrasocis.count(), "cobrament_socis added.")

        print("Adding pistes...")
        # pistes creation
        for i in range(PISTES):
            numero = i
            tipus = fake.random_element(elements=("outdoor", "indoor"))
            Pistes.objects.create(numero=numero, tipus=tipus)
        pistes = Pistes.objects.all()
        print(pistes.count(), "pistes added.")

        print("Adding recepcionistes...")
        # recepcionistes creation
        for i in range(RECEPCIONISTES):
            id = random.randint(10000000, 99999999)
            id = str(id) + random.choice(letras)
            nom = fake.first_name()
            cognom = fake.last_name()
            email = fake.unique.email()
            contrasenya = fake.password(
                length=8, upper_case=False, digits=False, special_chars=False
            )
            telefon = fake.numerify(text="+34 #########")
            Recepcionista.objects.create(
                DNI=id,
                nom=nom,
                cognom=cognom,
                telefon=telefon,
                email=email,
                contrasenya=contrasenya,
            )
        recepcionistes = Recepcionista.objects.all()
        print(recepcionistes.count(), "recepcionistes added.")

        print("Adding reserves...")
        # reserves creation
        jugadors_list = Jugadors.objects.all()
        for i in range(RESERVAS):
            for jug in jugadors_list:
                jugador = jug
                fecha = fake.date_between(
                    start_date=date(2023, 1, 1), end_date=date(2023, 12, 12)
                )
                exist_reserva = Reserva.objects.filter(fecha=fecha, jugador=jug)
                if exist_reserva:
                    continue
                # ----------- hores -----------
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
                canchas = list(pistes)
                cancha = random.choice(canchas)
                reserves = Reserva.objects.filter(cancha=cancha, fecha=fecha)
                for reserv in reserves:
                    if (
                        reserv.hora_inicio <= hora_inicio <= reserv.hora_fin
                        or reserv.hora_inicio <= hora_fin <= reserv.hora_fin
                    ):
                        cancha = random.choice(canchas)
                recepcionista = random.choice(recepcionistes)
                Reserva.objects.create(
                    jugador=jugador,
                    fecha=fecha,
                    cancha=cancha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    recepcionista=recepcionista,
                )
        reserves = Reserva.objects.all()
        print(reserves.count(), "reserves added.")

        """print("Adding cobraments...")
      # cobraments creation
      for res in reserves:
         jugen = [2,4]
         for i in range(random.choice(jugen)):
            reserva = res
            cobraments_totals = Cobrament.objects.filter(reserva=res)
            if (cobraments_totals.count() >= 4):
               continue
            quiReserva = Cobrament.objects.filter(jugador=res.jugador, reserva=res)
            if (quiReserva):
               jugador = random.choice(jugadors)
               # comprovem que aquest jugador no esta associat a una reserva a la mateixa data
               existeix = Cobrament.objects.filter(jugador=jugador, data=res.fecha)
               while existeix:
                  jugador = random.choice(jugadors)
                  existeix = Cobrament.objects.filter(jugador=jugador, data=res.fecha) 
            else:
               jugador = res.jugador
               # comprovacio jugador no te una reserva que coincideixi en hores
               cobraments = Cobrament.objects.filter(jugador=res.jugador)
               sortir = False
               for single in cobraments:
                  res2 = single.reserva
                  if (res2.fecha == res.fecha and (res2.hora_inicio <= res.hora_inicio <= res2.hora_fin or res2.hora_inicio <= res.hora_fin <= res2.hora_fin)):
                     sortir = True
                     break
               if (sortir == True):
                  continue
            data = res.fecha
            # ---- calcul preu ----------------------------------           
            hora_inicio = datetime.strptime(res.hora_inicio.strftime("%H:%M:%S"), "%H:%M:%S")
            hora_final = datetime.strptime(res.hora_fin.strftime("%H:%M:%S"), "%H:%M:%S")

            es_soci = Soci.objects.filter(id_jugador=res.jugador.id_jugador)
            # comprovem que si es soci, i la reserva es abans de les 13 i es entre dilluns i divendres
            if es_soci and hora_inicio.hour < 13 and (res.fecha.weekday() >= 0 and res.fecha.weekday() <= 4):
               importe = 0
            else:
               diferencia_tiempo = hora_final - hora_inicio
               diferencia_horas = int(diferencia_tiempo.total_seconds() / 3600)
               diferencia_minutos = int((diferencia_tiempo.total_seconds() % 3600) / 60)
               diferencia_horas += round(diferencia_minutos / 60, 2)
               if es_soci:
                  importe = (PRECIO_BASE*diferencia_horas)/2
               else:
                  importe = PRECIO_BASE*diferencia_horas
            
            recepcionista = random.choice(recepcionistes)
            Cobrament.objects.create(
               reserva=reserva,
               jugador=jugador,
               data=data,
               importe=importe,
               recepcionista=recepcionista)
      cobraments = Cobrament.objects.all()
      print(cobraments.count(), "cobraments added.")"""

        print("FAKE DATA CREATED")

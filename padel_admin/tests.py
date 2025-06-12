from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from datetime import datetime, timedelta, time, date
from decimal import Decimal
from .models import Jugadors, Recepcionista, Pistes, Tarifa, Reserva, Cobrament
from .services import ReservaService, CobroService


class ReservaCobroFlowTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.recepcionista = Recepcionista.objects.create(
            DNI="12345678A", nom="Recep", cognom="Test", contrasenya="pass"
        )
        self.jugador = Jugadors.objects.create(
            id_jugador=11111,
            nom="Juan",
            cognom="Pérez",
            email="jp@test.com",
            telefon="123456789",
            nivell=2,
            contrasenya="jperez",
        )
        self.pista = Pistes.objects.create(numero=1, tipo="Padel")
        self.fecha = date.today() + timedelta(days=1)
        self.hora_inicio = time(10, 0)
        self.hora_fin = time(11, 0)
        self.tarifa = Tarifa.objects.create(
            dia_semana=self.fecha.weekday(),
            hora_inicio=self.hora_inicio,
            hora_fin=self.hora_fin,
            precio=Decimal("20.00"),
        )
        self.request = self.factory.post("/fake-url/")
        self.request.COOKIES = {"acceso": str(self.recepcionista.DNI)}
        self.request.user = AnonymousUser()

    def test_flujo_reserva_cobro(self):
        # Crear reserva
        datos = {
            "jugador_nom": self.jugador.nom,
            "jugador_cognom": self.jugador.cognom,
            "fecha": self.fecha.strftime("%Y-%m-%d"),
            "hora_inicio_str": self.hora_inicio.strftime("%H:%M"),
            "duracion": "60",
            "type_cancha": self.pista.tipo,
            "cancha_numero": str(self.pista.numero),
        }
        reserva, error = ReservaService.crear_reserva(
            **datos, request=self.request, recepcionista_required=True
        )
        self.assertIsNotNone(reserva)
        self.assertIsNone(error)
        # Duplicidad: no debe permitir doble reserva igual
        reserva2, error2 = ReservaService.crear_reserva(
            **datos, request=self.request, recepcionista_required=True
        )
        self.assertIsNone(reserva2)
        self.assertIsNotNone(error2)
        # Cobro
        cobrament, importe, error = CobroService.registrar_cobro(
            reserva, self.jugador, self.fecha, self.request
        )
        self.assertIsNotNone(cobrament)
        self.assertEqual(importe, Decimal("20.00"))
        self.assertIsNone(error)
        # Duplicidad de cobro
        cobrament2, importe2, error2 = CobroService.registrar_cobro(
            reserva, self.jugador, self.fecha, self.request
        )
        self.assertIsNone(cobrament2)
        self.assertIsNotNone(error2)
        # Editar cobro
        cobrament_editado, error_edit = CobroService.editar_cobro(
            cobrament, "25.00", self.request
        )
        self.assertIsNotNone(cobrament_editado)
        self.assertIsNone(error_edit)
        self.assertEqual(cobrament_editado.importe, Decimal("25.00"))
        # Eliminar cobro
        ok, error_del = CobroService.eliminar_cobro(cobrament_editado, self.request)
        self.assertTrue(ok)
        self.assertIsNone(error_del)
        # Cancelar reserva y verificar devolución
        reserva.delete()
        self.assertFalse(Reserva.objects.filter(id=reserva.id).exists())
        # Si hubiera cobros, deberían eliminarse y registrarse en histórico (no se testea histórico aquí por simplicidad)


class JugadorAltaDuplicadoTest(TestCase):
    def setUp(self):
        self.jugador_data = dict(
            id_jugador=22222,
            nom="Ana",
            cognom="García",
            email="ana@test.com",
            telefon="987654321",
            nivell=1,
            contrasenya="anagarcia",
        )

    def test_alta_jugador_y_duplicado(self):
        Jugadors.objects.create(**self.jugador_data)
        self.assertEqual(Jugadors.objects.count(), 1)
        # Intentar crear duplicado y capturar IntegrityError sin romper la transacción
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Jugadors.objects.create(**self.jugador_data)
        self.assertEqual(Jugadors.objects.count(), 1)


class ReservaSolapamientoTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.recepcionista = Recepcionista.objects.create(
            DNI="99999999Z", nom="Rec", cognom="Solap", contrasenya="pass"
        )
        self.jugador = Jugadors.objects.create(
            id_jugador=33333,
            nom="Luis",
            cognom="Solapado",
            email="luis@test.com",
            telefon="111222333",
            nivell=2,
            contrasenya="luispass",
        )
        self.pista = Pistes.objects.create(numero=2, tipo="Padel")
        self.fecha = date.today() + timedelta(days=2)
        self.hora_inicio = time(12, 0)
        self.request = self.factory.post("/fake-url/")
        self.request.COOKIES = {"acceso": str(self.recepcionista.DNI)}
        self.request.user = AnonymousUser()
        Tarifa.objects.create(
            dia_semana=self.fecha.weekday(),
            hora_inicio=self.hora_inicio,
            hora_fin=time(13, 0),
            precio=Decimal("15.00"),
        )

    def test_reserva_solapada(self):
        datos = {
            "jugador_nom": self.jugador.nom,
            "jugador_cognom": self.jugador.cognom,
            "fecha": self.fecha.strftime("%Y-%m-%d"),
            "hora_inicio_str": self.hora_inicio.strftime("%H:%M"),
            "duracion": "60",
            "type_cancha": self.pista.tipo,
            "cancha_numero": str(self.pista.numero),
        }
        reserva, error = ReservaService.crear_reserva(
            **datos, request=self.request, recepcionista_required=True
        )
        self.assertIsNotNone(reserva)
        self.assertIsNone(error)
        # Intentar solapamiento (misma pista y horario)
        reserva2, error2 = ReservaService.crear_reserva(
            **datos, request=self.request, recepcionista_required=True
        )
        self.assertIsNone(reserva2)
        self.assertIn("cancha ya está reservada", error2)


class CobroMaximoTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.recepcionista = Recepcionista.objects.create(
            DNI="88888888Y", nom="Rec", cognom="Cobro", contrasenya="pass"
        )
        self.pista = Pistes.objects.create(numero=3, tipo="Padel")
        self.fecha = date.today() + timedelta(days=3)
        self.hora_inicio = time(14, 0)
        self.tarifa = Tarifa.objects.create(
            dia_semana=self.fecha.weekday(),
            hora_inicio=self.hora_inicio,
            hora_fin=time(15, 0),
            precio=Decimal("10.00"),
        )
        self.request = self.factory.post("/fake-url/")
        self.request.COOKIES = {"acceso": str(self.recepcionista.DNI)}
        self.request.user = AnonymousUser()
        self.jugadores = [
            Jugadors.objects.create(
                id_jugador=40000 + i,
                nom=f"J{i}",
                cognom="Cobro",
                email=f"j{i}@test.com",
                telefon=f"1000{i}",
                nivell=1,
                contrasenya=f"j{i}",
            )
            for i in range(5)
        ]
        datos = {
            "jugador_nom": self.jugadores[0].nom,
            "jugador_cognom": self.jugadores[0].cognom,
            "fecha": self.fecha.strftime("%Y-%m-%d"),
            "hora_inicio_str": self.hora_inicio.strftime("%H:%M"),
            "duracion": "60",
            "type_cancha": self.pista.tipo,
            "cancha_numero": str(self.pista.numero),
        }
        self.reserva, _ = ReservaService.crear_reserva(
            **datos, request=self.request, recepcionista_required=True
        )

    def test_cobro_maximo_4(self):
        for i in range(4):
            cobrament, importe, error = CobroService.registrar_cobro(
                self.reserva, self.jugadores[i], self.fecha, self.request
            )
            self.assertIsNotNone(cobrament)
            self.assertIsNone(error)
        # 5º cobro debe fallar
        cobrament5, importe5, error5 = CobroService.registrar_cobro(
            self.reserva, self.jugadores[4], self.fecha, self.request
        )
        self.assertIsNone(cobrament5)
        self.assertIn("Limite de 4", error5)

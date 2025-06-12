from django.test import TestCase, RequestFactory, Client, override_settings
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
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


class OptimizedViewsTestCase(TestCase):
    def setUp(self):
        # Crear datos mínimos: 2 canchas, 2 jugadores, 2 reservas en la misma semana
        self.cancha1 = Pistes.objects.create(numero=1, tipo="indoor")
        self.cancha2 = Pistes.objects.create(numero=2, tipo="outdoor")
        self.jugador1 = Jugadors.objects.create(
            id_jugador=10001,
            nom="Ana",
            cognom="López",
            email="ana@test.com",
            telefon="123",
            nivell="A",
            contrasenya="ana",
        )
        self.jugador2 = Jugadors.objects.create(
            id_jugador=10002,
            nom="Luis",
            cognom="Pérez",
            email="luis@test.com",
            telefon="456",
            nivell="B",
            contrasenya="luis",
        )
        fecha = datetime.now().date()
        self.reserva1 = Reserva.objects.create(
            jugador=self.jugador1,
            cancha=self.cancha1,
            fecha=fecha,
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
        )
        self.reserva2 = Reserva.objects.create(
            jugador=self.jugador2,
            cancha=self.cancha2,
            fecha=fecha,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
        )

    def test_calendario_canchas_query_count(self):
        """Verifica que la vista calendario_canchas no genera N+1 queries y responde correctamente."""
        client = self.client
        url = reverse("calendario_canchas")
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(url)
        # Esperamos un número bajo de queries (canchas, reservas, cobros, etc.)
        self.assertLessEqual(
            len(ctx.captured_queries),
            6,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana")
        self.assertContains(response, "Luis")


from contextlib import contextmanager
from django.db import connection


@contextmanager
def assertNumQueriesLessThan(num):
    initial = len(connection.queries)
    yield
    final = len(connection.queries)
    executed = final - initial
    assert (
        executed < num
    ), f"Se ejecutaron {executed} queries, se esperaban menos de {num}."


class CalendarioCanchasQueryTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Crear 3 canchas
        for i in range(1, 4):
            Pistes.objects.create(numero=i, tipo="padel")
        # Crear 2 jugadores
        j1 = Jugadors.objects.create(
            id_jugador=10001,
            nom="Ana",
            cognom="Lopez",
            email="ana@x.com",
            telefon="123",
            nivell=1,
            contrasenya="a",
        )
        j2 = Jugadors.objects.create(
            id_jugador=10002,
            nom="Luis",
            cognom="Perez",
            email="luis@x.com",
            telefon="456",
            nivell=2,
            contrasenya="b",
        )
        # Crear reservas para la semana
        base_date = date.today() - timedelta(days=date.today().weekday())
        for d in range(7):
            f = base_date + timedelta(days=d)
            Reserva.objects.create(
                jugador=j1,
                cancha=Pistes.objects.get(numero=1),
                fecha=f,
                hora_inicio=time(9, 0),
                hora_fin=time(10, 0),
            )
            Reserva.objects.create(
                jugador=j2,
                cancha=Pistes.objects.get(numero=2),
                fecha=f,
                hora_inicio=time(10, 0),
                hora_fin=time(11, 0),
            )

    def test_calendario_canchas_query_count(self):
        client = Client()
        url = reverse("calendario_canchas")
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = client.get(url)
        self.assertLessEqual(
            len(ctx.captured_queries),
            6,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana")
        self.assertContains(response, "Luis")

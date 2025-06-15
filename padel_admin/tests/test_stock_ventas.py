from django.test import TestCase
from padel_admin.models import (
    Producto,
    Proveedor,
    IngresoStock,
    Venta,
    VentaDetalle,
    Jugadors,
)
from django.urls import reverse
from django.contrib.auth.models import User


class StockVentasTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="admin123")
        self.jugador = Jugadors.objects.create(
            id_jugador="J1",
            nom="Juan",
            cognom="Pérez",
            nivell=3,
            telefon="123",
            email="juan@test.com",
            contrasenya="1234",
        )
        self.proveedor = Proveedor.objects.create(nombre="Proveedor1")
        self.producto = Producto.objects.create(
            nombre="Agua",
            categoria="bebida",
            precio_venta=100,
            stock_actual=0,
            unidad_medida="botella",
        )

    def test_ingreso_stock(self):
        self.client.login(username="admin", password="admin123")
        response = self.client.post(
            reverse("ingreso_stock"),
            {
                "producto": self.producto.id,
                "proveedor": self.proveedor.id,
                "cantidad": 10,
                "precio_compra": 50,
            },
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 10)
        self.assertRedirects(response, reverse("stock_lista"))

    def test_venta_con_stock_suficiente(self):
        # Primero ingreso stock
        IngresoStock.objects.create(
            producto=self.producto,
            proveedor=self.proveedor,
            cantidad=5,
            precio_compra=50,
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 5)
        self.client.login(username="admin", password="admin123")
        response = self.client.post(
            reverse("venta_nueva"),
            {
                "form-0-producto": self.producto.id,
                "form-0-cantidad": 3,
                "form-0-precio_unitario": 100,
                "form-TOTAL_FORMS": 1,
                "form-INITIAL_FORMS": 0,
                "jugador": self.jugador.id_jugador,
            },
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 2)

    def test_venta_con_stock_insuficiente(self):
        self.client.login(username="admin", password="admin123")
        response = self.client.post(
            reverse("venta_nueva"),
            {
                "form-0-producto": self.producto.id,
                "form-0-cantidad": 10,
                "form-0-precio_unitario": 100,
                "form-TOTAL_FORMS": 1,
                "form-INITIAL_FORMS": 0,
                "jugador": self.jugador.id_jugador,
            },
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 0)
        self.assertContains(response, "Stock insuficiente", status_code=200)

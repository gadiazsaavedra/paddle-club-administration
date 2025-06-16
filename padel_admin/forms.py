from django import forms
from .models import Proveedor, Producto, IngresoStock, Venta, VentaDetalle


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = "__all__"


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = "__all__"


class IngresoStockForm(forms.ModelForm):
    class Meta:
        model = IngresoStock
        fields = "__all__"


class VentaDetalleForm(forms.ModelForm):
    class Meta:
        model = VentaDetalle
        fields = ["producto", "cantidad", "precio_unitario"]


class VentaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["jugador"].label_from_instance = (
            lambda obj: f"{obj.nom} {obj.cognom}".strip()
        )

    class Meta:
        model = Venta
        fields = ["jugador"]

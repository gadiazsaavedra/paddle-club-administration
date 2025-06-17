from django import forms
from .models import (
    Proveedor,
    Producto,
    IngresoStock,
    Venta,
    VentaDetalle,
    DisponibilidadJugador,
    Jugadors,
)
import string
import random


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


class DisponibilidadJugadorForm(forms.ModelForm):
    dias_disponibles = forms.MultipleChoiceField(
        choices=DisponibilidadJugador.DIAS_SEMANA,
        widget=forms.CheckboxSelectMultiple,
        label="Días disponibles",
    )

    class Meta:
        model = DisponibilidadJugador
        fields = [
            "dias_disponibles",
            "franja_horaria_inicio",
            "franja_horaria_fin",
            "busca_con",
            "nivel",
            "disponible",
        ]
        widgets = {
            "franja_horaria_inicio": forms.TimeInput(
                format="%H:%M", attrs={"type": "time"}
            ),
            "franja_horaria_fin": forms.TimeInput(
                format="%H:%M", attrs={"type": "time"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si la instancia tiene dias_disponibles como lista, setear initial
        if self.instance and self.instance.pk and self.instance.dias_disponibles:
            self.initial["dias_disponibles"] = self.instance.dias_disponibles

    def clean_dias_disponibles(self):
        # Guardar como lista en el modelo (JSONField)
        return self.cleaned_data["dias_disponibles"]


class JugadorLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    contrasenya = forms.CharField(label="Contraseña", widget=forms.PasswordInput)


class JugadorRegistroForm(forms.ModelForm):
    contrasenya = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if Jugadors.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe un jugador con ese email.")
        return email

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Generar un ID único automáticamente
        if not instance.id_jugador:
            while True:
                nuevo_id = "".join(
                    random.choices(string.ascii_uppercase + string.digits, k=8)
                )
                if not Jugadors.objects.filter(id_jugador=nuevo_id).exists():
                    instance.id_jugador = nuevo_id
                    break
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Jugadors
        fields = [
            "nom",
            "cognom",
            "email",
            "telefon",
            "contrasenya",
            "nivell",
        ]
        labels = {
            "nom": "Nombre",
            "cognom": "Apellido",
            "email": "Email",
            "telefon": "Teléfono",
            "nivell": "Nivel",
        }

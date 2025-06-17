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
    HORAS_INICIO = [
        "06:00",
        "07:00",
        "08:00",
        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00",
        "17:00",
        "18:00",
        "19:00",
        "20:00",
        "21:00",
        "22:00",
        "23:00",
    ]
    HORAS_FIN = [
        "07:00",
        "08:00",
        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00",
        "17:00",
        "18:00",
        "19:00",
        "20:00",
        "21:00",
        "22:00",
        "23:00",
        "23:59",
    ]
    # Creamos campos para cada día de la semana
    for dia, label in DisponibilidadJugador.DIAS_SEMANA:
        locals()[f"{dia}_inicio"] = forms.TimeField(
            required=False,
            label=f"{label} desde",
            widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        )
        locals()[f"{dia}_fin"] = forms.TimeField(
            required=False,
            label=f"{label} hasta",
            widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        )
    busca_con = forms.ChoiceField(
        choices=DisponibilidadJugador.BUSCA_CON,
        label="Busco jugar con",
        required=True,
    )
    nivel = forms.ChoiceField(
        choices=DisponibilidadJugador.NIVELES, label="Nivel", required=True
    )
    disponible = forms.BooleanField(label="Disponible", required=False)

    days_fields = [
        {
            "dia": dia,
            "label": label,
            "inicio_field": f"{dia}_inicio",
            "fin_field": f"{dia}_fin",
        }
        for dia, label in DisponibilidadJugador.DIAS_SEMANA
    ]

    class Meta:
        model = DisponibilidadJugador
        fields = ["busca_con", "nivel", "disponible"]

    @property
    def dias_widgets(self):
        """Devuelve una lista de dicts con label, widget de inicio y widget de fin para cada día."""
        return [
            {
                "label": label,
                "inicio": self[f"{dia}_inicio"],
                "fin": self[f"{dia}_fin"],
            }
            for dia, label in self.instance.DIAS_SEMANA
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si hay instancia, rellenar los campos de hora por día
        if self.instance and self.instance.dias_disponibles:
            for d in self.instance.dias_disponibles:
                dia = d.get("dia")
                if dia:
                    self.fields[f"{dia}_inicio"].initial = d.get("inicio")
                    self.fields[f"{dia}_fin"].initial = d.get("fin")

    def clean(self):
        cleaned = super().clean()
        dias = []
        for dia, _ in DisponibilidadJugador.DIAS_SEMANA:
            inicio = cleaned.get(f"{dia}_inicio")
            fin = cleaned.get(f"{dia}_fin")
            if inicio and fin:
                if fin <= inicio:
                    self.add_error(
                        f"{dia}_fin", "La hora de fin debe ser mayor a la de inicio."
                    )
                else:
                    dias.append(
                        {
                            "dia": dia,
                            "inicio": inicio.strftime("%H:%M"),
                            "fin": fin.strftime("%H:%M"),
                        }
                    )
        cleaned["dias_disponibles"] = dias
        return cleaned

    def save(self, commit=True):
        self.instance.dias_disponibles = self.cleaned_data["dias_disponibles"]
        self.instance.busca_con = self.cleaned_data["busca_con"]
        self.instance.nivel = self.cleaned_data["nivel"]
        self.instance.disponible = self.cleaned_data["disponible"]
        return super().save(commit=commit)


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

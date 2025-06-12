from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction
from datetime import timedelta, date


class Jugadors(models.Model):
    id_jugador = models.CharField(primary_key=True, max_length=10)
    nom = models.CharField(max_length=30)
    cognom = models.CharField(max_length=30)
    nivell = models.IntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    telefon = models.CharField(max_length=13)
    email = models.EmailField(max_length=50)
    contrasenya = models.CharField(max_length=30)
    foto = models.ImageField(upload_to="fotos_jugadores/", blank=True, null=True)

    def __str__(self):
        return "{} , {} , {} , {} , {}, {}, {}".format(
            self.id_jugador,
            self.nom,
            self.cognom,
            self.nivell,
            self.telefon,
            self.email,
            self.contrasenya,
        )


class Soci(Jugadors):
    IBAN = models.CharField(max_length=34)

    def __str__(self):
        return "{} , {} , {} , {} , {}, {}, {}, {}".format(
            self.id_jugador,
            self.nom,
            self.cognom,
            self.nivell,
            self.telefon,
            self.email,
            self.contrasenya,
            self.IBAN,
        )


class CobramentSoci(models.Model):
    id_cobramentSoci = models.AutoField(primary_key=True)
    data = models.DateField()
    soci = models.ForeignKey(Soci, on_delete=models.CASCADE)

    def __str__(self):
        return "{} , {}, {}".format(self.id_cobraSoci, self.data, self.soci)


class Pistes(models.Model):
    numero = models.IntegerField(primary_key=True)
    tipo = models.CharField(max_length=20)  # Indoor/Outdoor o Techada/Al aire libre
    disponible = models.BooleanField(
        default=True
    )  # Para marcar si está en mantenimiento

    def __str__(self):
        return f"Cancha {self.numero} ({self.tipo})"


class Recepcionista(models.Model):
    DNI = models.CharField(primary_key=True, max_length=9)
    nom = models.CharField(max_length=30)
    cognom = models.CharField(max_length=30)
    email = models.EmailField(max_length=50)
    contrasenya = models.CharField(max_length=30)
    telefon = models.CharField(max_length=13)

    def __str__(self):
        return "{} , {} , {} , {} , {}, {}".format(
            self.DNI, self.nom, self.cognom, self.email, self.contrasenya, self.telefon
        )


class Reserva(models.Model):
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    fecha = models.DateField()
    cancha = models.ForeignKey(Pistes, on_delete=models.CASCADE)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    recepcionista = models.ForeignKey(
        Recepcionista, on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        unique_together = ("cancha", "fecha", "hora_inicio")
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["jugador"]),
            models.Index(fields=["cancha"]),
        ]

    def __str__(self):
        return f"{self.jugador} - {self.fecha} - {self.hora_inicio} - Cancha {self.cancha.numero}"


class Cobrament(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    data = models.DateField()
    importe = models.DecimalField(max_digits=9, decimal_places=2)
    recepcionista = models.ForeignKey(Recepcionista, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("reserva", "jugador")
        indexes = [
            models.Index(fields=["reserva"]),
            models.Index(fields=["jugador"]),
        ]

    def __str__(self):
        return "{} , {} , {}, {}, {}".format(
            self.reserva, self.jugador, self.data, self.importe, self.recepcionista
        )


class ReservaRecurrente(models.Model):
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    cancha = models.ForeignKey(Pistes, on_delete=models.CASCADE)
    dia_semana = models.IntegerField(
        choices=[
            (i, d)
            for i, d in enumerate(
                [
                    "Lunes",
                    "Martes",
                    "Miércoles",
                    "Jueves",
                    "Viernes",
                    "Sábado",
                    "Domingo",
                ]
            )
        ],
        help_text="Día de la semana (0=Lunes, 6=Domingo)",
    )
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    notas = models.CharField(max_length=200, blank=True, null=True)
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.jugador} - {self.get_dia_semana_display()} {self.hora_inicio} ({self.fecha_inicio} a {self.fecha_fin}) - Cancha {self.cancha.numero}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Crear reservas individuales para cada semana dentro del rango
        if self.activa:
            current_date = self.fecha_inicio
            # Buscar el primer día correcto de la semana
            while current_date.weekday() != self.dia_semana:
                current_date += timedelta(days=1)
            # Crear reservas semanales hasta la fecha_fin
            while current_date <= self.fecha_fin:
                # Evitar duplicados: solo crear si no existe
                from .models import Reserva

                if not Reserva.objects.filter(
                    jugador=self.jugador,
                    cancha=self.cancha,
                    fecha=current_date,
                    hora_inicio=self.hora_inicio,
                ).exists():
                    Reserva.objects.create(
                        jugador=self.jugador,
                        cancha=self.cancha,
                        fecha=current_date,
                        hora_inicio=self.hora_inicio,
                        hora_fin=self.hora_fin,
                    )
                current_date += timedelta(days=7)


class Tarifa(models.Model):
    DIAS_SEMANA = [
        (0, "Lunes"),
        (1, "Martes"),
        (2, "Miércoles"),
        (3, "Jueves"),
        (4, "Viernes"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    precio = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # Permite valores hasta 9,999,999.99

    class Meta:
        unique_together = ("dia_semana", "hora_inicio", "hora_fin")
        verbose_name = "Tarifa"
        verbose_name_plural = "Tarifas"
        ordering = ["dia_semana", "hora_inicio"]

    def __str__(self):
        return f"{self.get_dia_semana_display()} {self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')}: ${self.precio}"


class HistoricoReserva(models.Model):
    ACCION_CHOICES = [
        ("pago", "Pago realizado"),
        ("cancelacion", "Reserva cancelada"),
        ("devolucion", "Devolución realizada"),
    ]
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    importe = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    detalles = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["reserva"]),
            models.Index(fields=["jugador"]),
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):
        return f"{self.jugador} - {self.reserva} - {self.accion} - {self.fecha} - {self.importe}"

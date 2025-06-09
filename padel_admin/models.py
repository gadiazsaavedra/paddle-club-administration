from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


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

    def __str__(self):
        return f"{self.jugador} - {self.fecha} - {self.hora_inicio} - Cancha {self.cancha.numero}"


class Cobrament(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    data = models.DateField()
    importe = models.DecimalField(max_digits=4, decimal_places=2)
    recepcionista = models.ForeignKey(Recepcionista, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("reserva", "jugador")

    def __str__(self):
        return "{} , {} , {}, {}, {}".format(
            self.reserva, self.jugador, self.data, self.importe, self.recepcionista
        )

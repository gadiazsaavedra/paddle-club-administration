from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.
class Jugadors(models.Model):
    id_jugador = models.CharField(primary_key=True, max_length=10)
    nom = models.CharField(max_length=30)
    cognom = models.CharField(max_length=30)
    nivell = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(6)])
    telefon = models.CharField(max_length=13)
    email = models.EmailField(max_length=50)
    contrasenya = models.CharField(max_length=30)
    
    def __str__(self):
        return '{} - {} {} (Nivell: {})'.format(self.id_jugador, self.nom, self.cognom, self.nivell) # No incluir contraseña

class Soci(Jugadors):
    IBAN = models.CharField(max_length=34)

    def __str__(self):
        return '{} , {} , {} , {} , {}, {}, {}, {}'.format(self.id_jugador, self.nom, self.cognom, self.nivell, self.telefon, self.email, self.contrasenya, self.IBAN)

class ConfiguracionGlobal(models.Model):
    clave = models.CharField(max_length=50, primary_key=True)
    valor = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.clave}: {self.valor}"


class CobramentSoci(models.Model):
    id_cobramentSoci = models.AutoField(primary_key=True)
    data = models.DateField()
    soci = models.ForeignKey(Soci, on_delete=models.CASCADE)

    def __str__(self):
        return '{} , {}, {}'.format(self.id_cobramentSoci, self.data, self.soci) # Corregido typo id_cobraSoci

class Pistes(models.Model):
    numero = models.IntegerField(primary_key=True)
    tipus = models.CharField(max_length=20)
    
    def __str__(self):
        return '{} , {}'.format(self.numero, self.tipus)

class Recepcionista(models.Model):
    DNI = models.CharField(primary_key=True ,max_length=9)
    nom = models.CharField(max_length=30)
    cognom = models.CharField(max_length=30)
    email = models.EmailField(max_length=50)
    contrasenya = models.CharField(max_length=30)
    telefon = models.CharField(max_length=13)

    def __str__(self):
        return '{} - {} {}'.format(self.DNI, self.nom, self.cognom) # No incluir contraseña

class Reserva(models.Model):
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    data = models.DateField()
    pista = models.ForeignKey(Pistes, on_delete=models.CASCADE)
    horaInici = models.TimeField()
    horaFinalitzacio = models.TimeField()
    recepcionista = models.ForeignKey(Recepcionista, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('jugador', 'data')

    def __str__(self):
        return '{} , {} , {}, {} , {}, {}'.format(self.jugador, self.data, self.pista, self.horaInici, self.horaFinalitzacio, self.recepcionista)

class Cobrament(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    data = models.DateField()
    importe = models.DecimalField(max_digits=10, decimal_places=2) # Aumentado max_digits
    recepcionista = models.ForeignKey(Recepcionista, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('reserva', 'jugador')

    def __str__(self):
        return '{} , {} , {}, {}, {}'.format(self.reserva, self.jugador, self.data, self.importe, self.recepcionista)
    
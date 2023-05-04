from django.db import models

# Create your models here.
class Jugadors(models.Model):
    DNI = models.CharField(primary_key=True ,max_length=9)
    nom = models.CharField(max_length=30)
    cognom = models.CharField(max_length=30)
    email = models.EmailField(max_length=50)
    telefon = models.CharField(max_length=9)
    
    def __str__(self):
        return '{} , {} , {} , {} , {}'.format(self.DNI, self.nom, self.cognom, self.email, self.telefon)

class Soci(Jugadors):
    IBAN = models.CharField(max_length=34)

    def __str__(self):
        return '{} , {} , {} , {} , {} , {}'.format(self.DNI, self.nom, self.cognom, self.email, self.telefon, self.IBAN)

class CobramentSoci(models.Model):
    id = models.AutoField(primary_key=True)
    data = models.DateField()
    soci = models.ForeignKey(Soci, on_delete=models.CASCADE)

    def __str__(self):
        return '{} , {}, {}'.format(self.id, self.data, self.soci)

class Pistes(models.Model):
    numero = models.IntegerField(primary_key=True)
    tipus = models.CharField(max_length=20)
    
    def __str__(self):
        return '{} , {}'.format(self.numero, self.tipus)

class Reserva(models.Model):
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    data = models.DateField()
    pista = models.ForeignKey(Pistes, on_delete=models.CASCADE)
    horaInici = models.TimeField()
    horaFinalitzacio = models.TimeField()

    class Meta:
        unique_together = ('jugador', 'data')

    def __str__(self):
        return '{} , {} , {}, {} , {}'.format(self.jugador, self.data, self.pista, self.horaInici, self.horaFinalitzacio)

class Cobrament(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    data = models.DateField()
    importe = models.DecimalField(max_digits=2, decimal_places=2)

    def __str__(self):
        return '{} , {} , {}, {}'.format(self.reserva, self.jugador, self.data, self.importe)
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction
from datetime import timedelta, date
from django.core.exceptions import ValidationError
from .managers import ReservaManager, CobramentManager
from django_q.tasks import schedule
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver


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
    fecha_alta = models.DateField(auto_now_add=True)  # Fecha de alta del jugador

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

    def clean(self):
        # Validar duplicado por nombre y apellido (case-insensitive, ignora espacios)
        nom_normalizado = self.nom.strip().lower()
        cognom_normalizado = self.cognom.strip().lower()
        qs = Jugadors.objects.filter(
            nom__iexact=nom_normalizado, cognom__iexact=cognom_normalizado
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(
                "Ya existe un jugador con el mismo nombre y apellido."
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

    objects = ReservaManager()

    class Meta:
        unique_together = ("cancha", "fecha", "hora_inicio")
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["jugador"]),
            models.Index(fields=["cancha"]),
        ]

    def __str__(self):
        return f"{self.jugador} - {self.fecha} - {self.hora_inicio} - Cancha {self.cancha.numero}"

    def clean(self):
        # Validar solapamiento de reservas para la misma cancha
        solapadas = Reserva.objects.filter(
            cancha=self.cancha,
            fecha=self.fecha,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        )
        if self.pk:
            solapadas = solapadas.exclude(pk=self.pk)
        if solapadas.exists():
            raise ValidationError("La cancha ya está reservada en ese horario.")
        # Validar que el jugador no tenga otra reserva solapada
        jugador_solapadas = Reserva.objects.filter(
            jugador=self.jugador,
            fecha=self.fecha,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        )
        if self.pk:
            jugador_solapadas = jugador_solapadas.exclude(pk=self.pk)
        if jugador_solapadas.exists():
            raise ValidationError(
                "El jugador ya tiene una reserva que se solapa con este horario."
            )
        # Validar duplicado exacto
        duplicada = Reserva.objects.filter(
            jugador=self.jugador,
            cancha=self.cancha,
            fecha=self.fecha,
            hora_inicio=self.hora_inicio,
            hora_fin=self.hora_fin,
        )
        if self.pk:
            duplicada = duplicada.exclude(pk=self.pk)
        if duplicada.exists():
            raise ValidationError(
                "Ya existe una reserva idéntica para este jugador, cancha y horario."
            )


class Cobrament(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugadors, on_delete=models.CASCADE)
    data = models.DateField()
    importe = models.DecimalField(max_digits=9, decimal_places=2)
    recepcionista = models.ForeignKey(Recepcionista, on_delete=models.CASCADE)

    objects = CobramentManager()

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

    def clean(self):
        # Validar máximo de 4 cobros por reserva
        count = (
            Cobrament.objects.filter(reserva=self.reserva).exclude(pk=self.pk).count()
        )
        if count >= 4:
            raise ValidationError("Límite de 4 cobros por reserva.")
        # Validar que no se repita el jugador en la misma reserva
        if (
            Cobrament.objects.filter(reserva=self.reserva, jugador=self.jugador)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError("El jugador ya pagó esta reserva.")


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


class Proveedor(models.Model):
    nombre = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    CATEGORIAS = [
        ("bebida", "Bebida"),
        ("snack", "Snack"),
        ("otro", "Otro"),
    ]
    codigo = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="Código único de identificación",
    )
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default="otro")
    precio_venta = models.DecimalField(max_digits=8, decimal_places=2)
    stock_actual = models.PositiveIntegerField(default=0)
    unidad_medida = models.CharField(max_length=20, default="unidad")
    activo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.codigo:
            # Generar un código único si no se proporciona
            from uuid import uuid4

            self.codigo = str(uuid4())[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.categoria})"


class IngresoStock(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="ingresos"
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingresos",
    )
    fecha = models.DateField(auto_now_add=True)
    cantidad = models.PositiveIntegerField()
    precio_compra = models.DecimalField(max_digits=8, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Sumar al stock actual del producto
        self.producto.stock_actual += self.cantidad
        self.producto.save()

    def __str__(self):
        return f"Ingreso {self.cantidad} x {self.producto} de {self.proveedor}"


class Venta(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    jugador = models.ForeignKey(
        Jugadors,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas",
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def calcular_total(self):
        total = sum([detalle.subtotal() for detalle in self.detalles.all()])
        self.total = total
        self.save()
        return total

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.date()} - Total: ${self.total}"


class VentaDetalle(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Descontar del stock del producto
        self.producto.stock_actual = max(0, self.producto.stock_actual - self.cantidad)
        self.producto.save()

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} a ${self.precio_unitario}"


class HistorialStock(models.Model):
    TIPO_MOVIMIENTO = [
        ("ingreso", "Ingreso"),
        ("salida", "Salida"),
        ("ajuste", "Ajuste"),
        ("merma", "Merma"),
    ]
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="historial_stock"
    )
    cantidad = models.IntegerField()
    tipo = models.CharField(max_length=10, choices=TIPO_MOVIMIENTO)
    fecha = models.DateTimeField(auto_now_add=True)
    motivo = models.CharField(max_length=200, blank=True, null=True)
    usuario = models.CharField(
        max_length=50, blank=True, null=True
    )  # nombre o identificador del responsable

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.cantidad} x {self.producto.nombre} el {self.fecha.strftime('%d/%m/%Y %H:%M')}"


class DisponibilidadJugador(models.Model):
    DIAS_SEMANA = [
        ("lunes", "Lunes"),
        ("martes", "Martes"),
        ("miercoles", "Miércoles"),
        ("jueves", "Jueves"),
        ("viernes", "Viernes"),
        ("sabado", "Sábado"),
        ("domingo", "Domingo"),
    ]
    BUSCA_CON = [
        ("hombre", "Hombre"),
        ("mujer", "Mujer"),
        ("ambos", "Ambos"),
    ]
    NIVELES = [
        ("novato", "Novato"),
        ("intermedio", "Intermedio"),
        ("avanzado", "Avanzado"),
    ]
    jugador = models.ForeignKey(
        Jugadors, on_delete=models.CASCADE, related_name="disponibilidades"
    )
    dias_disponibles = models.JSONField(
        help_text="Lista de días disponibles, ej: ['lunes', 'miercoles', 'viernes']"
    )
    franja_horaria_inicio = models.TimeField()
    franja_horaria_fin = models.TimeField()
    busca_con = models.CharField(max_length=10, choices=BUSCA_CON, default="ambos")
    nivel = models.CharField(max_length=10, choices=NIVELES)
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.jugador.nom} {self.jugador.cognom} - {self.nivel} - {self.dias_disponibles} {self.franja_horaria_inicio}-{self.franja_horaria_fin}"


class MatchJuego(models.Model):
    jugadores = models.ManyToManyField(Jugadors, related_name="matches")
    dia = models.CharField(max_length=10, choices=DisponibilidadJugador.DIAS_SEMANA)
    franja_horaria_inicio = models.TimeField()
    franja_horaria_fin = models.TimeField()
    nivel = models.CharField(max_length=10, choices=DisponibilidadJugador.NIVELES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    notificado = models.BooleanField(default=False)

    def __str__(self):
        return f"Match {self.dia} {self.franja_horaria_inicio}-{self.franja_horaria_fin} ({self.nivel}) - {self.jugadores.count()} jugadores"


class ConfiguracionSistema(models.Model):
    matching_activo = models.BooleanField(default=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Matching {'activo' if self.matching_activo else 'inactivo'}"


def buscar_y_crear_matches():
    """
    Busca coincidencias de jugadores disponibles y crea grupos de 4 para MatchJuego.
    Coincidencia: mismo día, franja horaria compatible, nivel y disponibilidad.
    """
    for dia, _ in DisponibilidadJugador.DIAS_SEMANA:
        for nivel, _ in DisponibilidadJugador.NIVELES:
            # Buscar todos los jugadores disponibles para ese día y nivel
            disponibles = DisponibilidadJugador.objects.filter(
                dias_disponibles__contains=[dia],
                nivel=nivel,
                disponible=True,
            ).order_by("franja_horaria_inicio")
            # Agrupar por franja horaria compatible
            grupos = []
            usados = set()
            for i, disp in enumerate(disponibles):
                if disp.id in usados:
                    continue
                grupo = [disp]
                usados.add(disp.id)
                for j, otro in enumerate(disponibles):
                    if i == j or otro.id in usados:
                        continue
                    # Chequear franja horaria compatible (intersección)
                    inicio = max(disp.franja_horaria_inicio, otro.franja_horaria_inicio)
                    fin = min(disp.franja_horaria_fin, otro.franja_horaria_fin)
                    if inicio < fin and otro.busca_con in (
                        disp.jugador.genero,
                        "ambos",
                    ):
                        grupo.append(otro)
                        usados.add(otro.id)
                    if len(grupo) == 4:
                        break
                if len(grupo) == 4:
                    # Crear el match si no existe uno igual
                    jugadores_ids = [d.jugador.id_jugador for d in grupo]
                    existe = (
                        MatchJuego.objects.filter(
                            dia=dia,
                            nivel=nivel,
                            franja_horaria_inicio=inicio,
                            franja_horaria_fin=fin,
                            jugadores__id_jugador__in=jugadores_ids,
                        )
                        .distinct()
                        .count()
                        > 0
                    )
                    if not existe:
                        match = MatchJuego.objects.create(
                            dia=dia,
                            nivel=nivel,
                            franja_horaria_inicio=inicio,
                            franja_horaria_fin=fin,
                        )
                        match.jugadores.set([d.jugador for d in grupo])


def notificar_jugadores_match(match):
    asunto = "¡Tienes un partido armado!"
    jugadores = match.jugadores.all()
    emails = [j.email for j in jugadores if j.email]
    mensaje = (
        f"Se ha formado un partido para el día {match.dia} de {match.franja_horaria_inicio.strftime('%H:%M')} a {match.franja_horaria_fin.strftime('%H:%M')}\n"
        f"Nivel: {match.nivel}\n"
        f"Jugadores: " + ", ".join(f"{j.nom} {j.cognom}" for j in jugadores)
    )
    send_mail(
        asunto,
        mensaje,
        "noreply@clubpaddle.com",  # Cambia por tu email real
        emails,
        fail_silently=True,
    )
    match.notificado = True
    match.save()


def agendar_matching_periodico():
    # Agenda la función buscar_y_crear_matches cada 2 minutos si no existe ya
    if not schedule.objects.filter(
        func="padel_admin.models.buscar_y_crear_matches"
    ).exists():
        schedule(
            "padel_admin.models.buscar_y_crear_matches",
            schedule_type=schedule.MINUTES,
            minutes=2,
            repeats=-1,
            name="Matching automático jugadores pádel",
        )


@receiver(post_save, sender=MatchJuego)
def avisar_recepcionista_match(sender, instance, created, **kwargs):
    if created and not instance.notificado:
        # Aquí podrías enviar un email al recepcionista o dejar un flag para mostrar en el admin
        # Ejemplo: print o log, o puedes implementar un email real si tienes el correo del recepcionista
        print(
            f"Nuevo match creado: {instance}. El recepcionista debe decidir si notifica por email o WhatsApp."
        )

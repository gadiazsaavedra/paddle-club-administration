# Generated by Django 4.2 on 2025-06-16 04:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('padel_admin', '0012_producto_codigo'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('matching_activo', models.BooleanField(default=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='MatchJuego',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dia', models.CharField(choices=[('lunes', 'Lunes'), ('martes', 'Martes'), ('miercoles', 'Miércoles'), ('jueves', 'Jueves'), ('viernes', 'Viernes'), ('sabado', 'Sábado'), ('domingo', 'Domingo')], max_length=10)),
                ('franja_horaria_inicio', models.TimeField()),
                ('franja_horaria_fin', models.TimeField()),
                ('nivel', models.CharField(choices=[('novato', 'Novato'), ('intermedio', 'Intermedio'), ('avanzado', 'Avanzado')], max_length=10)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('notificado', models.BooleanField(default=False)),
                ('jugadores', models.ManyToManyField(related_name='matches', to='padel_admin.jugadors')),
            ],
        ),
        migrations.CreateModel(
            name='HistorialStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.IntegerField()),
                ('tipo', models.CharField(choices=[('ingreso', 'Ingreso'), ('salida', 'Salida'), ('ajuste', 'Ajuste'), ('merma', 'Merma')], max_length=10)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('motivo', models.CharField(blank=True, max_length=200, null=True)),
                ('usuario', models.CharField(blank=True, max_length=50, null=True)),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historial_stock', to='padel_admin.producto')),
            ],
        ),
        migrations.CreateModel(
            name='DisponibilidadJugador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dias_disponibles', models.JSONField(help_text="Lista de días disponibles, ej: ['lunes', 'miercoles', 'viernes']")),
                ('franja_horaria_inicio', models.TimeField()),
                ('franja_horaria_fin', models.TimeField()),
                ('busca_con', models.CharField(choices=[('hombre', 'Hombre'), ('mujer', 'Mujer'), ('ambos', 'Ambos')], default='ambos', max_length=10)),
                ('nivel', models.CharField(choices=[('novato', 'Novato'), ('intermedio', 'Intermedio'), ('avanzado', 'Avanzado')], max_length=10)),
                ('disponible', models.BooleanField(default=True)),
                ('jugador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='disponibilidades', to='padel_admin.jugadors')),
            ],
        ),
    ]

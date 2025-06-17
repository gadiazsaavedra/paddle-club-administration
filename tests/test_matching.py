import pytest
from padel_admin.models import Jugadors, DisponibilidadJugador, MatchJuego
from django.utils import timezone


def crear_jugador(email, nombre, nivel="intermedio"):
    return Jugadors.objects.create(
        id_jugador=email.split("@")[0],
        nom=nombre,
        cognom="Test",
        email=email,
        nivell=2 if nivel == "intermedio" else 1,
        telefon="123456789",
    )


def test_matching_simple(db):
    # Crear dos jugadores con misma disponibilidad
    jugador1 = crear_jugador("a@a.com", "Ana")
    jugador2 = crear_jugador("b@b.com", "Beto")
    disp1 = DisponibilidadJugador.objects.create(
        jugador=jugador1,
        dias_disponibles=[{"dia": "lunes", "inicio": "18:00", "fin": "20:00"}],
        busca_con="ambos",
        nivel="intermedio",
        disponible=True,
    )
    disp2 = DisponibilidadJugador.objects.create(
        jugador=jugador2,
        dias_disponibles=[{"dia": "lunes", "inicio": "18:00", "fin": "20:00"}],
        busca_con="ambos",
        nivel="intermedio",
        disponible=True,
    )
    # Ejecutar lógica de matching (ajusta el import si tienes función específica)
    from padel_admin.services import buscar_y_crear_matches

    buscar_y_crear_matches()
    # Verificar que se creó un match
    matches = MatchJuego.objects.filter(
        dia="lunes", franja_horaria_inicio="18:00", nivel="intermedio"
    )
    assert matches.exists(), "No se creó el match esperado"
    match = matches.first()
    jugadores = list(match.jugadores.all())
    assert (
        jugador1 in jugadores and jugador2 in jugadores
    ), "Los jugadores no están en el match"
    # Limpieza
    MatchJuego.objects.all().delete()
    DisponibilidadJugador.objects.all().delete()
    Jugadors.objects.all().delete()

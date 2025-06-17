from padel_admin.models import Jugadors, DisponibilidadJugador

jugadores = [
    {
        "id_jugador": "J1",
        "nom": "Ana",
        "cognom": "García",
        "email": "ana@example.com",
        "nivel": 2,
        "contrasenya": "123",
        "telefon": "111",
    },
    {
        "id_jugador": "J2",
        "nom": "Luis",
        "cognom": "Pérez",
        "email": "luis@example.com",
        "nivel": 2,
        "contrasenya": "123",
        "telefon": "222",
    },
    {
        "id_jugador": "J3",
        "nom": "Sofía",
        "cognom": "López",
        "email": "sofia@example.com",
        "nivel": 2,
        "contrasenya": "123",
        "telefon": "333",
    },
    {
        "id_jugador": "J4",
        "nom": "Carlos",
        "cognom": "Ruiz",
        "email": "carlos@example.com",
        "nivel": 2,
        "contrasenya": "123",
        "telefon": "444",
    },
]

for data in jugadores:
    j, created = Jugadors.objects.get_or_create(
        id_jugador=data["id_jugador"], defaults=data
    )
    DisponibilidadJugador.objects.update_or_create(
        jugador=j,
        defaults={
            "dias_disponibles": ["martes"],
            "franja_horaria_inicio": "18:00",
            "franja_horaria_fin": "20:00",
            "busca_con": "ambos",
            "nivel": "intermedio",
            "disponible": True,
        },
    )
print("Jugadores y disponibilidades de demo cargados correctamente.")

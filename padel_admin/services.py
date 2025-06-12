from datetime import datetime, date
from decimal import Decimal
from .models import Jugadors, Reserva, Cobrament, Pistes, Recepcionista
from .utils import (
    get_recepcionista_or_none,
    calcular_importe_reserva,
    registrar_historico_reserva,  # Import correcto desde utils
)


class ReservaService:
    @staticmethod
    def crear_reserva(
        jugador_nom,
        jugador_cognom,
        fecha,
        hora_inicio_str,
        duracion,
        type_cancha,
        cancha_numero,
        request,
        recepcionista_required=True,
    ):
        # Robustez: aceptar fecha como str o date
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
            except Exception:
                return None, "Fecha inválida."
        try:
            jugador = Jugadors.objects.get(nom=jugador_nom, cognom=jugador_cognom)
        except Jugadors.DoesNotExist:
            return None, "El jugador no existe."
        try:
            hora_inicio = (
                datetime.strptime(hora_inicio_str, "%H:%M").time()
                if isinstance(hora_inicio_str, str)
                else hora_inicio_str
            )
        except Exception:
            return None, "Hora de inicio inválida."
        from .views import calcular_hora_fin

        hora_fin = calcular_hora_fin(hora_inicio, duracion)
        try:
            cancha = Pistes.objects.get(numero=cancha_numero, tipo=type_cancha)
        except Pistes.DoesNotExist:
            return None, "La cancha seleccionada no existe o no es del tipo elegido."
        # Validar solapamiento robusto y duplicados
        if Reserva.objects.filter(
            cancha=cancha,
            fecha=fecha,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio,
        ).exists():
            return None, "La cancha ya está reservada en ese horario."
        if Reserva.objects.filter(
            jugador=jugador,
            fecha=fecha,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio,
        ).exists():
            return (
                None,
                "El jugador ya tiene una reserva que se solapa con este horario.",
            )
        if Reserva.objects.filter(
            jugador=jugador,
            cancha=cancha,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
        ).exists():
            return (
                None,
                "Ya existe una reserva idéntica para este jugador, cancha y horario.",
            )
        recepcionista = None
        if recepcionista_required:
            acceso = request.COOKIES.get("acceso")
            if not acceso:
                return None, "No hay sesión de recepcionista activa."
            try:
                recepcionista = Recepcionista.objects.get(DNI=acceso)
            except Recepcionista.DoesNotExist:
                return None, "Recepcionista no encontrado. Inicie sesión nuevamente."
        reserva = Reserva(
            jugador=jugador,
            fecha=fecha,
            cancha=cancha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            recepcionista=recepcionista,
        )
        reserva.save()
        return reserva, None


class CobroService:
    @staticmethod
    def registrar_cobro(reserva, jugador, data, request):
        # Robustez: aceptar data como str o date
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, "%Y-%m-%d").date()
            except Exception:
                return None, None, "Fecha de cobro inválida."
        rec = get_recepcionista_or_none(request)
        if not rec:
            return None, None, "Recepcionista no encontrado. Inicie sesión nuevamente."
        importe = calcular_importe_reserva(reserva)
        try:
            if not importe or importe == 0:
                return (
                    None,
                    None,
                    "No se puede registrar el cobro porque el importe es 0. Verifique la tarifa configurada.",
                )
            partes = str(importe).split(".")
            if len(partes[0]) > 8:
                return None, None, "Importe demasiado grande para el campo."
            importe = importe.quantize(Decimal("0.01"))
        except Exception:
            return (
                None,
                None,
                "Error crítico al redondear el importe. No se pudo registrar el cobro.",
            )
        if abs(importe) >= Decimal("1000000.01"):
            return (
                None,
                None,
                f"El importe final ({importe}) excede el máximo permitido de 1,000,000.00.",
            )
        if Cobrament.objects.filter(reserva=reserva).count() >= 4:
            return None, None, "Limite de 4 persones en la cancha."
        if Cobrament.objects.filter(reserva=reserva, jugador=jugador).exists():
            return None, None, "El jugador ya pagó esta reserva."
        try:
            cobrament = Cobrament.objects.create(
                reserva=reserva,
                jugador=jugador,
                data=data,
                importe=importe,
                recepcionista=rec,
            )
            registrar_historico_reserva(
                reserva=reserva,
                jugador=jugador,
                accion="pago",
                importe=importe,
                detalles=f"Pago registrado por {jugador.nom} {jugador.cognom}",
            )
            return cobrament, importe, None
        except Exception as e:
            return (
                None,
                None,
                f"Error al guardar el cobro: {str(e)}. Importe ({importe}) inválido.",
            )

    @staticmethod
    def editar_cobro(cobrament, nuevo_importe, request):
        rec = get_recepcionista_or_none(request)
        if not rec:
            return None, "Recepcionista no encontrado. Inicie sesión nuevamente."
        try:
            nuevo_importe = Decimal(str(nuevo_importe))
            if not nuevo_importe.is_finite() or nuevo_importe < 0:
                return None, "Importe no válido (NaN/Infinito/Negativo)."
            if abs(nuevo_importe) >= Decimal("1000000.01"):
                return (
                    None,
                    f"El importe final ({nuevo_importe}) excede el máximo permitido de 1,000,000.00.",
                )
            nuevo_importe = nuevo_importe.quantize(
                Decimal("0.01"), rounding="ROUND_FLOOR"
            )
        except Exception as e:
            return None, f"Error al validar el importe: {str(e)}."
        try:
            importe_anterior = cobrament.importe
            cobrament.importe = nuevo_importe
            cobrament.recepcionista = rec
            cobrament.save()
            registrar_historico_reserva(
                reserva=cobrament.reserva,
                jugador=cobrament.jugador,
                accion="edicion_pago",
                importe=nuevo_importe,
                detalles=f"Edición de cobro: de {importe_anterior} a {nuevo_importe} por {rec.nom if hasattr(rec, 'nom') else rec.DNI}",
            )
            return cobrament, None
        except Exception as e:
            return None, f"Error al editar el cobro: {str(e)}."

    @staticmethod
    def eliminar_cobro(cobrament, request):
        rec = get_recepcionista_or_none(request)
        if not rec:
            return False, "Recepcionista no encontrado. Inicie sesión nuevamente."
        try:
            registrar_historico_reserva(
                reserva=cobrament.reserva,
                jugador=cobrament.jugador,
                accion="eliminacion_pago",
                importe=cobrament.importe,
                detalles=f"Cobro eliminado por {rec.nom if hasattr(rec, 'nom') else rec.DNI}",
            )
            cobrament.delete()
            return True, None
        except Exception as e:
            return False, f"Error al eliminar el cobro: {str(e)}."

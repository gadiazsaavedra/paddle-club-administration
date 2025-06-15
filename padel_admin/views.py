from datetime import datetime, date, time, timedelta
from enum import unique
import json
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
import random
from .models import (
    Jugadors,
    Reserva,
    Cobrament,
    Recepcionista,
    Pistes,
    Recepcionista,
    Tarifa,
    Proveedor,
    Producto,
    IngresoStock,
    Venta,
    VentaDetalle,
)
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import logging
from decimal import Decimal, InvalidOperation, localcontext
from django.urls import reverse
from .utils import (
    require_recepcionista,
    get_jugador_or_404,
    get_reserva_or_404,
    handle_view_errors,
    validate_required_fields,
    get_recepcionista_or_none,
    calcular_importe_reserva,
    registrar_historico_reserva,  # Asegurar import correcto
)
from .services import ReservaService, CobroService
from django.http import JsonResponse
from .forms import (
    ProveedorForm,
    ProductoForm,
    IngresoStockForm,
    VentaForm,
    VentaDetalleForm,
)
from django.forms import modelformset_factory
from django.forms import formset_factory
from django.db.models import Sum
from django.utils import timezone
from django.db import transaction


def landing(request):
    if request.method == "POST":
        dni = request.POST.get("dni")
        contrasenya = request.POST.get("contrasenya")
        try:
            recepcionista = Recepcionista.objects.get(DNI=dni, contrasenya=contrasenya)
            response = redirect("lista_reserves")
            response.set_cookie("acceso", str(recepcionista.DNI))
            return response
        except Recepcionista.DoesNotExist:
            messages.error(request, "El DNI o password son incorrectos")
            return render(request, "landing.html")
        except MultipleObjectsReturned:
            messages.error(
                request,
                "Error: hay múltiples recepcionistas con ese DNI. Contacte al administrador.",
            )
            return render(request, "landing.html")
    else:
        return render(request, "landing.html")


def home(request):
    """Vista principal (home) que muestra la página de bienvenida."""
    return render(request, "bienvenida.html")


@handle_view_errors
def lista_reserves(request):
    acceso = request.COOKIES.get("acceso")
    if not acceso:
        mensaje = "Acceso denegado: no hay sesión activa."
        return render(request, "landing.html", {"mensaje": mensaje})

    # hores disponibles
    hora_min = time(hour=9, minute=0, second=0)
    hora_max = time(hour=21, minute=0, second=0)
    hours = []
    current_hour = hora_min
    while current_hour <= hora_max:
        hours.append(current_hour.strftime("%H:%M"))
        current_hour = (
            datetime.combine(datetime.min, current_hour) + timedelta(minutes=30)
        ).time()

    pistas_disponibles = Pistes.objects.all().order_by("numero")
    jugadores_registrados = Jugadors.objects.all().order_by("nom", "cognom")

    # --- FUNCIONES INTERNAS PARA CENTRALIZAR LÓGICA ---
    def obtener_fecha_y_reservas(fecha_str=None):
        if fecha_str:
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        else:
            fecha_obj = date.today()
        day = fecha_obj.strftime("%Y-%m-%d")
        # select_related para evitar N+1
        reserves = (
            Reserva.objects.filter(fecha=fecha_obj)
            .select_related("jugador", "cancha")
            .prefetch_related("cobrament_set")
            .order_by("hora_inicio", "hora_inicio", "cancha")
        )
        return day, reserves

    def render_lista_reserves(request, contexto_extra=None):
        contexto = {
            "hours": hours,
            "pistas_disponibles": pistas_disponibles,
            "jugadores_registrados": jugadores_registrados,
        }
        if contexto_extra:
            contexto.update(contexto_extra)
        return render(request, "lista_reserves.html", contexto)

    # --- FIN FUNCIONES INTERNAS ---

    if request.method == "POST":
        # eliminar jugador
        if request.POST.get("_method") == "DELETE":
            jugador_id = request.POST.get("jugador_id")
            fecha = request.POST.get("data")
            hora_inicio = request.POST.get("hora_inicio")
            try:
                jugador = get_jugador_or_404(jugador_id)
                reservas = Reserva.objects.filter(
                    jugador=jugador, fecha=fecha
                ).order_by("hora_inicio")
                if not reservas.exists():
                    messages.error(request, "No se encontró el jugador o la reserva.")
                    day, reserves = obtener_fecha_y_reservas(fecha)
                    return render_lista_reserves(
                        request,
                        {
                            "reserves": reserves,
                            "day": day,
                        },
                    )
                elif reservas.count() == 1 or hora_inicio:
                    if hora_inicio:
                        reserva = reservas.filter(hora_inicio=hora_inicio).first()
                        if not reserva:
                            messages.error(
                                request,
                                "No se encontró la reserva con la hora indicada.",
                            )
                            day, reserves = obtener_fecha_y_reservas(fecha)
                            return render_lista_reserves(
                                request,
                                {
                                    "reserves": reserves,
                                    "day": day,
                                },
                            )
                    else:
                        reserva = reservas.first()
                else:
                    messages.warning(
                        request,
                        "Hay más de una reserva para este jugador y fecha. Selecciona la reserva a eliminar.",
                    )
                    day, reserves = obtener_fecha_y_reservas(fecha)
                    return render_lista_reserves(
                        request,
                        {
                            "reserves": reserves,
                            "day": day,
                            "jugador": jugador,
                            "reservas_a_eliminar": reservas,
                            "multiple_reservas": True,
                        },
                    )
                # Registrar histórico de cancelación antes de borrar
                from .models import HistoricoReserva

                # Si la reserva tiene cobros asociados, eliminarlos y registrar devolución
                from .models import HistoricoReserva, Cobrament

                cobros = Cobrament.objects.filter(reserva=reserva)
                for cobro in cobros:
                    registrar_historico_reserva(
                        reserva=reserva,
                        jugador=cobro.jugador,
                        accion="devolucion",
                        importe=cobro.importe,
                        detalles="Devolución automática por cancelación de reserva pagada",
                    )
                    cobro.delete()
                # Registrar histórico de cancelación antes de borrar
                registrar_historico_reserva(
                    reserva=reserva,
                    jugador=jugador,
                    accion="cancelacion",
                    importe=None,
                    detalles="Reserva cancelada por el usuario o admin",
                )
                reserva.delete()
            except Jugadors.DoesNotExist:
                messages.error(request, "No se encontró el jugador o la reserva.")
                day, reserves = obtener_fecha_y_reservas(fecha)
                return render_lista_reserves(
                    request,
                    {
                        "reserves": reserves,
                        "day": day,
                    },
                )
            day, reserves = obtener_fecha_y_reservas(fecha)
            return render_lista_reserves(request, {"reserves": reserves, "day": day})
        # AFEGIR RESERVA
        required_fields = [
            "fecha-2",
            "horaInici",
            "horaFinalitzacio",
            "Pista",
            "cancha_numero",
            "jugador_select",
        ]
        missing = validate_required_fields(request, required_fields)
        if missing:
            messages.error(
                request, f"Faltan campos obligatorios: {', '.join(missing)}."
            )
            day, reserves = obtener_fecha_y_reservas()
            return render_lista_reserves(
                request,
                {
                    "reserves": reserves,
                    "day": day,
                },
            )
        datos = obtener_datos_reserva_formulario(request, modo="recepcionista")
        reserva, error = ReservaService.crear_reserva(
            **datos, request=request, recepcionista_required=True
        )
        if error:
            messages.error(request, error)
            day, reserves = obtener_fecha_y_reservas()
            return render_lista_reserves(
                request,
                {
                    "reserves": reserves,
                    "day": day,
                },
            )
        messages.success(request, "Reserva creada exitosamente.")
        # Redirigir al calendario semanal tras crear la reserva
        return redirect("calendario_canchas")

    fecha = request.GET.get("fecha")
    day, reserves = obtener_fecha_y_reservas(fecha)
    # Para mostrar importe estimado en el formulario de reserva
    importe_estimado = None
    if (
        request.method == "GET"
        and request.GET.get("fecha")
        and request.GET.get("hora")
        and request.GET.get("horaFinalitzacio")
    ):
        try:
            fecha_str = request.GET.get("fecha")
            hora_inicio_str = request.GET.get("hora")
            duracion = request.GET.get("horaFinalitzacio")
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M").time()
            hora_fin = calcular_hora_fin(hora_inicio, duracion)
            tarifa = obtener_tarifa_para_reserva(fecha_obj, hora_inicio, hora_fin)
            if tarifa:
                dt_inicio = datetime.combine(fecha_obj, hora_inicio)
                dt_fin = datetime.combine(fecha_obj, hora_fin)
                duracion_horas = (dt_fin - dt_inicio).total_seconds() / 3600
                importe_estimado = round(float(tarifa.precio) * duracion_horas, 2)
        except Exception as e:
            logging.exception(e)
            importe_estimado = None

    # --- NUEVO: calcular estado de cobro del titular para cada reserva ---
    titular_pagado_dict = {}
    for reserva in reserves:
        # True si existe un cobro para el titular de la reserva
        titular_pagado_dict[reserva.id] = reserva.cobrament_set.filter(
            jugador=reserva.jugador
        ).exists()

    return render_lista_reserves(
        request,
        {
            "reserves": reserves,
            "day": day,
            "importe_estimado": importe_estimado,
            "titular_pagado_dict": titular_pagado_dict,
        },
    )


@handle_view_errors
def lista_jugadors(request):
    acceso = request.COOKIES.get("acceso")
    if not acceso:
        messages.error(request, "Acceso denegado: no hay sesión activa.")
        return render(request, "landing.html")
    search_query = request.GET.get("search")

    if request.method == "POST":
        if request.POST.get("_method") == "DELETE":
            jugador_id = request.POST.get("jugador_id")
            jugador = get_jugador_or_404(jugador_id)
            jugador.delete()
            return redirect("lista_jugadors")

        elif request.POST.get("_method") == "PATCH":
            jugador_id = request.POST.get("id_jugador")
            jugador = get_jugador_or_404(jugador_id)
            required_fields = ["nom", "cognom", "email", "telefon", "nivell"]
            missing = validate_required_fields(request, required_fields)
            if missing:
                campos = [
                    campo if campo != "cognom" else "apellido" for campo in missing
                ]
                messages.error(
                    request, f"Faltan campos obligatorios: {', '.join(campos)}."
                )
                return redirect("lista_jugadors")
            nom = request.POST.get("nom")
            cognom = request.POST.get("cognom")
            # Normalización para evitar duplicados en edición
            nom_normalizado = nom.strip().lower()
            cognom_normalizado = cognom.strip().lower()
            if (
                Jugadors.objects.filter(
                    nom__iexact=nom_normalizado, cognom__iexact=cognom_normalizado
                )
                .exclude(id_jugador=jugador_id)
                .exists()
            ):
                messages.warning(
                    request,
                    f"Ya existe un jugador con el nombre '{nom}' y apellido '{cognom}'. No se puede actualizar con datos duplicados.",
                )
                return redirect("lista_jugadors")
            jugador.nom = nom
            jugador.cognom = cognom
            jugador.email = request.POST.get("email")
            jugador.telefon = request.POST.get("telefon")
            jugador.nivell = request.POST.get("nivell")
            if request.FILES.get("foto"):
                jugador.foto = request.FILES.get("foto")
            jugador.save()
            messages.success(request, "Jugador actualizado correctamente.")
            return redirect("lista_jugadors")

        else:
            # Procesar los datos del formulario (alta jugador)
            required_fields = ["nom", "cognom", "email", "telefon", "nivell"]
            missing = validate_required_fields(request, required_fields)
            if missing:
                campos = [
                    campo if campo != "cognom" else "apellido" for campo in missing
                ]
                messages.error(
                    request, f"Faltan campos obligatorios: {', '.join(campos)}."
                )
                return redirect("lista_jugadors")
            nom = request.POST.get("nom")
            cognom = request.POST.get("cognom")
            email = request.POST.get("email")
            telefon = request.POST.get("telefon")
            nivell = request.POST.get("nivell")
            contrasenya = str(nom)
            foto = request.FILES.get("foto")
            # Validar duplicado por nombre y apellido (case-insensitive, ignora espacios)
            nom_normalizado = nom.strip().lower()
            cognom_normalizado = cognom.strip().lower()
            if Jugadors.objects.filter(
                nom__iexact=nom_normalizado, cognom__iexact=cognom_normalizado
            ).exists():
                messages.warning(
                    request,
                    f"Ya existe un jugador con el nombre '{nom}' y apellido '{cognom}'. No se creó el jugador.",
                )
                return redirect("lista_jugadors")
            id_jugador = random.randrange(10000, 100000)
            # Evitar duplicados por id_jugador
            while Jugadors.objects.filter(id_jugador=id_jugador).exists():
                id_jugador = random.randrange(10000, 100000)
            jugador = Jugadors(
                id_jugador=id_jugador,
                nom=nom,
                cognom=cognom,
                email=email,
                telefon=telefon,
                nivell=nivell,
                contrasenya=contrasenya,
                foto=foto,
            )
            jugador.save()
            messages.success(request, "Jugador creado correctamente.")
            return redirect("lista_jugadors")

    jugadors_list = Jugadors.objects.all()
    if search_query:
        jugadors_list = jugadors_list.filter(
            nom__icontains=search_query
        ) | jugadors_list.filter(cognom__icontains=search_query)
    paginator = Paginator(jugadors_list, 100)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
        "search_query": search_query,
    }
    return render(request, "lista_jugadors.html", context)


@handle_view_errors
def perfil_jugador(request):
    jugador_id = request.COOKIES.get("jugador_id")
    if not jugador_id:
        return redirect("login")
    jugador = get_jugador_or_404(jugador_id)
    reservas = (
        Reserva.objects.filter(jugador=jugador)
        .select_related("cancha", "recepcionista")
        .prefetch_related("cobrament_set")
        .order_by("-fecha", "-hora_inicio")
    )
    total_reservas = reservas.count()
    total_horas = sum(
        [
            (
                datetime.combine(r.fecha, r.hora_fin)
                - datetime.combine(r.fecha, r.hora_inicio)
            ).total_seconds()
            / 3600
            for r in reservas
        ]
    )
    canchas_usadas = (
        reservas.values("cancha__numero", "cancha__tipo").distinct().count()
    )
    if request.method == "POST":
        required_fields = ["nom", "cognom", "email", "telefon", "nivell"]
        missing = validate_required_fields(request, required_fields)
        if missing:
            messages.error(
                request, f"Faltan campos obligatorios: {', '.join(missing)}."
            )
        else:
            nom = request.POST.get("nom")
            cognom = request.POST.get("cognom")
            nom_normalizado = nom.strip().lower()
            cognom_normalizado = cognom.strip().lower()
            if (
                Jugadors.objects.filter(
                    nom__iexact=nom_normalizado, cognom__iexact=cognom_normalizado
                )
                .exclude(id_jugador=jugador.id_jugador)
                .exists()
            ):
                messages.warning(
                    request,
                    f"Ya existe un jugador con el nombre '{nom}' y apellido '{cognom}'. No se puede actualizar con datos duplicados.",
                )
            else:
                jugador.nom = nom
                jugador.cognom = cognom
                jugador.email = request.POST.get("email")
                jugador.telefon = request.POST.get("telefon")
                jugador.nivell = request.POST.get("nivell")
                if request.FILES.get("foto"):
                    jugador.foto = request.FILES.get("foto")
                jugador.save()
                messages.success(request, "Perfil actualizado correctamente.")
    context = {
        "jugador": jugador,
        "reservas": reservas,
        "total_reservas": total_reservas,
        "total_horas": total_horas,
        "canchas_usadas": canchas_usadas,
    }
    return render(request, "perfil_jugador.html", context)


def obtener_datos_cobro_formulario(request):
    """Extrae los datos necesarios para registrar un cobro desde el request."""
    # En este caso, el importe se calcula, pero si en el futuro se permite ingresar importe manual, aquí se puede extraer
    return {}


def registrar_cobro_util(reserva, jugador, data, request):
    """Centraliza la lógica de cálculo, validación y registro de cobros. Devuelve (cobrament, importe_final, error_message)"""
    rec = get_recepcionista_or_none(request)
    if not rec:
        return None, None, "Recepcionista no encontrado. Inicie sesión nuevamente."
    # Calcular importe según tarifa y duración
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


@handle_view_errors
def lista_cobraments(request, data, id_jugador):
    acceso = request.COOKIES.get("acceso")
    if not acceso:
        messages.error(request, "Acceso Denegado: no hay sesión activa.")
        return render(request, "landing.html")
    jugador = get_jugador_or_404(id_jugador)
    reservas = (
        Reserva.objects.filter(fecha=data, jugador=jugador)
        .select_related("cancha", "jugador")
        .prefetch_related("cobrament_set")
        .order_by("hora_inicio")
    )
    if not reservas.exists():
        messages.error(request, "No se encontró el jugador o la reserva.")
        return render(request, "lista_cobraments.html")
    elif reservas.count() == 1:
        reserva = reservas.first()
    else:
        messages.warning(
            request,
            "Hay más de una reserva para este jugador y fecha. Selecciona la reserva deseada.",
        )
        return render(
            request,
            "lista_cobraments.html",
            {"jugador": jugador, "reservas": reservas, "multiple_reservas": True},
        )
    cobros = reserva.cobrament_set.all().select_related("jugador", "recepcionista")
    ya_pago = cobros.filter(jugador=jugador).exists()
    if request.method == "POST":
        if request.POST.get("devolucion") == "1":
            for cobro in cobros:
                registrar_historico_reserva(
                    reserva=reserva,
                    jugador=cobro.jugador,
                    accion="devolucion",
                    importe=cobro.importe,
                    detalles="Devolución automática por cancelación de reserva pagada desde gestión de cobros",
                )
                cobro.delete()
            registrar_historico_reserva(
                reserva=reserva,
                jugador=jugador,
                accion="cancelacion",
                importe=None,
                detalles="Reserva cancelada y devuelta desde gestión de cobros",
            )
            reserva.delete()
            messages.success(
                request, "Reserva cancelada, cobro devuelto y turno liberado."
            )
            return redirect("lista_reserves")
        cobrament, importe_final, error = CobroService.registrar_cobro(
            reserva, jugador, data, request
        )
        if error:
            messages.error(request, error)
            return render(
                request,
                "lista_cobraments.html",
                {
                    "jugador": jugador,
                    "reserva": reserva,
                    "importe": importe_final if importe_final is not None else 0,
                    "ya_pago": ya_pago,
                },
            )
        messages.success(
            request,
            f"{jugador.nom} {jugador.cognom} ha realizado un pago de {importe_final} $",
        )
        return render(
            request,
            "lista_cobraments.html",
            {
                "importe": importe_final,
                "jugador": jugador,
                "reserva": reserva,
                "ya_pago": True,
            },
        )
    tarifa = obtener_tarifa_para_reserva(
        reserva.fecha, reserva.hora_inicio, reserva.hora_fin
    )
    try:
        if not tarifa or tarifa.precio in (None, ""):
            importe = Decimal("0.00")
        else:
            precio_str = str(tarifa.precio).replace(" ", "").replace(",", ".")
            precio_decimal = Decimal(precio_str)
            dt_inicio = datetime.combine(reserva.fecha, reserva.hora_inicio)
            dt_fin = datetime.combine(reserva.fecha, reserva.hora_fin)
            duracion_horas = Decimal(
                str((dt_fin - dt_inicio).total_seconds())
            ) / Decimal("3600")
            importe = precio_decimal * duracion_horas
            if not importe.is_finite() or importe < 0:
                importe = Decimal("0.00")
            else:
                importe = importe.quantize(Decimal("0.01"), rounding="ROUND_FLOOR")
    except Exception:
        importe = Decimal("0.00")
    return render(
        request,
        "lista_cobraments.html",
        {
            "jugador": jugador,
            "reserva": reserva,
            "importe": importe,
            "ya_pago": ya_pago,
            "cobros": cobros,
        },
    )


@handle_view_errors
def editar_cobro(request, id_cobro):
    cobrament = get_reserva_or_404(id_cobro, model_class=Cobrament)
    if request.method == "POST":
        nuevo_importe = request.POST.get("nuevo_importe")
        cobrament_editado, error = CobroService.editar_cobro(
            cobrament, nuevo_importe, request
        )
        if error:
            messages.error(request, error)
            return render(request, "editar_cobro.html", {"cobrament": cobrament})
        messages.success(request, "Cobro editado correctamente.")
        return redirect(
            reverse(
                "lista_cobraments",
                kwargs={
                    "data": cobrament.reserva.fecha,
                    "id_jugador": cobrament.jugador.id_jugador,
                },
            )
        )
    return render(request, "editar_cobro.html", {"cobrament": cobrament})


@handle_view_errors
def eliminar_cobro(request, id_cobro):
    cobrament = get_reserva_or_404(id_cobro, model_class=Cobrament)
    if request.method == "POST":
        ok, error = CobroService.eliminar_cobro(cobrament, request)
        if error:
            messages.error(request, error)
            return render(
                request,
                "eliminar_cobro.html",
                {"cobrament": cobrament},
            )
        messages.success(request, "Cobro eliminado correctamente.")
        return redirect(
            reverse(
                "lista_cobraments",
                kwargs={
                    "data": cobrament.reserva.fecha,
                    "id_jugador": cobrament.jugador.id_jugador,
                },
            )
        )
    return render(request, "eliminar_cobro.html", {"cobrament": cobrament})


def logout(request):
    response = redirect(
        "login"
    )  # Redirige a la página de inicio de sesión después de hacer logout
    response.delete_cookie("acceso")  # Elimina la cookie 'recepcionista_id'
    return response


def calendario_canchas(request):
    # Obtener fecha actual o la seleccionada
    fecha_str = request.GET.get("fecha")
    if fecha_str:
        fecha_actual = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    else:
        fecha_actual = datetime.now().date()

    # Generar fechas para la semana
    inicio_semana = fecha_actual - timedelta(days=fecha_actual.weekday())
    fechas_semana = [inicio_semana + timedelta(days=i) for i in range(7)]

    # Obtener todas las canchas
    canchas = Pistes.objects.all().order_by("numero")

    # Horas disponibles (9:00 a 21:00)
    horas = []
    hora_actual = datetime.strptime("09:00", "%H:%M").time()
    hora_fin = datetime.strptime("21:00", "%H:%M").time()

    while hora_actual <= hora_fin:
        horas.append(hora_actual)
        dt = datetime.combine(datetime.today(), hora_actual)
        dt = dt + timedelta(minutes=30)
        hora_actual = dt.time()

    # Obtener todas las reservas para la semana
    reservas = Reserva.objects.filter(
        fecha__gte=fechas_semana[0], fecha__lte=fechas_semana[6]
    ).select_related("jugador", "cancha")
    # Construir índice: {(cancha_numero, fecha): [reserva, ...]}
    reservas_index = {}
    for r in reservas:
        reservas_index.setdefault((r.cancha.numero, r.fecha), []).append(r)

    # Obtener todos los cobros de reservas de la semana
    cobros = Cobrament.objects.filter(reserva__in=reservas)
    reservas_pagadas_ids = set(cobros.values_list("reserva_id", flat=True))

    calendario_cancha_filas = []
    for cancha in canchas:
        filas = []
        for hora in horas:
            estados = []
            for i, fecha in enumerate(fechas_semana):
                # Buscar reserva para esta cancha, fecha y hora
                reservas_dia = reservas_index.get((cancha.numero, fecha), [])
                reserva = next(
                    (r for r in reservas_dia if r.hora_inicio <= hora < r.hora_fin),
                    None,
                )
                if reserva:
                    if reserva.id in reservas_pagadas_ids:
                        estados.append(
                            (
                                "pagado",
                                fecha,
                                reserva.jugador.nom,
                                reserva.jugador.cognom,
                            )
                        )
                    else:
                        estados.append(
                            (
                                "ocupado",
                                fecha,
                                reserva.jugador.nom,
                                reserva.jugador.cognom,
                            )
                        )
                else:
                    estados.append(("disponible", fecha, "", ""))
            filas.append({"hora": hora, "estados": estados})
        calendario_cancha_filas.append((cancha, filas))

    context = {
        "canchas": canchas,
        "fechas_semana": fechas_semana,
        "horas": horas,
        "calendario_cancha_filas": calendario_cancha_filas,
        "fecha_actual": fecha_actual,
    }

    return render(request, "calendario_canchas.html", context)


@csrf_exempt
def reservar_cancha(request):
    if request.method == "POST":
        datos = obtener_datos_reserva_formulario(request, modo="jugador")
        reserva, error = ReservaService.crear_reserva(
            **datos, request=request, recepcionista_required=False
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Reserva creada exitosamente.")
    return redirect("calendario_canchas")


@csrf_exempt
def ajax_reservar_cancha(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            datos = {
                "jugador_nom": data.get("jugador_nom", "Anonimo"),
                "jugador_cognom": data.get("jugador_cognom", ""),
                "fecha": data.get("fecha"),
                "hora_inicio_str": data.get("hora"),
                "duracion": data.get("duracion", "60"),
                "type_cancha": data.get("tipo"),
                "cancha_numero": data.get("cancha"),
            }
            reserva, error = ReservaService.crear_reserva(
                **datos, request=request, recepcionista_required=False
            )
            if error:
                return JsonResponse({"success": False, "error": error})
            return JsonResponse(
                {
                    "success": True,
                    "estado": "ocupado",
                    "jugador_nom": reserva.jugador.nom,
                    "jugador_cognom": reserva.jugador.cognom,
                }
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Método no permitido"})


def crear_reserva(request):
    if request.method == "POST":
        datos = obtener_datos_reserva_formulario(request, modo="jugador")
        reserva, error = ReservaService.crear_reserva(
            **datos, request=request, recepcionista_required=True
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Reserva creada exitosamente.")
    return redirect("calendario_canchas")


def obtener_tarifa_para_reserva(fecha, hora_inicio, hora_fin):
    # fecha: date, hora_inicio/hora_fin: time
    dia_semana = fecha.weekday()  # 0=Lunes
    # Buscar tarifa que cubra el rango horario
    tarifa = (
        Tarifa.objects.filter(
            dia_semana=dia_semana, hora_inicio__lte=hora_inicio, hora_fin__gte=hora_fin
        )
        .order_by("hora_inicio")
        .first()
    )
    return tarifa


def calcular_hora_fin(hora_inicio, duracion):
    if duracion == "30":
        return (
            datetime.combine(datetime.min, hora_inicio) + timedelta(minutes=30)
        ).time()
    elif duracion == "60":
        return (datetime.combine(datetime.min, hora_inicio) + timedelta(hours=1)).time()
    elif duracion == "90":
        return (
            datetime.combine(datetime.min, hora_inicio) + timedelta(hours=1, minutes=30)
        ).time()
    else:
        return (
            datetime.combine(datetime.min, hora_inicio) + timedelta(minutes=30)
        ).time()


def obtener_datos_reserva_formulario(request, modo="recepcionista"):
    """Extrae y valida los datos del formulario para crear una reserva."""
    if modo == "recepcionista":
        jugador_select = request.POST.get("jugador_select")
        if jugador_select:
            partes = jugador_select.split("|", 1)
            jugador_nom = partes[0].strip()
            jugador_cognom = partes[1].strip() if len(partes) > 1 else ""
        else:
            jugador_nom = request.POST.get("jugador_nom", "").strip()
            jugador_cognom = request.POST.get("jugador_cognom", "").strip()
        fecha = request.POST.get("fecha-2")
        hora_inicio_str = request.POST.get("horaInici")
        duracion = request.POST.get("horaFinalitzacio")
        type_cancha = request.POST.get("Pista")
        cancha_numero = request.POST.get("cancha_numero")
    else:
        # Para modo jugador (crear_reserva y reservar_cancha)
        jugador_nom = request.POST.get("jugador_nom", "").strip()
        jugador_cognom = request.POST.get("jugador_cognom", "").strip()
        fecha = request.POST.get("fecha")
        hora_inicio_str = request.POST.get("hora_inicio")
        duracion = request.POST.get("duracion")
        type_cancha = request.POST.get("cancha_tipo")
        cancha_numero = request.POST.get("cancha_id")
    return {
        "jugador_nom": jugador_nom,
        "jugador_cognom": jugador_cognom,
        "fecha": fecha,
        "hora_inicio_str": hora_inicio_str,
        "duracion": duracion,
        "type_cancha": type_cancha,
        "cancha_numero": cancha_numero,
    }


# Lista de ventas
from django.contrib.auth.decorators import login_required


@login_required
def ventas_lista(request):
    ventas = Venta.objects.prefetch_related("detalles", "jugador").order_by("-fecha")
    return render(request, "ventas_lista.html", {"ventas": ventas})


# Registrar nueva venta
@login_required
def venta_nueva(request):
    VentaDetalleFormSet = formset_factory(VentaDetalleForm, extra=3)
    if request.method == "POST":
        venta_form = VentaForm(request.POST)
        detalle_forms = VentaDetalleFormSet(request.POST)
        errores = []
        detalles_validos = []
        total = 0
        detalles_completos = False
        if venta_form.is_valid() and detalle_forms.is_valid():
            for form in detalle_forms:
                producto = form.cleaned_data.get("producto")
                cantidad = form.cleaned_data.get("cantidad")
                if producto or cantidad:
                    detalles_completos = True
                if producto and cantidad:
                    if cantidad <= 0:
                        errores.append(
                            f"La cantidad del producto '{producto}' debe ser mayor a cero."
                        )
                        continue
                    if producto.stock_actual < cantidad:
                        errores.append(
                            f"Stock insuficiente para '{producto}'. Disponible: {producto.stock_actual}, solicitado: {cantidad}."
                        )
                        continue
                    detalles_validos.append(form)
                    total += cantidad * form.cleaned_data.get("precio_unitario", 0)
            if not detalles_completos:
                errores.append(
                    "Debes completar al menos un producto y cantidad para registrar la venta."
                )
            elif not detalles_validos:
                errores.append(
                    "Debes ingresar al menos un producto con cantidad válida y stock suficiente."
                )
            if errores:
                for error in errores:
                    messages.error(request, error)
            else:
                with transaction.atomic():
                    venta = venta_form.save(commit=False)
                    venta.total = total
                    venta.save()
                    for form in detalles_validos:
                        detalle = form.save(commit=False)
                        detalle.venta = venta
                        detalle.save()
                messages.success(request, "Venta registrada correctamente.")
                return redirect("ventas_lista")
        else:
            # Mostrar errores de validación de los formularios
            if not venta_form.is_valid():
                for field, errors in venta_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            if not detalle_forms.is_valid():
                for form in detalle_forms:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Detalle - {field}: {error}")
    else:
        venta_form = VentaForm()
        detalle_forms = VentaDetalleFormSet()
    return render(
        request,
        "venta_nueva.html",
        {"venta_form": venta_form, "detalle_forms": detalle_forms},
    )


# Lista de stock
@login_required
def stock_lista(request):
    productos = Producto.objects.all().order_by("nombre")
    return render(request, "stock_lista.html", {"productos": productos})


# Registrar ingreso de stock
@login_required
def ingreso_stock(request):
    if request.method == "POST":
        form = IngresoStockForm(request.POST)
        if form.is_valid():
            cantidad = form.cleaned_data.get("cantidad")
            precio_compra = form.cleaned_data.get("precio_compra")
            errores = []
            if cantidad is None or cantidad <= 0:
                errores.append("La cantidad debe ser mayor a cero.")
            if precio_compra is None or precio_compra <= 0:
                errores.append("El precio de compra debe ser mayor a cero.")
            if errores:
                for error in errores:
                    messages.error(request, error)
            else:
                form.save()
                messages.success(request, "Ingreso de stock registrado correctamente.")
                return redirect("stock_lista")
    else:
        form = IngresoStockForm()
    return render(request, "ingreso_stock.html", {"form": form})


@login_required
def resumen_caja(request):
    hoy = timezone.localdate()
    ventas = Venta.objects.filter(fecha__date=hoy)
    total_ventas = ventas.aggregate(total=Sum("total"))["total"] or 0
    detalles = VentaDetalle.objects.filter(venta__in=ventas)
    productos_vendidos = (
        detalles.values("producto__nombre")
        .annotate(cantidad=Sum("cantidad"), total=Sum("precio_unitario"))
        .order_by("-cantidad")
    )
    return render(
        request,
        "resumen_caja.html",
        {
            "ventas": ventas,
            "total_ventas": total_ventas,
            "productos_vendidos": productos_vendidos,
            "fecha": hoy,
        },
    )

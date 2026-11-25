import hashlib
import json
import logging
import secrets
from datetime import timedelta

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.cuentas.models import Rol, Usuario
from apps.instituciones.models import Institucion

from .models import TokenRecuperacion


def datos_usuario(user):
    institucion = None
    if user.institucion_id:
        institucion = Institucion.objects.filter(pk=user.institucion_id).values(
            "id", "nombre", "estado"
        ).first()
    return {
        "id": user.pk,
        "correo": user.correo,
        "nombres": user.nombres,
        "apellidos": user.apellidos,
        "rol": user.rol,
        "institucion_id": user.institucion_id,
        "institucion": institucion,
    }


def _registrar_auditoria(user, tipo, resultado, detalle, categoria=EventoAuditoria.Categoria.TECNICA):
    institucion_id = user.institucion_id if user and user.institucion_id else EventoAuditoria._meta.get_field(
        "institucion_id"
    ).default
    actor_id = user.pk if user else None
    with transaction.atomic():
        ultimo = (
            EventoAuditoria.objects.select_for_update()
            .filter(institucion_id=institucion_id)
            .order_by("-secuencia")
            .first()
        )
        secuencia = (ultimo.secuencia + 1) if ultimo else 1
        anterior = ultimo.hash_propio if ultimo else "0" * 64
        contenido = json.dumps(
            {
                "institucion_id": institucion_id,
                "secuencia": secuencia,
                "categoria": categoria,
                "tipo": tipo,
                "actor_id": actor_id,
                "resultado": resultado,
                "detalle": detalle,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        propio = hashlib.sha256((anterior + contenido).encode("utf-8")).hexdigest()
        return EventoAuditoria.objects.create(
            institucion_id=institucion_id,
            secuencia=secuencia,
            categoria=categoria,
            tipo=tipo,
            actor_id=actor_id,
            resultado=resultado,
            detalle=json.dumps(detalle, ensure_ascii=False),
            fecha=timezone.now(),
            hash_anterior=anterior,
            hash_propio=propio,
        )


def _notificar_bloqueo_de_cuenta(user):
    """Alerta roja al ADMIN_SISTEMA. Un fallo aquí nunca debe impedir responder el intento de ingreso."""
    try:
        # Importes locales: evitan ciclos entre módulos al cargar
        from apps.chat.services import GRUPO_ADMIN_SISTEMA, crear_y_emitir_notificacion
        from apps.cuentas.services import ids_usuarios_por_rol

        crear_y_emitir_notificacion(
            destinatario_ids=ids_usuarios_por_rol(Rol.ADMIN_SISTEMA),
            grupo=GRUPO_ADMIN_SISTEMA,
            institucion_id=None,
            tipo="CUENTA_BLOQUEADA",
            titulo="Cuenta bloqueada por intentos fallidos",
            mensaje=f"La cuenta {user.correo} se bloqueó 15 minutos tras 3 intentos fallidos de ingreso.",
            referencia=user.pk,
            subevento="seguridad.anomalia",
        )
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("No se pudo notificar el bloqueo de la cuenta.")


MENSAJES_INSTITUCION_NO_ACTIVA = {
    Institucion.Estado.PENDIENTE_APROBACION: (
        "Tu solicitud de registro está pendiente de aprobación. Te avisaremos por correo cuando "
        "el Administrador del Sistema la revise."
    ),
    Institucion.Estado.RECHAZADA: (
        "La solicitud de registro de tu institución no fue aprobada. Revisa el correo con el motivo."
    ),
    Institucion.Estado.SUSPENDIDA: "Tu institución está suspendida. Comunícate con el equipo de Retiro Seguro.",
}


def autenticar(request, correo, contrasena):
    user = Usuario._base_manager.filter(correo__iexact=correo).first()
    ahora = timezone.now()
    if user and user.bloqueado_hasta and user.bloqueado_hasta > ahora:
        _registrar_auditoria(user, "INGRESO_BLOQUEADO", "FALLO", {"motivo": "bloqueo_temporal"})
        return None, "La cuenta está bloqueada temporalmente."
    if user and user.estado in (Usuario.Estado.BLOQUEADA, Usuario.Estado.SUSPENDIDA):
        _registrar_auditoria(user, "INGRESO_RECHAZADO", "FALLO", {"motivo": user.estado})
        return None, "La cuenta no está disponible."
    autenticado = authenticate(request, username=correo, password=contrasena)
    if autenticado is None:
        if user:
            user.intentos_fallidos += 1
            campos = ["intentos_fallidos"]
            if user.intentos_fallidos >= 3:
                user.bloqueado_hasta = ahora + timedelta(minutes=15)
                campos.append("bloqueado_hasta")
            user.save(update_fields=campos)
            _registrar_auditoria(
                user,
                "INTENTO_INGRESO_FALLIDO",
                "FALLO",
                {"intentos_fallidos": user.intentos_fallidos},
            )
            if user.intentos_fallidos >= 3:
                _notificar_bloqueo_de_cuenta(user)
        return None, "Credenciales inválidas."

    # El estado de la institución se informa solo a quien ya demostró conocer la contraseña:
    # así no se revela a terceros si un correo está registrado ni en qué estado está su colegio.
    if autenticado.rol == Rol.ADMIN_ESCOLAR and autenticado.institucion_id:
        institucion = Institucion.objects.filter(pk=autenticado.institucion_id).only("estado").first()
        if not institucion or institucion.estado != Institucion.Estado.ACTIVA:
            estado = institucion.estado if institucion else None
            _registrar_auditoria(
                autenticado, "INGRESO_RECHAZADO", "FALLO", {"motivo": "institucion_no_activa", "estado": estado}
            )
            return None, MENSAJES_INSTITUCION_NO_ACTIVA.get(estado, "La institución todavía no está activa.")

    # TOTP/2FA reservado para el 2.º bimestre. El 1.er bimestre usa solo correo y contraseña.
    # codigo_totp = request.data.get("codigo_totp", "")
    # if autenticado.totp_secreto_cifrado:
    #     if not codigo_totp:
    #         return None, "La cuenta requiere un código TOTP."
    #     try:
    #         secreto = Fernet(settings.FIELD_ENCRYPTION_KEY.encode("utf-8")).decrypt(
    #             autenticado.totp_secreto_cifrado.encode("utf-8")
    #         ).decode("utf-8")
    #     except (InvalidToken, ValueError):
    #         return None, "No se pudo validar la configuración TOTP."
    #     if not pyotp.TOTP(secreto).verify(codigo_totp):
    #         _registrar_auditoria(autenticado, "INTENTO_TOTP_FALLIDO", "FALLO", {})
    #         return None, "El código TOTP no es válido."

    login(request, autenticado)
    autenticado.intentos_fallidos = 0
    autenticado.bloqueado_hasta = None
    autenticado.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
    _registrar_auditoria(autenticado, "INGRESO_EXITOSO", "EXITO", {})
    return autenticado, None


def cerrar_sesion(request):
    user = request.user
    logout(request)
    _registrar_auditoria(user, "CIERRE_SESION", "EXITO", {})


def cambiar_contrasena(user, contrasena_actual, nueva_contrasena):
    if not user.contrasena_temporal:
        raise ValueError("La cuenta no requiere cambio de contraseña temporal.")
    if not user.check_password(contrasena_actual):
        raise ValueError("La contraseña actual no es válida.")
    user.set_password(nueva_contrasena)
    user.contrasena_temporal = False
    user.expira_temporal = None
    user.save(update_fields=["password", "contrasena_temporal", "expira_temporal"])
    _registrar_auditoria(user, "CAMBIO_CONTRASENA", "EXITO", {})


def solicitar_recuperacion(correo):
    user = Usuario._base_manager.filter(correo__iexact=correo).first()
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    registro = TokenRecuperacion.objects.create(
        usuario_id=user.pk,
        hash_token=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expira_en=timezone.now() + timedelta(minutes=30),
    )
    _registrar_auditoria(user, "SOLICITUD_RECUPERACION", "EXITO", {})
    enlace = f"https://localhost:8443/autenticacion/restablecer/?token={token}"
    try:
        send_mail(
            subject="Recuperación de contraseña - Retiro Seguro",
            message=(
                f"Hola {user.nombres},\n\n"
                "Solicitaste recuperar tu contraseña.\n"
                f"Usa este enlace antes de 30 minutos:\n{enlace}\n\n"
                "Si no solicitaste este cambio, ignora este correo."
            ),
            from_email=None,
            recipient_list=[user.correo],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001
        registro.delete()
        logging.getLogger(__name__).exception(
            "No se pudo enviar el correo de recuperación para el usuario %s.",
            user.pk,
        )
        return None
    return None


def confirmar_recuperacion(token, nueva_contrasena):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    registro = TokenRecuperacion.objects.filter(
        hash_token=token_hash, usado_en__isnull=True, expira_en__gt=timezone.now()
    ).first()
    if not registro:
        raise ValueError("El token es inválido o expiró.")
    with transaction.atomic():
        usuario = Usuario._base_manager.select_for_update().get(pk=registro.usuario_id)
        usuario.set_password(nueva_contrasena)
        usuario.contrasena_temporal = False
        usuario.expira_temporal = None
        usuario.save(update_fields=["password", "contrasena_temporal", "expira_temporal"])
        registro.usado_en = timezone.now()
        registro.save(update_fields=["usado_en"])
    _registrar_auditoria(usuario, "RECUPERACION_CONTRASENA", "EXITO", {})

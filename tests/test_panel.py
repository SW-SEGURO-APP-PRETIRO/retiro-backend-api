import pytest
from django.test import Client
from apps.cuentas.models import Usuario
from apps.instituciones.models import Institucion

@pytest.fixture
def colegio(db):
    return Institucion.objects.create(nombre="Colegio de prueba", ruc="1790000000001", correo="colegio@example.test", estado="ACTIVA")

@pytest.fixture
def admin(colegio):
    return Usuario.objects.create(correo="admin@example.test", cedula="1700000001", nombres="Ana", apellidos="Prueba", rol="ADMIN_ESCOLAR", institucion_id=colegio.pk, estado="ACTIVA")

@pytest.mark.django_db
def test_login_publico_emite_csrf(client):
    response = client.get("/autenticacion/ingresar/")
    assert response.status_code == 200
    assert "csrftoken" in response.cookies
    assert b"codigo_totp" in response.content


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("rol", "institucion_id"),
    [
        ("ADMIN_ESCOLAR", 1),
        ("ADMIN_SISTEMA", None),
    ],
)
def test_login_api_reconoce_ambos_administradores(client, colegio, rol, institucion_id):
    usuario = Usuario.objects.create(
        correo=f"{rol.lower()}@login.test",
        cedula="1700000088" if rol == "ADMIN_ESCOLAR" else "1700000089",
        nombres="Administrador",
        apellidos="Prueba",
        rol=rol,
        institucion_id=colegio.pk if rol == "ADMIN_ESCOLAR" else None,
        estado="ACTIVA",
    )
    usuario.set_password("ClaveSegura#2026")
    usuario.save()

    response = client.post(
        "/api/v1/autenticacion/ingresar/",
        {"correo": usuario.correo, "contrasena": "ClaveSegura#2026"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["datos"]["usuario"]["rol"] == rol

def test_anonimo_no_ve_panel(client):
    response = client.get("/escolar/")
    assert response.status_code == 302
    assert "/autenticacion/ingresar/" in response.url

@pytest.mark.django_db
@pytest.mark.parametrize("pantalla", ["", "estudiantes/", "padres/", "guardias/", "asignaciones/", "cuidadores/", "cursos/", "puertas/", "chat/", "institucion/", "bitacora/", "notificaciones/"])
def test_pantallas_escolares(client, admin, pantalla):
    client.force_login(admin)
    response = client.get("/escolar/" + pantalla)
    assert response.status_code == 200
    assert b"Retiro Seguro" in response.content
    assert "no-store" in response.headers["Cache-Control"]

@pytest.mark.django_db
def test_roles_moviles_no_acceden_al_panel_web(client, colegio):
    guardia = Usuario.objects.create(
        correo="guardia.portal@example.test",
        cedula="1700000011",
        nombres="Jorge",
        apellidos="Guardia",
        rol="GUARDIA",
        institucion_id=colegio.pk,
        estado="ACTIVA",
    )
    cuidador = Usuario.objects.create(
        correo="cuidador.portal@example.test",
        cedula="1700000012",
        nombres="Ricardo",
        apellidos="Cuidador",
        rol="CUIDADOR_FIJO",
        institucion_id=colegio.pk,
        estado="ACTIVA",
    )
    client.force_login(guardia)
    response = client.get("/escolar/")
    assert response.status_code == 403
    assert b"Acceso exclusivo para administraci" in response.content

    client.force_login(cuidador)
    assert client.get("/escolar/").status_code == 403


@pytest.mark.django_db
def test_padre_no_accede_al_panel_web_pero_si_a_api_movil(client, colegio):
    padre = Usuario.objects.create(
        correo="padre.portal@example.test",
        cedula="1700000010",
        nombres="Carlos",
        apellidos="Representante",
        rol="PADRE",
        institucion_id=colegio.pk,
        estado="ACTIVA",
    )
    client.force_login(padre)
    assert client.get("/escolar/").status_code == 403
    assert client.get("/api/v1/cuidadores/").status_code == 200

@pytest.mark.django_db
def test_clave_temporal_redirige(client, admin):
    admin.contrasena_temporal = True
    admin.save()
    client.force_login(admin)
    assert client.get("/escolar/").url == "/autenticacion/cambiar-contrasena/"

@pytest.mark.django_db
def test_usuarios_ajenos_no_se_listan_ni_consultan(client, admin, colegio):
    otra = Institucion.objects.create(nombre="Otra", ruc="1790000000002", correo="otra@example.test", estado="ACTIVA")
    ajeno = Usuario.objects.create(correo="ajeno@example.test", cedula="1700000002", rol="PADRE", institucion_id=otra.pk)
    client.force_login(admin)
    datos = client.get("/api/v1/cuentas/usuarios/").json()["datos"]
    assert ajeno.pk not in [u["id"] for u in datos]
    assert client.get(f"/api/v1/cuentas/usuarios/{ajeno.pk}/").status_code == 404

@pytest.mark.django_db
def test_institucion_suspendida_no_ve_panel(client, admin, colegio):
    colegio.estado = "SUSPENDIDA"
    colegio.save()
    client.force_login(admin)
    assert client.get("/escolar/").status_code == 403

@pytest.mark.django_db
def test_crud_estudiante_via_api_real_y_bitacora(client, admin, colegio):
    from apps.instituciones.models import Curso
    from shared.tenancy.context import contexto_institucion
    with contexto_institucion(colegio.pk):
        curso = Curso.objects.create(institucion_id=colegio.pk, nombre="3ro A", hora_salida="13:00")
    client.force_login(admin)
    response = client.post("/api/v1/cuentas/estudiantes/", {"nombres":"María", "apellidos":"Prueba", "cedula":"1711000016", "fecha_nacimiento":"2017-03-10", "curso_id":curso.pk, "estado":"ACTIVO", "hora_salida_especial":None}, content_type="application/json")
    assert response.status_code == 201, response.content
    pk = response.json()["datos"]["id"]
    assert client.patch(f"/api/v1/cuentas/estudiantes/{pk}/", {"nombres":"María Elena"}, content_type="application/json").status_code == 200
    assert client.get(f"/api/v1/cuentas/estudiantes/{pk}/").json()["datos"]["nombres"] == "María Elena"
    eventos = client.get("/api/v1/auditoria/operativa/").json()["datos"]["resultados"]
    assert {"ESTUDIANTE_CREADO", "ESTUDIANTE_ACTUALIZADO"} <= {e["tipo"] for e in eventos}
    assert client.delete(f"/api/v1/cuentas/estudiantes/{pk}/").status_code == 200
    assert client.get(f"/api/v1/cuentas/estudiantes/{pk}/").status_code == 404

@pytest.mark.django_db
def test_mutacion_sin_csrf_se_rechaza(admin):
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin)
    assert client.post("/api/v1/cuentas/estudiantes/", {}, content_type="application/json").status_code == 403

@pytest.mark.django_db
def test_bitacora_no_admite_escritura(client, admin):
    client.force_login(admin)
    assert client.post("/api/v1/auditoria/operativa/", {}, content_type="application/json").status_code == 405

@pytest.mark.django_db
def test_html_escapa_nombre_de_usuario(client, admin):
    admin.nombres = '<script>alert("xss")</script>'
    admin.save()
    client.force_login(admin)
    response = client.get("/escolar/")
    assert b'<script>alert(' not in response.content
    assert b'&lt;script&gt;' in response.content


@pytest.mark.django_db
def test_admin_escolar_puede_activar_y_desactivar_padres(client, admin, colegio):
    padre = Usuario.objects.create(
        correo="padre.estado@example.test",
        cedula="1711000017",
        nombres="Laura",
        apellidos="Estado",
        rol="PADRE",
        institucion_id=colegio.pk,
        estado="ACTIVA",
    )
    client.force_login(admin)

    bloquear = client.post(f"/api/v1/cuentas/usuarios/{padre.pk}/bloquear/")
    assert bloquear.status_code == 200
    padre.refresh_from_db()
    assert padre.estado == "BLOQUEADA"

    activar = client.post(f"/api/v1/cuentas/usuarios/{padre.pk}/desbloquear/")
    assert activar.status_code == 200
    padre.refresh_from_db()
    assert padre.estado == "ACTIVA"


@pytest.mark.django_db
def test_admin_escolar_puede_rechazar_solicitud_pendiente(client, admin, colegio):
    from apps.cuentas.models import Estudiante, Rol
    from apps.cuidadores.models import AutorizacionCuidador, Cuidador
    from apps.instituciones.models import Curso
    from shared.tenancy.context import contexto_institucion

    padre = Usuario.objects.create(
        correo="padre.rechazo@example.test",
        cedula="1711000018",
        nombres="Carlos",
        apellidos="Rechazo",
        rol=Rol.PADRE,
        institucion_id=colegio.pk,
        estado="ACTIVA",
    )
    with contexto_institucion(colegio.pk):
        curso = Curso.objects.create(
            institucion_id=colegio.pk,
            nombre="5to A",
            hora_salida="13:30",
        )
        estudiante = Estudiante.objects.create(
            institucion_id=colegio.pk,
            cedula="1711000019",
            nombres="Ana",
            apellidos="Estudiante",
            fecha_nacimiento="2016-04-12",
            curso_id=curso.pk,
        )
        cuidador = Cuidador.objects.create(
            institucion_id=colegio.pk,
            tipo=Cuidador.Tipo.FIJO,
            cedula="1711000020",
            nombres="Lucía",
            apellidos="Mendoza",
            correo="lucia.rechazo@example.test",
        )
        autorizacion = AutorizacionCuidador.objects.create(
            institucion_id=colegio.pk,
            cuidador=cuidador,
            estudiante_id=estudiante.pk,
            solicitada_por_id=padre.pk,
            estado=AutorizacionCuidador.Estado.SOLICITADO,
        )

    client.force_login(admin)
    response = client.post(
        f"/api/v1/cuidadores/autorizaciones/{autorizacion.pk}/rechazar/",
        {"motivo": "La identidad no coincide con el registro."},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    autorizacion.refresh_from_db()
    assert autorizacion.estado == "RECHAZADO"
    assert autorizacion.rechazada_por_id == admin.pk
    assert autorizacion.motivo_rechazo == "La identidad no coincide con el registro."


@pytest.mark.django_db
def test_flujo_movil_padre_solicita_y_recibe_aprobacion(client, admin, colegio, monkeypatch):
    from apps.chat.models import Notificacion
    from apps.cuentas.models import Estudiante, RelacionPadreEstudiante, Rol
    from apps.cuidadores.models import AutorizacionCuidador, Cuidador
    from apps.instituciones.models import Curso
    from shared.tenancy.context import contexto_institucion

    padre = Usuario.objects.create(
        correo="padre.movilejemplo@example.test",
        cedula="1711000022",
        nombres="Carmen",
        apellidos="Padre",
        rol=Rol.PADRE,
        institucion_id=colegio.pk,
        estado="ACTIVA",
    )
    with contexto_institucion(colegio.pk):
        curso = Curso.objects.create(institucion_id=colegio.pk, nombre="6to API", hora_salida="13:00")
        estudiante = Estudiante.objects.create(
            institucion_id=colegio.pk,
            cedula="1711000023",
            nombres="Luis",
            apellidos="Estudiante",
            fecha_nacimiento="2015-01-10",
            curso_id=curso.pk,
        )
        RelacionPadreEstudiante.objects.create(
            institucion_id=colegio.pk,
            padre=padre,
            estudiante=estudiante,
            vigente=True,
        )

    client.force_login(padre)
    crear = client.post(
        "/api/v1/cuidadores/",
        {
            "tipo": "FIJO",
            "cedula": "1711000024",
            "nombres": "Andrea",
            "apellidos": "Móvil",
            "telefono": "0991112233",
            "correo": "andrea.movilejemplo@example.test",
        },
        content_type="application/json",
    )
    assert crear.status_code == 201, crear.content
    cuidador_id = crear.json()["datos"]["id"]

    solicitar = client.post(
        f"/api/v1/cuidadores/{cuidador_id}/solicitar-autorizacion/",
        {"estudiante_id": estudiante.pk},
        content_type="application/json",
    )
    assert solicitar.status_code == 201, solicitar.content
    autorizacion_id = solicitar.json()["datos"]["id"]

    pendiente_admin = client.get("/api/v1/cuidadores/autorizaciones/")
    assert pendiente_admin.status_code == 200

    monkeypatch.setattr(
        "apps.cuidadores.services.send_mail",
        lambda **kwargs: 1,
    )
    client.force_login(admin)
    aprobar = client.post(
        f"/api/v1/cuidadores/autorizaciones/{autorizacion_id}/aprobar/",
        {},
        content_type="application/json",
    )
    assert aprobar.status_code == 200, aprobar.content

    aprobacion = Notificacion._base_manager.filter(
        institucion_id=colegio.pk,
        destinatario_id=padre.pk,
        tipo="ACCESO_EMITIDO",
    ).first()
    assert aprobacion is not None
    assert "aprobada" in aprobacion.titulo.lower() or "aprobada" in aprobacion.mensaje.lower()

    autorizacion = AutorizacionCuidador._base_manager.get(pk=autorizacion_id)
    assert autorizacion.estado == "ACCESO_EMITIDO"


@pytest.fixture
def admin_sistema(db):
    return Usuario.objects.create(
        correo="admin.sistema@example.test",
        cedula="1700000099",
        nombres="Admin",
        apellidos="Sistema",
        rol="ADMIN_SISTEMA",
        institucion_id=None,
        estado="ACTIVA",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "pantalla",
    [
        "",
        "instituciones/",
        "pendientes/",
        "administradores/",
        "cuentas/",
        "seguridad/",
        "bitacora/",
        "integridad/",
        "chat/",
        "notificaciones/",
    ],
)
def test_pantallas_admin_sistema(client, admin_sistema, pantalla):
    client.force_login(admin_sistema)
    response = client.get("/sistema/" + pantalla)
    assert response.status_code == 200
    assert b"Administraci\xc3\xb3n del sistema" in response.content
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "modo",
    ["ingresar/", "recuperar/", "restablecer/"],
)
def test_rutas_antiguas_auth_sistema_redirigen_a_login_unico(client, modo):
    response = client.get("/sistema/autenticacion/" + modo)
    assert response.status_code == 302
    assert response.url == "/autenticacion/" + modo


def test_anonimo_no_ve_panel_sistema(client):
    response = client.get("/sistema/")
    assert response.status_code == 302
    assert "/autenticacion/ingresar/" in response.url


@pytest.mark.django_db
def test_clave_temporal_admin_sistema_redirige_a_cambio_unico(client, admin_sistema):
    admin_sistema.contrasena_temporal = True
    admin_sistema.save()
    client.force_login(admin_sistema)
    assert client.get("/sistema/").url == "/autenticacion/cambiar-contrasena/"


@pytest.mark.django_db
def test_raiz_redirige_segun_rol(client, admin, admin_sistema):
    client.force_login(admin_sistema)
    assert client.get("/").url == "/sistema/"
    client.force_login(admin)
    assert client.get("/").status_code == 200


@pytest.mark.django_db
def test_admin_escolar_no_ve_panel_sistema_y_viceversa(client, admin, admin_sistema):
    client.force_login(admin)
    assert client.get("/sistema/").status_code == 403
    client.force_login(admin_sistema)
    assert client.get("/escolar/").status_code == 403



@pytest.mark.django_db
def test_admin_sistema_no_opera_entidades_escolares(client, admin_sistema, colegio):
    client.force_login(admin_sistema)
    assert client.get("/api/v1/cuentas/estudiantes/").status_code == 403
    assert client.get("/api/v1/cuentas/relaciones-padre-estudiante/").status_code == 403
    assert client.get("/api/v1/instituciones/cursos/").status_code == 403
    assert client.get("/api/v1/instituciones/puertas/").status_code == 403
    assert client.get("/api/v1/cuidadores/autorizaciones/").status_code == 403


@pytest.mark.django_db
def test_admin_sistema_lista_aprueba_rechaza_suspende_y_reactiva_instituciones(
    client, admin_sistema
):
    inst = Institucion.objects.create(
        nombre="Colegio Pendiente",
        ruc="1790000000019",
        correo="pendiente@example.test",
        direccion="Quito",
        telefono="022000000",
        responsable="Rector",
        estado="PENDIENTE_APROBACION",
    )
    admin_col = Usuario.objects.create(
        correo="rector@example.test",
        cedula="1711000021",
        nombres="Rector",
        apellidos="Colegio",
        rol="ADMIN_ESCOLAR",
        institucion_id=inst.pk,
        estado="PENDIENTE",
    )
    client.force_login(admin_sistema)

    # Listar todas las instituciones
    listado = client.get("/api/v1/instituciones/")
    assert listado.status_code == 200
    assert inst.pk in [i["id"] for i in listado.json()["datos"]]

    # Rechazo sin motivo falla
    sin_motivo = client.post(
        f"/api/v1/instituciones/{inst.pk}/aprobar/",
        {"aprobada": False, "motivo": ""},
        content_type="application/json",
    )
    assert sin_motivo.status_code == 400

    # Aprobar activa institución y su admin escolar
    aprobar = client.post(
        f"/api/v1/instituciones/{inst.pk}/aprobar/",
        {"aprobada": True, "motivo": ""},
        content_type="application/json",
    )
    assert aprobar.status_code == 200
    inst.refresh_from_db()
    admin_col.refresh_from_db()
    assert inst.estado == "ACTIVA"
    assert admin_col.estado == "ACTIVA"

    # Suspender institución activa
    suspender = client.post(
        f"/api/v1/instituciones/{inst.pk}/suspender/",
        {"motivo": "Mantenimiento de convenio"},
        content_type="application/json",
    )
    assert suspender.status_code == 200
    inst.refresh_from_db()
    assert inst.estado == "SUSPENDIDA"
    assert inst.motivo_estado == "Mantenimiento de convenio"

    # Reactivar institución suspendida
    reactivar = client.post(
        f"/api/v1/instituciones/{inst.pk}/reactivar/",
        {},
        content_type="application/json",
    )
    assert reactivar.status_code == 200
    inst.refresh_from_db()
    assert inst.estado == "ACTIVA"
    assert inst.motivo_estado == ""


@pytest.mark.django_db
def test_chat_salas_y_mensajes_en_panel_escolar_y_sistema(client, admin, admin_sistema, colegio):
    padre = Usuario.objects.create(
        correo="padre.chat@example.test",
        cedula="1711000033",
        nombres="Elena",
        apellidos="Padre",
        rol="PADRE",
        institucion_id=colegio.pk,
        estado="ACTIVA",
    )

    # Padre entra directamente a la sala general de su colegio y envía mensaje
    client.force_login(padre)
    general_padre = client.get("/api/v1/chat/general/")
    assert general_padre.status_code == 200
    sala_general_id = general_padre.json()["datos"]["sala"]["id"]

    envio = client.post(
        "/api/v1/chat/general/",
        {"sala_id": sala_general_id, "contenido": "Buenos días, consulta sobre horario de retiro."},
        content_type="application/json",
    )
    assert envio.status_code == 201

    # Admin escolar lee el mensaje en la sala general y responde
    client.force_login(admin)
    mensajes_admin = client.get("/api/v1/chat/general/")
    assert mensajes_admin.status_code == 200
    assert mensajes_admin.json()["datos"]["mensajes"][0]["contenido"] == "Buenos días, consulta sobre horario de retiro."

    resp_admin = client.post(
        "/api/v1/chat/general/",
        {"sala_id": sala_general_id, "contenido": "El horario normal es 13:00."},
        content_type="application/json",
    )
    assert resp_admin.status_code == 201

    # Admin sistema puede escribir en la sala general de la institución
    client.force_login(admin_sistema)
    msg_sys = client.post(
        "/api/v1/chat/general/",
        {"sala_id": sala_general_id, "contenido": "Notificación de soporte técnico."},
        content_type="application/json",
    )
    assert msg_sys.status_code == 201




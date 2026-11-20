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

def test_anonimo_no_ve_panel(client):
    response = client.get("/escolar/")
    assert response.status_code == 302
    assert "/autenticacion/ingresar/" in response.url

@pytest.mark.django_db
@pytest.mark.parametrize("pantalla", ["", "estudiantes/", "padres/", "guardias/", "asignaciones/", "cuidadores/", "cursos/", "puertas/", "institucion/", "bitacora/", "notificaciones/"])
def test_pantallas_escolares(client, admin, pantalla):
    client.force_login(admin)
    response = client.get("/escolar/" + pantalla)
    assert response.status_code == 200
    assert b"Retiro Seguro" in response.content
    assert "no-store" in response.headers["Cache-Control"]

@pytest.mark.django_db
def test_otro_rol_no_ve_panel(client, admin):
    Usuario.objects.filter(pk=admin.pk).update(rol="PADRE")
    client.force_login(Usuario.objects.get(pk=admin.pk))
    assert client.get("/escolar/").status_code == 403

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

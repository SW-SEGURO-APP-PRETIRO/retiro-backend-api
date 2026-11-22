"""python scripts/preview_escolar.py [--prepare-only]. Solo escucha en loopback."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_preview"
import django  # noqa: E402
django.setup()
from django.core.management import call_command  # noqa: E402

def prepare():
    call_command("migrate", run_syncdb=True, verbosity=0)
    from seed_demo import sembrar
    sembrar("VistaEscolar#2026")
    from apps.cuentas.models import Estudiante, Usuario
    from apps.cuidadores.models import Cuidador, AutorizacionCuidador
    from apps.chat.models import Notificacion
    from apps.instituciones.models import Institucion
    from shared.tenancy.context import sin_filtro
    from django.utils import timezone
    from seed_demo import _cedula
    with sin_filtro():
        colegio = Institucion.objects.get(correo="administracion@ue-los-alisos.edu.ec")
        admin = Usuario.objects.get(correo=os.environ.get("DEMO_ADMIN_ESCOLAR_EMAIL", "maria.cardenas@ue-los-alisos.edu.ec"))
        admin_sistema = Usuario.objects.get(correo=os.environ.get("DEMO_ADMIN_SISTEMA_EMAIL", "admin.sistema@retiroseguro.test"))
        padre = Usuario.objects.get(correo=os.environ.get("DEMO_PADRE_EMAIL", "carolina.andrade@ejemplo.ec"))
        student = Estudiante.objects.filter(institucion_id=colegio.pk).first()
        cuidador, _ = Cuidador.objects.get_or_create(institucion_id=colegio.pk, cedula=_cedula("171600001"), defaults={"tipo":"FIJO", "nombres":"Lucía", "apellidos":"Mendoza Cevallos", "correo":"lucia.mendoza@ejemplo.ec", "telefono":"0990000000"})
        AutorizacionCuidador.objects.get_or_create(institucion_id=colegio.pk, cuidador=cuidador, estudiante_id=student.pk, defaults={"solicitada_por_id":padre.pk, "estado":"SOLICITADO", "solicitada_en":timezone.now(), "firma_hmac":"demo"})
        Notificacion.objects.get_or_create(institucion_id=colegio.pk, destinatario_id=admin.pk, tipo="SOLICITUD_CUIDADOR", defaults={"titulo":"Nueva solicitud de cuidador", "mensaje":"Una familia solicitó un nuevo acceso. Revisa la solicitud.", "referencia":cuidador.pk})
        from seed_demo import _ruc
        pendiente, _ = Institucion.objects.get_or_create(
            correo="rectorado@colegio-san-gabriel.edu.ec",
            defaults={
                "nombre": "Unidad Educativa San Gabriel del Valle",
                "ruc": _ruc("179300001"),
                "direccion": "Av. América y Mariana de Jesús, Quito",
                "telefono": "022450890",
                "responsable": "Dr. Esteban Patricio Villacreses",
                "estado": Institucion.Estado.PENDIENTE_APROBACION,
            },
        )
        if not Usuario.objects.filter(correo="esteban.villacreses@colegio-san-gabriel.edu.ec").exists():
            u_pend = Usuario.objects.crear_usuario(
                correo="esteban.villacreses@colegio-san-gabriel.edu.ec",
                password="VistaEscolar#2026",
                cedula=_cedula("171700001"),
                nombres="Esteban Patricio",
                apellidos="Villacreses",
                rol="ADMIN_ESCOLAR",
                institucion_id=pendiente.pk,
                estado="PENDIENTE",
            )
            u_pend.contrasena_temporal = True
            u_pend.save(update_fields=["contrasena_temporal"])
        Notificacion.objects.get_or_create(
            institucion_id=0,
            destinatario_id=admin_sistema.pk,
            tipo="INSTITUCION_PENDIENTE",
            defaults={
                "titulo": "Institución pendiente de aprobación",
                "mensaje": f"{pendiente.nombre} solicitó registrarse y espera su aprobación.",
                "referencia": str(pendiente.pk),
            },
        )
    print("Vista previa con datos ficticios (Ingreso único en http://127.0.0.1:8000/autenticacion/ingresar/):")
    print(f"  1. Admin Sistema (/sistema/) : {os.environ.get('DEMO_ADMIN_SISTEMA_EMAIL', 'admin.sistema@retiroseguro.test'):<36} | Clave: VistaEscolar#2026")
    print(f"  2. Admin Escolar (/escolar/) : {os.environ.get('DEMO_ADMIN_ESCOLAR_EMAIL', 'maria.cardenas@ue-los-alisos.edu.ec'):<36} | Clave: VistaEscolar#2026")
    print(f"  3. Padre Familia (/escolar/) : {os.environ.get('DEMO_PADRE_EMAIL', 'carolina.andrade@ejemplo.ec'):<36} | Clave: VistaEscolar#2026")
    print("  4. Guardia       (/escolar/) : jorge.herrera@ue-los-alisos.edu.ec  | Clave: VistaEscolar#2026")
    print("  5. Cuidador Fijo (/escolar/) : se registra desde el endpoint móvil")

if __name__ == "__main__":
    prepare()
    if "--prepare-only" not in sys.argv:
        call_command("runserver", "127.0.0.1:8000", use_reloader=False)

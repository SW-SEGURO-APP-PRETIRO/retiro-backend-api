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
        colegio = Institucion.objects.get(correo="contacto1@colegio1.test")
        admin = Usuario.objects.get(correo="admin1@colegio1.test")
        padre = Usuario.objects.get(correo="padre1@colegio1.test")
        student = Estudiante.objects.filter(institucion_id=colegio.pk).first()
        cuidador, _ = Cuidador.objects.get_or_create(institucion_id=colegio.pk, cedula=_cedula("171600001"), defaults={"tipo":"FIJO", "nombres":"Lucía", "apellidos":"Mendoza", "correo":"lucia.mendoza@example.test", "telefono":"0990000000"})
        AutorizacionCuidador.objects.get_or_create(institucion_id=colegio.pk, cuidador=cuidador, estudiante_id=student.pk, defaults={"solicitada_por_id":padre.pk, "estado":"SOLICITADO", "solicitada_en":timezone.now(), "firma_hmac":"demo"})
        Notificacion.objects.get_or_create(institucion_id=colegio.pk, destinatario_id=admin.pk, tipo="SOLICITUD_CUIDADOR", defaults={"titulo":"Nueva solicitud de cuidador", "mensaje":"Una familia solicitó un nuevo acceso. Revisa la solicitud.", "referencia":cuidador.pk})
    print("Vista previa con datos ficticios: http://127.0.0.1:8000/escolar/")
    print("Cuenta local: admin1@colegio1.test | Clave: VistaEscolar#2026")

if __name__ == "__main__":
    prepare()
    if "--prepare-only" not in sys.argv:
        call_command("runserver", "127.0.0.1:8000", use_reloader=False)

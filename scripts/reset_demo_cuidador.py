"""Elimina únicamente los datos creados para una demostración de cuidador fijo.

Uso:
  docker compose exec app python scripts/reset_demo_cuidador.py \
    --correo correo-del-cuidador-demo@example.test

No elimina instituciones, padres, administradores, estudiantes ni guardias.
"""
import argparse
import os
import sys
from pathlib import Path


def preparar_django():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "src"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--correo", required=True, help="Correo del cuidador fijo a eliminar")
    parser.add_argument("--institucion", type=int, default=None)
    args = parser.parse_args()

    from django.db import transaction

    from apps.autenticacion.models import TokenRecuperacion
    from apps.chat.models import Notificacion
    from apps.cuentas.models import Usuario
    from apps.cuidadores.models import AutorizacionCuidador, Cuidador
    from apps.retiros.models import PaseEstudiante, PaseQR, Retiro, SesionSalida
    from shared.tenancy.context import sin_filtro

    correo = args.correo.strip().lower()
    with sin_filtro(), transaction.atomic():
        cuidadores = Cuidador._base_manager.filter(correo__iexact=correo)
        if args.institucion:
            cuidadores = cuidadores.filter(institucion_id=args.institucion)
        cuidadores = list(cuidadores)

        cuidador_ids = [cuidador.pk for cuidador in cuidadores]
        inst_ids = {cuidador.institucion_id for cuidador in cuidadores}

        autorizaciones = AutorizacionCuidador._base_manager.filter(
            cuidador_id__in=cuidador_ids
        )
        autorizacion_ids = list(autorizaciones.values_list("pk", flat=True))

        for institucion_id in inst_ids:
            Retiro._base_manager.filter(
                institucion_id=institucion_id,
                pase__cuidador_id__in=cuidador_ids,
            ).delete()
            PaseEstudiante._base_manager.filter(
                institucion_id=institucion_id,
                pase__cuidador_id__in=cuidador_ids,
            ).delete()
            PaseQR._base_manager.filter(
                institucion_id=institucion_id,
                cuidador_id__in=cuidador_ids,
            ).delete()
            SesionSalida._base_manager.filter(
                institucion_id=institucion_id,
                cuidador_id__in=cuidador_ids,
            ).delete()

        referencias = [str(pk) for pk in [*cuidador_ids, *autorizacion_ids]]
        for institucion_id in inst_ids:
            Notificacion._base_manager.filter(
                institucion_id=institucion_id,
                referencia__in=referencias,
            ).delete()

        autorizaciones.delete()

        cuentas = Usuario.objects.filter(correo__iexact=correo)
        if args.institucion:
            cuentas = cuentas.filter(institucion_id=args.institucion)
        cuenta_ids = list(cuentas.values_list("pk", flat=True))
        if cuenta_ids:
            TokenRecuperacion.objects.filter(usuario_id__in=cuenta_ids).delete()
        cuentas_eliminadas = cuentas.count()
        cuentas.delete()

        cuidadores_eliminados = len(cuidadores)
        Cuidador._base_manager.filter(pk__in=cuidador_ids).delete()

    print(
        "Limpieza completada:",
        f"{cuidadores_eliminados} cuidador(es),",
        f"{len(autorizacion_ids)} autorización(es),",
        f"{cuentas_eliminadas} cuenta(s).",
    )


if __name__ == "__main__":
    preparar_django()
    main()

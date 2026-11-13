"""Datos FICTICIOS de demostración (Infraestructura y Base de Datos).

Crea 2 instituciones con sus cursos y puerta, los 5 roles, estudiantes y la relación padre-hijo.
Es idempotente: se puede ejecutar varias veces sin duplicar. Ningún dato es real.

Uso:  docker compose exec app python scripts/seed_demo.py
"""
import os
import sys
from datetime import date, time
from pathlib import Path


def _preparar_django():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()


def _cedula(base9: str) -> str:
    """Completa 9 dígitos con el verificador para obtener una cédula válida FICTICIA."""
    suma = 0
    for i, c in enumerate(base9):
        n = int(c) * (2 if i % 2 == 0 else 1)
        suma += n - 9 if n > 9 else n
    return base9 + str((10 - suma % 10) % 10)


def _ruc(base9: str) -> str:
    """RUC ficticio de sociedad privada (tercer dígito 9). Salta bases cuyo verificador sería 10."""
    coef = [4, 3, 2, 7, 6, 5, 4, 3, 2]
    n = int(base9)
    while True:
        base = f"{n:09d}"
        residuo = sum(int(d) * c for d, c in zip(base, coef)) % 11
        if residuo != 1:  # residuo 1 daría un verificador de dos dígitos (inválido)
            break
        n += 1
    dv = 0 if residuo == 0 else 11 - residuo
    return f"{base}{dv}001"


def sembrar(clave: str | None = None) -> dict:
    from django.utils import timezone

    from apps.cuentas.models import Estudiante, RelacionPadreEstudiante, Rol, Usuario
    from apps.instituciones.models import Curso, Institucion, Puerta
    from shared.tenancy.context import sin_filtro

    clave = clave or os.environ.get("SEED_PASSWORD", "ClaveDemo#2026")
    resumen = {}

    def usuario(correo, rol, inst, n, nombres, apellidos, **extra):
        u = Usuario.objects.filter(correo=correo).first()
        if u is None:
            u = Usuario.objects.crear_usuario(
                correo, clave,
                cedula=_cedula(f"17{inst.id if inst else 0}{n:02d}0001"),
                nombres=nombres, apellidos=apellidos, rol=rol,
                institucion_id=inst.id if inst else None,
                estado=Usuario.Estado.ACTIVA, **extra,
            )
        resumen[correo] = rol
        return u

    with sin_filtro():  # proceso interno: la semilla escribe en varias instituciones
        usuario("admin.sistema@retiroseguro.test", Rol.ADMIN_SISTEMA, None, 1, "Admin", "Sistema")

        for i, nombre in ((1, "Unidad Educativa Demo Norte"), (2, "Colegio Demo Sur")):
            inst, _ = Institucion.objects.get_or_create(
                correo=f"contacto{i}@colegio{i}.test",
                defaults=dict(
                    nombre=nombre, ruc=_ruc(f"179{i:02d}0001"), direccion="Dirección ficticia 100",
                    telefono="022000000", responsable=f"Responsable {i}",
                    estado=Institucion.Estado.ACTIVA, aprobada_en=timezone.now(),
                ),
            )
            puerta, _ = Puerta.objects.get_or_create(institucion_id=inst.id, nombre="Puerta principal")
            cursos = [
                Curso.objects.get_or_create(institucion_id=inst.id, nombre=n, defaults={"hora_salida": h})[0]
                for n, h in (("1ro A", time(13, 0)), ("2do A", time(13, 30)))
            ]

            usuario(f"admin{i}@colegio{i}.test", Rol.ADMIN_ESCOLAR, inst, 1, "Ana", f"Admin{i}")
            padre = usuario(f"padre{i}@colegio{i}.test", Rol.PADRE, inst, 2, "Pedro", f"Padre{i}")
            usuario(f"guardia{i}@colegio{i}.test", Rol.GUARDIA, inst, 3, "Gloria", f"Guardia{i}",
                    puerta_id=puerta.id)
            usuario(f"cuidador{i}@colegio{i}.test", Rol.CUIDADOR_FIJO, inst, 4, "Carlos", f"Cuidador{i}")

            for k, (nom, curso) in enumerate((("Luis", cursos[0]), ("Sofía", cursos[1])), start=1):
                est, _ = Estudiante.objects.get_or_create(
                    institucion_id=inst.id, cedula=_cedula(f"17{inst.id}10{k:04d}"),
                    defaults=dict(nombres=nom, apellidos=f"Padre{i}", curso_id=curso.id,
                                  fecha_nacimiento=date(2015 + k, 3, 10)),
                )
                RelacionPadreEstudiante.objects.get_or_create(
                    institucion_id=inst.id, padre=padre, estudiante=est)
    return resumen


if __name__ == "__main__":
    _preparar_django()
    resultado = sembrar()
    print("\nCuentas de demostración (contraseña: la variable SEED_PASSWORD del .env):")
    for correo, rol in sorted(resultado.items(), key=lambda x: x[1]):
        print(f"  {rol:<14} {correo}")
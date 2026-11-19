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

        instituciones = (
            {
                "correo": "administracion@ue-los-alisos.edu.ec",
                "nombre": "Unidad Educativa Los Alisos",
                "ruc_base": "179100001",
                "direccion": "Av. Los Shyris N35-120 y Suecia, Quito",
                "telefono": "022601420",
                "responsable": "Lic. María Fernanda Cárdenas",
                "admin": ("maria.cardenas@ue-los-alisos.edu.ec", "María Fernanda", "Cárdenas"),
                "padre": ("carolina.andrade@ejemplo.ec", "Carolina Isabel", "Andrade López"),
                "guardia": ("jorge.herrera@ue-los-alisos.edu.ec", "Jorge Luis", "Herrera"),
                "cuidador": ("ricardo.zambrano@ue-los-alisos.edu.ec", "Ricardo Javier", "Zambrano"),
                "cursos": (
                    ("Segundo de Básica A", time(13, 0)),
                    ("Cuarto de Básica A", time(13, 30)),
                    ("Séptimo de Básica A", time(14, 0)),
                ),
                "estudiantes": (
                    ("Mateo Sebastián", "Andrade Cárdenas", date(2019, 5, 14)),
                    ("Valentina Daniela", "Torres Andrade", date(2017, 8, 22)),
                    ("Samuel Nicolás", "Vega Andrade", date(2014, 2, 9)),
                ),
            },
            {
                "correo": "administracion@colegio-nuevo-mundo.edu.ec",
                "nombre": "Colegio Nuevo Mundo",
                "ruc_base": "179200001",
                "direccion": "Cdla. Kennedy Norte, calle 8ava y Av. del Ejército, Guayaquil",
                "telefono": "042318560",
                "responsable": "MSc. Paola Alejandra Moreno",
                "admin": ("paola.moreno@colegio-nuevo-mundo.edu.ec", "Paola Alejandra", "Moreno"),
                "padre": ("diego.loor@ejemplo.ec", "Diego Fernando", "Loor"),
                "guardia": ("luis.velez@colegio-nuevo-mundo.edu.ec", "Luis Fernando", "Vélez"),
                "cuidador": ("gabriela.munoz@colegio-nuevo-mundo.edu.ec", "Gabriela Carolina", "Muñoz"),
                "cursos": (
                    ("Primero de Básica B", time(12, 30)),
                    ("Tercero de Básica B", time(13, 0)),
                    ("Octavo de Básica B", time(13, 30)),
                ),
                "estudiantes": (
                    ("Sofía Isabella", "Pérez Loor", date(2020, 3, 18)),
                    ("Santiago Gabriel", "Mendoza Vera", date(2018, 10, 5)),
                    ("Emilia Antonella", "García Reyes", date(2015, 6, 27)),
                ),
            },
        )

        for i, datos in enumerate(instituciones, start=1):
            inst, _ = Institucion.objects.get_or_create(
                correo=datos["correo"],
                defaults=dict(
                    nombre=datos["nombre"], ruc=_ruc(datos["ruc_base"]), direccion=datos["direccion"],
                    telefono=datos["telefono"], responsable=datos["responsable"],
                    estado=Institucion.Estado.ACTIVA, aprobada_en=timezone.now(),
                ),
            )
            puerta, _ = Puerta.objects.get_or_create(institucion_id=inst.id, nombre="Puerta principal")
            cursos = [
                Curso.objects.get_or_create(institucion_id=inst.id, nombre=n, defaults={"hora_salida": h})[0]
                for n, h in datos["cursos"]
            ]

            admin_correo, admin_nombres, admin_apellidos = datos["admin"]
            usuario(admin_correo, Rol.ADMIN_ESCOLAR, inst, 1, admin_nombres, admin_apellidos)
            padre_correo, padre_nombres, padre_apellidos = datos["padre"]
            padre = usuario(padre_correo, Rol.PADRE, inst, 2, padre_nombres, padre_apellidos)
            guardia_correo, guardia_nombres, guardia_apellidos = datos["guardia"]
            usuario(guardia_correo, Rol.GUARDIA, inst, 3, guardia_nombres, guardia_apellidos,
                    telefono="0991234567", puerta_id=puerta.id)
            cuidador_correo, cuidador_nombres, cuidador_apellidos = datos["cuidador"]
            usuario(cuidador_correo, Rol.CUIDADOR_FIJO, inst, 4, cuidador_nombres, cuidador_apellidos,
                    telefono="0987654321")

            for k, ((nombres, apellidos, fecha_nacimiento), curso) in enumerate(
                zip(datos["estudiantes"], cursos),
                start=1,
            ):
                est, _ = Estudiante.objects.get_or_create(
                    institucion_id=inst.id, cedula=_cedula(f"17{inst.id}10{k:04d}"),
                    defaults=dict(nombres=nombres, apellidos=apellidos, curso_id=curso.id,
                                  fecha_nacimiento=fecha_nacimiento),
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
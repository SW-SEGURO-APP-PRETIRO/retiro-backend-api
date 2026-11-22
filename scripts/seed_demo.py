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

    from apps.auditoria.models import EventoAuditoria
    from apps.autenticacion.services import _registrar_auditoria
    from apps.chat.models import Notificacion
    from apps.cuentas.models import Estudiante, RelacionPadreEstudiante, Rol, Usuario
    from apps.cuidadores.models import AutorizacionCuidador, Cuidador
    from apps.instituciones.models import Curso, Institucion, Puerta
    from shared.tenancy.context import sin_filtro

    clave = clave or os.environ.get("SEED_PASSWORD", "ClaveDemo#2026")
    resumen = {}

    def usuario(correo, rol, inst, n, nombres, apellidos, **extra):
        if inst is None:
            u = Usuario.objects.filter(rol=rol).first()
        else:
            u = Usuario.objects.filter(institucion_id=inst.id, rol=rol).first()
        if u is None:
            u = Usuario.objects.filter(correo__iexact=correo).first()
        if u is None:
            u = Usuario.objects.crear_usuario(
                correo, clave,
                cedula=_cedula(f"17{inst.id if inst else 0}{n:02d}0001"),
                nombres=nombres, apellidos=apellidos, rol=rol,
                institucion_id=inst.id if inst else None,
                estado=Usuario.Estado.ACTIVA, **extra,
            )
        else:
            conflicto = Usuario.objects.filter(correo__iexact=correo).exclude(pk=u.pk).first()
            if conflicto is not None:
                conflicto.correo = (
                    f"liberada-{conflicto.pk}-{inst.id if inst else 'sistema'}"
                    f"-{conflicto.rol.lower()}@ejemplo.test"
                )
                conflicto.save(update_fields=["correo"])
            u.correo = correo
            u.nombres = nombres
            u.apellidos = apellidos
            u.estado = Usuario.Estado.ACTIVA
            u.set_password(clave)
            for campo, valor in extra.items():
                setattr(u, campo, valor)
            u.save()
        resumen[correo] = rol
        return u

    def registrar(actor, tipo, detalle):
        _registrar_auditoria(
            actor,
            tipo,
            "EXITO",
            detalle,
            categoria=EventoAuditoria.Categoria.OPERATIVA,
        )

    with sin_filtro():  # proceso interno: la semilla escribe en varias instituciones
        admin_sistema_correo = os.environ.get(
            "DEMO_ADMIN_SISTEMA_EMAIL",
            "admin.sistema@retiroseguro.test",
        )
        usuario(admin_sistema_correo, Rol.ADMIN_SISTEMA, None, 1, "Admin", "Sistema")

        instituciones = (
            {
                "correo": "administracion@ue-los-alisos.edu.ec",
                "nombre": "Unidad Educativa Los Alisos",
                "ruc_base": "179100001",
                "direccion": "Av. Los Shyris N35-120 y Suecia, Quito",
                "telefono": "022601420",
                "responsable": "Lic. María Fernanda Cárdenas",
                "admin": (
                    os.environ.get("DEMO_ADMIN_ESCOLAR_EMAIL", "maria.cardenas@ue-los-alisos.edu.ec"),
                    "María Fernanda",
                    "Cárdenas",
                ),
                "padre": (
                    os.environ.get("DEMO_PADRE_EMAIL", "carolina.andrade@ejemplo.ec"),
                    "Carolina Isabel",
                    "Andrade López",
                ),
                "guardia": ("jorge.herrera@ue-los-alisos.edu.ec", "Jorge Luis", "Herrera"),
                "crear_cuidador_fijo": False,
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
                "crear_cuidador_fijo": True,
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
            inst = Institucion.objects.filter(nombre=datos["nombre"]).first()
            if inst is None:
                inst = Institucion.objects.create(
                    nombre=datos["nombre"],
                    ruc=_ruc(datos["ruc_base"]),
                    direccion=datos["direccion"],
                    telefono=datos["telefono"],
                    correo=datos["correo"],
                    responsable=datos["responsable"],
                    estado=Institucion.Estado.ACTIVA,
                    aprobada_en=timezone.now(),
                )
            else:
                inst.correo = datos["correo"]
                inst.direccion = datos["direccion"]
                inst.telefono = datos["telefono"]
                inst.responsable = datos["responsable"]
                inst.estado = Institucion.Estado.ACTIVA
                inst.aprobada_en = timezone.now()
                inst.save()
            puerta, puerta_creada = Puerta.objects.get_or_create(institucion_id=inst.id, nombre="Puerta principal")
            cursos = []

            admin_correo, admin_nombres, admin_apellidos = datos["admin"]
            admin = usuario(admin_correo, Rol.ADMIN_ESCOLAR, inst, 1, admin_nombres, admin_apellidos)
            for nombre_curso, hora_salida in datos["cursos"]:
                curso, curso_creado = Curso.objects.get_or_create(
                    institucion_id=inst.id,
                    nombre=nombre_curso,
                    defaults={"hora_salida": hora_salida},
                )
                cursos.append(curso)
                if curso_creado:
                    registrar(
                        admin,
                        "CURSO_CREADO",
                        {"curso_id": curso.pk, "nombre": curso.nombre},
                    )
            padre_correo, padre_nombres, padre_apellidos = datos["padre"]
            padre = usuario(padre_correo, Rol.PADRE, inst, 2, padre_nombres, padre_apellidos)
            guardia_correo, guardia_nombres, guardia_apellidos = datos["guardia"]
            guardia = usuario(
                guardia_correo,
                Rol.GUARDIA,
                inst,
                3,
                guardia_nombres,
                guardia_apellidos,
                telefono="0991234567",
                puerta_id=puerta.id,
            )
            if puerta_creada:
                registrar(admin, "PUERTA_CREADA", {"puerta_id": puerta.pk, "nombre": puerta.nombre})

            cuidador = None
            if datos.get("crear_cuidador_fijo"):
                cuidador_correo, cuidador_nombres, cuidador_apellidos = datos["cuidador"]
                cuidador_usuario = usuario(
                    cuidador_correo,
                    Rol.CUIDADOR_FIJO,
                    inst,
                    4,
                    nombres=cuidador_nombres,
                    apellidos=cuidador_apellidos,
                    telefono="0987654321",
                )
                cuidador = Cuidador._base_manager.filter(
                    institucion_id=inst.id,
                    cedula=_cedula(f"17{inst.id}20{inst.id:02d}00"),
                ).first()
                if cuidador is None:
                    cuidador = Cuidador.objects.create(
                        institucion_id=inst.id,
                        tipo=Cuidador.Tipo.FIJO,
                        usuario_id=cuidador_usuario.pk,
                        cedula=_cedula(f"17{inst.id}20{inst.id:02d}00"),
                        nombres=cuidador_nombres,
                        apellidos=cuidador_apellidos,
                        telefono="0987654321",
                        correo=cuidador_correo,
                    )
                    registrar(
                        admin,
                        "CUIDADOR_CREADO",
                        {"cuidador_id": cuidador.pk, "tipo": cuidador.tipo},
                    )
                else:
                    cuidador.tipo = Cuidador.Tipo.FIJO
                    cuidador.usuario_id = cuidador_usuario.pk
                    cuidador.nombres = cuidador_nombres
                    cuidador.apellidos = cuidador_apellidos
                    cuidador.telefono = "0987654321"
                    cuidador.correo = cuidador_correo
                    cuidador.save()

            temporal_cedula = _cedula(f"17{inst.id}30{inst.id:02d}00")
            temporal = Cuidador._base_manager.filter(
                institucion_id=inst.id,
                cedula=temporal_cedula,
            ).first()
            if temporal is None:
                temporal = Cuidador.objects.create(
                    institucion_id=inst.id,
                    tipo=Cuidador.Tipo.TEMPORAL,
                    usuario_id=None,
                    cedula=temporal_cedula,
                    nombres="Cuidador temporal",
                    apellidos=f"Demostración {i}",
                    telefono="",
                    correo="",
                )
                registrar(
                    admin,
                    "CUIDADOR_CREADO",
                    {"cuidador_id": temporal.pk, "tipo": temporal.tipo},
                )

            for k, ((nombres, apellidos, fecha_nacimiento), curso) in enumerate(
                zip(datos["estudiantes"], cursos),
                start=1,
            ):
                est, estudiante_creado = Estudiante.objects.get_or_create(
                    institucion_id=inst.id, cedula=_cedula(f"17{inst.id}10{k:04d}"),
                    defaults=dict(nombres=nombres, apellidos=apellidos, curso_id=curso.id,
                                  fecha_nacimiento=fecha_nacimiento),
                )
                relacion, relacion_creada = RelacionPadreEstudiante.objects.get_or_create(
                    institucion_id=inst.id, padre=padre, estudiante=est)
                if estudiante_creado:
                    registrar(
                        admin,
                        "ESTUDIANTE_CREADO",
                        {
                            "estudiante_id": est.pk,
                            "curso": curso.nombre,
                        },
                    )
                if relacion_creada:
                    registrar(
                        admin,
                        "RELACION_PADRE_ESTUDIANTE_CREADA",
                        {
                            "relacion_id": relacion.pk,
                            "padre_id": padre.pk,
                            "estudiante_id": est.pk,
                        },
                    )

            primer_estudiante = Estudiante.objects.filter(institucion_id=inst.id).order_by("id").first()
            if primer_estudiante and cuidador is not None:
                autorizacion, creada = AutorizacionCuidador.objects.get_or_create(
                    institucion_id=inst.id,
                    cuidador=cuidador,
                    estudiante_id=primer_estudiante.pk,
                    defaults={
                        "solicitada_por_id": padre.pk,
                        "estado": (
                            AutorizacionCuidador.Estado.SOLICITADO
                            if i == 1
                            else AutorizacionCuidador.Estado.RECHAZADO
                        ),
                        "motivo_rechazo": (
                            ""
                            if i == 1
                            else "La autorización no corresponde a la persona registrada por la familia."
                        ),
                        "rechazada_por_id": admin.pk if i != 1 else None,
                        "rechazada_en": timezone.now() if i != 1 else None,
                    },
                )
                if creada:
                    registrar(
                        padre,
                        "AUTORIZACION_SOLICITADA",
                        {
                            "autorizacion_id": autorizacion.pk,
                            "cuidador_id": cuidador.pk,
                            "estudiante_id": primer_estudiante.pk,
                        },
                    )
                    if i != 1:
                        registrar(
                            admin,
                            "CUIDADOR_AUTORIZACION_RECHAZADA",
                            {
                                "autorizacion_id": autorizacion.pk,
                                "cuidador_id": cuidador.pk,
                                "estudiante_id": primer_estudiante.pk,
                                "motivo": autorizacion.motivo_rechazo,
                            },
                        )

                Notificacion.objects.get_or_create(
                    institucion_id=inst.id,
                    destinatario_id=admin.pk,
                    tipo="CUIDADOR_SOLICITADO" if i == 1 else "ACCESO_RECHAZADO",
                    titulo="Nueva solicitud de cuidador" if i == 1 else "Solicitud de cuidador rechazada",
                    defaults={
                        "mensaje": (
                            "Hay una solicitud pendiente de revisión."
                            if i == 1
                            else "Se registró el rechazo de una solicitud."
                        ),
                        "referencia": str(autorizacion.pk),
                    },
                )
    return resumen


if __name__ == "__main__":
    _preparar_django()
    resultado = sembrar()
    print("\nCuentas de demostración (contraseña: la variable SEED_PASSWORD del .env):")
    for correo, rol in sorted(resultado.items(), key=lambda x: x[1]):
        print(f"  {rol:<14} {correo}")
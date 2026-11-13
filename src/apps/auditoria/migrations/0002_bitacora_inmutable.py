"""Disparadores de base de datos que rechazan UPDATE y DELETE sobre la bitácora (capa 2 de 3).

Funciona en SQL Server (Docker) y en SQLite (pruebas). Se quitan al revertir la migración.
"""
from django.db import migrations

TABLA = "auditoria_eventoauditoria"
MENSAJE = "La bitacora es inmutable: no se permite UPDATE ni DELETE."


def crear(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "microsoft":
        schema_editor.execute(
            f"CREATE TRIGGER trg_auditoria_inmutable ON {TABLA} INSTEAD OF UPDATE, DELETE AS "
            f"BEGIN SET NOCOUNT ON; THROW 51000, '{MENSAJE}', 1; END"
        )
    elif vendor == "sqlite":
        for accion in ("UPDATE", "DELETE"):
            schema_editor.execute(
                f"CREATE TRIGGER trg_auditoria_no_{accion.lower()} BEFORE {accion} ON {TABLA} "
                f"BEGIN SELECT RAISE(ABORT, '{MENSAJE}'); END"
            )


def quitar(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "microsoft":
        schema_editor.execute("DROP TRIGGER IF EXISTS trg_auditoria_inmutable")
    elif vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS trg_auditoria_no_update")
        schema_editor.execute("DROP TRIGGER IF EXISTS trg_auditoria_no_delete")


class Migration(migrations.Migration):
    dependencies = [("auditoria", "0001_initial")]
    operations = [migrations.RunPython(crear, quitar)]
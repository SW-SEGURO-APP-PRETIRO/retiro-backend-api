"""Espera a SQL Server, crea la base de datos y el usuario de la aplicación si no existen.

SQL Server en Docker arranca SIN base de datos de la aplicación. Este comando (idempotente)
se conecta como `sa` y deja listo: base de datos + login + usuario con permisos para migrar.
"""
import os
import re
import time

import pyodbc
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

IDENTIFICADOR = re.compile(r"^[A-Za-z0-9_]+$")


def _literal(texto: str) -> str:
    return "N'" + texto.replace("'", "''") + "'"


class Command(BaseCommand):
    help = "Espera a SQL Server y crea la base de datos y el usuario de la aplicación."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=120, help="Segundos máximos de espera")

    def _conectar(self, base: str, sa_password: str, host: str, port: str):
        cadena = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={host},{port};DATABASE={base};"
            f"UID=sa;PWD={sa_password};Encrypt=yes;TrustServerCertificate=yes"
        )
        return pyodbc.connect(cadena, autocommit=True, timeout=5)

    def handle(self, *args, **opciones):
        cfg = settings.DATABASES["default"]
        base, usuario, clave = cfg["NAME"], cfg["USER"], cfg["PASSWORD"]
        host, puerto = cfg["HOST"], str(cfg["PORT"])
        sa_password = os.environ.get("MSSQL_SA_PASSWORD", "")

        for nombre in (base, usuario):
            if not IDENTIFICADOR.match(nombre):
                raise CommandError(f"Nombre no permitido (solo letras, números y _): {nombre!r}")
        if not sa_password or not clave:
            raise CommandError("Faltan MSSQL_SA_PASSWORD o DB_PASSWORD en el entorno (.env).")

        limite = time.time() + opciones["timeout"]
        while True:
            try:
                conexion = self._conectar("master", sa_password, host, puerto)
                break
            except pyodbc.Error as exc:
                if time.time() > limite:
                    raise CommandError(f"SQL Server no respondió a tiempo: {exc}") from exc
                self.stdout.write("Esperando a SQL Server...")
                time.sleep(3)

        cursor = conexion.cursor()
        cursor.execute(f"IF DB_ID({_literal(base)}) IS NULL CREATE DATABASE [{base}]")
        cursor.execute(
            f"IF SUSER_ID({_literal(usuario)}) IS NULL "
            f"CREATE LOGIN [{usuario}] WITH PASSWORD = {_literal(clave)}, CHECK_POLICY = ON "
            f"ELSE ALTER LOGIN [{usuario}] WITH PASSWORD = {_literal(clave)}"
        )
        conexion.close()

        conexion = self._conectar(base, sa_password, host, puerto)
        cursor = conexion.cursor()
        cursor.execute(
            f"IF USER_ID({_literal(usuario)}) IS NULL CREATE USER [{usuario}] FOR LOGIN [{usuario}]"
        )
        cursor.execute(f"ALTER ROLE db_owner ADD MEMBER [{usuario}]")
        conexion.close()
        self.stdout.write(self.style.SUCCESS(f"Base '{base}' y usuario '{usuario}' listos."))
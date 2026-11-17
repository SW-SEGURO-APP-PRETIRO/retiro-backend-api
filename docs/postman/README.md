# Colección Postman A+B

## Archivos

- `retiro-escolar-seguro-a-b.postman_collection.json`: colección de Bloque A y Bloque B.
- `retiro-escolar-seguro-a-b.postman_environment.json`: variables locales.
- `scripts/postman/ejecutar.ps1`: preparación y ejecución automatizada desde PowerShell.

## Contratos relacionados

- REST: OpenAPI generado con `drf-spectacular`.
- Swagger: `https://localhost:8443/api/docs/`.
- Esquema OpenAPI: `https://localhost:8443/api/schema/`.
- ReDoc: `https://localhost:8443/api/redoc/`.

La colección prueba la implementación actual, no reemplaza el contrato OpenAPI.

## Preparación manual

Desde la raíz del repositorio:

```powershell
docker compose up -d --build app
docker compose exec app python manage.py check
docker compose exec app python scripts/seed_demo.py
```

La semilla crea datos ficticios idempotentes:

```text
Usuario: admin.sistema@retiroseguro.test
Contraseña: ClaveDemo*2026

Admin escolar:
admin1@colegio1.test
admin2@colegio2.test

Instituciones:
Unidad Educativa Demo Norte
Colegio Demo Sur
```

## Importar en Postman

1. Abrir Postman.
2. Importar `retiro-escolar-seguro-a-b.postman_collection.json`.
3. Importar `retiro-escolar-seguro-a-b.postman_environment.json`.
4. Seleccionar el ambiente `Retiro Escolar Seguro - A+B - Local`.
5. Si Caddy usa un certificado interno, desactivar temporalmente la validación SSL de Postman para localhost.
6. Ejecutar primero la carpeta `00 - Preparación`.
7. Ejecutar las carpetas en orden.

La colección conserva la cookie `sessionid`. El request inicial de documentación obtiene la cookie `csrftoken`; el script de colección la envía como `X-CSRFToken` en operaciones que modifican datos.

## Orden de ejecución

```text
00 - Preparación
A - Autenticación
B - Instituciones
B - Cuentas
```

La colección crea una institución nueva pendiente y la aprueba durante la ejecución. Los IDs se guardan automáticamente en variables de entorno.

## Ejecutar con Newman

Requiere Node.js y Newman:

```powershell
npm install -g newman
newman run .\docs\postman\retiro-escolar-seguro-a-b.postman_collection.json `
  -e .\docs\postman\retiro-escolar-seguro-a-b.postman_environment.json `
  --insecure
```

El parámetro `--insecure` solo debe usarse en este entorno local porque Caddy utiliza un certificado interno.

### Nota sobre Newman y CSRF

En la validación realizada contra `https://localhost:8443`, Newman pudo ejecutar salud,
Swagger y login, pero el proxy rechazó una solicitud POST posterior con `CSRF token incorrect`.
Esto ocurre cuando Newman no conserva la pareja `csrftoken` + `sessionid` como lo hace Postman
Desktop. En Postman Desktop se debe mantener activo **Settings > Data > Cookie manager** y
ejecutar primero `00 - Preparación`. Si Newman sigue mostrando `403`, revisar el cookie jar,
el certificado local y el valor `csrf_token` del ambiente antes de interpretar el resultado como
un fallo funcional del endpoint.

## Resultados esperados

La ejecución debe mostrar:

- login correcto: `200`;
- credenciales inválidas: `401`;
- payload inválido: `400`;
- registro institucional: `201`;
- aprobación: `200`;
- creación de curso, puerta, usuario y estudiante: `201`;
- listados y actualizaciones: `200`;
- relación creada y eliminada: `201` y `200`;
- intento con curso ajeno: `400` o `409`.

## Verificación posterior en SQL Server

```sql
SELECT id, nombre, estado, creada_por_id, aprobada_por_id
FROM dbo.instituciones_institucion
ORDER BY id DESC;

SELECT id, correo, rol, institucion_id, estado, contrasena_temporal
FROM dbo.cuentas_usuario
ORDER BY id DESC;

SELECT id, institucion_id, nombre, hora_salida, activo
FROM dbo.instituciones_curso
ORDER BY id DESC;

SELECT id, institucion_id, nombre, activa
FROM dbo.instituciones_puerta
ORDER BY id DESC;

SELECT id, institucion_id, cedula, nombres, curso_id, estado
FROM dbo.cuentas_estudiante
ORDER BY id DESC;

SELECT TOP 100 id, institucion_id, categoria, tipo, actor_id, resultado, fecha
FROM dbo.auditoria_eventoauditoria
ORDER BY id DESC;
```

## Cómo interpretar un fallo

Un request solo está correcto si coinciden:

```text
respuesta HTTP
+ formato JSON
+ cookie/sesión
+ permisos por rol
+ institución del usuario
+ estado de la base
+ auditoría
```

Si un request devuelve `200` pero no modifica la tabla esperada, el caso falla.

Si modifica una institución distinta a la del usuario, es un fallo crítico de aislamiento.

Si crea datos sin auditoría, es un fallo de trazabilidad.

## Extensión por Bloques C y D

La persona que implemente C y D debe agregar carpetas a la misma colección:

```text
C - Cuidadores y autorizaciones
D - Notificaciones y WebSockets
D - Retiros y QR
```

No debe crear otra colección independiente. Debe conservar las variables, los scripts de CSRF y el formato de respuestas actual.

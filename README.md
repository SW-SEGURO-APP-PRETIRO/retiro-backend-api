# Retiro Escolar Seguro

Sistema web y API para gestionar de forma segura la operación de retiro de estudiantes: instituciones, cuentas, relaciones entre representantes y estudiantes, solicitudes de cuidadores, notificaciones y auditoría. La aplicación está construida como un monolito modular y aplica aislamiento de datos por institución.

> **Estado del alcance:** los paneles administrativos, autenticación, cuentas, instituciones, cuidadores, notificaciones, chat y auditoría cuentan con interfaces y/o endpoints integrados. El módulo `retiros` ya define sus modelos de sesiones y pases QR, pero todavía no está conectado a rutas REST en `config/urls.py`; no se debe asumir que el flujo de validación QR y registro de retiros está disponible.

## Capacidades actuales

- **Panel escolar (`/escolar/`)**: administración de estudiantes, representantes, guardias, asignaciones, cuidadores, cursos, puertas, información institucional, notificaciones, chat y bitácora operativa.
- **Panel del sistema (`/sistema/`)**: supervisión global de instituciones y cuentas, aprobación/rechazo y cambio de estado de instituciones, seguridad, notificaciones y bitácora técnica.
- **Autenticación** mediante sesiones Django, inicio y cierre de sesión, recuperación de contraseña, cambio de contraseña temporal y bloqueo por intentos fallidos.
- **API REST** para autenticación, instituciones, cuentas, cuidadores, auditoría, notificaciones y salas/mensajes de chat.
- **Tiempo real** con Django Channels y Redis para notificaciones y mensajes de chat mediante WebSocket.
- **Aislamiento multiinstitución** para los datos escolares, aplicado por middleware y managers de modelos.
- **Bitácora de auditoría de solo adición**, con protección en Python y en SQL Server y enlaces SHA-256 entre eventos.
- **Datos ficticios de demostración**, cargados con un script idempotente.

La aplicación tiene cinco roles: `ADMIN_SISTEMA`, `ADMIN_ESCOLAR`, `PADRE`, `GUARDIA` y `CUIDADOR_FIJO`. El administrador del sistema supervisa la plataforma; el administrador escolar opera únicamente su institución. Los demás roles usan la API y las funciones habilitadas para su flujo.

## Arquitectura

| Componente | Tecnología / responsabilidad |
|---|---|
| Backend | Python 3.12, Django 5.2, Django REST Framework |
| Paneles web | Plantillas Django y JavaScript/CSS estáticos, sin framework de frontend |
| HTTP y WebSocket | Daphne, ASGI y Django Channels |
| Base de datos | SQL Server 2022, con driver ODBC 18 |
| Mensajería en tiempo real | Redis 7 y `channels_redis` |
| Proxy local | Caddy, HTTPS en `localhost:8443` |
| Esquema API | OpenAPI, Swagger UI y ReDoc con `drf-spectacular` |

### Módulos Django

| Módulo | Responsabilidad |
|---|---|
| `instituciones` | Instituciones, cursos, puertas y verificación |
| `cuentas` | Usuarios, estudiantes y relaciones padre-estudiante |
| `autenticacion` | Inicio de sesión, recuperación y cambios de contraseña |
| `cuidadores` | Cuidadores y autorizaciones por estudiante |
| `retiros` | Modelos de sesiones de salida, pases QR y retiros; rutas REST pendientes |
| `chat` | Notificaciones, salas, participantes y mensajes |
| `auditoria` | Eventos técnicos y operativos de solo adición |

Código transversal como tenancy, permisos, validadores y comandos de gestión está en `src/shared/`. La configuración Django y ASGI está en `src/config/`; las plantillas y los recursos estáticos están en `src/templates/` y `src/static/`.

## Rutas principales

### Web

| Ruta | Uso |
|---|---|
| `/` | Redirige al panel correspondiente según el rol |
| `/escolar/` | Panel del administrador escolar |
| `/sistema/` | Panel del administrador del sistema |
| `/autenticacion/ingresar/` | Inicio de sesión |
| `/autenticacion/recuperar/` | Solicitud de recuperación |
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | Documentación ReDoc |
| `/api/schema/` | Esquema OpenAPI |
| `/salud/` | Comprobación HTTP y conexión a base de datos |

### API REST

Todas las rutas de API usan el prefijo `/api/v1/`.

| Prefijo | Recursos |
|---|---|
| `/autenticacion/` | Sesión, perfil, inicio/cierre de sesión y recuperación |
| `/instituciones/` | Registro, aprobación, institución actual, cursos y puertas |
| `/cuentas/` | Usuarios, estudiantes y relaciones padre-estudiante |
| `/cuidadores/` | Cuidadores, solicitudes y autorizaciones |
| `/auditoria/` | Consultas de bitácora técnica y operativa |
| `/notificaciones/` | Consulta y marcado de notificaciones |
| `/chat/` | Salas y mensajes persistidos |

La autenticación de la API usa sesiones Django. Las mutaciones requieren CSRF; el usuario autenticado determina su institución, no un `institucion_id` enviado por el cliente.

### WebSocket

`/ws/notificaciones/` utiliza la sesión autenticada de Django. Transporta notificaciones y mensajes de chat; también admite presencia y heartbeat. El socket no confía en un identificador de usuario enviado por el cliente.

## Requisitos

- Git.
- Docker Desktop con Docker Compose v2.
- Para ejecutar las pruebas JavaScript: Node.js con soporte para `node --test`.
- No se necesita instalar Python localmente para levantar el sistema con Docker.

## Puesta en marcha con Docker

Desde PowerShell:

```powershell
git clone https://github.com/SW-SEGURO-APP-PRETIRO/retiro-backend-api.git
Set-Location retiro-backend-api
Copy-Item .env.example .env
```

Edita `.env` antes del primer arranque. Define valores propios y fuertes para `DJANGO_SECRET_KEY`, `MSSQL_SA_PASSWORD`, `DB_PASSWORD`, `FIELD_ENCRYPTION_KEY` y `HMAC_SIGNING_KEY`. No reutilices las claves de ejemplo ni compartas el archivo `.env`.

Se pueden generar claves con el contenedor de la aplicación:

```powershell
docker compose run --rm --no-deps app python -c "import secrets; print(secrets.token_urlsafe(50))"
docker compose run --rm --no-deps app python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Usa una salida independiente para cada clave `DJANGO_SECRET_KEY` y `HMAC_SIGNING_KEY`, y la salida de Fernet para `FIELD_ENCRYPTION_KEY`.

Construye y arranca los servicios:

```powershell
docker compose up --build -d
docker compose ps
```

Compose levanta SQL Server, Redis, Django/Daphne y Caddy. La aplicación espera a que la base esté disponible, aplica migraciones y luego inicia el servidor ASGI. Cuando la base esté saludable, abre <https://localhost:8443/salud/>. En desarrollo, el navegador puede advertir que el certificado HTTPS local no es de confianza.

### Datos de demostración

La semilla crea registros ficticios para probar los paneles. Es idempotente y usa `SEED_PASSWORD` de `.env` para las cuentas creadas o actualizadas:

```powershell
docker compose exec app python scripts/seed_demo.py
```

No uses las cuentas ni contraseñas de demostración en producción. En desarrollo, el backend de correo predeterminado imprime los correos en los logs de `app`; para SMTP real configura `EMAIL_BACKEND` y las variables `EMAIL_HOST*` en `.env`.

### Comandos Docker útiles

```powershell
docker compose ps
docker compose logs app --tail 60
docker compose down
```

`docker compose down -v` elimina también los volúmenes persistentes, incluida la base de datos. Úsalo solo cuando quieras borrar esos datos.

## Pruebas y verificaciones

Las pruebas Python usan una base SQLite en memoria aislada, por lo que no requieren SQL Server:

```powershell
python -m pip install -r requirements.txt
python -m pytest
```

Las pruebas de los módulos JavaScript se ejecutan con Node:

```powershell
node --test tests/frontend.test.mjs
```

Con los servicios Docker levantados también se pueden ejecutar:

```powershell
docker compose exec app python manage.py check
docker compose exec app python manage.py showmigrations
```

## Convenciones importantes para contribuir

1. Los datos pertenecientes a una institución deben heredar de `TenantModel` y respetar el contexto de tenancy. `sin_filtro()` se reserva para procesos internos, como semillas y tareas de sistema.
2. No confíes en la institución que envía el cliente: obtén el ámbito desde el usuario autenticado.
3. Las referencias entre módulos se manejan por ID, no con importaciones directas de modelos ni claves foráneas entre aplicaciones. Dentro de un módulo sí se pueden usar claves foráneas.
4. Los tokens se almacenan como hashes. Los secretos TOTP y las fotos usan campos cifrados; las firmas de cuidadores/autorizaciones usan HMAC.
5. La auditoría es de solo adición. No intentes editar o borrar eventos; el trigger de SQL Server también bloquea cambios directos.
6. Agrega migraciones al modificar modelos y mantén actualizados los documentos relacionados.

## Documentación adicional

- [Guía del equipo](GUIA_DEL_EQUIPO.md): base de datos, Docker, tenancy y convenciones.
- [Diagrama entidad-relación](docs/ER.md): modelos y relaciones.
- [Colección de Postman](docs/postman/README.md).

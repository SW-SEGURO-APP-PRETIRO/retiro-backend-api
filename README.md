# Retiro Escolar Seguro

Aplicación web monolítica para que los **colegios controlen quién retira a cada estudiante**. Gestiona instituciones, cuentas, relaciones entre representantes y estudiantes, solicitudes de cuidadores, notificaciones y auditoría. Está construida como un **monolito modular** y aplica **aislamiento de datos por institución**.

**Problema que resuelve:** en la salida de clases, el personal del colegio no siempre sabe si la persona que viene a recoger a un niño está autorizada. Retiro Escolar Seguro centraliza esas autorizaciones, deja registro de cada decisión en una bitácora inmutable y comunica a la comunidad escolar en tiempo real.

> **Estado del alcance:** los paneles administrativos, el registro de instituciones, la autenticación, las cuentas, las instituciones, los cuidadores, las notificaciones, el chat y la auditoría cuentan con interfaces y/o endpoints integrados. El módulo `retiros` ya define sus modelos de sesiones y pases QR, pero todavía no está conectado a rutas REST en `config/urls.py`: no se debe asumir que el flujo de validación QR y registro de retiros está disponible.

---

## Contenido

1. [Capacidades y roles](#1-capacidades-y-roles)
2. [Arquitectura y tecnologías](#2-arquitectura-y-tecnologías)
3. [Requisitos previos](#3-requisitos-previos)
4. [Instalación y ejecución](#4-instalación-y-ejecución)
5. [Cuentas de prueba](#5-cuentas-de-prueba)
6. [Cómo usar la aplicación](#6-cómo-usar-la-aplicación)
7. [Rutas principales](#7-rutas-principales)
8. [Pruebas y verificaciones](#8-pruebas-y-verificaciones)
9. [Requisitos del primer bimestre](#9-requisitos-del-primer-bimestre)
10. [Tiempo real con WebSocket](#10-tiempo-real-con-websocket)
11. [Base de datos](#11-base-de-datos)
12. [Estructura del proyecto](#12-estructura-del-proyecto)
13. [Rendimiento](#13-rendimiento)
14. [Comandos útiles y solución de problemas](#14-comandos-útiles-y-solución-de-problemas)
15. [Convenciones para contribuir](#15-convenciones-para-contribuir)
16. [Documentación adicional y equipo](#16-documentación-adicional-y-equipo)

---

## 1. Capacidades y roles

- **Registro de instituciones (`/autenticacion/registrar/`)**: una persona del colegio registra su institución y queda como su Administrador Escolar, pendiente de aprobación.
- **Panel escolar (`/escolar/`)**: estudiantes, representantes, guardias, asignaciones, cuidadores, cursos, puertas, información institucional, notificaciones, chat y bitácora operativa.
- **Panel del sistema (`/sistema/`)**: supervisión global de instituciones y cuentas, aprobación o rechazo y cambio de estado de instituciones, seguridad, notificaciones, chat y bitácora técnica.
- **Autenticación** con sesiones de Django: inicio y cierre de sesión, recuperación de contraseña, cambio de contraseña temporal y bloqueo por intentos fallidos.
- **API REST** para autenticación, instituciones, cuentas, cuidadores, auditoría, notificaciones y chat.
- **Tiempo real** con Django Channels y Redis: chat, usuarios conectados y notificaciones por WebSocket.
- **Aislamiento multiinstitución**, aplicado por middleware y managers de modelos.
- **Bitácora de auditoría de solo adición**, protegida en Python y en SQL Server, con enlaces SHA-256 entre eventos.
- **Datos ficticios de demostración**, cargados con un script idempotente.

La aplicación tiene cinco roles: `ADMIN_SISTEMA`, `ADMIN_ESCOLAR`, `PADRE`, `GUARDIA` y `CUIDADOR_FIJO`. El Administrador del Sistema supervisa la plataforma; el Administrador Escolar opera únicamente su institución. Los demás roles usan la API (cliente móvil) y las funciones habilitadas para su flujo.

---

## 2. Arquitectura y tecnologías

| Componente | Tecnología / responsabilidad |
|---|---|
| Backend | Python 3.12, Django 5.2 (monolito modular), Django REST Framework |
| Interfaz web | Plantillas Django + HTML5, CSS3 y JavaScript (módulos ES), sin framework de frontend |
| HTTP y WebSocket | Daphne (ASGI) y Django Channels, en el mismo proceso |
| Base de datos | SQL Server 2022 (`mssql-django`, driver ODBC 18) |
| Mensajería en tiempo real y presencia | Redis 7 y `channels-redis` |
| Contraseñas | Argon2 (hash con sal) |
| Proxy local | Caddy: HTTPS y WSS en `localhost:8443` |
| Esquema de la API | OpenAPI, Swagger UI y ReDoc con `drf-spectacular` |
| Contenedores | Docker + Docker Compose |
| Pruebas | pytest + pytest-django · `node --test` para el JavaScript |

Stack permitido por el enunciado: **Django (Python) + Django Channels (ASGI)**.

### Módulos Django

| Módulo | Responsabilidad |
|---|---|
| `instituciones` | Instituciones, cursos, puertas, registro y aprobación |
| `cuentas` | Usuarios, estudiantes y relaciones padre-estudiante |
| `autenticacion` | Inicio de sesión, recuperación y cambios de contraseña |
| `cuidadores` | Cuidadores y autorizaciones por estudiante |
| `retiros` | Modelos de sesiones de salida, pases QR y retiros; rutas REST pendientes |
| `chat` | Notificaciones, salas, participantes, mensajes y presencia |
| `auditoria` | Eventos técnicos y operativos de solo adición |
| `panel_escolar` | Pantallas del Administrador Escolar y registro de instituciones |
| `panel_sistema` | Pantallas del Administrador del Sistema |

El código transversal (tenancy, permisos, validadores y comandos de gestión) está en `src/shared/`. La configuración Django y ASGI está en `src/config/`; las plantillas y los recursos estáticos, en `src/templates/` y `src/static/`.

---

## 3. Requisitos previos

- **Git**.
- **Docker Desktop** (con Docker Compose v2) encendido.
- Para las pruebas JavaScript: **Node.js 18 o superior** (soporte para `node --test`).

No hace falta instalar Python, SQL Server ni Redis para levantar el sistema: todo corre dentro de contenedores.

---

## 4. Instalación y ejecución

### 4.1 Clonar el repositorio

```bash
git clone https://github.com/SW-SEGURO-APP-PRETIRO/retiro-backend-api.git
cd retiro-backend-api
```

### 4.2 Crear el archivo `.env`

```bash
# Windows (PowerShell)
Copy-Item .env.example .env
# Linux / macOS
cp .env.example .env
```

Edita **solo tu `.env`** (nunca se sube al repositorio). Define valores propios y fuertes; no reutilices las claves de ejemplo:

| Variable | Qué poner |
|---|---|
| `MSSQL_SA_PASSWORD` | Contraseña del administrador de SQL Server: mínimo 8 caracteres, con mayúscula, minúscula, número y símbolo |
| `DB_PASSWORD` | Otra contraseña distinta, igual de compleja |
| `DJANGO_SECRET_KEY` | Cadena aleatoria (ver abajo) |
| `HMAC_SIGNING_KEY` | Otra cadena aleatoria (ver abajo) |
| `FIELD_ENCRYPTION_KEY` | Clave Fernet (ver abajo) |

Para generar las claves sin instalar nada:

```bash
# Cadena aleatoria: ejecútalo una vez para DJANGO_SECRET_KEY y otra para HMAC_SIGNING_KEY
docker compose run --rm --no-deps app python -c "import secrets; print(secrets.token_urlsafe(50))"

# Clave Fernet (FIELD_ENCRYPTION_KEY)
docker compose run --rm --no-deps app python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> La primera vez se construye la imagen y tarda unos minutos.

Variables opcionales:

| Variable | Para qué |
|---|---|
| `SEED_PASSWORD` | Contraseña de las cuentas de prueba (por defecto `ClaveDemo#2026`) |
| `EMAIL_BACKEND`, `EMAIL_HOST*` | Por defecto los correos se **imprimen en los logs** de `app`. Para enviarlos de verdad usa el backend SMTP (por ejemplo, Gmail con contraseña de aplicación). |
| `PASSWORD_RESET_URL` | Dirección de la página de restablecimiento que llega en el correo de recuperación. En producción, el dominio HTTPS real. |
| `SITE_URL` | Dirección pública del sitio para los demás enlaces enviados por correo (por ejemplo, la aprobación del registro) |
| `DB_HOST_PORT` | Puerto de tu equipo donde se publica el SQL Server de Docker para SSMS o DBeaver (por defecto `1433`). Cámbialo, por ejemplo a `14333`, si ya tienes un SQL Server instalado. |

### 4.3 Levantar el proyecto

```bash
docker compose up --build -d
docker compose ps
```

| Servicio | Qué es |
|---|---|
| `db` | SQL Server 2022 (la primera vez descarga ~1,5 GB) |
| `redis` | Capa de mensajes de Channels y presencia de usuarios |
| `app` | Django + Daphne (HTTP y WebSocket en el mismo proceso) |
| `proxy` | Caddy: HTTPS en el puerto **8443** |

Al arrancar, `app` ejecuta en orden: `esperar_bd` (espera a SQL Server y crea la base y el usuario si no existen), `migrate` (crea las tablas y el disparador de la bitácora) y Daphne.

### 4.4 Comprobar que funciona

Abre **https://localhost:8443/salud/**. El navegador avisará "No es seguro" porque el certificado es local: pulsa *Avanzado → Continuar*. Debe responder:

```json
{"estado": "ok"}
```

### 4.5 Cargar los datos de prueba

```bash
docker compose exec app python scripts/seed_demo.py
```

Crea datos **ficticios** (2 colegios con cursos, puertas, estudiantes, representantes y las cuentas de la sección siguiente). Es idempotente: se puede ejecutar varias veces sin duplicar registros. No uses estas cuentas ni contraseñas en producción.

### 4.6 Entrar

Abre **https://localhost:8443/autenticacion/ingresar/**.

---

## 5. Cuentas de prueba

Todas usan la contraseña de `SEED_PASSWORD` (por defecto **`ClaveDemo#2026`**).

| Rol | Correo | Acceso web |
|---|---|---|
| Administrador del Sistema | `admin.sistema@retiroseguro.test` | Panel del sistema (`/sistema/`) |
| Administrador Escolar · U. E. Los Alisos | `maria.cardenas@ue-los-alisos.edu.ec` | Panel escolar (`/escolar/`) |
| Administrador Escolar · Colegio Nuevo Mundo | `paola.moreno@colegio-nuevo-mundo.edu.ec` | Panel escolar (`/escolar/`) |
| Padre · Los Alisos | `carolina.andrade@ejemplo.ec` | Solo API (cliente móvil) |
| Guardia · Los Alisos | `jorge.herrera@ue-los-alisos.edu.ec` | Solo API (cliente móvil) |

> Los correos de los administradores se pueden cambiar con `DEMO_ADMIN_SISTEMA_EMAIL`, `DEMO_ADMIN_ESCOLAR_EMAIL` y `DEMO_PADRE_EMAIL` en el `.env`.
>
> Tras **3 contraseñas erróneas** la cuenta se bloquea **15 minutos** (protección contra fuerza bruta).

---

## 6. Cómo usar la aplicación

Hay **un solo inicio de sesión**. El sistema lee el rol de la cuenta y lleva a cada persona a su panel.

```
https://localhost:8443/autenticacion/ingresar/
        │
        ├── ADMIN_SISTEMA  → /sistema/   instituciones, cuentas, seguridad, bitácora técnica, chat
        └── ADMIN_ESCOLAR  → /escolar/   estudiantes, padres, guardias, cuidadores, cursos, chat…
```

### 6.1 Registro de una institución (SignUp)

1. En el inicio de sesión, pulsa **"Regístrala aquí"** (`/autenticacion/registrar/`).
2. La persona del colegio llena **sus datos** (será el Administrador Escolar), los **datos de la institución** y su **contraseña**.
3. La solicitud queda **pendiente de aprobación**. Si intenta entrar antes, el sistema le indica que falta la aprobación.
4. El **Administrador del Sistema** la revisa en **Solicitudes pendientes** y la **aprueba o rechaza** (con motivo).
5. La persona recibe un **correo** con el resultado y, si fue aprobada, entra con su **correo personal** (no el institucional) y la contraseña que eligió.

> **Datos para probar el registro:** el RUC debe tener 13 dígitos, empezar con un código de provincia (01-24 o 30), tener tercer dígito 0-6 o 9 y terminar en el establecimiento (por ejemplo `1791234567001`). La cédula valida su dígito verificador; puedes usar `1723456701`, `1723456719` o `1723456727`.

### 6.2 Recuperación de contraseña

1. En el inicio de sesión, pulsa **"¿Olvidaste tu contraseña?"** y escribe el correo.
2. Se envía un **enlace de un solo uso que caduca en 30 minutos**. En desarrollo el correo aparece en los logs:
   ```bash
   docker compose logs app --tail 40
   ```
3. Abre el enlace y define la nueva contraseña. El token se guarda en la sesión y se retira de la URL para que no quede expuesto en el historial ni en cabeceras `Referer`.

### 6.3 CRUD de estudiantes (entidad principal)

En **Panel escolar → Estudiantes**:

| Operación | Cómo |
|---|---|
| Crear | Botón **"Nuevo estudiante"** |
| Listar y paginar | 20 por página, paginado **en el servidor** |
| Buscar y filtrar | Por nombre, apellido o cédula, y por estado (activo o inactivo) |
| Consultar por identificador | **"Ver detalle"**, o directamente `https://localhost:8443/escolar/estudiantes/?id=1` |
| Actualizar | **"Editar"** |
| Eliminar | **"Eliminar"**, con diálogo de confirmación. Un estudiante con historial (representantes, autorizaciones o retiros) no se borra: se sugiere marcarlo inactivo. |

### 6.4 Chat en tiempo real

**Panel → Chat institucional.** Para verlo en acción, abre dos navegadores (o una ventana normal y otra de incógnito) con dos cuentas del mismo colegio, o con el Administrador del Sistema:

- Los mensajes aparecen **al instante**, sin recargar la página.
- El historial queda **guardado en la base de datos**.
- La franja **"En línea (n)"** muestra **quién está conectado** y se actualiza sola cuando alguien entra o sale.
- Fuera del chat llega un **aviso emergente** de mensaje nuevo, además de **notificaciones** en tiempo real (solicitudes de cuidadores, aprobaciones, cuentas bloqueadas).

### 6.5 Documentación de la API

- Swagger UI: **https://localhost:8443/api/docs/**
- ReDoc: **https://localhost:8443/api/redoc/**

Las rutas usan la sesión del navegador: inicia sesión primero y luego abre Swagger en la misma pestaña.

---

## 7. Rutas principales

### Web

| Ruta | Uso |
|---|---|
| `/` | Redirige al panel correspondiente según el rol |
| `/escolar/` | Panel del Administrador Escolar |
| `/sistema/` | Panel del Administrador del Sistema |
| `/autenticacion/ingresar/` | Inicio de sesión |
| `/autenticacion/registrar/` | Registro de una institución y su Administrador Escolar |
| `/autenticacion/recuperar/` | Solicitud de recuperación de contraseña |
| `/api/docs/` · `/api/redoc/` · `/api/schema/` | Swagger UI, ReDoc y esquema OpenAPI |
| `/salud/` | Comprobación HTTP y de conexión a la base de datos |

### API REST

Todas las rutas usan el prefijo `/api/v1/`.

| Prefijo | Recursos |
|---|---|
| `/autenticacion/` | Sesión, perfil, inicio y cierre de sesión, recuperación |
| `/instituciones/` | Registro, aprobación, institución actual, cursos y puertas |
| `/cuentas/` | Usuarios, estudiantes (con `?page=`, `?q=` y `?estado=`) y relaciones padre-estudiante |
| `/cuidadores/` | Cuidadores, solicitudes y autorizaciones |
| `/auditoria/` | Consultas de bitácora técnica y operativa |
| `/notificaciones/` | Consulta y marcado de notificaciones |
| `/chat/` | Salas, mensajes persistidos y usuarios conectados (`/chat/conectados/`) |

La API usa sesiones de Django. Las mutaciones requieren CSRF, y el usuario autenticado determina su institución: nunca un `institucion_id` enviado por el cliente.

### WebSocket

`/ws/notificaciones/` usa la sesión autenticada de Django. Transporta notificaciones, mensajes de chat y cambios de presencia, y admite heartbeat. No confía en un identificador de usuario enviado por el cliente. Ver [sección 10](#10-tiempo-real-con-websocket).

---

## 8. Pruebas y verificaciones

### Python (pytest)

Las pruebas usan una configuración aislada (`tests/settings.py`, SQLite en memoria): **no tocan SQL Server ni tus datos**.

Con Docker:

```bash
docker compose run --rm --no-deps app python -m pytest --ds=tests.settings
```

> Dentro de Docker hay que indicar `--ds=tests.settings`, porque el contenedor fija `DJANGO_SETTINGS_MODULE=config.settings`.

O con Python instalado localmente:

```bash
python -m pip install -r requirements.txt
python -m pytest
```

### JavaScript (Node.js)

```bash
node --test tests/frontend.test.mjs
```

### Verificaciones de Django (con los servicios levantados)

```bash
docker compose exec app python manage.py check
docker compose exec app python manage.py showmigrations
```

### Qué cubren las pruebas

| Archivo | Qué prueba |
|---|---|
| `tests/test_registro.py` | Registro: validaciones de cédula, RUC, teléfono, correo y contraseña; duplicados; CSRF; flujo pendiente → aprobación o rechazo → ingreso |
| `tests/test_estudiantes.py` | CRUD: paginación y búsqueda en el servidor, filtro por estado, eliminación segura, aislamiento entre colegios |
| `tests/test_presencia.py` | Usuarios conectados: alcance por institución, WebSocket que anuncia conexión y desconexión, funcionamiento sin Redis |
| `tests/test_seed_demo.py` | Script de datos de prueba: no duplica y funciona con ids de institución grandes |
| `tests/test_panel.py` | Autenticación, recuperación de contraseña, permisos por rol, contraseña temporal, aislamiento entre colegios, bitácora inmutable, escape de HTML, chat, cuidadores e instituciones |
| `tests/frontend.test.mjs` | Cliente de la API (CSRF, errores), catálogos de pantallas y verificación de la cadena de la bitácora |

---

## 9. Requisitos del primer bimestre

### Funcionales

| Requisito | Dónde se cumple |
|---|---|
| Registro (SignUp) con validación | `/autenticacion/registrar/`: formulario renderizado en el servidor (`apps/panel_escolar/forms.py`), validado en el cliente y en el servidor |
| Inicio de sesión contra la BD, contraseña con hash y sal | `apps/autenticacion/services.py` · **Argon2** (`PASSWORD_HASHERS` en `config/settings.py`) |
| Recuperación de clave con token de un solo uso y caducidad | Token aleatorio de 32 bytes; en la BD solo se guarda su hash SHA-256; caduca en 30 min y se invalida al usarse |
| Pantalla principal solo con sesión | `/escolar/` y `/sistema/`: sin sesión redirigen al inicio de sesión. Menú con CRUD, chat y cerrar sesión. |
| CRUD de la entidad principal (Estudiante) | Ver [6.3](#63-crud-de-estudiantes-entidad-principal). Estudiante: cédula, nombres, apellidos, fecha de nacimiento, curso, hora de salida especial y estado |
| Chat con WebSocket | Sala general por colegio, mensajes en tiempo real, historial en la BD, usuarios conectados y notificaciones. Ver [10](#10-tiempo-real-con-websocket). |
| Base de datos documentada | [`docs/ER.md`](docs/ER.md) y [`docs/erDiagram.mmd`](docs/erDiagram.mmd) |

### No funcionales

| Requisito | Cómo se cumple |
|---|---|
| Validación en el cliente | Atributos HTML5 (`required`, `pattern`, `minlength`, `maxlength`, `type=email`) y mensajes en español junto a cada campo |
| Validación en el servidor | Formularios y serializers de Django; validadores de cédula y RUC ecuatorianos (`shared/utils/validadores.py`) |
| Rutas protegidas y sesiones seguras | Sesión de Django: cookie `HttpOnly` y `SameSite=Lax` (más `Secure` y HSTS con `DJANGO_DEBUG=False`); expira tras 30 min de inactividad |
| Inyección SQL | Todas las consultas usan el ORM de Django (parametrizadas) |
| XSS | Autoescape de plantillas y `escapeHTML` en el JavaScript de los paneles |
| CSRF | Token CSRF en formularios y en todas las peticiones que modifican datos (cabecera `X-CSRFToken`) |
| Secretos | En variables de entorno (`.env`), fuera del repositorio |
| Aislamiento entre colegios | Cada consulta se filtra por la institución del usuario (`shared/tenancy`) |
| Navegabilidad | Menú lateral coherente en ambos paneles |
| Rendimiento | Paginación en el servidor, índices en los campos de búsqueda y chat sin recargar. Ver [13](#13-rendimiento). |
| Calidad | Pruebas automatizadas ([8](#8-pruebas-y-verificaciones)) y este README |

---

## 10. Tiempo real con WebSocket

El servidor WebSocket es parte de la misma aplicación: **Django Channels** sobre el servidor ASGI **Daphne**. No usa servicios externos.

### Handshake y seguridad

1. El navegador abre `wss://localhost:8443/ws/notificaciones/`. La petición HTTP lleva la cabecera `Upgrade: websocket` y viaja cifrada por **TLS** gracias al proxy Caddy.
2. `AllowedHostsOriginValidator` **rechaza orígenes** que no estén en `DJANGO_ALLOWED_HOSTS`.
3. `AuthMiddlewareStack` identifica al usuario con la **cookie de sesión** de Django. El cliente nunca envía su id.
4. Si no hay sesión, el servidor cierra con el código **4001**.
5. Cada mensaje recibido se **valida**: tamaño máximo de 4 KB, JSON válido y solo eventos permitidos.

### Eventos

| Dirección | Evento | Para qué |
|---|---|---|
| Cliente → servidor | `ping` | Mantener viva la conexión y renovar la presencia |
| Cliente → servidor | `presencia` | Marcarse `ACTIVO` o `AUSENTE` |
| Cliente → servidor | `notificacion.leer` | Marcar una notificación como leída |
| Servidor → cliente | `chat.mensaje` | Nuevo mensaje en la sala general |
| Servidor → cliente | `presencia.cambio` | Alguien se conectó o desconectó (actualiza "En línea") |
| Servidor → cliente | `notificacion.nueva` | Solicitud de cuidador, aprobación, cuenta bloqueada… |

### Respaldo ante fallos

- Si se corta la conexión, el navegador **reintenta** hasta 5 veces con espera creciente (1 s, 2 s, 4 s…). El botón **"Actualizar"** del chat recarga los mensajes por la API REST.
- Los mensajes y notificaciones **se guardan primero en la base** y luego se emiten. Si Redis falla, nada se pierde: la página los recupera por la API REST.
- La presencia vive en Redis con expiración de 120 s, así que una conexión que se corta sin avisar desaparece sola de la lista.

---

## 11. Base de datos

SQL Server con **20 tablas de negocio en 7 módulos**: instituciones, cuentas, autenticación, cuidadores, retiros, chat y auditoría.

- Diagrama y descripción: [`docs/ER.md`](docs/ER.md) · [`docs/erDiagram.mmd`](docs/erDiagram.mmd)
- **Bitácora inmutable** en tres capas: el código impide modificar o borrar eventos, un **disparador** de SQL Server rechaza `UPDATE` y `DELETE`, y cada evento guarda el **hash SHA-256** del anterior (cadena de integridad).
- Índices en los campos de búsqueda, por ejemplo `(institucion_id, apellidos)` y `(institucion_id, cedula)` en estudiantes.

---

## 12. Estructura del proyecto

```
retiro-backend-api/
├── docker-compose.yml        # db + redis + app + proxy
├── Dockerfile                # Python 3.12 + driver ODBC 18 de SQL Server
├── .env.example              # plantilla de variables (sin secretos)
├── proxy/Caddyfile           # HTTPS y WSS locales
├── scripts/seed_demo.py      # datos ficticios de demostración
├── docs/                     # diagrama E-R, colección de Postman
├── tests/                    # pruebas automatizadas
└── src/
    ├── config/               # settings, urls, asgi (HTTP + WebSocket)
    ├── shared/               # tenancy, permisos, validadores, comandos
    ├── templates/            # plantillas HTML (escolar/, sistema/)
    ├── static/               # CSS y JavaScript de los paneles
    └── apps/                 # módulos (ver sección 2)
```

Cada módulo separa **modelos**, **servicios** (lógica de negocio), **vistas** y **rutas**. Las vistas no contienen lógica de negocio: llaman a los servicios.

---

## 13. Rendimiento

Medidas aplicadas:

- **Paginación en el servidor** del listado de estudiantes (20 por página).
- **Índices** en los campos de búsqueda (apellidos y cédula por institución).
- **Chat sin recargar**: actualización por WebSocket.
- Respuestas comprimidas por el proxy (`encode gzip`).

### Medición

Informe de **Lighthouse** (Chrome → DevTools → Lighthouse, modo *Navigation*, dispositivo *Desktop*) sobre la pantalla de Estudiantes con sesión iniciada:

| Métrica | Resultado |
|---|---|
| Performance | _pendiente_ |
| Accessibility | _pendiente_ |
| Best Practices | _pendiente_ |
| Tiempo de respuesta de `GET /api/v1/cuentas/estudiantes/?page=1` | _pendiente_ |

> El informe completo se guarda en `docs/rendimiento/`.

---

## 14. Comandos útiles y solución de problemas

| Qué | Comando |
|---|---|
| Ver el estado de los servicios | `docker compose ps` |
| Ver los logs de la app (y los correos simulados) | `docker compose logs app --tail 60` |
| Reconstruir la app tras cambiar código | `docker compose up -d --build app` |
| Apagar (conserva los datos) | `docker compose down` |
| **Apagar y borrar la base de datos** | `docker compose down -v` |
| Volver a cargar los datos de prueba | `docker compose exec app python scripts/seed_demo.py` |

**El navegador dice "No es seguro".** Es normal: el certificado HTTPS es local (Caddy). Pulsa *Avanzado → Continuar*.

**`app` no arranca o se reinicia.** Revisa `docker compose logs app`. Lo más común es que `MSSQL_SA_PASSWORD` o `DB_PASSWORD` no cumplan la complejidad que exige SQL Server.

**`ports are not available: ... 127.0.0.1:1433`.** Ya tienes un SQL Server instalado en tu equipo usando el puerto 1433. Agrega `DB_HOST_PORT=14333` a tu `.env` y vuelve a ejecutar `docker compose up -d`. Para conectar SSMS usa `localhost,14333`.

**"Credenciales inválidas" con una cuenta de prueba.** Revisa que la contraseña sea exactamente el valor de `SEED_PASSWORD`, con mayúsculas y símbolos. Tras 3 intentos fallidos, la cuenta se bloquea 15 minutos.

**¿Puedo ejecutar el script de semillas varias veces?** Sí. No duplica registros y funciona aunque SQL Server haya saltado los ids (salta de 1000 en 1000 al reiniciarse). Para empezar de cero: `docker compose down -v` y vuelve a la [sección 4.3](#43-levantar-el-proyecto). **Esto borra todos los datos.**

**Las pruebas intentan conectarse a SQL Server.** Falta `--ds=tests.settings` en el comando de pytest dentro de Docker.

---

## 15. Convenciones para contribuir

1. Los datos que pertenecen a una institución deben heredar de `TenantModel` y respetar el contexto de tenancy. `sin_filtro()` se reserva para procesos internos, como semillas y tareas del sistema.
2. No confíes en la institución que envía el cliente: obtén el ámbito del usuario autenticado.
3. Las referencias entre módulos se manejan por id, no con importaciones directas de modelos ni claves foráneas entre aplicaciones. Dentro de un módulo sí se pueden usar claves foráneas.
4. Los tokens se almacenan como hashes. Los secretos TOTP y las fotos usan campos cifrados; las firmas de cuidadores y autorizaciones usan HMAC.
5. La auditoría es de solo adición. No intentes editar ni borrar eventos: el disparador de SQL Server también bloquea los cambios directos.
6. Agrega migraciones al modificar modelos y mantén actualizada la documentación relacionada.

---

## 16. Documentación adicional y equipo

- [Guía del equipo](GUIA_DEL_EQUIPO.md): base de datos, Docker, tenancy y convenciones.
- [Diagrama entidad-relación](docs/ER.md): modelos y relaciones.
- [Colección de Postman](docs/postman/README.md).

| Integrante | Aporte principal |
|---|---|
| Evelin Rocha | Base de datos, modelos, Docker, bitácora inmutable, datos de prueba |
| Alison | API de autenticación, cuentas e instituciones; gestión escolar, correo y recuperación segura |
| Génesis | Cuidadores, auditoría, notificaciones y WebSocket |
| Christian Puchaicela | Panel del Administrador Escolar |
| Esteban | Panel del Administrador del Sistema y chat |

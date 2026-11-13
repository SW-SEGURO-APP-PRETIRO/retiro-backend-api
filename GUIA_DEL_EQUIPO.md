# Guía del equipo: base de datos y Docker

## 1. Qué está implementado

El repositorio contiene el **esqueleto del monolito modular** (Django + SQL Server + Redis) y **toda la base de datos**: las 20 tablas de negocio de los 7 módulos, con sus migraciones aplicadas y probadas en SQL Server real.

### Infraestructura (Docker)

| Archivo | Qué hace |
|---|---|
| `Dockerfile` | Construye la imagen de la app: Python 3.12, driver ODBC 18 de Microsoft para SQL Server, librerías de `requirements.txt`. |
| `docker-compose.yml` | Arranca 4 servicios: `db` (SQL Server 2022), `redis`, `app` (Daphne, HTTP y WebSocket) y `proxy` (Caddy, HTTPS). |
| `proxy/Caddyfile` | Proxy con certificado local. Reenvía HTTPS y WebSocket (`wss://`) a la app. |
| `.env.example` | Plantilla de variables de entorno, sin secretos. El `.env` real **nunca** se sube. |
| `.gitignore` | Bloquea `.env`, cachés de Python y archivos del editor. |
| `requirements.txt` | Librerías de Python. |

Al arrancar, `app` ejecuta en orden: `esperar_bd` (espera a SQL Server y crea la base y el usuario si no existen), `migrate` (crea las tablas y el disparador de la bitácora) y Daphne.

### Base de datos: 20 tablas en 7 módulos

| Módulo | Tablas | Estado |
|---|---|---|
| `instituciones` | `Institucion`, `Curso`, `Puerta`, `TokenVerificacion` | Hecho, con migración |
| `cuentas` | `Usuario`, `Estudiante`, `RelacionPadreEstudiante` | Hecho, con migración |
| `autenticacion` | `TokenRecuperacion` | Hecho, con migración |
| `cuidadores` | `Cuidador`, `AutorizacionCuidador`, `PersonaBloqueada` | Hecho, con migración |
| `retiros` | `SesionSalida`, `PaseQR`, `PaseEstudiante`, `Retiro` | Hecho, con migración |
| `chat` | `Notificacion`, `SalaChat`, `SalaParticipante`, `MensajeChat` | Hecho, con migración |
| `auditoria` | `EventoAuditoria` (+ disparador que la hace inmutable) | Hecho, con migración |

Total en SQL Server: 26 tablas (las 20 de negocio más 6 propias de Django: sesiones, permisos y migraciones). **No se toman en cuenta la entidades de salaChat, sala Paritcipante, MensajeChAT DEBIDO QUE NO SE IMPLEMENTA EL CHTA**

**Lo que ya está verificado en un equipo real:** SQL Server arranca, todas las migraciones se aplican, `https://localhost:8443/salud/` responde `{"estado": "ok"}`, la semilla se ejecuta dos veces sin duplicar datos y la bitácora rechaza modificaciones (ver sección 3).

**Qué significa "hecho":** las tablas, sus relaciones y sus reglas de integridad existen. La **lógica de cada módulo** (servicios, vistas, formularios) la escribe cada responsable encima de estas tablas.

### Tablas del chat (decisión pendiente del equipo)

`Notificacion` es lo que se usa para las alertas en tiempo real (por ejemplo "retiro realizado"). `SalaChat`, `SalaParticipante` y `MensajeChat` están modeladas y migradas porque el documento de requerimientos define sala general por institución con historial en la base de datos, pero **no se implementan debio a que con el docente se converso sobre las notificaciones push** 

### Código compartido (`src/shared`)

| Archivo | Qué hace |
|---|---|
| `tenancy/context.py`, `tenancy/models.py` | **Aislamiento por institución.** `TenantModel` es la clase base de toda tabla de un colegio. Su manager filtra automáticamente por la institución del usuario, y **sin institución no devuelve nada**. |
| `middlewares/tenancy.py` | Fija la institución del usuario autenticado en cada petición web. |
| `utils/validadores.py` | Valida cédula y RUC ecuatorianos. |
| `management/commands/esperar_bd.py` | Comando que prepara la base de datos al arrancar. |

### Configuración (`src/config`)

`settings.py`, `urls.py` (incluye `/salud/`), `asgi.py` y `routing.py`. **Son valores iniciales**: quien tenga la responsabilidad de esa área puede ajustarlos (sesiones, Argon2 y cabeceras → Auth/Seguridad; capa de canales, `asgi` y `routing` → tiempo real).

### Datos de demostración

`scripts/seed_demo.py` crea datos ficticios: 2 colegios, 9 usuarios (1 Administrador del Sistema y 4 por colegio: Admin Escolar, Padre, Guardia y Cuidador Fijo), cursos, puerta, 4 estudiantes y sus relaciones padre-hijo. Se puede ejecutar varias veces sin duplicar. **No carga** cuidadores, pases, retiros ni notificaciones: cada responsable agrega los datos de su módulo cuando tenga su lógica.

### Diagrama E-R

`docs/ER.md` (y `docs/er.png` si está subido). Cubre las 17 tablas.

---

## 2. Cómo levantar el proyecto (después de clonar)

Requisitos: Git y Docker Desktop (con Compose v2) funcionando. No hace falta instalar Python.

**1. Clonar**

```
git clone https://github.com/SW-SEGURO-APP-PRETIRO/retiro-backend-api.git
cd retiro-backend-api
```

Mientras el trabajo no esté fusionado en `main`, usa la rama: `git checkout feat/base-de-datos-y-docker`.

**2. Crear tu `.env`**

Windows: `copy .env.example .env` · Linux/Mac: `cp .env.example .env`

Edita **solo tu `.env`** y cambia:

| Variable | Qué poner |
|---|---|
| `MSSQL_SA_PASSWORD` | Contraseña tuya: mínimo 8 caracteres, con mayúscula, minúscula, número y símbolo |
| `DB_PASSWORD` | Otra contraseña distinta, igual de compleja |
| `DJANGO_SECRET_KEY` | Cadena aleatoria (ver abajo) |
| `FIELD_ENCRYPTION_KEY` | Clave Fernet (ver abajo) |
| `HMAC_SIGNING_KEY` | Cadena aleatoria (ver abajo) |

Generar las claves (con Docker, sin instalar nada):

```
docker compose run --rm --no-deps app python -c "import secrets; print(secrets.token_urlsafe(50))"
docker compose run --rm --no-deps app python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

La primera construye la imagen y tarda unos minutos. Úsala dos veces para `DJANGO_SECRET_KEY` y `HMAC_SIGNING_KEY`, y la segunda para `FIELD_ENCRYPTION_KEY`.

**3. Levantar todo**

```
docker compose up --build -d
docker compose ps
```

La primera vez descarga SQL Server (~1,5 GB). Espera a que `db` diga `healthy`.

**4. Comprobar**

Abre `https://localhost:8443/salud/`. El navegador avisará "No es seguro" porque el certificado es local: pulsa *Avanzado → Continuar*. Debe responder `{"estado": "ok"}`.

**5. Cargar datos de prueba**

```
docker compose exec app python scripts/seed_demo.py
```

La contraseña de todas las cuentas de demostración es el valor de `SEED_PASSWORD` de tu `.env`.

### Comandos útiles

| Qué | Comando |
|---|---|
| Ver estado | `docker compose ps` |
| Ver logs de la app | `docker compose logs app --tail 60` |
| Apagar (conserva los datos) | `docker compose down` |
| **Apagar y borrar la base de datos** | `docker compose down -v` |
| Reconstruir la app tras cambiar código | `docker compose up -d --build app` |
| Listar las tablas | ver recuadro abajo |

Listar las tablas de la base:

```
docker compose exec db sh -c "/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P $MSSQL_SA_PASSWORD -d retiro_escolar -Q 'SELECT name FROM sys.tables ORDER BY name'"
```

> **Importante:** el código se copia dentro de la imagen al construirla. Si cambias un archivo, hay que **reconstruir** (`--build app`) para que la app lo use.

> **Si cambias la contraseña `sa` en tu `.env` después del primer arranque**, SQL Server no se entera (queda fijada en el volumen). Hay que usar `docker compose down -v` y volver a levantar.

### Ver la base con DBeaver o SSMS

En `docker-compose.yml`, descomenta el puerto `127.0.0.1:1433:1433` del servicio `db` y reinicia. Conecta a `localhost,1433` con el usuario `retiro_app` y tu `DB_PASSWORD`, marcando "Trust server certificate". Nunca publiques ese puerto en un servidor.

---

## 3. La bitácora inmutable (`EventoAuditoria`)

La bitácora no se puede modificar ni borrar, y esto se impone en **tres capas**:

1. **Python:** `save()` sobre un evento existente, `delete()` y `update()` masivos lanzan error (en `auditoria/models.py`).
2. **Base de datos:** un disparador `trg_auditoria_inmutable` (tipo `INSTEAD OF UPDATE, DELETE`, creado por la migración `0002_bitacora_inmutable`) rechaza cualquier modificación, **incluso por SQL directo**.
3. **Cadena de hashes:** cada evento guarda el hash del anterior (`hash_anterior`, `hash_propio` con SHA-256), y `(institucion_id, secuencia)` es único. Si alguien altera o inserta algo fuera de orden, la cadena se rompe y se puede detectar.

**Probar la capa 2 en vivo** (sirve para la defensa):

```
docker compose exec -T db sh -c "/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P $MSSQL_SA_PASSWORD -d retiro_escolar" < scripts\probar_bitacora.sql
```

(En Linux/Mac usa `scripts/probar_bitacora.sql`.) El resultado esperado: el `INSERT` funciona, el `UPDATE` y el `DELETE` fallan con *"La bitacora es inmutable"* (Msg 51000), y al final no queda ninguna fila de prueba. El aviso `Msg 3903 ROLLBACK` que aparece después es normal: el error del disparador ya canceló la transacción.

**Detalles que deben conocer quienes escriban en la bitácora:**

- Los eventos globales (sin institución) usan `institucion_id = 0`, no `NULL`, para que la restricción de unicidad de la cadena funcione igual en SQL Server.
- Si la bitácora rechaza un cambio, SQL Server **cancela toda la transacción**. Si el retiro y su evento van en la misma transacción, un fallo en la bitácora deshace también el retiro (comportamiento "falla cerrado" del documento de requerimientos).
- El servicio que registra eventos (`registrar_evento`) y el que verifica la cadena (`verificar_cadena`) **no están en este repositorio**: corresponden al responsable de Auditoría. La tabla y sus protecciones sí están listas.

---

## 4. Cómo trabajar encima (reglas para el equipo)

### Cada módulo escribe su lógica sobre sus propias tablas

Los modelos van en `src/apps/<módulo>/models.py`. Si necesitas un campo en un módulo que no es tuyo, pídelo a su responsable.

### Reglas del monolito modular

1. **Toda tabla de un colegio hereda de `TenantModel`** (`from shared.tenancy.models import TenantModel`). Así lleva `institucion_id` y el filtro automático.
2. **Entre módulos, las referencias son por número, sin `ForeignKey`.** Por ejemplo `curso_id = models.PositiveBigIntegerField()` en lugar de apuntar a `Curso`. Dentro de un mismo módulo sí se usan claves foráneas.
3. **No importes `models` de otro módulo.** Usa sus `services.py` o `selectors.py`.
4. **`sin_filtro()` es solo para procesos internos** (semillas, tareas del sistema). Nunca lo uses desde una vista.
5. **En un consumer de WebSocket** el middleware HTTP no corre: fija la institución a mano con `contexto_institucion(...)` (`shared/tenancy/context.py`).
6. **El rol de un usuario no se puede cambiar** después de crear la cuenta.
7. **Los tokens nunca se guardan en claro**: guarda solo su hash.

### Generar una migración (si cambias un modelo)

Genérala **escribiendo en tu carpeta** (no dentro del contenedor):

```
docker run --rm --env-file .env -v "%cd%":/app retiro-backend-api-app python manage.py makemigrations <modulo>
```

- En PowerShell usa `${PWD}` en lugar de `%cd%`, y en Linux/Mac `$(pwd)`.
- `<modulo>` es el nombre de la carpeta (`instituciones`, `cuentas`, `autenticacion`, `cuidadores`, `retiros`, `chat`, `auditoria`).
- Es normal que aparezca un aviso "Login timeout expired": solo significa que ese comando no necesita la base.
- Sube el archivo de migración nuevo (por ejemplo `0003_...py`).
- Luego `docker compose up -d --build app` para aplicarlo.

---

## 5. Cómo leer el diagrama E-R (`docs/ER.md`)

El diagrama dibuja las tablas con sus columnas y cómo se relacionan.

| Elemento | Significado |
|---|---|
| Recuadro | Una tabla |
| `PK` | Clave primaria (el `id`) |
| `UK` | Valor único: no puede repetirse (`ruc`, `correo`, `hash_token`) |
| `FK` | Clave foránea real, solo dentro del mismo módulo |
| Línea continua | Relación con clave foránea |
| Línea punteada | Referencia por número entre módulos, **sin** clave foránea |
| `bigint` | Entero grande de SQL Server (ids y referencias) |

### Decisiones de diseño que el diagrama refleja

1. **Una tabla por colegio, un campo `institucion_id` por tabla.** Todos los colegios comparten las mismas tablas, y el filtro automático evita que uno vea datos de otro.
2. **Los cinco roles viven en `Usuario`.** Se distinguen por el campo `rol` (Administrador del Sistema, Administrador Escolar, Padre, Guardia y Cuidador Fijo). No hay una tabla por rol, porque todos comparten correo, contraseña y estado.
3. **`Estudiante` está en `cuentas`** junto a `Usuario`, porque `RelacionPadreEstudiante` necesita claves foráneas reales hacia ambos y estas solo existen dentro de un mismo módulo. El estudiante no inicia sesión.
4. **El Administrador del Sistema no tiene institución.** Una regla en la propia base exige que todos los demás roles sí la tengan.
5. **`Cuidador` es una persona, no una cuenta.** Un cuidador temporal no tiene cuenta; el fijo sí, y se enlaza por `Cuidador.usuario_id` con su fila en `Usuario`.
6. **`AutorizacionCuidador`** relaciona un cuidador con un estudiante (quién la solicitó, quién emitió el acceso, cuándo se revocó). Lleva una firma HMAC para detectar manipulación. Hay una sola autorización viva por cuidador y estudiante.
7. **Pases QR:** `SesionSalida` es la salida del cuidador fijo (dura 20 minutos); `PaseQR` es cada código (los dinámicos rotan cada 30 segundos y pertenecen a una sesión; el estático del temporal no tiene sesión); `PaseEstudiante` dice qué estudiantes cubre un pase (puede ser más de uno); `Retiro` es la entrega confirmada por el guardia. Un estudiante solo puede retirarse **una vez por día** (restricción única sobre `estudiante_id` + `fecha`).
8. **Se guarda el hash, no el token** (`TokenVerificacion`, `TokenRecuperacion`, `PaseQR`).
9. **Reglas en la base de datos, no solo en el código:** un correo y un RUC no se repiten; una persona (cédula) tiene una sola cuenta por colegio; un pase `USADO` debe tener fecha de uso; solo hay una sala general por colegio.
10. **Cifrado:** los campos `foto_cifrada`, `foto_entrega_cifrada` y `totp_secreto_cifrado` existen como columnas binarias o de texto. El cifrado en sí lo implementa Criptografía.
11. **La bitácora es de solo adición** (ver sección 3).

---


### Cómo cambiar el modelo si algo no convence

El diagrama es el dibujo de los modelos, así que un cambio acordado afecta al código:

1. El dueño del módulo edita su `models.py`.
2. Genera una migración nueva (`makemigrations`) y la sube.
3. Se actualizan `docs/ER.md` y, si toca campos que llena, `scripts/seed_demo.py`.
4. Cada compañero hace `git pull`, reconstruye (`docker compose up -d --build app`) y, si lo necesita, reinicia su base con `docker compose down -v`.
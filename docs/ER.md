# Diagrama entidad-relación del sistema

Las 17 tablas de negocio de los 7 módulos del monolito.

- **Línea continua:** clave foránea real (solo dentro del mismo módulo).
- **Línea punteada:** referencia por id entre módulos, sin clave foránea (regla MM-03).
- Todas las tablas de un colegio llevan `institucion_id` (aislamiento por colegio). Para no saturar el diagrama solo se dibuja la línea en las tablas principales.
- Los **cinco roles** (Administrador del Sistema, Administrador Escolar, Padre, Guardia y Cuidador Fijo) se guardan en `Usuario`, diferenciados por el campo `rol`.
- `Cuidador` guarda a la persona que retira; si es fijo, `usuario_id` apunta a su cuenta en `Usuario`.
- `institucion_id = 0` en `EventoAuditoria` indica un evento global (sin institución).
- El módulo `chat` solo persiste las notificaciones; el envío en tiempo real va por WebSocket y push, sin tablas de mensajes.

| Módulo | Tablas |
|---|---|
| instituciones | Institucion, Curso, Puerta, TokenVerificacion |
| cuentas | Usuario, Estudiante, RelacionPadreEstudiante |
| autenticacion | TokenRecuperacion |
| cuidadores | Cuidador, AutorizacionCuidador, PersonaBloqueada |
| retiros | SesionSalida, PaseQR, PaseEstudiante, Retiro |
| chat | Notificacion |
| auditoria | EventoAuditoria |

```mermaid
erDiagram
    Institucion ||..o{ Curso : "institucion_id"
    Institucion ||..o{ Puerta : "institucion_id"
    Institucion ||..o{ TokenVerificacion : "institucion_id"
    Institucion ||..o{ Usuario : "institucion_id"
    Institucion ||..o{ Estudiante : "institucion_id"
    Curso ||..o{ Estudiante : "curso_id"
    Puerta ||..o{ Usuario : "puerta_id (guardia)"
    Puerta ||..o{ Retiro : "puerta_id"
    Usuario ||--o{ RelacionPadreEstudiante : "padre"
    Estudiante ||--o{ RelacionPadreEstudiante : "estudiante"
    Usuario ||..o{ TokenRecuperacion : "usuario_id"
    Usuario ||..o| Cuidador : "usuario_id (fijo)"
    Cuidador ||--o{ AutorizacionCuidador : "cuidador"
    Estudiante ||..o{ AutorizacionCuidador : "estudiante_id"
    Usuario ||..o{ AutorizacionCuidador : "solicitada_por_id"
    Estudiante ||..o{ PersonaBloqueada : "estudiante_id"
    Cuidador ||..o{ SesionSalida : "cuidador_id"
    Cuidador ||..o{ PaseQR : "cuidador_id"
    SesionSalida ||--o{ PaseQR : "sesion"
    PaseQR ||--o{ PaseEstudiante : "pase"
    Estudiante ||..o{ PaseEstudiante : "estudiante_id"
    PaseQR ||--o{ Retiro : "pase"
    Estudiante ||..o{ Retiro : "estudiante_id"
    Usuario ||..o{ Retiro : "guardia_id"
    Usuario ||..o{ Notificacion : "destinatario_id"
    Usuario ||..o{ EventoAuditoria : "actor_id"

    Institucion {
        bigint id PK
        string nombre
        string ruc UK
        string direccion
        string telefono
        string correo UK
        string responsable
        string estado
        string motivo_estado
        datetime creada_en
        datetime aprobada_en
        bigint aprobada_por_id
    }
    Curso {
        bigint id PK
        bigint institucion_id
        string nombre
        time hora_salida
        bool activo
    }
    Puerta {
        bigint id PK
        bigint institucion_id
        string nombre
        bool activa
    }
    TokenVerificacion {
        bigint id PK
        bigint institucion_id
        string hash_token UK
        datetime expira_en
        datetime usado_en
    }
    Usuario {
        bigint id PK
        bigint institucion_id
        string correo UK
        string cedula
        string nombres
        string apellidos
        string telefono
        string rol
        string estado
        bigint puerta_id
        text totp_secreto_cifrado
        bool contrasena_temporal
        datetime expira_temporal
        int intentos_fallidos
        datetime bloqueado_hasta
        datetime creado_en
    }
    Estudiante {
        bigint id PK
        bigint institucion_id
        string cedula
        string nombres
        string apellidos
        date fecha_nacimiento
        bigint curso_id
        time hora_salida_especial
        binary foto_cifrada
        string estado
    }
    RelacionPadreEstudiante {
        bigint id PK
        bigint institucion_id
        bigint padre_id FK
        bigint estudiante_id FK
        bool vigente
    }
    TokenRecuperacion {
        bigint id PK
        bigint usuario_id
        string hash_token UK
        datetime creado_en
        datetime expira_en
        datetime usado_en
    }
    Cuidador {
        bigint id PK
        bigint institucion_id
        string tipo
        bigint usuario_id
        string cedula
        string nombres
        string apellidos
        string telefono
        string correo
        binary foto_cifrada
        string firma_hmac
        datetime creado_en
    }
    AutorizacionCuidador {
        bigint id PK
        bigint institucion_id
        bigint cuidador_id FK
        bigint estudiante_id
        bigint solicitada_por_id
        string estado
        datetime solicitada_en
        bigint acceso_emitido_por_id
        datetime acceso_emitido_en
        datetime revocada_en
        string firma_hmac
    }
    PersonaBloqueada {
        bigint id PK
        bigint institucion_id
        bigint estudiante_id
        string cedula
        bigint registrada_por_id
        datetime registrada_en
    }
    SesionSalida {
        bigint id PK
        bigint institucion_id
        bigint cuidador_id
        datetime inicia_en
        datetime expira_en
        int rotacion_actual
        string estado
    }
    PaseQR {
        bigint id PK
        bigint institucion_id
        bigint cuidador_id
        string tipo
        bigint sesion_id FK
        string hash_token UK
        int numero_rotacion
        datetime creado_en
        datetime expira_en
        datetime usado_en
        string estado
    }
    PaseEstudiante {
        bigint id PK
        bigint institucion_id
        bigint pase_id FK
        bigint estudiante_id
        datetime retirado_en
    }
    Retiro {
        bigint id PK
        bigint institucion_id
        bigint pase_id FK
        bigint guardia_id
        bigint puerta_id
        bigint estudiante_id
        binary foto_entrega_cifrada
        datetime fecha_hora
        date fecha
    }
    Notificacion {
        bigint id PK
        bigint institucion_id
        bigint emisor_id
        bigint destinatario_id
        string tipo
        string titulo
        string mensaje
        string referencia
        bool leida
        datetime creada_en
        datetime leida_en
    }
    EventoAuditoria {
        bigint id PK
        bigint institucion_id
        bigint secuencia
        string tipo
        bigint actor_id
        string resultado
        text detalle
        datetime fecha
        string hash_anterior
        string hash_propio UK
    }
```
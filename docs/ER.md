# Diagrama entidad-relación

Tablas del módulo `instituciones` y del módulo `cuentas`.

- **Línea continua:** clave foránea real (dentro del mismo módulo).
- **Línea punteada:** referencia por id entre módulos, sin clave foránea (regla MM-03).
- Casi todas las tablas llevan `institucion_id` (aislamiento por colegio); no se dibuja cada línea para no saturar el diagrama.

```mermaid
erDiagram
    Institucion ||..o{ Curso : "institucion_id"
    Institucion ||..o{ Puerta : "institucion_id"
    Institucion ||..o{ TokenVerificacion : "institucion_id"
    Institucion ||..o{ Usuario : "institucion_id"
    Institucion ||..o{ Estudiante : "institucion_id"
    Curso ||..o{ Estudiante : "curso_id"
    Puerta ||..o{ Usuario : "puerta_id (guardia)"
    Usuario ||--o{ RelacionPadreEstudiante : "padre"
    Estudiante ||--o{ RelacionPadreEstudiante : "estudiante"

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
```
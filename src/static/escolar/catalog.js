// Los nombres y tipos corresponden a los serializers de feat/backend-api.
const f = (name, label, type = "text", extra = {}) => ({
  name,
  label,
  type,
  ...extra,
});
const identity = [
  f("nombres", "Nombres", "text", { required: true, max: 100 }),
  f("apellidos", "Apellidos", "text", { required: true, max: 100 }),
  f("cedula", "Cédula", "text", {
    required: true,
    pattern: "[0-9]{10}",
    max: 10,
  }),
  f("correo", "Correo electrónico", "email", { required: true, max: 254 }),
  f("telefono", "Teléfono", "tel", { max: 20 }),
];
export const catalog = {
  estudiantes: {
    endpoint: "cuentas/estudiantes/",
    singular: "estudiante",
    create: "Nuevo estudiante",
    columns: [
      ["persona", "Estudiante"],
      ["cedula", "Cédula"],
      ["curso", "Curso"],
      ["salida", "Salida"],
      ["estado", "Estado"],
    ],
    fields: [
      ...identity.filter((x) => !["correo", "telefono"].includes(x.name)),
      f("fecha_nacimiento", "Fecha de nacimiento", "date", { required: true }),
      f("curso_id", "Curso", "select", {
        source: "cursos",
        required: true,
        number: true,
      }),
      f("hora_salida_especial", "Salida especial", "time", {
        nullable: true,
        help: "Déjalo vacío para usar el horario del curso.",
      }),
      f("estado", "Estado", "select", {
        required: true,
        options: [
          ["ACTIVO", "Activo"],
          ["INACTIVO", "Inactivo"],
        ],
      }),
    ],
    defaults: { estado: "ACTIVO" },
    remove: true,
    // Paginación, búsqueda y filtro de estado se resuelven en el servidor (?page=&q=&estado=)
    serverPaging: true,
    serverSearch: true,
  },
  padres: {
    endpoint: "cuentas/usuarios/",
    query: "?rol=PADRE",
    singular: "representante",
    create: "Nuevo representante",
    columns: [
      ["persona", "Representante"],
      ["correo", "Correo"],
      ["telefono", "Teléfono"],
      ["estado", "Estado"],
    ],
    fields: identity,
    defaults: { rol: "PADRE" },
  },
  guardias: {
    endpoint: "cuentas/usuarios/",
    query: "?rol=GUARDIA",
    singular: "guardia",
    create: "Nuevo guardia",
    columns: [
      ["persona", "Guardia"],
      ["correo", "Correo"],
      ["puerta", "Puerta asignada"],
      ["estado", "Estado"],
    ],
    fields: [
      ...identity,
      f("puerta_id", "Puerta asignada", "select", {
        source: "puertas",
        number: true,
        nullable: true,
      }),
    ],
    defaults: { rol: "GUARDIA" },
  },
  asignaciones: {
    endpoint: "cuentas/relaciones-padre-estudiante/",
    singular: "asignación",
    create: "Vincular representante",
    columns: [
      ["estudiante", "Estudiante"],
      ["padre", "Representante"],
      ["vigente", "Vínculo"],
    ],
    fields: [
      f("estudiante", "Estudiante", "select", {
        source: "estudiantes",
        number: true,
        required: true,
      }),
      f("padre", "Padre o representante", "select", {
        source: "padres",
        number: true,
        required: true,
      }),
    ],
    defaults: { vigente: true },
    remove: true,
    noEdit: true,
  },
  cursos: {
    endpoint: "instituciones/cursos/",
    singular: "curso",
    create: "Nuevo curso",
    columns: [
      ["nombre", "Curso"],
      ["hora_salida", "Hora de salida"],
      ["activo", "Estado"],
    ],
    fields: [
      f("nombre", "Nombre del curso", "text", { max: 80, required: true }),
      f("hora_salida", "Hora de salida", "time", { required: true }),
      f("activo", "Curso activo", "checkbox"),
    ],
    defaults: { activo: true },
    remove: true,
  },
  puertas: {
    endpoint: "instituciones/puertas/",
    singular: "puerta",
    create: "Nueva puerta",
    columns: [
      ["nombre", "Puerta"],
      ["activa", "Estado"],
    ],
    fields: [
      f("nombre", "Nombre de la puerta", "text", { max: 80, required: true }),
      f("activa", "Puerta activa", "checkbox"),
    ],
    defaults: { activa: true },
    remove: true,
  },
  cuidadores: {
    endpoint: "cuidadores/autorizaciones/",
    singular: "solicitud",
    columns: [
      ["cuidador", "Cuidador"],
      ["estudiante_nombre", "Estudiante"],
      ["solicitante", "Solicitado por"],
      ["solicitada_en", "Fecha"],
      ["estado", "Estado"],
    ],
    noEdit: true,
  },
  bitacora: {
    endpoint: "auditoria/operativa/",
    singular: "evento",
    serverPaging: true,
    columns: [
      ["fecha", "Fecha y hora"],
      ["tipo", "Evento"],
      ["actor_nombre", "Actor"],
      ["resultado", "Resultado"],
    ],
    noEdit: true,
  },
  notificaciones: {
    endpoint: "notificaciones/",
    singular: "notificación",
    serverPaging: true,
    columns: [
      ["titulo", "Notificación"],
      ["mensaje", "Mensaje"],
      ["creada_en", "Recibida"],
      ["leida", "Estado"],
    ],
    noEdit: true,
  },
};
export const caregiverApplicationFields = [
  f("tipo", "Tipo de cuidador", "select", {
    required: true,
    options: [
      ["FIJO", "Cuidador fijo (con cuenta y QR dinámico)"],
      ["TEMPORAL", "Cuidador temporal (solo QR estático)"],
    ],
  }),
  f("estudiante_id", "Hijo / estudiante a retirar", "select", {
    source: "estudiantes",
    required: true,
    number: true,
  }),
  f("nombres", "Nombres del cuidador", "text", { required: true, max: 100 }),
  f("apellidos", "Apellidos del cuidador", "text", { required: true, max: 100 }),
  f("cedula", "Cédula del cuidador", "text", {
    required: true,
    pattern: "[0-9]{10}",
    max: 10,
  }),
  f("correo", "Correo electrónico", "email", {
    max: 254,
    help: "Obligatorio para cuidador fijo (recibirá sus credenciales por correo).",
  }),
  f("telefono", "Teléfono", "tel", { max: 20 }),
];

export const institutionFields = [
  f("nombre", "Nombre de la institución", "text", { required: true, max: 200 }),
  f("ruc", "RUC", "text", { required: true, pattern: "[0-9]{13}", max: 13 }),
  f("responsable", "Responsable", "text", { required: true, max: 150 }),
  f("correo", "Correo institucional", "email", { required: true, max: 254 }),
  f("telefono", "Teléfono", "tel", { required: true, max: 20 }),
  f("direccion", "Dirección", "text", { required: true, max: 255 }),
];

// Catálogo de vistas y esquemas para el Panel de Administrador del Sistema (ADMIN_SISTEMA).
// Sigue estrictamente los contratos REST existentes del monolito Django.

export const ROLES = [
  ["ADMIN_SISTEMA", "Administrador del Sistema"],
  ["ADMIN_ESCOLAR", "Administrador Escolar"],
  ["PADRE", "Padre / representante"],
  ["GUARDIA", "Guardia"],
  ["CUIDADOR_FIJO", "Cuidador fijo"],
];

export const ESTADOS_INSTITUCION = [
  ["PENDIENTE_APROBACION", "Pendiente de aprobación"],
  ["ACTIVA", "Activa"],
  ["SUSPENDIDA", "Suspendida"],
  ["RECHAZADA", "Rechazada"],
  ["PENDIENTE_VERIFICACION", "Pendiente de verificación"],
];

export const ESTADOS_USUARIO = [
  ["ACTIVA", "Activa"],
  ["PENDIENTE", "Pendiente"],
  ["BLOQUEADA", "Bloqueada"],
  ["SUSPENDIDA", "Suspendida"],
];

export const EVENTOS_TECNICOS = [
  "INGRESO_EXITOSO",
  "INTENTO_INGRESO_FALLIDO",
  "INGRESO_BLOQUEADO",
  "INGRESO_RECHAZADO",
  "INTENTO_TOTP_FALLIDO",
  "CIERRE_SESION",
  "CAMBIO_CONTRASENA",
  "SOLICITUD_RECUPERACION",
  "RECUPERACION_CONTRASENA",
  "INSTITUCION_APROBADA",
  "INSTITUCION_RECHAZADA",
  "INSTITUCION_SUSPENDIDA",
  "INSTITUCION_REACTIVADA",
  "USUARIO_BLOQUEADO",
  "USUARIO_DESBLOQUEADO",
];

export const EVENTOS_ANOMALIA = new Set([
  "INTENTO_INGRESO_FALLIDO",
  "INGRESO_BLOQUEADO",
  "INGRESO_RECHAZADO",
  "INTENTO_TOTP_FALLIDO",
]);

export const EVENTOS_INSTITUCION = new Set([
  "INSTITUCION_REGISTRADA",
  "INSTITUCION_APROBADA",
  "INSTITUCION_RECHAZADA",
  "INSTITUCION_SUSPENDIDA",
  "INSTITUCION_REACTIVADA",
]);

export const systemCatalog = {
  instituciones: {
    endpoint: "instituciones/",
    singular: "institución",
    columns: [
      ["institucion", "Institución"],
      ["ruc", "RUC"],
      ["responsable", "Responsable"],
      ["admin_escolar", "Admin. escolar"],
      ["estado", "Estado"],
      ["creada_en", "Registro"],
    ],
  },
  pendientes: {
    endpoint: "instituciones/pendientes/",
    singular: "solicitud institucional",
    columns: [
      ["institucion", "Institución"],
      ["ruc", "RUC"],
      ["correo", "Correo institucional"],
      ["admin_escolar", "Admin. escolar"],
      ["creada_en", "Solicitada"],
      ["estado", "Estado"],
    ],
  },
  administradores: {
    endpoint: "cuentas/usuarios/",
    query: "?rol=ADMIN_ESCOLAR",
    singular: "administrador escolar",
    columns: [
      ["persona", "Administrador escolar"],
      ["institucion_nombre", "Institución"],
      ["institucion_estado", "Estado colegio"],
      ["seguridad_clave", "Contraseña temporal"],
      ["estado", "Estado cuenta"],
    ],
  },
  cuentas: {
    endpoint: "cuentas/usuarios/",
    singular: "cuenta",
    columns: [
      ["persona", "Usuario"],
      ["rol_badge", "Rol"],
      ["institucion_nombre", "Institución"],
      ["seguridad_resumen", "Seguridad"],
      ["estado", "Estado"],
    ],
  },
  seguridad: {
    endpoint: "cuentas/usuarios/",
    singular: "cuenta supervisada",
    columns: [
      ["persona", "Cuenta"],
      ["rol_badge", "Rol"],
      ["institucion_nombre", "Institución"],
      ["riesgo_motivo", "Condición de seguridad"],
      ["estado", "Estado"],
    ],
  },
  bitacora: {
    endpoint: "auditoria/tecnica/",
    singular: "evento técnico",
    serverPaging: true,
    columns: [
      ["fecha", "Fecha y hora"],
      ["tipo", "Evento técnico"],
      ["actor_nombre", "Actor"],
      ["entidad_global", "Ámbito / Entidad"],
      ["integridad_hash", "Secuencia y hash"],
      ["resultado", "Resultado"],
    ],
  },
  notificaciones: {
    endpoint: "notificaciones/",
    singular: "notificación",
    serverPaging: true,
    columns: [
      ["titulo", "Alerta / Notificación"],
      ["mensaje", "Detalle"],
      ["creada_en", "Recibida"],
      ["leida", "Estado"],
    ],
  },
};

/**
 * Verifica la integridad criptográfica y de secuencia de un lote de eventos de auditoría.
 * Agrupa por institucion_id (0 = global) y comprueba:
 * 1. Que cada evento tenga hash_propio y hash_anterior de 64 caracteres hexadecimales.
 * 2. Que dentro de cada cadena (ordenada por secuencia ascendente), si dos eventos son
 *    consecutivos (secuencia N y N+1), el hash_anterior de N+1 coincida exactamente con el hash_propio de N,
 *    y que si secuencia === 1 su hash_anterior sea "0".repeat(64).
 */
export function verifyAuditChain(events) {
  const hashRegex = /^[0-9a-f]{64}$/i;
  const GENESIS = "0".repeat(64);
  const byScope = new Map();
  const anomalies = [];

  for (const ev of events || []) {
    const scope = ev.institucion_id ?? 0;
    if (!byScope.has(scope)) byScope.set(scope, []);
    byScope.get(scope).push(ev);
  }

  const chains = [];
  for (const [scope, list] of byScope.entries()) {
    const sorted = [...list].sort((a, b) => Number(a.secuencia) - Number(b.secuencia));
    let valid = true;
    const issues = [];

    for (let i = 0; i < sorted.length; i++) {
      const curr = sorted[i];
      if (!hashRegex.test(curr.hash_propio || "") || !hashRegex.test(curr.hash_anterior || "")) {
        valid = false;
        issues.push(`Secuencia #${curr.secuencia}: formato SHA-256 inválido.`);
      }
      if (Number(curr.secuencia) === 1 && curr.hash_anterior !== GENESIS) {
        valid = false;
        issues.push(`Secuencia #1: el hash anterior no coincide con el bloque génesis.`);
      }
      if (i > 0) {
        const prev = sorted[i - 1];
        if (Number(curr.secuencia) === Number(prev.secuencia)) {
          valid = false;
          issues.push(`Secuencia duplicada #${curr.secuencia}.`);
        } else if (
          Number(curr.secuencia) === Number(prev.secuencia) + 1 &&
          curr.hash_anterior !== prev.hash_propio
        ) {
          valid = false;
          issues.push(
            `Ruptura de enlace entre secuencia #${prev.secuencia} y #${curr.secuencia}.`,
          );
        }
      }
    }

    if (!valid) {
      for (const issue of issues) anomalies.push({ scope, issue });
    }
    const last = sorted[sorted.length - 1];
    chains.push({
      scope,
      count: sorted.length,
      firstSeq: sorted[0]?.secuencia ?? 0,
      lastSeq: last?.secuencia ?? 0,
      headHash: last?.hash_propio ?? GENESIS,
      status: valid ? "INTEGRA" : "INCONSISTENTE",
      issues,
    });
  }

  return {
    intact: anomalies.length === 0,
    totalEvents: (events || []).length,
    chains,
    anomalies,
  };
}

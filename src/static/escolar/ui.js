import { escapeHTML as e } from "./api.js";
const paths = {
  home: "M3 10 12 3l9 7v10H3Z M9 20v-7h6v7",
  students: "m2 8 10-5 10 5-10 5Z M6 10v6c3 3 9 3 12 0v-6 M22 8v8",
  people:
    "M16 21v-3a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v3 M9 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M17 3a4 4 0 0 1 0 8 M22 21v-3a4 4 0 0 0-3-3.87",
  shield: "m12 2 9 4v6c0 5-5 8-9 10-4-2-9-5-9-10V6Z M8 12l3 3 5-6",
  link: "M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2 M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2",
  check: "M9 11l3 3 8-8 M20 12v8H4V4h11",
  calendar: "M4 5h16v16H4Z M4 10h16 M8 2v6 M16 2v6",
  door: "M4 21h16 M7 21V3h10v18 M13 12h1",
  history: "M3 11a9 9 0 1 1 2 7 M3 4v7h7 M12 7v5l3 2",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4",
  school: "m3 9 9-6 9 6v12H3Z M9 21v-7h6v7 M6 11h1 M17 11h1",
  logout: "M10 3H3v18h7 M8 12h13 M17 8l4 4-4 4",
  menu: "M3 6h18 M3 12h18 M3 18h18",
  search: "M21 21l-5-5 M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16",
  arrow: "M4 12h16 M15 7l5 5-5 5",
  plus: "M12 4v16 M4 12h16",
  refresh: "M20 7a9 9 0 1 0 1 9 M20 2v5h-5",
};
export const icon = (name) =>
  `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.school}"/></svg>`;
export function icons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((el) => {
    el.innerHTML = icon(el.dataset.icon);
  });
}
export function name(row) {
  return row
    ? [row.nombres, row.apellidos].filter(Boolean).join(" ") ||
        row.nombre ||
        `#${row.id}`
    : "—";
}
export function person(row, subtitle = "") {
  const n = name(row);
  const initials = n
    .split(/\s+/)
    .slice(0, 2)
    .map((x) => x[0])
    .join("");
  return `<div class="person"><span class="avatar">${e(initials)}</span><div><strong>${e(n)}</strong>${subtitle ? `<small>${e(subtitle)}</small>` : ""}</div></div>`;
}
export function human(value) {
  const labels = {
    SOLICITADO: "Pendiente de revisión",
    ACCESO_EMITIDO: "Acceso emitido",
    ACTIVO: "Activo",
    ACTIVA: "Activa",
    INACTIVO: "Inactivo",
    REVOCADO: "Revocado",
    RECHAZADO: "Rechazado",
    EXPIRADO: "Expirado",
    PENDIENTE: "Pendiente",
    BLOQUEADA: "Bloqueada",
    SUSPENDIDA: "Suspendida",
    EXITO: "Exitoso",
    FALLO: "Fallido",
    ESTUDIANTE_CREADO: "Estudiante registrado",
    ESTUDIANTE_ACTUALIZADO: "Estudiante actualizado",
    USUARIO_CREADO: "Cuenta creada",
    USUARIO_ACTUALIZADO: "Cuenta actualizada",
    USUARIO_BLOQUEADO: "Cuenta desactivada",
    USUARIO_DESBLOQUEADO: "Cuenta activada",
    CURSO_CREADO: "Curso creado",
    PUERTA_CREADA: "Puerta registrada",
    RELACION_PADRE_ESTUDIANTE_CREADA: "Asignación creada",
    CUIDADOR_CREADO: "Cuidador registrado",
    AUTORIZACION_SOLICITADA: "Solicitud de cuidador",
    CUIDADOR_AUTORIZACION_APROBADA: "Solicitud aprobada",
    CUIDADOR_AUTORIZACION_REVOCADA: "Autorización revocada",
    CUIDADOR_AUTORIZACION_RECHAZADA: "Solicitud rechazada",
    INGRESO_EXITOSO: "Inicio de sesión",
    CIERRE_SESION: "Cierre de sesión",
    CAMBIO_CONTRASENA: "Cambio de contraseña",
    RECUPERACION_CONTRASENA: "Recuperación de contraseña",
    SOLICITUD_RECUPERACION: "Solicitud de recuperación",
    INGRESO_RECHAZADO: "Inicio de sesión rechazado",
    INGRESO_BLOQUEADO: "Cuenta bloqueada por seguridad",
    INTENTO_TOTP_FALLIDO: "Código de seguridad inválido",
  };
  return (
    labels[value] ||
    String(value ?? "—")
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(/^./, (c) => c.toUpperCase())
  );
}
export function badge(value) {
  const type = ["ACTIVO", "ACTIVA", "ACCESO_EMITIDO", "EXITO"].includes(value)
    ? "good"
    : ["FALLO", "BLOQUEADA", "REVOCADO", "RECHAZADO"].includes(value)
      ? "bad"
      : ["SOLICITADO", "PENDIENTE"].includes(value)
        ? "warn"
        : "neutral";
  return `<span class="badge ${type}"><span class="status-dot"></span>${e(human(value))}</span>`;
}
export function date(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? "—"
    : new Intl.DateTimeFormat("es-EC", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "America/Guayaquil",
      }).format(d);
}
export function toast(text) {
  const el = document.querySelector("#toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => {
    el.hidden = true;
  }, 5000);
}
export function fieldsHTML(fields, values, sources) {
  return fields
    .map((f) => {
      const value = values[f.name] ?? "";
      const id = `field-${f.name}`;
      const help = f.help
        ? `<small id="help-${f.name}">${e(f.help)}</small>`
        : "";
      const attrs = `id="${id}" name="${f.name}" ${f.required ? "required" : ""} ${f.max ? `maxlength="${f.max}"` : ""} ${f.pattern ? `pattern="${f.pattern}"` : ""} ${f.help ? `aria-describedby="help-${f.name}"` : ""}`;
      if (f.type === "checkbox")
        return `<label class="checkbox-field" for="${id}"><input type="checkbox" ${attrs} ${value ? "checked" : ""}>${e(f.label)}</label>`;
      let input;
      if (f.type === "select") {
        const options =
          f.options || (sources[f.source] || []).map((r) => [r.id, name(r)]);
        input = `<select ${attrs}><option value="">Selecciona una opción</option>${options.map(([v, l]) => `<option value="${e(v)}" ${String(v) === String(value) ? "selected" : ""}>${e(l)}</option>`).join("")}</select>`;
      } else
        input = `<input type="${f.type}" ${attrs} value="${e(value)}" ${f.name === "cedula" || f.name === "ruc" ? 'inputmode="numeric"' : ""} ${f.type === "date" ? `max="${new Date().toISOString().slice(0, 10)}"` : ""}>`;
      return `<label for="${id}">${e(f.label)}${f.required ? ' <span aria-hidden="true">*</span>' : ""}${input}${help}</label>`;
    })
    .join("");
}
export function formData(fields, form) {
  const result = {};
  fields.forEach((f) => {
    let v =
      f.type === "checkbox"
        ? form.elements[f.name].checked
        : form.elements[f.name].value.trim();
    if (v === "" && f.nullable) v = null;
    else if (f.number && v !== "") v = Number(v);
    result[f.name] = v;
  });
  return result;
}

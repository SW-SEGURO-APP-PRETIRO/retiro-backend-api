import { api, errorText, escapeHTML as e, rows } from "./api.js";
import {
  icons,
  icon,
  name,
  person,
  human,
  badge,
  date,
  toast,
} from "./ui.js";
import {
  ROLES,
  ESTADOS_INSTITUCION,
  ESTADOS_USUARIO,
  EVENTOS_TECNICOS,
  EVENTOS_ANOMALIA,
  EVENTOS_INSTITUCION,
  systemCatalog,
  verifyAuditChain,
} from "./catalog.js";

const page = document.body.dataset.page;
const config = systemCatalog[page];
const content = document.querySelector("#content");
const actions = document.querySelector("#page-actions");
const errorBox = document.querySelector("#page-error");

const state = {
  records: [],
  instituciones: [],
  usuarios: [],
  auditRecent: [],
  search: "",
  status: "",
  roleFilter: "",
  instFilter: "",
  audit: {},
  page: 1,
  total: 0,
  currentUser: null,
  chatRooms: [],
  chatMessages: [],
  chatContacts: [],
  activeRoomId: null,
};

let loadVersion = 0;
icons();

const findInst = (id) =>
  state.instituciones.find((i) => String(i.id) === String(id));
const findUser = (id) =>
  state.usuarios.find((u) => String(u.id) === String(id));
const adminsOfInst = (instId) =>
  state.usuarios.filter(
    (u) =>
      u.rol === "ADMIN_ESCOLAR" && String(u.institucion_id) === String(instId),
  );

function isTemporarilyLocked(u) {
  return Boolean(u.bloqueado_hasta && new Date(u.bloqueado_hasta) > new Date());
}

function userSecurityRisk(u) {
  const reasons = [];
  if (u.estado === "BLOQUEADA") reasons.push("Bloqueada permanentemente");
  if (isTemporarilyLocked(u))
    reasons.push(`Bloqueo temporal hasta ${date(u.bloqueado_hasta)}`);
  if (u.intentos_fallidos > 0)
    reasons.push(`${u.intentos_fallidos} intento(s) fallido(s)`);
  if (u.contrasena_temporal)
    reasons.push(
      u.expira_temporal
        ? `Clave temporal (vence ${date(u.expira_temporal)})`
        : "Clave temporal pendiente",
    );
  return reasons;
}

function entityForAudit(row) {
  const det = row.detalle || {};
  if (det.institucion_id) {
    const inst = findInst(det.institucion_id);
    return inst ? inst.nombre : `Institución #${det.institucion_id}`;
  }
  if (det.usuario_id) {
    const u = findUser(det.usuario_id);
    return u ? `${name(u)} (${u.correo})` : `Usuario #${det.usuario_id}`;
  }
  if (row.institucion_id && Number(row.institucion_id) !== 0) {
    const inst = findInst(row.institucion_id);
    return inst ? inst.nombre : `Institución #${row.institucion_id}`;
  }
  return "Plataforma global (#0)";
}

function cell(row, key) {
  switch (key) {
    case "institucion":
      return `<div class="person"><span class="avatar">${e((row.nombre || "I").slice(0, 2).toUpperCase())}</span><div><strong>${e(row.nombre)}</strong><small>${e(row.correo)} · ${e(row.telefono || "Sin teléfono")}</small></div></div>`;
    case "persona":
      return person(row, `${row.correo} · Cédula ${row.cedula}`);
    case "admin_escolar": {
      const admins = adminsOfInst(row.id);
      if (!admins.length)
        return `<span class="badge bad"><span class="status-dot"></span>Sin administrador</span>`;
      const primary = admins[0];
      return person(
        primary,
        `${primary.correo} · ${human(primary.estado)}${primary.contrasena_temporal ? " · Clave temporal" : ""}`,
      );
    }
    case "institucion_nombre": {
      if (!row.institucion_id) return `<span class="muted">Plataforma global</span>`;
      const inst = findInst(row.institucion_id);
      return inst ? e(inst.nombre) : `Institución #${e(row.institucion_id)}`;
    }
    case "institucion_estado": {
      if (!row.institucion_id) return "—";
      const inst = findInst(row.institucion_id);
      return inst ? badge(inst.estado) : "—";
    }
    case "rol_badge":
      return `<span class="badge neutral">${e(human(row.rol))}</span>`;
    case "seguridad_clave":
      return row.contrasena_temporal
        ? `<span class="badge warn"><span class="status-dot"></span>Cambio pendiente</span>`
        : `<span class="badge good"><span class="status-dot"></span>Actualizada</span>`;
    case "seguridad_resumen": {
      const risks = userSecurityRisk(row);
      return risks.length
        ? `<span class="badge ${row.estado === "BLOQUEADA" || isTemporarilyLocked(row) ? "bad" : "warn"}">${e(risks[0])}</span>`
        : `<span class="muted">Sin alertas</span>`;
    }
    case "riesgo_motivo": {
      const risks = userSecurityRisk(row);
      return risks.length ? e(risks.join(" · ")) : "—";
    }
    case "entidad_global":
      return e(entityForAudit(row));
    case "integridad_hash":
      return `<code>#${e(row.secuencia)} · ${e((row.hash_propio || "").slice(0, 10))}…</code>`;
    case "leida":
      return `<span class="badge ${row.leida ? "neutral" : "warn"}">${row.leida ? "Leída" : "Sin leer"}</span>`;
    case "estado":
    case "resultado":
      return badge(row[key]);
    case "fecha":
    case "creada_en":
    case "aprobada_en":
      return e(date(row[key]));
    case "tipo":
      return e(human(row[key]));
    default:
      return e(row[key] ?? "—");
  }
}

function rowActions(row) {
  const b = (action, label, extra = "") =>
    `<button class="text-button ${extra}" data-action="${action}" data-id="${row.id}">${label}</button>`;

  if (page === "instituciones" || page === "pendientes") {
    let btns = b("detail-inst", "Ver ficha");
    if (row.estado === "PENDIENTE_APROBACION") {
      btns +=
        b("approve-inst", "Aprobar") +
        b("reject-inst", "Rechazar", "danger-text");
    } else if (row.estado === "ACTIVA") {
      btns += b("suspend-inst", "Suspender", "danger-text");
    } else if (row.estado === "SUSPENDIDA") {
      btns += b("reactivate-inst", "Reactivar");
    }
    return btns;
  }

  if (["administradores", "cuentas", "seguridad"].includes(page)) {
    let btns = b("detail-user", "Ver cuenta");
    const isSelf = state.currentUser && row.id === state.currentUser.id;
    if (!isSelf) {
      if (row.estado === "BLOQUEADA") {
        btns += b("unblock-user", "Desbloquear");
      } else {
        btns += b("block-user", "Bloquear", "danger-text");
        if (row.intentos_fallidos > 0 || isTemporarilyLocked(row)) {
          btns += b("unblock-user", "Limpiar bloqueo");
        }
      }
    }
    btns += b("recover-user", "Enviar recuperación");
    return btns;
  }

  if (page === "bitacora") return b("detail-audit", "Ver evento");
  if (page === "notificaciones")
    return row.leida ? "" : b("read-notif", "Marcar leída");
  return "";
}

function toolbar() {
  if (page === "bitacora") {
    return `<form class="filters" id="audit-filters">
      <label>Desde<input name="fecha_desde" type="date" value="${e(state.audit.fecha_desde || "")}"></label>
      <label>Hasta<input name="fecha_hasta" type="date" value="${e(state.audit.fecha_hasta || "")}"></label>
      <label>Tipo de evento
        <select name="tipo">
          <option value="">Todos los eventos técnicos</option>
          ${EVENTOS_TECNICOS.map((t) => `<option value="${t}" ${state.audit.tipo === t ? "selected" : ""}>${e(human(t))} (${t})</option>`).join("")}
        </select>
      </label>
      <label>Actor (ID)<input name="usuario" type="number" min="1" placeholder="Ej. 1" value="${e(state.audit.usuario || "")}"></label>
      <button class="button primary" type="submit">Aplicar filtros</button>
    </form>`;
  }

  if (page === "notificaciones") {
    return `<div class="tabs"><button data-filter="" aria-selected="${!state.status}">Todas</button><button data-filter="no_leidas" aria-selected="${!!state.status}">Sin leer</button></div>`;
  }

  if (page === "seguridad") {
    return `<div class="tabs">
      <button data-sec-tab="" aria-selected="${!state.status}">Todas con alerta</button>
      <button data-sec-tab="BLOQUEADA" aria-selected="${state.status === "BLOQUEADA"}">Bloqueadas</button>
      <button data-sec-tab="TEMPORAL_LOCK" aria-selected="${state.status === "TEMPORAL_LOCK"}">Bloqueo temporal / Intentos</button>
      <button data-sec-tab="CLAVE_TEMPORAL" aria-selected="${state.status === "CLAVE_TEMPORAL"}">Contraseña temporal</button>
    </div>`;
  }

  const instOptions = state.instituciones
    .map(
      (i) =>
        `<option value="${i.id}" ${String(state.instFilter) === String(i.id) ? "selected" : ""}>${e(i.nombre)}</option>`,
    )
    .join("");

  return `<div class="list-toolbar">
    <label class="search">${icon("search")}<input type="search" id="search" placeholder="Buscar por nombre, RUC, correo o cédula" aria-label="Buscar en ${e(page)}" value="${e(state.search)}"></label>
    <div class="filter-cluster">
      ${
        page === "cuentas"
          ? `<label class="sr-only" for="role-filter">Rol</label><select id="role-filter"><option value="">Todos los roles</option>${ROLES.map(([v, l]) => `<option value="${v}" ${state.roleFilter === v ? "selected" : ""}>${e(l)}</option>`).join("")}</select>`
          : ""
      }
      ${
        ["cuentas", "administradores"].includes(page)
          ? `<label class="sr-only" for="inst-filter">Institución</label><select id="inst-filter"><option value="">Todas las instituciones</option>${instOptions}</select>`
          : ""
      }
      ${
        page === "instituciones"
          ? `<label class="sr-only" for="status-filter">Estado</label><select id="status-filter"><option value="">Todos los estados</option>${ESTADOS_INSTITUCION.map(([v, l]) => `<option value="${v}" ${state.status === v ? "selected" : ""}>${e(l)}</option>`).join("")}</select>`
          : ["cuentas", "administradores"].includes(page)
            ? `<label class="sr-only" for="status-filter">Estado</label><select id="status-filter"><option value="">Todos los estados</option>${ESTADOS_USUARIO.map(([v, l]) => `<option value="${v}" ${state.status === v ? "selected" : ""}>${e(l)}</option>`).join("")}</select>`
            : ""
      }
      <span class="muted" id="result-count"></span>
    </div>
  </div>`;
}

function filteredRecords() {
  const q = state.search.toLocaleLowerCase("es");
  return state.records.filter((row) => {
    if (page === "seguridad") {
      const risks = userSecurityRisk(row);
      if (!risks.length) return false;
      if (state.status === "BLOQUEADA" && row.estado !== "BLOQUEADA")
        return false;
      if (
        state.status === "TEMPORAL_LOCK" &&
        !(isTemporarilyLocked(row) || row.intentos_fallidos > 0)
      )
        return false;
      if (state.status === "CLAVE_TEMPORAL" && !row.contrasena_temporal)
        return false;
    } else {
      if (state.status && !config.serverPaging && row.estado !== state.status)
        return false;
    }
    if (state.roleFilter && row.rol !== state.roleFilter) return false;
    if (
      state.instFilter &&
      String(row.institucion_id) !== String(state.instFilter)
    )
      return false;
    if (!q) return true;
    return config.columns
      .map(([k]) => cell(row, k).replace(/<[^>]*>/g, " "))
      .join(" ")
      .toLocaleLowerCase("es")
      .includes(q);
  });
}

function renderList() {
  let banner = "";
  if (page === "administradores") {
    const activeWithoutAdmin = state.instituciones.filter((inst) => {
      const activeAdmins = adminsOfInst(inst.id).filter(
        (u) => u.estado === "ACTIVA",
      );
      return inst.estado === "ACTIVA" && activeAdmins.length === 0;
    });
    if (activeWithoutAdmin.length) {
      banner = `<div class="error-box" role="status"><strong>Atención:</strong> ${activeWithoutAdmin.length} institución(es) activa(s) no cuentan con un administrador escolar activo (${e(activeWithoutAdmin.map((i) => i.nombre).join(", "))}).</div>`;
    }
  }
  if (page === "seguridad") {
    const anomalies = state.auditRecent.filter((a) =>
      EVENTOS_ANOMALIA.has(a.tipo),
    );
    banner = `<section class="panel" style="margin-bottom:24px"><div class="section-heading"><div><h2>Anomalías e intentos fallidos recientes</h2><p>Eventos de seguridad detectados en la bitácora técnica.</p></div><a href="/sistema/bitacora/" class="text-link">Abrir bitácora técnica ${icon("arrow")}</a></div>${
      anomalies.length
        ? anomalies
            .slice(0, 5)
            .map(
              (a) =>
                `<div class="compact-row"><div><strong>${e(human(a.tipo))}</strong> · <span class="muted">${e(a.actor_nombre || "Sistema")}</span><br><small class="muted">${e(date(a.fecha))} · Secuencia #${e(a.secuencia)}</small></div>${badge(a.resultado)}</div>`,
            )
            .join("")
        : `<div class="inline-empty">${icon("shield")}<div><strong>Sin anomalías recientes</strong><p>No se registran fallos de autenticación ni códigos TOTP inválidos recientes.</p></div></div>`
    }</section>`;
  }

  content.innerHTML = `${banner}${toolbar()}<div id="table-region"></div>`;

  document.querySelector("#search")?.addEventListener("input", (ev) => {
    state.search = ev.target.value;
    state.page = 1;
    renderTable();
  });
  document.querySelector("#status-filter")?.addEventListener("change", (ev) => {
    state.status = ev.target.value;
    state.page = 1;
    renderTable();
  });
  document.querySelector("#role-filter")?.addEventListener("change", (ev) => {
    state.roleFilter = ev.target.value;
    state.page = 1;
    renderTable();
  });
  document.querySelector("#inst-filter")?.addEventListener("change", (ev) => {
    state.instFilter = ev.target.value;
    state.page = 1;
    renderTable();
  });
  document.querySelector("#audit-filters")?.addEventListener("submit", (ev) => {
    ev.preventDefault();
    state.audit = Object.fromEntries(new FormData(ev.target));
    state.page = 1;
    loadRecords();
  });
  content.querySelectorAll("[data-filter]").forEach((b) =>
    b.addEventListener("click", () => {
      state.status = b.dataset.filter;
      state.page = 1;
      loadRecords();
    }),
  );
  content.querySelectorAll("[data-sec-tab]").forEach((b) =>
    b.addEventListener("click", () => {
      state.status = b.dataset.secTab;
      state.page = 1;
      renderList();
    }),
  );
  renderTable();
}

function renderTable() {
  const filtered = filteredRecords();
  const total = config.serverPaging ? state.total : filtered.length;
  const count = document.querySelector("#result-count");
  if (count) count.textContent = `${total} resultados`;
  const max = Math.max(1, Math.ceil(total / 20));
  state.page = Math.min(state.page, max);
  const visible = config.serverPaging
    ? filtered
    : filtered.slice((state.page - 1) * 20, state.page * 20);
  const region = document.querySelector("#table-region");
  region.innerHTML = visible.length
    ? `<div class="table-scroll" tabindex="0" role="region" aria-label="Listado de ${e(page)}"><table><thead><tr>${config.columns.map(([, label]) => `<th scope="col">${label}</th>`).join("")}<th scope="col" class="align-right">Acciones</th></tr></thead><tbody>${visible.map((row) => `<tr>${config.columns.map(([key]) => `<td>${cell(row, key)}</td>`).join("")}<td class="row-actions">${rowActions(row)}</td></tr>`).join("")}</tbody></table></div>`
    : `<div class="empty-state">${icon(page === "pendientes" ? "check" : "shield")}<h2>${state.search || state.status || state.roleFilter || state.instFilter ? "No hay coincidencias" : "Sin registros pendientes"}</h2><p>${state.search || state.status || state.roleFilter || state.instFilter ? "Prueba con otra búsqueda o limpia los filtros activos." : page === "pendientes" ? "Todas las solicitudes de registro institucional han sido atendidas." : page === "seguridad" ? "No hay cuentas bloqueadas, con intentos fallidos ni contraseñas temporales pendientes." : "Los registros de la plataforma aparecerán aquí."}</p></div>`;
  region.insertAdjacentHTML(
    "beforeend",
    `<div class="pagination"><span>${total ? `${(state.page - 1) * 20 + 1}–${Math.min(state.page * 20, total)} de ${total}` : "0 resultados"}</span><div><button class="button" data-page-step="-1" ${state.page <= 1 ? "disabled" : ""}>Anterior</button><span>Página ${state.page} de ${max}</span><button class="button" data-page-step="1" ${state.page >= max ? "disabled" : ""}>Siguiente</button></div></div>`,
  );
}

async function loadContextSources() {
  const requests = [
    api("instituciones/"),
    api("cuentas/usuarios/"),
  ];
  if (["inicio", "instituciones", "pendientes", "seguridad", "integridad"].includes(page)) {
    requests.push(api("auditoria/tecnica/?tamano=50"));
  }
  const [instRes, userRes, auditRes] = await Promise.all(requests);
  state.instituciones = rows(instRes);
  state.usuarios = rows(userRes);
  if (auditRes) state.auditRecent = rows(auditRes);

  const pendingTotal = state.instituciones.filter(
    (i) => i.estado === "PENDIENTE_APROBACION",
  ).length;
  const counter = document.querySelector("#pending-count");
  if (counter) {
    counter.textContent = pendingTotal;
    counter.hidden = !pendingTotal;
  }
}

async function loadRecords() {
  const version = ++loadVersion;
  errorBox.hidden = true;
  content.setAttribute("aria-busy", "true");
  try {
    await loadContextSources();
    const params = new URLSearchParams(config.query || "");
    if (config.serverPaging) params.set("page", state.page);
    if (page === "notificaciones" && state.status)
      params.set("no_leidas", "true");
    for (const [key, value] of Object.entries(state.audit || {}))
      if (value) params.set(key, value);

    const result = await api(
      config.endpoint + (params.size ? `?${params}` : ""),
    );
    if (version !== loadVersion) return;
    state.records = rows(result);
    state.total = result.datos?.total ?? state.records.length;
    if (page === "bitacora" && document.querySelector("#audit-filters"))
      renderTable();
    else renderList();
  } catch (error) {
    if (version === loadVersion) showError(error);
  } finally {
    if (version === loadVersion) content.setAttribute("aria-busy", "false");
  }
}

function showError(error) {
  errorBox.replaceChildren();
  errorBox.hidden = false;
  errorBox.append(document.createTextNode(errorText(error) + " "));
  const retry = document.createElement("button");
  retry.className = "text-button";
  retry.textContent = "Reintentar";
  retry.onclick = () => location.reload();
  errorBox.append(retry);
  if (content.querySelector(".loading")) content.innerHTML = "";
}

function showDetail(title, html) {
  document.querySelector("#detail-title").textContent = title;
  document.querySelector("#detail-body").innerHTML = html;
  document.querySelector("#detail").showModal();
}

function confirm(title, description, operation, label = "Confirmar") {
  const dialog = document.querySelector("#confirmation");
  const button = document.querySelector("#confirm-button");
  const box = document.querySelector("#confirm-error");
  document.querySelector("#confirm-title").textContent = title;
  document.querySelector("#confirm-description").textContent = description;
  button.textContent = label;
  box.hidden = true;
  document.querySelector("#confirm-form").onsubmit = async (ev) => {
    ev.preventDefault();
    if (button.disabled) return;
    button.disabled = true;
    button.textContent = "Procesando…";
    try {
      const result = await operation();
      dialog.close();
      toast(result?.mensaje || "Operación completada.");
      if (config) await loadRecords();
      else if (page === "integridad") await renderIntegrity();
      else await overview();
    } catch (error) {
      box.textContent = errorText(error);
      box.hidden = false;
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  };
  dialog.showModal();
}

function askReason({
  title,
  description,
  label = "Motivo",
  required = true,
  submitLabel = "Confirmar",
  operation,
}) {
  const dialog = document.querySelector("#reason-dialog");
  const form = document.querySelector("#reason-form");
  const input = document.querySelector("#reason-input");
  const button = document.querySelector("#reason-button");
  const box = document.querySelector("#reason-error");

  document.querySelector("#reason-title").textContent = title;
  document.querySelector("#reason-description").textContent = description;
  document.querySelector("#reason-label").innerHTML =
    `${e(label)}${required ? ' <span aria-hidden="true">*</span>' : ""}`;
  input.required = required;
  input.value = "";
  button.textContent = submitLabel;
  box.hidden = true;

  form.onsubmit = async (ev) => {
    ev.preventDefault();
    const motivo = input.value.trim();
    if (required && !motivo) {
      box.textContent = "El motivo es obligatorio para esta operación.";
      box.hidden = false;
      return;
    }
    if (button.disabled) return;
    button.disabled = true;
    button.textContent = "Procesando…";
    box.hidden = true;
    try {
      const result = await operation(motivo);
      dialog.close();
      toast(result?.mensaje || "Decisión registrada.");
      if (config) await loadRecords();
      else await overview();
    } catch (error) {
      box.textContent = errorText(error);
      box.hidden = false;
    } finally {
      button.disabled = false;
      button.textContent = submitLabel;
    }
  };
  dialog.showModal();
}

function showInstitutionDetail(inst) {
  const creador = inst.creada_por_id ? findUser(inst.creada_por_id) : null;
  const aprobador = inst.aprobada_por_id ? findUser(inst.aprobada_por_id) : null;
  const admins = adminsOfInst(inst.id);
  const history = state.auditRecent.filter(
    (ev) =>
      EVENTOS_INSTITUCION.has(ev.tipo) &&
      String(ev.detalle?.institucion_id) === String(inst.id),
  );

  showDetail(
    inst.nombre,
    `<dl>
      <dt>Estado actual</dt><dd>${badge(inst.estado)}</dd>
      ${inst.motivo_estado ? `<dt>Motivo registrado</dt><dd>${e(inst.motivo_estado)}</dd>` : ""}
      <dt>RUC</dt><dd><code>${e(inst.ruc)}</code></dd>
      <dt>Correo institucional</dt><dd>${e(inst.correo)}</dd>
      <dt>Teléfono</dt><dd>${e(inst.telefono)}</dd>
      <dt>Dirección</dt><dd>${e(inst.direccion)}</dd>
      <dt>Responsable registrado</dt><dd>${e(inst.responsable)}</dd>
      <dt>Fecha de registro</dt><dd>${e(date(inst.creada_en))}</dd>
      <dt>Creada por</dt><dd>${e(creador ? `${name(creador)} (${creador.correo})` : inst.creada_por_id ? `Usuario #${inst.creada_por_id}` : "Registro público inicial")}</dd>
      <dt>Decisión tomada por</dt><dd>${e(aprobador ? `${name(aprobador)} (${aprobador.correo})` : inst.aprobada_por_id ? `Usuario #${inst.aprobada_por_id}` : "Pendiente de decisión")}</dd>
      <dt>Fecha de decisión</dt><dd>${e(date(inst.aprobada_en))}</dd>
    </dl>
    <h3>Administrador(es) escolar(es) asociado(s)</h3>
    ${
      admins.length
        ? `<dl>${admins.map((a) => `<dt>${e(name(a))}</dt><dd>${e(a.correo)} · Cédula ${e(a.cedula)} · ${badge(a.estado)} ${a.contrasena_temporal ? badge("PENDIENTE") : ""}</dd>`).join("")}</dl>`
        : `<p class="muted">No se encontró una cuenta ADMIN_ESCOLAR asociada.</p>`
    }
    <h3>Historial de cambios de estado en bitácora</h3>
    ${
      history.length
        ? `<dl>${history.map((h) => `<dt>${e(date(h.fecha))} · ${e(human(h.tipo))}</dt><dd>Por ${e(h.actor_nombre || "Sistema")} ${h.detalle?.motivo ? `· Motivo: ${e(h.detalle.motivo)}` : ""}</dd>`).join("")}</dl>`
        : `<p class="muted">Sin cambios de estado recientes en el lote técnico consultado.</p>`
    }`,
  );
}

function showUserDetail(u) {
  const inst = u.institucion_id ? findInst(u.institucion_id) : null;
  const risks = userSecurityRisk(u);
  showDetail(
    name(u),
    `<dl>
      <dt>Correo electrónico</dt><dd>${e(u.correo)}</dd>
      <dt>Cédula</dt><dd><code>${e(u.cedula)}</code></dd>
      <dt>Teléfono</dt><dd>${e(u.telefono || "—")}</dd>
      <dt>Rol inmutable</dt><dd>${e(human(u.rol))} (<code>${e(u.rol)}</code>)</dd>
      <dt>Estado de cuenta</dt><dd>${badge(u.estado)}</dd>
      <dt>Institución</dt><dd>${e(inst ? `${inst.nombre} (${human(inst.estado)})` : "Plataforma global (sin institución)")}</dd>
      <dt>Contraseña temporal</dt><dd>${u.contrasena_temporal ? `Sí (expira: ${e(date(u.expira_temporal))})` : "No (contraseña definitiva activa)"}</dd>
      <dt>Intentos fallidos de ingreso</dt><dd>${e(u.intentos_fallidos)}</dd>
      <dt>Bloqueo temporal hasta</dt><dd>${e(date(u.bloqueado_hasta))}</dd>
      <dt>Cuenta creada en</dt><dd>${e(date(u.creado_en))}</dd>
      ${risks.length ? `<dt>Alertas de seguridad</dt><dd>${e(risks.join(" · "))}</dd>` : ""}
    </dl>
    <p class="muted">Separación de funciones: el administrador del sistema puede bloquear, desbloquear o enviar enlace seguro de recuperación, sin alterar datos operativos del colegio.</p>`,
  );
}

async function act(action, id) {
  const row =
    state.records.find((r) => String(r.id) === String(id)) ||
    findInst(id) ||
    findUser(id);
  if (!row) return;

  if (action === "detail-inst") return showInstitutionDetail(row);
  if (action === "detail-user") return showUserDetail(row);

  if (action === "approve-inst") {
    return confirm(
      "Aprobar institución",
      `Se aprobará a ${row.nombre} (RUC ${row.ruc}) y se activará automáticamente la cuenta de su administrador escolar.`,
      () =>
        api(`instituciones/${row.id}/aprobar/`, {
          method: "POST",
          body: { aprobada: true, motivo: "" },
        }),
      "Aprobar institución",
    );
  }

  if (action === "reject-inst") {
    return askReason({
      title: "Rechazar solicitud institucional",
      description: `Indica el motivo obligatorio de rechazo para ${row.nombre}. La institución quedará marcada como RECHAZADA y no se activarán sus cuentas.`,
      label: "Motivo del rechazo",
      required: true,
      submitLabel: "Rechazar solicitud",
      operation: (motivo) =>
        api(`instituciones/${row.id}/aprobar/`, {
          method: "POST",
          body: { aprobada: false, motivo },
        }),
    });
  }

  if (action === "suspend-inst") {
    return askReason({
      title: "Suspender institución activa",
      description: `Se suspenderá el acceso operativo de ${row.nombre}. Ningún administrador escolar de esta institución podrá operar mientras esté suspendida.`,
      label: "Motivo de suspensión",
      required: true,
      submitLabel: "Suspender institución",
      operation: (motivo) =>
        api(`instituciones/${row.id}/suspender/`, {
          method: "POST",
          body: { motivo },
        }),
    });
  }

  if (action === "reactivate-inst") {
    return confirm(
      "Reactivar institución",
      `Se restablecerá el estado ACTIVA para ${row.nombre} y su administrador escolar podrá volver a operar.`,
      () =>
        api(`instituciones/${row.id}/reactivar/`, {
          method: "POST",
          body: {},
        }),
      "Reactivar institución",
    );
  }

  if (action === "block-user" || action === "unblock-user") {
    const isBlock = action === "block-user";
    return confirm(
      isBlock ? "Bloquear cuenta" : "Desbloquear cuenta",
      isBlock
        ? `Se bloqueará el acceso de ${name(row)} (${row.correo}) por seguridad o incumplimiento.`
        : `Se restablecerá el estado ACTIVA de ${name(row)} (${row.correo}), reiniciando sus intentos fallidos y bloqueos temporales.`,
      () =>
        api(
          `cuentas/usuarios/${row.id}/${isBlock ? "bloquear" : "desbloquear"}/`,
          { method: "POST" },
        ),
      isBlock ? "Bloquear cuenta" : "Desbloquear cuenta",
    );
  }

  if (action === "recover-user") {
    return confirm(
      "Iniciar recuperación segura de acceso",
      `Se generará un token de recuperación de un solo uso (vigencia 30 min) para ${row.correo} sin exponer ni asignar contraseñas manualmente.`,
      () =>
        api("autenticacion/solicitar-recuperacion/", {
          method: "POST",
          body: { correo: row.correo },
        }),
      "Generar recuperación",
    );
  }

  if (action === "read-notif") {
    try {
      await api(`notificaciones/${row.id}/leida/`, { method: "PATCH" });
      state.page = 1;
      await loadRecords();
      await updateNotificationCount();
    } catch (error) {
      showError(error);
    }
    return;
  }

  if (action === "detail-audit") {
    const chainReport = verifyAuditChain([row]);
    showDetail(
      "Detalle del evento técnico",
      `<dl>
        <dt>Evento</dt><dd>${e(human(row.tipo))} (<code>${e(row.tipo)}</code>)</dd>
        <dt>Fecha y hora</dt><dd>${e(date(row.fecha))}</dd>
        <dt>Resultado</dt><dd>${badge(row.resultado)}</dd>
        <dt>Actor</dt><dd>${e(row.actor_nombre || "Sistema")} ${row.actor_id ? `(#${e(row.actor_id)})` : ""}</dd>
        <dt>Ámbito / Entidad</dt><dd>${e(entityForAudit(row))}</dd>
        <dt>Secuencia</dt><dd>#${e(row.secuencia)} (Categoría ${e(human(row.categoria))})</dd>
        <dt>Estado de integridad</dt><dd>${badge(chainReport.intact ? "INTEGRA" : "INCONSISTENTE")}</dd>
      </dl>
      <h3>Detalle seguro (sin contraseñas ni tokens)</h3>
      <pre>${e(JSON.stringify(row.detalle, null, 2))}</pre>
      <details open>
        <summary>Cadena criptográfica SHA-256</summary>
        <p>Hash propio</p><code>${e(row.hash_propio)}</code>
        <p>Hash anterior</p><code>${e(row.hash_anterior)}</code>
      </details>`,
    );
  }
}

async function overview() {
  await loadContextSources();
  const [notifRes, saludRes] = await Promise.all([
    api("notificaciones/?tamano=5"),
    fetch("/salud/", { credentials: "same-origin", cache: "no-store" })
      .then((r) => r.json())
      .catch(() => ({ estado: "degradado" })),
  ]);

  const notifications = rows(notifRes);
  const inst = state.instituciones;
  const users = state.usuarios;
  const audit = state.auditRecent;

  const byState = (s) => inst.filter((i) => i.estado === s);
  const pendingInst = byState("PENDIENTE_APROBACION");
  const activeInst = byState("ACTIVA");
  const suspendedInst = byState("SUSPENDIDA");
  const rejectedInst = byState("RECHAZADA");

  const blockedUsers = users.filter(
    (u) => u.estado === "BLOQUEADA" || isTemporarilyLocked(u),
  );
  const securityAlerts = audit.filter(
    (a) => EVENTOS_ANOMALIA.has(a.tipo) || a.resultado === "FALLO",
  );
  const integrity = verifyAuditChain(audit);

  const rolesCount = ROLES.map(([rol, label]) => ({
    rol,
    label,
    total: users.filter((u) => u.rol === rol).length,
  }));

  content.innerHTML = `<div class="overview-date"><span>${new Intl.DateTimeFormat("es-EC", { dateStyle: "full", timeZone: "America/Guayaquil" }).format(new Date())}</span><span>Estado de servicios: BD ${saludRes.estado === "ok" ? "Operativa" : "Verificar"} · Cadena SHA-256 ${integrity.intact ? "Íntegra" : "Con alerta"}</span></div>
    <section class="metrics" aria-label="Indicadores globales de la plataforma">
      <div><span>Instituciones pendientes</span><strong class="${pendingInst.length ? "attention" : ""}">${pendingInst.length}</strong><small>${inst.length} registradas en total</small></div>
      <div><span>Instituciones activas</span><strong>${activeInst.length}</strong><small>${suspendedInst.length} suspendidas · ${rejectedInst.length} rechazadas</small></div>
      <div><span>Cuentas bloqueadas</span><strong class="${blockedUsers.length ? "attention" : ""}">${blockedUsers.length}</strong><small>${users.length} cuentas globales supervisadas</small></div>
      <div><span>Alertas e incidentes</span><strong class="${securityAlerts.length ? "attention" : ""}">${securityAlerts.length}</strong><small>Eventos técnicos fallidos o anomalías</small></div>
    </section>

    <div class="overview-grid">
      <section class="panel">
        <div class="section-heading"><div><h2>Solicitudes de instituciones por aprobar</h2><p>Validación de RUC, correo y activación de administrador escolar.</p></div><a href="/sistema/pendientes/" class="text-link">Ver solicitudes ${icon("arrow")}</a></div>
        ${
          pendingInst.length
            ? `<div class="request-list">${pendingInst
                .slice(0, 4)
                .map(
                  (r) =>
                    `<div class="request-row"><div class="person"><span class="avatar">${e(r.nombre.slice(0, 2).toUpperCase())}</span><div><strong>${e(r.nombre)}</strong><small>RUC ${e(r.ruc)} · ${e(r.responsable)}</small></div></div>${badge(r.estado)}<button class="text-button" data-action="approve-inst" data-id="${r.id}">Aprobar</button><button class="text-button danger-text" data-action="reject-inst" data-id="${r.id}">Rechazar</button></div>`,
                )
                .join("")}</div>`
            : `<div class="inline-empty">${icon("check")}<div><strong>Sin instituciones pendientes</strong><p>Todas las solicitudes de colegios han sido procesadas.</p></div></div>`
        }
      </section>

      <section class="panel">
        <div class="section-heading"><div><h2>Distribución global por rol y estado</h2><p>Supervisión agregada sin intervención en operaciones escolares.</p></div><a href="/sistema/cuentas/" class="text-link">Supervisar cuentas ${icon("arrow")}</a></div>
        <div class="schedule">
          ${rolesCount
            .map(
              (r) =>
                `<div class="schedule-row"><span>${e(r.label)}</span><span class="schedule-track"></span><strong>${r.total}</strong></div>`,
            )
            .join("")}
        </div>
        <a class="section-footer" href="/sistema/administradores/">Revisar administradores escolares ${icon("arrow")}</a>
      </section>
    </div>

    <div class="overview-grid lower">
      <section class="panel">
        <div class="section-heading"><div><h2>Últimos eventos técnicos e incidentes</h2><p>Bitácora inmutable encadenada por hash SHA-256.</p></div><a href="/sistema/bitacora/" class="text-link">Bitácora técnica ${icon("arrow")}</a></div>
        ${
          audit.length
            ? audit
                .slice(0, 5)
                .map(
                  (ev) =>
                    `<div class="compact-row"><div><strong>${e(human(ev.tipo))}</strong> · <span class="muted">${e(ev.actor_nombre || "Sistema")}</span><br><small class="muted">${e(date(ev.fecha))} · #${e(ev.secuencia)} · ${e((ev.hash_propio || "").slice(0, 10))}…</small></div>${badge(ev.resultado)}</div>`,
                )
                .join("")
            : '<p class="section-empty">Todavía no hay eventos técnicos registrados.</p>'
        }
      </section>

      <section class="panel">
        <div class="section-heading"><div><h2>Alertas y notificaciones del sistema</h2><p>Solicitudes de colegios, cuentas bloqueadas y anomalías.</p></div><a href="/sistema/notificaciones/" class="text-link">Ver bandeja ${icon("arrow")}</a></div>
        ${
          notifications.length
            ? notifications
                .map(
                  (n) =>
                    `<a class="notification-row" href="/sistema/notificaciones/"><span class="status-dot ${n.leida ? "" : "unread"}"></span><div><strong>${e(n.titulo)}</strong><small>${e(n.mensaje)} · ${e(date(n.creada_en))}</small></div>${icon("arrow")}</a>`,
                )
                .join("")
            : '<p class="section-empty">No hay notificaciones recientes para el administrador del sistema.</p>'
        }
        <a class="section-footer" href="/sistema/integridad/">Validar integridad criptográfica y servicios ${icon("arrow")}</a>
      </section>
    </div>`;
  content.setAttribute("aria-busy", "false");
}

async function renderIntegrity() {
  content.setAttribute("aria-busy", "true");
  errorBox.hidden = true;
  try {
    await loadContextSources();
    const salud = await fetch("/salud/", {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then((r) => r.json())
      .catch(() => ({ estado: "error" }));

    const report = verifyAuditChain(state.auditRecent);
    const activeInstWithoutAdmin = state.instituciones.filter(
      (i) =>
        i.estado === "ACTIVA" &&
        adminsOfInst(i.id).filter((u) => u.estado === "ACTIVA").length === 0,
    );
    const nonSystemWithoutInst = state.usuarios.filter(
      (u) => u.rol !== "ADMIN_SISTEMA" && !u.institucion_id,
    );
    const systemWithInst = state.usuarios.filter(
      (u) => u.rol === "ADMIN_SISTEMA" && u.institucion_id,
    );

    content.innerHTML = `<section class="metrics" aria-label="Estado de integridad">
        <div><span>Cadena SHA-256</span><strong>${report.intact ? "Válida" : "Alerta"}</strong><small>${report.totalEvents} eventos técnicos verificados</small></div>
        <div><span>Ámbitos encadenados</span><strong>${report.chains.length}</strong><small>Secuencias independientes verificadas</small></div>
        <div><span>Aislamiento multi-colegio</span><strong>${nonSystemWithoutInst.length === 0 && systemWithInst.length === 0 ? "Íntegro" : "Inconsistente"}</strong><small>Regla ck_usuario_rol_institucion</small></div>
        <div><span>Servicio de base de datos</span><strong>${salud.estado === "ok" ? "Activo" : "Fallo"}</strong><small>Endpoint /salud/ e inmutabilidad FAU_STG.1</small></div>
      </section>

      <div class="overview-grid">
        <section class="panel">
          <div class="section-heading"><div><h2>Verificación de cadenas de auditoría</h2><p>Comprobación de enlaces hash_anterior → hash_propio y secuencias.</p></div><a href="/sistema/bitacora/" class="text-link">Inspeccionar eventos ${icon("arrow")}</a></div>
          ${
            report.chains.length
              ? report.chains
                  .map((c) => {
                    const inst = c.scope ? findInst(c.scope) : null;
                    const label =
                      c.scope === 0
                        ? "Cadena global del sistema (#0)"
                        : inst
                          ? `${inst.nombre} (#${c.scope})`
                          : `Institución #${c.scope}`;
                    return `<div class="compact-row"><div><strong>${e(label)}</strong><br><small class="muted">${c.count} evento(s) · Secuencia #${e(c.firstSeq)} a #${e(c.lastSeq)} · Hash cabeza: <code>${e(c.headHash.slice(0, 16))}…</code></small></div>${badge(c.status)}</div>`;
                  })
                  .join("")
              : `<div class="inline-empty">${icon("key")}<div><strong>Sin eventos para verificar</strong><p>La cadena se inicializará con el bloque génesis (64 ceros).</p></div></div>`
          }
        </section>

        <section class="panel">
          <div class="section-heading"><div><h2>Restricciones y gobernanza de plataforma</h2><p>Controles activos de seguridad y separación de responsabilidades.</p></div></div>
          <div class="compact-row"><div><strong>Inmutabilidad de bitácora (3 capas)</strong><br><small class="muted">Modelo Python, disparador SQL trg_auditoria_inmutable y cadena SHA-256</small></div>${badge("ACTIVA")}</div>
          <div class="compact-row"><div><strong>Aislamiento de cuentas por institución</strong><br><small class="muted">${nonSystemWithoutInst.length} cuentas operativas sin institución · ${systemWithInst.length} admin sistema con institución</small></div>${badge(nonSystemWithoutInst.length === 0 && systemWithInst.length === 0 ? "INTEGRA" : "INCONSISTENTE")}</div>
          <div class="compact-row"><div><strong>Cobertura de administradores escolares</strong><br><small class="muted">${activeInstWithoutAdmin.length ? `${activeInstWithoutAdmin.length} colegio(s) activo(s) sin administrador activo` : "Todo colegio activo tiene un administrador escolar activo"}</small></div>${badge(activeInstWithoutAdmin.length === 0 ? "INTEGRA" : "PENDIENTE")}</div>
          <div class="compact-row"><div><strong>Separación de dominio operativo</strong><br><small class="muted">El administrador del sistema no modifica estudiantes, cursos, puertas, cuidadores ni retiros</small></div>${badge("ACTIVA")}</div>
        </section>
      </div>`;
  } catch (error) {
    showError(error);
  } finally {
    content.setAttribute("aria-busy", "false");
  }
}

async function updateNotificationCount() {
  const result = await api("notificaciones/?tamano=1");
  document.querySelector("#unread-dot").hidden = !result.datos.no_leidas;
}

async function loadSystemChat(preserveRoom = true) {
  content.setAttribute("aria-busy", "true");
  errorBox.hidden = true;
  try {
    const roomsRes = await api("chat/salas/");
    state.chatRooms = rows(roomsRes);
    if (
      !preserveRoom ||
      !state.activeRoomId ||
      !state.chatRooms.some((r) => r.id === state.activeRoomId)
    ) {
      state.activeRoomId = state.chatRooms[0]?.id || null;
    }
    if (state.activeRoomId) {
      const msgRes = await api(`chat/salas/${state.activeRoomId}/mensajes/`);
      state.chatMessages = rows(msgRes);
    } else {
      state.chatMessages = [];
    }
    renderSystemChatView();
  } catch (error) {
    showError(error);
  } finally {
    content.setAttribute("aria-busy", "false");
  }
}

function renderSystemChatView() {
  const activeRoom =
    state.chatRooms.find((r) => r.id === state.activeRoomId) ||
    state.chatRooms[0] ||
    null;
  if (activeRoom && !state.activeRoomId) state.activeRoomId = activeRoom.id;

  content.innerHTML = `<div class="chat-layout">
    <aside class="chat-rooms" aria-label="Salas generales por institución">
      <div class="chat-rooms-header"><span>Salas generales (${state.chatRooms.length})</span></div>
      ${state.chatRooms
        .map(
          (r) =>
            `<button type="button" class="chat-room-btn" data-room-id="${r.id}" aria-selected="${r.id === state.activeRoomId}">
              <strong>${e(r.nombre || `Sala general · ${r.institucion_nombre}`)}</strong>
              <small>${e(r.institucion_nombre)} · ${e(r.ultimo_mensaje?.contenido || "Sala general de la institución")}</small>
            </button>`,
        )
        .join("")}
    </aside>
    <section class="chat-main" aria-label="Mensajes de la sala general">
      <header class="chat-header">
        <div><strong>${e(activeRoom ? activeRoom.nombre || `Sala general · ${activeRoom.institucion_nombre}` : "Sala general")}</strong><br><small class="muted">${e(activeRoom ? activeRoom.institucion_nombre : "Plataforma")} · Sala general única de la institución</small></div>
        ${badge("ACTIVA")}
      </header>
      <div class="chat-messages" id="chat-messages">
        ${
          state.chatMessages.length
            ? state.chatMessages
                .map((m) => {
                  const mine =
                    String(m.autor_id) === String(state.currentUser?.id);
                  return `<div class="chat-bubble ${mine ? "mine" : ""}">
                    <div class="chat-bubble-meta"><strong>${e(mine ? "Tú (Admin. Sistema)" : m.autor_nombre)}</strong><span>${e(human(m.autor_rol))}</span><span>· ${e(date(m.enviado_en))}</span></div>
                    <div>${e(m.contenido)}</div>
                  </div>`;
                })
                .join("")
            : `<div class="inline-empty">${icon("chat")}<div><strong>Sala general lista</strong><p>Escribe un mensaje abajo para comunicarte en la sala general de la institución seleccionada.</p></div></div>`
        }
      </div>
      <form class="chat-composer" id="chat-form">
        <input name="contenido" placeholder="Escribe un mensaje en la sala general…" maxlength="2000" autocomplete="off" required>
        <button class="button primary" type="submit">Enviar mensaje</button>
      </form>
    </section>
  </div>`;

  const msgBox = document.querySelector("#chat-messages");
  if (msgBox) msgBox.scrollTop = msgBox.scrollHeight;

  content.querySelectorAll("[data-room-id]").forEach((btn) => {
    btn.onclick = async () => {
      state.activeRoomId = Number(btn.dataset.roomId);
      await loadSystemChat(true);
    };
  });

  document.querySelector("#chat-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const input = ev.target.elements.contenido;
    const text = input.value.trim();
    if (!text) return;
    const btn = ev.target.querySelector("button");
    btn.disabled = true;
    try {
      await api("chat/general/", {
        method: "POST",
        body: {
          sala_id: state.activeRoomId,
          contenido: text,
        },
      });
      input.value = "";
      await loadSystemChat(true);
    } catch (error) {
      showError(error);
    } finally {
      btn.disabled = false;
    }
  });
}

content.addEventListener("click", (ev) => {
  const action = ev.target.closest("[data-action]");
  if (action) act(action.dataset.action, action.dataset.id);
  const step = ev.target.closest("[data-page-step]");
  if (step && !step.disabled) {
    state.page += Number(step.dataset.pageStep);
    if (config?.serverPaging) loadRecords();
    else renderTable();
  }
});

document.querySelectorAll("[data-close]").forEach(
  (button) =>
    (button.onclick = () => {
      const dialog = button.closest("dialog");
      if (dialog.querySelector('button[type="submit"]:disabled')) return;
      dialog.close();
    }),
);
document.querySelector("#detail").addEventListener("close", () => {
  document.querySelector("#detail-body").replaceChildren();
});
document.querySelector("#reason-dialog").addEventListener("cancel", (ev) => {
  if (document.querySelector("#reason-button").disabled) ev.preventDefault();
});
document.querySelector("#confirmation").addEventListener("cancel", (ev) => {
  if (document.querySelector("#confirm-button").disabled) ev.preventDefault();
});
document.querySelector("#menu-toggle").onclick = () => {
  const open = document.body.classList.toggle("menu-open");
  document.querySelector("#menu-toggle").setAttribute("aria-expanded", open);
};
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") {
    document.body.classList.remove("menu-open");
    document
      .querySelector("#menu-toggle")
      .setAttribute("aria-expanded", "false");
  }
});
document.querySelector("#logout").onclick = async () => {
  try {
    await api("autenticacion/cerrar-sesion/", { method: "POST" });
    location.assign("/autenticacion/ingresar/");
  } catch (error) {
    showError(error);
  }
};

let socket,
  pingTimer,
  reconnectTimer,
  retries = 0,
  stopped = false;

function connectNotifications() {
  if (stopped) return;
  socket = new WebSocket(
    `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/notificaciones/`,
  );
  socket.onopen = () => {
    retries = 0;
    document.querySelector("#connection").textContent = "Avisos en tiempo real";
    document.querySelector("#connection").classList.add("online");
    pingTimer = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN)
        socket.send(JSON.stringify({ evento: "ping" }));
    }, 45000);
  };
  socket.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      return;
    }
    if (data.notificacion) {
      toast(data.notificacion.titulo || "Nueva alerta del sistema.");
      updateNotificationCount().catch(() => {});
      if (page === "notificaciones" || page === "pendientes") loadRecords();
      else if (page === "inicio") overview();
    }
    if (data.evento === "chat.mensaje" && data.mensaje) {
      if (page === "chat") {
        loadSystemChat(true);
      } else if (
        String(data.mensaje.autor_id) !== String(state.currentUser?.id)
      ) {
        toast(
          `Mensaje de ${data.mensaje.autor_nombre}: ${data.mensaje.contenido.slice(0, 60)}`,
        );
      }
    }
  };
  socket.onclose = (event) => {
    clearInterval(pingTimer);
    document.querySelector("#connection").classList.remove("online");
    document.querySelector("#connection").textContent = "Avisos sin conexión";
    if (event.code === 4001) {
      stopped = true;
      return;
    }
    if (!stopped && retries < 5)
      reconnectTimer = setTimeout(
        connectNotifications,
        Math.min(30000, 1000 * 2 ** retries++),
      );
  };
  socket.onerror = () => socket.close();
}

window.addEventListener("pagehide", () => {
  stopped = true;
  clearInterval(pingTimer);
  clearTimeout(reconnectTimer);
  socket?.close();
});

async function start() {
  try {
    const profile = await api("autenticacion/perfil/");
    if (profile.datos.usuario.rol !== "ADMIN_SISTEMA")
      throw new Error("Esta cuenta no pertenece a la administración del sistema.");
    if (profile.datos.requiere_cambio_contrasena) {
      location.assign("/autenticacion/cambiar-contrasena/");
      return;
    }
    state.currentUser = profile.datos.usuario;

    if (page === "inicio") {
      actions.innerHTML = `<button class="button" id="refresh">${icon("refresh")} Actualizar</button><a href="/sistema/pendientes/" class="button primary">${icon("check")} Revisar solicitudes</a>`;
      document.querySelector("#refresh").onclick = () => overview();
      await overview();
    } else if (page === "integridad") {
      actions.innerHTML = `<button class="button primary" id="refresh">${icon("refresh")} Verificar cadenas ahora</button>`;
      document.querySelector("#refresh").onclick = () => renderIntegrity();
      await renderIntegrity();
    } else if (page === "chat") {
      await loadContextSources();
      actions.innerHTML = `<button class="button" id="refresh-chat">${icon("refresh")} Actualizar</button>`;
      document.querySelector("#refresh-chat").onclick = () =>
        loadSystemChat(true);
      await loadSystemChat(false);
    } else {
      actions.innerHTML = `<button class="button" id="refresh" aria-label="Actualizar listado">${icon("refresh")} Actualizar</button>${page === "notificaciones" ? '<button class="button primary" id="read-all">Marcar todas leídas</button>' : ""}`;
      document.querySelector("#refresh").onclick = () => loadRecords();
      document.querySelector("#read-all")?.addEventListener("click", () =>
        confirm(
          "Marcar todas como leídas",
          "Se marcarán todas las notificaciones del sistema como leídas.",
          async () => {
            const result = await api("notificaciones/marcar-todas-leidas/", {
              method: "POST",
            });
            state.page = 1;
            await updateNotificationCount();
            return result;
          },
        ),
      );
      await loadRecords();
    }
    updateNotificationCount().catch(() => {});
    connectNotifications();
  } catch (error) {
    showError(error);
    content.setAttribute("aria-busy", "false");
  }
}

start();

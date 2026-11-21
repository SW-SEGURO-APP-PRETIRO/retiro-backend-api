import { api, errorText, escapeHTML as e, rows } from "./api.js";
import {
  catalog,
  institutionFields,
  caregiverApplicationFields,
} from "./catalog.js";
import {
  icons,
  icon,
  name,
  person,
  human,
  badge,
  date,
  toast,
  fieldsHTML,
  formData,
} from "./ui.js";
const page = document.body.dataset.page,
  config = catalog[page];
const content = document.querySelector("#content"),
  actions = document.querySelector("#page-actions"),
  errorBox = document.querySelector("#page-error");
const state = {
  records: [],
  sources: {},
  search: "",
  status: "",
  page: 1,
  total: 0,
  next: false,
  previous: false,
  institution: null,
  busy: false,
  user: null,
  chatRooms: [],
  chatMessages: [],
  chatContacts: [],
  activeRoomId: null,
};
const isPadre = () => state.user?.rol === "PADRE";
let loadVersion = 0;
icons();
const find = (source, id) =>
  state.sources[source]?.find((r) => String(r.id) === String(id));
const time = (v) => (v ? String(v).slice(0, 5) : "—");
function cell(row, key) {
  switch (key) {
    case "persona":
      return person(
        row,
        page === "estudiantes"
          ? `Estudiante #${row.id}`
          : `Cédula ${row.cedula}`,
      );
    case "curso":
      return e(name(find("cursos", row.curso_id)));
    case "salida":
      return e(
        time(
          row.hora_salida_especial || find("cursos", row.curso_id)?.hora_salida,
        ),
      );
    case "puerta":
      return e(name(find("puertas", row.puerta_id)));
    case "estudiante":
      return e(name(find("estudiantes", row.estudiante)));
    case "padre":
      return e(name(find("padres", row.padre)));
    case "solicitante":
      if (isPadre() && String(row.solicitada_por_id) === String(state.user?.id))
        return e(name(state.user));
      return e(name(find("padres", row.solicitada_por_id)));
    case "cuidador":
      return person(row.cuidador, human(row.cuidador.tipo));
    case "vigente":
      return badge(row.vigente ? "ACTIVO" : "INACTIVO");
    case "activo":
    case "activa":
      return badge(row[key] ? "ACTIVO" : "INACTIVO");
    case "leida":
      return `<span class="badge ${row.leida ? "neutral" : "warn"}">${row.leida ? "Leída" : "Sin leer"}</span>`;
    case "estado":
    case "resultado":
      return badge(row[key]);
    case "fecha":
    case "creada_en":
    case "solicitada_en":
      return e(date(row[key]));
    case "hora_salida":
      return e(time(row[key]));
    case "tipo":
      return e(human(row[key]));
    default:
      return e(row[key] ?? "—");
  }
}
function rowActions(row) {
  const b = (action, label, extra = "") =>
    `<button class="text-button ${extra}" data-action="${action}" data-id="${row.id}">${label}</button>`;
  if (isPadre()) {
    if (page === "cuidadores") return b("detail", "Ver detalle");
    if (page === "notificaciones")
      return row.leida ? "" : b("read", "Marcar leída");
    return "";
  }
  if (page === "cuidadores")
    return (
      b("detail", "Ver detalle") +
      (row.estado === "SOLICITADO"
        ? b("approve", "Emitir acceso") +
          b("reject", "Rechazar", "danger-text")
        : ["ACTIVO", "ACCESO_EMITIDO"].includes(row.estado)
          ? b("revoke", "Revocar", "danger-text")
          : "")
    );
  if (page === "bitacora") return b("detail", "Ver evento");
  if (page === "notificaciones")
    return row.leida ? "" : b("read", "Marcar leída");
  if (["padres", "guardias"].includes(page))
    return (
      b("edit", "Editar") +
      (row.estado === "ACTIVA"
        ? b("deactivate", "Desactivar", "danger-text")
        : b("activate", "Activar"))
    );
  return (
    (!config.noEdit ? b("edit", "Editar") : "") +
    (config.remove ? b("delete", "Eliminar", "danger-text") : "")
  );
}
function toolbar() {
  if (page === "bitacora")
    return `<form class="filters" id="audit-filters"><label>Desde<input name="fecha_desde" type="date"></label><label>Hasta<input name="fecha_hasta" type="date"></label><label>Tipo de evento<input name="tipo" placeholder="Ej. ESTUDIANTE_CREADO"></label><label>Actor (ID)<input name="usuario" type="number" min="1"></label><button class="button" type="submit">Aplicar filtros</button></form>`;
  if (page === "notificaciones")
    return `<div class="tabs"><button data-filter="" aria-selected="${!state.status}">Todas</button><button data-filter="no_leidas" aria-selected="${!!state.status}">Sin leer</button></div>`;
  return `<div class="list-toolbar"><label class="search">${icon("search")}<input type="search" id="search" placeholder="Buscar ${page === "cuidadores" ? "cuidador o estudiante" : "por nombre o cédula"}" aria-label="Buscar en ${page}" value="${e(state.search)}"></label><div class="filter-cluster">${["estudiantes", "padres", "guardias", "cuidadores"].includes(page) ? `<label class="sr-only" for="status-filter">Estado</label><select id="status-filter"><option value="">Todos los estados</option>${(page === "cuidadores" ? ["SOLICITADO", "ACCESO_EMITIDO", "ACTIVO", "REVOCADO", "EXPIRADO", "RECHAZADO"] : page === "estudiantes" ? ["ACTIVO", "INACTIVO"] : ["ACTIVA", "PENDIENTE", "BLOQUEADA", "SUSPENDIDA"]).map((s) => `<option ${state.status === s ? "selected" : ""} value="${s}">${human(s)}</option>`).join("")}</select>` : ""}<span class="muted" id="result-count"></span></div></div>`;
}
function renderList() {
  content.innerHTML = `${toolbar()}<div id="table-region"></div>`;
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
  renderTable();
}
function filteredRecords() {
  const q = state.search.toLocaleLowerCase("es");
  return state.records.filter(
    (row) =>
      (!state.status || config.serverPaging || row.estado === state.status) &&
      (!q ||
        config.columns
          .map(([k]) => cell(row, k).replace(/<[^>]*>/g, " "))
          .join(" ")
          .toLocaleLowerCase("es")
          .includes(q)),
  );
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
    : `<div class="empty-state">${icon(page === "cuidadores" ? "check" : "students")}<h2>${state.search || state.status ? "No hay coincidencias" : "Todavía no hay " + page}</h2><p>${state.search || state.status ? "Prueba con otra búsqueda o cambia los filtros." : page === "cuidadores" ? "Las solicitudes de las familias aparecerán aquí para su revisión." : page === "bitacora" ? "Los eventos operativos registrados aparecerán aquí." : page === "notificaciones" ? "Las novedades de tu institución aparecerán aquí." : "Usa el botón de la parte superior para agregar el primer registro."}</p></div>`;
  region.insertAdjacentHTML(
    "beforeend",
    `<div class="pagination"><span>${total ? `${(state.page - 1) * 20 + 1}–${Math.min(state.page * 20, total)} de ${total}` : "0 resultados"}</span><div><button class="button" data-page-step="-1" ${state.page <= 1 ? "disabled" : ""}>Anterior</button><span>Página ${state.page} de ${max}</span><button class="button" data-page-step="1" ${state.page >= max ? "disabled" : ""}>Siguiente</button></div></div>`,
  );
}
async function loadRecords() {
  const version = ++loadVersion;
  errorBox.hidden = true;
  content.setAttribute("aria-busy", "true");
  try {
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
async function sources() {
  const endpoints = {
    cursos: "instituciones/cursos/",
    puertas: "instituciones/puertas/",
    estudiantes: "cuentas/estudiantes/",
    padres: "cuentas/usuarios/?rol=PADRE",
  };
  const needed = isPadre()
    ? {
        inicio: ["cursos", "estudiantes"],
        estudiantes: ["cursos"],
        cuidadores: ["estudiantes"],
      }[page] || []
    : {
        inicio: ["cursos", "estudiantes", "padres"],
        estudiantes: ["cursos"],
        guardias: ["puertas"],
        asignaciones: ["estudiantes", "padres"],
        cuidadores: ["padres", "estudiantes"],
      }[page] || [];
  const results = await Promise.all(
    needed.map(async (key) => [key, rows(await api(endpoints[key]))]),
  );
  for (const [key, value] of results) state.sources[key] = value;
}

async function requestCaregiverModal() {
  const dialog = document.querySelector("#editor");
  const form = document.querySelector("#editor-form");
  document.querySelector("#dialog-title").textContent =
    "Solicitar autorización de cuidador";
  document.querySelector("#dialog-description").textContent =
    "Registra los datos del cuidador y selecciona a tu hijo. El administrador escolar revisará la solicitud.";
  document.querySelector("#form-fields").innerHTML = fieldsHTML(
    caregiverApplicationFields,
    { tipo: "FIJO" },
    state.sources,
  );
  const box = document.querySelector("#form-error");
  box.hidden = true;
  form.onsubmit = async (ev) => {
    ev.preventDefault();
    const button = document.querySelector("#save-button");
    if (button.disabled) return;
    button.disabled = true;
    button.textContent = "Enviando…";
    box.hidden = true;
    try {
      const payload = formData(caregiverApplicationFields, form);
      const estudianteId = payload.estudiante_id;
      delete payload.estudiante_id;
      let cuidadorId;
      try {
        const created = await api("cuidadores/", {
          method: "POST",
          body: payload,
        });
        cuidadorId = created.datos.id;
      } catch (err) {
        const list = rows(await api("cuidadores/"));
        const existing = list.find((c) => c.cedula === payload.cedula);
        if (!existing) throw err;
        cuidadorId = existing.id;
      }
      const authRes = await api(
        `cuidadores/${cuidadorId}/solicitar-autorizacion/`,
        {
          method: "POST",
          body: { estudiante_id: estudianteId },
        },
      );
      dialog.close();
      toast(authRes.mensaje || "Solicitud de cuidador registrada.");
      if (page === "cuidadores") await loadRecords();
      else if (page === "inicio") await parentOverview();
    } catch (error) {
      box.textContent = errorText(error);
      box.hidden = false;
    } finally {
      button.disabled = false;
      button.textContent = "Guardar cambios";
    }
  };
  dialog.showModal();
}
async function edit(row = null) {
  const dialog = document.querySelector("#editor"),
    form = document.querySelector("#editor-form");
  const fields = page === "institucion" ? institutionFields : config.fields;
  document.querySelector("#dialog-title").textContent =
    page === "institucion"
      ? "Editar institución"
      : row
        ? `Editar ${config.singular}`
        : config.create;
  document.querySelector("#dialog-description").textContent =
    page === "asignaciones"
      ? "Vincula únicamente al representante legal que corresponde al estudiante."
      : page === "padres" || page === "guardias"
        ? "La cuenta se crea con contraseña temporal. El rol no podrá cambiarse."
        : "Los campos con * son obligatorios.";
  document.querySelector("#form-fields").innerHTML = fieldsHTML(
    fields,
    row || config?.defaults || {},
    state.sources,
  );
  const box = document.querySelector("#form-error");
  box.hidden = true;
  form.onsubmit = async (ev) => {
    ev.preventDefault();
    const button = document.querySelector("#save-button");
    if (button.disabled) return;
    button.disabled = true;
    button.textContent = "Guardando…";
    box.hidden = true;
    try {
      const body = {
        ...(!row ? config?.defaults : {}),
        ...formData(fields, form),
      };
      const endpoint =
        page === "institucion"
          ? "instituciones/mi-institucion/"
          : config.endpoint + (row ? `${row.id}/` : "");
      const result = await api(endpoint, {
        method: row ? "PATCH" : "POST",
        body,
      });
      dialog.close();
      toast(result.mensaje || "Cambios guardados.");
      if (page === "institucion") {
        state.institution = result.datos;
        renderInstitution();
        document.querySelector("#school-name").textContent =
          result.datos.nombre;
      } else await loadRecords();
      if (result.datos?.contrasena_temporal) {
        showDetail(
          "Cuenta creada",
          `<p>Entrega estas credenciales al titular por un canal seguro. La contraseña solo se muestra durante esta sesión.</p><dl><dt>Correo</dt><dd>${e(result.datos.usuario.correo)}</dd><dt>Contraseña temporal</dt><dd><code>${e(result.datos.contrasena_temporal)}</code></dd></dl>`,
        );
      }
    } catch (error) {
      box.textContent = errorText(error);
      box.hidden = false;
    } finally {
      button.disabled = false;
      button.textContent = "Guardar cambios";
    }
  };
  dialog.showModal();
}
function showDetail(title, html) {
  document.querySelector("#detail-title").textContent = title;
  document.querySelector("#detail-body").innerHTML = html;
  document.querySelector("#detail").showModal();
}
function confirm(title, description, operation, label = "Confirmar") {
  const dialog = document.querySelector("#confirmation"),
    button = document.querySelector("#confirm-button"),
    box = document.querySelector("#confirm-error");
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
async function act(action, id) {
  const row = state.records.find((r) => r.id === Number(id));
  if (!row) return;
  if (action === "edit") return edit(row);
  if (action === "activate" || action === "deactivate")
    return confirm(
      action === "activate" ? "Activar cuenta" : "Desactivar cuenta",
      action === "activate"
        ? `Se habilitará nuevamente el acceso de ${name(row)}.`
        : `Se impedirá el acceso de ${name(row)} a esta institución.`,
      () =>
        api(
          `cuentas/usuarios/${row.id}/${action === "activate" ? "desbloquear" : "bloquear"}/`,
          { method: "POST" },
        ),
      action === "activate" ? "Activar" : "Desactivar",
    );
  if (action === "delete")
    return confirm(
      `Eliminar ${config.singular}`,
      `Se eliminará ${page === "asignaciones" ? "el vínculo seleccionado" : name(row)}. Esta acción no se puede deshacer.`,
      () => api(`${config.endpoint}${row.id}/`, { method: "DELETE" }),
      "Eliminar",
    );
  if (action === "approve")
    return confirm(
      "Emitir acceso al cuidador",
      `Se procesará la solicitud de ${name(row.cuidador)} para ${row.estudiante_nombre || "el estudiante indicado"}. Si es un cuidador fijo, el servidor enviará sus credenciales por correo.`,
      () =>
        api(`cuidadores/autorizaciones/${row.id}/aprobar/`, { method: "POST" }),
      "Emitir acceso",
    );
  if (action === "revoke")
    return confirm(
      "Revocar autorización",
      `Se revocará la autorización de ${name(row.cuidador)} para este estudiante.`,
      () =>
        api(`cuidadores/autorizaciones/${row.id}/revocar/`, { method: "POST" }),
      "Revocar",
    );
  if (action === "reject")
    return confirm(
      "Rechazar solicitud de cuidador",
      `Se rechazará la solicitud de ${name(row.cuidador)} para ${row.estudiante_nombre || "el estudiante indicado"}. El padre solicitante recibirá una notificación.`,
      () =>
        api(`cuidadores/autorizaciones/${row.id}/rechazar/`, {
          method: "POST",
          body: {},
        }),
      "Rechazar",
    );
  if (action === "read") {
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
  if (action === "detail") {
    if (page === "bitacora")
      showDetail(
        "Detalle del evento",
        `<dl><dt>Evento</dt><dd>${e(human(row.tipo))}</dd><dt>Fecha</dt><dd>${e(date(row.fecha))}</dd><dt>Resultado</dt><dd>${badge(row.resultado)}</dd><dt>Actor</dt><dd>${e(row.actor_nombre || "Sistema")}</dd><dt>Secuencia</dt><dd>${e(row.secuencia)}</dd><dt>Categoría</dt><dd>${e(human(row.categoria))}</dd></dl><h3>Datos del evento</h3><pre>${e(JSON.stringify(row.detalle, null, 2))}</pre><details><summary>Integridad del registro</summary><p>Hash propio</p><code>${e(row.hash_propio)}</code><p>Hash anterior</p><code>${e(row.hash_anterior)}</code></details>`,
      );
    else
      showDetail(
        "Solicitud de cuidador",
        `<dl><dt>Cuidador</dt><dd>${e(name(row.cuidador))}</dd><dt>Tipo</dt><dd>${e(human(row.cuidador.tipo))}</dd><dt>Correo</dt><dd>${e(row.cuidador.correo || "—")}</dd><dt>Cédula</dt><dd>${e(row.cuidador.cedula)}</dd><dt>Estudiante</dt><dd>${e(row.estudiante_nombre || `#${row.estudiante_id}`)}</dd><dt>Solicitado por</dt><dd>${e(name(find("padres", row.solicitada_por_id)))}</dd><dt>Estado</dt><dd>${badge(row.estado)}</dd><dt>Fecha de solicitud</dt><dd>${e(date(row.solicitada_en))}</dd></dl>`,
      );
  }
}
content.addEventListener("click", (ev) => {
  const action = ev.target.closest("[data-action]");
  if (action) act(action.dataset.action, action.dataset.id);
  const step = ev.target.closest("[data-page-step]");
  if (step && !step.disabled) {
    state.page += Number(step.dataset.pageStep);
    if (config.serverPaging) loadRecords();
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
document.querySelector("#editor").addEventListener("cancel", (ev) => {
  if (document.querySelector("#save-button").disabled) ev.preventDefault();
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

function renderInstitution() {
  const row = state.institution;
  content.innerHTML = `<section class="institution-layout"><div><h2>Datos de la institución</h2><p class="muted">Mantén actualizada la información de contacto del colegio.</p>${badge(row.estado)}</div><dl class="institution-details">${institutionFields.map((f) => `<div><dt>${f.label}</dt><dd>${e(row[f.name] || "—")}</dd></div>`).join("")}</dl></section>`;
  content.setAttribute("aria-busy", "false");
}
async function overview() {
  const result = await Promise.all([
    api("cuidadores/autorizaciones/?estado=SOLICITADO"),
    api("cuentas/relaciones-padre-estudiante/"),
    api("notificaciones/?tamano=4"),
  ]);
  const pending = rows(result[0]),
    relations = rows(result[1]),
    notifications = rows(result[2]);
  const students = state.sources.estudiantes || [],
    parents = state.sources.padres || [],
    courses = state.sources.cursos || [];
  const assigned = new Set(
    relations.filter((r) => r.vigente).map((r) => r.estudiante),
  );
  const missing = students.filter(
    (s) => s.estado === "ACTIVO" && !assigned.has(s.id),
  );
  content.innerHTML = `<div class="overview-date"><span>${new Intl.DateTimeFormat("es-EC", { dateStyle: "full", timeZone: "America/Guayaquil" }).format(new Date())}</span><span>Información actual del colegio</span></div>
    <section class="metrics" aria-label="Resumen de la institución"><div><span>Estudiantes activos</span><strong>${students.filter((s) => s.estado === "ACTIVO").length}</strong><small>${students.length} estudiantes registrados</small></div><div><span>Representantes</span><strong>${parents.length}</strong><small>Cuentas de padres y madres</small></div><div><span>Sin representante</span><strong class="${missing.length ? "attention" : ""}">${missing.length}</strong><small>Estudiantes activos por vincular</small></div><div><span>Solicitudes pendientes</span><strong class="${pending.length ? "attention" : ""}">${pending.length}</strong><small>Accesos de cuidadores por revisar</small></div></section>
    <div class="overview-grid"><section class="panel"><div class="section-heading"><div><h2>Solicitudes de cuidadores</h2><p>El siguiente paso para un retiro autorizado.</p></div><a href="/escolar/cuidadores/" class="text-link">Ver todas ${icon("arrow")}</a></div>${
      pending.length
        ? `<div class="request-list">${pending
            .slice(0, 4)
            .map(
              (r) =>
                `<div class="request-row">${person(r.cuidador, `${human(r.cuidador.tipo)} · ${r.estudiante_nombre || "Estudiante #" + r.estudiante_id}`)}${badge("SOLICITADO")}<a href="/escolar/cuidadores/" class="text-link">Revisar</a></div>`,
            )
            .join("")}</div>`
        : `<div class="inline-empty">${icon("check")}<div><strong>Sin solicitudes pendientes</strong><p>Las nuevas solicitudes aparecerán aquí.</p></div></div>`
    }</section>
    <section class="panel"><div class="section-heading"><div><h2>Vínculos por completar</h2><p>Estudiantes activos sin representante.</p></div></div>${
      missing.length
        ? missing
            .slice(0, 4)
            .map(
              (r) =>
                `<div class="compact-row">${person(r, name(find("cursos", r.curso_id)))}<a class="text-link" href="/escolar/asignaciones/">Vincular</a></div>`,
            )
            .join("")
        : `<div class="inline-empty">${icon("link")}<div><strong>${students.length ? "Todos tienen un representante" : "Comienza con la matrícula"}</strong><p>${students.length ? "Los vínculos de estudiantes activos están completos." : "Registra estudiantes y vincula a sus familias."}</p></div></div>`
    }<a class="section-footer" href="/escolar/asignaciones/">Administrar asignaciones ${icon("arrow")}</a></section></div>
    <div class="overview-grid lower"><section class="panel"><div class="section-heading"><div><h2>Horarios de salida</h2><p>Jornada regular por curso.</p></div><a href="/escolar/cursos/" class="text-link">Gestionar ${icon("arrow")}</a></div>${
      courses.length
        ? `<div class="schedule">${courses
            .filter((c) => c.activo)
            .slice(0, 6)
            .map(
              (c) =>
                `<div class="schedule-row"><span>${e(c.nombre)}</span><span class="schedule-track"></span><strong>${e(time(c.hora_salida))}</strong></div>`,
            )
            .join("")}</div>`
        : '<p class="section-empty">Crea un curso para definir su horario de salida.</p>'
    }</section><section class="panel"><div class="section-heading"><div><h2>Últimas notificaciones</h2><p>Novedades de tu comunidad escolar.</p></div><a href="/escolar/notificaciones/" class="text-link">Ver todas ${icon("arrow")}</a></div>${notifications.length ? notifications.map((n) => `<a class="notification-row" href="/escolar/notificaciones/"><span class="status-dot ${n.leida ? "" : "unread"}"></span><div><strong>${e(n.titulo)}</strong><small>${e(date(n.creada_en))}</small></div>${icon("arrow")}</a>`).join("") : '<p class="section-empty">Todavía no tienes notificaciones.</p>'}</section></div>`;
  const counter = document.querySelector("#pending-count");
  counter.textContent = pending.length;
  counter.hidden = !pending.length;
  content.setAttribute("aria-busy", "false");
}

async function parentOverview() {
  const result = await Promise.all([
    api("cuidadores/autorizaciones/"),
    api("notificaciones/?tamano=4"),
  ]);
  const authorizations = rows(result[0]);
  const notifications = rows(result[1]);
  const children = state.sources.estudiantes || [];
  const courses = state.sources.cursos || [];
  const activeAuth = authorizations.filter((a) =>
    ["ACTIVO", "ACCESO_EMITIDO"].includes(a.estado),
  );
  const pendingAuth = authorizations.filter((a) => a.estado === "SOLICITADO");

  content.innerHTML = `<div class="overview-date"><span>${new Intl.DateTimeFormat("es-EC", { dateStyle: "full", timeZone: "America/Guayaquil" }).format(new Date())}</span><span>Portal familiar · ${e(state.institution?.nombre || "Mi institución")}</span></div>
    <section class="metrics" aria-label="Resumen familiar">
      <div><span>Hijos vinculados</span><strong>${children.length}</strong><small>Estudiantes bajo tu representación</small></div>
      <div><span>Cuidadores autorizados</span><strong>${activeAuth.length}</strong><small>Con acceso emitido o activo</small></div>
      <div><span>Solicitudes en revisión</span><strong class="${pendingAuth.length ? "attention" : ""}">${pendingAuth.length}</strong><small>Pendientes de aprobación escolar</small></div>
      <div><span>Notificaciones</span><strong>${notifications.filter((n) => !n.leida).length}</strong><small>Avisos recientes sin leer</small></div>
    </section>
    <div class="overview-grid">
      <section class="panel">
        <div class="section-heading"><div><h2>Mis hijos</h2><p>Estudiantes y sus horarios de salida oficiales.</p></div><a href="/escolar/estudiantes/" class="text-link">Ver detalle ${icon("arrow")}</a></div>
        ${
          children.length
            ? children
                .map((s) => {
                  const curso = find("cursos", s.curso_id);
                  const salida = time(
                    s.hora_salida_especial || curso?.hora_salida,
                  );
                  return `<div class="compact-row">${person(s, `${curso ? curso.nombre : "Curso"} · Salida ${salida}`)}${badge(s.estado)}</div>`;
                })
                .join("")
            : `<div class="inline-empty">${icon("students")}<div><strong>Sin estudiantes vinculados</strong><p>Solicita a la administración del colegio que vincule tu cuenta con tus hijos.</p></div></div>`
        }
      </section>
      <section class="panel">
        <div class="section-heading"><div><h2>Estado de mis cuidadores</h2><p>Personas autorizadas para retirar a tus hijos.</p></div><a href="/escolar/cuidadores/" class="text-link">Gestionar ${icon("arrow")}</a></div>
        ${
          authorizations.length
            ? authorizations
                .slice(0, 4)
                .map(
                  (r) =>
                    `<div class="request-row">${person(r.cuidador, `${human(r.cuidador.tipo)} · ${r.estudiante_nombre || "Estudiante #" + r.estudiante_id}`)}${badge(r.estado)}</div>`,
                )
                .join("")
            : `<div class="inline-empty">${icon("check")}<div><strong>Aún no has registrado cuidadores</strong><p>Puedes registrar un cuidador fijo o temporal y solicitar su autorización.</p></div></div>`
        }
        <a class="section-footer" href="/escolar/cuidadores/">Registrar o revisar cuidadores ${icon("arrow")}</a>
      </section>
    </div>
    <div class="overview-grid lower">
      <section class="panel">
        <div class="section-heading"><div><h2>Horarios del colegio</h2><p>Jornadas regulares de salida.</p></div><a href="/escolar/chat/" class="text-link">Abrir chat con el colegio ${icon("arrow")}</a></div>
        ${
          courses.length
            ? `<div class="schedule">${courses
                .filter((c) => c.activo)
                .slice(0, 6)
                .map(
                  (c) =>
                    `<div class="schedule-row"><span>${e(c.nombre)}</span><span class="schedule-track"></span><strong>${e(time(c.hora_salida))}</strong></div>`,
                )
                .join("")}</div>`
            : '<p class="section-empty">Horarios no disponibles.</p>'
        }
      </section>
      <section class="panel">
        <div class="section-heading"><div><h2>Últimas notificaciones</h2><p>Avisos sobre retiros y autorizaciones.</p></div><a href="/escolar/notificaciones/" class="text-link">Ver todas ${icon("arrow")}</a></div>
        ${
          notifications.length
            ? notifications
                .map(
                  (n) =>
                    `<a class="notification-row" href="/escolar/notificaciones/"><span class="status-dot ${n.leida ? "" : "unread"}"></span><div><strong>${e(n.titulo)}</strong><small>${e(date(n.creada_en))}</small></div>${icon("arrow")}</a>`,
                )
                .join("")
            : '<p class="section-empty">Todavía no tienes notificaciones.</p>'
        }
      </section>
    </div>`;
  content.setAttribute("aria-busy", "false");
}

async function loadChat() {
  content.setAttribute("aria-busy", "true");
  errorBox.hidden = true;
  try {
    const res = await api("chat/general/");
    const sala = res.datos?.sala || null;
    state.activeRoomId = sala?.id || null;
    state.chatRooms = sala ? [sala] : [];
    state.chatMessages = Array.isArray(res.datos?.mensajes)
      ? res.datos.mensajes
      : [];
    renderChatView();
  } catch (error) {
    showError(error);
  } finally {
    content.setAttribute("aria-busy", "false");
  }
}

function renderChatView() {
  const activeRoom = state.chatRooms[0] || {
    nombre: `Sala general · ${state.institution?.nombre || "Mi institución"}`,
    tipo: "GENERAL",
  };
  content.innerHTML = `<section class="panel" style="display:flex;flex-direction:column;min-height:480px;max-height:640px">
    <header class="chat-header">
      <div><strong>${e(activeRoom.nombre || "Sala general de la institución")}</strong><br><small class="muted">Sala general única del colegio · Participan administradores escolares, padres, guardias y cuidadores fijos</small></div>
      ${badge("ACTIVA")}
    </header>
    <div class="chat-messages" id="chat-messages">
      ${
        state.chatMessages.length
          ? state.chatMessages
              .map((m) => {
                const mine = String(m.autor_id) === String(state.user?.id);
                return `<div class="chat-bubble ${mine ? "mine" : ""}">
                  <div class="chat-bubble-meta"><strong>${e(mine ? "Tú" : m.autor_nombre)}</strong><span>${e(human(m.autor_rol))}</span><span>· ${e(date(m.enviado_en))}</span></div>
                  <div>${e(m.contenido)}</div>
                </div>`;
              })
              .join("")
          : `<div class="inline-empty">${icon("chat")}<div><strong>Sala general lista</strong><p>Escribe un mensaje abajo para comunicarte con la comunidad de tu institución.</p></div></div>`
      }
    </div>
    <form class="chat-composer" id="chat-form">
      <input id="chat-input" name="contenido" placeholder="Escribe un mensaje en la sala general…" maxlength="2000" autocomplete="off" required>
      <button class="button primary" type="submit">Enviar mensaje</button>
    </form>
  </section>`;

  const msgBox = document.querySelector("#chat-messages");
  if (msgBox) msgBox.scrollTop = msgBox.scrollHeight;

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
      await loadChat();
    } catch (error) {
      showError(error);
    } finally {
      btn.disabled = false;
    }
  });
}
async function updateNotificationCount() {
  const result = await api("notificaciones/?tamano=1");
  document.querySelector("#unread-dot").hidden = !result.datos.no_leidas;
}
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
      toast("Tienes una nueva notificación del colegio.");
      updateNotificationCount().catch(() => {});
      if (page === "notificaciones") loadRecords();
    }
    if (data.evento === "chat.mensaje" && data.mensaje) {
      if (page === "chat") {
        loadChat(true);
      } else if (String(data.mensaje.autor_id) !== String(state.user?.id)) {
        toast(`Nuevo mensaje de ${data.mensaje.autor_nombre}: ${data.mensaje.contenido.slice(0, 60)}`);
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
    const rol = profile.datos.usuario.rol;
    if (!["ADMIN_ESCOLAR", "PADRE"].includes(rol))
      throw new Error("Esta cuenta no pertenece al portal escolar.");
    if (profile.datos.requiere_cambio_contrasena) {
      location.assign("/autenticacion/cambiar-contrasena/");
      return;
    }
    state.user = profile.datos.usuario;
    state.institution = (await api("instituciones/mi-institucion/")).datos;
    document.querySelector("#school-name").textContent =
      state.institution.nombre;
    await sources();
    if (page === "inicio") {
      if (isPadre()) {
        actions.innerHTML = `<a href="/escolar/cuidadores/" class="button primary">${icon("plus")} Solicitar cuidador</a>`;
        await parentOverview();
      } else {
        actions.innerHTML = `<a href="/escolar/estudiantes/" class="button primary">${icon("plus")} Gestionar estudiantes</a>`;
        await overview();
      }
    } else if (page === "chat") {
      actions.innerHTML = `<button class="button" id="refresh-chat">${icon("refresh")} Actualizar</button>`;
      document.querySelector("#refresh-chat").onclick = () => loadChat();
      await loadChat();
    } else if (page === "institucion") {
      if (isPadre()) {
        actions.innerHTML = `<a href="/escolar/chat/" class="button primary">${icon("chat")} Contactar al colegio</a>`;
      } else {
        actions.innerHTML =
          '<button class="button primary" id="edit-institution">Editar institución</button>';
        document.querySelector("#edit-institution").onclick = () =>
          edit(state.institution);
      }
      renderInstitution();
    } else {
      const canCreate = !isPadre() && config.create;
      const padreCaregiverCreate = isPadre() && page === "cuidadores";
      actions.innerHTML = `<button class="button" id="refresh" aria-label="Actualizar listado">${icon("refresh")} Actualizar</button>${canCreate ? `<button class="button primary" id="create">${icon("plus")} ${config.create}</button>` : ""}${padreCaregiverCreate ? `<button class="button primary" id="request-caregiver">${icon("plus")} Solicitar cuidador</button>` : ""}${page === "notificaciones" ? '<button class="button primary" id="read-all">Marcar todas leídas</button>' : ""}`;
      document
        .querySelector("#create")
        ?.addEventListener("click", () => edit());
      document
        .querySelector("#request-caregiver")
        ?.addEventListener("click", () => requestCaregiverModal());
      document.querySelector("#refresh").onclick = () => loadRecords();
      document.querySelector("#read-all")?.addEventListener("click", () =>
        confirm(
          "Marcar todas como leídas",
          "Se marcarán todas tus notificaciones como leídas.",
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

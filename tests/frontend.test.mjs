import test from "node:test";
import assert from "node:assert/strict";
import { catalog } from "../src/static/escolar/catalog.js";
import { escapeHTML, rows, api, ApiError } from "../src/static/escolar/api.js";
import { formData, human } from "../src/static/escolar/ui.js";

test("un estudiante nuevo tiene estado válido sin selección adicional", () => {
  assert.equal(catalog.estudiantes.defaults.estado, "ACTIVO");
  assert.equal(
    catalog.estudiantes.fields.find((f) => f.name === "estado").required,
    true,
  );
});
test("los datos se escapan antes de insertarlos en HTML", () => {
  assert.equal(
    escapeHTML('<img src=x onerror="alert(1)">'),
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
  );
});
test("el cliente interpreta listas y paginación envuelta", () => {
  assert.deepEqual(rows({ datos: [{ id: 1 }] }), [{ id: 1 }]);
  assert.deepEqual(rows({ datos: { resultados: [{ id: 2 }], total: 1 } }), [
    { id: 2 },
  ]);
});
test("el formulario conserva nulos, IDs numéricos y booleanos del contrato", () => {
  assert.deepEqual(
    formData(
      [
        { name: "curso_id", number: true },
        { name: "hora", nullable: true },
        { name: "activo", type: "checkbox" },
      ],
      {
        elements: {
          curso_id: { value: "2" },
          hora: { value: "" },
          activo: { checked: false },
        },
      },
    ),
    { curso_id: 2, hora: null, activo: false },
  );
});
test("las mutaciones incluyen CSRF y no persisten credenciales", async () => {
  globalThis.location = { origin: "http://localhost", assign: () => {} };
  globalThis.document = { cookie: "csrftoken=test-token" };
  let request;
  globalThis.fetch = async (url, options) => {
    request = options;
    return { ok: true, json: async () => ({ datos: { id: 1 } }) };
  };
  await api("cuentas/estudiantes/", {
    method: "POST",
    body: { nombres: "María" },
  });
  assert.equal(request.headers["X-CSRFToken"], "test-token");
  assert.equal(request.credentials, "same-origin");
  assert.equal(request.cache, "no-store");
});
test("un error de validación conserva detalles y estado HTTP", async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 400,
    json: async () => ({
      error: { mensaje: "Datos inválidos", detalles: { cedula: ["Inválida"] } },
    }),
  });
  await assert.rejects(
    api("cuentas/estudiantes/"),
    (error) =>
      error instanceof ApiError &&
      error.status === 400 &&
      error.details.cedula[0] === "Inválida",
  );
});
test("el estado rechazado se presenta en lenguaje humano", () => {
  assert.equal(human("RECHAZADO"), "Rechazado");
  assert.equal(human("CUIDADOR_AUTORIZACION_RECHAZADA"), "Solicitud rechazada");
});
test("un login inválido muestra el error sin redirigir ni vaciar el formulario", async () => {
  let redirected = false;
  globalThis.location = {
    origin: "http://localhost",
    assign: () => {
      redirected = true;
    },
  };
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ error: { mensaje: "Credenciales inválidas" } }),
  });
  await assert.rejects(
    api("autenticacion/ingresar/", { method: "POST", body: {} }),
  );
  assert.equal(redirected, false);
});

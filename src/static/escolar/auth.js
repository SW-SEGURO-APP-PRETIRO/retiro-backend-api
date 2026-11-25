import { api, errorText } from "./api.js";
const mode = document.body.dataset.auth;
const form = document.querySelector("#auth-form");
const errorBox = document.querySelector("#auth-error");
const message = document.querySelector("#auth-message");
const endpoints = {
  ingresar: "ingresar",
  recuperar: "solicitar-recuperacion",
  restablecer: "confirmar-recuperacion",
  "cambiar-contrasena": "cambiar-contrasena-temporal",
};
if (mode === "restablecer")
  form.elements.token.value =
    new URLSearchParams(location.search).get("token") || "";
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;
  message.hidden = true;
  const data = Object.fromEntries(new FormData(form));
  delete data.csrfmiddlewaretoken;
  if (
    data.confirmacion !== undefined &&
    data.confirmacion !== data.nueva_contrasena
  ) {
    errorBox.textContent = "Las contraseñas no coinciden.";
    errorBox.hidden = false;
    return;
  }
  delete data.confirmacion;
  const button = form.querySelector("[type=submit]");
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Procesando…";
  try {
    const result = await api(`autenticacion/${endpoints[mode]}/`, {
      method: "POST",
      body: data,
    });
    if (mode === "ingresar") {
      const rol = result.datos.usuario.rol;
      if (rol === "ADMIN_SISTEMA") {
        location.assign(
          result.datos.sesion.requiere_cambio_contrasena
            ? "/autenticacion/cambiar-contrasena/"
            : "/sistema/",
        );
        return;
      }
      if (rol !== "ADMIN_ESCOLAR") {
        await api("autenticacion/cerrar-sesion/", { method: "POST" });
        throw new Error(
          "Acceso exclusivo para administración: los padres, guardias y cuidadores fijos no tienen acceso a los paneles web.",
        );
      }
      location.assign(
        result.datos.sesion.requiere_cambio_contrasena
          ? "/autenticacion/cambiar-contrasena/"
          : "/escolar/",
      );
    } else if (mode === "recuperar") {
      message.textContent = result.mensaje;
      message.hidden = false;
      // El contrato actual devuelve el token en desarrollo; no persistirlo ni registrarlo.
      const link = document.createElement("a");
      link.href = "/autenticacion/restablecer/";
      link.textContent = "Ingresar token de recuperación";
      link.className = "auth-link";
      message.append(link);
      if (document.body.dataset.preview === "true" && result.datos?.token) {
        const code = document.createElement("code");
        code.textContent = result.datos.token;
        message.append(code);
      }
    } else {
      location.assign("/autenticacion/ingresar/");
    }
  } catch (error) {
    errorBox.textContent =
      mode === "ingresar" && error.status === 401
        ? // Credenciales erróneas: mensaje genérico. Otros motivos (solicitud pendiente, cuenta
          // bloqueada…) los explica el servidor y se muestran tal cual.
          error.message && error.message !== "Credenciales inválidas."
          ? error.message
          : "No se pudo iniciar sesión. Revisa tus credenciales."
        : errorText(error);
    errorBox.hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = label;
  }
});

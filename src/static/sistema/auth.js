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
      if (result.datos.usuario.rol !== "ADMIN_SISTEMA") {
        await api("autenticacion/cerrar-sesion/", { method: "POST" });
        throw new Error(
          "Este panel es exclusivo para el Administrador del Sistema (ADMIN_SISTEMA).",
        );
      }
      location.assign(
        result.datos.sesion.requiere_cambio_contrasena
          ? "/sistema/autenticacion/cambiar-contrasena/"
          : "/sistema/",
      );
    } else if (mode === "recuperar") {
      message.textContent = result.mensaje;
      message.hidden = false;
      const link = document.createElement("a");
      link.href = "/sistema/autenticacion/restablecer/";
      link.textContent = "Ingresar token de recuperación";
      link.className = "auth-link";
      message.append(link);
      if (document.body.dataset.preview === "true" && result.datos?.token) {
        const code = document.createElement("code");
        code.textContent = result.datos.token;
        message.append(code);
      }
    } else {
      location.assign("/sistema/autenticacion/ingresar/");
    }
  } catch (error) {
    errorBox.textContent =
      mode === "ingresar" && error.status === 401
        ? "No se pudo iniciar sesión. Revisa tus credenciales y el código de verificación."
        : errorText(error);
    errorBox.hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = label;
  }
});

import { api, errorText } from "./api.js";
const mode = document.body.dataset.auth;
const form = document.querySelector("#auth-form");
const errorBox = document.querySelector("#auth-error");
const message = document.querySelector("#auth-message");
let lockTimer;
function showLoginError(error) {
  const text = error.message || "No se pudo iniciar sesión.";
  const lockedUntil = Date.parse(error.details?.bloqueado_hasta || "");
  if (!Number.isFinite(lockedUntil)) {
    errorBox.textContent = text;
    return;
  }

  errorBox.dataset.lockedUntil = String(lockedUntil);
  const updateCountdown = () => {
    const remaining = Math.max(0, Math.ceil((lockedUntil - Date.now()) / 1000));
    if (!remaining) {
      clearInterval(lockTimer);
      delete errorBox.dataset.lockedUntil;
      form.querySelector("[type=submit]").disabled = false;
      errorBox.textContent = "El bloqueo terminó. Ya puedes intentar de nuevo.";
      return;
    }
    const minutes = Math.floor(remaining / 60);
    const seconds = String(remaining % 60).padStart(2, "0");
    errorBox.textContent = `${text} Tiempo restante: ${minutes}:${seconds}.`;
  };
  updateCountdown();
  if (lockedUntil > Date.now()) lockTimer = setInterval(updateCountdown, 1000);
}
const endpoints = {
  ingresar: "ingresar",
  recuperar: "solicitar-recuperacion",
  restablecer: "confirmar-recuperacion",
  "cambiar-contrasena": "cambiar-contrasena-temporal",
};
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearInterval(lockTimer);
  delete errorBox.dataset.lockedUntil;
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
    } else {
      location.assign("/sistema/autenticacion/ingresar/");
    }
  } catch (error) {
    if (mode === "ingresar" && error.status === 401) showLoginError(error);
    else errorBox.textContent = errorText(error);
    errorBox.hidden = false;
  } finally {
    const lockedUntil = Number(errorBox.dataset.lockedUntil);
    button.disabled = Number.isFinite(lockedUntil) && lockedUntil > Date.now();
    button.textContent = label;
  }
});

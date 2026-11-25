// Validación en el cliente del registro. Solo mejora la experiencia: el servidor vuelve a validar todo.
const form = document.querySelector("#registro-form");
const boton = document.querySelector("#registro-enviar");

function mensaje(input) {
  const v = input.validity;
  const nombre = input.closest("label")?.querySelector("span")?.textContent.replace("*", "").trim() || "Este campo";
  if (v.valueMissing) return `${nombre} es obligatorio.`;
  if (v.typeMismatch) return "Escribe un correo válido, por ejemplo nombre@dominio.com.";
  if (v.patternMismatch) return input.title || "El formato no es válido.";
  if (v.tooShort) return `Debe tener al menos ${input.minLength} caracteres.`;
  if (v.tooLong) return `Debe tener como máximo ${input.maxLength} caracteres.`;
  if (input.name === "confirmar_contrasena" && input.value !== form.elements.contrasena.value)
    return "Las contraseñas no coinciden.";
  return "";
}

function validar(input) {
  const label = input.closest("label");
  if (!label) return true;
  // Quita solo los mensajes generados en el cliente; los del servidor se van cuando se edita el campo
  label.querySelectorAll(".field-error.cliente").forEach((el) => el.remove());
  const texto = mensaje(input);
  const delServidor = label.querySelector(".field-error:not(.cliente)");
  label.classList.toggle("con-error", Boolean(texto || delServidor));
  input.setAttribute("aria-invalid", texto || delServidor ? "true" : "false");
  if (texto) {
    const error = document.createElement("small");
    error.className = "field-error cliente";
    error.id = `${input.id}-error`;
    error.textContent = texto;
    label.append(error);
    input.setAttribute("aria-describedby", error.id);
  } else input.removeAttribute("aria-describedby");
  return !texto;
}

// Solo dígitos en cédula, RUC y teléfonos (inputmode="numeric")
form.querySelectorAll('input[inputmode="numeric"]').forEach((input) =>
  input.addEventListener("input", () => {
    const limpio = input.value.replace(/\D/g, "");
    if (limpio !== input.value) input.value = limpio;
  }),
);

form.querySelectorAll("input").forEach((input) => {
  input.addEventListener("blur", () => input.value && validar(input));
  input.addEventListener("input", () => {
    const label = input.closest("label");
    if (!label?.classList.contains("con-error")) return;
    label.querySelectorAll(".field-error:not(.cliente)").forEach((el) => el.remove());
    validar(input);
  });
});
form.elements.contrasena.addEventListener("input", () => {
  const confirmar = form.elements.confirmar_contrasena;
  if (confirmar.value) validar(confirmar);
});

form.addEventListener("submit", (event) => {
  const invalidos = [...form.querySelectorAll("input:not([type=hidden])")].filter((i) => !validar(i));
  if (invalidos.length) {
    event.preventDefault();
    invalidos[0].focus();
    return;
  }
  // Evita envíos dobles mientras el servidor responde
  boton.disabled = true;
  boton.textContent = "Enviando solicitud…";
});

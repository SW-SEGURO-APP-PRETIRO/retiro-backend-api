export class ApiError extends Error {
  constructor(message, status = 0, details = {}) {
    super(message);
    this.status = status;
    this.details = details;
  }
}
export function csrfToken() {
  return decodeURIComponent(
    document.cookie
      .split("; ")
      .find((c) => c.startsWith("csrftoken="))
      ?.split("=")
      .slice(1)
      .join("=") || "",
  );
}
export async function api(path, { method = "GET", body, signal } = {}) {
  const url = new URL(
    path.startsWith("/api/") ? path : `/api/v1/${path}`,
    location.origin,
  );
  if (url.origin !== location.origin || !url.pathname.startsWith("/api/v1/"))
    throw new ApiError("Destino no permitido.");
  let response;
  try {
    response = await fetch(url, {
      method,
      credentials: "same-origin",
      cache: "no-store",
      signal,
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(method !== "GET" ? { "X-CSRFToken": csrfToken() } : {}),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(
      "No se pudo conectar. Revisa tu conexión e inténtalo de nuevo.",
    );
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new ApiError(
      payload.error?.mensaje || "No se pudo completar la solicitud.",
      response.status,
      payload.error?.detalles || {},
    );
    const publicEndpoint =
      /\/autenticacion\/(ingresar|solicitar-recuperacion|confirmar-recuperacion)\/$/.test(
        url.pathname,
      );
    if (
      !publicEndpoint &&
      (response.status === 401 ||
        (response.status === 403 &&
          payload.error?.codigo === "NOT_AUTHENTICATED"))
    ) {
      location.assign("/sistema/autenticacion/ingresar/");
    }
    throw error;
  }
  return payload;
}
export function errorText(error) {
  const details = Object.entries(error.details || {}).map(
    ([field, messages]) =>
      `${field.replaceAll("_", " ")}: ${Array.isArray(messages) ? messages.join(" ") : String(messages)}`,
  );
  return [error.message, ...details].join(" ");
}
export function escapeHTML(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}
export function rows(payload) {
  return Array.isArray(payload.datos)
    ? payload.datos
    : payload.datos?.resultados || [];
}

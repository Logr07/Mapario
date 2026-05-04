const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const DEFAULT_TIMEOUT_MS = normalizeTimeout(import.meta.env.VITE_API_TIMEOUT_MS, 20000);
const CSRF_HEADER_NAME = "X-CSRF-Token";

let csrfToken = "";
let csrfTokenPromise = null;

/**
 * Odesle autentizovaný API požadavek s automatickou správou CSRF tokenu,
 * timeoutem a jednim transparentním retry při vypršení CSRF (403).
 *
 * @param {string} path - Cesta API relativně k base URL (např. `/auth/me`).
 * @param {object} [options={}] - Fetch options plus následující rozšíření:
 * @param {BodyInit} [options.body] - Tělo požadavku.
 * @param {boolean} [options.csrfRetry=true] - Zda se má po 403 zkusit znovu.
 * @param {object} [options.headers] - Další hlavičky přidané k požadavku.
 * @param {AbortSignal} [options.signal] - Externí abort signál.
 * @param {number} [options.timeoutMs] - Přepis výchozího timeoutu.
 * @returns {Promise<object|null>} Parsovaný JSON payload, nebo `null` pro 204 odpovědi.
 * @throws {Error} Při síťové chybě, timeoutu nebo ne-OK HTTP odpovědi.
 */
export async function apiRequest(path, options = {}) {
  const {
    body,
    csrfRetry = true,
    headers: customHeaders,
    signal,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    ...fetchOptions
  } = options;
  const method = String(fetchOptions.method || "GET").toUpperCase();
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(customHeaders || {}),
  };

  if (requiresCsrfToken(method, path) && !headers[CSRF_HEADER_NAME]) {
    headers[CSRF_HEADER_NAME] = await getCsrfToken();
  }

  const { requestSignal, cleanup } = createTimeoutSignal(signal, timeoutMs);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      ...fetchOptions,
      method,
      body,
      headers,
      signal: requestSignal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Server neodpověděl včas. Zkus to prosím znovu.");
    }
    throw error;
  } finally {
    cleanup();
  }

  if (response.status === 403 && requiresCsrfToken(method, path) && csrfRetry) {
    csrfToken = "";
    await getCsrfToken({ force: true });
    return apiRequest(path, {
      body,
      csrfRetry: false,
      headers: customHeaders,
      signal,
      timeoutMs,
      ...fetchOptions,
    });
  }

  if (!response.ok) {
    const detail = await readError(response);
    throw new Error(detail || `API request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    if (path === "/auth/logout") {
      csrfToken = "";
    }
    return null;
  }

  const payload = await response.json();
  if (payload && typeof payload.csrf_token === "string") {
    csrfToken = payload.csrf_token;
  }
  return payload;
}

async function readError(response) {
  try {
    const payload = await response.json();
    return payload.message || payload.error || payload.detail;
  } catch {
    return "";
  }
}

/**
 * Sloučí externí abort signál s volitelným timeoutem do jednoho AbortControlleru.
 * Vrací výsledný signál a cleanup funkci, která musí být zavolána po požadavku.
 *
 * @param {AbortSignal|undefined} signal
 * @param {number} timeoutMs
 * @returns {{ requestSignal: AbortSignal, cleanup: function }}
 */
function createTimeoutSignal(signal, timeoutMs) {
  const hasTimeout = Number.isFinite(timeoutMs) && timeoutMs > 0;
  if (typeof AbortController === "undefined" || (!hasTimeout && !signal)) {
    return { requestSignal: signal, cleanup: () => {} };
  }

  const controller = new AbortController();
  let timeoutId = null;
  let abortHandler = null;

  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      abortHandler = () => controller.abort();
      signal.addEventListener("abort", abortHandler, { once: true });
    }
  }

  if (hasTimeout) {
    timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  }

  return {
    requestSignal: controller.signal,
    cleanup: () => {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
      if (signal && abortHandler) {
        signal.removeEventListener("abort", abortHandler);
      }
    },
  };
}

function normalizeTimeout(rawValue, fallback) {
  const value = Number.parseInt(rawValue, 10);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

/** @returns {boolean} `true` pokud daná kombinace metody a cesty vyžaduje CSRF token. */
function requiresCsrfToken(method, path) {
  return !["GET", "HEAD", "OPTIONS", "TRACE"].includes(method) && path !== "/auth/csrf";
}

/**
 * Načte (nebo vrátí cachovaný) CSRF token; souběžné požadavky jsou deduplikovany.
 *
 * @param {{ force?: boolean }} [options]
 * @returns {Promise<string>}
 */
async function getCsrfToken({ force = false } = {}) {
  if (csrfToken && !force) {
    return csrfToken;
  }

  if (!csrfTokenPromise || force) {
    csrfTokenPromise = fetch(`${API_BASE_URL}/auth/csrf`, {
      credentials: "include",
      headers: {
        Accept: "application/json",
      },
    })
      .then(async (response) => {
        if (!response.ok) {
          const detail = await readError(response);
          throw new Error(detail || "CSRF token se nepodařilo načíst.");
        }
        const payload = await response.json();
        if (!payload?.csrf_token) {
          throw new Error("CSRF token se nepodařilo načíst.");
        }
        csrfToken = payload.csrf_token;
        return csrfToken;
      })
      .finally(() => {
        csrfTokenPromise = null;
      });
  }

  return csrfTokenPromise;
}

// The founder token is a random session secret issued by the backend (not a password).
const KEY = "mate.founderToken";

let memoryToken: string | null = null;

export function getToken(): string | null {
  try {
    return window.localStorage.getItem(KEY) ?? memoryToken;
  } catch {
    return memoryToken;
  }
}

export function setToken(token: string | null): void {
  memoryToken = token;
  try {
    if (token) window.localStorage.setItem(KEY, token);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: keep the in-memory copy */
  }
}

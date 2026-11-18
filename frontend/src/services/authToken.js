import { API_BASE_URL } from './apiBase.js';

const GUEST_TOKEN_KEY = 'flightguard_guest_access_token';
const GUEST_EXPIRY_KEY = 'flightguard_guest_access_expiry';
const GUEST_ID_KEY = 'flightguard_guest_id';
let tokenGetter = null;
let guestPromise = null;

export function setAuthTokenGetter(getter) {
  tokenGetter = getter;
}

export function getGuestIdentity() {
  return localStorage.getItem(GUEST_ID_KEY);
}

export async function createOrReuseGuestSession() {
  const existing = localStorage.getItem(GUEST_TOKEN_KEY);
  const expiry = Number(localStorage.getItem(GUEST_EXPIRY_KEY) || 0);
  const existingUserId = getGuestIdentity();
  if (existing && existingUserId && expiry > Date.now() + 60_000) {
    return { token: existing, userId: existingUserId };
  }
  if (!guestPromise) {
    guestPromise = fetch(`${API_BASE_URL.replace(/\/$/, '')}/auth/guest`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    }).then(async (response) => {
      if (!response.ok) throw new Error('Guest access could not be initialized.');
      const data = await response.json();
      localStorage.setItem(GUEST_TOKEN_KEY, data.access_token);
      localStorage.setItem(GUEST_EXPIRY_KEY, String(Date.now() + data.expires_in * 1000));
      localStorage.setItem(GUEST_ID_KEY, data.user.id);
      return { token: data.access_token, userId: data.user.id };
    }).finally(() => { guestPromise = null; });
  }
  return guestPromise;
}

export async function getApiToken() {
  if (tokenGetter) return tokenGetter();
  const guest = await createOrReuseGuestSession();
  return guest.token;
}

export function clearGuestSession() {
  localStorage.removeItem(GUEST_TOKEN_KEY);
  localStorage.removeItem(GUEST_EXPIRY_KEY);
  localStorage.removeItem(GUEST_ID_KEY);
}

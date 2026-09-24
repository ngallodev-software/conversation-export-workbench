const STORAGE_KEY = 'cew-app-lock-v1';
const ITERATIONS = 210000;

function bytesToBase64(bytes) {
  let binary = '';
  for (const value of bytes) binary += String.fromCharCode(value);
  return btoa(binary);
}

function base64ToBytes(value) {
  const binary = atob(value);
  return Uint8Array.from(binary, char => char.charCodeAt(0));
}

async function derive(pin, salt, iterations = ITERATIONS) {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(String(pin)),
    'PBKDF2',
    false,
    ['deriveBits'],
  );
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', hash: 'SHA-256', salt, iterations },
    key,
    256,
  );
  return new Uint8Array(bits);
}

export function hasAppLock() {
  return Boolean(localStorage.getItem(STORAGE_KEY));
}

export async function setAppLock(pin) {
  if (String(pin).length < 4) throw new Error('App lock PIN must be at least 4 characters');
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const hash = await derive(pin, salt);
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    version: 1,
    iterations: ITERATIONS,
    salt: bytesToBase64(salt),
    hash: bytesToBase64(hash),
  }));
}

export async function verifyAppLock(pin) {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return true;
  let config;
  try {
    config = JSON.parse(raw);
  } catch {
    return false;
  }
  const actual = await derive(
    pin,
    base64ToBytes(config.salt),
    Number(config.iterations) || ITERATIONS,
  );
  const expected = base64ToBytes(config.hash);
  if (actual.length !== expected.length) return false;
  let mismatch = 0;
  for (let index = 0; index < actual.length; index += 1) {
    mismatch |= actual[index] ^ expected[index];
  }
  return mismatch === 0;
}

export function clearAppLock() {
  localStorage.removeItem(STORAGE_KEY);
}

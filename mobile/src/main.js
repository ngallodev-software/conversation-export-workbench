import { strFromU8, unzipSync } from 'fflate';
import { NativeBiometrics } from '@ngallodev/cew-native-biometrics';
import { clearAppLock, hasAppLock, setAppLock, verifyAppLock } from './app-lock.js';
import {
  CONVERSATION_SCHEMA,
  buildSearchIndex,
  detectProvider,
  normalizeProviderExport,
} from './providers.js';

const BUNDLE_SCHEMAS = new Set(['cew.bundle/v1', 'cew.bundle/v2']);
const REQUIRED_FILES = new Set(['manifest.json', 'conversations.json', 'search.json']);
const MAX_COMPRESSED_BYTES = 128 * 1024 * 1024;
const MAX_MEMBER_BYTES = 256 * 1024 * 1024;
const MAX_ATTACHMENT_TOTAL_BYTES = 128 * 1024 * 1024;
const MAX_RATIO = 200;
const THEME_KEY = 'cew-theme';
const THEMES = ['system', 'dark', 'light'];

const input = document.getElementById('bundle-input');
const search = document.getElementById('search');
const clearButton = document.getElementById('clear-archive');
const list = document.getElementById('conversation-list');
const article = document.getElementById('conversation');
const emptyState = document.getElementById('empty-state');
const archiveMeta = document.getElementById('archive-meta');
const status = document.getElementById('status');
const themeToggle = document.getElementById('theme-toggle');
const lockNow = document.getElementById('lock-now');
const removeLock = document.getElementById('remove-lock');
const lockScreen = document.getElementById('lock-screen');
const unlockForm = document.getElementById('unlock-form');
const unlockPin = document.getElementById('unlock-pin');
const unlockError = document.getElementById('unlock-error');
const biometricUnlock = document.getElementById('biometric-unlock');
const attachmentsButton = document.getElementById('attachments-button');
const attachmentsDialog = document.getElementById('attachments-dialog');
const attachmentsClose = document.getElementById('attachments-close');
const attachmentsList = document.getElementById('attachments-list');

let archive = null;
let activeId = null;
let initialized = false;
let currentTheme = localStorage.getItem(THEME_KEY) || 'system';

function setStatus(message) {
  status.textContent = message;
  status.classList.add('visible');
  window.clearTimeout(setStatus.timer);
  setStatus.timer = window.setTimeout(() => status.classList.remove('visible'), 2800);
}

function decodeJson(bytes, name) {
  try {
    return JSON.parse(strFromU8(bytes));
  } catch {
    throw new Error('Invalid JSON in ' + name);
  }
}

function safeUrl(raw) {
  try {
    const url = new URL(String(raw || ''));
    if (url.protocol === 'https:' || url.protocol === 'http:') return url.href;
  } catch {}
  return null;
}

function validateConversation(record) {
  if (!record || record.schema_version !== CONVERSATION_SCHEMA) {
    throw new Error('Unsupported conversation schema');
  }
  if (!Array.isArray(record.messages)) throw new Error('Conversation messages must be an array');
}

async function sha256Hex(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
}

async function parseBundle(fileBytes) {
  const rejected = [];
  let attachmentTotal = 0;
  const files = unzipSync(fileBytes, {
    filter(info) {
      const isAttachment = String(info.name || '').startsWith('attachments/');
      if (!REQUIRED_FILES.has(info.name) && !isAttachment) return false;
      if (isAttachment) {
        attachmentTotal += Number(info.originalSize || 0);
        if (attachmentTotal > MAX_ATTACHMENT_TOTAL_BYTES) {
          rejected.push('attachment payloads exceed mobile import limit');
          return false;
        }
      }
      if (info.originalSize > MAX_MEMBER_BYTES) {
        rejected.push(info.name + ': member too large');
        return false;
      }
      if (info.size > 0 && info.originalSize / info.size > MAX_RATIO) {
        rejected.push(info.name + ': suspicious compression ratio');
        return false;
      }
      return true;
    },
  });
  if (rejected.length) throw new Error(rejected[0]);
  for (const name of REQUIRED_FILES) {
    if (!files[name]) throw new Error('Bundle missing ' + name);
  }

  const manifest = decodeJson(files['manifest.json'], 'manifest.json');
  const conversations = decodeJson(files['conversations.json'], 'conversations.json');
  const searchIndex = decodeJson(files['search.json'], 'search.json');

  if (!BUNDLE_SCHEMAS.has(manifest.schema_version)) throw new Error('Unsupported .cew bundle schema');
  if (manifest.conversation_schema !== CONVERSATION_SCHEMA) throw new Error('Unsupported canonical conversation schema');
  if (!Array.isArray(conversations) || !Array.isArray(searchIndex)) throw new Error('Invalid bundle payload');
  if (manifest.conversation_count !== conversations.length) throw new Error('Bundle conversation count mismatch');
  conversations.forEach(validateConversation);

  const attachmentEntries = Array.isArray(manifest.attachments) ? manifest.attachments : [];
  const attachments = {};
  for (const entry of attachmentEntries) {
    if (!entry || typeof entry !== 'object') throw new Error('Invalid attachment metadata');
    const path = String(entry.path || '');
    if (!path.startsWith('attachments/')) throw new Error('Unsafe attachment path');
    const payload = files[path];
    if (!payload) throw new Error('Bundle attachment missing: ' + path);
    if (Number(entry.size) !== payload.byteLength) throw new Error('Attachment size mismatch: ' + path);
    const digest = await sha256Hex(payload);
    if (digest !== String(entry.sha256 || '')) throw new Error('Attachment hash mismatch: ' + path);
    attachments[path] = {
      bytes: payload,
      name: String(entry.name || path.split('/').pop() || 'attachment'),
      mime_type: String(entry.mime_type || 'application/octet-stream'),
      sha256: digest,
    };
  }

  return { manifest, conversations, searchIndex, attachments };
}

function rawImportManifest(conversations, filename, provider) {
  return {
    schema_version: 'cew.mobile-import/v1',
    conversation_schema: CONVERSATION_SCHEMA,
    conversation_count: conversations.length,
    providers: [...new Set(conversations.map(record => record.provider))].sort(),
    sources: [{ kind: 'provider-export', filename, provider }],
  };
}

function parseProviderData(data, filename) {
  const provider = detectProvider(data);
  if (!provider) throw new Error('Could not detect ChatGPT, Claude, or DeepSeek export');
  const conversations = normalizeProviderExport(data, provider);
  conversations.forEach(validateConversation);
  return {
    manifest: rawImportManifest(conversations, filename, provider),
    conversations,
    searchIndex: buildSearchIndex(conversations),
  };
}

function parseRawZip(fileBytes, filename) {
  const rejected = [];
  const files = unzipSync(fileBytes, {
    filter(info) {
      const basename = String(info.name || '').split('/').pop();
      if (basename !== 'conversations.json') return false;
      if (info.originalSize > MAX_MEMBER_BYTES) {
        rejected.push(info.name + ': member too large');
        return false;
      }
      if (info.size > 0 && info.originalSize / info.size > MAX_RATIO) {
        rejected.push(info.name + ': suspicious compression ratio');
        return false;
      }
      return true;
    },
  });
  if (rejected.length) throw new Error(rejected[0]);
  const names = Object.keys(files).filter(name => name.split('/').pop() === 'conversations.json').sort();
  if (!names.length) throw new Error('ZIP does not contain conversations.json');
  if (names.length > 64) throw new Error('ZIP contains too many conversations.json files');
  return parseProviderData(decodeJson(files[names[0]], names[0]), filename);
}

async function parseImportedFile(file) {
  if (file.size > MAX_COMPRESSED_BYTES) throw new Error('Import file is too large');
  const bytes = new Uint8Array(await file.arrayBuffer());
  const lower = file.name.toLowerCase();
  if (lower.endsWith('.cew')) return await parseBundle(bytes);
  if (lower.endsWith('.zip')) return parseRawZip(bytes, file.name);
  if (lower.endsWith('.json')) return parseProviderData(decodeJson(bytes, file.name), file.name);
  throw new Error('Choose a .cew, provider export .zip, or conversations .json file');
}

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('cew-mobile', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('archive');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function storeArchive(value) {
  const db = await openDatabase();
  await new Promise((resolve, reject) => {
    const tx = db.transaction('archive', 'readwrite');
    tx.objectStore('archive').put(value, 'current');
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

async function loadStoredArchive() {
  const db = await openDatabase();
  const value = await new Promise((resolve, reject) => {
    const tx = db.transaction('archive', 'readonly');
    const req = tx.objectStore('archive').get('current');
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
  db.close();
  return value;
}

async function clearStoredArchive() {
  const db = await openDatabase();
  await new Promise((resolve, reject) => {
    const tx = db.transaction('archive', 'readwrite');
    tx.objectStore('archive').delete('current');
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

function conversationKey(record) {
  return String(record.provider || '') + ':' + String(record.id || '');
}

function matchingConversations(query) {
  if (!archive) return [];
  const q = query.trim().toLowerCase();
  if (!q) return archive.conversations;
  const ids = new Set(
    archive.searchIndex
      .filter(item => String(item.title || '').toLowerCase().includes(q) || String(item.text || '').toLowerCase().includes(q))
      .map(item => String(item.provider || '') + ':' + String(item.id || ''))
  );
  return archive.conversations.filter(record => ids.has(conversationKey(record)));
}

function renderList() {
  list.replaceChildren();
  if (!archive) return;
  const matches = matchingConversations(search.value);
  for (const record of matches) {
    const li = document.createElement('li');
    const button = document.createElement('button');
    if (conversationKey(record) === activeId) button.classList.add('active');
    const title = document.createElement('span');
    title.className = 'conv-title';
    title.textContent = record.title || 'Untitled';
    const provider = document.createElement('span');
    provider.className = 'conv-provider';
    provider.textContent = record.provider;
    button.append(title, provider);
    button.addEventListener('click', () => renderConversation(record));
    li.append(button);
    list.append(li);
  }
}

function externalLink(label, raw) {
  const href = safeUrl(raw);
  if (!href) {
    const span = document.createElement('span');
    span.textContent = label || raw || '';
    return span;
  }
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.textContent = label || href;
  anchor.rel = 'noopener noreferrer';
  anchor.className = 'read-link';
  anchor.addEventListener('click', event => {
    event.preventDefault();
    if (window.confirm('Open external link?\n\n' + href)) {
      window.open(href, '_blank', 'noopener,noreferrer');
    }
  });
  return anchor;
}

function renderPart(part) {
  const type = part?.type;
  if (type === 'text' || type === 'thinking') {
    const div = document.createElement('div');
    div.className = 'part ' + (type === 'thinking' ? 'thinking' : '');
    div.textContent = String(part.content || '');
    return div;
  }
  if (type === 'search') {
    const wrapper = document.createElement('div');
    wrapper.className = 'part';
    for (const result of Array.isArray(part.results) ? part.results : []) {
      const row = document.createElement('div');
      row.className = 'search-result';
      row.append(externalLink(String(result.title || result.url || ''), result.url));
      if (result.snippet) {
        const snippet = document.createElement('div');
        snippet.textContent = String(result.snippet);
        row.append(snippet);
      }
      wrapper.append(row);
    }
    return wrapper;
  }
  if (type === 'read_link') {
    const div = document.createElement('div');
    div.className = 'part';
    div.append(externalLink(String(part.url || ''), part.url));
    return div;
  }
  if (type === 'tool_use' || type === 'tool_result') {
    const details = document.createElement('details');
    details.className = 'part tool-part';
    const summary = document.createElement('summary');
    summary.textContent = type === 'tool_use' ? 'Tool: ' + (part.name || 'use') : 'Tool result';
    const pre = document.createElement('pre');
    pre.textContent = JSON.stringify(type === 'tool_use' ? part.input : part.content, null, 2);
    details.append(summary, pre);
    return details;
  }
  if (type === 'attachment') {
    const div = document.createElement('div');
    div.className = 'part';
    div.textContent = 'Attachment: ' + (part.name || 'unnamed');
    return div;
  }
  return document.createDocumentFragment();
}

function renderConversation(record) {
  activeId = conversationKey(record);
  article.replaceChildren();
  const title = document.createElement('h2');
  title.textContent = record.title || 'Untitled';
  const meta = document.createElement('div');
  meta.className = 'conversation-meta';
  meta.textContent = String(record.provider || '') + ' · ' + String(record.started_at || '');
  article.append(title, meta);

  for (const message of record.messages) {
    const section = document.createElement('section');
    section.className = 'message ' + (message.role || 'assistant');
    const role = document.createElement('div');
    role.className = 'message-role';
    role.textContent = message.role || 'assistant';
    section.append(role);
    for (const part of Array.isArray(message.parts) ? message.parts : []) {
      section.append(renderPart(part));
    }
    article.append(section);
  }
  emptyState.hidden = true;
  article.hidden = false;
  renderList();
  article.focus({ preventScroll: true });
}

function archiveStats(value) {
  const providerCounts = new Map();
  let messages = 0;
  let attachmentParts = 0;
  for (const record of value.conversations) {
    providerCounts.set(record.provider, (providerCounts.get(record.provider) || 0) + 1);
    messages += Array.isArray(record.messages) ? record.messages.length : 0;
    for (const message of Array.isArray(record.messages) ? record.messages : []) {
      for (const part of Array.isArray(message.parts) ? message.parts : []) {
        if (part?.type === 'attachment') attachmentParts += 1;
      }
    }
  }
  const providers = [...providerCounts.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(entry => entry[0] + ' ' + entry[1])
    .join(' · ');
  return {
    conversations: value.conversations.length,
    messages,
    attachments: Math.max(attachmentParts, Object.keys(value.attachments || {}).length),
    providers,
  };
}

function renderArchive() {
  if (!archive) {
    archiveMeta.textContent = 'No archive imported.';
    attachmentsButton.hidden = true;
    list.replaceChildren();
    article.hidden = true;
    emptyState.hidden = false;
    return;
  }
  const stats = archiveStats(archive);
  const attachmentText = stats.attachments ? ' · ' + stats.attachments + ' attachments' : '';
  archiveMeta.textContent =
    stats.conversations + ' conversations · ' +
    stats.messages + ' messages' +
    attachmentText +
    (stats.providers ? ' · ' + stats.providers : '');
  attachmentsButton.hidden = stats.attachments === 0;
  attachmentsButton.textContent = 'Attachments (' + stats.attachments + ')';
  renderList();
}

async function shareOrDownloadAttachment(metadata) {
  const attachment = archive?.attachments?.[metadata.path];
  if (!attachment) {
    setStatus('Attachment payload is not available in this archive.');
    return;
  }
  const blob = new Blob([attachment.bytes], { type: attachment.mime_type || 'application/octet-stream' });
  const file = new File([blob], attachment.name, { type: blob.type });
  try {
    if (navigator.canShare && navigator.canShare({ files: [file] }) && navigator.share) {
      await navigator.share({ files: [file], title: attachment.name });
      return;
    }
  } catch (error) {
    if (error?.name === 'AbortError') return;
  }

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = attachment.name;
  anchor.rel = 'noopener';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderAttachmentLibrary() {
  attachmentsList.replaceChildren();
  if (!archive) return;
  const entries = Array.isArray(archive.manifest?.attachments) ? archive.manifest.attachments : [];
  for (const entry of entries) {
    const item = document.createElement('li');
    const info = document.createElement('div');
    const name = document.createElement('strong');
    name.textContent = String(entry.name || 'attachment');
    const detail = document.createElement('span');
    detail.textContent = ' · ' + Math.round(Number(entry.size || 0) / 1024) + ' KB';
    info.append(name, detail);
    const action = document.createElement('button');
    action.type = 'button';
    action.className = 'subtle-button';
    action.textContent = 'Share / Save';
    action.addEventListener('click', () => shareOrDownloadAttachment(entry));
    item.append(info, action);
    attachmentsList.append(item);
  }
}

function resolvedTheme(mode) {
  if (mode !== 'system') return mode;
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function applyTheme(mode) {
  currentTheme = THEMES.includes(mode) ? mode : 'system';
  localStorage.setItem(THEME_KEY, currentTheme);
  document.documentElement.dataset.theme = resolvedTheme(currentTheme);
  themeToggle.textContent = 'Theme: ' + currentTheme;
}

function cycleTheme() {
  const index = THEMES.indexOf(currentTheme);
  applyTheme(THEMES[(index + 1) % THEMES.length]);
}

function updateLockButtons() {
  const configured = hasAppLock();
  lockNow.textContent = configured ? 'Lock now' : 'Set app lock';
  removeLock.hidden = !configured;
}

async function refreshBiometricAvailability() {
  biometricUnlock.hidden = true;
  if (!hasAppLock()) return false;
  try {
    const result = await NativeBiometrics.isAvailable();
    biometricUnlock.hidden = !result?.available;
    return Boolean(result?.available);
  } catch {
    return false;
  }
}

async function tryBiometricUnlock() {
  unlockError.textContent = '';
  biometricUnlock.disabled = true;
  try {
    const result = await NativeBiometrics.authenticate();
    if (!result?.authenticated) throw new Error('Biometric authentication was not accepted.');
    hideLockScreen();
    await initializeUnlockedApp();
    setStatus('Unlocked with device biometrics.');
  } catch (error) {
    unlockError.textContent = 'Biometric unlock was not completed. Use your PIN to continue.';
  } finally {
    biometricUnlock.disabled = false;
  }
}

function showLockScreen() {
  lockScreen.hidden = false;
  document.body.classList.add('locked');
  unlockError.textContent = '';
  unlockPin.value = '';
  window.setTimeout(() => unlockPin.focus(), 0);
  refreshBiometricAvailability();
}

function hideLockScreen() {
  lockScreen.hidden = true;
  document.body.classList.remove('locked');
  unlockError.textContent = '';
  unlockPin.value = '';
}

async function initializeUnlockedApp() {
  if (initialized) return;
  initialized = true;
  try {
    archive = await loadStoredArchive();
    renderArchive();
  } catch {
    setStatus('Could not restore local archive.');
  }
}

input.addEventListener('change', async () => {
  const file = input.files?.[0];
  if (!file) return;
  try {
    setStatus('Importing archive…');
    const parsed = await parseImportedFile(file);
    archive = parsed;
    activeId = null;
    await storeArchive(parsed);
    renderArchive();
    setStatus('Archive imported for offline use.');
  } catch (error) {
    setStatus(error instanceof Error ? error.message : 'Import failed');
  } finally {
    input.value = '';
  }
});

search.addEventListener('input', renderList);
themeToggle.addEventListener('click', cycleTheme);
attachmentsButton.addEventListener('click', () => {
  renderAttachmentLibrary();
  attachmentsDialog.showModal();
});
attachmentsClose.addEventListener('click', () => attachmentsDialog.close());

clearButton.addEventListener('click', async () => {
  if (archive && !window.confirm('Clear the imported archive from this device?')) return;
  await clearStoredArchive();
  archive = null;
  activeId = null;
  search.value = '';
  renderArchive();
  setStatus('Local archive cleared.');
});

lockNow.addEventListener('click', async () => {
  try {
    if (!hasAppLock()) {
      const pin = window.prompt('Create an app-lock PIN (at least 4 characters):');
      if (pin === null) return;
      const confirmPin = window.prompt('Confirm the app-lock PIN:');
      if (pin !== confirmPin) throw new Error('PIN confirmation did not match');
      await setAppLock(pin);
      updateLockButtons();
      setStatus('App lock enabled.');
    }
    showLockScreen();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : 'Could not configure app lock');
  }
});

removeLock.addEventListener('click', async () => {
  const pin = window.prompt('Enter the current app-lock PIN to remove it:');
  if (pin === null) return;
  if (!(await verifyAppLock(pin))) {
    setStatus('Incorrect app-lock PIN.');
    return;
  }
  clearAppLock();
  updateLockButtons();
  setStatus('App lock removed.');
});

biometricUnlock.addEventListener('click', tryBiometricUnlock);

unlockForm.addEventListener('submit', async event => {
  event.preventDefault();
  if (!(await verifyAppLock(unlockPin.value))) {
    unlockError.textContent = 'Incorrect PIN.';
    unlockPin.select();
    return;
  }
  hideLockScreen();
  await initializeUnlockedApp();
});

window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
  if (currentTheme === 'system') applyTheme('system');
});

applyTheme(currentTheme);
updateLockButtons();

if (hasAppLock()) {
  showLockScreen();
} else {
  await initializeUnlockedApp();
}

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

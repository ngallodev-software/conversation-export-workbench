"""
SPA (index.html) generator for the conversation viewer.

Scans output/<provider>/ directories, extracts title/timestamp metadata
from the generated HTML files, and writes output/index.html.

CSS is loaded from template files referenced in config/spa.toml.
"""

import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROVIDERS = ["deepseek", "claude", "chatgpt"]

PROVIDER_LABELS = {
    "deepseek": "DeepSeek",
    "claude":   "Claude",
    "chatgpt":  "ChatGPT",
    "all":      "All",
}

_DEFAULT_CONFIG = {
    "spa": {
        "main_template":   "config/spa_output_templates/main_spa.css",
        "thread_template": "config/spa_output_templates/thread.css",
    },
    "providers": {
        "deepseek": {
            "thread_template": "config/spa_output_templates/deepseek_thread.css",
            "accent_color": "#4a90e2",
            "label": "DeepSeek",
        },
        "claude": {
            "thread_template": "config/spa_output_templates/claude_thread.css",
            "accent_color": "#c57d3d",
            "label": "Claude",
        },
        "chatgpt": {
            "thread_template": "config/spa_output_templates/chatgpt_thread.css",
            "accent_color": "#10a37f",
            "label": "ChatGPT",
        },
    },
}


def load_config(config_path: Path | None = None) -> dict:
    """Load spa.toml or return defaults."""
    if config_path is None or not config_path.exists():
        return _DEFAULT_CONFIG

    if tomllib is None:
        print(
            "Warning: tomllib/tomli not available — using default config. "
            "Install tomli (`pip install tomli`) for Python < 3.11.",
            file=sys.stderr,
        )
        return _DEFAULT_CONFIG

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        # Merge with defaults so missing keys fall back gracefully
        merged = {
            "spa": {**_DEFAULT_CONFIG["spa"], **data.get("spa", {})},
            "providers": {},
        }
        for p, defaults in _DEFAULT_CONFIG["providers"].items():
            merged["providers"][p] = {**defaults, **data.get("providers", {}).get(p, {})}
        # Include any extra providers defined only in the toml
        for p, cfg in data.get("providers", {}).items():
            if p not in merged["providers"]:
                merged["providers"][p] = cfg
        return merged
    except Exception as e:
        print(f"Warning: failed to load {config_path}: {e} — using defaults.", file=sys.stderr)
        return _DEFAULT_CONFIG


def load_css_templates(config: dict, base_dir: Path) -> str:
    """Read and concatenate CSS template files in order."""
    paths = [config["spa"]["main_template"], config["spa"]["thread_template"]]
    for p_cfg in config["providers"].values():
        t = p_cfg.get("thread_template")
        if t:
            paths.append(t)

    parts = []
    for rel in paths:
        p = base_dir / rel
        if not p.exists():
            print(f"Warning: CSS template not found: {p}", file=sys.stderr)
            continue
        try:
            parts.append(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: could not read {p}: {e}", file=sys.stderr)

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def _extract_meta(html_path: Path) -> dict:
    """Return {file, title, ts} from a generated conversation HTML file."""
    text = html_path.read_text(encoding="utf-8")
    m_title = re.search(r"<h1>(.*?)</h1>", text)
    title = m_title.group(1) if m_title else html_path.stem.replace("-", " ").title()
    m_ts = re.search(r'data-started-ts="(\d+)"', text)
    ts = int(m_ts.group(1)) if m_ts else 0
    return {"file": html_path.name, "title": title, "ts": ts}


def scan_provider(output_dir: Path, provider: str) -> list[dict]:
    """Return sorted list of conversation metadata dicts for one provider."""
    provider_dir = output_dir / provider
    if not provider_dir.is_dir():
        return []
    metas = []
    for html_file in sorted(provider_dir.glob("*.html")):
        if html_file.name == "index.html":
            continue
        meta = _extract_meta(html_file)
        meta["provider"] = provider
        metas.append(meta)
    metas.sort(key=lambda m: m["ts"], reverse=True)
    return metas


# ---------------------------------------------------------------------------
# JS data builder
# ---------------------------------------------------------------------------

def _js_conv_list(convs: list[dict]) -> str:
    """Render a JS array literal from a list of conv dicts."""
    items = []
    for c in convs:
        title_esc = c["title"].replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
        items.append(
            f'  {{ file:"{c["file"]}", title:"{title_esc}", ts:{c["ts"]}, provider:"{c["provider"]}" }}'
        )
    return "[\n" + ",\n".join(items) + "\n]"


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chats</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    darkMode: 'class',
    theme: {
      extend: {
        colors: {
          surface: { 900:'#0c0e14', 800:'#111318', 700:'#16181f', 600:'#1c1f28', 500:'#232733' },
          accent:  { blue:'#4a90e2', green:'#4ade80', amber:'#f59e0b', muted:'#6b7280' }
        },
        fontFamily: {
          sans: ['-apple-system','BlinkMacSystemFont','"Segoe UI"','Roboto','sans-serif'],
          mono: ['"JetBrains Mono"','"Fira Code"','monospace'],
        }
      }
    }
  }
</script>
<style>
%%CSS%%
</style>
</head>
<body class="bg-[#0c0e14] text-gray-300 font-sans h-screen flex flex-col overflow-hidden">

<!-- Top bar -->
<header class="flex-none flex items-center gap-3 px-4 py-2.5 bg-[#111318] border-b border-gray-800/60 z-20">
  <button id="sidebar-toggle" class="md:hidden text-gray-500 hover:text-gray-300 p-1 rounded">
    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
    </svg>
  </button>

  <!-- Logo + menu trigger -->
  <div class="relative flex items-center gap-2">
    <button id="menu-trigger" class="flex items-center gap-2 rounded-md px-1 py-0.5 hover:bg-[#1c1f28] transition-colors">
      <div class="w-6 h-6 rounded-full bg-gradient-to-br from-violet-500 to-blue-400 flex items-center justify-center flex-none">
        <svg class="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 20 20">
          <path d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5z"/>
        </svg>
      </div>
      <span id="header-title" class="text-sm font-semibold text-gray-200 tracking-tight">Chat Export Viewer</span>
      <svg class="w-3 h-3 text-gray-600 ml-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
      </svg>
    </button>

    <!-- User menu -->
    <div id="user-menu" class="hidden">
      <!-- Provider filter -->
      %%PROVIDER_MENU_SECTION%%

      <!-- Sort controls -->
      <div class="menu-section">
        <div class="menu-section-title">Sort conversations</div>
        <div class="flex flex-wrap gap-1.5">
          <button class="sort-btn" data-sort="date-desc">Newest first</button>
          <button class="sort-btn" data-sort="date-asc">Oldest first</button>
          <button class="sort-btn" data-sort="alpha-asc">A \u2192 Z</button>
          <button class="sort-btn" data-sort="alpha-desc">Z \u2192 A</button>
        </div>
      </div>

      <!-- Display options -->
      <div class="menu-section">
        <div class="menu-section-title">Display</div>
        <div class="toggle-row">
          <label for="toggle-ts">Show timestamps</label>
          <label class="toggle-switch">
            <input type="checkbox" id="toggle-ts">
            <span class="toggle-track"></span>
          </label>
        </div>
      </div>

      <!-- Manage conversations -->
      <div class="menu-section">
        <div class="menu-section-title">Manage conversations</div>
        <div id="menu-file-list" class="space-y-px max-h-56 overflow-y-auto"></div>
      </div>
    </div>
  </div>

  <div class="flex-1 max-w-xs ml-auto">
    <div class="relative">
      <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11A6 6 0 105 11a6 6 0 0012 0z"/>
      </svg>
      <input id="search-input" type="text" placeholder="Search chats\u2026"
        class="w-full bg-[#1c1f28] border border-gray-800 rounded-md py-1.5 pl-8 pr-3 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-blue-700 focus:ring-1 focus:ring-blue-800">
    </div>
  </div>

  <span id="search-mode-badge">full-text</span>
  <div id="conv-count" class="text-xs text-gray-600 flex-none hidden md:block"></div>
</header>

<!-- Main layout -->
<div class="flex flex-1 overflow-hidden">
  <div id="sidebar-overlay"></div>

  <!-- Left sidebar -->
  <aside id="sidebar" class="w-64 bg-[#111318] border-r border-gray-800/60 flex flex-col overflow-hidden">
    <div class="flex-1 overflow-y-auto py-2" id="conv-list-container">
      <div class="px-3 py-1.5 mb-1">
        <span class="text-[.6rem] font-bold tracking-widest uppercase text-gray-600">Chats</span>
      </div>
      <ul id="conv-list" class="space-y-px px-1.5"></ul>
    </div>

    <div class="border-t border-gray-800/60 flex-none"></div>

    <div class="flex-none overflow-y-auto max-h-60 py-2" id="jump-nav-container" style="display:none">
      <div class="px-3 py-1.5 mb-1 flex items-center gap-1.5">
        <svg class="w-3 h-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8M4 18h4"/>
        </svg>
        <span id="jump-nav-label" class="text-[.6rem] font-bold tracking-widest uppercase text-gray-600">Jump to</span>
      </div>
      <ul id="jump-nav" class="space-y-px px-1.5"></ul>
    </div>
  </aside>

  <!-- Content area -->
  <main class="flex-1 overflow-y-auto" id="main-content">
    <div id="empty-state" class="flex flex-col items-center justify-center h-full gap-3 opacity-30">
      <svg class="w-12 h-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
      </svg>
      <p class="text-sm">Select a chat</p>
    </div>
    <div id="loading-state" class="flex items-center justify-center h-full gap-2 opacity-40" style="display:none!important">
      <div class="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      <span class="text-sm">Loading\u2026</span>
    </div>
    <div id="conv-content" class="max-w-3xl mx-auto px-6 py-8 fade-in" style="display:none"></div>
  </main>
</div>

<script>
// ─── Data ───────────────────────────────────────────────────────────────────
const ALL_CONVERSATIONS = %%ALL_CONVERSATIONS%%;

// ─── Persistence ────────────────────────────────────────────────────────────
const LS = {
  KEY_SCROLL:   'spa_scroll_positions',
  KEY_ACTIVE:   'spa_active_file',
  KEY_HIDDEN:   'spa_hidden_files',
  KEY_PREFS:    'spa_prefs',
  KEY_PROVIDER: 'spa_active_provider',

  getScrolls()  { try { return JSON.parse(localStorage.getItem(this.KEY_SCROLL)||'{}'); } catch{return {};} },
  saveScroll(file,pos){ try { const m=this.getScrolls(); m[file]=pos; localStorage.setItem(this.KEY_SCROLL,JSON.stringify(m)); } catch{} },
  getActiveFile(){ try { return localStorage.getItem(this.KEY_ACTIVE)||null; } catch{return null;} },
  saveActiveFile(f){ try { if(f) localStorage.setItem(this.KEY_ACTIVE,f); else localStorage.removeItem(this.KEY_ACTIVE); } catch{} },
  getHidden()   { try { return new Set(JSON.parse(localStorage.getItem(this.KEY_HIDDEN)||'[]')); } catch{return new Set();} },
  saveHidden(s) { try { localStorage.setItem(this.KEY_HIDDEN,JSON.stringify([...s])); } catch{} },
  getPrefs()    { try { return Object.assign({sort:'date-desc',showTs:false}, JSON.parse(localStorage.getItem(this.KEY_PREFS)||'{}')); } catch{return {sort:'date-desc',showTs:false};} },
  savePrefs(p)  { try { localStorage.setItem(this.KEY_PREFS,JSON.stringify(p)); } catch{} },
  getProvider() { return localStorage.getItem(this.KEY_PROVIDER)||'%%DEFAULT_PROVIDER%%'; },
  saveProvider(p){ try { localStorage.setItem(this.KEY_PROVIDER,p); } catch{} },
};

// ─── State ──────────────────────────────────────────────────────────────────
let hiddenFiles        = LS.getHidden();
let prefs              = LS.getPrefs();
let activeProvider     = LS.getProvider();
let CONVERSATIONS      = ALL_CONVERSATIONS.filter(c => !hiddenFiles.has(c.provider + ':' + c.file));
let activeIndex        = -1;
let filteredConvs      = [];
let currentSearchQuery = '';
let currentSearchHits  = null;
let isFullTextSearch   = false;

const loadedContent    = new Map();  // "provider:file" → { bodyHtml }
const contentTextCache = new Map();  // "provider:file" → plaintext
const persistedScrolls = LS.getScrolls();

// ─── DOM refs ───────────────────────────────────────────────────────────────
const convList         = document.getElementById('conv-list');
const jumpNav          = document.getElementById('jump-nav');
const jumpNavContainer = document.getElementById('jump-nav-container');
const jumpNavLabel     = document.getElementById('jump-nav-label');
const convContent      = document.getElementById('conv-content');
const emptyState       = document.getElementById('empty-state');
const loadingState     = document.getElementById('loading-state');
const searchInput      = document.getElementById('search-input');
const convCount        = document.getElementById('conv-count');
const sidebar          = document.getElementById('sidebar');
const sidebarOverlay   = document.getElementById('sidebar-overlay');
const sidebarToggle    = document.getElementById('sidebar-toggle');
const menuTrigger      = document.getElementById('menu-trigger');
const userMenu         = document.getElementById('user-menu');
const menuFileList     = document.getElementById('menu-file-list');
const searchModeBadge  = document.getElementById('search-mode-badge');
const mainContentEl    = document.getElementById('main-content');
const toggleTs         = document.getElementById('toggle-ts');

function fileKey(conv) { return conv.provider + ':' + conv.file; }
function pathFor(conv)  { return conv.provider + '/' + conv.file; }

const PROVIDER_LABELS = %%PROVIDER_LABELS%%;
const headerTitle = document.getElementById('header-title');

function updateHeaderTitle(p) {
  headerTitle.textContent = p === 'all' ? 'Chats' : (PROVIDER_LABELS[p] || p) + ' Chats';
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escapeRegex(s) { return s.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&'); }

function fmtTs(ts) {
  if (!ts) return '';
  return new Date(ts).toLocaleDateString('en-GB', {day:'2-digit',month:'short',year:'numeric'});
}

// ─── Provider filter ────────────────────────────────────────────────────────
function setProvider(p) {
  activeProvider = p;
  LS.saveProvider(p);
  updateHeaderTitle(p);
  document.querySelectorAll('.provider-filter-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.p === p));
  activeIndex = -1;
  filteredConvs = applyFilter(currentSearchQuery);
  renderList(currentSearchHits);
  const lastFile = LS.getActiveFile();
  if (lastFile) {
    const idx = filteredConvs.findIndex(c => fileKey(c) === lastFile);
    if (idx >= 0) { loadConversation(idx); return; }
  }
  convContent.style.display = 'none';
  emptyState.style.display = '';
  jumpNavContainer.style.display = 'none';
}

// ─── Sorting / filtering ────────────────────────────────────────────────────
function sortConversations(list) {
  const s = prefs.sort;
  return [...list].sort((a, b) => {
    if (s === 'date-desc') return (b.ts||0) - (a.ts||0);
    if (s === 'date-asc')  return (a.ts||0) - (b.ts||0);
    if (s === 'alpha-asc') return a.title.localeCompare(b.title);
    if (s === 'alpha-desc')return b.title.localeCompare(a.title);
    return 0;
  });
}

function getVisibleConvs() {
  const all = ALL_CONVERSATIONS.filter(c => !hiddenFiles.has(fileKey(c)));
  if (activeProvider === 'all') return all;
  return all.filter(c => c.provider === activeProvider);
}

function applyFilter(q) {
  const base = getVisibleConvs();
  if (!q) return sortConversations(base);
  const lq = q.toLowerCase();
  return sortConversations(base.filter(c => c.title.toLowerCase().includes(lq)));
}

// ─── Prefs ──────────────────────────────────────────────────────────────────
function applyPrefs() {
  toggleTs.checked = prefs.showTs;
  document.body.classList.toggle('show-ts', prefs.showTs);
  document.querySelectorAll('.sort-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.sort === prefs.sort));
}

toggleTs.addEventListener('change', () => {
  prefs.showTs = toggleTs.checked;
  document.body.classList.toggle('show-ts', prefs.showTs);
  LS.savePrefs(prefs);
  renderList(currentSearchHits);
});

document.querySelectorAll('.sort-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    prefs.sort = btn.dataset.sort;
    LS.savePrefs(prefs);
    document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('active', b.dataset.sort === prefs.sort));
    filteredConvs = applyFilter(currentSearchQuery);
    renderList(currentSearchHits);
  });
});

// ─── Sidebar list ───────────────────────────────────────────────────────────
function renderList(searchHits) {
  currentSearchHits = searchHits || null;
  convList.innerHTML = '';
  convCount.textContent = filteredConvs.length + ' of ' + getVisibleConvs().length;
  convCount.classList.remove('hidden');

  if (filteredConvs.length === 0) {
    convList.innerHTML = '<li class="px-3 py-2 text-xs text-gray-600">No matches</li>';
    return;
  }

  filteredConvs.forEach((conv, i) => {
    const isActive = i === activeIndex;
    const li = document.createElement('li');
    li.className = 'conv-item rounded-md px-2.5 py-2 cursor-pointer' + (isActive ? ' active' : '');
    li.dataset.idx = i;

    const short = conv.title.length > 36 ? conv.title.slice(0,34) + '\u2026' : conv.title;
    const hits   = searchHits && searchHits.has(i);
    const dateStr = fmtTs(conv.ts);
    const dot    = activeProvider === 'all'
      ? '<span class="provider-dot" data-p="' + conv.provider + '"></span>' : '';

    li.innerHTML =
      '<div class="flex items-center gap-1">' +
        dot +
        '<span class="block text-xs leading-snug text-gray-300 flex-1">' + escHtml(short) + '</span>' +
        (hits ? '<span class="text-[.58rem] text-amber-500 flex-none">' + searchHits.get(i).length + '\u00d7</span>' : '') +
        '<button class="remove-btn text-gray-700 hover:text-red-500 p-0.5 rounded" title="Remove" data-idx="' + i + '">' +
          '<svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>' +
          '</svg>' +
        '</button>' +
      '</div>' +
      '<div class="conv-date">' + dateStr + '</div>' +
      (hits ? '<div class="mt-0.5 space-y-0.5">' + searchHits.get(i).slice(0,2).map(s =>
        '<div class="text-[.6rem] text-amber-700/80 leading-snug line-clamp-1 pl-1 border-l border-amber-900">\u2026' + escHtml(s) + '\u2026</div>'
      ).join('') + '</div>' : '');

    li.setAttribute('title', conv.title);
    li.addEventListener('click', e => { if (e.target.closest('.remove-btn')) return; loadConversation(i); });
    li.querySelector('.remove-btn').addEventListener('click', e => { e.stopPropagation(); quickRemove(i); });
    convList.appendChild(li);
  });
}

// ─── Shared remove helper ────────────────────────────────────────────────────
function removeConversation(key, { rerenderMenu = false } = {}) {
  const idx = filteredConvs.findIndex(c => fileKey(c) === key);
  if (idx === activeIndex) {
    activeIndex = -1;
    convContent.style.display = 'none';
    emptyState.style.display = '';
    jumpNavContainer.style.display = 'none';
    LS.saveActiveFile(null);
  }
  hiddenFiles.add(key);
  LS.saveHidden(hiddenFiles);
  filteredConvs = applyFilter(currentSearchQuery);
  if (activeIndex > idx) activeIndex--;
  renderList(currentSearchHits);
  if (rerenderMenu) renderMenuFileList();
}

function quickRemove(idx) {
  const conv = filteredConvs[idx];
  if (!conv) return;
  removeConversation(fileKey(conv));
}

// ─── Menu file list ─────────────────────────────────────────────────────────
function renderMenuFileList() {
  menuFileList.innerHTML = '';
  const allConvs = activeProvider === 'all'
    ? ALL_CONVERSATIONS
    : ALL_CONVERSATIONS.filter(c => c.provider === activeProvider);

  allConvs.forEach(conv => {
    const key     = fileKey(conv);
    const visible = !hiddenFiles.has(key);
    const short   = conv.title.length > 36 ? conv.title.slice(0,34) + '\u2026' : conv.title;
    const dot     = '<span class="provider-dot" data-p="' + conv.provider + '" style="display:inline-block;margin-right:.25rem"></span>';
    const row = document.createElement('div');
    row.className = 'file-row';
    row.innerHTML =
      '<span class="file-name" title="' + escHtml(conv.title) + '">' + dot + escHtml(short) + '</span>' +
      (visible
        ? '<span class="file-status">\u2713</span><button class="file-action remove" data-key="' + key + '">Remove</button>'
        : '<button class="file-action add" data-key="' + key + '">Add</button>');
    menuFileList.appendChild(row);
  });

  menuFileList.querySelectorAll('.file-action.add').forEach(btn => {
    btn.addEventListener('click', () => {
      hiddenFiles.delete(btn.dataset.key);
      LS.saveHidden(hiddenFiles);
      filteredConvs = applyFilter(currentSearchQuery);
      renderList(currentSearchHits);
      renderMenuFileList();
    });
  });

  menuFileList.querySelectorAll('.file-action.remove').forEach(btn => {
    btn.addEventListener('click', () => {
      removeConversation(btn.dataset.key, { rerenderMenu: true });
    });
  });
}

// ─── Search ─────────────────────────────────────────────────────────────────
let searchDebounce = null;
searchInput.addEventListener('input', () => { clearTimeout(searchDebounce); searchDebounce = setTimeout(handleSearch, 180); });

async function handleSearch() {
  const q = searchInput.value.trim();
  currentSearchQuery = q;

  if (!q) {
    isFullTextSearch = false;
    searchModeBadge.classList.remove('active');
    filteredConvs = sortConversations(getVisibleConvs());
    renderList(null);
    clearContentHighlights();
    jumpNavLabel.textContent = 'Jump to';
    if (activeIndex >= 0) buildJumpNav();
    return;
  }

  const lq = q.toLowerCase();
  const titleMatchKeys = new Set(
    getVisibleConvs().filter(c => c.title.toLowerCase().includes(lq)).map(fileKey)
  );

  const searchHits = new Map();
  getVisibleConvs().forEach((conv, i) => {
    const key = fileKey(conv);
    let text = contentTextCache.get(key);
    if (text === undefined) {
      if (loadedContent.has(key)) {
        const tmp = document.createElement('div');
        tmp.innerHTML = loadedContent.get(key).bodyHtml;
        text = tmp.textContent || '';
        contentTextCache.set(key, text);
      } else { text = null; }
    }
    if (text && text.toLowerCase().includes(lq)) {
      const snippets = []; let idx2 = 0; const tl = text.toLowerCase();
      while (snippets.length < 3) {
        const pos = tl.indexOf(lq, idx2);
        if (pos === -1) break;
        snippets.push(text.slice(Math.max(0,pos-28), Math.min(text.length,pos+lq.length+28)).replace(/\\n+/g,' ').trim());
        idx2 = pos + lq.length;
      }
      searchHits.set(i, snippets);
    }
  });

  const allVisible = getVisibleConvs();
  const matchIdxs = new Set();
  allVisible.forEach((c, i) => {
    if (titleMatchKeys.has(fileKey(c)) || searchHits.has(i)) matchIdxs.add(i);
  });

  isFullTextSearch = [...matchIdxs].some(i => !titleMatchKeys.has(fileKey(allVisible[i])));
  filteredConvs = sortConversations(allVisible.filter((_, i) => matchIdxs.has(i)));
  searchModeBadge.classList.toggle('active', isFullTextSearch);

  // Remap searchHits keys to filteredConvs indices
  const remapped = new Map();
  filteredConvs.forEach((conv, fi) => {
    const oi = allVisible.indexOf(conv);
    if (searchHits.has(oi)) remapped.set(fi, searchHits.get(oi));
  });

  renderList(remapped.size > 0 ? remapped : null);
  if (activeIndex >= 0 && q) highlightContentMatches(q);
}

// ─── Highlight ───────────────────────────────────────────────────────────────
function highlightContentMatches(q) {
  if (!q || activeIndex < 0) return;
  clearContentHighlights();
  if (!q.trim()) return;
  const lq = q.toLowerCase();
  jumpNavLabel.textContent = 'Search hits';
  let matchCount = 0;
  walkTextNodes(convContent, node => {
    const text = node.textContent;
    if (!text.toLowerCase().includes(lq)) return;
    const parts = text.split(new RegExp('(' + escapeRegex(q) + ')', 'gi'));
    if (parts.length <= 1) return;
    const frag = document.createDocumentFragment();
    parts.forEach(part => {
      if (part.toLowerCase() === lq) {
        const mark = document.createElement('mark');
        mark.textContent = part; mark.dataset.matchIdx = matchCount++;
        frag.appendChild(mark);
      } else { frag.appendChild(document.createTextNode(part)); }
    });
    node.parentNode.replaceChild(frag, node);
  });
  buildJumpNavWithSearchHits(q);
}

function clearContentHighlights() {
  convContent.querySelectorAll('mark').forEach(m => {
    const p = m.parentNode;
    p.replaceChild(document.createTextNode(m.textContent), m);
    p.normalize();
  });
}

function walkTextNodes(el, fn) {
  if (['SCRIPT','STYLE','PRE','CODE'].includes(el.tagName)) return;
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const p = node.parentElement;
      if (!p) return NodeFilter.FILTER_REJECT;
      if (['SCRIPT','STYLE','PRE','CODE'].includes(p.tagName)) return NodeFilter.FILTER_REJECT;
      return node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    }
  });
  const nodes = []; let n;
  while ((n = walker.nextNode())) nodes.push(n);
  nodes.forEach(fn);
}

// ─── Jump nav ────────────────────────────────────────────────────────────────
function buildJumpNav() {
  jumpNav.innerHTML = '';
  jumpNavLabel.textContent = 'Jump to';
  const userMsgs = convContent.querySelectorAll('.message.user');
  const items = [];

  userMsgs.forEach((msg, i) => {
    const text = msg.textContent.trim().replace(/^YOU\\s*/i,'').slice(0,52);
    const label = text || ('Turn ' + (i+1));
    const id = 'jump-msg-' + i;
    msg.id = id;
    items.push({ id, label: label.length>50 ? label.slice(0,48)+'\u2026' : label });
  });

  convContent.querySelectorAll('.message.assistant h2, .message.assistant h3').forEach((h,i) => {
    const text = h.textContent.trim().slice(0,52);
    const id = 'jump-h-' + i; h.id = id;
    if (text.length > 3) items.push({ id, label: text.length>50?text.slice(0,48)+'\u2026':text, isHeading:true });
  });

  if (items.length === 0) return;
  items.forEach(item => {
    const li = document.createElement('li');
    li.innerHTML = '<a href="#' + item.id + '" class="jump-link block px-2.5 py-1 rounded truncate' + (item.isHeading?' pl-5 italic':'') + '" data-target="' + item.id + '" title="' + escHtml(item.label) + '">' + (item.isHeading?'\u21b3 ':'') + escHtml(item.label) + '</a>';
    li.querySelector('a').addEventListener('click', e => { e.preventDefault(); scrollToTarget(item.id, li.querySelector('a')); });
    jumpNav.appendChild(li);
  });
  jumpNavContainer.style.display = 'block';
  attachScrollObserver();
}

function buildJumpNavWithSearchHits(q) {
  jumpNav.innerHTML = '';
  jumpNavLabel.textContent = 'Search hits';
  const userMsgs = convContent.querySelectorAll('.message.user');
  userMsgs.forEach((msg,i) => { msg.id = 'jump-msg-' + i; });
  const assistantMsgs = convContent.querySelectorAll('.message.assistant');
  assistantMsgs.forEach((msg,i) => { if (!msg.id) msg.id = 'jump-asst-' + i; });

  convContent.querySelectorAll('.message').forEach((msg,i) => {
    const marks = msg.querySelectorAll('mark');
    if (marks.length === 0) return;
    const msgId = msg.id || ('jump-m-' + i); msg.id = msgId;
    const labelEl = msg.querySelector('.role-label');
    const rawText = (labelEl ? msg.textContent.replace(labelEl.textContent,'') : msg.textContent).trim().replace(/\\n+/g,' ');
    const label = rawText.slice(0,46) + (rawText.length>46?'\u2026':'');
    const li = document.createElement('li');
    li.innerHTML = '<a href="#' + msgId + '" class="jump-link search-hit block px-2.5 py-1 rounded truncate" data-target="' + msgId + '" title="' + escHtml(label) + '"><span class="text-[.58rem] text-amber-600 mr-0.5">' + marks.length + '\u00d7</span>' + escHtml(label) + '</a>';
    li.querySelector('a').addEventListener('click', e => {
      e.preventDefault(); scrollToTarget(msgId, li.querySelector('a'));
      const fm = msg.querySelector('mark');
      if (fm) { fm.classList.add('search-active'); setTimeout(()=>fm.classList.remove('search-active'),1400); }
    });
    jumpNav.appendChild(li);
  });
  if (jumpNav.children.length > 0) jumpNavContainer.style.display = 'block';
}

function scrollToTarget(id, linkEl) {
  const target = document.getElementById(id);
  if (target) {
    target.scrollIntoView({ behavior:'smooth', block:'start' });
    target.style.outline = '1px solid #4a90e240';
    setTimeout(() => target.style.outline='', 1200);
    jumpNav.querySelectorAll('.jump-link').forEach(a => a.classList.remove('active-heading'));
    if (linkEl) linkEl.classList.add('active-heading');
  }
}

function attachScrollObserver() {
  const allTargets = [...convContent.querySelectorAll('[id^="jump-"]')];
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        jumpNav.querySelectorAll('.jump-link').forEach(a => a.classList.toggle('active-heading', a.dataset.target === id));
      }
    });
  }, { root: mainContentEl, threshold: 0.1, rootMargin: '-10% 0px -80% 0px' });
  allTargets.forEach(el => observer.observe(el));
}

// ─── Load conversation ───────────────────────────────────────────────────────
async function loadConversation(idx) {
  if (idx === activeIndex) return;

  if (activeIndex !== -1 && filteredConvs[activeIndex]) {
    LS.saveScroll(fileKey(filteredConvs[activeIndex]), mainContentEl.scrollTop);
    persistedScrolls[fileKey(filteredConvs[activeIndex])] = mainContentEl.scrollTop;
  }

  const prevIndex = activeIndex;
  activeIndex = idx;
  const conv = filteredConvs[idx];
  if (!conv) return;
  const key = fileKey(conv);
  LS.saveActiveFile(key);

  sidebar.classList.remove('open'); sidebarOverlay.classList.remove('active');
  renderList(currentSearchHits);

  // Set provider class on content area for CSS accent colours
  convContent.className = 'provider-' + conv.provider + ' max-w-3xl mx-auto px-6 py-8 fade-in';

  // Fast path
  if (loadedContent.has(key)) {
    const cached = loadedContent.get(key);
    emptyState.style.display = 'none'; loadingState.style.display = 'none';
    convContent.innerHTML = cached.bodyHtml; convContent.style.display = 'block';
    convContent.classList.remove('fade-in'); void convContent.offsetWidth; convContent.classList.add('fade-in');
    buildJumpNav();
    const saved = persistedScrolls[key];
    mainContentEl.scrollTop = saved !== undefined ? saved : 0;
    if (currentSearchQuery) highlightContentMatches(currentSearchQuery);
    return;
  }

  // Slow path
  if (prevIndex === -1) {
    emptyState.style.display = 'none';
    loadingState.style.removeProperty('display');
    convContent.style.display = 'none';
  }
  jumpNavContainer.style.display = 'none'; jumpNav.innerHTML = '';

  try {
    const res = await fetch(pathFor(conv));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const html = await res.text();

    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const container = doc.querySelector('.container');
    const bodyHtml = container ? container.innerHTML : doc.body.innerHTML;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = bodyHtml;

    // Convert .thinking blocks to collapsible <details>
    tempDiv.querySelectorAll('.thinking').forEach(el => {
      const label = el.querySelector('.thinking-label');
      const labelText = label ? label.textContent : 'Thinking';
      const contentHtml = label ? el.innerHTML.replace(label.outerHTML,'') : el.innerHTML;
      const details = document.createElement('details');
      details.className = 'thinking-toggle';
      details.innerHTML =
        '<summary class="flex items-center gap-1.5 cursor-pointer select-none mb-1">' +
          '<span class="thinking-label">' + labelText + '</span>' +
          '<svg class="w-3 h-3" style="color:#4a4a28" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>' +
          '</svg>' +
        '</summary>' +
        '<div class="thinking-body" style="font-style:italic;color:#6b7040;font-size:.84rem;line-height:1.7">' + contentHtml + '</div>';
      el.replaceWith(details);
    });

    loadedContent.set(key, { bodyHtml: tempDiv.innerHTML });
    contentTextCache.set(key, tempDiv.textContent || '');

    if (activeIndex !== idx) return;

    loadingState.style.display = 'none';
    convContent.innerHTML = tempDiv.innerHTML; convContent.style.display = 'block';
    emptyState.style.display = 'none';
    convContent.classList.remove('fade-in'); void convContent.offsetWidth; convContent.classList.add('fade-in');
    buildJumpNav();
    mainContentEl.scrollTop = 0;
    if (currentSearchQuery) { highlightContentMatches(currentSearchQuery); handleSearch(); }

  } catch (err) {
    if (activeIndex !== idx) return;
    loadingState.style.display = 'none';
    convContent.innerHTML = '<div class="text-red-400 text-sm p-4 bg-red-950/30 rounded-lg border border-red-900/40">Failed to load: ' + escHtml(err.message) + '<br><span class="text-gray-500 text-xs">Serve via <code>python3 -m http.server</code></span></div>';
    convContent.style.display = 'block'; emptyState.style.display = 'none';
  }
}

// ─── Mobile sidebar ─────────────────────────────────────────────────────────
sidebarToggle.addEventListener('click', () => { sidebar.classList.toggle('open'); sidebarOverlay.classList.toggle('active'); });
sidebarOverlay.addEventListener('click', () => { sidebar.classList.remove('open'); sidebarOverlay.classList.remove('active'); });

// ─── User menu ───────────────────────────────────────────────────────────────
menuTrigger.addEventListener('click', e => {
  e.stopPropagation();
  userMenu.classList.toggle('hidden');
  if (!userMenu.classList.contains('hidden')) renderMenuFileList();
});
document.addEventListener('click', e => {
  if (!userMenu.contains(e.target) && e.target !== menuTrigger) userMenu.classList.add('hidden');
});

// Provider filter buttons
document.querySelectorAll('.provider-filter-btn').forEach(btn => {
  btn.addEventListener('click', () => setProvider(btn.dataset.p));
});

// ─── Scroll persistence ──────────────────────────────────────────────────────
window.addEventListener('beforeunload', () => {
  if (activeIndex >= 0 && filteredConvs[activeIndex])
    LS.saveScroll(fileKey(filteredConvs[activeIndex]), mainContentEl.scrollTop);
});
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden' && activeIndex >= 0 && filteredConvs[activeIndex])
    LS.saveScroll(fileKey(filteredConvs[activeIndex]), mainContentEl.scrollTop);
});

// ─── Init ────────────────────────────────────────────────────────────────────
applyPrefs();
updateHeaderTitle(activeProvider);
document.querySelectorAll('.provider-filter-btn').forEach(b =>
  b.classList.toggle('active', b.dataset.p === activeProvider));
filteredConvs = sortConversations(getVisibleConvs());
renderList(null);

const lastFile = LS.getActiveFile();
if (lastFile) {
  const lastIdx = filteredConvs.findIndex(c => fileKey(c) === lastFile);
  if (lastIdx >= 0) {
    loadConversation(lastIdx).then(() => {
      const saved = persistedScrolls[lastFile];
      if (saved) setTimeout(() => { mainContentEl.scrollTop = saved; }, 80);
    });
  }
}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_spa(
    output_dir: Path,
    config_path: Path | None = None,
    providers: list[str] | None = None,
) -> str:
    """
    Build the SPA HTML string.

    Args:
        output_dir:  root output directory (contains provider subdirs)
        config_path: path to spa.toml; defaults to output_dir/../../config/spa.toml
        providers:   list of providers to include; defaults to all with HTML files
    """
    # Resolve config
    if config_path is None:
        config_path = output_dir.parent / "config" / "spa.toml"
        if not config_path.exists():
            # Try sibling config/ (when output_dir is inside the project)
            config_path = Path(__file__).parent.parent / "config" / "spa.toml"

    config   = load_config(config_path)
    base_dir = Path(__file__).parent.parent  # project root

    if providers is None:
        providers = [p for p in PROVIDERS if (output_dir / p).is_dir()
                     and any(f for f in (output_dir / p).glob("*.html") if f.name != "index.html")]

    # Collect conversations per provider
    all_convs       = []
    found_providers = []
    for p in providers:
        convs = scan_provider(output_dir, p)
        if convs:
            all_convs.extend(convs)
            found_providers.append(p)

    if not all_convs:
        raise ValueError(
            f"No HTML conversations found in {output_dir} for providers: {providers}"
        )

    default_provider = found_providers[0] if len(found_providers) == 1 else "all"

    # Build provider filter section for settings menu
    if len(found_providers) > 1:
        btns = []
        for p in found_providers:
            label = config["providers"].get(p, {}).get("label") or PROVIDER_LABELS.get(p, p.title())
            btns.append(f'          <button class="provider-filter-btn" data-p="{p}">{label}</button>')
        btns.append(f'          <button class="provider-filter-btn" data-p="all">All</button>')
        provider_section = (
            '      <div class="menu-section">\n'
            '        <div class="menu-section-title">Provider</div>\n'
            '        <div class="flex flex-wrap gap-1.5">\n'
            + "\n".join(btns) + "\n"
            "        </div>\n"
            "      </div>\n"
        )
    else:
        provider_section = ""  # Single provider — no filter needed

    # Load CSS from templates
    css = load_css_templates(config, base_dir)

    js_data = _js_conv_list(all_convs)

    # Build JS provider labels object: { deepseek: "DeepSeek", claude: "Claude", ... }
    label_pairs = []
    for p in found_providers:
        label = config["providers"].get(p, {}).get("label") or PROVIDER_LABELS.get(p, p.title())
        label_pairs.append(f'"{p}":"{label}"')
    js_provider_labels = "{" + ",".join(label_pairs) + "}"

    html = _HTML_TEMPLATE
    html = html.replace("%%CSS%%", css)
    html = html.replace("%%PROVIDER_MENU_SECTION%%", provider_section)
    html = html.replace("%%ALL_CONVERSATIONS%%", js_data)
    html = html.replace("%%DEFAULT_PROVIDER%%", default_provider)
    html = html.replace("%%PROVIDER_LABELS%%", js_provider_labels)

    return html

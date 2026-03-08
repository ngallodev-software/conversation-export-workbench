"""
SPA (index.html) generator for the conversation viewer.

Scans output/<provider>/ directories, extracts title/timestamp metadata
from the generated HTML files, and writes output/index.html.
"""

import re
from pathlib import Path


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
        meta = _extract_meta(html_file)
        meta["provider"] = provider
        metas.append(meta)
    # Sort newest first by default
    metas.sort(key=lambda m: m["ts"], reverse=True)
    return metas


# ---------------------------------------------------------------------------
# SPA template (inline JS handles all interactivity)
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


SPA_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Conversations</title>
<style>
:root {
  --bg:        #0a0c10;
  --sidebar:   #0e1118;
  --border:    #1a1f2a;
  --text:      #c8cdd8;
  --text-dim:  #4a5060;
  --text-mid:  #788090;
  --accent-ds: #4a90e2;
  --accent-cl: #c57d3d;
  --accent-all:#7c5cbf;
  --active-bg: #141828;
  --hover-bg:  #111520;
  --radius:    8px;
}
* { box-sizing:border-box; margin:0; padding:0; }
html,body { height:100%; overflow:hidden; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }

/* ── Layout ── */
#app { display:flex; height:100vh; }
#sidebar { width:270px; min-width:220px; max-width:340px; display:flex; flex-direction:column; background:var(--sidebar); border-right:1px solid var(--border); flex-shrink:0; }
#main { flex:1; overflow:hidden; display:flex; flex-direction:column; }
#conv-content { flex:1; overflow-y:auto; padding:2rem 2.5rem; }
#conv-content .container { max-width:860px; margin:0 auto; }

/* ── Header ── */
#header { padding:.8rem 1rem .6rem; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; gap:.5rem; flex-shrink:0; }
#header-title { font-size:.78rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--text-mid); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1; }
#menu-btn { background:none; border:none; cursor:pointer; color:var(--text-mid); padding:.15rem .3rem; border-radius:4px; font-size:.95rem; line-height:1; flex-shrink:0; }
#menu-btn:hover { color:var(--text); background:var(--hover-bg); }
#header-wrap { position:relative; }

/* ── Provider tabs ── */
#provider-tabs { display:flex; border-bottom:1px solid var(--border); flex-shrink:0; }
.tab-btn { flex:1; padding:.45rem .3rem; font-size:.65rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; background:none; border:none; cursor:pointer; color:var(--text-dim); border-bottom:2px solid transparent; transition:color .15s,border-color .15s; }
.tab-btn:hover { color:var(--text-mid); }
.tab-btn.active[data-p="deepseek"] { color:var(--accent-ds); border-bottom-color:var(--accent-ds); }
.tab-btn.active[data-p="claude"]   { color:var(--accent-cl); border-bottom-color:var(--accent-cl); }
.tab-btn.active[data-p="all"]      { color:var(--accent-all); border-bottom-color:var(--accent-all); }

/* ── Search ── */
#search-wrap { padding:.55rem .8rem; border-bottom:1px solid var(--border); flex-shrink:0; }
#search { width:100%; background:#111520; border:1px solid var(--border); border-radius:var(--radius); padding:.35rem .7rem; font-size:.78rem; color:var(--text); outline:none; }
#search::placeholder { color:var(--text-dim); }
#search:focus { border-color:#2a3a5a; }

/* ── Conversation list ── */
#conv-list { flex:1; overflow-y:auto; padding:.4rem 0; }
.conv-item { padding:.5rem .9rem; cursor:pointer; border-radius:6px; margin:.1rem .4rem; transition:background .12s; }
.conv-item:hover { background:var(--hover-bg); }
.conv-item.active { background:var(--active-bg); }
.conv-name { font-size:.8rem; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:flex; align-items:center; gap:.4rem; }
.provider-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }
.provider-dot[data-p="deepseek"] { background:var(--accent-ds); }
.provider-dot[data-p="claude"]   { background:var(--accent-cl); }
.conv-date { font-size:.58rem; color:var(--text-dim); margin-top:.15rem; display:none; }
body.show-ts .conv-date { display:block; }
.search-snippet { font-size:.67rem; color:var(--text-mid); margin-top:.2rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* ── Jump nav ── */
#jump-nav { width:200px; min-width:160px; max-width:220px; overflow-y:auto; padding:.8rem .5rem; border-left:1px solid var(--border); font-size:.7rem; flex-shrink:0; }
#jump-nav a { display:block; padding:.28rem .5rem; color:var(--text-dim); text-decoration:none; border-radius:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:.1rem; transition:background .1s,color .1s; }
#jump-nav a:hover { color:var(--text); background:var(--hover-bg); }
#jump-nav a.active { color:var(--text); background:var(--active-bg); }
#jump-nav a .hit-count { font-size:.6rem; color:#5a9fc0; margin-left:.3rem; }
#main-row { display:flex; flex:1; overflow:hidden; }

/* ── Loading overlay ── */
#loading-overlay { display:none; position:absolute; top:0; left:0; right:0; bottom:0; background:rgba(10,12,16,.6); align-items:center; justify-content:center; z-index:10; pointer-events:none; }
#loading-overlay.visible { display:flex; }
#main { position:relative; }
.spinner { width:24px; height:24px; border:2px solid var(--border); border-top-color:var(--accent-ds); border-radius:50%; animation:spin .7s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }

/* ── User menu ── */
#user-menu { position:absolute; top:calc(100% + 6px); right:0; width:230px; background:#111520; border:1px solid var(--border); border-radius:var(--radius); box-shadow:0 8px 24px rgba(0,0,0,.5); z-index:100; padding:.5rem 0; }
#user-menu.hidden { display:none; }
.menu-section { padding:.4rem .8rem; border-bottom:1px solid var(--border); }
.menu-section:last-child { border-bottom:none; }
.menu-section-title { font-size:.6rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--text-dim); margin-bottom:.45rem; }
.sort-btn { display:block; width:100%; text-align:left; padding:.3rem .5rem; font-size:.72rem; color:var(--text-mid); background:none; border:1px solid transparent; border-radius:4px; cursor:pointer; margin-bottom:.2rem; }
.sort-btn:hover { background:var(--hover-bg); color:var(--text); }
.sort-btn.active { color:var(--accent-ds); border-color:#1a3a5a; background:#0d1a2a; }
.toggle-row { display:flex; align-items:center; justify-content:space-between; padding:.2rem 0; }
.toggle-label { font-size:.72rem; color:var(--text-mid); }
.toggle-switch { position:relative; width:28px; height:15px; flex-shrink:0; }
.toggle-switch input { opacity:0; width:0; height:0; position:absolute; }
.toggle-track { position:absolute; inset:0; background:#1f2937; border-radius:99px; cursor:pointer; transition:background .2s; }
.toggle-track::after { content:""; position:absolute; width:11px; height:11px; background:#fff; border-radius:50%; top:2px; left:2px; transition:transform .2s; }
.toggle-switch input:checked + .toggle-track { background:var(--accent-ds); }
.toggle-switch input:checked + .toggle-track::after { transform:translateX(13px); }
#menu-file-list { max-height:180px; overflow-y:auto; margin-top:.3rem; }
.menu-file-row { display:flex; align-items:center; gap:.5rem; padding:.2rem 0; font-size:.72rem; color:var(--text-mid); cursor:pointer; }
.menu-file-row:hover { color:var(--text); }
.menu-file-row input[type=checkbox] { accent-color:var(--accent-ds); flex-shrink:0; }

/* ── Content timestamps ── */
#conv-content .msg-time { display:none; }
body.show-ts #conv-content .msg-time { display:inline; }

/* ── Search highlights ── */
mark { background:#3a5a20; color:#c0e080; border-radius:2px; padding:0 1px; }
mark.search-active { background:#5a8a30; outline:2px solid #8ac050; }

/* ── Fade transition ── */
#conv-content { transition:opacity .12s ease; }
#conv-content.fading { opacity:0; }

/* ── Responsive ── */
@media(max-width:900px) { #jump-nav { display:none; } }
@media(max-width:600px) { #sidebar { width:200px; } }
</style>
</head>
<body>
<div id="app">
  <!-- Sidebar -->
  <div id="sidebar">
    <div id="header-wrap">
      <div id="header">
        <span id="header-title">Conversations</span>
        <button id="menu-btn" title="Options">⚙</button>
      </div>
      <div id="user-menu" class="hidden">
        <div class="menu-section">
          <div class="menu-section-title">Sort</div>
          <button class="sort-btn" data-sort="date-desc">Newest first</button>
          <button class="sort-btn" data-sort="date-asc">Oldest first</button>
          <button class="sort-btn" data-sort="alpha-asc">A → Z</button>
          <button class="sort-btn" data-sort="alpha-desc">Z → A</button>
        </div>
        <div class="menu-section">
          <div class="menu-section-title">Display</div>
          <div class="toggle-row">
            <span class="toggle-label">Show timestamps</span>
            <label class="toggle-switch">
              <input type="checkbox" id="toggle-ts">
              <span class="toggle-track"></span>
            </label>
          </div>
        </div>
        <div class="menu-section">
          <div class="menu-section-title">Conversations</div>
          <div id="menu-file-list"></div>
        </div>
      </div>
    </div>
    <div id="provider-tabs">%%PROVIDER_TABS%%</div>
    <div id="search-wrap">
      <input id="search" type="search" placeholder="Search…" autocomplete="off" spellcheck="false">
    </div>
    <div id="conv-list"></div>
  </div>

  <!-- Main -->
  <div id="main">
    <div id="loading-overlay"><div class="spinner"></div></div>
    <div id="main-row">
      <div id="conv-content"><p style="color:#4a5060;padding:3rem 0;text-align:center;">Select a conversation</p></div>
      <div id="jump-nav"></div>
    </div>
  </div>
</div>

<script>
// ─── Data ───────────────────────────────────────────────────────────────────
const ALL_CONVERSATIONS = %%ALL_CONVERSATIONS%%;

// ─── LocalStorage ───────────────────────────────────────────────────────────
const LS = {
  KEY_SCROLL:    'ds_scroll_positions',
  KEY_ACTIVE:    'ds_active_file',
  KEY_HIDDEN:    'ds_hidden_files',
  KEY_PREFS:     'ds_prefs',
  KEY_PROVIDER:  'ds_active_provider',
  getScrolls()  { try { return new Map(Object.entries(JSON.parse(localStorage.getItem(this.KEY_SCROLL)||'{}')));} catch{return new Map();} },
  saveScroll(file,pos) { try { const m=this.getScrolls(); m.set(file,pos); localStorage.setItem(this.KEY_SCROLL,JSON.stringify(Object.fromEntries(m))); } catch{} },
  getActiveFile(){ return localStorage.getItem(this.KEY_ACTIVE)||null; },
  saveActiveFile(f){ try{localStorage.setItem(this.KEY_ACTIVE,f);}catch{} },
  getHidden()   { try { return new Set(JSON.parse(localStorage.getItem(this.KEY_HIDDEN)||'[]'));} catch{return new Set();} },
  saveHidden(s) { try { localStorage.setItem(this.KEY_HIDDEN,JSON.stringify([...s]));} catch{} },
  getPrefs()    { try { return Object.assign({sort:'date-desc',showTs:false}, JSON.parse(localStorage.getItem(this.KEY_PREFS)||'{}')); } catch{return {sort:'date-desc',showTs:false};} },
  savePrefs(p)  { try { localStorage.setItem(this.KEY_PREFS,JSON.stringify(p)); } catch{} },
  getProvider() { return localStorage.getItem(this.KEY_PROVIDER)||'%%DEFAULT_PROVIDER%%'; },
  saveProvider(p){ try{localStorage.setItem(this.KEY_PROVIDER,p);}catch{} },
};

// ─── State ───────────────────────────────────────────────────────────────────
let hiddenFiles        = LS.getHidden();
let prefs              = LS.getPrefs();
let activeProvider     = LS.getProvider();
let activeIndex        = -1;                   // index in filteredConvs
let filteredConvs      = [];
let currentSearchQuery = '';
let currentSearchHits  = null;
const loadedContent    = new Map();            // file → { bodyHtml }
const contentTextCache = new Map();            // file → plaintext
const persistedScrolls = LS.getScrolls();

// ─── DOM refs ────────────────────────────────────────────────────────────────
const convListEl    = document.getElementById('conv-list');
const mainContentEl = document.getElementById('conv-content');
const jumpNavEl     = document.getElementById('jump-nav');
const searchEl      = document.getElementById('search');
const loadingEl     = document.getElementById('loading-overlay');
const menuBtn       = document.getElementById('menu-btn');
const userMenu      = document.getElementById('user-menu');
const toggleTs      = document.getElementById('toggle-ts');
const menuFileList  = document.getElementById('menu-file-list');
const providerTabs  = document.querySelectorAll('.tab-btn');

// ─── Helpers ─────────────────────────────────────────────────────────────────
function fmtTs(ms) {
  if (!ms) return '';
  const d = new Date(ms);
  return d.toLocaleDateString(undefined, {year:'numeric',month:'short',day:'numeric'});
}

function getActiveConvs() {
  const all = ALL_CONVERSATIONS.filter(c => !hiddenFiles.has(c.provider + ':' + c.file));
  if (activeProvider === 'all') return all;
  return all.filter(c => c.provider === activeProvider);
}

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

function applyPrefs() {
  toggleTs.checked = prefs.showTs;
  document.body.classList.toggle('show-ts', prefs.showTs);
  document.querySelectorAll('.sort-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.sort === prefs.sort);
  });
}

function fileKey(conv) {
  return conv.provider + ':' + conv.file;
}

function pathFor(conv) {
  return conv.provider + '/' + conv.file;
}

// ─── Provider tabs ───────────────────────────────────────────────────────────
function setProvider(p) {
  activeProvider = p;
  LS.saveProvider(p);
  providerTabs.forEach(t => t.classList.toggle('active', t.dataset.p === p));
  activeIndex = -1;
  renderList();
  // Restore last active file for this provider
  const lastFile = LS.getActiveFile();
  if (lastFile) {
    const idx = filteredConvs.findIndex(c => fileKey(c) === lastFile || c.file === lastFile);
    if (idx >= 0) { loadConversation(idx); return; }
  }
  mainContentEl.innerHTML = '<p style="color:#4a5060;padding:3rem 0;text-align:center;">Select a conversation</p>';
  jumpNavEl.innerHTML = '';
}

// ─── List rendering ──────────────────────────────────────────────────────────
function renderList() {
  const q = currentSearchQuery.trim().toLowerCase();
  const base = sortConversations(getActiveConvs());

  if (q) {
    filteredConvs = base.filter(c => {
      if (c.title.toLowerCase().includes(q)) return true;
      const key = fileKey(c);
      if (contentTextCache.has(key)) {
        return contentTextCache.get(key).toLowerCase().includes(q);
      }
      return false;
    });
  } else {
    filteredConvs = base;
  }

  convListEl.innerHTML = filteredConvs.map((c, i) => {
    const isActive = i === activeIndex;
    const snippet  = (currentSearchHits && currentSearchHits.get(i)) || '';
    const dot      = activeProvider === 'all'
      ? `<span class="provider-dot" data-p="${c.provider}"></span>` : '';
    return `<div class="conv-item${isActive?' active':''}" data-idx="${i}">
      <div class="conv-name">${dot}${escHtml(c.title)}</div>
      ${prefs.showTs && c.ts ? `<div class="conv-date">${fmtTs(c.ts)}</div>` : ''}
      ${snippet ? `<div class="search-snippet">${snippet}</div>` : ''}
    </div>`;
  }).join('');

  convListEl.querySelectorAll('.conv-item').forEach(el => {
    el.addEventListener('click', () => loadConversation(+el.dataset.idx));
  });
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Load conversation ────────────────────────────────────────────────────────
async function loadConversation(idx) {
  if (idx === activeIndex) return;

  const conv = filteredConvs[idx];
  if (!conv) return;

  // Save scroll for current conversation
  if (activeIndex >= 0 && filteredConvs[activeIndex]) {
    persistedScrolls.set(fileKey(filteredConvs[activeIndex]), mainContentEl.scrollTop);
  }

  const prevIndex = activeIndex;
  activeIndex = idx;
  LS.saveActiveFile(fileKey(conv));

  // Update active state in list
  convListEl.querySelectorAll('.conv-item').forEach((el, i) => {
    el.classList.toggle('active', i === idx);
  });

  const key = fileKey(conv);

  // Fast path: already cached
  if (loadedContent.has(key)) {
    const { bodyHtml } = loadedContent.get(key);
    mainContentEl.innerHTML = bodyHtml;
    const savedPos = persistedScrolls.get(key) ?? 0;
    mainContentEl.scrollTop = savedPos;
    buildJumpNav();
    if (currentSearchQuery) {
      highlightContentMatches(currentSearchQuery);
    }
    return;
  }

  // Slow path: fetch
  // Show spinner overlay; keep existing content visible underneath
  if (prevIndex === -1) {
    mainContentEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#4a5060;">Loading…</div>';
  }
  loadingEl.classList.add('visible');

  try {
    const resp = await fetch(pathFor(conv));
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const html = await resp.text();

    // Guard: user clicked away during fetch
    if (activeIndex !== idx) return;

    const doc = new DOMParser().parseFromString(html, 'text/html');
    const container = doc.querySelector('.container');
    const bodyHtml = container ? container.innerHTML : html;

    loadedContent.set(key, { bodyHtml });
    // Cache plaintext for search
    contentTextCache.set(key, container ? container.textContent : doc.body.textContent);

    mainContentEl.innerHTML = bodyHtml;
    mainContentEl.scrollTop = 0;
    buildJumpNav();
    if (currentSearchQuery) {
      highlightContentMatches(currentSearchQuery);
      handleSearch();  // update hit counts now this conv is loaded
    }
  } catch (e) {
    if (activeIndex === idx) {
      mainContentEl.innerHTML = `<p style="color:#e05050;padding:2rem">Failed to load: ${escHtml(e.message)}</p>`;
    }
  } finally {
    if (activeIndex === idx) loadingEl.classList.remove('visible');
  }
}

// ─── Jump nav ────────────────────────────────────────────────────────────────
function buildJumpNav() {
  const headings = mainContentEl.querySelectorAll('.message');
  if (!headings.length) { jumpNavEl.innerHTML = ''; return; }

  jumpNavEl.innerHTML = [...headings].map((el, i) => {
    const label = el.querySelector('.role-label');
    const text  = label ? label.textContent.split('\n')[0].trim().slice(0,40) : `#${i+1}`;
    return `<a href="#" data-idx="${i}">${escHtml(text)}</a>`;
  }).join('');

  jumpNavEl.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const el = mainContentEl.querySelectorAll('.message')[+a.dataset.idx];
      if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
    });
  });

  // IntersectionObserver for active highlight
  const links = jumpNavEl.querySelectorAll('a');
  const msgs  = mainContentEl.querySelectorAll('.message');
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const i = [...msgs].indexOf(entry.target);
        links.forEach((l, li) => l.classList.toggle('active', li === i));
      }
    });
  }, { root: mainContentEl, threshold: 0.1 });
  msgs.forEach(m => obs.observe(m));
}

function buildJumpNavWithSearchHits(q) {
  const ql = q.toLowerCase();
  const msgs  = [...mainContentEl.querySelectorAll('.message')];
  const links = [...jumpNavEl.querySelectorAll('a')];
  links.forEach((a, i) => {
    const marks = msgs[i] ? msgs[i].querySelectorAll('mark').length : 0;
    const existing = a.querySelector('.hit-count');
    if (existing) existing.remove();
    if (marks > 0) {
      const span = document.createElement('span');
      span.className = 'hit-count';
      span.textContent = `×${marks}`;
      a.appendChild(span);
    }
  });
}

// ─── Search ──────────────────────────────────────────────────────────────────
function clearContentHighlights() {
  mainContentEl.querySelectorAll('mark').forEach(m => {
    const parent = m.parentNode;
    parent.replaceChild(document.createTextNode(m.textContent), m);
    parent.normalize();
  });
}

function highlightContentMatches(q) {
  clearContentHighlights();
  if (!q) return;
  const ql = q.toLowerCase();
  const walker = document.createTreeWalker(mainContentEl, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let n;
  while ((n = walker.nextNode())) nodes.push(n);

  nodes.forEach(node => {
    const text = node.textContent;
    const idx  = text.toLowerCase().indexOf(ql);
    if (idx < 0) return;
    const before = text.slice(0, idx);
    const match  = text.slice(idx, idx + q.length);
    const after  = text.slice(idx + q.length);
    const mark   = document.createElement('mark');
    mark.textContent = match;
    const frag = document.createDocumentFragment();
    if (before) frag.appendChild(document.createTextNode(before));
    frag.appendChild(mark);
    if (after) frag.appendChild(document.createTextNode(after));
    node.parentNode.replaceChild(frag, node);
  });

  buildJumpNavWithSearchHits(q);
}

async function handleSearch() {
  const q = searchEl.value.trim().toLowerCase();
  currentSearchQuery = q;
  currentSearchHits  = null;

  if (!q) { renderList(); clearContentHighlights(); buildJumpNav(); return; }

  // Build hit map for sidebar snippets
  const hits = new Map();
  filteredConvs.forEach((c, i) => {
    const key = fileKey(c);
    if (contentTextCache.has(key)) {
      const text = contentTextCache.get(key).toLowerCase();
      const pos  = text.indexOf(q);
      if (pos >= 0) {
        const raw  = contentTextCache.get(key);
        const snip = raw.slice(Math.max(0, pos - 20), pos + 80).replace(/\s+/g, ' ');
        hits.set(i, `…${escHtml(snip)}…`);
      }
    }
  });
  currentSearchHits = hits;
  renderList();

  // Highlight current conversation
  if (activeIndex >= 0) highlightContentMatches(q);
}

// ─── User menu ────────────────────────────────────────────────────────────────
function buildMenuFileList() {
  const all = ALL_CONVERSATIONS;
  menuFileList.innerHTML = all.map(c => {
    const key     = fileKey(c);
    const checked = !hiddenFiles.has(key) ? 'checked' : '';
    const dot     = `<span class="provider-dot" data-p="${c.provider}" style="display:inline-block;"></span>`;
    return `<label class="menu-file-row">
      <input type="checkbox" data-key="${key}" ${checked}>
      ${dot} ${escHtml(c.title.slice(0, 35))}
    </label>`;
  }).join('');

  menuFileList.querySelectorAll('input[type=checkbox]').forEach(cb => {
    cb.addEventListener('change', () => {
      const key = cb.dataset.key;
      if (cb.checked) hiddenFiles.delete(key);
      else hiddenFiles.add(key);
      LS.saveHidden(hiddenFiles);
      if (activeIndex >= 0 && filteredConvs[activeIndex] && hiddenFiles.has(fileKey(filteredConvs[activeIndex]))) {
        activeIndex = -1;
        mainContentEl.innerHTML = '<p style="color:#4a5060;padding:3rem 0;text-align:center;">Select a conversation</p>';
        jumpNavEl.innerHTML = '';
      }
      renderList();
    });
  });
}

// ─── Event wiring ────────────────────────────────────────────────────────────
menuBtn.addEventListener('click', e => {
  e.stopPropagation();
  const hidden = userMenu.classList.toggle('hidden');
  if (!hidden) buildMenuFileList();
});
document.addEventListener('click', e => {
  if (!userMenu.contains(e.target) && e.target !== menuBtn) userMenu.classList.add('hidden');
});

document.querySelectorAll('.sort-btn').forEach(b => {
  b.addEventListener('click', () => {
    prefs.sort = b.dataset.sort;
    LS.savePrefs(prefs);
    applyPrefs();
    renderList();
  });
});

toggleTs.addEventListener('change', () => {
  prefs.showTs = toggleTs.checked;
  LS.savePrefs(prefs);
  applyPrefs();
  renderList();
});

searchEl.addEventListener('input', handleSearch);

providerTabs.forEach(t => {
  t.addEventListener('click', () => setProvider(t.dataset.p));
});

// Persist scroll on exit
window.addEventListener('beforeunload', () => {
  if (activeIndex >= 0 && filteredConvs[activeIndex])
    persistedScrolls.set(fileKey(filteredConvs[activeIndex]), mainContentEl.scrollTop);
});
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden' && activeIndex >= 0 && filteredConvs[activeIndex])
    persistedScrolls.set(fileKey(filteredConvs[activeIndex]), mainContentEl.scrollTop);
});

// ─── Init ────────────────────────────────────────────────────────────────────
applyPrefs();
providerTabs.forEach(t => t.classList.toggle('active', t.dataset.p === activeProvider));
renderList();

// Restore last active conversation
const lastFile = LS.getActiveFile();
if (lastFile) {
  const idx = filteredConvs.findIndex(c => fileKey(c) === lastFile || c.file === lastFile);
  if (idx >= 0) loadConversation(idx);
}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

PROVIDERS = ["deepseek", "claude"]

PROVIDER_LABELS = {
    "deepseek": "DeepSeek",
    "claude":   "Claude",
    "all":      "All",
}


def build_spa(output_dir: Path, providers: list[str] | None = None) -> str:
    """
    Build the SPA HTML string.

    Args:
        output_dir: root output directory (contains provider subdirs)
        providers: list of providers to include, e.g. ['deepseek', 'claude'].
                   Defaults to all known providers that have HTML files.
    """
    if providers is None:
        providers = [p for p in PROVIDERS if (output_dir / p).is_dir()
                     and any((output_dir / p).glob("*.html"))]

    # Collect conversations per provider
    all_convs = []
    found_providers = []
    for p in providers:
        convs = scan_provider(output_dir, p)
        if convs:
            all_convs.extend(convs)
            found_providers.append(p)

    if not all_convs:
        raise ValueError(f"No HTML conversations found in {output_dir} for providers: {providers}")

    # Determine default provider for LS (first found, or "all" if multiple)
    default_provider = found_providers[0] if len(found_providers) == 1 else "all"

    # Build provider tab HTML
    tabs_html = ""
    if len(found_providers) > 1:
        for p in found_providers:
            label = PROVIDER_LABELS.get(p, p.title())
            tabs_html += f'<button class="tab-btn" data-p="{p}">{label}</button>\n'
        tabs_html += f'<button class="tab-btn" data-p="all">{PROVIDER_LABELS["all"]}</button>\n'
    # If only one provider, no tabs needed (hide the tab bar via empty content)

    js_data = _js_conv_list(all_convs)

    html = SPA_TEMPLATE
    html = html.replace("%%PROVIDER_TABS%%", tabs_html)
    html = html.replace("%%ALL_CONVERSATIONS%%", js_data)
    html = html.replace("%%DEFAULT_PROVIDER%%", default_provider)

    # Hide provider tabs bar when only one provider
    if len(found_providers) <= 1:
        html = html.replace(
            '<div id="provider-tabs">%%PROVIDER_TABS%%</div>',
            '<div id="provider-tabs" style="display:none;"></div>'
        ).replace("%%PROVIDER_TABS%%", "")

    return html

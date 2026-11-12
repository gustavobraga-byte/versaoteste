/* ==========================================================================
   UFVAI · web (webui-v1) — cliente novo (sem build, sem dependências)
   --------------------------------------------------------------------------
   Contrato com o servidor: /api/ufvai/*  (ver pesquisai/webapi.py)
   Eventos: SSE em /api/ufvai/events?sid=<id>

   Recursos (paridade com a interface web do OpenCode):
     · sessões (busca, criar, renomear, duplicar, compactar)
     · conversa com streaming real (texto, raciocínio, ferramentas)
     · menu "/" com os comandos do agente · menu "@" com arquivos do projeto
     · anexos de arquivo (arrastar/selecionar) e menções de arquivo
     · seletor de modelo + variante · somente o agente UFVAI
     · painel de ajustes (geral, modelo, agente, comandos, habilidades,
       sessão, atalhos, sobre)
     · ações de sessão (segundo plano, contexto) e de mensagem (copiar)
   ========================================================================== */
(() => {
  'use strict';

  /* ── infraestrutura ───────────────────────────────────────────────── */

  const BASE = (() => {
    let p = location.pathname.replace(/[^/]*$/, '');
    if (!p.endsWith('/')) p += '/';
    return p;
  })();

  const api = (p) => `${BASE}api/ufvai${p}`;
  const $ = (sel) => document.querySelector(sel);

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  async function apiGet(path) {
    const res = await fetch(api(path), { headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function apiPost(path, body) {
    const res = await fetch(api(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body || {}),
    });
    let data = {};
    try { data = await res.json(); } catch (e) { /* resposta sem corpo */ }
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  const state = {
    sessionId: '',
    sessions: [],
    messages: [],
    active: {},
    agents: [],
    commands: [],
    skills: [],
    models: [],
    providers: [],
    model: { id: '', providerID: '', variant: '' },
    agent: 'UFVAI',
    running: false,
    stream: {},
    manualSwitch: 0,
    source: null,
    attachments: [],
    pendingSkills: [],   // menções @skill ainda não enviadas
    palette: null,      // {kind:'command'|'mention', items, index, query}
    settingsTab: 'geral',
    locale: 'pt-BR',
    settingsOpen: false,
    allExpanded: false,
    view: 'web',            // 'web' | 'ttyd' — qual moldura está visível
    sseWaiters: [],          // promises à espera da abertura do SSE
    autoScroll: true,        // v0.7.11-web25: rolagem automática ativa
    about: {},               // ficha do UFVAI (aba "Sobre")
    autosave: null,          // configuração de autosave (vinda do wrapper)
    explorerPath: '',         // pasta atual do explorador de arquivos
    usage: null,           // {used, limit, percent} — janela de contexto
    uploads: [],           // anexos já gravados em disco pelo gateway
    prefs: {
      expandReasoning: false,
      expandTools: false,
      autosaveEnabled: true,
    },
  };

  /* ── preferências persistentes ────────────────────────────────────── */

  const PREFS_KEY = 'ufvai_web_prefs';

  function loadPrefs() {
    try {
      const raw = localStorage.getItem(PREFS_KEY);
      if (raw) Object.assign(state.prefs, JSON.parse(raw));
    } catch (e) { /* ignora */ }
  }

  function savePrefs() {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(state.prefs)); } catch (e) { /* ignora */ }
  }

  /* ── idioma (i18n) ─────────────────────────────────────────────────── */

  // v0.7.11-web23: a web segue o idioma escolhido na interface principal.
  // O dicionário vive em `i18n.json` (servido junto com o cliente) e o
  // idioma chega por `postMessage {type:'ufvai-lang'}` do wrapper — trocar o
  // idioma lá troca aqui, sem recarregar nada.
  const I18N = { locales: {}, default: 'pt-BR' };

  function localeFromTag(tag) {
    const key = String(tag || '').trim().toLowerCase().replace('-', '_');
    const map = {
      pt: 'pt-BR', pt_br: 'pt-BR', br: 'pt-BR',
      en: 'en', en_us: 'en',
      es: 'es', es_es: 'es',
      fr: 'fr', fr_fr: 'fr',
      zh: 'zh', zh_cn: 'zh',
    };
    return map[key] || null;
  }

  /**
   * Idioma escolhido na interface principal, lido do cookie.
   *
   * O cookie não depende da porta: quando a web roda no mesmo host do
   * wrapper (implantação local), o cookie ``pesquisai_lang`` é visível aqui.
   * No proxy do Colab os hosts são diferentes — aí quem manda é o
   * ``postMessage`` ``ufvai-lang``.
   */
  function localeFromCookie() {
    try {
      const match = document.cookie.match(/(?:^| )pesquisai_lang=([^;]+)/);
      return match ? localeFromTag(decodeURIComponent(match[1])) : null;
    } catch (e) { return null; }
  }

  function t(key, fallback) {
    const table = I18N.locales[state.locale] || I18N.locales[I18N.default] || {};
    if (table[key]) return table[key];
    if (fallback !== undefined) return fallback;
    return key;
  }

  /** Aplica o idioma: textos, placeholders, títulos e o `lang` do documento. */
  function applyLocale(lang) {
    const tag = localeFromTag(lang);
    if (!tag || !I18N.locales[tag]) return false;
    state.locale = tag;
    document.documentElement.setAttribute('lang', tag);
    document.querySelectorAll('[data-i18n]').forEach((node) => {
      const value = t(node.getAttribute('data-i18n'), '');
      if (value) node.textContent = value;
    });
    document.querySelectorAll('[data-i18n-title]').forEach((node) => {
      const value = t(node.getAttribute('data-i18n-title'), '');
      if (value) node.title = value;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((node) => {
      const value = t(node.getAttribute('data-i18n-placeholder'), '');
      if (value) node.placeholder = value;
    });
    applyPlaceholder();
    try { localStorage.setItem('ufvai_web_lang', tag); } catch (e) { /* ignora */ }
    renderSessions();
    renderAttachments();
    if (state.settingsOpen) renderSettings();
    return true;
  }

  /** Em tela estreita o placeholder longo é cortado: usa a versão curta. */
  function applyPlaceholder() {
    const input = $('#input');
    if (!input) return;
    const narrow = window.matchMedia('(max-width: 560px)').matches;
    input.placeholder = narrow
      ? t('composer.placeholderShort')
      : t('composer.placeholder');
  }

  async function loadI18n() {
    try {
      const res = await fetch(`${BASE}i18n.json`, { headers: { Accept: 'application/json' } });
      if (!res.ok) return;
      const data = await res.json();
      I18N.locales = data.locales || {};
      I18N.default = data.default || 'pt-BR';
    } catch (e) { /* sem i18n: segue em português */ }
  }

  /* ── markdown (leve, seguro: escapa tudo antes) ───────────────────── */

  const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ESC[c]);

  function inline(text) {
    const codes = [];
    let out = escapeHtml(text);
    out = out.replace(/`([^`\n]+)`/g, (_, code) => {
      codes.push(code);
      return `${codes.length - 1}`;
    });
    out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      (_, label, url) => `<a href="${url}" target="_blank" rel="noopener">${label}</a>`);
    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?:;]|$)/g, '$1<em>$2</em>');
    out = out.replace(/(\d+)/g, (_, i) => `<code>${escapeHtml(codes[Number(i)])}</code>`);
    return out;
  }

  function md(src) {
    const lines = String(src || '').split('\n');
    const out = [];
    let para = [];
    let list = null;

    const flushPara = () => {
      if (para.length) { out.push(`<p>${inline(para.join('\n'))}</p>`); para = []; }
    };
    const flushList = () => { if (list) { out.push(`</${list}>`); list = null; } };

    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i];

      if (/^```/.test(raw)) {
        flushPara(); flushList();
        const body = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) { body.push(lines[i]); i++; }
        out.push(`<pre><code>${escapeHtml(body.join('\n'))}</code></pre>`);
        continue;
      }
      if (/^\s*$/.test(raw)) { flushPara(); flushList(); continue; }

      const heading = raw.match(/^(#{1,4})\s+(.*)$/);
      if (heading) {
        flushPara(); flushList();
        const level = heading[1].length;
        out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
        continue;
      }
      if (/^(-{3,}|\*{3,})$/.test(raw.trim())) {
        flushPara(); flushList();
        out.push('<hr>');
        continue;
      }
      const quote = raw.match(/^>\s?(.*)$/);
      if (quote) {
        flushPara(); flushList();
        out.push(`<blockquote>${inline(quote[1])}</blockquote>`);
        continue;
      }
      const bullet = raw.match(/^\s*[-*+]\s+(.*)$/);
      const numbered = raw.match(/^\s*\d+[.)]\s+(.*)$/);
      if (bullet || numbered) {
        flushPara();
        const kind = bullet ? 'ul' : 'ol';
        if (list !== kind) { flushList(); out.push(`<${kind}>`); list = kind; }
        out.push(`<li>${inline((bullet || numbered)[1])}</li>`);
        continue;
      }
      flushList();
      para.push(raw);
    }
    flushPara(); flushList();
    return out.join('\n');
  }

  /* ── tema ─────────────────────────────────────────────────────────── */

  const THEME_KEY = 'pesquisai_theme';

  function applyTheme(theme) {
    // aceita o valor canônico do UFVAI ("pesquisai"/"pesquisai-light") e as
    // formas abreviadas ("light"/"dark") que a interface principal usava
    const light = theme === 'pesquisai-light' || theme === 'light';
    const value = light ? 'pesquisai-light' : 'pesquisai';
    document.documentElement.setAttribute('data-theme', value);
    document.documentElement.style.colorScheme = value === 'pesquisai-light' ? 'light' : 'dark';
    try { localStorage.setItem(THEME_KEY, value); } catch (e) { /* modo restrito */ }
    // O cookie é compartilhado com a interface principal (mesmo domínio,
    // porta diferente) — o botão de tema do cabeçalho do UFVAI e o da web
    // ficam em sincronia.
    try {
      document.cookie = `pesquisai_theme=${encodeURIComponent(value)}; path=/; max-age=31536000; SameSite=Lax`;
    } catch (e) { /* ignora */ }
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: 'ufvai-theme', theme: value }, '*');
      }
    } catch (e) { /* cross-origin bloqueado */ }
    try {
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute('content', value === 'pesquisai-light' ? '#f5f6f7' : '#141c24');
    } catch (e) { /* ignora */ }
  }

  function currentTheme() {
    try {
      const cookie = document.cookie.match(/(?:^| )pesquisai_theme=([^;]+)/);
      if (cookie) return decodeURIComponent(cookie[1]);
    } catch (e) { /* ignora */ }
    try {
      const stored = localStorage.getItem(THEME_KEY);
      if (stored) return stored;
    } catch (e) { /* ignora */ }
    return 'pesquisai';
  }

  window.addEventListener('message', (event) => {
    const data = event.data || {};
    if (data.type === 'ufvai-theme') applyTheme(data.theme);
    // v0.7.11-web24: qual vista está visível no wrapper (terminal ou web).
    // A web só segue o foco do terminal quando o terminal está à frente.
    if (data.type === 'ufvai-view') {
      state.view = data.view === 'ttyd' ? 'ttyd' : 'web';
    }
    // v0.7.11-web25: estado do autosave vindo do wrapper
    if (data.type === 'ufvai-autosave-state') {
      const payload = data.payload || {};
      state.autosave = {
        enabled: !!payload.enabled,
        intervalMin: payload.intervalMin || 10,
        scope: payload.scope || 'active',
        selectedIds: payload.selectedIds || [],
        sessions: payload.sessions || [],
        known: true,
      };
      state.prefs.autosaveEnabled = state.autosave.enabled;
      if (state.settingsOpen) renderSettings();
    }
    if (data.type === 'ufvai-autosave-saved') {
      toast(t('settings.autosaveSaved'));
    }
    // v0.7.11-web23: a interface principal propaga o idioma escolhido —
    // a web troca os textos na hora, sem recarregar.
    if (data.type === 'ufvai-lang') {
      if (applyLocale(data.lang)) {
        try { localStorage.setItem('ufvai_web_lang', state.locale); } catch (e) { /* ignora */ }
        toast(t('app.tagline'));
      }
    }
    // v0.7.11-web18: a interface principal confirma que a web respondeu; sem
    // este "pong" ela cai no proxy antigo (tela em branco).
    if (data.type === 'ufvai-ping') {
      try {
        if (event.source) {
          event.source.postMessage({ type: 'ufvai-pong', url: location.href }, '*');
        }
      } catch (e) { /* cross-origin bloqueado */ }
    }
  });

  /* ── toast ────────────────────────────────────────────────────────── */

  let toastTimer = null;
  function toast(message, kind) {
    const node = $('#toast');
    node.textContent = message;
    node.className = kind === 'err' ? 'toast err' : 'toast';
    node.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { node.hidden = true; }, 4200);
  }

  /* ── entrada de texto (prompt do navegador) ──────────────────────── */

  // v0.7.11-web24: `prompt()` é BLOQUEADO dentro de iframe sem
  // `allow="modals"` — por isso renomear a sessão não fazia nada na web.
  // Este modal resolve (e ainda funciona fora do iframe).
  let askResolve = null;

  function askText(title, value, hint, okLabel) {
    const modal = $('#prompt-modal');
    $('#prompt-title').textContent = title || '';
    $('#prompt-hint').textContent = hint || '';
    const input = $('#prompt-input');
    input.value = value || '';
    const ok = $('#prompt-ok');
    ok.textContent = okLabel || t('session.rename');
    modal.hidden = false;
    setTimeout(() => {
      input.focus();
      input.select();
    }, 30);
    return new Promise((resolve) => { askResolve = resolve; });
  }

  function closeAsk(value) {
    const modal = $('#prompt-modal');
    if (!modal || modal.hidden) return;
    modal.hidden = true;
    const resolve = askResolve;
    askResolve = null;
    if (resolve) resolve(value);
  }

  /* ── permissões (decisões do motor) ───────────────────────────────── */

  // v0.7.11-web24: quando o motor pede licença para agir, a web ficava
  // esperando em silêncio — o turno travava e as opções não apareciam.
  // Agora o pedido vira um cartão com as três decisões.

  const PERMISSION_LABELS = {
    bash: 'command',
    edit: 'edição',
    write: 'escrita',
    read: 'leitura',
    webfetch: 'acesso à internet',
    websearch: 'busca na internet',
    patch: 'edição',
    external_directory: 'acesso ao disco',
  };

  function permissionLabel(action) {
    const key = String(action || '').toLowerCase();
    return PERMISSION_LABELS[key] || key || t('tool.other');
  }

  function renderPermission(request) {
    const box = $('#permissions');
    if (!box) return;
    const id = String(request.id || '');
    if (!id) return;
    const existing = box.querySelector(`[data-pid="${id}"]`);
    if (existing) existing.remove();
    const card = el('div', 'perm-card');
    card.dataset.pid = id;
    const head = el('div', 'perm-head');
    head.appendChild(el('span', 'perm-icon', '🔐'));
    const title = el('div', 'perm-title');
    title.appendChild(el('strong', null, t('permission.title')));
    title.appendChild(el('span', 'perm-action', permissionLabel(request.action)));
    head.appendChild(title);
    card.appendChild(head);
    const msg = request.message || (request.resources || []).join('\n');
    if (msg) card.appendChild(el('pre', 'perm-msg', msg));
    const actions = el('div', 'perm-actions');
    const once = el('button', 'btn primary', t('permission.once'));
    once.addEventListener('click', () => replyPermission(id, 'once'));
    const always = el('button', 'btn', t('permission.always'));
    always.addEventListener('click', () => replyPermission(id, 'always'));
    const reject = el('button', 'btn danger', t('permission.reject'));
    reject.addEventListener('click', () => replyPermission(id, 'reject'));
    actions.appendChild(once);
    actions.appendChild(always);
    actions.appendChild(reject);
    card.appendChild(actions);
    box.appendChild(card);
    box.hidden = false;
    scrollToEnd(false);
  }

  function clearPermission(id) {
    const box = $('#permissions');
    if (!box) return;
    const node = box.querySelector(`[data-pid="${id}"]`);
    if (node) node.remove();
    box.hidden = box.children.length === 0;
  }

  async function replyPermission(id, decision) {
    if (!state.sessionId) return;
    try {
      await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/permission`, {
        requestID: id, decision,
      });
      clearPermission(id);
      toast(t('permission.done'));
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  /** Recarrega os pedidos de permissão em aberto (boot e reconexão). */
  async function loadPermissions() {
    if (!state.sessionId) return;
    try {
      const data = await apiGet(`/sessions/${encodeURIComponent(state.sessionId)}/permission`);
      const rows = data.permissions || [];
      const box = $('#permissions');
      if (box) box.innerHTML = '';
      rows.forEach(renderPermission);
      if (box) box.hidden = rows.length === 0;
    } catch (e) { /* sem permissões pendentes */ }
  }

  /* ── autosave (configuração do wrapper, via postMessage) ───────────── */

  /**
   * v0.7.11-web25: o autosave é agendado pelo WRAPPER (é o que mantém o
   * terminal vivo). A web não compartilha `localStorage` com ele (origens
   * diferentes no proxy do Colab), então a comunicação é por `postMessage`:
   *
   *   web → wrapper : ``ufvai-autosave-get`` / ``ufvai-autosave-set``
   *   wrapper → web : ``ufvai-autosave-state`` / ``ufvai-autosave-saved``
   */
  function askAutosave() {
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: 'ufvai-autosave-get' }, '*');
      }
    } catch (e) { /* cross-origin bloqueado */ }
  }

  async function pushAutosave() {
    const cfg = state.autosave || {};
    const payload = {
      enabled: !!cfg.enabled,
      intervalMin: parseInt(cfg.intervalMin, 10) || 10,
      scope: cfg.scope || 'active',
      selectedIds: cfg.selectedIds || [],
    };
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: 'ufvai-autosave-set', payload }, '*');
        toast(t('settings.autosaveSaved'));
      } else {
        // fora do wrapper (web aberta direto): mostra o estado local
        toast(t('settings.autosaveStandalone'));
      }
    } catch (e) {
      toast(t('settings.autosaveStandalone'), 'err');
    }
  }

  /* ── explorador de arquivos (v0.7.11-web26) ──────────────────────── */

  // Mini navegador da pasta do agente (Google Drive). Leve: sem framework,
  // só DOM — lista de arquivos + prévia mínima (texto, imagem, Office),
  // download e o link para editar no Google Drive.

  const EXPLORER_ICON = {
    directory: '📁',
    image: '🖼️',
    office: '📄',
    pdf: '📕',
    text: '📄',
    binary: '🔒',
  };

  function explorerIcon(item) {
    if (item.type === 'directory') return EXPLORER_ICON.directory;
    return EXPLORER_ICON[item.kind] || '📄';
  }

  function humanSize(bytes) {
    const value = Number(bytes || 0);
    if (!value) return '';
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${Math.round(value / 1024)} kB`;
    return `${(value / 1048576).toFixed(1)} MB`;
  }

  async function openExplorer() {
    document.body.classList.add('explorer-open');
    $('#explorer').hidden = false;
    await loadExplorer(state.explorerPath || '');
  }

  function closeExplorer() {
    document.body.classList.remove('explorer-open');
    $('#explorer').hidden = true;
  }

  async function loadExplorer(path) {
    const list = $('#exp-list');
    state.explorerPath = path || '';
    $('#exp-path').textContent = '/' + (path || '');
    list.innerHTML = '';
    list.appendChild(el('div', 'exp-empty', t('explorer.loading')));
    try {
      const data = await apiGet(`/explorer?path=${encodeURIComponent(path || '')}`);
      list.innerHTML = '';
      if (data.error) {
        list.appendChild(el('div', 'exp-empty', data.error));
        return;
      }
      const items = data.items || [];
      if (!items.length) {
        list.appendChild(el('div', 'exp-empty', t('explorer.empty')));
      }
      items.forEach((item) => {
        const row = el('button', 'exp-item');
        row.type = 'button';
        row.appendChild(el('span', 'exp-icon', explorerIcon(item)));
        row.appendChild(el('span', 'exp-name', item.name));
        if (item.type !== 'directory') {
          row.appendChild(el('span', 'exp-size', humanSize(item.size)));
        }
        row.addEventListener('click', () => {
          if (item.type === 'directory') {
            loadExplorer(item.path);
          } else {
            previewExplorerFile(item);
          }
        });
        list.appendChild(row);
      });
    } catch (e) {
      list.innerHTML = '';
      list.appendChild(el('div', 'exp-empty', String(e.message || e)));
    }
  }

  /* ── prévisualização formatada (leve) ──────────────────────────────── */

  // v0.7.11-web26: a prévia é **formatada**, mas leve — sem biblioteca:
  // markdown renderizado com o `md()` já existente, CSV como tabela, JSON
  // identado e código com uma coloração mínima (escape ANTES das regex,
  // então nada de injeção de HTML).

  const HL_KEYWORDS = {
    py: 'def class return if elif else import from as with try except finally for while in not and or None True False self lambda yield pass raise async await',
    js: 'function const let var return if else for while class new this import export from async await try catch finally null undefined true false',
    ts: 'interface type enum function const let var return if else for while class new this import export from async await try catch null undefined true false',
    sh: 'if then else fi for while do done case esac function return export local echo cd ls set source',
    css: 'important media supports keyframes from to inherit initial unset auto none flex grid block inline',
    html: 'html head body div span a img script style link meta title p ul li table tr td th',
    json: 'true false null',
  };

  const HL_EXT = {
    py: 'py', js: 'js', mjs: 'js', cjs: 'js', ts: 'ts', tsx: 'ts', jsx: 'js',
    sh: 'sh', bash: 'sh', zsh: 'sh', css: 'css', scss: 'css', html: 'html',
    htm: 'html', xml: 'html', json: 'json', yaml: 'yaml', yml: 'yaml', toml: 'toml',
  };

  function highlightCode(text, lang) {
    let out = escapeHtml(text);
    const words = (HL_KEYWORDS[lang] || '').split(' ').filter(Boolean);
    if (words.length) {
      const pattern = new RegExp(`\\b(${words.join('|')})\\b`, 'g');
      out = out.replace(pattern, '<span class="hl-kw">$1</span>');
    }
    if (lang === 'py' || lang === 'sh') {
      out = out.replace(/(#[^\n]*)/g, '<span class="hl-com">$1</span>');
    } else {
      out = out.replace(/(\/\/[^\n]*)/g, '<span class="hl-com">$1</span>');
    }
    out = out.replace(/(&quot;[^&\n]*?&quot;|&#39;[^&\n]*?&#39;)/g, '<span class="hl-str">$1</span>');
    out = out.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="hl-num">$1</span>');
    return out;
  }

  function csvToTable(text) {
    const rows = [];
    let row = [];
    let cell = '';
    let quoted = false;
    const source = String(text || '').slice(0, 120_000);
    for (let i = 0; i < source.length && rows.length < 120; i += 1) {
      const ch = source[i];
      if (quoted) {
        if (ch === '"' && source[i + 1] === '"') { cell += '"'; i += 1; }
        else if (ch === '"') quoted = false;
        else cell += ch;
      } else if (ch === '"') quoted = true;
      else if (ch === ',' || ch === ';' || ch === '\t') { row.push(cell); cell = ''; }
      else if (ch === '\n') { row.push(cell); rows.push(row); row = []; cell = ''; }
      else if (ch !== '\r') cell += ch;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    if (!rows.length) return null;
    const head = rows[0].map((c) => c.trim());
    const body = rows.slice(1).filter((r) => r.some((c) => c.trim()));
    const table = el('table', 'exp-table');
    const thead = el('thead');
    const trh = el('tr');
    head.forEach((cell) => trh.appendChild(el('th', null, cell)));
    thead.appendChild(trh);
    table.appendChild(thead);
    const tbody = el('tbody');
    body.forEach((r) => {
      const tr = el('tr');
      for (let i = 0; i < head.length; i += 1) tr.appendChild(el('td', null, (r[i] || '').trim()));
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
  }

  /** Conteúdo formatado da prévia, conforme o tipo do arquivo. */
  function renderPreviewContent(box, data) {
    const name = String(data.name || '');
    const suffix = name.includes('.') ? name.slice(name.lastIndexOf('.') + 1).toLowerCase() : '';
    const text = data.text || '';

    if (suffix === 'md' || suffix === 'markdown') {
      const boxMd = el('div', 'exp-prev-md');
      boxMd.innerHTML = md(text);
      box.appendChild(boxMd);
      return;
    }
    if (suffix === 'csv' || suffix === 'tsv') {
      const table = csvToTable(text);
      if (table) { box.appendChild(table); return; }
    }
    if (suffix === 'json') {
      try {
        const pretty = JSON.stringify(JSON.parse(text), null, 2);
        const pre = el('pre', 'exp-prev-text');
        pre.innerHTML = highlightCode(pretty, 'json');
        box.appendChild(pre);
        return;
      } catch (e) { /* não é JSON válido: cai no texto simples */ }
    }
    const pre = el('pre', 'exp-prev-text');
    pre.innerHTML = highlightCode(text, HL_EXT[suffix] || '');
    box.appendChild(pre);
  }

  async function previewExplorerFile(item) {
    const box = $('#exp-preview');
    box.hidden = false;
    box.innerHTML = '';
    box.appendChild(el('div', 'exp-empty', t('explorer.loading')));
    try {
      const data = await apiGet(`/explorer/preview?path=${encodeURIComponent(item.path)}`);
      box.innerHTML = '';
      const head = el('div', 'exp-prev-head');
      head.appendChild(el('span', 'exp-prev-name', data.name || item.name));
      const actions = el('div', 'exp-prev-actions');
      const dl = el('a', 'mini-btn', t('explorer.download'));
      dl.href = data.downloadUrl || '';
      dl.setAttribute('download', data.name || item.name);
      actions.appendChild(dl);
      const drive = el('a', 'mini-btn', t('explorer.drive'));
      drive.href = data.driveUrl || item.driveUrl || '';
      drive.target = '_blank';
      drive.rel = 'noopener';
      actions.appendChild(drive);
      head.appendChild(actions);
      box.appendChild(head);

      const body = el('div', 'exp-prev-body');
      if (data.error) body.appendChild(el('p', 'exp-prev-note', data.error));
      if (data.kind === 'image' && data.inlineUrl) {
        const img = document.createElement('img');
        img.className = 'exp-prev-image';
        img.alt = data.name || '';
        img.src = data.inlineUrl;
        body.appendChild(img);
      } else if (data.text) {
        renderPreviewContent(body, data);
      }
      if (data.truncated) {
        body.appendChild(el('p', 'exp-prev-note', t('explorer.truncated')));
      }
      box.appendChild(body);
    } catch (e) {
      box.innerHTML = '';
      box.appendChild(el('div', 'exp-empty', String(e.message || e)));
    }
  }

  /* ── finalizar sessão (com confirmação) ───────────────────────────── */

  // v0.7.11-web26: encerrar o trabalho com a sessão. Sempre pergunta antes
  // — e oferece as duas saídas reais: arquivar (a conversa continua na lista,
  // marcada com ✔) ou excluir do histórico (o autosave no Drive é o
  // arquivo de segurança).

  function askFinalize() {
    const modal = $('#confirm-modal');
    const row = currentSession();
    $('#confirm-title').textContent = t('session.finalize');
    $('#confirm-message').textContent = t('session.finalizeAsk')
      .replace('{title}', row ? sessionTitle(row) : '');
    modal.hidden = false;
  }

  function closeConfirm() {
    $('#confirm-modal').hidden = true;
  }

  async function finalizeSession(mode) {
    const sid = state.sessionId;
    if (!sid) { closeConfirm(); return; }
    try {
      const result = await apiPost(`/sessions/${encodeURIComponent(sid)}/finalize`, { mode });
      closeConfirm();
      toast(t('session.finalizeDone'));
      await refreshSessions();
      if (mode === 'delete') {
        const next = state.sessions.find((s) => s.id !== sid);
        if (next) await openSession(next.id);
        else await newSession();
      } else if (result && result.title) {
        // a sessão foi arquivada: o título no topo acompanha
        const row = state.sessions.find((s) => s.id === sid);
        if (row) row.title = result.title;
        $('#session-title').textContent = result.title;
        renderSessions();
      }
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  /* ── sessões ──────────────────────────────────────────────────────── */

  function relativeTime(ms) {
    if (!ms) return '';
    const diff = Math.max(0, Date.now() - ms);
    const min = Math.floor(diff / 60000);
    if (min < 1) return 'agora';
    if (min < 60) return `${min} min`;
    const hours = Math.floor(min / 60);
    if (hours < 24) return `${hours} h`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} d`;
    return new Date(ms).toLocaleDateString('pt-BR');
  }

  function sessionTitle(row) {
    if (row.title && row.title.trim()) return row.title.trim();
    return row.id.slice(0, 10);
  }

  function currentSession() {
    return state.sessions.find((s) => s.id === state.sessionId) || null;
  }

  function renderSessions() {
    const list = $('#sessions');
    const filter = ($('#session-search').value || '').trim().toLowerCase();
    list.innerHTML = '';
    const rows = state.sessions.filter((row) => {
      if (!filter) return true;
      return (row.title || '').toLowerCase().includes(filter) || row.id.toLowerCase().includes(filter);
    });
    if (!rows.length) {
      list.appendChild(el('div', 'model-group', 'sem sessões'));
      return;
    }
    rows.forEach((row) => {
      const item = el('button', 'session-item' + (row.id === state.sessionId ? ' active' : ''));
      item.type = 'button';
      if (state.active[row.id]) item.appendChild(el('span', 's-dot'));
      item.appendChild(el('span', 's-title', sessionTitle(row)));
      item.appendChild(el('span', 's-time', relativeTime(row.updated || row.created)));
      item.addEventListener('click', () => openSession(row.id, { focus: true }));
      // v0.7.11-web20: duplo clique no nome renomeia a sessão
      item.addEventListener('dblclick', (event) => {
        event.preventDefault();
        event.stopPropagation();
        renameSession(row.id);
      });
      list.appendChild(item);
    });
  }

  function renderUsage() {
    const row = currentSession();
    const pill = $('#usage-pill');
    if (!row) { pill.hidden = true; return; }
    const tokens = (row.tokens || {});
    const parts = [];
    const total = (tokens.input || 0) + (tokens.output || 0) + (tokens.reasoning || 0);
    if (total) parts.push(`${Math.round(total / 1000)}k tokens`);
    if (row.cost) parts.push(`$${Number(row.cost).toFixed(2)}`);
    // v0.7.11-web23: percentual da janela de contexto
    const usage = state.usage;
    if (usage && usage.limit) {
      const pct = Math.max(0, Math.min(100, Number(usage.percent) || 0));
      parts.push(`${pct.toFixed(pct < 10 ? 1 : 0)}% ${t('top.context')}`);
      pill.title = `${Math.round(usage.used / 1000)}k / ${Math.round(usage.limit / 1000)}k ${t('top.context')}`;
    }
    if (!parts.length) { pill.hidden = true; return; }
    pill.hidden = false;
    pill.textContent = parts.join(' · ');
  }

  /** Atualiza o uso da janela de contexto da sessão aberta. */
  async function refreshUsage() {
    if (!state.sessionId) return;
    try {
      const data = await apiGet(`/sessions/${encodeURIComponent(state.sessionId)}/usage`);
      state.usage = data || null;
      renderUsage();
    } catch (e) { /* motor fora do ar: mantém o último valor */ }
  }

  /* ── mensagens ────────────────────────────────────────────────────── */

  const TOOL_LIMITS = { input: 2500, output: 6000 };

  function truncate(text, limit) {
    const value = String(text ?? '');
    if (value.length <= limit) return value;
    return `${value.slice(0, limit)}
… (${value.length - limit} caracteres omitidos)`;
  }

  /** Rótulo curto da ferramenta (nomes próprios do motor). */
  function toolLabel(name) {
    const raw = String(name || '');
    const key = raw.toLowerCase().replace(/[^a-z]/g, '');
    const map = {
      shell: 'toolname.shell', bash: 'toolname.shell', write: 'toolname.write',
      edit: 'toolname.edit', read: 'toolname.read', list: 'toolname.list',
      grep: 'toolname.grep', glob: 'toolname.glob', patch: 'toolname.patch',
      todowrite: 'toolname.todo', webfetch: 'toolname.web', websearch: 'toolname.web',
      task: 'toolname.task', skill: 'toolname.skill',
    };
    const id = map[key];
    if (id) return t(id);
    return raw || t('toolname.other');
  }

  /** Diff por linhas: devolve {kind:'add'|'del'|'ctx', text}. */
  function diffRows(oldText, newText) {
    const a = String(oldText ?? '').split('\n');
    const b = String(newText ?? '').split('\n');
    let start = 0;
    while (start < a.length && start < b.length && a[start] === b[start]) start += 1;
    let endA = a.length;
    let endB = b.length;
    while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) {
      endA -= 1; endB -= 1;
    }
    const rows = [];
    a.slice(0, start).forEach((text) => rows.push({ kind: 'ctx', text }));
    a.slice(start, endA).forEach((text) => rows.push({ kind: 'del', text }));
    b.slice(start, endB).forEach((text) => rows.push({ kind: 'add', text }));
    a.slice(endA).forEach((text) => rows.push({ kind: 'ctx', text }));
    return rows;
  }

  /** Desenha o diff: adições em verde, supressões em vermelho. */
  function renderDiff(container, rows) {
    const box = el('div', 'diff');
    rows.forEach((row) => {
      const line = el('div', 'diff-row ' + row.kind);
      line.appendChild(el('span', 'diff-sign', row.kind === 'add' ? '+' : (row.kind === 'del' ? '−' : ' ')));
      line.appendChild(el('span', 'diff-text', row.text || ' '));
      box.appendChild(line);
    });
    container.appendChild(box);
    return box;
  }

  /** Bloco de diff a partir do payload do gateway ({added, removed}). */
  function diffFromPayload(payload) {
    if (!payload) return [];
    const rows = [];
    (payload.removed || []).forEach((text) => rows.push({ kind: 'del', text }));
    (payload.added || []).forEach((text) => rows.push({ kind: 'add', text }));
    return rows;
  }

  /** Entrada da ferramenta em formato legível (nada de JSON em uma linha). */
  function formatToolInput(name, input) {
    if (input === undefined || input === null) return '';
    const key = String(name || '').toLowerCase();
    if (typeof input === 'string') return `$ ${input}`;
    if (key.includes('shell') || key.includes('bash')) {
      const cmd = input.command || input.cmd || input.script || '';
      const extra = Object.entries(input)
        .filter(([k]) => !['command', 'cmd', 'script'].includes(k))
        .map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`)
        .join(' · ');
      return `$ ${cmd}${extra ? `\n${extra}` : ''}`;
    }
    if (key.includes('write') || key.includes('edit') || key.includes('patch')) {
      const path = input.filePath || input.path || input.file || '';
      const head = path ? `${t('tool.file')}: ${path}` : '';
      return head;
    }
    try {
      return truncate(JSON.stringify(input, null, 2), TOOL_LIMITS.input);
    } catch (e) {
      return truncate(String(input), TOOL_LIMITS.input);
    }
  }

  /** Tela de entrada da ferramenta: cabeçalho + diff/preview + saída. */
  function toolContent(name, input, output, diff) {
    const wrap = el('div', 'tool-content');
    const key = String(name || '').toLowerCase();
    const path = (input && typeof input === 'object')
      ? (input.filePath || input.path || input.file || '')
      : '';

    if (path) {
      wrap.appendChild(el('div', 'tool-path', path));
    }

    // diff: do gateway (write/edit) ou calculado do próprio `edit`
    let rows = diffFromPayload(diff);
    if (!rows.length && input && typeof input === 'object'
        && typeof input.oldString === 'string' && typeof input.newString === 'string') {
      rows = diffRows(input.oldString, input.newString);
    }
    if (rows.length) {
      const added = rows.filter((r) => r.kind === 'add').length;
      const removed = rows.filter((r) => r.kind === 'del').length;
      const legend = el('div', 'diff-legend');
      legend.appendChild(el('span', 'dl-add', `+${added} ${t('tool.added')}`));
      legend.appendChild(el('span', 'dl-del', `−${removed} ${t('tool.removed')}`));
      wrap.appendChild(legend);
      renderDiff(wrap, rows);
    } else if (input && typeof input === 'object' && typeof input.content === 'string') {
      // `write` sem foto anterior: mostra a prévia do conteúdo gravado
      const preview = el('pre', 'tool-preview', truncate(input.content, 1200));
      wrap.appendChild(preview);
    } else {
      const text = formatToolInput(name, input);
      if (text) wrap.appendChild(el('pre', 'tool-preview', text));
    }

    if (output) {
      wrap.appendChild(el('pre', 'tool-output', truncate(output, TOOL_LIMITS.output)));
    }
    return wrap;
  }

  /** Resumo compacto do uso de ferramentas (estilo "Used 39 · Write, Shell"). */
  function toolSummary(tools) {
    if (!tools || !tools.length) return null;
    const names = [];
    tools.forEach((tool) => {
      const label = toolLabel(tool.name);
      if (!names.includes(label)) names.push(label);
    });
    const count = tools.length;
    const node = el('button', 'tool-summary');
    node.type = 'button';
    node.appendChild(el('span', 'ts-count', `${count}`));
    node.appendChild(el('span', 'ts-label', count === 1 ? t('tool.call') : t('tool.calls')));
    node.appendChild(el('span', 'ts-names', names.join(' · ')));
    return node;
  }

  /** Botão de copiar — usado na resposta, no raciocínio e nas ferramentas. */
  function miniCopy(getText, label) {
    const btn = el('button', 'mini-btn copy', label || t('tool.copy'));
    btn.type = 'button';
    btn.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const text = getText();
      if (!text) { toast(t('warn.copyFailed'), 'err'); return; }
      try {
        await navigator.clipboard.writeText(text);
        toast(t('tool.copied'));
      } catch (e) {
        toast(t('tool.copyFail'), 'err');
      }
    });
    return btn;
  }

  function textBlock(label, body, cls) {
    const details = el('details', 'block' + (cls ? ' ' + cls : ''));
    const summary = el('summary');
    summary.appendChild(el('span', 'block-label', label));
    details.appendChild(summary);
    const bodyNode = el('div', 'block-body', body || '');
    details.appendChild(bodyNode);
    details.__body = bodyNode;
    // v0.7.11-web23: copiar o raciocínio
    summary.appendChild(miniCopy(() => bodyNode.textContent || ''));
    return details;
  }

  function toolBlock(name, status) {
    const details = el('details', 'block tool');
    const summary = el('summary');
    const head = el('span', 'tool-head');
    head.appendChild(el('span', 'tool-name', toolLabel(name)));
    const statusNode = el('span', 'status-run', status || t('tool.running'));
    head.appendChild(statusNode);
    summary.appendChild(head);
    details.appendChild(summary);
    const body = el('div', 'block-body');
    details.appendChild(body);
    details.__body = body;
    details.__status = statusNode;
    // v0.7.11-web23: copiar a ferramenta (entrada + saída)
    summary.appendChild(miniCopy(() => body.textContent || ''));
    return details;
  }

  function assistantShell(message) {
    const wrap = el('div', 'msg msg-assistant');
    const who = el('div', 'who');
    who.appendChild(el('b', null, message.agent || 'UFVAI'));
    if (message.model && message.model.id) {
      who.appendChild(el('span', 'tag', message.model.id));
    }
    wrap.appendChild(who);
    return wrap;
  }

  function copyButton(getText, label) {
    const actions = el('div', 'msg-actions');
    actions.appendChild(miniCopy(getText, label || t('tool.copy')));
    return actions;
  }

  /** Abre/fecha TODOS os blocos (raciocínio e ferramentas) da conversa. */
  function setAllExpanded(open) {
    document.querySelectorAll('#messages details.block').forEach((block) => {
      block.open = open;
    });
    const btn = $('#expand-all-btn');
    if (btn) {
      btn.classList.toggle('on', open);
      const label = btn.querySelector('.lb-text');
      if (label) label.textContent = open ? t('tool.collapseAll') : t('tool.expandAll');
      btn.title = open ? t('tool.collapseAll') : t('tool.expandAll');
    }
    state.allExpanded = open;
  }

  function renderMessage(message) {
    if (message.role === 'user') {
      const wrap = el('div', 'msg msg-user');
      wrap.appendChild(el('div', 'bubble', message.text || ''));
      wrap.appendChild(copyButton(() => message.text || ''));
      return wrap;
    }

    const wrap = assistantShell(message);
    const answer = el('div', 'answer');
    answer.innerHTML = md(message.text || '');
    wrap.appendChild(answer);

    if (message.reasoning) {
      const block = textBlock(t('tool.reasoning'), message.reasoning, 'reasoning');
      block.open = !!state.prefs.expandReasoning;
      wrap.appendChild(block);
    }
    const tools = message.tools || [];
    if (tools.length) {
      const summary = toolSummary(tools);
      if (summary) {
        summary.addEventListener('click', () => {
          const blocks = wrap.querySelectorAll('details.block.tool');
          const shouldOpen = ![...blocks].every((b) => b.open);
          blocks.forEach((b) => { b.open = shouldOpen; });
        });
        wrap.appendChild(summary);
      }
      tools.forEach((tool) => {
        const block = toolBlock(tool.name, tool.status);
        block.__body.innerHTML = '';
        block.__body.appendChild(
          toolContent(tool.name, tool.input, tool.output, tool.diff),
        );
        if (tool.status === 'error') block.__status.textContent = t('tool.error');
        if (tool.status === 'completed') block.__status.textContent = t('tool.done');
        block.open = !!state.prefs.expandTools;
        wrap.appendChild(block);
      });
    }
    if (message.error) {
      wrap.appendChild(el('div', 'msg-error', message.error));
    }
    wrap.appendChild(copyButton(() => message.text || '', t('session.copyResponse')));
    return wrap;
  }

  function renderMessages() {
    const box = $('#messages');
    box.innerHTML = '';
    $('#empty-state').hidden = state.messages.length > 0;
    state.messages.forEach((message) => box.appendChild(renderMessage(message)));
    scrollToEnd(true);
  }

  /**
   * Rolagem automática: a conversa **segue** o conteúdo novo.
   *
   * v0.7.11-web25: antes a rolagem só acontecia se o usuário já estivesse
   * perto do fim — as mensagens novas "apareciam fora da tela". Agora ela
   * acompanha sempre; se o usuário rolar para cima, a rolagem automática é
   * pausada e aparece o botão "ir para o fim".
   */
  function scrollToEnd(force) {
    const thread = $('#thread');
    if (!thread) return;
    if (!force && !state.autoScroll) { showJump(true); return; }
    // v0.7.11-web25: sem animação — a rolagem automática acontece a cada
    // fragmento de texto e a animação a deixava sempre "a caminho".
    thread.scrollTop = thread.scrollHeight;
    showJump(false);
  }

  function showJump(visible) {
    const btn = $('#jump-btn');
    if (btn) btn.hidden = !visible;
  }

  function onThreadScroll() {
    const thread = $('#thread');
    if (!thread) return;
    const dist = thread.scrollHeight - thread.scrollTop - thread.clientHeight;
    // rolagem para CIMA (ação do usuário) → pausa a rolagem automática.
    // Mas se o CONTEÚDO mudou (nova conversa, nova mensagem renderizada), o
    // salto para 0 é do re-render, não do usuário — nesse caso a conversa
    // deve continuar acompanhando.
    const subiu = thread.scrollTop < lastScrollTop - 4;
    const conteudoMudou = Math.abs(thread.scrollHeight - lastScrollHeight) > 40;
    lastScrollTop = thread.scrollTop;
    lastScrollHeight = thread.scrollHeight;
    if (subiu && !conteudoMudou) {
      lastUserScrollUp = Date.now();
      state.autoScroll = false;
      showJump(true);
      return;
    }
    state.autoScroll = dist < 120;
    showJump(!state.autoScroll);
  }

  let lastScrollTop = 0;
  let lastScrollHeight = 0;
  let lastUserScrollUp = 0;
  let lastTouchY = 0;

  /**
   * Intenção de rolagem para CIMA — detectada em ``wheel``/``touchmove``,
   * que disparam **antes** do evento ``scroll``. Sem isso havia uma corrida:
   * o `ResizeObserver` (que acompanha o conteúdo) puxava a conversa de volta
   * ao fim antes de o evento `scroll` ser processado, e o usuário nunca
   * conseguia ler uma mensagem antiga.
   */
  function onScrollIntent(event) {
    let delta = 0;
    if (event.deltaY !== undefined) {
      delta = event.deltaY;
    } else if (event.touches && event.touches.length) {
      const y = event.touches[0].clientY;
      delta = lastTouchY - y;
      lastTouchY = y;
    }
    if (delta > 0) return;             // rolando para baixo
    lastUserScrollUp = Date.now();
    state.autoScroll = false;
    showJump(true);
  }

  /* ── streaming ────────────────────────────────────────────────────── */

  function streamSlot(messageID) {
    if (!state.stream[messageID]) {
      const wrap = el('div', 'msg msg-assistant');
      const who = el('div', 'who');
      who.appendChild(el('b', null, 'UFVAI'));
      wrap.appendChild(who);
      const answer = el('div', 'answer');
      wrap.appendChild(answer);
      const slot = { wrap, answer, text: '', reasoning: '', tools: {}, toolInputs: {}, reasoningBlock: null, __tools: '' };
      // v0.7.11-web24: as mensagens em streaming também precisam do botão
      // de copiar (antes ele só existia nas mensagens do histórico).
      wrap.appendChild(copyButton(() => slot.text || '', t('session.copyResponse')));
      state.stream[messageID] = slot;
      $('#messages').appendChild(wrap);
      $('#empty-state').hidden = true;
    }
    return state.stream[messageID];
  }

  function scheduleRender(slot) {
    if (slot.__pending) return;
    slot.__pending = true;
    requestAnimationFrame(() => {
      slot.__pending = false;
      slot.answer.innerHTML = md(slot.text);
      if (slot.reasoningBlock) slot.reasoningBlock.__body.textContent = slot.reasoning;
      scrollToEnd(false);
    });
  }

  function handleEvent(ev) {
    if (!ev || !ev.type) return;
    if (ev.sid && state.sessionId && ev.sid !== state.sessionId) return;

    switch (ev.type) {
      case 'run.started':
        setRunning(true);
        break;
      case 'run.finished':
      case 'run.failed':
        setRunning(false);
        refreshSessions();
        refreshUsage();
        // v0.7.11-web24: completa o texto que possa ter ficado faltando
        syncTail();
        break;
      case 'step.started': {
        const slot = streamSlot(ev.messageID);
        const who = slot.wrap.querySelector('.who');
        if (who && ev.agent) who.querySelector('b').textContent = ev.agent;
        break;
      }
      case 'text.started':
        streamSlot(ev.messageID);
        break;
      case 'text.delta': {
        const slot = streamSlot(ev.messageID);
        slot.text += ev.delta || '';
        scheduleRender(slot);
        break;
      }
      case 'text.ended': {
        const slot = streamSlot(ev.messageID);
        if (typeof ev.text === 'string' && ev.text.length >= slot.text.length) slot.text = ev.text;
        scheduleRender(slot);
        break;
      }
      case 'reasoning.started':
        streamSlot(ev.messageID);
        break;
      case 'reasoning.delta': {
        const slot = streamSlot(ev.messageID);
        slot.reasoning += ev.delta || '';
        if (!slot.reasoningBlock) {
          slot.reasoningBlock = textBlock(t('tool.reasoning'), '', 'reasoning');
          slot.reasoningBlock.open = !!state.prefs.expandReasoning;
          slot.wrap.appendChild(slot.reasoningBlock);
        }
        scheduleRender(slot);
        break;
      }
      case 'reasoning.ended': {
        const slot = streamSlot(ev.messageID);
        if (ev.text) slot.reasoning = ev.text;
        if (!slot.reasoningBlock) {
          slot.reasoningBlock = textBlock(t('tool.reasoning'), slot.reasoning, 'reasoning');
          slot.wrap.appendChild(slot.reasoningBlock);
        }
        scheduleRender(slot);
        break;
      }
      case 'tool.started': {
        const slot = streamSlot(ev.messageID);
        const block = toolBlock(ev.name, t('tool.running'));
        slot.toolInputs[ev.callID] = ev.input;
        block.__body.innerHTML = '';
        block.__body.appendChild(toolContent(ev.name, ev.input, null, null));
        slot.tools[ev.callID] = block;
        slot.wrap.appendChild(block);
        scrollToEnd(false);
        break;
      }
      case 'tool.finished': {
        const slot = streamSlot(ev.messageID);
        const block = slot.tools[ev.callID];
        if (block) {
          block.__status.textContent = ev.status === 'error' ? t('tool.error') : t('tool.done');
          if (ev.status === 'error') block.__status.className = 'status-error';
          // v0.7.11-web23: o diff do arquivo alterado chega no fim da chamada
          const input = slot.toolInputs && slot.toolInputs[ev.callID];
          block.__body.innerHTML = '';
          block.__body.appendChild(toolContent(ev.name, input, ev.output, ev.diff));
        }
        scrollToEnd(false);
        break;
      }
      case 'inbox.enqueued':
        if (ev.text) {
          const wrap = el('div', 'msg msg-user');
          wrap.appendChild(el('div', 'bubble', ev.text));
          wrap.style.opacity = '0.65';
          $('#messages').appendChild(wrap);
          scrollToEnd(false);
        }
        break;
      case 'permission.asked':
        renderPermission(ev);
        break;
      case 'permission.replied':
        clearPermission(ev.id);
        break;
      case 'error':
        toast(ev.error || 'erro do motor', 'err');
        break;
      default:
        break;
    }
  }

  function setRunning(running) {
    state.running = !!running;
    $('#status').hidden = !running;
    $('#stop-btn').hidden = !running;
    $('#status-text').textContent = running ? t('status.working') : '';
    if (running) watchRun();
  }

  /**
   * v0.7.11-web24: o aviso "Trabalhando…" ficava na tela para sempre quando
   * o evento ``run.finished`` se perdia (queda do SSE no fim do turno).
   * O watchdog consulta o motor: quando a sessão deixa de estar ``busy``,
   * o aviso some — independente do evento.
   */
  let runWatchTimer = null;

  function watchRun() {
    if (runWatchTimer) return;
    runWatchTimer = setInterval(async () => {
      if (!state.running || !state.sessionId) return;
      try {
        const row = await apiGet(`/sessions/${encodeURIComponent(state.sessionId)}`);
        const busy = Number(row.busy || 0);
        const updated = Number(row.updated || 0);
        // `busy` é o instante em que a execução começou; `updated` é a última
        // escrita — se a última escrita é posterior, a sessão já terminou.
        if (busy && updated && busy < updated) {
          setRunning(false);
          await syncTail();
        } else {
          // ainda rodando: confere se o texto chegou inteiro (evento perdido)
          await syncTail();
        }
      } catch (e) { /* motor fora do ar: o watchdog de reconexão trata */ }
    }, 4000);
  }

  /**
   * v0.7.11-web24: as vezes a mensagem parava no meio (evento de streaming
   * perdido). Ao fim do turno — e a cada reconexão do SSE — a web relê as
   * últimas mensagens do motor e completa o que ficou faltando.
   */
  async function syncTail() {
    if (!state.sessionId) return;
    try {
      const data = await apiGet(`/sessions/${encodeURIComponent(state.sessionId)}/messages?limit=40`);
      const rows = data.messages || [];
      if (!rows.length) return;
      const last = rows[rows.length - 1];
      if (!last || last.role !== 'assistant') return;
      const slot = state.stream[last.id];
      if (slot) {
        const texto = last.text || '';
        const ferramentas = JSON.stringify(last.tools || []);
        if (slot.text !== texto || slot.__tools !== ferramentas) {
          slot.text = texto;
          slot.__tools = ferramentas;
          slot.answer.innerHTML = md(texto);
          if (slot.reasoningBlock && last.reasoning) {
            slot.reasoningBlock.__body.textContent = last.reasoning;
          }
          renderStreamTools(slot, last.tools || []);
        }
        return;
      }
      const known = state.messages.find((m) => m.id === last.id);
      if (!known) {
        // v0.7.11-web24: os eventos do turno se perderam por completo — o
        // motor tem a resposta, então ela é reconstruída aqui.
        if (state.running) {
          const novo = streamSlot(last.id);
          novo.text = last.text || '';
          novo.__tools = JSON.stringify(last.tools || []);
          novo.answer.innerHTML = md(novo.text);
          if (last.reasoning) {
            novo.reasoningBlock = textBlock(t('tool.reasoning'), last.reasoning, 'reasoning');
            novo.reasoningBlock.open = !!state.prefs.expandReasoning;
            novo.wrap.appendChild(novo.reasoningBlock);
          }
          renderStreamTools(novo, last.tools || []);
          return;
        }
        state.messages.push(last);
        renderMessages();
      } else if ((known.text || '') !== (last.text || '')) {
        known.text = last.text;
        known.reasoning = last.reasoning;
        known.tools = last.tools;
        renderMessages();
      }
    } catch (e) { /* mantém o que já está na tela */ }
  }

  /** Reconstrói os blocos de ferramentas de uma mensagem em streaming. */
  function renderStreamTools(slot, tools) {
    if (!slot) return;
    const existentes = slot.wrap.querySelectorAll('details.block.tool');
    existentes.forEach((node) => node.remove());
    (tools || []).forEach((tool) => {
      const block = toolBlock(tool.name, tool.status);
      block.__body.innerHTML = '';
      block.__body.appendChild(toolContent(tool.name, tool.input, tool.output, tool.diff));
      if (tool.status === 'error') block.__status.textContent = t('tool.error');
      if (tool.status === 'completed') block.__status.textContent = t('tool.done');
      block.open = !!state.prefs.expandTools;
      slot.wrap.appendChild(block);
    });
  }

  /* ── eventos (SSE) ────────────────────────────────────────────────── */

  // v0.7.11-web23: se a conexão ficar caída por mais de 10 minutos, o
  // ambiente do Colab provavelmente foi encerrado (inatividade). O aviso
  // explica o que houve e lembra que o Drive está intacto.
  const DEAD_AFTER_MS = 10 * 60 * 1000;
  let downSince = 0;

  /**
   * Detecta a queda do ambiente (Colab encerrado).
   *
   * v0.7.11-web25: dois sinais independentes — o SSE (que só cai se o
   * gateway ou o motor morrem) e um **heartbeat** em ``/health`` (que cobre o
   * caso do servidor inteiro ter ido). Depois de 10 minutos sem resposta,
   * o aviso explica o que houve.
   */
  function markEngineDown() {
    const dot = $('#engine-dot');
    const text = $('#engine-text');
    if (dot) dot.className = 'dot bad';
    if (text) text.textContent = t('sidebar.reconnecting');
    if (!downSince) {
      downSince = Date.now();
      setTimeout(() => {
        if (downSince && Date.now() - downSince >= DEAD_AFTER_MS) showEngineDead();
      }, DEAD_AFTER_MS + 500);
    }
  }

  function showEngineDead() {
    const banner = $('#engine-dead');
    if (banner) banner.hidden = false;
    const text = $('#engine-text');
    if (text) text.textContent = t('sidebar.engineDead');
  }

  function markEngineUp() {
    downSince = 0;
    const banner = $('#engine-dead');
    if (banner) banner.hidden = true;
  }

  /** Heartbeat: sonda o gateway (não depende do SSE). */
  async function heartbeat() {
    try {
      const res = await fetch(`${BASE}health`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      markEngineUp();
    } catch (e) {
      markEngineDown();
    }
  }

  function connectEvents() {
    if (state.source) { state.source.close(); state.source = null; }
    const url = api(`/events${state.sessionId ? `?sid=${encodeURIComponent(state.sessionId)}` : ''}`);
    const source = new EventSource(url);
    state.source = source;
    source.onmessage = (event) => {
      try { handleEvent(JSON.parse(event.data)); } catch (e) { /* frame inválido */ }
    };
    source.onerror = () => {
      markEngineDown();
    };
    source.onopen = () => {
      markEngineUp();
      const dot = $('#engine-dot');
      const text = $('#engine-text');
      if (dot) dot.className = 'dot ok';
      if (text) text.textContent = t('sidebar.connected');
      // v0.7.11-web24: ao reconectar, o que chegou durante a queda se perdeu
      // — relê a cauda da conversa e reidrata as permissões pendentes.
      syncTail();
      loadPermissions();
      const waiters = state.sseWaiters.splice(0, state.sseWaiters.length);
      waiters.forEach((fn) => fn());
    };
  }

  /**
   * v0.7.11-web24: o prompt precisa sair **depois** que o SSE está aberto.
   * Antes, a mensagem era publicada logo após trocar de sessão e os eventos
   * (``run.started``, ``text.delta``) se perdiam — a resposta aparecia
   * vazia ou truncada.
   */
  function ensureEvents() {
    if (state.source && state.source.readyState === 1) return Promise.resolve();
    return new Promise((resolve) => {
      state.sseWaiters.push(resolve);
      connectEvents();
      // não bloqueia o envio se o motor estiver fora do ar
      setTimeout(() => {
        const waiters = state.sseWaiters.splice(0, state.sseWaiters.length);
        waiters.forEach((fn) => fn());
      }, 2500);
    });
  }

  /* ── sessão ───────────────────────────────────────────────────────── */

  function applyModel(model) {
    state.model = {
      id: model.id || '',
      providerID: model.providerID || '',
      variant: model.variant || '',
    };
    const label = state.model.id ? `${state.model.id} · ${state.model.providerID}` : 'modelo…';
    $('#model-label').textContent = label;
    renderVariant();
  }

  function currentModelEntry() {
    return state.models.find(
      (m) => m.id === state.model.id && m.providerID === state.model.providerID,
    ) || null;
  }

  function renderVariant() {
    const entry = currentModelEntry();
    const variants = (entry && entry.variants) || [];
    const box = $('#variant-chip');
    if (!box) return;
    if (!variants.length) { box.hidden = true; return; }
    box.hidden = false;
    box.textContent = state.model.variant ? `variante: ${state.model.variant}` : 'variante: padrão';
  }

  async function openSession(sid, opts) {
    if (!sid) return;
    const options = opts || {};
    state.sessionId = sid;
    state.manualSwitch = Date.now();
    state.stream = {};
    state.attachments = [];
    renderAttachments();
    closePalette();
    $('#session-title').textContent = 'carregando…';

    try {
      const data = await apiGet(`/sessions/${encodeURIComponent(sid)}/messages`);
      state.messages = data.messages || [];
    } catch (e) {
      state.messages = [];
      toast('não foi possível carregar a sessão', 'err');
    }

    const row = state.sessions.find((s) => s.id === sid);
    $('#session-title').textContent = row ? sessionTitle(row) : sid.slice(0, 12);
    if (row) applyModel(row.model || {});
    if (row && row.agent) {
      state.agent = row.agent;
      $('#agent-label').textContent = row.agent;
    }
    renderMessages();
    renderSessions();
    renderUsage();
    refreshUsage();
    connectEvents();
    // Só uma escolha explícita do usuário move o terminal: abrir a página não
    // deve arrastar a TUI para outra sessão.
    if (options.focus) {
      apiPost('/focus', { sid }).catch(() => {});
    }
  }

  async function refreshSessions() {
    try {
      const data = await apiGet('/sessions');
      state.sessions = data.sessions || [];
      state.active = data.active || {};
      renderSessions();
      renderUsage();
    } catch (e) { /* mantém a lista anterior */ }
  }

  async function newSession() {
    try {
      const body = {};
      if (state.agent) body.agent = state.agent;
      if (state.model.id && state.model.providerID) body.model = state.model;
      const data = await apiPost('/sessions', body);
      const row = data.session;
      state.sessions.unshift(row);
      renderSessions();
      await openSession(row.id, { focus: true });
      $('#input').focus();
    } catch (e) {
      toast('não foi possível criar a sessão', 'err');
    }
  }

  /* ── envio ────────────────────────────────────────────────────────── */

  async function send() {
    const input = $('#input');
    const text = input.value.trim();
    if (!text && !state.attachments.length) return;
    if (!state.sessionId) { await newSession(); }

    input.value = '';
    input.style.height = 'auto';

    const wrap = el('div', 'msg msg-user');
    wrap.appendChild(el('div', 'bubble', text || `(${t('composer.attached')})`));
    if (state.attachments.length) {
      const names = state.attachments
        .map((a) => `📎 ${a.name}${a.path ? `\n${a.path}` : ''}`)
        .join('\n');
      wrap.appendChild(el('div', 'bubble-attach', names));
    }
    $('#messages').appendChild(wrap);
    $('#empty-state').hidden = true;
    scrollToEnd(true);

    // v0.7.11-web23: o anexo vai inline (o modelo lê) E o gateway recebe o
    // caminho em disco (o agente abre).
    const files = state.attachments
      .filter((a) => a.uri)
      .map((a) => ({ uri: a.uri, source: { type: 'inline' }, name: a.name }));
    const uploads = state.attachments
      .filter((a) => a.path)
      .map((a) => ({ name: a.name, path: a.path, size: a.size }));
    const skills = state.pendingSkills.slice();
    state.attachments = [];
    state.pendingSkills = [];
    renderAttachments();

    try {
      // v0.7.11-web24: garante o SSE aberto antes de publicar (evita perder
      // os eventos do turno).
      await ensureEvents();
      await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/message`, {
        text, files, skills: skills.length ? skills : undefined,
        uploads: uploads.length ? uploads : undefined,
      });
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  async function stop() {
    if (!state.sessionId) return;
    try {
      await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/interrupt`, {});
      toast('interrompendo…');
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  /* ── anexos ───────────────────────────────────────────────────────── */

  // v0.7.11-web23: 25 MB (limite do gateway; o motor aceita inline grande,
  // mas o upload em disco é o que o agente realmente consegue abrir).
  const MAX_ATTACHMENT = 25 * 1024 * 1024;

  function humanSize(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} kB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  function renderAttachments() {
    const box = $('#attachments');
    box.innerHTML = '';
    state.attachments.forEach((item, index) => {
      const chip = el('span', 'chip' + (item.mime && item.mime.startsWith('image/') ? ' image' : ''));
      chip.appendChild(el('span', 'c-name', item.name));
      if (item.size) chip.appendChild(el('span', 'c-size', humanSize(item.size)));
      if (item.path) chip.appendChild(el('span', 'c-path', item.path));
      if (item.pending) chip.appendChild(el('span', 'c-path', t('composer.uploading')));
      const rm = el('button', null, '✕');
      rm.type = 'button';
      rm.title = t('composer.remove');
      rm.addEventListener('click', () => {
        state.attachments.splice(index, 1);
        renderAttachments();
      });
      chip.appendChild(rm);
      box.appendChild(chip);
    });
    box.hidden = state.attachments.length === 0;
  }

  function readFileAsDataUri(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('falha ao ler o arquivo'));
      reader.onload = () => resolve(String(reader.result || ''));
      reader.readAsDataURL(file);
    });
  }

  /**
   * Anexa arquivos do dispositivo.
   *
   * Duas vias: (1) o arquivo vai **inline** no prompt (data URI) para o
   * modelo enxergar o conteúdo; (2) o gateway o grava em ``/tmp`` e devolve
   * o caminho absoluto, que é injetado no prompt — sem isso o agente
   * recebe o arquivo "no vácuo" e não consegue abrir.
   */
  async function attachLocalFiles(files) {
    for (const file of files) {
      if (file.size > MAX_ATTACHMENT) {
        toast(`${file.name} ${t('composer.tooBig')}`, 'err');
        continue;
      }
      const item = {
        name: file.name, size: file.size, mime: file.type || '', uri: '', path: '', pending: true,
      };
      state.attachments.push(item);
      renderAttachments();
      try {
        const uri = await readFileAsDataUri(file);
        item.uri = uri;
        const base64 = uri.includes(',') ? uri.split(',')[1] : '';
        const res = await apiPost('/upload', {
          sid: state.sessionId || '',
          name: file.name,
          mime: file.type || '',
          data: base64,
        });
        if (res && res.ok) {
          item.path = res.path || '';
          item.name = res.name || file.name;
          item.size = res.size || file.size;
        } else {
          toast(`${file.name}: ${t('composer.uploadFail')}`, 'err');
        }
      } catch (e) {
        toast(`${file.name}: ${t('composer.uploadFail')}`, 'err');
      } finally {
        item.pending = false;
        renderAttachments();
      }
    }
  }

  /* ── paletas: "/" (comandos) e "@" (arquivos) ────────────────────── */

  function triggerAtCaret() {
    const input = $('#input');
    const pos = input.selectionStart ?? input.value.length;
    const before = input.value.slice(0, pos);
    const command = before.match(/(^|\s)\/([^\s/]*)$/);
    if (command) {
      return { kind: 'command', query: command[2], start: pos - command[2].length - 1, end: pos };
    }
    const mention = before.match(/(^|\s)@([^\s@]*)$/);
    if (mention) {
      const query = mention[2] || '';
      return { kind: 'mention', query, start: pos - query.length - 1, end: pos };
    }
    return null;
  }

  function closePalette() {
    state.palette = null;
    $('#palette').hidden = true;
  }

  function basename(path) {
    const clean = String(path || '').replace(/\/+$/, '');
    const parts = clean.split('/');
    return parts[parts.length - 1] || clean || path;
  }

  function rebuildMentionItems(pal) {
    const q = (pal.query || '').toLowerCase();
    const skills = state.skills
      .filter((s) => !q || s.id.toLowerCase().includes(q) || (s.name || '').toLowerCase().includes(q))
      .map((s) => ({
        group: t('palette.skills'),
        type: 'skill',
        id: s.id,
        name: '@' + s.id,
        desc: s.description || s.name || '',
      }));
    const files = (pal.files || []).map((f) => ({
      group: t('palette.files'),
      type: 'file',
      path: f.path,
      name: '@' + basename(f.path),
      desc: f.path,
    }));
    pal.items = skills.concat(files);
  }

  function openPalette(kind, query, start, end) {
    const pal = {
      kind, query, index: 0,
      start: start ?? 0, end: end ?? 0,
      items: [], files: [],
    };
    if (kind === 'command') {
      // v0.7.11-web23: o menu "/" lista TODOS os comandos do OpenCode —
      // os do agente (motor) e os nativos da barra da TUI, traduzidos pelo
      // plugin ``ufvai.pt`` e agrupados pela categoria.
      const q = String(query || '').toLowerCase();
      pal.items = state.commands
        .filter((c) => {
          if (!q) return true;
          return [c.name, c.title, c.native, ...(c.aliases || [])]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(q));
        })
        .map((c) => ({
          group: c.group || t('palette.commands'),
          type: 'command',
          name: '/' + c.name,
          desc: c.description || c.title || '',
          action: c.action || '',
          scope: c.scope || 'motor',
          native: c.native || c.name,
        }));
    } else {
      rebuildMentionItems(pal);
    }
    state.palette = pal;
    $('#palette').hidden = false;
    $('#palette-head').textContent = kind === 'command'
      ? `${t('palette.commands')} — “/${query}”`
      : `${t('palette.skills')} · ${t('palette.files')} — “@${query}”`;
    renderPalette();
    if (kind !== 'command') searchFiles(query);
  }

  function renderPalette() {
    const box = $('#palette-list');
    box.innerHTML = '';
    const pal = state.palette;
    if (!pal) return;
    if (!pal.items.length) {
      box.appendChild(el('div', 'palette-group', pal.loading ? '…' : t('palette.noResults')));
      return;
    }
    const groups = new Map();
    pal.items.forEach((item, index) => {
      if (!groups.has(item.group)) groups.set(item.group, []);
      groups.get(item.group).push({ item, index });
    });
    groups.forEach((entries, group) => {
      box.appendChild(el('div', 'palette-group', String(group).toUpperCase()));
      entries.forEach(({ item, index }) => {
        const node = el('button', 'palette-item' + (index === pal.index ? ' active' : ''));
        node.type = 'button';
        node.appendChild(el('span', 'p-name', item.name));
        if (item.scope === 'tui') {
          // v0.7.11-web23: sinaliza os comandos que só existem no terminal
          node.appendChild(el('span', 'p-badge', 'TUI'));
        }
        node.appendChild(el('span', 'p-desc', item.desc || ''));
        node.addEventListener('click', () => { pal.index = index; choosePalette(); });
        box.appendChild(node);
      });
    });
  }

  async function searchFiles(query) {
    const pal = state.palette;
    if (!pal || pal.kind === 'command') return;
    pal.loading = true;
    renderPalette();
    try {
      const dir = (state.sessions[0] || {}).directory || '';
      const data = await apiGet(`/files?query=${encodeURIComponent(query)}&directory=${encodeURIComponent(dir)}`);
      if (!state.palette || state.palette.kind === 'command') return;
      state.palette.files = data.files || [];
      state.palette.loading = false;
      rebuildMentionItems(state.palette);
      renderPalette();
    } catch (e) {
      if (state.palette) {
        state.palette.loading = false;
        state.palette.files = [];
        rebuildMentionItems(state.palette);
        renderPalette();
      }
    }
  }

  function replaceRange(start, end, text) {
    const input = $('#input');
    input.value = input.value.slice(0, start) + text + input.value.slice(end);
    const pos = start + text.length;
    input.setSelectionRange(pos, pos);
    input.focus();
    autoGrow();
  }

  async function choosePalette() {
    const pal = state.palette;
    if (!pal) return;
    const item = pal.items[pal.index];
    if (!item) return;

    if (item.type === 'command') {
      // v0.7.11-web23: comando nativo com ação na web → executa; comando
      // só do terminal → pede a troca para a interface do terminal (que
      // roda na moldura ao lado); comando de agente → insere o texto.
      if (item.action) {
        closePalette();
        runCommandAction(item.action);
        return;
      }
      if (item.scope === 'tui') {
        closePalette();
        showTerminalForCommand(item.native);
        return;
      }
      replaceRange(pal.start, pal.end, `${item.name} `);
      closePalette();
      return;
    }

    if (item.type === 'skill') {
      // menção de habilidade: "@id" no texto + anexo em `skills` do prompt
      const text = `@${item.id}`;
      replaceRange(pal.start, pal.end, `${text} `);
      state.pendingSkills = state.pendingSkills.filter((s) => s.id !== item.id);
      state.pendingSkills.push({
        id: item.id,
        mention: { start: pal.start, end: pal.start + text.length, text },
      });
      closePalette();
      return;
    }

    // arquivo do projeto: anexa (o servidor lê e devolve o data URI)
    const dir = (state.sessions[0] || {}).directory || '';
    closePalette();
    replaceRange(pal.start, pal.end, `@${basename(item.path)} `);
    try {
      const data = await apiPost('/file', { path: item.path, directory: dir });
      const file = data.file || {};
      state.attachments.push({ name: file.name || basename(item.path), uri: file.uri, mime: '' });
      renderAttachments();
    } catch (e) {
      toast(`não foi possível anexar ${item.path}`, 'err');
    }
  }

  function movePalette(delta) {
    const pal = state.palette;
    if (!pal || !pal.items.length) return;
    pal.index = (pal.index + delta + pal.items.length) % pal.items.length;
    renderPalette();
  }

  /* ── ações dos comandos nativos ────────────────────────────────────── */

  /** Executa no web o equivalente de um comando nativo da TUI. */
  async function runCommandAction(action) {
    switch (action) {
      case 'new-session': await newSession(); return;
      case 'rename-session': renameSession(); return;
      case 'fork-session': await forkSession(); return;
      case 'compact-session': await compactSession(); return;
      case 'background-session': await backgroundSession(); return;
      case 'copy-session-link': await copySessionLink(); return;
      case 'open-models': openModels(); return;
      case 'open-variants': openVariants(); return;
      case 'open-agents': openAgents(); return;
      case 'open-skills': openSkillPalette(); return;
      case 'open-settings': openSettings('geral'); return;
      case 'open-shortcuts': openSettings('atalhos'); return;
      case 'toggle-theme':
        applyTheme(currentTheme() === 'pesquisai-light' ? 'pesquisai' : 'pesquisai-light');
        return;
      case 'toggle-terminal': showTerminalForCommand(''); return;
      default: return;
    }
  }

  /** Abre a paleta de habilidades (``@``). */
  function openSkillPalette() {
    const input = $('#input');
    input.focus();
    const pos = input.selectionStart ?? input.value.length;
    input.value = `${input.value.slice(0, pos)}@${input.value.slice(pos)}`;
    input.setSelectionRange(pos + 1, pos + 1);
    const trig = triggerAtCaret();
    if (trig) openPalette(trig.kind, trig.query, trig.start, trig.end);
    autoGrow();
  }

  /** Copia o link da sessão atual. */
  async function copySessionLink() {
    const url = `${location.origin}${location.pathname}#${state.sessionId}`;
    try {
      await navigator.clipboard.writeText(url);
      toast(t('session.copy'));
    } catch (e) {
      toast(t('tool.copyFail'), 'err');
    }
  }

  /**
   * Comando que só existe no terminal (TUI): pede ao wrapper que mostre a
   * moldura do terminal — ele fica ao lado da web, no mesmo ambiente.
   */
  function showTerminalForCommand(command) {
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({
          type: 'ufvai-show-terminal',
          command: command ? `/${command}` : '',
        }, '*');
      }
    } catch (e) { /* cross-origin bloqueado */ }
    toast(t('palette.terminalOnly'));
  }

  /* ── seletor de modelo ────────────────────────────────────────────── */

  function modelMeta(model) {
    return model.context ? `${Math.round(model.context / 1000)}k` : '';
  }

  function renderModelList(filter) {
    const list = $('#model-list');
    list.innerHTML = '';
    const needle = (filter || '').trim().toLowerCase();
    const groups = new Map();
    state.models.forEach((model) => {
      if (needle) {
        const hay = `${model.name} ${model.id} ${model.providerID}`.toLowerCase();
        if (!hay.includes(needle)) return;
      }
      if (!groups.has(model.providerID)) groups.set(model.providerID, []);
      groups.get(model.providerID).push(model);
    });

    const providerMeta = new Map((state.providers || []).map((p) => [p.id, p]));
    let shown = 0;
    groups.forEach((models, providerID) => {
      const meta = providerMeta.get(providerID) || {};
      const head = el('div', 'model-group');
      head.textContent = `${meta.name || providerID} · ${models.length}`;
      list.appendChild(head);
      models.sort((a, b) => (b.available - a.available) || a.name.localeCompare(b.name));
      models.forEach((model) => {
        const item = el('button', 'model-item' + (model.id === state.model.id && model.providerID === state.model.providerID ? ' current' : ''));
        item.type = 'button';
        if (!model.available) item.classList.add('unavailable');
        const name = el('div', 'm-name');
        name.appendChild(document.createTextNode(model.name));
        const sub = el('small');
        sub.textContent = model.id;
        name.appendChild(sub);
        item.appendChild(name);
        if (model.cost && model.cost.free) item.appendChild(el('span', 'badge free', 'grátis'));
        if (!model.available) item.appendChild(el('span', 'badge nokey', 'sem chave'));
        item.appendChild(el('span', 'm-meta', modelMeta(model)));
        item.addEventListener('click', () => pickModel(model));
        list.appendChild(item);
        shown++;
      });
    });

    if (!shown) list.appendChild(el('div', 'model-group', 'nenhum modelo encontrado'));
    $('#model-foot').textContent = state.models.length
      ? `${state.models.length} modelos · ${state.models.filter((m) => m.available).length} com provedor configurado`
      : 'catálogo vazio — o motor ainda está subindo';
  }

  function openModels() {
    $('#model-modal').hidden = false;
    $('#model-search').value = '';
    renderModelList('');
    $('#model-search').focus();
  }

  async function pickModel(model) {
    if (!state.sessionId) { await newSession(); }
    try {
      await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/model`, {
        model: { id: model.id, providerID: model.providerID },
      });
      applyModel({ id: model.id, providerID: model.providerID, variant: '' });
      const row = currentSession();
      if (row) { row.model = { ...state.model }; renderSessions(); }
      $('#model-modal').hidden = true;
      toast(`modelo: ${model.name}`);
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  async function pickVariant(variant) {
    if (!state.sessionId || !state.model.id) return;
    try {
      await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/model`, {
        model: {
          id: state.model.id,
          providerID: state.model.providerID,
          ...(variant ? { variant } : {}),
        },
      });
      applyModel({ ...state.model, variant });
      toast(variant ? `variante: ${variant}` : 'variante: padrão');
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  function openVariants() {
    const entry = currentModelEntry();
    const variants = (entry && entry.variants) || [];
    if (!variants.length) {
      toast('este modelo não tem variantes');
      return;
    }
    const list = $('#session-actions');
    list.innerHTML = '';
    $('#session-modal-title').textContent = 'Variante do modelo';
    const head = el('div', 'model-group', `variantes de ${entry.name}`);
    list.appendChild(head);
    const make = (label, value) => {
      const item = el('button', 'model-item' + (state.model.variant === value ? ' current' : ''));
      item.type = 'button';
      item.appendChild(el('div', 'm-name', label));
      item.addEventListener('click', async () => {
        $('#session-modal').hidden = true;
        await pickVariant(value);
      });
      list.appendChild(item);
    };
    make('padrão', '');
    variants.forEach((v) => make(v, v));
    $('#session-modal').hidden = false;
  }

  /* ── agente (somente UFVAI) ───────────────────────────────────────── */

  function openAgents() {
    // O motor expõe rotinas internas (general, explore, compaction…); a
    // interface do UFVAI mostra **apenas o UFVAI** — abrir aqui leva aos
    // ajustes do agente.
    openSettings('agente');
  }

  /* ── ajustes ──────────────────────────────────────────────────────── */

  function switchRow(label, key, onChange) {
    const r = el('div', 'setting-row');
    r.appendChild(el('div', 's-label', label));
    const sw = el('button', 'switch' + (state.prefs[key] ? ' on' : ''));
    sw.type = 'button';
    sw.setAttribute('role', 'switch');
    sw.setAttribute('aria-checked', state.prefs[key] ? 'true' : 'false');
    sw.setAttribute('aria-label', label);
    sw.addEventListener('click', () => {
      state.prefs[key] = !state.prefs[key];
      sw.classList.toggle('on', state.prefs[key]);
      sw.setAttribute('aria-checked', state.prefs[key] ? 'true' : 'false');
      savePrefs();
      if (onChange) onChange();
    });
    r.appendChild(sw);
    return r;
  }

  function row(label, value) {
    const r = el('div', 'setting-row');
    r.appendChild(el('div', 's-label', label));
    r.appendChild(el('div', 's-value', value));
    return r;
  }

  function renderSettings() {
    const pane = $('#settings-pane');
    pane.innerHTML = '';
    const tab = state.settingsTab;

    if (tab === 'geral') {
      pane.appendChild(el('h3', null, t('settings.appearance')));
      pane.appendChild(row(t('settings.theme'), currentTheme() === 'pesquisai-light' ? 'claro' : 'escuro'));
      pane.appendChild(el('p', null, t('settings.themeNote')));
      pane.appendChild(row(t('settings.language'), (state.locale || 'pt-BR').toUpperCase()));
      pane.appendChild(el('p', null, t('settings.languageNote')));

      pane.appendChild(el('h3', null, t('settings.display')));
      pane.appendChild(el('p', null, t('settings.displayNote')));
      pane.appendChild(switchRow(t('settings.expandReasoning'), 'expandReasoning',
        () => { renderMessages(); }));
      pane.appendChild(switchRow(t('settings.expandTools'), 'expandTools',
        () => { renderMessages(); }));
      pane.appendChild(el('p', null, t('settings.expandAllNote')));
      const actions = el('div', 'setting-actions');
      const bAll = el('button', 'btn', t('tool.expandAll'));
      bAll.addEventListener('click', () => {
        setAllExpanded(true);
        renderSettings();
      });
      const bNone = el('button', 'btn', t('tool.collapseAll'));
      bNone.addEventListener('click', () => {
        setAllExpanded(false);
        renderSettings();
      });
      actions.appendChild(bAll);
      actions.appendChild(bNone);
      pane.appendChild(actions);

      pane.appendChild(el('h3', null, t('settings.engine')));
      pane.appendChild(row(t('settings.version'), (state.engine && state.engine.version) || '—'));
      pane.appendChild(row(t('settings.directory'), state.directory || '—'));
      pane.appendChild(row(t('settings.modelsCount'), String(state.models.length)));
      pane.appendChild(row(t('settings.providers'), String((state.providers || []).length)));
    }

    if (tab === 'modelo') {
      pane.appendChild(el('h3', null, t('settings.modelSession')));
      pane.appendChild(row(t('settings.current'), state.model.id ? `${state.model.id} · ${state.model.providerID}` : '—'));
      pane.appendChild(row(t('settings.variantRow'), state.model.variant || t('settings.default')));
      const actions = el('div', 'setting-actions');
      const b = el('button', 'btn primary', t('settings.chooseModel'));
      b.addEventListener('click', () => { $('#settings-modal').hidden = true; openModels(); });
      actions.appendChild(b);
      pane.appendChild(actions);
      pane.appendChild(el('h3', null, t('settings.providersTitle')));
      const list = el('div', 'setting-list');
      (state.providers || []).forEach((p) => {
        const item = el('div', 'setting-item');
        item.appendChild(el('b', null, p.name || p.id));
        item.appendChild(el('span', null,
          `${p.models} modelos · ${p.available ? t('settings.providerOk') : t('settings.providerNoKey')}`));
        list.appendChild(item);
      });
      pane.appendChild(list);
    }

    if (tab === 'agente') {
      pane.appendChild(el('h3', null, t('settings.agent')));
      pane.appendChild(el('p', null, t('settings.agentNote')));
      const list = el('div', 'setting-list');
      state.agents.forEach((a) => {
        const item = el('div', 'setting-item');
        item.appendChild(el('b', null, a.name || a.id));
        item.appendChild(el('span', null,
          [a.description, a.model && a.model.id ? `modelo: ${a.model.id}` : ''].filter(Boolean).join(' · ')));
        list.appendChild(item);
      });
      pane.appendChild(list);
    }

    if (tab === 'comandos') {
      pane.appendChild(el('h3', null, t('palette.commands')));
      pane.appendChild(el('p', null, t('settings.commandsNote')));
      const list = el('div', 'setting-list');
      state.commands.forEach((c) => {
        const item = el('div', 'setting-item');
        item.appendChild(el('b', null, '/' + c.name));
        item.appendChild(el('span', null, [c.title, c.description].filter(Boolean).join(' — ')));
        list.appendChild(item);
      });
      pane.appendChild(list);
    }

    if (tab === 'habilidades') {
      pane.appendChild(el('h3', null, t('palette.skills')));
      const list = el('div', 'setting-list');
      if (!state.skills.length) {
        list.appendChild(el('div', 'setting-item', t('settings.skillsNone')));
      }
      state.skills.forEach((s) => {
        const item = el('div', 'setting-item');
        item.appendChild(el('b', null, s.name || s.id));
        item.appendChild(el('span', null, s.description || ''));
        list.appendChild(item);
      });
      pane.appendChild(list);
    }

    if (tab === 'sessao') {
      const s = currentSession();
      pane.appendChild(el('h3', null, t('settings.sessionCurrent')));
      if (!s) {
        pane.appendChild(el('p', null, t('warn.noSession')));
      } else {
        pane.appendChild(row(t('settings.title'), s.title || s.id));
        pane.appendChild(row(t('settings.id'), s.id));
        pane.appendChild(row(t('settings.agent'), s.agent || 'UFVAI'));
        pane.appendChild(row(t('settings.modelRow'), s.model && s.model.id ? `${s.model.id} · ${s.model.providerID}` : '—'));
        pane.appendChild(row(t('settings.created'), new Date(s.created).toLocaleString('pt-BR')));
        pane.appendChild(row(t('settings.updated'), new Date(s.updated).toLocaleString('pt-BR')));
        const tokens = s.tokens || {};
        pane.appendChild(row(t('settings.tokens'), `${tokens.input || 0} entrada · ${tokens.output || 0} saída · ${tokens.reasoning || 0} raciocínio`));
        pane.appendChild(row(t('settings.cost'), `$${Number(s.cost || 0).toFixed(4)}`));
        if (state.usage && state.usage.limit) {
          pane.appendChild(row(t('top.context'),
            `${Math.round(state.usage.used / 1000)}k / ${Math.round(state.usage.limit / 1000)}k (${state.usage.percent}%)`));
        }
        pane.appendChild(row(t('settings.directory'), s.directory || '—'));
      }
      const actions = el('div', 'setting-actions');
      const b1 = el('button', 'btn', t('settings.showContext'));
      b1.addEventListener('click', showContext);
      const b2 = el('button', 'btn', t('settings.duplicateSession'));
      b2.addEventListener('click', forkSession);
      const b3 = el('button', 'btn', t('settings.compact'));
      b3.addEventListener('click', compactSession);
      actions.appendChild(b1); actions.appendChild(b2); actions.appendChild(b3);
      pane.appendChild(actions);
    }

    if (tab === 'autosave') {
      // v0.7.11-web25: a configuração de autosave vive no WRAPPER (é o que
      // agenda o salvamento). A web lê e escreve por `postMessage`.
      const cfg = state.autosave || {};
      pane.appendChild(el('h3', null, t('settings.tab.autosave')));
      pane.appendChild(el('p', null, t('settings.autosaveNote')));
      pane.appendChild(switchRow(t('settings.autosaveEnabled'), 'autosaveEnabled', async () => {
        await pushAutosave();
      }));
      const interval = el('div', 'setting-row');
      interval.appendChild(el('span', 's-label', t('settings.autosaveInterval')));
      const number = document.createElement('input');
      number.type = 'number';
      number.min = '1';
      number.max = '240';
      number.className = 'num-input';
      number.value = String(cfg.intervalMin || 10);
      number.addEventListener('change', async () => {
        const min = Math.max(1, parseInt(number.value, 10) || 10);
        number.value = String(min);
        if (state.autosave) state.autosave.intervalMin = min;
        await pushAutosave();
      });
      interval.appendChild(number);
      interval.appendChild(el('span', 's-value', t('settings.minutes')));
      pane.appendChild(interval);

      pane.appendChild(el('h3', null, t('settings.autosaveScope')));
      const scopeList = el('div', 'scope-list');
      [['active', t('settings.scopeActive')], ['all', t('settings.scopeAll')],
       ['selected', t('settings.scopeSelected')]].forEach(([value, label]) => {
        const opt = el('button', 'scope-opt' + ((cfg.scope || 'active') === value ? ' on' : ''),
          label);
        opt.type = 'button';
        opt.addEventListener('click', async () => {
          state.autosave.scope = value;
          renderSettings();
          await pushAutosave();
        });
        scopeList.appendChild(opt);
      });
      pane.appendChild(scopeList);

      if ((cfg.scope || 'active') === 'selected') {
        pane.appendChild(el('h3', null, t('settings.autosaveSessions')));
        const list = el('div', 'setting-list');
        const selected = new Set(cfg.selectedIds || []);
        (cfg.sessions || []).forEach((s) => {
          const item = el('label', 'setting-item');
          const box = document.createElement('input');
          box.type = 'checkbox';
          box.checked = selected.has(s.id);
          box.addEventListener('change', async () => {
            const set = new Set(state.autosave.selectedIds || []);
            if (box.checked) set.add(s.id); else set.delete(s.id);
            state.autosave.selectedIds = [...set];
            await pushAutosave();
          });
          item.appendChild(box);
          item.appendChild(el('span', null, s.title || s.id));
          list.appendChild(item);
        });
        if (!state.autosave.sessions || !state.autosave.sessions.length) {
          list.appendChild(el('div', 'setting-item', t('warn.noSession')));
        }
        pane.appendChild(list);
      }
      pane.appendChild(row(t('settings.autosaveState'), cfg.known
        ? t('settings.autosaveConnected') : t('settings.autosaveStandalone')));
    }

    if (tab === 'atalhos') {
      pane.appendChild(el('h3', null, t('settings.shortcuts')));
      pane.appendChild(el('p', null, t('settings.shortcutHint')));
      const atalhos = [
        ['Enter', t('key.send')],
        ['Shift+Enter', t('key.newline')],
        ['/', t('key.commands')],
        ['@', t('key.mention')],
        ['Ctrl+Shift+A', t('key.expandAll')],
        ['Ctrl+B', t('key.background')],
        ['Ctrl+\\', t('key.toggleSidebar')],
        ['Ctrl+U', t('key.attach')],
        ['Esc', t('key.interrupt')],
        ['Ctrl+Shift+R', t('key.close')],
      ];
      atalhos.forEach(([k, d]) => {
        const r = el('div', 'shortcut-row');
        r.appendChild(el('span', null, d));
        const kbd = el('kbd', null, k);
        r.appendChild(kbd);
        pane.appendChild(r);
      });
    }

    if (tab === 'sobre') {
      // v0.7.11-web25: ficha real do UFVAI (fonte: /api/ufvai/about →
      // pesquisai/__version__.py), no lugar do texto genérico.
      const about = state.about || {};
      const card = el('div', 'about');
      const logo = el('div', 'about-logo');
      const img = document.createElement('img');
      img.src = 'assets/logo.svg';
      img.alt = 'UFVAI';
      logo.appendChild(img);
      card.appendChild(logo);
      card.appendChild(el('h3', 'about-name', 'UFVAI — Universidade Federal de Viçosa'));
      card.appendChild(el('p', 'about-tag', t('app.tagline')));
      card.appendChild(el('p', 'about-desc', t('app.description')));
      const rows = el('div', 'about-rows');
      const put = (label, value) => {
        if (!value) return;
        const r = el('div', 'about-row');
        r.appendChild(el('span', 'ar-label', label));
        r.appendChild(el('span', 'ar-value', value));
        rows.appendChild(r);
      };
      put(t('about.version'), about.version || '');
      put(t('about.codename'), about.codename || '');
      put(t('about.release'), about.release_date || '');
      put(t('about.author'), about.author || '');
      put(t('about.email'), about.email || '');
      put(t('about.institution'), about.institution || '');
      put(t('about.registry'), about.registry || '');
      put(t('about.license'), about.license ? `MIT — ${about.license}` : '');
      put(t('about.languages'), (about.languages || '').replace(/_/g, '-'));
      put(t('about.agencies'), about.agencies || '');
      card.appendChild(rows);
      const links = el('div', 'about-links');
      const gh = el('a', 'about-link', 'GitHub — gustavobraga-byte/PesquisAI');
      gh.href = 'https://github.com/gustavobraga-byte/PesquisAI';
      gh.target = '_blank';
      gh.rel = 'noopener';
      links.appendChild(gh);
      const mail = el('a', 'about-link', about.email || '');
      if (about.email) {
        mail.href = `mailto:${about.email}`;
        links.appendChild(mail);
      }
      card.appendChild(links);
      pane.appendChild(card);
    }
  }

  function openSettings(tab) {
    state.settingsTab = tab || state.settingsTab;
    state.settingsOpen = true;
    document.querySelectorAll('#settings-tabs .tab').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tab === state.settingsTab);
    });
    renderSettings();
    $('#settings-modal').hidden = false;
  }

  async function showContext() {
    if (!state.sessionId) return;
    try {
      const data = await apiGet(`/sessions/${encodeURIComponent(state.sessionId)}/context`);
      const list = $('#session-actions');
      list.innerHTML = '';
      const head = el('div', 'model-group', 'contexto da sessão');
      list.appendChild(head);
      const info = data.data || data;
      const item = el('div', 'setting-item');
      item.appendChild(el('b', null, 'Resumo'));
      item.appendChild(el('span', null, JSON.stringify(info).slice(0, 900)));
      list.appendChild(item);
      $('#session-modal').hidden = false;
    } catch (e) {
      toast('não foi possível ler o contexto', 'err');
    }
  }

  async function forkSession() {
    if (!state.sessionId) return;
    try {
      const data = await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/fork`, {});
      await refreshSessions();
      const row = data.session || {};
      if (row.id) {
        state.sessions.unshift(row);
        renderSessions();
        await openSession(row.id, { focus: true });
      }
      $('#session-modal').hidden = true;
      $('#settings-modal').hidden = true;
      toast('sessão duplicada');
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  async function compactSession() {
    if (!state.sessionId) return;
    try {
      await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/compact`, {});
      $('#session-modal').hidden = true;
      $('#settings-modal').hidden = true;
      await openSession(state.sessionId);
      toast('histórico compactado');
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  async function renameSession(sid) {
    const target = sid || state.sessionId;
    if (!target) return;
    const row = state.sessions.find((s) => s.id === target) || currentSession();
    const title = await askText(
      t('session.rename'),
      row ? sessionTitle(row) : '',
      t('session.renamePrompt'),
      t('session.rename'),
    );
    if (!title || !title.trim()) return;
    try {
      await apiPost(`/sessions/${encodeURIComponent(target)}/rename`, { title: title.trim() });
      const item = state.sessions.find((s) => s.id === target);
      if (item) item.title = title.trim();
      if (target === state.sessionId) $('#session-title').textContent = title.trim();
      renderSessions();
      toast(t('session.done'));
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  async function backgroundSession() {
    if (!state.sessionId) return;
    try {
      await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/background`, {});
      toast('execução movida para segundo plano');
      $('#session-modal').hidden = true;
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  function openSessionMenu() {
    const list = $('#session-actions');
    list.innerHTML = '';
    $('#session-modal-title').textContent = t('modal.session');
    const head = el('div', 'model-group', t('sidebar.sessions'));
    list.appendChild(head);
    const actions = [
      [t('session.rename'), renameSession],
      [t('session.fork'), forkSession],
      [t('session.compact'), compactSession],
      [t('session.context'), showContext],
      [t('session.background'), backgroundSession],
      [t('session.finalize'), askFinalize],
    ];
    actions.forEach(([label, fn]) => {
      const item = el('button', 'model-item');
      item.type = 'button';
      item.appendChild(el('div', 'm-name', label));
      item.addEventListener('click', () => { $('#session-modal').hidden = true; fn(); });
      list.appendChild(item);
    });
    $('#session-modal').hidden = false;
  }

  /* ── foco TUI → web ───────────────────────────────────────────────── */

  /**
   * v0.7.11-web24: a web seguia a sessão do TERMINAL a cada 2,5 s — e como o
   * ttyd fica em outra sessão, a web **puxava o usuário para outra conversa**
   * no meio do turno (aí a mensagem "parava" e o aviso de execução sumia).
   *
   * Agora a web só segue o foco do terminal quando o **terminal é a vista
   * visível** (o wrapper avisa por `postMessage {type:'ufvai-view'}`) e nunca
   * durante uma execução.
   */
  function pollFocus() {
    if (state.view === 'web') return;
    if (state.running) return;
    apiGet('/focus')
      .then((focus) => {
        if (!focus || !focus.sid) return;
        if (focus.source !== 'tui') return;
        if (focus.sid === state.sessionId) return;
        if (Date.now() - state.manualSwitch < 4000) return;
        openSession(focus.sid);
      })
      .catch(() => {});
  }

  /* ── inicialização ────────────────────────────────────────────────── */

  async function boot() {
    loadPrefs();
    applyTheme(currentTheme());
    // v0.7.11-web23: i18n — dicionário local + idioma do wrapper/motor
    await loadI18n();
    const cookieLang = localeFromCookie();
    if (cookieLang) applyLocale(cookieLang);
    let saved = null;
    try { saved = localStorage.getItem('ufvai_web_lang'); } catch (e) { /* ignora */ }
    if (saved && !cookieLang) applyLocale(saved);
    try {
      const loc = await apiGet('/locale');
      if (loc && loc.lang && !cookieLang) applyLocale(loc.lang);
    } catch (e) { /* segue com o idioma salvo */ }
    try {
      if (localStorage.getItem('ufvai_side_hidden') === '1') {
        document.body.classList.add('side-hidden');
        $('#menu-btn').classList.add('on');
      }
    } catch (e) { /* ignora */ }

    let data;
    try {
      data = await apiGet('/bootstrap');
    } catch (e) {
      $('#engine-dot').className = 'dot bad';
      $('#engine-text').textContent = 'sem conexão';
      toast('não foi possível falar com o motor', 'err');
      return;
    }

    state.engine = data.engine || {};
    state.directory = data.directory || '';
    state.agents = data.agents || [];
    state.sessions = data.sessions || [];
    state.active = data.active || {};
    state.models = (data.models && data.models.models) || [];
    state.providers = (data.models && data.models.providers) || [];

    $('#engine-sub').textContent = state.engine.version
      ? `motor ${state.engine.version} · ${state.models.length} modelos`
      : '';
    $('#engine-dot').className = 'dot ok';
    $('#engine-text').textContent = 'motor conectado';

    const preferred = state.agents.find((a) => a.id.toUpperCase() === 'UFVAI');
    state.agent = (preferred || state.agents[0] || {}).id || 'UFVAI';
    $('#agent-label').textContent = state.agent;

    // comandos e habilidades (menus "/" e "@")
    try {
      const extra = await apiGet(`/commands?lang=${encodeURIComponent(state.locale)}`);
      state.commands = extra.commands || [];
      state.skills = extra.skills || [];
    } catch (e) { /* segue sem os menus */ }

    renderSessions();
    renderModelList('');
    renderAttachments();

    const hash = (location.hash || '').replace(/^#/, '');
    const target = (data.current && data.current.id) || (hash || (state.sessions[0] || {}).id);
    if (target) {
      await openSession(target);
    } else {
      await newSession();
    }

    // v0.7.11-web25: rolagem automática — o `ResizeObserver` garante que a
    // conversa **acompanhe** o conteúdo: texto que chega em pedaços, blocos
    // de ferramenta, anexos e o rodapé das mensagens mudam a altura depois do
    // último render (a rolagem ficava alguns pixels acima do fim).
    if (window.ResizeObserver) {
      const observer = new ResizeObserver(() => {
        if (!state.autoScroll) return;
        // logo após o usuário rolar para cima, não puxa a conversa de volta
        if (Date.now() - lastUserScrollUp < 1500) return;
        scrollToEnd(false);
      });
      observer.observe($('#messages'));
    }

    connectEvents();
    setInterval(refreshSessions, 20000);
    setInterval(pollFocus, 2500);
    setInterval(refreshUsage, 30000);
    // v0.7.11-web25: heartbeat — detecta a queda do ambiente mesmo sem SSE
    setInterval(heartbeat, 10000);
    // v0.7.11-web25: ficha do UFVAI e configuração de autosave
    try {
      const about = await apiGet('/about');
      state.about = about || {};
    } catch (e) { /* segue sem a ficha */ }
    askAutosave();
  }

  /* ── eventos da interface ─────────────────────────────────────────── */

  function autoGrow() {
    const input = $('#input');
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 220) + 'px';
  }

  function bind() {
    const input = $('#input');
    input.addEventListener('input', () => {
      autoGrow();
      const trig = triggerAtCaret();
      if (!trig) { closePalette(); return; }
      if (state.palette && state.palette.kind === trig.kind && state.palette.query === trig.query) {
        // mesma consulta: só atualiza o intervalo de substituição
        state.palette.start = trig.start;
        state.palette.end = trig.end;
        return;
      }
      openPalette(trig.kind, trig.query, trig.start, trig.end);
    });
    input.addEventListener('blur', () => setTimeout(() => { if (!state.palette) closePalette(); }, 150));
    input.addEventListener('keydown', (event) => {
      if (state.palette) {
        if (event.key === 'ArrowDown') { event.preventDefault(); movePalette(1); return; }
        if (event.key === 'ArrowUp') { event.preventDefault(); movePalette(-1); return; }
        if (event.key === 'Enter' || event.key === 'Tab') { event.preventDefault(); choosePalette(); return; }
        if (event.key === 'Escape') { event.preventDefault(); closePalette(); return; }
      }
      if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        send();
      }
    });

    $('#send-btn').addEventListener('click', send);
    $('#stop-btn').addEventListener('click', stop);
    $('#new-session').addEventListener('click', newSession);
    $('#refresh-btn').addEventListener('click', async () => {
      await refreshSessions();
      toast('atualizado');
    });
    $('#session-search').addEventListener('input', renderSessions);

    $('#attach-btn').addEventListener('click', () => $('#file-input').click());
    $('#file-input').addEventListener('change', (event) => {
      attachLocalFiles([...event.target.files]);
      event.target.value = '';
    });

    $('#model-pill').addEventListener('click', openModels);
    $('#model-close').addEventListener('click', () => { $('#model-modal').hidden = true; });
    $('#model-search').addEventListener('input', (e) => renderModelList(e.target.value));

    $('#agent-pill').addEventListener('click', openAgents);
    $('#variant-chip').addEventListener('click', openVariants);

    $('#settings-btn').addEventListener('click', () => openSettings('geral'));
    $('#settings-close').addEventListener('click', () => { $('#settings-modal').hidden = true; });
    document.querySelectorAll('#settings-tabs .tab').forEach((btn) => {
      btn.addEventListener('click', () => openSettings(btn.dataset.tab));
    });

    $('#session-title').addEventListener('dblclick', () => renameSession());
    $('#session-menu-btn').addEventListener('click', openSessionMenu);
    $('#session-close').addEventListener('click', () => { $('#session-modal').hidden = true; });

    // v0.7.11-web23: "expandir tudo" — abre/fecha todos os blocos já
    // renderizados (raciocínio e ferramentas).
    $('#expand-all-btn').addEventListener('click', () => {
      const anyClosed = [...document.querySelectorAll('#messages details.block')]
        .some((b) => !b.open);
      setAllExpanded(anyClosed);
    });

    // v0.7.11-web23: o botão claro/escuro foi removido da web (o do
    // cabeçalho do wrapper é a fonte da verdade).

    $('#thread').addEventListener('scroll', onThreadScroll, { passive: true });
    $('#thread').addEventListener('wheel', onScrollIntent, { passive: true });
    $('#thread').addEventListener('touchmove', onScrollIntent, { passive: true });

    // v0.7.11-web26: explorador de arquivos
    $('#explorer-btn').addEventListener('click', () => {
      if (document.body.classList.contains('explorer-open')) closeExplorer();
      else openExplorer();
    });
    $('#exp-close').addEventListener('click', closeExplorer);
    $('#exp-refresh').addEventListener('click', () => loadExplorer(state.explorerPath));
    $('#exp-up').addEventListener('click', () => {
      const path = String(state.explorerPath || '');
      const parent = path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '';
      loadExplorer(parent);
    });
    $('#jump-btn').addEventListener('click', () => {
      state.autoScroll = true;
      const thread = $('#thread');
      if (thread && thread.scrollTo) {
        thread.scrollTo({ top: thread.scrollHeight, behavior: 'smooth' });
      } else {
        scrollToEnd(true);
      }
      setTimeout(() => scrollToEnd(true), 500);
    });
    $('#dead-action').addEventListener('click', () => {
      toast(t('warn.deadAction'));
    });

    // v0.7.11-web26: confirmação de finalização da sessão
    $('#confirm-close').addEventListener('click', closeConfirm);
    $('#confirm-cancel').addEventListener('click', closeConfirm);
    $('#confirm-archive').addEventListener('click', () => finalizeSession('archive'));
    $('#confirm-delete').addEventListener('click', () => finalizeSession('delete'));

    $('#menu-btn').addEventListener('click', () => {
      // v0.7.11-web21: no desktop o botão OCULTA as sessões (a coluna
      // colapsa); no responsivo abre a gaveta.
      const mobile = window.matchMedia('(max-width: 900px)').matches;
      if (mobile) {
        document.body.classList.toggle('side-open');
        $('#scrim').hidden = !document.body.classList.contains('side-open');
      } else {
        const hidden = document.body.classList.toggle('side-hidden');
        try { localStorage.setItem('ufvai_side_hidden', hidden ? '1' : '0'); } catch (e) {}
        $('#menu-btn').classList.toggle('on', hidden);
        $('#menu-btn').title = hidden ? t('top.sessions') : t('top.sessions');
      }
    });
    // v0.7.11-web24: o "✕" do quadrado de sessões foi removido (não
    // funcionava); a gaveta fecha pelo botão ☰ ou tocando fora.
    $('#scrim').addEventListener('click', () => {
      document.body.classList.remove('side-open');
      $('#scrim').hidden = true;
    });

    // v0.7.11-web24: modal de entrada (substitui prompt(), bloqueado em iframe)
    $('#prompt-ok').addEventListener('click', () => {
      closeAsk($('#prompt-input').value);
    });
    $('#prompt-cancel').addEventListener('click', () => closeAsk(null));
    $('#prompt-close').addEventListener('click', () => closeAsk(null));
    $('#prompt-input').addEventListener('keydown', (event) => {
      if (event.key === 'Enter') { event.preventDefault(); closeAsk($('#prompt-input').value); }
      if (event.key === 'Escape') { event.preventDefault(); closeAsk(null); }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closePalette();
        $('#model-modal').hidden = true;
        $('#settings-modal').hidden = true;
        $('#session-modal').hidden = true;
      }
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        $('#session-search').focus();
      }
      if ((event.ctrlKey || event.metaKey) && event.key === 'l') {
        event.preventDefault();
        $('#input').focus();
      }
      if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
        event.preventDefault();
        backgroundSession();
      }
      // v0.7.11-web23: expandir/recolher tudo
      if ((event.ctrlKey || event.metaKey) && event.shiftKey
          && (event.key === 'A' || event.key === 'a')) {
        event.preventDefault();
        const anyClosed = [...document.querySelectorAll('#messages details.block')]
          .some((b) => !b.open);
        setAllExpanded(anyClosed);
      }
      // v0.7.11-web23: ocultar/mostrar as sessões
      if ((event.ctrlKey || event.metaKey) && event.key === '\\') {
        event.preventDefault();
        $('#menu-btn').click();
      }
      // v0.7.11-web23: anexar arquivo
      if ((event.ctrlKey || event.metaKey) && event.key === 'u') {
        event.preventDefault();
        $('#file-input').click();
      }
    });

    window.addEventListener('beforeunload', () => {
      if (state.source) state.source.close();
    });
    // v0.7.11-web23: o placeholder muda com a largura da tela
    window.addEventListener('resize', () => {
      applyPlaceholder();
    });
  }

  bind();
  boot();

  // Handle de diagnóstico (usado pelos testes de aceitação e pelo autor
  // para depurar no console do navegador). Não expõe nada sensível.
  window.__ufvai = {
    state,
    setRunning,
    syncTail,
    renderPermission,
    replyPermission,
    loadPermissions,
    watchRun,
  };
})();

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
    usage: null,           // {used, limit, percent} — janela de contexto
    uploads: [],           // anexos já gravados em disco pelo gateway
    prefs: {
      expandReasoning: false,
      expandTools: false,
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

  function scrollToEnd(force) {
    const thread = $('#thread');
    const near = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 160;
    if (force || near) thread.scrollTop = thread.scrollHeight;
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
      const slot = { wrap, answer, text: '', reasoning: '', tools: {}, toolInputs: {}, reasoningBlock: null };
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
    $('#status-text').textContent = running ? 'Trabalhando…' : '';
  }

  /* ── eventos (SSE) ────────────────────────────────────────────────── */

  // v0.7.11-web23: se a conexão ficar caída por mais de 10 minutos, o
  // ambiente do Colab provavelmente foi encerrado (inatividade). O aviso
  // explica o que houve e lembra que o Drive está intacto.
  const DEAD_AFTER_MS = 10 * 60 * 1000;
  let downSince = 0;

  function markEngineDown() {
    const dot = $('#engine-dot');
    const text = $('#engine-text');
    if (dot) dot.className = 'dot bad';
    if (text) text.textContent = t('sidebar.reconnecting');
    if (!downSince) {
      downSince = Date.now();
      setTimeout(() => {
        if (downSince && Date.now() - downSince >= DEAD_AFTER_MS) {
          const banner = $('#engine-dead');
          if (banner) banner.hidden = false;
          if (text) text.textContent = t('sidebar.engineDead');
        }
      }, DEAD_AFTER_MS + 500);
    }
  }

  function markEngineUp() {
    downSince = 0;
    const banner = $('#engine-dead');
    if (banner) banner.hidden = true;
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
    };
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
      pane.appendChild(el('h3', null, t('settings.aboutTitle')));
      pane.appendChild(el('p', null, t('settings.aboutText')));
      pane.appendChild(row(t('settings.engine'), (state.engine && state.engine.version) || '—'));
      pane.appendChild(row(t('sidebar.sessions'), String(state.sessions.length)));
      pane.appendChild(row(t('settings.modelsCount'), String(state.models.length)));
      pane.appendChild(row(t('palette.commands'), String(state.commands.length)));
      pane.appendChild(row(t('palette.skills'), String(state.skills.length)));
      pane.appendChild(row('Endpoint', BASE + 'api/ufvai/'));
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
    const title = prompt('Novo título da sessão:', row ? sessionTitle(row) : '');
    if (!title || !title.trim()) return;
    try {
      await apiPost(`/sessions/${encodeURIComponent(target)}/rename`, { title: title.trim() });
      const item = state.sessions.find((s) => s.id === target);
      if (item) item.title = title.trim();
      if (target === state.sessionId) $('#session-title').textContent = title.trim();
      renderSessions();
      toast('sessão renomeada');
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
    $('#session-modal-title').textContent = 'Sessão';
    const head = el('div', 'model-group', 'sessão');
    list.appendChild(head);
    const actions = [
      ['Renomear…', renameSession],
      ['Duplicar (fork)', forkSession],
      ['Compactar histórico', compactSession],
      ['Ver contexto', showContext],
      ['Mover para segundo plano', backgroundSession],
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

  function pollFocus() {
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

    connectEvents();
    setInterval(refreshSessions, 20000);
    setInterval(pollFocus, 2500);
    setInterval(refreshUsage, 30000);
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

    $('#dead-action').addEventListener('click', () => {
      toast(t('warn.deadAction'));
    });

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
    $('#side-close').addEventListener('click', () => {
      document.body.classList.remove('side-open');
      $('#scrim').hidden = true;
    });
    $('#scrim').addEventListener('click', () => {
      document.body.classList.remove('side-open');
      $('#scrim').hidden = true;
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
})();

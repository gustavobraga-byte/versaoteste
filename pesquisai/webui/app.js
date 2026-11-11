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
    if (!parts.length) { pill.hidden = true; return; }
    pill.hidden = false;
    pill.textContent = parts.join(' · ');
  }

  /* ── mensagens ────────────────────────────────────────────────────── */

  const TOOL_LIMITS = { input: 2500, output: 6000 };

  function truncate(text, limit) {
    const value = String(text ?? '');
    if (value.length <= limit) return value;
    return `${value.slice(0, limit)}
… (${value.length - limit} caracteres omitidos)`;
  }

  /** Rótulo curto da ferramenta no estilo da SPA ("Write", "Shell", "Edit"). */
  function toolLabel(name) {
    const raw = String(name || 'ferramenta');
    const map = {
      shell: 'Shell', bash: 'Shell', write: 'Write', edit: 'Edit', read: 'Read',
      list: 'List', grep: 'Grep', glob: 'Glob', patch: 'Edit', todowrite: 'Todo',
      webfetch: 'Web', websearch: 'Web', task: 'Task', skill: 'Skill',
    };
    const key = raw.toLowerCase().replace(/[^a-z]/g, '');
    return map[key] || raw.charAt(0).toUpperCase() + raw.slice(1);
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
      const body = input.content || input.newString || input.new_string || '';
      const head = path ? `arquivo: ${path}` : '';
      const preview = body ? truncate(String(body), 1200) : '';
      return [head, preview].filter(Boolean).join('\n');
    }
    try {
      return truncate(JSON.stringify(input, null, 2), TOOL_LIMITS.input);
    } catch (e) {
      return truncate(String(input), TOOL_LIMITS.input);
    }
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
    node.appendChild(el('span', 'ts-label', count === 1 ? 'chamada' : 'chamadas'));
    node.appendChild(el('span', 'ts-names', names.join(' · ')));
    return node;
  }

  function textBlock(label, body, cls) {
    const details = el('details', 'block' + (cls ? ' ' + cls : ''));
    const summary = el('summary');
    summary.appendChild(el('span', null, label));
    details.appendChild(summary);
    const bodyNode = el('div', 'block-body', body || '');
    details.appendChild(bodyNode);
    details.__body = bodyNode;
    return details;
  }

  function toolBlock(name, status) {
    const details = el('details', 'block tool');
    const summary = el('summary');
    const head = el('span', 'tool-head');
    head.appendChild(el('span', 'tool-name', name || 'ferramenta'));
    const statusNode = el('span', 'status-run', status || 'executando');
    head.appendChild(statusNode);
    summary.appendChild(head);
    details.appendChild(summary);
    const body = el('div', 'block-body', '');
    details.appendChild(body);
    details.__body = body;
    details.__status = statusNode;
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
    const btn = el('button', 'mini-btn', label || 'Copiar');
    btn.type = 'button';
    btn.addEventListener('click', async () => {
      const text = getText();
      try {
        await navigator.clipboard.writeText(text);
        toast('copiado');
      } catch (e) {
        toast('não foi possível copiar', 'err');
      }
    });
    actions.appendChild(btn);
    return actions;
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
      const block = textBlock('raciocínio', message.reasoning, 'reasoning');
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
        const body = [];
        const input = formatToolInput(tool.name, tool.input);
        if (input) body.push(input);
        if (tool.output) body.push(truncate(tool.output, TOOL_LIMITS.output));
        block.__body.textContent = body.join('\n\n');
        if (tool.status === 'error') block.__status.textContent = 'erro';
        if (tool.status === 'completed') block.__status.textContent = 'concluído';
        block.open = !!state.prefs.expandTools;
        wrap.appendChild(block);
      });
    }
    if (message.error) {
      wrap.appendChild(el('div', 'msg-error', message.error));
    }
    wrap.appendChild(copyButton(() => message.text || '', 'Copiar resposta'));
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
      const slot = { wrap, answer, text: '', reasoning: '', tools: {}, reasoningBlock: null };
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
          slot.reasoningBlock = textBlock('raciocínio', '', 'reasoning');
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
          slot.reasoningBlock = textBlock('raciocínio', slot.reasoning, 'reasoning');
          slot.wrap.appendChild(slot.reasoningBlock);
        }
        scheduleRender(slot);
        break;
      }
      case 'tool.started': {
        const slot = streamSlot(ev.messageID);
        const block = toolBlock(ev.name, 'executando');
        if (ev.input !== undefined && ev.input !== null) {
          block.__body.textContent = formatToolInput(ev.name, ev.input);
        }
        slot.tools[ev.callID] = block;
        slot.wrap.appendChild(block);
        scrollToEnd(false);
        break;
      }
      case 'tool.finished': {
        const slot = streamSlot(ev.messageID);
        const block = slot.tools[ev.callID];
        if (block) {
          block.__status.textContent = ev.status === 'error' ? 'erro' : 'concluído';
          if (ev.status === 'error') block.__status.className = 'status-error';
          if (ev.output) {
            block.__body.textContent = (block.__body.textContent ? block.__body.textContent + '\n\n' : '')
              + truncate(ev.output, TOOL_LIMITS.output);
          }
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

  function connectEvents() {
    if (state.source) { state.source.close(); state.source = null; }
    const url = api(`/events${state.sessionId ? `?sid=${encodeURIComponent(state.sessionId)}` : ''}`);
    const source = new EventSource(url);
    state.source = source;
    source.onmessage = (event) => {
      try { handleEvent(JSON.parse(event.data)); } catch (e) { /* frame inválido */ }
    };
    source.onerror = () => {
      $('#engine-dot').className = 'dot bad';
      $('#engine-text').textContent = 'reconectando…';
    };
    source.onopen = () => {
      $('#engine-dot').className = 'dot ok';
      $('#engine-text').textContent = 'motor conectado';
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
    wrap.appendChild(el('div', 'bubble', text || '(anexo)'));
    if (state.attachments.length) {
      const names = state.attachments.map((a) => `📎 ${a.name}`).join('\n');
      wrap.appendChild(el('div', 'bubble-attach', names));
    }
    $('#messages').appendChild(wrap);
    $('#empty-state').hidden = true;
    scrollToEnd(true);

    const files = state.attachments.map((a) => ({
      uri: a.uri, source: { type: 'inline' }, name: a.name,
    }));
    const skills = state.pendingSkills.slice();
    state.attachments = [];
    state.pendingSkills = [];
    renderAttachments();

    try {
      await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/message`, {
        text, files, skills: skills.length ? skills : undefined,
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

  const MAX_ATTACHMENT = 5 * 1024 * 1024;

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
      const rm = el('button', null, '✕');
      rm.type = 'button';
      rm.title = 'Remover';
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

  async function attachLocalFiles(files) {
    for (const file of files) {
      if (file.size > MAX_ATTACHMENT) {
        toast(`${file.name} é maior que 5 MB — arquivo ignorado`, 'err');
        continue;
      }
      try {
        const uri = await readFileAsDataUri(file);
        state.attachments.push({
          name: file.name, size: file.size, mime: file.type || '', uri,
        });
      } catch (e) {
        toast(String(e.message || e), 'err');
      }
    }
    renderAttachments();
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
        group: 'habilidades',
        type: 'skill',
        id: s.id,
        name: '@' + s.id,
        desc: s.description || s.name || '',
      }));
    const files = (pal.files || []).map((f) => ({
      group: 'arquivos',
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
      pal.items = state.commands
        .filter((c) => !query || c.name.toLowerCase().includes(query.toLowerCase()))
        .map((c) => ({ group: 'comandos', type: 'command', name: '/' + c.name, desc: c.description || '' }));
    } else {
      rebuildMentionItems(pal);
    }
    state.palette = pal;
    $('#palette').hidden = false;
    $('#palette-head').textContent = kind === 'command'
      ? `comandos — “/${query}”`
      : `habilidades e arquivos — “@${query}”`;
    renderPalette();
    if (kind !== 'command') searchFiles(query);
  }

  function renderPalette() {
    const box = $('#palette-list');
    box.innerHTML = '';
    const pal = state.palette;
    if (!pal) return;
    if (!pal.items.length) {
      box.appendChild(el('div', 'palette-group', pal.loading ? 'procurando…' : 'nenhum item'));
      return;
    }
    const groups = new Map();
    pal.items.forEach((item, index) => {
      if (!groups.has(item.group)) groups.set(item.group, []);
      groups.get(item.group).push({ item, index });
    });
    groups.forEach((entries, group) => {
      box.appendChild(el('div', 'palette-group', group));
      entries.forEach(({ item, index }) => {
        const node = el('button', 'palette-item' + (index === pal.index ? ' active' : ''));
        node.type = 'button';
        node.appendChild(el('span', 'p-name', item.name));
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
      pane.appendChild(el('h3', null, 'Aparência e ambiente'));
      pane.appendChild(row('Tema', currentTheme() === 'pesquisai-light' ? 'claro' : 'escuro'));
      pane.appendChild(el('p', null, 'O tema também é sincronizado com o botão da interface principal (terminal ↔ web).'));
      const actions = el('div', 'setting-actions');
      const b1 = el('button', 'btn', 'Alternar tema');
      b1.addEventListener('click', () => {
        applyTheme(currentTheme() === 'pesquisai-light' ? 'pesquisai' : 'pesquisai-light');
        renderSettings();
      });
      actions.appendChild(b1);
      pane.appendChild(actions);

      pane.appendChild(el('h3', null, 'Exibição do conteúdo'));
      pane.appendChild(el('p', null,
        'Define se os blocos de raciocínio e de ferramentas aparecem abertos ou recolhidos.'));
      pane.appendChild(switchRow('Expandir raciocínio', 'expandReasoning',
        () => { renderMessages(); }));
      pane.appendChild(switchRow('Expandir ferramentas', 'expandTools',
        () => { renderMessages(); }));
      pane.appendChild(el('h3', null, 'Motor'));
      pane.appendChild(row('Versão', (state.engine && state.engine.version) || '—'));
      pane.appendChild(row('Diretório', state.directory || '—'));
      pane.appendChild(row('Modelos no catálogo', String(state.models.length)));
      pane.appendChild(row('Provedores', String((state.providers || []).length)));
    }

    if (tab === 'modelo') {
      pane.appendChild(el('h3', null, 'Modelo da sessão'));
      pane.appendChild(row('Atual', state.model.id ? `${state.model.id} · ${state.model.providerID}` : '—'));
      pane.appendChild(row('Variante', state.model.variant || 'padrão'));
      const actions = el('div', 'setting-actions');
      const b = el('button', 'btn primary', 'Escolher modelo');
      b.addEventListener('click', () => { $('#settings-modal').hidden = true; openModels(); });
      actions.appendChild(b);
      pane.appendChild(actions);
      pane.appendChild(el('h3', null, 'Provedores'));
      const list = el('div', 'setting-list');
      (state.providers || []).forEach((p) => {
        const item = el('div', 'setting-item');
        item.appendChild(el('b', null, p.name || p.id));
        item.appendChild(el('span', null,
          `${p.models} modelos · ${p.available ? 'credencial detectada' : 'chave não detectada'}`));
        list.appendChild(item);
      });
      pane.appendChild(list);
    }

    if (tab === 'agente') {
      pane.appendChild(el('h3', null, 'Agente'));
      pane.appendChild(el('p', null, 'O UFVAI é o único agente exposto: os demais são rotinas internas do motor.'));
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
      pane.appendChild(el('h3', null, 'Comandos'));
      pane.appendChild(el('p', null, 'Digite / no campo de mensagem para abrir o menu.'));
      const list = el('div', 'setting-list');
      state.commands.forEach((c) => {
        const item = el('div', 'setting-item');
        item.appendChild(el('b', null, '/' + c.name));
        item.appendChild(el('span', null, c.description || ''));
        list.appendChild(item);
      });
      pane.appendChild(list);
    }

    if (tab === 'habilidades') {
      pane.appendChild(el('h3', null, 'Habilidades'));
      const list = el('div', 'setting-list');
      if (!state.skills.length) {
        list.appendChild(el('div', 'setting-item', 'nenhuma habilidade disponível'));
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
      pane.appendChild(el('h3', null, 'Sessão atual'));
      if (!s) {
        pane.appendChild(el('p', null, 'nenhuma sessão aberta'));
      } else {
        pane.appendChild(row('Título', s.title || s.id));
        pane.appendChild(row('ID', s.id));
        pane.appendChild(row('Agente', s.agent || 'UFVAI'));
        pane.appendChild(row('Modelo', s.model && s.model.id ? `${s.model.id} · ${s.model.providerID}` : '—'));
        pane.appendChild(row('Criada', new Date(s.created).toLocaleString('pt-BR')));
        pane.appendChild(row('Atualizada', new Date(s.updated).toLocaleString('pt-BR')));
        const tokens = s.tokens || {};
        pane.appendChild(row('Tokens', `${tokens.input || 0} entrada · ${tokens.output || 0} saída · ${tokens.reasoning || 0} raciocínio`));
        pane.appendChild(row('Custo', `$${Number(s.cost || 0).toFixed(4)}`));
        pane.appendChild(row('Diretório', s.directory || '—'));
      }
      const actions = el('div', 'setting-actions');
      const b1 = el('button', 'btn', 'Ver contexto');
      b1.addEventListener('click', showContext);
      const b2 = el('button', 'btn', 'Duplicar sessão');
      b2.addEventListener('click', forkSession);
      const b3 = el('button', 'btn', 'Compactar histórico');
      b3.addEventListener('click', compactSession);
      actions.appendChild(b1); actions.appendChild(b2); actions.appendChild(b3);
      pane.appendChild(actions);
    }

    if (tab === 'atalhos') {
      pane.appendChild(el('h3', null, 'Atalhos'));
      const atalhos = [
        ['Enter', 'enviar a mensagem'],
        ['Shift+Enter', 'nova linha'],
        ['/', 'menu de comandos'],
        ['@', 'mencionar arquivo do projeto'],
        ['Ctrl+K', 'buscar sessões'],
        ['Ctrl+L', 'focar o campo de mensagem'],
        ['Ctrl+B', 'mover a execução para segundo plano'],
        ['Esc', 'fechar menus / interromper'],
        ['Ctrl+Shift+R', 'recarregar a interface'],
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
      pane.appendChild(el('h3', null, 'UFVAI · Web'));
      pane.appendChild(el('p', null,
        'Cliente próprio do UFVAI (sem a SPA do OpenCode): conversa em streaming, ' +
        'comandos, arquivos, modelo e ajustes — tudo servido pelo contrato ' +
        '/api/ufvai/* do gateway local.'));
      pane.appendChild(row('Motor', (state.engine && state.engine.version) || '—'));
      pane.appendChild(row('Sessões', String(state.sessions.length)));
      pane.appendChild(row('Modelos', String(state.models.length)));
      pane.appendChild(row('Comandos', String(state.commands.length)));
      pane.appendChild(row('Habilidades', String(state.skills.length)));
      pane.appendChild(row('Endpoint', BASE + 'api/ufvai/'));
    }
  }

  function openSettings(tab) {
    state.settingsTab = tab || state.settingsTab;
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
      const extra = await apiGet('/commands');
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

    $('#theme-btn').addEventListener('click', () => {
      applyTheme(currentTheme() === 'pesquisai-light' ? 'pesquisai' : 'pesquisai-light');
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
        $('#menu-btn').title = hidden ? 'Mostrar as sessões' : 'Ocultar as sessões';
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
    });

    window.addEventListener('beforeunload', () => {
      if (state.source) state.source.close();
    });
  }

  bind();
  boot();
})();

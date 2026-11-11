/* ==========================================================================
   UFVAI · web (webui-v1) — cliente novo (escrito do zero, sem dependências)
   --------------------------------------------------------------------------
   Contrato com o servidor: /api/ufvai/*  (ver pesquisai/webapi.py)
   Eventos: SSE em /api/ufvai/events?sid=<id>
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
    models: [],
    providers: [],
    model: { id: '', providerID: '', variant: '' },
    agent: '',
    running: false,
    stream: {},
    manualSwitch: 0,
    source: null,
  };

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
    const value = theme === 'pesquisai-light' ? 'pesquisai-light' : 'pesquisai';
    document.documentElement.setAttribute('data-theme', value);
    document.documentElement.style.colorScheme = value === 'pesquisai-light' ? 'light' : 'dark';
    try { localStorage.setItem(THEME_KEY, value); } catch (e) { /* modo restrito */ }
    try {
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute('content', value === 'pesquisai-light' ? '#f6f7f5' : '#0b0d0e');
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

  function renderSessions() {
    const list = $('#sessions');
    const filter = ($('#session-search').value || '').trim().toLowerCase();
    list.innerHTML = '';
    const rows = state.sessions.filter((row) => {
      if (!filter) return true;
      return (row.title || '').toLowerCase().includes(filter) || row.id.toLowerCase().includes(filter);
    });
    if (!rows.length) {
      const hint = el('div', 'model-group', rows.length ? 'nenhuma sessão' : 'sem sessões');
      list.appendChild(hint);
      return;
    }
    rows.forEach((row) => {
      const item = el('button', 'session-item' + (row.id === state.sessionId ? ' active' : ''));
      item.type = 'button';
      if (state.active[row.id]) item.appendChild(el('span', 's-dot'));
      item.appendChild(el('span', 's-title', sessionTitle(row)));
      item.appendChild(el('span', 's-time', relativeTime(row.updated || row.created)));
      item.addEventListener('click', () => openSession(row.id, { focus: true }));
      list.appendChild(item);
    });
  }

  /* ── mensagens ────────────────────────────────────────────────────── */

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
      const tag = el('span', 'tag', message.model.id);
      who.appendChild(tag);
    }
    wrap.appendChild(who);
    return wrap;
  }

  function renderMessage(message) {
    if (message.role === 'user') {
      const wrap = el('div', 'msg msg-user');
      wrap.appendChild(el('div', 'bubble', message.text || ''));
      return wrap;
    }

    const wrap = assistantShell(message);
    const answer = el('div', 'answer');
    answer.innerHTML = md(message.text || '');
    wrap.appendChild(answer);

    if (message.reasoning) {
      wrap.appendChild(textBlock('raciocínio', message.reasoning, 'reasoning'));
    }
    (message.tools || []).forEach((tool) => {
      const block = toolBlock(tool.name, tool.status);
      const body = [];
      if (tool.input !== undefined && tool.input !== null) {
        body.push('$ ' + (typeof tool.input === 'string' ? tool.input : JSON.stringify(tool.input, null, 2)));
      }
      if (tool.output) body.push(tool.output);
      block.__body.textContent = body.join('\n\n');
      if (tool.status === 'error') block.__status.textContent = 'erro';
      if (tool.status === 'completed') block.__status.textContent = 'concluído';
      wrap.appendChild(block);
    });
    if (message.error) {
      wrap.appendChild(el('div', 'msg-error', message.error));
    }
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
          block.__body.textContent = '$ ' + (typeof ev.input === 'string' ? ev.input : JSON.stringify(ev.input, null, 2));
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
            block.__body.textContent = (block.__body.textContent ? block.__body.textContent + '\n\n' : '') + ev.output;
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
      case 'session.updated':
        break;
      default:
        break;
    }
  }

  function setRunning(running) {
    state.running = !!running;
    $('#status').hidden = !running;
    $('#stop-btn').hidden = !running;
    $('#send-btn').disabled = false;
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
  }

  async function openSession(sid, opts) {
    if (!sid) return;
    const options = opts || {};
    state.sessionId = sid;
    state.manualSwitch = Date.now();
    state.stream = {};
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
    if (!text) return;
    if (!state.sessionId) { await newSession(); }

    input.value = '';
    input.style.height = 'auto';

    const wrap = el('div', 'msg msg-user');
    wrap.appendChild(el('div', 'bubble', text));
    $('#messages').appendChild(wrap);
    $('#empty-state').hidden = true;
    scrollToEnd(true);

    try {
      await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/message`, { text });
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

  /* ── seletor de modelo ────────────────────────────────────────────── */

  function modelMeta(model) {
    const ctx = model.context ? `${Math.round(model.context / 1000)}k` : '';
    return ctx;
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

    if (!shown) {
      list.appendChild(el('div', 'model-group', 'nenhum modelo encontrado'));
    }
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
      applyModel({ id: model.id, providerID: model.providerID });
      const row = state.sessions.find((s) => s.id === state.sessionId);
      if (row) { row.model = { ...state.model }; renderSessions(); }
      $('#model-modal').hidden = true;
      toast(`modelo: ${model.name}`);
    } catch (e) {
      toast(String(e.message || e), 'err');
    }
  }

  /* ── seletor de agente ────────────────────────────────────────────── */

  function openAgents() {
    const list = $('#agent-list');
    list.innerHTML = '';
    state.agents.forEach((agent) => {
      const item = el('button', 'model-item' + (agent.id === state.agent ? ' current' : ''));
      item.type = 'button';
      const name = el('div', 'm-name');
      name.appendChild(document.createTextNode(agent.name));
      if (agent.description) {
        const sub = el('small');
        sub.textContent = agent.description;
        name.appendChild(sub);
      }
      item.appendChild(name);
      item.addEventListener('click', async () => {
        try {
          if (state.sessionId) {
            await apiPost(`/sessions/${encodeURIComponent(state.sessionId)}/agent`, { agent: agent.id });
          }
          state.agent = agent.id;
          $('#agent-label').textContent = agent.name;
          $('#agent-modal').hidden = true;
        } catch (e) {
          toast(String(e.message || e), 'err');
        }
      });
      list.appendChild(item);
    });
    $('#agent-modal').hidden = false;
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
    applyTheme(currentTheme());

    let data;
    try {
      data = await apiGet('/bootstrap');
    } catch (e) {
      $('#brand-sub').textContent = 'motor indisponível';
      $('#engine-dot').className = 'dot bad';
      $('#engine-text').textContent = 'sem conexão';
      toast('não foi possível falar com o motor', 'err');
      return;
    }

    state.agents = data.agents || [];
    state.commands = data.commands || [];
    state.sessions = data.sessions || [];
    state.active = data.active || {};
    state.models = (data.models && data.models.models) || [];
    state.providers = (data.models && data.models.providers) || [];

    $('#brand-sub').textContent = data.directory ? data.directory.split('/').pop() : 'PesquisAI';
    $('#engine-sub').textContent = data.engine && data.engine.version
      ? `motor ${data.engine.version} · ${data.models ? data.models.total : 0} modelos`
      : '';
    $('#engine-dot').className = 'dot ok';
    $('#engine-text').textContent = 'motor conectado';

    const preferred = state.agents.find((a) => a.id.toUpperCase() === 'UFVAI');
    state.agent = (preferred || state.agents[0] || {}).id || '';
    $('#agent-label').textContent = state.agent || 'agente…';

    renderSessions();
    renderModelList('');

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

  function bind() {
    const input = $('#input');
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 220) + 'px';
    });
    input.addEventListener('keydown', (event) => {
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

    $('#model-pill').addEventListener('click', openModels);
    $('#model-close').addEventListener('click', () => { $('#model-modal').hidden = true; });
    $('#model-search').addEventListener('input', (e) => renderModelList(e.target.value));

    $('#agent-pill').addEventListener('click', openAgents);
    $('#agent-close').addEventListener('click', () => { $('#agent-modal').hidden = true; });

    $('#theme-btn').addEventListener('click', () => {
      applyTheme(currentTheme() === 'pesquisai-light' ? 'pesquisai' : 'pesquisai-light');
    });

    $('#menu-btn').addEventListener('click', () => {
      document.body.classList.toggle('side-open');
      $('#scrim').hidden = !document.body.classList.contains('side-open');
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
        $('#model-modal').hidden = true;
        $('#agent-modal').hidden = true;
      }
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        $('#session-search').focus();
      }
    });

    window.addEventListener('beforeunload', () => {
      if (state.source) state.source.close();
    });
  }

  bind();
  boot();
})();

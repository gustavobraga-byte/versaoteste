/* PesquisAI - Cliente da interface
 *
 * Logica JS extraida do template HTML (ANALISE_CODIGO.md Secao 4.1).
 * Inclui:
 *   - escape de HTML para nomes de arquivo (Secao 2.4)
 *   - filtro de caracteres via DOM API (sem innerHTML nao-trusted)
 */

(function () {
  'use strict';

  const CFG = window.PESQUISAI_CONFIG || {};
  const BASE = CFG.base || location.origin;

  // -------- Helpers --------------------------------------------------

  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function $(id) { return document.getElementById(id); }

  // -------- Toast ----------------------------------------------------

  let _toastT;
  function toast(msg, type) {
    type = type || 'info';
    const el = $('toast');
    if (!el) return;
    el.className = 'show ' + type;
    el.textContent = msg;
    clearTimeout(_toastT);
    _toastT = setTimeout(() => el.classList.remove('show'), 3800);
  }

  // -------- Backup / Restore ----------------------------------------

  async function doBackup() {
    toast('Exportando sessao...', 'info');
    try {
      const r = await fetch(BASE + '/api/backup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const d = await r.json();
      if (d.ok) {
        toast('Backup salvo: ' + d.file, 'ok');
      } else {
        toast(d.error || 'Erro desconhecido', 'err');
      }
    } catch (e) {
      toast('Falha na conexao: ' + e.message, 'err');
    }
  }

  async function openRestore() {
    $('modal-overlay').classList.add('open');
    const list = $('backup-list');
    list.innerHTML = '<div class="modal-empty">Carregando backups...</div>';
    try {
      const r = await fetch(BASE + '/api/backups');
      const d = await r.json();
      if (!d.backups || d.backups.length === 0) {
        list.innerHTML = '<div class="modal-empty">Nenhum backup encontrado.</div>';
        return;
      }
      // Build via DOM API to avoid innerHTML-based XSS.
      list.innerHTML = '';
      d.backups.forEach((f) => {
        const item = document.createElement('div');
        item.className = 'backup-item';
        // data-* attribute is automatically HTML-escaped by the browser.
        item.setAttribute('data-file', f);
        item.addEventListener('click', () => doRestore(f));

        const span = document.createElement('span');
        span.textContent = f;  // textContent is XSS-safe
        const lbl = document.createElement('span');
        lbl.className = 'restore-lbl';
        lbl.textContent = 'restaurar';

        item.appendChild(span);
        item.appendChild(lbl);
        list.appendChild(item);
      });
    } catch (e) {
      list.innerHTML = '<div class="modal-empty">Erro ao carregar backups.</div>';
    }
  }

  function closeModal() {
    $('modal-overlay').classList.remove('open');
  }

  async function doRestore(file) {
    closeModal();
    toast('Importando ' + file + '...', 'info');
    try {
      const r = await fetch(BASE + '/api/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file })
      });
      const d = await r.json();
      if (d.ok) {
        const sessionId = d.session_id || '';
        const cmd = sessionId ? 'opencode -s ' + sessionId : 'opencode';
        toast('Importado! session_id: ' + (sessionId || '(nao encontrado)'), 'ok');
        setTimeout(() => {
          const msg = 'Sessao restaurada!\n' +
            (sessionId ? 'Vai abrir: ' + cmd : 'Sem sessionId - vai abrir opencode padrao.') +
            '\n\nReiniciar o terminal agora?';
          if (window.confirm(msg)) {
            toast('Rodando: ' + cmd, 'info');
            fetch(BASE + '/api/run_terminal', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ command: cmd, no_fallback: true })
            }).then(() => {
              const fr = $('terminal-frame');
              const origSrc = fr.src.split('?')[0];
              fr.src = 'about:blank';
              setTimeout(() => {
                fr.src = origSrc + '?t=' + Date.now();
                toast('Terminal recarregado com sessao!', 'ok');
              }, 3500);
            }).catch((e) => { toast('Erro: ' + e.message, 'err'); });
          }
        }, 600);
      } else {
        toast(d.error || 'Erro ao importar', 'err');
      }
    } catch (e) {
      toast('Falha na conexao: ' + e.message, 'err');
    }
  }

  // -------- Provider modal ------------------------------------------

  const PROVIDERS = [
    { id: 'anthropic',    name: 'Anthropic',         env: 'ANTHROPIC_API_KEY',          hint: 'sk-ant-...' },
    { id: 'bedrock',      name: 'AWS Bedrock',       env: 'AWS_ACCESS_KEY_ID',          hint: 'AKIA...' },
    { id: 'azure',        name: 'Azure OpenAI',      env: 'AZURE_OPENAI_API_KEY',       hint: '...' },
    { id: 'deepseek',     name: 'DeepSeek',          env: 'DEEPSEEK_API_KEY',           hint: 'sk-...' },
    { id: 'google',       name: 'Google Gemini',     env: 'GOOGLE_GENERATIVE_AI_API_KEY', hint: 'AIza...' },
    { id: 'groq',         name: 'Groq',              env: 'GROQ_API_KEY',               hint: 'gsk_...' },
    { id: 'mistral',      name: 'Mistral',           env: 'MISTRAL_API_KEY',            hint: '...' },
    { id: 'nvidia',       name: 'Nvidia NIM',        env: 'NVIDIA_API_KEY',             hint: 'nvapi-...' },
    { id: 'openai',       name: 'OpenAI',            env: 'OPENAI_API_KEY',             hint: 'sk-...' },
    { id: 'opencode_go',  name: 'OpenCode Go',       env: 'OPENCODE_GO_API_KEY',        hint: 'sk-...' },
    { id: 'opencode_zen', name: 'OpenCode Zen',      env: 'OPENCODE_ZEN_API_KEY',       hint: 'sk-...' },
    { id: 'openrouter',   name: 'OpenRouter',        env: 'OPENROUTER_API_KEY',         hint: 'sk-or-...' },
    { id: 'together',     name: 'Together AI',       env: 'TOGETHER_API_KEY',           hint: '...' },
    { id: 'vertex',       name: 'Vertex AI',         env: 'VERTEX_API_KEY',             hint: '...' },
    { id: 'xai',          name: 'xAI (Grok)',        env: 'XAI_API_KEY',                hint: 'xai-...' }
  ];

  let _selProv = null;

  function connectProvider() {
    const grid = $('prov-list');
    // Clear via DOM (safer than innerHTML = '')
    while (grid.firstChild) grid.removeChild(grid.firstChild);

    PROVIDERS.forEach((p) => {
      const btn = document.createElement('button');
      btn.className = 'provider-card';
      btn.type = 'button';
      btn.textContent = p.name;  // textContent -> XSS safe
      btn.addEventListener('click', () => selectProvider(p.id));
      grid.appendChild(btn);
    });

    $('prov-step1').style.display = 'block';
    $('prov-step2').style.display = 'none';
    $('prov-key-input').value = '';

    const overlay = $('provider-overlay');
    overlay.classList.add('open');
  }

  function selectProvider(id) {
    _selProv = PROVIDERS.find((p) => p.id === id);
    if (!_selProv) return;
    $('prov-name-title').textContent = _selProv.name;
    $('prov-env-code').textContent = _selProv.env;
    $('prov-cmd-preview').textContent =
      'opencode --set-key ' + _selProv.id + '="<sua-key>"';
    $('prov-key-input').placeholder = _selProv.hint || 'Cole sua key aqui...';

    fetch(BASE + '/api/apikey?provider=' + _selProv.id)
      .then((r) => r.json())
      .then((d) => { if (d.apikey) $('prov-key-input').value = d.apikey; })
      .catch(() => { /* ignore */ });

    $('prov-step1').style.display = 'none';
    $('prov-step2').style.display = 'block';
    setTimeout(() => $('prov-key-input').focus(), 80);
  }

  function provBack() {
    $('prov-step1').style.display = 'block';
    $('prov-step2').style.display = 'none';
    $('prov-key-input').value = '';
  }

  function closeProvider() {
    $('provider-overlay').classList.remove('open');
    _selProv = null;
  }

  async function confirmProvider() {
    const key = $('prov-key-input').value.trim();
    if (!key) { toast('Insira a API key.', 'err'); return; }
    if (!_selProv) { toast('Selecione um provedor.', 'err'); return; }
    const prov = _selProv;
    closeProvider();

    toast('Salvando key no Drive...', 'info');
    try {
      const sr = await fetch(BASE + '/api/apikey', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: prov.id, env: prov.env, apikey: key })
      });
      const sd = await sr.json();
      if (!sd.ok) { toast('Erro ao salvar: ' + (sd.error || ''), 'err'); return; }
      toast('Key salva no Drive!', 'ok');
    } catch (e) {
      toast('Falha ao salvar key: ' + e.message, 'err');
      return;
    }

    const cmd = 'export ' + prov.env + '="' + key + '" && opencode';
    toast('Configurando provedor e reiniciando terminal...', 'info');
    try {
      await fetch(BASE + '/api/run_terminal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, no_fallback: true })
      });
      const fr = $('terminal-frame');
      const origSrc = fr.src.split('?')[0];
      fr.src = 'about:blank';
      setTimeout(() => {
        fr.src = origSrc + '?t=' + Date.now();
        toast(prov.name + ' configurado! Terminal reaberto.', 'ok');
      }, 3500);
    } catch (e) { toast('Erro ao rodar comando.', 'err'); }
  }

  // -------- Startup --------------------------------------------------

  window.addEventListener('load', () => {
    fetch(BASE + '/api/apikey/apply', { method: 'POST' }).catch(() => { /* ignore */ });
    // Expose handlers used by inline onclick attributes.
    window.doBackup = doBackup;
    window.openRestore = openRestore;
    window.closeModal = closeModal;
    window.connectProvider = connectProvider;
    window.provBack = provBack;
    window.closeProvider = closeProvider;
    window.confirmProvider = confirmProvider;
    // Keep the legacy onclicks working when called from inline attributes
    // that survived the template - the attributes themselves are static,
    // so they cannot reference unbound functions safely. We mirror them
    // on window to be safe in case the template still has them.
    window.doRestore = doRestore;
  });
})();

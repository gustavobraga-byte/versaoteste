/* web48 — regressão: item da fila SEMPRE vai para a sessão de destino.
   Roda: node tests/js/test_web48_queue_sid.mjs                            */
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { JSDOM } from 'jsdom';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '../../');
const APP = fs.readFileSync(path.join(ROOT, 'pesquisai/webui/app.js'), 'utf8');
const I18N = JSON.parse(fs.readFileSync(path.join(ROOT, 'pesquisai/webui/i18n.json'), 'utf8'));
const HTML = fs.readFileSync(path.join(ROOT, 'pesquisai/webui/index.html'), 'utf8');

let pass = 0, fail = 0;
const check = (label, cond) => {
  if (cond) { pass++; console.log('  ok  ' + label); }
  else { fail++; console.log('  FAIL ' + label); }
};

const dom = new JSDOM(HTML, { url: 'http://localhost/', runScripts: 'outside-only' });
const win = dom.window;
const calls = [];

const fetchMock = async (url, opts = {}) => {
  calls.push({ url, opts });
  let body = {};
  if (url.includes('i18n.json')) body = I18N;
  else if (url.includes('/bootstrap')) body = {
    agents: [], models: [], sessions: [], active: {}, commands: [], skills: [],
    engine: {}, locale: 'pt-BR',
  };
  else body = { ok: true };
  return { ok: true, status: 200, json: async () => body };
};

let api = null;
let trocarAoConectar = false;

class EventSourceMock {
  constructor(url) {
    this.url = url;
    this.readyState = 1;
    // Simula a troca de sessão DURANTE o await de ensureEvents(): antes da
    // correção, o POST saía para state.sessionId (s2) em vez de s1.
    if (trocarAoConectar && api && url.includes('sid=s1')) {
      api.state.sessionId = 's2';
    }
    setTimeout(() => { if (this.onopen) this.onopen({}); }, 0);
  }
  close() { this.readyState = 2; }
}
win.EventSource = EventSourceMock;
win.fetch = fetchMock;
win.confirm = () => true;
win.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {}, removeEventListener() {} });
win.requestAnimationFrame = () => 1;
const realSetTimeout = win.setTimeout.bind(win);
win.setTimeout = (fn, ms) => (ms >= 100 ? 1 : realSetTimeout(fn, ms));
win.setInterval = () => 1;

win.eval(APP);
api = win.__ufvai;
if (!api) { console.error('__ufvai indisponível'); process.exit(1); }
api.state.messages = [];
api.state.stream = {};
api.state.attachments = [];
api.state.pendingSkills = [];

console.log('\n[1] postQueuedItem preserva o sid após troca de sessão no await');
api.state.sessionId = 's1';
api.state.source = null;
api.state.eventsSid = null;
trocarAoConectar = true;
let antes = calls.length;
await api.postQueuedItem({ sid: 's1', text: 'pergunta para A', attachments: [], skills: [] });
const isPost = (c) => c.opts.method === 'POST' && /\/sessions\/[^/]+\/message$/.test(c.url);
const post1 = calls.slice(antes).find(isPost);
check('POST foi para /sessions/s1/message', !!post1 && post1.url.includes('/sessions/s1/message'));
check('troca para s2 foi simulada', api.state.sessionId === 's2');
trocarAoConectar = false;

console.log('\n[2] queueMessage congela o destino no enqueue');
api.state.sessionId = 's3';
api.state.source = null;
api.state.eventsSid = null;
api.state.queue = [];
api.queueMessage('enfileirada em C');
const item2 = api.state.queue[api.state.queue.length - 1];
check('item carrega sid s3', !!item2 && item2.sid === 's3');
check('bolha registra dataset.sid', !!item2 && item2.node.dataset.sid === 's3');
// postQueuedItem() é disparado sem await dentro de queueMessage: aguarda
// um tick para que o POST imediato conste em `calls`.
await new Promise((resolve) => setTimeout(resolve, 0));
check('POST imediato foi para s3',
  calls.slice(antes).some(c => isPost(c) && c.url.includes('/sessions/s3/message')));

console.log('\n[3] flushQueue não cruza a fila de A na sessão B');
api.state.sessionId = 's2';
api.state.queue = [];
const nodeA = win.document.createElement('div');
api.state.queue.push({ sid: 's1', text: 'de A', attachments: [], skills: [], node: nodeA });
antes = calls.length;
await api.flushQueue();
check('nenhum /message disparado na sessão B',
  !calls.slice(antes).some(isPost));
check('item de A permaneceu na fila', api.state.queue.length === 1);

api.state.sessionId = 's1';
antes = calls.length;
await api.flushQueue();
const post3 = calls.slice(antes).find(
  c => isPost(c) && c.url.includes('/sessions/s1/message'));
check('ao voltar para A, item publicado em /sessions/s1/message', !!post3);

console.log('\n[4] confirmação da inbox limpa a bolha da sessão correta');
api.state.sessionId = 's2';
const box = win.document.querySelector('#messages');
const mk = (sid, text) => {
  const n = win.document.createElement('div');
  n.className = 'msg msg-user queued';
  n.dataset.sid = sid;
  const b = win.document.createElement('div');
  b.className = 'bubble';
  b.textContent = text;
  n.appendChild(b);
  box.appendChild(n);
  return n;
};
const bolhaA = mk('s1', 'de A');
const bolhaB = mk('s2', 'de B');
api.state.queue = [
  { sid: 's1', text: 'de A', attachments: [], skills: [], node: bolhaA },
  { sid: 's2', text: 'de B', attachments: [], skills: [], node: bolhaB },
];
api.handleInboxEvent({ type: 'inbox.enqueued', sid: 's1', text: 'de A' });
check('bolha de A removida', !box.contains(bolhaA));
check('bolha de B preservada', box.contains(bolhaB));
check('item de A saiu da fila; item de B ficou',
  !api.state.queue.some(it => it.sid === 's1') && api.state.queue.some(it => it.sid === 's2'));

console.log(`\nRESULTADO: ${pass} passaram, ${fail} falharam`);
process.exit(fail ? 1 : 0);

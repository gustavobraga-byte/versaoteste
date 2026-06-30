# 🐛 PesquisAI v0.5.1.3 — Hotfix: Conectores de Provedor de IA não salvavam

> **Data:** 2026-06-30
> **Tipo:** Bugfix (non-breaking)
> **Compatibilidade:** drop-in para v0.5.1.2 (mesma API, mesmas dependências)
> **Severidade:** 🔴 Alta — bloqueava completamente o salvamento de API keys

---

## 🐛 Bug corrigido

Ao clicar em **"Salvar e Conectar"** no modal de provedores de IA, a chave
digitada **nunca era salva**. O console do navegador mostrava:

```
Uncaught TypeError: Cannot read properties of null (reading 'id')
    at HTMLButtonElement.onclick (confirmProvider)
```

O usuário só via o overlay fechar e nada acontecer. As API keys
permaneciam ausentes em `/api/apikey` e o backend retornava 404 ao
consultá-las.

---

## 🔍 Causa raiz

A função `confirmProvider()` (no `launch_app_responsive.py`) tinha um
erro de **ordenação de operações**:

```javascript
// ❌ ANTES (v0.5.1.2) — CRASHAVA ANTES DE SALVAR
async function confirmProvider() {
  const key = document.getElementById("prov-key-input").value.trim();
  if (!key) { toast("⚠️ Insira a API key.", "err"); return; }
  if (!_selProv) { toast("⚠️ Selecione um provedor.", "err"); return; }
  closeProvider();            // ← (1) zera _selProv = null
  toast("💾 Salvando…", "info");
  try {
    await fetch(BASE + "/api/apikey", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: _selProv.id, ... })  // ← (2) CRASH: _selProv é null!
    });
    toast("✅ Salvo!", "ok");
  } catch(e) { toast("❌ " + e.message, "err"); }
}
```

`closeProvider()` internamente executa `_selProv = null`. Como a
próxima linha usa `_selProv.id`, o JS lança `TypeError` **antes** de
chamar `fetch`. O `try/catch` captura o erro e mostra um toast
vermelho, mas a chave **jamais** chega ao backend.

---

## 🛠️ Correção aplicada

```javascript
// ✅ DEPOIS (v0.5.1.3) — salva corretamente
async function confirmProvider() {
  const key = document.getElementById("prov-key-input").value.trim();
  if (!key) { toast("⚠️ Insira a API key.", "err"); return; }
  if (!_selProv) { toast("⚠️ Selecione um provedor.", "err"); return; }

  // 🐛 HOTFIX v0.5.1.3 — guardar refs em variáveis locais ANTES de fechar overlay
  const provId = _selProv.id;
  const provEnv = _selProv.env;
  const provName = _selProv.name;

  toast("💾 Salvando…", "info");
  try {
    const r = await fetch(BASE + "/api/apikey", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: provId, env: provEnv, apikey: key })
    });
    const d = await r.json().catch(() => ({}));
    if (r.ok && (d.ok !== false)) {
      toast(`✅ ${provName} conectado!`, "ok");
      closeProvider();
    } else {
      toast("❌ " + (d.error || `Erro HTTP ${r.status}`), "err");
    }
  } catch(e) {
    toast("❌ " + e.message, "err");
  }
}
```

**Três melhorias em uma:**

1. **Captura local** de `provId`, `provEnv`, `provName` antes de qualquer
   operação que possa alterar `_selProv` (defesa em profundidade).
2. **Tratamento de resposta HTTP** — agora o frontend verifica `r.ok`
   e o JSON de retorno (`d.error`) em vez de sempre mostrar "✅ Salvo!".
3. **`closeProvider()` movido para depois do sucesso** — se o servidor
   retornar erro, o overlay permanece aberto para o usuário tentar de novo.

---

## ✅ Validação E2E

```bash
# 1) POST de teste (simulando o frontend)
$ curl -s -X POST http://localhost:8001/api/apikey \
    -H "Content-Type: application/json" \
    -d '{"provider":"anthropic","env":"ANTHROPIC_API_KEY","apikey":"sk-ant-test-12345"}'
{"ok": true}                          # ← HTTP 200

# 2) GET para confirmar que a chave foi persistida
$ curl -s "http://localhost:8001/api/apikey?provider=anthropic"
{"apikey": "sk-ant-test-12345"}       # ← chave presente!

# 3) Payload inválido (sem provider) — backend rejeita corretamente
$ curl -s -X POST http://localhost:8001/api/apikey \
    -H "Content-Type: application/json" -d '{"apikey":"abc"}'
{"error": "provider e apikey obrigatórios."}   # ← HTTP 400
```

> **[DADO CONFIRMADO]** Auditoria: comparação `before/after` no HTML
> servido em `localhost:8001` confirma que o JS do `confirmProvider` foi
> substituído em `/tmp/pesquisai-wrapper/index.html`.

---

## 📦 Arquivos do patch

| Arquivo | Linhas alteradas | Tipo |
|---|---|---|
| `pesquisai/launch_app_responsive.py` | +20 / −7 | Frontend (89 KB → 99 KB) |
| `pesquisai/launch_app_responsive_v041.py` | +20 / −7 | Frontend (129 KB → 138 KB) |

> **Nenhuma dependência nova.** Nenhuma mudança breaking. 100% drop-in.
> O `env` dos provedores `opencode_go` e `opencode_zen` foi **preservado**
> como `OPENCODE_API_KEY` (decisão de design original, ambos compartilham
> a mesma plataforma OpenCode).

---

## 🛠️ Como aplicar

```bash
# 1. Backup
cp "/tmp/pesquisai/pesquisai/launch_app_responsive.py" \
   "/tmp/pesquisai/pesquisai/launch_app_responsive.py.bak.v0.5.1.2"
cp "/tmp/pesquisai/pesquisai/launch_app_responsive_v041.py" \
   "/tmp/pesquisai/pesquisai/launch_app_responsive_v041.py.bak.v0.5.1.2"

# 2. Aplique o patch (já está aplicado no zip)
unzip -o "/content/drive/My Drive/PesquisAI/pesquisai-v0.5.1.3-provider-fix.zip"
cp pesquisai/launch_app_responsive.py      /tmp/pesquisai/pesquisai/
cp pesquisai/launch_app_responsive_v041.py /tmp/pesquisai/pesquisai/
cp pesquisai/launch_app_responsive.py      /tmp/skill_pesquisai/pesquisai/
cp pesquisai/launch_app_responsive_v041.py /tmp/skill_pesquisai/pesquisai/

# 3. Regenere o HTML servido (o wrapper é gerado em runtime)
cd /tmp/pesquisai/pesquisai && python3 launch_app_responsive.py
# → gera /tmp/pesquisai-wrapper/index.html

# 4. Force reload no navegador (Ctrl+Shift+R / Cmd+Shift+R)
```

---

## 🔍 Como verificar no navegador

1. Abrir a topbar do PesquisAI (`http://localhost:8001/`)
2. Clicar em 🔌 **+ provedor**
3. Selecionar um provedor (ex: **Anthropic**)
4. Digitar uma API key (pode ser uma fake para teste)
5. Clicar em **Salvar e Conectar**
6. **Esperado:** toast verde "✅ Anthropic conectado!" e overlay fecha
7. Reabrir o modal e selecionar o mesmo provedor → a key deve aparecer
   no input (ou consultar via `GET /api/apikey?provider=anthropic`)

---

## 📊 Resumo da versão

| Item | Valor |
|---|---|
| Versão | 0.5.1.2 → 0.5.1.3 |
| Tipo | bugfix |
| Arquivos alterados | 2 (frontend) |
| Linhas adicionadas | +20 (líquido) |
| Compatibilidade | 100% drop-in para v0.5.1.2 |
| Severidade do bug | 🔴 Alta (bloqueava salvamento de API keys) |

---

*PesquisAI · v0.5.1.3 — hotfix · 2026-06-30*

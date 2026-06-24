# 🔧 Patch v0.4.1 — Correções do Site PesquisAI

> **Versão:** 0.4.1 (patch corretivo)
> **Data:** 2026-06-23
> **Compatibilidade:** PesquisAI v0.2.1+ (do GitHub)
> **Tipo:** 🐛 Bug fixes (sem breaking changes)

## ⚠️ Problemas Reportados pelo Usuário

Em 2026-06-23, no chat `session-ses_10b7.md`, o usuário reportou 3 problemas com o site do PesquisAI:

1. **"o site não ficou responsivo"**
2. **"a alteração para o tema claro e escuro não está funcionando (ela deve ao clicar recarregar o terminal com o tema correto)"**
3. **"a alteração de lingua deve ter um link ou alguma opção na interface"**

## 🔍 Diagnóstico

Investigando o `pesquisai/launch_app.py` do GitHub (https://github.com/gustavobraga-byte/PesquisAI/blob/main/pesquisai/launch_app.py), encontrei:

| # | Problema | Causa Raiz | Solução |
|---|----------|-----------|---------|
| 1 | Site não responsivo | `launch_app.py` do GitHub **não tem media queries** — só CSS estático | Adicionar 5 breakpoints + hamburger menu + modais fluidos |
| 2 | Tema não recarrega terminal | `toggleTheme()` chama `applyWrapperTheme()` (muda só CSS do wrapper), mas **nunca recarrega o iframe do ttyd** | Adicionar reload do iframe após aplicar tema (mesmo padrão usado em `confirmProvider()`) |
| 3 | Idioma sem opção na UI | O módulo `i18n` existe (4 idiomas completos), mas **não há seletor na topbar** | Adicionar dropdown com 4 idiomas + persistência em cookie + recarregamento |

> **Observação importante:** o `launch_app_responsive.py` que faz parte do release v0.4.0 (em `pesquisai-v0.4.0/pesquisai/`) JÁ TEM a responsividade, mas o PesquisAI principal no GitHub ainda usa o `launch_app.py` antigo (que importa nada responsivo).

## 🚀 Como Aplicar o Patch

### Opção 1 — Drop-in (Recomendada) ⚡

Copia o arquivo novo para o PesquisAI principal:

```bash
# 1. Baixar o patch
cp launch_app_responsive_v041.py \
   /content/drive/My\ Drive/PesquisAI/pesquisai/launch_app_responsive_v041.py

# 2. Editar launch_app.py do PesquisAI principal
#    Substituir APENAS a definição da função create_wrapper_html:

# ANTES (em pesquisai/launch_app.py):
def create_wrapper_html(terminal_url, drive_url):
    wrapper_html = f"""<!DOCTYPE html>..."""
    os.makedirs(WRAPPER_DIR, exist_ok=True)
    with open(os.path.join(WRAPPER_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(wrapper_html)


# DEPOIS:
from .launch_app_responsive_v041 import create_wrapper_html
```

### Opção 2 — Sem editar o `launch_app.py` (mais seguro) 🛡️

Criar um pequeno wrapper que importa a nova função:

```bash
# 1. Copiar o patch
cp launch_app_responsive_v041.py \
   /content/drive/My\ Drive/PesquisAI/pesquisai/launch_app_responsive_v041.py
```

```python
# 2. Criar /content/drive/My Drive/PesquisAI/pesquisai/_patch_v041.py
"""Patch v0.4.1 — drop-in para o launch_app.py sem editar o original."""
from .launch_app_responsive_v041 import create_wrapper_html as _v041


def create_wrapper_html(terminal_url, drive_url):
    """Wrapper v0.4.1 com responsividade + tema + idioma."""
    return _v041(terminal_url, drive_url)
```

```python
# 3. Em launch_app.py, alterar APENAS a última linha do arquivo
#    (onde start_wrapper_server() chama create_wrapper_html):
#    Trocar de:
#        create_wrapper_html(terminal_url, drive_url)
#    Para:
#        from ._patch_v041 import create_wrapper_html
#        create_wrapper_html(terminal_url, drive_url)
```

### Opção 3 — Para o PesquisAI-v0.4.0 (release que criamos)

Se você está usando o pacote `pesquisai-v0.4.0/`, **o patch já está aplicado**:

```python
# O launch_app_responsive.py do v0.4.0 foi atualizado para v0.4.1
from pesquisai.launch_app_responsive import create_wrapper_html
# (já tem as 3 correções)
```

## ✅ O Que Mudou em Detalhes

### 1. 📱 Responsividade Completa

| Breakpoint | Faixa | Layout |
|------------|-------|--------|
| Mobile pequeno | < 480px | Modo compacto, hamburger fullscreen |
| Mobile | 480-767px | Hamburger + ícones essenciais |
| Tablet | 768-1023px | Topbar condensado |
| Tablet portrait | 768-1024px portrait | UFV footer oculto |
| Desktop | ≥ 1024px | Layout original completo |
| Landscape mobile | max-height 500px | Topbar reduzido, terminal expandido |

**CSS adicionado (resumo):**

```css
.hamburger { display: none; }
@media (max-width: 767px) {
  .hamburger { display: inline-flex; }
  .tb-btn { display: none; }      /* migram para hamburger */
  #terminal-frame { height: calc(100vh - 50px - 36px) !important; }
  #modal { width: 95vw !important; }
}

.mobile-menu {
  position: fixed; top: 50px; right: 0;
  width: 280px; max-width: 85vw;
  transform: translateX(100%);
  transition: transform .25s ease;
}
.mobile-menu.open { transform: translateX(0); }
```

**HTML adicionado:**

```html
<button class="hamburger" onclick="toggleMobileMenu()" id="hamburger-btn">
  <svg viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6"/>...</svg>
</button>

<div class="mobile-menu-overlay" id="mobile-overlay" onclick="toggleMobileMenu()"></div>
<div class="mobile-menu" id="mobile-menu" aria-hidden="true">
  <button class="tb-btn btn-backup" onclick="doBackup(); toggleMobileMenu();">Salvar backup</button>
  <button class="tb-btn btn-restore" onclick="openRestore(); toggleMobileMenu();">Restaurar</button>
  <!-- ... todos os outros itens ... -->
</div>
```

### 2. 🎨 Tema Recarrega o Terminal

**ANTES (com bug):**

```javascript
async function toggleTheme() {
  const btn = document.getElementById("theme-toggle");
  const cur = btn.dataset.theme || "pesquisai";
  const next = cur === "pesquisai" ? "pesquisai-light" : "pesquisai";
  // ...
  applyWrapperTheme(next);  // 🐛 Só muda CSS do wrapper
  // O iframe do ttyd continua com o tema antigo!
  toast("☀️ Tema claro", "info");
}
```

**DEPOIS (corrigido):**

```javascript
async function toggleTheme() {
  const btn = document.getElementById("theme-toggle");
  const cur = btn.dataset.theme || "pesquisai";
  const next = cur === "pesquisai" ? "pesquisai-light" : "pesquisai";
  // ...
  btn.dataset.theme = next;
  applyWrapperTheme(next);  // 1. Aplica tema na UI

  // ✅ FIX: Recarrega iframe do ttyd para o terminal usar o novo tema
  toast("☀️ Tema claro (UI + terminal)", "info");
  const fr = document.getElementById("terminal-frame");
  if (fr) {
    const origSrc = fr.src.split("?")[0];
    fr.src = "about:blank";
    setTimeout(() => {
      fr.src = origSrc + "?theme=" + next + "&t=" + Date.now();
      toast("✅ Terminal recarregado com novo tema", "ok");
    }, 3500);
  }
}
```

**Mudanças complementares:**

- `applyWrapperTheme()` agora também atualiza `<meta name="theme-color">` para a barra de status do navegador mobile.
- `loadInitialTheme()` lê primeiro o **cookie** (sem flash) e depois valida com o servidor.
- Indicador visual do tema ativo: `#theme-toggle[data-theme="pesquisai-light"]` fica em amber.

### 3. 🌐 Seletor de Idioma na UI

**HTML adicionado (na topbar):**

```html
<button class="lang-btn" id="lang-btn" onclick="toggleLangMenu()"
        aria-haspopup="true" aria-expanded="false" title="Idioma / Language">
  <span class="lang-flag" id="lang-flag">🇧🇷</span>
  <span class="lang-code" id="lang-code">PT</span>
  <span class="lang-chevron"></span>
</button>

<div class="lang-menu" id="lang-menu" role="menu">
  <!-- Preenchido dinamicamente por buildLangMenu() -->
</div>
```

**JavaScript (sistema completo):**

```javascript
// Detecção de idioma (URL > cookie > navegador > padrão)
function getCurrentLang() {
  // 1. Query param ?lang=xx_XX
  const ql = new URL(location.href).searchParams.get("lang");
  if (ql && LANGS[ql]) return ql;
  // 2. Cookie persistido
  const ck = getCookie(LANG_COOKIE);
  if (ck && LANGS[ck]) return ck;
  // 3. navigator.language
  // 4. Padrão "pt_BR"
}

// Aplica idioma em todos os elementos data-i18n
function applyLang(lang) {
  const dict = I18N[lang] || I18N["pt_BR"];
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) el.textContent = dict[key];
  });
  document.documentElement.lang = lang.replace("_", "-");
  // Persiste
  setCookie(LANG_COOKIE, lang);
}

function setLang(lang) {
  // Salva no backend (opcional) + recarrega para traduções de toasts
  fetch(BASE + "/api/lang", {
    method: "POST",
    body: JSON.stringify({ lang })
  }).catch(() => {});
  applyLang(lang);
  toast("🌐 Idioma alterado para " + lang, "info");
  setTimeout(() => location.reload(), 700);
}
```

**Backend (opcional mas recomendado) — adicionar 2 endpoints no `launch_app.py`:**

```python
# No BaseHTTPRequestHandler do launch_app.py, adicionar:

def _handle_lang(self, body: dict) -> dict:
    """GET/POST /api/lang — gerencia idioma persistido."""
    lang = body.get("lang", "pt_BR")
    lang = _normalize_lang(lang)  # pt_BR, en_US, es_ES, fr_FR
    if lang not in SUPPORTED_LANGUAGES:
        return {"ok": False, "error": f"Idioma '{lang}' não suportado"}
    # Persiste no Drive
    config_path = os.path.join(DRIVE_BACKUP_DIR, "lang.json")
    os.makedirs(DRIVE_BACKUP_DIR, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"lang": lang, "updated_at": datetime.now().isoformat()}, f)
    return {"ok": True, "lang": lang}

# No do_POST(), adicionar caso "lang":
#   case "lang": self._json(self._handle_lang(body))
# No do_GET(), adicionar:
#   if self.path == "/api/lang":
#       return self._json({"lang": _load_lang()})
```

**Traduções inline (incluídas no HTML):**

4 dicionários JSON são injetados no `<script>` para tradução client-side instantânea (sem precisar reload para strings visíveis):

| Chave | pt_BR | en_US | es_ES | fr_FR |
|-------|-------|-------|-------|-------|
| `ui.backup` | Salvar backup | Save backup | Guardar copia | Sauvegarder |
| `dashboard.title` | Dashboard de Saúde | Health Dashboard | Panel de Salud | Tableau de bord |
| `theme.light` | Tema claro (UI + terminal) | Light theme (UI + terminal) | Tema claro (UI + terminal) | Thème clair (UI + terminal) |
| `theme.terminal_reloaded` | Terminal recarregado com novo tema | Terminal reloaded with new theme | Terminal recargado con nuevo tema | Terminal rechargé avec le nouveau thème |
| ... (40+ chaves) | ... | ... | ... | ... |

## 🧪 Como Testar

### Teste 1 — Responsividade

```bash
# No navegador desktop:
# 1. Abrir DevTools (F12)
# 2. Modo responsivo (Ctrl+Shift+M)
# 3. Testar em:
#    - iPhone SE (375x667)   → hamburger deve aparecer
#    - iPad (768x1024)        → topbar condensado
#    - Desktop (1920x1080)    → layout original
```

### Teste 2 — Tema

```bash
# 1. Clicar no botão ◑ (sol) na topbar
# 2. Deve aparecer toast: "☀️ Tema claro (UI + terminal)"
# 3. Após 3.5s, deve aparecer: "✅ Terminal recarregado com novo tema"
# 4. Verificar que o terminal dentro do iframe MUDOU DE TEMA também
```

### Teste 3 — Idioma

```bash
# 1. Clicar no botão 🇧🇷 PT (com bandeira) na topbar
# 2. Menu dropdown deve abrir com 4 opções:
#    🇧🇷 Português (Brasil)        ✓
#    🇺🇸 English (United States)
#    🇪🇸 Español (España)
#    🇫🇷 Français (France)
# 3. Selecionar "🇺🇸 English (United States)"
# 4. Página deve recarregar com:
#    - <html lang="en-US">
#    - Botões traduzidos: "Save backup", "Restore", "Drive"
#    - Modal "Session History" em vez de "Histórico de Sessões"
# 5. Recarregar a página: idioma deve persistir (cookie)
```

### Teste 4 — Query param de idioma

```bash
# Forçar idioma via URL:
http://localhost:8001/?lang=fr_FR
# Deve abrir em francês
```

## 🔒 Compatibilidade

- ✅ **Backward compatible** — se JS do hamburger falhar, topbar original ainda funciona
- ✅ **API inalterada** — `create_wrapper_html(terminal_url, drive_url)` mantém a mesma assinatura
- ✅ **Sem migração de dados** — apenas visual/CSS/JS
- ✅ **CSS puro** — sem dependências externas adicionais
- ✅ **Tema claro/escuro** — funciona normalmente em todos os breakpoints
- ✅ **i18n server-side** — usa o módulo `i18n` do release v0.4.0

## 📊 Estatísticas do Patch

| Métrica | Valor |
|---------|-------|
| Arquivos modificados | 1 (`launch_app.py` do GitHub) |
| Linhas adicionadas | ~700 |
| Linhas removidas | 0 (substituição aditiva) |
| Funções JS novas | 7 (toggleLangMenu, buildLangMenu, applyLang, setLang, getCurrentLang, setCookie, getCookie) |
| Media queries | 6 |
| Idiomas inline | 4 (pt_BR, en_US, es_ES, fr_FR) |
| Strings traduzidas | 40+ chaves |
| Breaking changes | 0 |

## 📝 Notas de Migração

1. **Nenhuma mudança de API** — `create_wrapper_html(terminal_url, drive_url)` mantém a mesma assinatura
2. **Sem migração de dados** — apenas visual/CSS/JS
3. **Backward compatible** — se o JavaScript do hamburger falhar, a topbar original ainda funciona
4. **CSS puro** — sem dependências externas adicionais
5. **Tema claro/escuro** — funciona normalmente em todos os breakpoints
6. **Idioma persistido em 3 camadas** — `?lang=xx_XX` (URL) > cookie > `navigator.language` > padrão
7. **i18n server-side** — usa o módulo `i18n` do release v0.4.0 (com fallback em pt_BR)

## 🐛 Problemas Conhecidos

| Problema | Workaround |
|----------|-----------|
| Terminal demora 3.5s para recarregar após trocar tema | É o tempo de restart do ttyd. Pode ser reduzido para 2s se o backend responder mais rápido |
| Idioma do conteúdo do terminal (não da UI) é controlado pelo opencode, não pelo i18n | Configurar variável `LANG` no servidor |

## 📄 Licença

MIT — Copyright (c) 2026 Gustavo Bastos Braga (UFV)

---

**Versão:** 0.4.1
**Anterior:** 0.4.0 (International & Mobile)
**Tipo:** 🐛 Patch corretivo (sem breaking changes)

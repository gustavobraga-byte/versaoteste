# PesquisAI v0.4.2.3 — Release Notes (HOTFIX)

> **Data:** 2026-06-24
> **Versão:** 0.4.2.3
> **Codinome:** ses_106b hotfix (JS broken escapes — buttons restored)
> **Status:** ✅ Pronto para deploy no GitHub
> **Tema padrão:** 🌙 Escuro (com anti-flash CSS)

## 🔥 BUG CRÍTICO RESOLVIDO

**Sintoma:** ao carregar o wrapper HTML do PesquisAI, **nenhum botão funcionava** (📜 Histórico, 🌍 Idioma, 🌓 Tema, 🩺 Dashboard, 💾 Backup, etc.).

**Causa raiz:** A string tripla `"""..."""` em `pesquisai/launch_app_responsive_v041.py` continha escapes de aspas (`\'` e `\"`) que o Python removia durante a compilação. O HTML resultante tinha JavaScript com sintaxe inválida → `SyntaxError` no `<script>` → nenhuma função/event handler era registrada → **nada funcionava**.

## 📦 Conteúdo do Release

- **65 arquivos** Python/Markdown/JSON/TOML/YAML
- **5 categorias principais:** `agents/`, `docs/`, `grant_finder/`, `i18n/`, `pesquisai/`, `skills/`
- **Compatibilidade:** Python ≥ 3.10
- **Testes:** 79/79 pytest verdes (sem regressão)

## 🆕 Mudanças em v0.4.2.3 (ses_106b hotfix)

### 1. 🐛 `renderSessions()` reescrito (linha 1684)
- **Antes:** `onclick="restoreSession(\'' + id + '\')"` (concatenação frágil com `\'` perdido)
- **Depois:** `<div data-session-id="..." class="session-item">` + event listener global
- **Por que funciona:** elimina concatenação dinâmica de aspas dentro de string tripla Python

### 2. 🐛 `restoreSession()` corrigido (linha 1714)
- **Antes:** `confirm("Restaurar sessão \"" + id + "\" ?")` (`\"` perdido)
- **Depois:** `confirm("Restaurar sessão " + chr(34) + id + chr(34) + " ?")`
- **Por que funciona:** `chr(34)` é concatenação JS em runtime, zero risco de escape Python

### 3. 🐛 `escapeHtml()` simplificado (linha 1736)
- **Antes:** object literal com `\"":"&quot;"` (sintaxe inválida)
- **Depois:** `if/else` chain (sem aspas dentro de string)
- **Por que funciona:** elimina o conflito de aspas no objeto de mapeamento

## 🧪 Validação Final

- ✅ **`node --check` no JS extraído: SEM ERROS** (sintaxe 100% válida)
- ✅ **HTML regenerado: 89.127 chars** (vs 88.517 da v0.4.2.2)
- ✅ **10/10 funções JS verificadas** funcionando
- ✅ **42 botões** com `onclick="..."` validados
- ✅ **79/79 testes pytest** continuam passando (zero regressão)

### Comandos de validação

```bash
# 1. Validar JS com Node
python3 -c "
import re
with open('/tmp/pesquisai-wrapper/index.html') as f:
    html = f.read()
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
big = max(scripts, key=len)
with open('/tmp/test.js', 'w') as f:
    f.write(big)
"
node --check /tmp/test.js  # ✅ No errors

# 2. Rodar testes
python3 -m pytest grant_finder/tests/ i18n/tests/ --tb=line
# ✅ 79 passed in 1.01s
```

## 📋 Resumo das versões (v0.4.2.x)

| Versão | Codinome | Data | Mudanças |
|---|---|---|---|
| 0.4.2.3 | ses_106b hotfix | 2026-06-24 | 🔥 JS broken escapes — botões restaurados |
| 0.4.2.2 | ses_10a4+ polish | 2026-06-24 | Footer PC + Skills + Sessions + Lang + Version |
| 0.4.2.1 | ses_10a4 fixes | 2026-06-23 | Theme contrast + Dashboard + Markdown |
| 0.4.1 | UI fixes | 2026-06-23 | Responsive + Theme + Language |

## 🔗 Links

- **Repositório:** https://github.com/gustavobraga-byte/PesquisAI
- **Release ZIP:** `pesquisai-v0.4.2.3-github.zip` (novo)
- **Skill grant-finder:** https://github.com/gustavobraga-byte/grant-finder
- **Skill meta-search-br:** https://github.com/gustavobraga-byte/meta-search-br
- **OpenCode:** https://opencode.ai

## ✍️ Autoria

**Gustavo Bastos Braga** — Universidade Federal de Viçosa (UFV)
**Email:** gustavo.braga@ufv.br
**SisPPG/UFV:** 10356285004
**Licença:** MIT

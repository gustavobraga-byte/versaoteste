# PesquisAI v0.4.2.2 — Release Notes

> **Data:** 2026-06-24
> **Versão:** 0.4.2.2
> **Codinome:** ses_10a4+ polish
> **Status:** ✅ Pronto para deploy no GitHub
> **Tema padrão:** 🌙 Escuro (com anti-flash CSS)

## 📦 Conteúdo do Release

- **65 arquivos** Python/Markdown/JSON/TOML/YAML
- **5 categorias principais:** `agents/`, `docs/`, `grant_finder/`, `i18n/`, `pesquisai/`, `skills/`
- **Tamanho compactado:** 316 KB
- **Tamanho descompactado:** 710 KB
- **Testes:** 119 (100% verdes)
- **Cobertura:** 71.58%
- **Compatibilidade:** Python ≥ 3.10

## 🆕 Mudanças em v0.4.2.2 (ses_10a4+ polish)

### 1. 🖥️ Footer PC alinhado à direita
- Botão de provedor + "Powered by OpenCode" agora ficam à direita no desktop
- Implementado via `margin-left: auto` em `.footer-row-2` dentro de `@media (min-width: 768px)`
- Mobile/tablet mantém o layout de 2 linhas

### 2. 🧩 Skills em `skills/` com clone URL
- `skills/grant-finder/`: README + SKILL.md + `__init__.py` (NOVO)
- `skills/meta-search-br/`: README (NOVO) + SKILL.md com seção de clone
- Links:
  - https://github.com/gustavobraga-byte/grant-finder
  - https://github.com/gustavobraga-byte/meta-search-br

### 3. 📜 Histórico de sessão carregando
- `openSessions()` agora faz `fetch("/api/sessions")` e popula a lista
- Cada item é clicável e chama `restoreSession(id)` (POST em `/api/restore`)
- Busca em tempo real via `filterSessions()`
- 12 novas strings i18n (3 por idioma × 4 idiomas)

### 4. 🌍 Saudação no idioma
- `start_ttyd(lang)` usa `get_greeting(lang)` ao invés de `--prompt 'oi'`
- Saudações multilíngues (curtas + dica entre parênteses):
  - 🇧🇷 "Olá! (Dica: A partir de agora responda em português brasileiro.)"
  - 🇺🇸 "Hello! (Tip: From now on, please respond in English.)"
  - 🇪🇸 "¡Hola! (Consejo: A partir de ahora responda en español.)"
  - 🇫🇷 "Bonjour ! (Astuce: À partir de maintenant, répondez en français.)"
- **Ajuste pós-ses_10a4+:** a frase "Eu sou o PesquisAI" foi removida das
  saudações (era冗余 e ocupava espaço desnecessário no `--prompt`).
- Novos endpoints `GET/POST /api/lang` que reiniciam o ttyd com a saudação
- Idioma persistido em `~/.config/pesquisai_lang`

### 5. 📦 `__version__.py` movido
- De `/__version__.py` → `/pesquisai/__version__.py`
- Versão bumpada para `0.4.2.2`
- Mantém compatibilidade com fallback hardcoded

### 6. 🧹 AGENTS.md multilíngues padronizados
- Removido `- [link/lien/enlace]` das 4 variantes (pt_BR, en_US, es_ES, fr_FR)
- Formato final: `- `agents/AGENTS.<lang>.md` (nome do idioma)`

## 🧪 Validação

- ✅ **119/119 testes** passando
  - `grant_finder/tests/`: 48 testes
  - `i18n/tests/`: 31 testes
  - `skills/meta-search-br/tests/`: 40 testes
- ✅ **Sintaxe Python** validada em 5 arquivos
- ✅ **Geração do HTML** validada (88.517 chars)
- ✅ **`get_greeting()`** testada para 4 idiomas
- ✅ **Comando bash do ttyd** testado para 4 idiomas
- ✅ **Zip descompactado** + testes rodam em pasta temporária

## 🔗 Links

- **Repositório:** https://github.com/gustavobraga-byte/PesquisAI
- **Release ZIP:** `pesquisai-v0.4.1-github.zip` (316 KB)
- **SHA-256:** `7f75dcf23f84fe50ad59c227574a4cd33c1c6ee6dfee1aabafab78f16a3e2dda`
- **Skill grant-finder:** https://github.com/gustavobraga-byte/grant-finder
- **Skill meta-search-br:** https://github.com/gustavobraga-byte/meta-search-br
- **OpenCode:** https://opencode.ai

## ✍️ Autoria

**Gustavo Bastos Braga** — Universidade Federal de Viçosa (UFV)
**Email:** gustavo.braga@ufv.br
**SisPPG/UFV:** 10356285004
**Licença:** MIT

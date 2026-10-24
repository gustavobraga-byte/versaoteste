# Pendente de push — v0.7.5 (sem bump) · 24/10/2026

> O código novo **já está nesta pasta** (`UFVAI-v0.7.5/`). O que falta é
> publicar no GitHub (`gustavobraga-byte/versaoteste`) — o boot do Colab
> clona o repositório, não esta pasta.
>
> Patch pronto: `patches/2026-10-24-idioma-boot-v075.patch`
> (`git apply --check` **OK** num clone limpo; 53 testes dos arquivos
> afetados + 190 JS passando lá).

## O que mudou (9 arquivos)

| Arquivo | Conteúdo |
|---|---|
| `pesquisai/launch_app.py` | idioma no Drive (`config/prefs.json`), saudação no idioma do cliente, `greeting_pending`, injeção da mensagem ao trocar idioma, gzip do HTML, auto-cura do ttyd, **auto-reconnect do terminal** (vigia no index + `pid` em `/api/ttyd_ready`), **log de diagnóstico** (`/tmp/ufvai-logs/wrapper.log`) e **fim do `pkill -9 -x ttyd`** ao preparar o index (matava o terminal vivo) |
| `pesquisai/launch_app_responsive_v041.py` | init em `DOMContentLoaded`, retomada em 350 ms, CSS externo não bloqueante, POST de idioma com saudação pendente, **detecção**: navegador vence cookie automático (cookie só manda se `pesquisai_lang_src=user`), recarga do iframe quando o ttyd reinicia |
| `pesquisai/run_fast.py` | `opencode models` com timeout de 25 s e `cwd` no `seed_ufvai_greeting` (saudação caía em modelo sem quota) |
| `tests/test_v075_lang_boot.py` | **novo** — 19 testes (prefs, pendência, endpoint, gzip, DOMContentLoaded) |
| `tests/test_v075_ttyd_autorevive.py` | **novo** — 7 testes da auto-cura do terminal |
| `tests/test_v075_ttyd_reconnect.py` | **novo** — 7 testes do auto-reconnect (vigia, pid, log) |
| `tests/test_v075_startup_single_session.py` | ajuste: `_set_lang_only(full_lang, source="browser")` |
| `tests/test_instalacao_pacote.py` | aceita a célula de boot no formato em uso |
| `tests/js/test_v075_opening_once.js` | 1 linha sincronizada |

## Como publicar (patch — recomendado)

```bash
git clone https://github.com/gustavobraga-byte/versaoteste.git
cd versaoteste
PATCH="/content/drive/My Drive/PesquisAI/UFVAI-v0.7.5/patches/2026-10-24-idioma-boot-v075.patch"
git apply --stat "$PATCH"
git apply "$PATCH"
git add -A
git commit -m "v0.7.5: idioma no boot, saudacao por idioma, abertura leve e reconnect do terminal"
git push
```

## ⚠️ Não substitua a pasta inteira

`UFVAI-v0.7.5/` é um **subconjunto** do repositório. Não existem aqui (mas
existem no GitHub e não devem ser apagados):

- `tests/test_basic.py`, `test_launch_app.py`, `test_run_fast.py` e demais
  testes antigos;
- `pesquisai/obsidian/obsidian/` (subpacote legado, sem imports no código).

## Validação

- Pacote do Drive: **176 testes Python** + **190 verificações JS**.
- Clone limpo + patch: `git apply --check` OK; 47 testes dos arquivos
  afetados + 190 JS.
- Runtime: `GET /` gzip 74.945 B · `/api/ttyd_ready` com `pid` ·
  index do ttyd com o vigia no `<head>`.

## Observações

- `tests/test_basic.py` **já falha no HEAD do repositório** (importa
  `WEBCLI_PORT`, que não existe em `constants.py`) — não é efeito deste
  patch.
- A chave OpenRouter do modelo padrão está com limite zerado
  (`$0.00 of $0.00 used; does not reset`); o caminho gratuito
  (`opencode/big-pickle`) funciona.

# 🖥️ UFVAI v0.7.11-web — interface web do OpenCode no lugar do ttyd

> **Variante da v0.7.11.** A janela principal do UFVAI deixa de exibir o
> terminal `ttyd` e passa a exibir a **SPA oficial do OpenCode**, servida pelo
> próprio motor (`opencode serve`), com a **identidade visual do UFVAI**
> (navy + dourado + creme) injetada por um proxy local.

---

## 1. O que muda

| Antes (v0.7.11) | Agora (v0.7.11-web) |
|---|---|
| iframe aponta para `ttyd` na porta 8000 | iframe aponta para o **proxy da SPA** na porta **8002** |
| interface = TUI dentro do terminal | interface = **web app do OpenCode** (chat, sessões, arquivos) |
| tema = `pesquisai` no ttyd | tema **UFVAI** injetado no web app (`--v2-*`) |
| login = terminal | **Basic auth injetada pelo proxy** (o navegador nunca vê a senha) |

O `ttyd` continua sendo iniciado em segundo plano (porta 8000) como
**fallback** e para os recursos que dependem dele (`/api/run_terminal`,
reinício de idioma, etc.), mas **não aparece** na janela principal.

---

## 2. Arquitetura

```
Navegador
  │  https://<colab>/proxy/8001/        (wrapper UFVAI: topbar, rodapé, modais)
  │      └── iframe https://<colab>/proxy/8002/
  ▼
Proxy UFVAI (pesquisai/ocweb.py, 0.0.0.0:8002)
  │  • injeta Authorization: Basic opencode:<service.json.password>
  │  • repassa /_assets, /icons, /api/* e SSE /api/event
  │  • injeta <style> com a paleta UFVAI + badge
  ▼
OpenCode web (127.0.0.1:<porta do service.json>, só loopback)
```

O proxy lê `~/.local/state/opencode/service.json` a cada requisição. Se o
motor reiniciar (nova porta/senha), ele se adapta sem reiniciar o wrapper.

---

## 3. Como executar

Nada muda no fluxo do Colab: rode a célula de boot da árvore
`UFVAI-v0.7.11-web/` e abra a interface na **porta 8001**. A janela já abre
com a SPA do OpenCode.

No `.deb` (Linux com TUN/NET_ADMIN), o mesmo vale:

```bash
sudo apt install ./debs/pesquisai_0.7.11-web1_amd64.deb
ufvai
```

Se o serviço ainda não estiver pronto (onboarding sem chave), o proxy devolve
uma página “O motor do OpenCode ainda não está disponível” que recarrega a
cada 3 s — em vez de um JSON de erro.

---

## 4. Tema UFVAI

O CSS injetado sobrescreve os tokens `--v2-*` do motor:

| Token | Claro | Escuro |
|---|---|---|
| `--v2-background-bg-deep` | `#efece4` | `#0d0f10` |
| `--v2-background-bg-base` | `#f6f5f0` | `#111518` |
| `--v2-background-bg-layer-01` | `#ffffff` | `#161b1e` |
| `--v2-text-text-base` | `#23282c` | `#f2f1ea` |
| `--v2-text-text-muted` | `#5f6468` | `#a8a49a` |
| `--v2-border-border-base` | `#ddd8cc` | `#2a3136` |
| `--v2-text-text-accent` | `#8a6d33` | `#d9b45c` |
| `--v2-background-bg-accent` | `#8a6d33` | `#b29149` |

Além dos tokens:

* barra superior de 3 px em degradê **navy → dourado**;
* badge fixo **UFV·AI** no canto inferior esquerdo;
* tipografia do sistema (`Segoe UI`/system-ui);
* título da aba = **UFVAI · OpenCode**.

O tema claro/escuro acompanha o `localStorage` do próprio OpenCode
(`opencode-color-scheme`), então o botão de tema do web app continua valendo.

---

## 5. Segurança

- A senha do serviço (`service.json`) **nunca** chega ao navegador: o proxy a
  converte em `Authorization: Basic` no servidor.
- O proxy escuta em `0.0.0.0:8002` (necessário para o proxy do Colab), mas o
  upstream é sempre `127.0.0.1:<porta>`; não há exposição direta do motor.
- O CSP do próprio OpenCode é preservado (`style-src 'unsafe-inline'` já
  permite o CSS injetado; nenhum script inline é adicionado).
- O token de sessão do wrapper (`X-UFVAI-Token`) continua valendo para as
  rotas `/api/*` do **wrapper** (8001), não para o proxy.

---

## 6. Limitações

- **É a UI do OpenCode**, não uma tela feita pelo UFVAI: menus, atalhos e
  fluxos são os do motor. A customização é visual (cores, tipografia, badge).
- O **chat** usa SSE (`/api/event`); o proxy repassa em chunks. WebSocket é
  suportado por túnel, mas o PTY persistente pode variar conforme a versão do
  OpenCode.
- O `ttyd` continua rodando (fallback). Para desativá-lo de vez, remova a
  chamada `start_ttyd()` em `launch_app.launch()` — não recomendado, pois
  recursos do wrapper dependem dele.
- Sem navegador real neste ambiente, a validação foi por HTTP: HTML, assets,
  `/api/session` e SSE responderam 200/streaming; o teste visual fica com o
  usuário.

---

## 7. Testes

```bash
python -m pytest tests/test_v0711_ocweb.py -q -o addopts=""
# 9 passed
```

Cobrem: leitura do `service.json`, Basic auth, injeção de tema/badge/título,
`ready()` sem serviço, status e a troca de `/api/ttyd_ready` por
`/api/ocweb_ready` no HTML do wrapper.

---

## 8. Arquivos

- `pesquisai/ocweb.py` — proxy + tema (novo)
- `pesquisai/constants.py` — `OCWEB_PORT = 8002`
- `pesquisai/launch_app.py` — inicia o proxy e aponta o iframe para 8002;
  `GET /api/ocweb_ready`
- `pesquisai/launch_app_responsive_v041.py` — `create_wrapper_html(..., web_mode=True)`
- `tests/test_v0711_ocweb.py`

---

## 9. Diagnóstico: “continua abrindo o ttyd”

Se a janela principal ainda mostra o terminal, verifique nesta ordem:

1. **Célula de boot errada (causa mais comum até a revisão `web2`).**
   A célula copiava sempre `UFVAI-v0.7.11/` para `/tmp/pesquisai`, mesmo
   aberta dentro de `UFVAI-v0.7.11-web/`. A versão corrigida resolve a
   origem pela pasta do próprio arquivo (ou pela pasta atual que contenha
   `pesquisai/ocweb.py`).
2. **Sessão sem restart.** O servidor antigo continua na porta 8001 e o bind
   novo falha dentro de uma thread (sem erro visível). A célula corrigida
   detecta a porta ocupada e manda reiniciar o runtime.
3. **Confirmação rápida:**

   ```bash
   curl -s http://127.0.0.1:8002/__ufvai_ready        # {"ready": true, ...}
   curl -s http://127.0.0.1:8001/ | grep -o 'data-terminal-url="[^"]*"'
   # deve conter 8002, não 8000
   ```

4. Se `data-terminal-url` ainda apontar para 8000, o HTML em
   `/tmp/pesquisai-wrapper/index.html` é antigo: rode o boot de novo após
   **Runtime → Restart session**.

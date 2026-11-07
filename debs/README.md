# 🔬 UFVAI — pacote Debian/Ubuntu offline

> **Versão do app:** 0.7.11 · **Revisão do pacote:** `0.7.11-offline1`
> **Data do empacotamento:** 06/11/2026
> **Motor:** OpenCode V2 — referência **2.2.5**
> **Licença:** MIT · **Autor:** Gustavo Bastos Braga (UFV) · SisPPG/UFV 10356285004

Pacote gerado a partir da árvore `UFVAI-v0.7.11/`. Substitui `0.7.10-offline1`.

---

## 📦 Pacotes disponíveis

| Arquivo | Arquitetura | Tamanho | SHA-256 |
|---|---|---|---|
| `pesquisai_0.7.11-offline1_amd64.deb` | x86_64 | 1,3 MB | `02cca8261284c6e54dd6bb07aadd094f5e8731e47dd91d058b18eee87b0ff544` |
| `pesquisai_0.7.11-offline1_arm64.deb` | aarch64 | 1,2 MB | `d10b04fc6aa3937118cb69a767ae04cfd680baff73b3f7675fc6130dd3e73e05` |

> Checksums oficiais em [`SHA256SUMS`](SHA256SUMS). O **motor OpenCode não vai
> embutido** (~240 MB): instale com `ufvai --engine-install` (sem `sudo`).

---

## ✨ Novidades do 0.7.11

| Item | O que muda |
|---|---|
| 🛡 **VPN da UFV no Colab** | OpenVPN em **user+net namespace** (`unshare -Urn`) + `slirp4netns` + **SOCKS5** em `127.0.0.1:1081`; sem `CAP_NET_ADMIN` no contêiner |
| 🎓 **Tela inicial** | depois dos Termos/onboarding: **“Você é aluno(a) da UFV?”** → painel **CPF + senha** |
| 🔐 **Credenciais** | senha nunca em log/linha de comando; “lembrar” grava **cifrado** no Drive; aviso de **1 dispositivo por CPF** |
| 🌐 **Split tunnel** | só a rede da UFV; o restante do Colab continua na internet normal |
| 🚀 **Modo total** | `redirect-gateway` + serviço do OpenCode/terminal dentro do namespace: o agente inteiro sai pela UFV (wrapper e kernel do notebook ficam fora) |
| 🔌 **Modelo local** | encaminhador `127.0.0.1:11435` → Ollama/vLLM `10.0.0.10:11434` na intranet, com DNS da VPN |
| 🧪 **Teste interno** | botão **Testar acesso** (`sistemas.ufv.br`) + detalhes técnicos (TUN, rotas, DNS, log) |

Novos endpoints: `GET /api/vpn` e `POST /api/vpn/{connect,disconnect,profile,test,forget,answer}`.
Módulo `pesquisai/vpn.py`; guia em `/opt/pesquisai/docs/VPN_UFV.md`.

---

## 🐧 Requisitos

- **Debian 11+ / Ubuntu 22.04+** (amd64 ou arm64)
- **Python 3.10+** com `python3-cryptography`, `python3-requests`, `python3-bs4`, `python3-yaml`
- **Portas livres:** `8000` (terminal), `8001` (interface)
- **Rede:** primeira instalação do motor/skills; depois funciona offline

---

## 🚀 Instalação

```bash
sha256sum -c SHA256SUMS
sudo apt install ./pesquisai_0.7.11-offline1_amd64.deb   # ou _arm64.deb
ufvai --engine-install                                    # motor OpenCode V2 (sem sudo)
ufvai --doctor
ufvai                                                     # http://localhost:8001
```

No primeiro acesso: **Termos → onboarding do provedor → terminal**.
Quem já tem chave não vê o onboarding.

---

## 🕹️ Comandos

| Comando | Efeito |
|---|---|
| `ufvai` | inicia em segundo plano e mostra a URL |
| `ufvai --foreground` | inicia no terminal (logs visíveis) |
| `ufvai --status` | estado da interface, terminal, motor e memória |
| `ufvai --doctor` | diagnóstico completo do ambiente |
| `ufvai --stop` | encerra a instância deste usuário |
| `ufvai --engine-install` | instala/atualiza o motor OpenCode V2 |
| `ufvai --version` | versão do app + versão do motor |
| `pesquisai …` | alias de compatibilidade |

---

## 📂 O que o pacote instala

```
/opt/pesquisai/                  aplicativo (código, agentes, i18n, docs)
/opt/pesquisai/bin/ttyd          terminal web embutido
/opt/pesquisai/VERSION           0.7.11-offline1
/opt/pesquisai/docs/             CHAVES_API.md · ONBOARDING.md · VPN_UFV.md · chaves-api-tutorial.html · TERMS_OF_USE.md
/usr/bin/ufvai                   comando principal
/usr/bin/pesquisai               alias
/usr/bin/ufvai-engine            instalador do motor
/usr/lib/python3/dist-packages/ufvai.pth
/usr/share/applications/ufvai.desktop
/usr/share/man/man1/ufvai.1.gz
```

Dados do usuário (nunca removidos): `~/PesquisAI/{vault,outputs,backups,logs,sessions,config}`.

---

## 🧪 Validação executada (05/11/2026)

- **Build:** `bash build-deb.sh amd64` e `bash build-deb.sh arm64` concluíram;
  `dpkg-deb -f` → `Version: 0.7.11-offline1`.
- **Conteúdo:** `pesquisai/vpn.py`, `docs/VPN_UFV.md`, `VERSION` e o
  tutorial HTML presentes no pacote.
- **Testes da versão:** `pytest -o addopts="" tests/test_v0711_vpn.py -q`
  → **22 passed**.
- **Checksums:** `SHA256SUMS` regravado com os dois pacotes desta revisão.

> A suíte completa **não** foi executada neste runtime (o ambiente reinicia sob
> carga). Valide na máquina de destino com `ufvai --doctor` e, se for usar a VPN,
> com as suas credenciais reais (o teste offline cobre o resto).

---

## 🔧 Solução de problemas

**Onboarding não aparece** — já existe chave (comportamento correto) ou a aba já
clicou em “Agora não”. Abra em nova aba/limpe o `sessionStorage`, ou use
🔌 Provedores.

**VPN não conecta** — confira CPF/senha no portal `vpn.ufvnet.ufv.br`; veja
`~/.config/ufvai/vpn/openvpn.log`; no `.deb`, instale `openvpn` e
`slirp4netns` (`sudo apt install openvpn slirp4netns`).

**“A chave deve começar com AIza…”** — o campo detecta o provedor pelo prefixo.
Confira o provedor escolhido e cole a chave inteira.

**Chave salva, mas o terminal não responde** — o serviço é reerguido em segundo
plano; aguarde alguns segundos. Se persistir:

```bash
python3 /opt/pesquisai/scripts/diag_keys_v22.py
tail -n 80 ~/PesquisAI/logs/ufvai.log
```

**Trocar o modelo padrão do Google** — `UFVAI_GOOGLE_MODEL=google/<modelo>`;
para não forçar, `UFVAI_GOOGLE_MODEL_LOCK=0`.

**Desinstalar mantendo os dados** — `sudo apt remove pesquisai`.

---

## 🛠️ Recompilar

```bash
cd UFVAI-v0.7.11
./build-deb.sh both          # amd64 + arm64
./build-deb.sh --rev offline2
```

---

## 🔐 Integridade

- Sem `pip` e sem rede no `postinst`; dados do usuário preservados.
- Chaves **cifradas** em `backups/`; nunca enviadas a terceiros pela UFVAI.
- A chave nunca é gravada em log; a API devolve apenas a versão mascarada.

---

MIT © 2026 Gustavo Bastos Braga — Universidade Federal de Viçosa.

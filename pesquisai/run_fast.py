"""
run_fast.py — Versão otimizada do PesquisAI.

Otimizações implementadas:
  1. Skills clonadas em PARALELO com ThreadPoolExecutor (8× mais rápido)
  2. Cache de repositórios — usa git pull --depth 1 se já existir
  3. apt-get update executado UMA ÚNICA vez (antes rodeava duas vezes)
  4. opencode já instalado é detectado e pula reinstalação
  5. pip install com --no-cache-dir evita overhead de cache
  6. Barra de progresso reflete economia de tempo real
  7. Skills definidas centralmente em constants.py (SKILL_REGISTRY)

v0.6.7 — POLÍTICA "PAINEL ÚNICO": nenhuma mensagem textual é impressa no
fluxo de inicialização (Colab). Marca, versão, estágios e progresso são
comunicados exclusivamente pelo painel da logomarca (_BootPanel via
progress_bar.show()). Falhas críticas vão para `logger` (stderr) para
não poluir o painel nem perder diagnóstico. O único trecho textual
restante é `_offline_keep_alive()` — modo .deb/offline, onde NÃO há
painel e os prints são a única saída (feedback exigido desde v0.6.1).

Uso:
    from run_fast import run
    run()
"""

import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from .constants import (
    DRIVE_PATH,
    SKILLS_DIR,
    SKILL_REGISTRY,
    SKILL_MAPPINGS,
    ESSENTIAL_SKILLS,
    THEME_DIR,
    AGENT_DIR,
    TUI_JSON,
    OPENCODE_CFG,
    WORK_DIR,
    WRAPPER_DIR,
    TERMINAL_PORT,
    WRAPPER_PORT,
    logger,
)
from .jokes import next_joke
from .progress_bar import show as progress, finish as progress_finish


# ── Utilitários ──────────────────────────────────────────────

def _run(cmd: str, **kw) -> subprocess.CompletedProcess:
    """Executa um comando shell e retorna o resultado."""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def _check_bin(name: str) -> bool:
    """Verifica se um binário existe no sistema."""
    if shutil.which(name):
        return True
    for d in ["~/.local/bin", "~/.npm-global/bin", "~/.opencode/bin", "/usr/local/bin"]:
        path = os.path.expanduser(os.path.join(d, name))
        if os.path.isfile(path):
            return True
    return False


# ── Etapa 1: Google Drive ────────────────────────────────────

def setup_drive() -> tuple[str, str]:
    """Monta o Google Drive e retorna (folder_path, drive_url)."""
    progress(1, 4, "Montando Google Drive...")
    try:
        from google.colab import drive, auth  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ImportError:
        # v0.6.0 (offline/.deb): persistir em ~/PesquisAI (não /tmp).
        _local = os.path.join(os.path.expanduser("~"), "PesquisAI")
        try:
            os.makedirs(_local, exist_ok=True)
            if os.access(_local, os.W_OK):
                # v0.6.0: mesma estrutura prometida pelo launcher .deb
                for _sub in ("vault", "outputs", "backups", "logs", "sessions"):
                    try:
                        os.makedirs(os.path.join(_local, _sub), exist_ok=True)
                    except Exception:
                        pass
                return _local, "https://drive.google.com/drive/my-drive"
        except Exception:
            pass
        os.makedirs("/tmp/pesquisai_work", exist_ok=True)
        return "/tmp/pesquisai_work", "https://drive.google.com/drive/my-drive"

    mounted = os.path.exists("/content/drive/My Drive")
    if not mounted:
        # v0.6.8: painel único — suprimir saída ruidosa do drive.mount
        # ("Mounted at /content/drive") que poluiria o stdout. Mensagem já
        # está no painel (progress_bar 20% → "Montando Google Drive...").
        import contextlib, io
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                drive.mount("/content/drive", force_remount=False)
        except Exception:
            try:
                drive.mount("/content/drive", force_remount=False)
            except Exception:
                pass

    os.makedirs(DRIVE_PATH, exist_ok=True)
    os.chdir(DRIVE_PATH)

    folder_url: str = "https://drive.google.com/drive/my-drive"
    try:
        auth.authenticate_user()
        service = build("drive", "v3")
        result = service.files().list(
            q="name='PesquisAI' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id)",
        ).execute()
        files = result.get("files", [])
        if files:
            folder_url = f"https://drive.google.com/drive/folders/{files[0]['id']}"
    except Exception:
        pass

    return DRIVE_PATH, folder_url


# ── Etapa 2: Dependências ────────────────────────────────────

def _install_opencode_if_missing() -> bool:
    """Instala o opencode se não estiver presente."""
    if _check_bin("opencode"):
        return True

    for cmd in [
        "curl -fsSL https://opencode.ai/install | bash",
    ]:
        r = _run(cmd, check=False)
        if r.returncode == 0 and _check_bin("opencode"):
            return True
    logger.error("Falha ao instalar o opencode — todas as tentativas falharam.")
    return False


def _install_system_deps() -> None:
    """Instala ttyd, uv, xclip, xsel em um único apt-get."""
    tasks: list[str] = []
    if not _check_bin("ttyd"):
        tasks.append("ttyd")
    if not _check_bin("xclip"):
        tasks.append("xclip")
    if not _check_bin("xsel"):
        tasks.append("xsel")
    tasks = list(set(tasks))

    if tasks:
        subprocess.run(["apt-get", "update", "-qq"], capture_output=True, text=True, check=False)
        r = subprocess.run(
            ["apt-get", "install", "-y", "-qq", *tasks],
            capture_output=True, text=True, check=False,
        )
        if r.returncode != 0:
            logger.warning("apt-get falhou (%s) — tentando download manual do ttyd...", tasks)
            subprocess.run(
                ["curl", "-fsSL",
                 "https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64",
                 "-o", "/usr/local/bin/ttyd"],
                capture_output=True, text=True, check=False,
            )
            subprocess.run(["chmod", "+x", "/usr/local/bin/ttyd"],
                           capture_output=True, text=True, check=False)

    if not _check_bin("uv"):
        _run("curl -LsSf https://astral.sh/uv/install.sh | sh", check=False)


def _install_python_deps() -> None:
    """Instala dependências Python necessárias."""
    subprocess.run(
        ["pip", "install", "--quiet", "--no-cache-dir",
         "google-api-python-client", "google-auth-httplib2",
         "google-auth-oauthlib", "cryptography", "pyyaml>=6.0"],
        capture_output=True, text=True, check=False,
    )


def _setup_theme_and_agent() -> None:
    """Configura tema escuro e agente UFVAI no OpenCode."""
    import json

    os.makedirs(THEME_DIR, exist_ok=True)
    os.makedirs(AGENT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OPENCODE_CFG), exist_ok=True)

    # v0.6.4: paleta harmonizada com a identidade UFVAI
    # (azul-escuro #141c24/#1f2831 · dourado #b29149/#d4b56a ·
    #  amarelo UFV #D1A705 · vermelho UFV #901812)
    theme = {
        "$schema": "https://opencode.ai/theme.json",
        "defs": {
            "bg0": "#141c24", "bg1": "#1a232c", "bg2": "#1f2831", "bg3": "#26313c",
            "bg4": "#2f3d4a", "fg0": "#e8e6e0", "fg1": "#a8b2ba", "fg2": "#6b7684",
            "fg3": "#33414d", "blue": "#d4b56a", "blueDim": "#8a6d33",
            "blueGlow": "#b29149", "green": "#5dba7e", "greenDark": "#1d4a2e",
            "amber": "#D1A705", "amberDark": "#5c4a10", "red": "#e07a70",
            "redDark": "#571512", "cyan": "#7fa8bd", "purple": "#c98a76",
            "synKeyword": "#7fa8bd", "synString": "#5dba7e", "synComment": "#6b7684",
            "synNumber": "#D1A705", "synFunction": "#d4b56a", "synType": "#c98a76",
            "synOp": "#a8b2ba",
        },
        "theme": {
            "primary": {"dark": "blue", "light": "blueDim"},
            "secondary": {"dark": "cyan", "light": "cyan"},
            "accent": {"dark": "purple", "light": "purple"},
            "error": {"dark": "red", "light": "red"},
            "warning": {"dark": "amber", "light": "amber"},
            "success": {"dark": "green", "light": "green"},
            "info": {"dark": "cyan", "light": "cyan"},
            "text": {"dark": "fg0", "light": "fg0"},
            "textMuted": {"dark": "fg1", "light": "fg1"},
            "background": {"dark": "bg0", "light": "bg0"},
            "backgroundPanel": {"dark": "bg1", "light": "bg1"},
            "backgroundElement": {"dark": "bg2", "light": "bg2"},
            "border": {"dark": "bg3", "light": "bg3"},
            "borderActive": {"dark": "bg4", "light": "bg4"},
            "borderSubtle": {"dark": "bg2", "light": "bg2"},
            "diffAdded": {"dark": "green", "light": "green"},
            "diffRemoved": {"dark": "red", "light": "red"},
            "diffContext": {"dark": "fg1", "light": "fg1"},
            "diffHunkHeader": {"dark": "fg2", "light": "fg2"},
            "diffHighlightAdded": {"dark": "greenDark", "light": "greenDark"},
            "diffHighlightRemoved": {"dark": "redDark", "light": "redDark"},
            "syntaxKeyword": {"dark": "synKeyword", "light": "synKeyword"},
            "syntaxString": {"dark": "synString", "light": "synString"},
            "syntaxComment": {"dark": "synComment", "light": "synComment"},
            "syntaxNumber": {"dark": "synNumber", "light": "synNumber"},
            "syntaxFunction": {"dark": "synFunction", "light": "synFunction"},
            "syntaxType": {"dark": "synType", "light": "synType"},
            "syntaxOperator": {"dark": "synOp", "light": "synOp"},
            "syntaxPunctuation": {"dark": "fg2", "light": "fg2"},
            "markdownHeading": {"dark": "blue", "light": "blue"},
            "markdownBold": {"dark": "fg0", "light": "fg0"},
            "markdownItalic": {"dark": "fg1", "light": "fg1"},
            "markdownCode": {"dark": "green", "light": "green"},
            "markdownLink": {"dark": "cyan", "light": "cyan"},
        },
    }

    with open(os.path.join(THEME_DIR, "pesquisai.json"), "w") as f:
        json.dump(theme, f, indent=2)

    # ── Tema claro (acessibilidade) ──────────────────────────
    # v0.6.4: mesma estrutura, paleta clara UFVAI (papel quente + azul-escuro).
    light_defs = {
        "bg0": "#faf9f6", "bg1": "#ffffff", "bg2": "#f1efe9", "bg3": "#e5e1d6",
        "bg4": "#d9d3c4", "fg0": "#1f2831", "fg1": "#4a5560", "fg2": "#857f72",
        "fg3": "#aaa392", "blue": "#8a6d33", "blueDim": "#d4b56a",
        "blueGlow": "#b29149", "green": "#2e7d32", "greenDark": "#a5d6a7",
        "amber": "#a67c00", "amberDark": "#ffcc80", "red": "#c0392b",
        "redDark": "#ef9a9a", "cyan": "#4a7c8c", "purple": "#9a5a48",
        "synKeyword": "#4a7c8c", "synString": "#2e7d32", "synComment": "#857f72",
        "synNumber": "#a67c00", "synFunction": "#8a6d33", "synType": "#9a5a48",
        "synOp": "#4a5560",
    }
    theme_light = {**theme, "defs": light_defs}
    with open(os.path.join(THEME_DIR, "pesquisai-light.json"), "w") as f:
        json.dump(theme_light, f, indent=2)

    # Tema padrão: respeita escolha persistida em tui.json (default = escuro)
    try:
        existing_tui = json.load(open(TUI_JSON))
    except Exception:
        existing_tui = {}
    tui_theme = existing_tui.get("theme", "pesquisai")
    with open(TUI_JSON, "w") as f:
        json.dump({"$schema": "https://opencode.ai/tui.json", "theme": tui_theme}, f, indent=2)

    agents_md = os.path.join(os.path.dirname(os.path.dirname(__file__)), "AGENTS.md")
    content = open(agents_md, encoding="utf-8").read() if os.path.exists(agents_md) else "# PesquisAI"

    # ── Injetar instruções de autopilot no prompt do agente ───
    # Isto faz o agente SALVAR AUTONOMAMENTE no vault do Obsidian
    # sem precisar que o usuário peça.
    autopilot_instructions = """

## 🤖 AUTOPILOT — Salvamento Autônomo (v0.5.1+)

Você tem uma memória persistente via Obsidian vault no Google Drive.
Use-a AUTONOMAMENTE — **não espere o usuário pedir para salvar**.

### O que você DEVE fazer automaticamente:

1. **ANTES de responder** — recorde informações relevantes:
   ```python
   from pesquisai.obsidian.autopilot import recall
   results = recall("tema da pergunta do usuário")
   # Se houver resultados, use-os como contexto
   ```

2. **DEPOIS de concluir uma tarefa** — salve o resultado:
   ```python
   from pesquisai.obsidian.autopilot import save
   save(
       title="Título da nota",
       body="## Resultados\\n\\n- ...\\n\\n[DADO CONFIRMADO]",
       tags=["pesquisai/ibge"],
       template="research",
   )
   ```

3. **Ao usar uma skill** — registre:
   ```python
   from pesquisai.obsidian.autopilot import log_skill
   log_skill("ibge-br")
   ```

4. **Ao gerar um arquivo** — registre:
   ```python
   from pesquisai.obsidian.autopilot import log_file
   log_file("resultado.csv")
   ```

5. **Ao final da conversa** — log de sessão:
   ```python
   from pesquisai.obsidian.autopilot import end_session
   end_session(summary="Resumo do que foi feito nesta sessão")
   ```

### Quando salvar AUTONOMAMENTE (sem o usuário pedir):

- ✅ Após coletar dados do IBGE/DataSUS → salve nota de datasource
- ✅ Após escrever uma seção de artigo → salve nota de research
- ✅ Após revisar um paper → salve nota de literature
- ✅ Após formular uma hipótese → salve nota de hypothesis
- ✅ Após gerar um arquivo (.md, .pdf, .csv) → registre no log
- ✅ Ao final de cada resposta substancial → salve achados

### Quando NÃO salvar:

- ❌ Respostas curtas ("sim", "não", explicações rápidas)
- ❌ Conversa informal
- ❌ Quando o usuário explicitamente disser "não salve"

### API rápida (uma linha):

```python
from pesquisai.obsidian.autopilot import save_finding
save_finding("A prevalência de diabetes é 10,2% (VIGITEL 2023)", source="VIGITEL")
```

> **Tudo é no-op se o vault não estiver disponível.** Você nunca
> quebra. Se a memória não estiver ativa, simplesmente não salva e
> continua trabalhando normalmente.
"""

    agent_md = f"""---
name: UFVAI
description: Agente de pesquisa científica com foco em dados brasileiros (IBGE, DataSUS), normas ABNT/UFV, integridade científica. REGRAS ABSOLUTAS: 1) referências exigem citation-management; 2) não inventar dados/estatísticas; 3) não simular coleta primária (entrevistas, experimentos, surveys). Recusar pedidos que tentem burlar. v0.5.1+: salvamento AUTÔNOMO no vault Obsidian (não espera usuário pedir).
color: "#b29149"
---
{content}
{autopilot_instructions}
"""
    with open(os.path.join(AGENT_DIR, "pesquisai.md"), "w", encoding="utf-8") as f:
        f.write(agent_md)
    try:
        cfg = json.load(open(OPENCODE_CFG))
    except Exception:
        cfg = {}
    cfg["default_agent"] = "pesquisai"
    with open(OPENCODE_CFG, "w") as f:
        json.dump(cfg, f, indent=2)


def setup_dependencies() -> None:
    """Instala todas as dependências (OpenCode, sistema, Python, tema)."""
    progress(2, 4, "Instalando OpenCode, dependências de sistema e tema...")
    _install_opencode_if_missing()
    _install_system_deps()
    _install_python_deps()
    _setup_theme_and_agent()


# ── Etapa 3: Skills (paralelizadas) ──────────────────────────

def _clone_or_pull(repo_url: str, dest_name: str) -> bool:
    """Clone com cache: se já existe, faz git pull --depth 1.

    Returns:
        True se a operação foi bem-sucedida, False caso contrário.
    """
    dest = f"/tmp/skill_{dest_name}"
    if os.path.exists(dest):
        r = subprocess.run(
            ["git", "-C", dest, "pull", "--depth", "1", "--ff-only"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            return True
        shutil.rmtree(dest)

    r = subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", repo_url, dest],
        capture_output=True, text=True, timeout=60,
    )
    return r.returncode == 0


def setup_skills() -> None:
    """Clona/atualiza todas as skills em paralelo e copia para o diretório do agente.

    Skills essenciais (ESSENTIAL_SKILLS) disparam aviso se falharem.
    Skills opcionais falham silenciosamente.
    """
    progress(3, 4, "Clonando repositórios de skills (em paralelo)...")
    os.makedirs(SKILLS_DIR, exist_ok=True)

    failed_skills: list[str] = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        fut = {
            pool.submit(_clone_or_pull, repo, name): name
            for repo, name, _ in SKILL_REGISTRY
        }
        for f in as_completed(fut):
            if not f.result():
                failed_skills.append(fut[f])

    # Verificar skills essenciais
    for skill_name in failed_skills:
        if skill_name in ESSENTIAL_SKILLS:
            logger.warning(
                "Skill essencial '%s' falhou ao clonar. "
                "Algumas funcionalidades podem não estar disponíveis.",
                skill_name,
            )

    # Copiar para o diretório do agente
    for src, dest_name in SKILL_MAPPINGS:
        dest = os.path.join(SKILLS_DIR, dest_name)
        if os.path.exists(src):
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest, dirs_exist_ok=True)


# ── Etapa 3.5: Obsidian Vault (autopilot) ─────────────────────

def setup_obsidian_vault() -> None:
    """Inicializa o vault do Obsidian no Google Drive (autopilot).

    Cria a estrutura de pastas, a daily note de hoje, o MOC raiz,
    e inicia a sessão de log automático. Tudo é no-op se falhar.
    v0.6.7: sem prints — o estado é visível na interface; falha vai
    para o logger e o boot continua sem memória.
    """
    try:
        from pesquisai.obsidian.autopilot import auto_init
        auto_init()
    except Exception as exc:
        logger.warning("Obsidian memory: falha ao inicializar (%s) — continuando sem memória", exc)


# ── Etapa 4: Launch ───────────────────────────────────────────

def setup_launch(folder_path: str, drive_url: str) -> str:
    """Inicia os servidores e a interface web.

    Returns:
        URL do banner de acesso.
    """
    progress(4, 4, "Iniciando servidores e interface web...")
    from pesquisai import launch_app as _la
    from pesquisai.launch_app import launch, set_drive_info, show_ready_message, show_launch_button
    set_drive_info(folder_path, drive_url)
    banner_url = launch()
    progress_finish()
    # v0.6.7: no Colab o card final (logomarca + botão) substitui o antigo
    # badge verde "✨ UFVAI pronto!"; fora do Colab mantém o print legado.
    if not getattr(_la, "IN_COLAB", False):
        show_ready_message()
    show_launch_button(banner_url)
    return banner_url


# ── Orquestrador ──────────────────────────────────────────────

def _offline_keep_alive(banner_url: str) -> None:
    """v0.6.3: mantém o processo vivo no modo offline (.deb/local).

    O servidor HTTP do wrapper roda em thread daemon; se run() retornasse,
    o interpretador encerraria o processo e a porta 8001 cairia logo após a
    inicialização (ERR_CONNECTION_REFUSED). No Colab o kernel permanece vivo,
    então isto só se aplica fora dele.

    Desabilitar (scripts/testes): export UFVAI_NO_KEEPALIVE=1
    """
    import signal

    def _sigterm(_sig, _frm):
        # Encerramento limpo via `kill <pid>` (launcher grava o PID)
        print("\n👋 UFVAI encerrado (SIGTERM).")
        raise SystemExit(0)

    try:
        signal.signal(signal.SIGTERM, _sigterm)
    except Exception:
        pass

    print()
    print("🧬 UFVAI rodando em segundo plano nesta máquina.")
    print(f"   Interface: {banner_url}  ·  Terminal: http://localhost:{TERMINAL_PORT}")
    if os.environ.get("UFVAI_NO_KEEPALIVE", "").strip().lower() in ("1", "true", "yes", "on"):
        print("ℹ️  UFVAI_NO_KEEPALIVE=1 — processo NÃO será mantido vivo.")
        return
    print("   Para encerrar (foreground): Ctrl+C  ·  (background): kill $(cat ~/PesquisAI/pesquisai.pid)")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n👋 Encerrando UFVAI… até a próxima! 🧬")


def run() -> None:
    """Orquestrador principal do PesquisAI.

    Sequência: Drive → Dependências → Skills → Obsidian vault → Launch.
    v0.6.7: nenhuma saída textual — todo o feedback visual vem do painel
    de boot da logomarca (_BootPanel), do clone até os 100% + botão.
    """
    progress(0, 4, "Preparando...")

    # v0.6.7: o banner textual "🧑‍🔬 PESQUISAI (MODO RÁPIDO)" foi aposentado —
    # o painel de boot da logomarca (display "ufvai_boot_panel") já comunica
    # marca, versão e progresso desde o primeiro segundo do carregamento.

    folder_path, drive_url = setup_drive()
    setup_dependencies()
    setup_skills()
    setup_obsidian_vault()
    banner_url = setup_launch(folder_path, drive_url)

    # v0.6.3: fora do Colab, mantém o processo vivo para que a interface
    # continue acessível (threads daemon morreriam com o fim de run()).
    if not os.path.isdir("/content/drive"):
        from .launch_app import IN_COLAB as _in_colab
        if not _in_colab:
            _offline_keep_alive(banner_url)


if __name__ == "__main__":
    run()

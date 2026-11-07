# ═══════════════════════════════════════════════════════════════════════
# UFVAI 0.7.11 — BOOT LOCAL (usa a árvore do Drive, sem git clone)
# ═══════════════════════════════════════════════════════════════════════
# Use esta célula NO LUGAR da célula antiga que fazia `git clone` do
# repositório. Ela copia /content/drive/My Drive/PesquisAI/UFVAI-v0.7.11
# para /tmp/pesquisai e inicia o UFVAI.
#
# IMPORTANTE: rode depois de um **Runtime → Restart session** (ou
# "Desconectar e excluir ambiente"). Sem reiniciar, o wrapper antigo
# (0.7.10) ainda está na porta 8001 e a nova célula não consegue subir.
# ═══════════════════════════════════════════════════════════════════════
import os
import sys
import shutil
import subprocess

# 1) Drive montado
try:
    from google.colab import drive
    if not os.path.isdir("/content/drive/MyDrive"):
        drive.mount("/content/drive")
except Exception:
    pass

SRC = "/content/drive/My Drive/PesquisAI/UFVAI-v0.7.11"
DST = "/tmp/pesquisai"

if not os.path.isdir(SRC):
    raise SystemExit(f"Árvore não encontrada: {SRC}")

# 2) copia a árvore local (sem .git/debs/deliverable)
if os.path.exists(DST):
    shutil.rmtree(DST)
shutil.copytree(
    SRC, DST,
    ignore=shutil.ignore_patterns(
        ".git", "debs", "deliverable", "__pycache__",
        "*.pyc", ".pytest_cache", "*.egg-info",
    ),
)

os.chdir(DST)
sys.path.insert(0, DST)

# 3) instala o pacote `pesquisai` a partir da árvore copiada
for _cmd in (
    [sys.executable, "-m", "pip", "install", "-q", "--no-deps", "-e", DST],
    [sys.executable, "-m", "pip", "install", "-q", "-e", DST],
):
    try:
        subprocess.run(_cmd, check=False, timeout=900)
    except Exception:
        pass

# 4) confere a versão antes de subir
try:
    from pesquisai.__version__ import __version__
    print(f"UFVAI {__version__} — árvore {DST}")
except Exception as exc:
    print(f"[AVISO] não foi possível ler a versão: {exc}")

# 5) sobe o UFVAI
from main import run
run()

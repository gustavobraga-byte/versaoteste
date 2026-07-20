"""
main.py — Ponto de entrada único do PesquisAI v0.6.0 (WEBCLI Mode).

v0.6.0 WEBCLI: usa o `opencode web` (webcli oficial) em vez de ttyd.
O `opencode web` já serve a interface web completa do opencode — não
precisamos mais de FastAPI, React, WebSocket nem nada customizado.

Uso:
    python main.py                  # Inicia opencode web (padrão)
    python main.py --port 8080      # Customiza porta
    python main.py --no-setup       # Pula setup (assume já feito)
    python main.py --check          # Verifica opencode
    python main.py --version        # Mostra versão
    python main.py --background     # Roda em background (retorna PID)

No Google Colab:
    !python main.py
"""
import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request

from pesquisai.constants import VERSION, WEBCLI_PORT, is_colab
from pesquisai.opencode_utils import (
    find_opencode, opencode_installed, get_opencode_version,
    install_opencode,
)


def check_opencode_installation() -> dict:
    """Verifica se o opencode CLI está instalado e funcional."""
    bin_path = find_opencode()
    return {
        "installed": bin_path is not None,
        "bin": bin_path,
        "version": get_opencode_version() if bin_path else None,
    }


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """Aguarda o servidor opencode web ficar disponível."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = urllib.request.urlopen(url, timeout=2)
            if r.status == 200:
                return True
        except Exception:
            time.sleep(0.5)
    return False


def run_webcli(port: int, hostname: str = "0.0.0.0", background: bool = False):
    """Inicia o opencode web (webcli oficial).

    Args:
        port: Porta para servir a UI
        hostname: Hostname para bind (0.0.0.0 para acesso externo)
        background: Se True, retorna o subprocess sem bloquear
    """
    opencode_bin = find_opencode()
    if not opencode_bin:
        print("❌ opencode CLI não encontrado.")
        print("   Tentando instalar...")
        if not install_opencode():
            print("❌ Falha na instalação. Tente manualmente:")
            print("   curl -fsSL https://opencode.ai/install | bash")
            sys.exit(1)
        opencode_bin = find_opencode()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print(f"║  🔬 PesquisAI v{VERSION} — WEBCLI Mode                       ║")
    print("║                                                              ║")
    print("║  ✅ Interface web oficial do opencode                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"🚀 Iniciando opencode web na porta {port}...")
    print(f"   Binário: {opencode_bin}")
    print(f"   Versão:  {get_opencode_version()}")
    print()

    # Monta comando. mdns=false para não descobrir via mDNS.
    # --cors=* para permitir CORS de qualquer origem.
    cmd = [
        opencode_bin,
        "web",
        "--port", str(port),
        "--hostname", hostname,
        "--cors", "*",
    ]

    if background:
        # Inicia em background
        log_file = os.path.expanduser("~/.config/pesquisai/webcli.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        log = open(log_file, "w")
        proc = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
        print(f"   PID: {proc.pid}")
        print(f"   Log: {log_file}")
        # Salva PID para referência
        pid_file = os.path.expanduser("~/.config/pesquisai/webcli.pid")
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
        # Aguarda o servidor ficar pronto
        url = f"http://127.0.0.1:{port}/"
        print(f"   Aguardando {url} ...")
        if wait_for_server(url, timeout=30):
            print(f"   ✅ Servidor pronto em {url}")
        else:
            print(f"   ⚠️  Timeout aguardando {url}")
        return proc

    # Modo foreground — substitui o processo atual
    try:
        os.execvp(opencode_bin, cmd)
    except FileNotFoundError:
        print(f"❌ Binário não encontrado: {opencode_bin}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="PesquisAI v0.6.0 — WEBCLI Mode (opencode web, sem ttyd)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py                  Inicia opencode web (padrão, porta 8000)
  python main.py --port 8080      Customiza porta
  python main.py --no-setup       Pula setup (assume skills já instaladas)
  python main.py --background     Roda em background (retorna PID)
  python main.py --check          Verifica opencode
  python main.py --version        Mostra versão

Ambientes:
  Google Colab   →  !python main.py  (use output.serve_kernel_port_as_window)
  Local          →  python main.py  (abre http://localhost:8000)
""",
    )
    parser.add_argument(
        "--port", type=int, default=WEBCLI_PORT,
        help=f"Porta do webcli (padrão: {WEBCLI_PORT})",
    )
    parser.add_argument(
        "--hostname", default="0.0.0.0",
        help="Hostname para bind (padrão: 0.0.0.0)",
    )
    parser.add_argument(
        "--no-setup", action="store_true",
        help="Pula o setup (assume opencode e skills já instalados)",
    )
    parser.add_argument(
        "--background", action="store_true",
        help="Roda em background (não bloqueia o terminal)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Verifica instalação do opencode e sai",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Mostra versão e sai",
    )

    args = parser.parse_args()

    if args.version:
        print(f"PesquisAI v{VERSION} (WEBCLI Mode)")
        sys.exit(0)

    if args.check:
        info = check_opencode_installation()
        if info["installed"]:
            print(f"✅ opencode encontrado: {info['bin']}")
            print(f"   Versão: {info['version']}")
            sys.exit(0)
        else:
            print("❌ opencode NÃO encontrado.")
            print("   Instale com: curl -fsSL https://opencode.ai/install | bash")
            sys.exit(1)

    # 1. Setup (a menos que --no-setup)
    if not args.no_setup:
        from pesquisai.setup import setup
        try:
            setup()
        except KeyboardInterrupt:
            print("\n⚠️  Setup interrompido.")
            sys.exit(1)

    # 2. Inicia opencode web
    if is_colab():
        print("📓 Ambiente: Google Colab")
        print(f"   Use output.serve_kernel_port_as_window({args.port}) para abrir a UI.")
        print(f"   Ou use localtunnel/ngrok para expor publicamente.")
        print()

    run_webcli(port=args.port, hostname=args.hostname, background=args.background)


if __name__ == "__main__":
    main()

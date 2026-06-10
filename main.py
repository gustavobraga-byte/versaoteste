import sys
import os

from constants import logger
from jokes import next_joke
from progress_bar import show as progress, finish as progress_finish


def run():
    progress(0, 4, "Preparando...")

    print("\n" + "=" * 50)
    print("  🧑‍🔬  INICIANDO PESQUISAI")
    print("=" * 50)

    try:
        print(f"\n{next_joke('administracao')}")
        progress(1, 4, "Montando Google Drive...")
        from setup_drive import mount_drive
        folder_path, drive_url = mount_drive()
    except Exception as e:
        logger.error("Falha na montagem do Drive: %s", e)
        print("\n❌ Erro ao configurar o Google Drive. Verifique as permissões e tente novamente.")
        return

    try:
        print(f"\n{next_joke('administracao')}")
        progress(2, 4, "Instalando OpenCode, tema e dependências...")
        from setup_dependencies import run_all as setup_deps
        setup_deps()
    except Exception as e:
        logger.error("Falha na instalação de dependências: %s", e)
        print("\n❌ Erro ao instalar dependências. Continuando com as já instaladas.")

    try:
        print(f"\n{next_joke('administracao')}")
        progress(3, 4, "Clonando repositórios de skills...")
        from setup_skills import install_skills
        install_skills()
    except Exception as e:
        logger.error("Falha na instalação de skills: %s", e)
        print("\n❌ Erro ao instalar skills. Continuando com as já instaladas.")

    try:
        print(f"\n{next_joke('administracao')}")
        progress(4, 4, "Iniciando servidores e interface web...")
        from launch_app import launch, set_drive_info, show_ready_message, show_launch_button
        set_drive_info(folder_path, drive_url)
        banner_url = launch()
    except Exception as e:
        logger.error("Falha ao lançar interface: %s", e)
        print("\n❌ Erro ao iniciar a interface web.")
        return

    progress_finish()
    show_ready_message()
    show_launch_button(banner_url)


if __name__ == "__main__":
    run()

"""Sistema de internacionalização (i18n) do PesquisAI.

Suporta pt_BR (padrão) e en_US. Use a função _() para strings
visíveis ao usuário. Defina PESQUISAI_LOCALE no ambiente para trocar.
"""

import os
import json


_locale = os.environ.get("PESQUISAI_LOCALE", "pt_BR")

TRANSLATIONS = {
    "pt_BR": {
        "loading": "Carregando o PesquisAI...",
        "starting": "INICIANDO PESQUISAI",
        "drive_mounting": "Configurando Google Drive...",
        "drive_mounted": "Drive montado com sucesso!",
        "drive_not_colab": "Não está rodando no Google Colab. Pulando montagem do Drive.",
        "drive_error": "Erro ao configurar o Google Drive. Verifique as permissões e tente novamente.",
        "drive_already_mounted": "Google Drive já está montado!",
        "drive_auth": "Autenticação concluída!",
        "drive_already_auth": "Já autenticado!",
        "deps_installing": "Instalando dependências...",
        "deps_opencode": "Instalando OpenCode...",
        "deps_uv": "Instalando uv...",
        "deps_clipboard": "Instalando ferramentas de clipboard...",
        "deps_python": "Instalando dependências Python...",
        "deps_done": "Dependências e configurações concluídas!",
        "deps_error": "Erro ao instalar dependências. Continuando com as já instaladas.",
        "skills_installing": "Instalando skills...",
        "skills_copying": "Copiando skills para o diretório do agente...",
        "skills_done": "Todas as skills instaladas com sucesso!",
        "skills_error": "Erro ao instalar skills. Continuando com as já instaladas.",
        "launch_ttyd": "Instalando ttyd...",
        "launch_ttyd_done": "ttyd instalado.",
        "launch_terminal": "Terminal iniciado.",
        "launch_wrapper": "Servidor wrapper iniciado na porta",
        "launch_ready": "PesquisAI pronto!",
        "launch_error": "Erro ao iniciar a interface web.",
        "setup_configure_error": "Erro ao configurar. Tentando continuar...",
        "progress_drive": "Google Drive",
        "progress_deps": "Dependências",
        "progress_skills": "Skills",
        "progress_launch": "Inicializando",
        "health_ok": "ok",
        "key_loaded": "Keys carregadas do Drive",
        "key_restored": "Config do OpenCode restaurada do Drive.",
        "backup_dir": "Diretório de backups",
        "session_exported": "Sessão exportada com sucesso.",
        "session_imported": "Sessão importada com sucesso.",
        "no_session": "Nenhuma sessão encontrada para exportar.",
        "project_created": "Projeto criado",
        "project_switched": "Projeto alterado para",
        "project_listed": "Projetos disponíveis",
    },
    "en_US": {
        "loading": "Loading PesquisAI...",
        "starting": "STARTING PESQUISAI",
        "drive_mounting": "Setting up Google Drive...",
        "drive_mounted": "Drive mounted successfully!",
        "drive_not_colab": "Not running on Google Colab. Skipping Drive mount.",
        "drive_error": "Error setting up Google Drive. Check permissions and try again.",
        "drive_already_mounted": "Google Drive is already mounted!",
        "drive_auth": "Authentication complete!",
        "drive_already_auth": "Already authenticated!",
        "deps_installing": "Installing dependencies...",
        "deps_opencode": "Installing OpenCode...",
        "deps_uv": "Installing uv...",
        "deps_clipboard": "Installing clipboard tools...",
        "deps_python": "Installing Python dependencies...",
        "deps_done": "Dependencies and configuration complete!",
        "deps_error": "Error installing dependencies. Continuing with existing ones.",
        "skills_installing": "Installing skills...",
        "skills_copying": "Copying skills to agent directory...",
        "skills_done": "All skills installed successfully!",
        "skills_error": "Error installing skills. Continuing with installed ones.",
        "launch_ttyd": "Installing ttyd...",
        "launch_ttyd_done": "ttyd installed.",
        "launch_terminal": "Terminal started.",
        "launch_wrapper": "Wrapper server started on port",
        "launch_ready": "PesquisAI ready!",
        "launch_error": "Error starting web interface.",
        "setup_configure_error": "Error configuring. Attempting to continue...",
        "progress_drive": "Google Drive",
        "progress_deps": "Dependencies",
        "progress_skills": "Skills",
        "progress_launch": "Initializing",
        "health_ok": "ok",
        "key_loaded": "Keys loaded from Drive",
        "key_restored": "OpenCode config restored from Drive.",
        "backup_dir": "Backup directory",
        "session_exported": "Session exported successfully.",
        "session_imported": "Session imported successfully.",
        "no_session": "No sessions found to export.",
        "project_created": "Project created",
        "project_switched": "Switched to project",
        "project_listed": "Available projects",
    },
}


def _(key):
    return TRANSLATIONS.get(_locale, TRANSLATIONS["pt_BR"]).get(key, key)


def set_locale(locale):
    global _locale
    if locale in TRANSLATIONS:
        _locale = locale

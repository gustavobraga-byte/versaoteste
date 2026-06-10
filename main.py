"""Ponto de entrada do PesquisAI. Orquestra o pipeline de inicialização."""

import sys
import os

from constants import logger
from jokes import next_joke
from i18n import _, set_locale


def _in_colab():
    try:
        import google.colab
        return True
    except ImportError:
        return False


def _maybe_html(html):
    if _in_colab():
        from IPython.display import display, HTML
        display(HTML(html))
    else:
        import re
        print(re.sub(r'<[^>]+>', '', html).strip())


class ProgressTracker:
    def __init__(self):
        self.stages = [
            (_("progress_drive"), 0, 20),
            (_("progress_deps"), 20, 50),
            (_("progress_skills"), 50, 80),
            (_("progress_launch"), 80, 100),
        ]
        self.current = 0
        self._show_loading()

    def _show_loading(self):
        if not _in_colab():
            return
        from IPython.display import display, HTML, clear_output
        clear_output(wait=True)
        from html_template import render_loading_html
        display(HTML(render_loading_html()))

    def _update_display(self, pct, stage_name, detail=""):
        if not _in_colab():
            return
        from IPython.display import display, HTML, clear_output
        clear_output(wait=True)
        from html_template import render_loading_html
        bar_width = 40
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        html = f"""<style>
@keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
body {{ background: #0b0d0f; color: #dde4e8; font-family: 'DM Mono', monospace; }}
.progress-container {{ padding: 40px 20px; text-align: center; }}
.progress-bar {{ width: 80%; max-width: 600px; margin: 20px auto;
  background: #191e21; border-radius: 8px; overflow: hidden; height: 24px; }}
.progress-fill {{ height: 100%; width: {pct}%;
  background: linear-gradient(90deg, #4fc3f7, #5dba7e);
  transition: width 0.5s ease; border-radius: 8px; }}
.progress-label {{ color: #4fc3f7; font-size: 14px; margin-top: 12px; }}
.progress-detail {{ color: #7e8f97; font-size: 12px; margin-top: 4px; animation: pulse 1.5s infinite; }}
.progress-pct {{ color: #5dba7e; font-size: 13px; margin-top: 8px; }}
</style>
<div class="progress-container">
  <div style="font-size: 24px; margin-bottom: 8px;">🔬</div>
  <div style="color: #4fc3f7; font-size: 16px; font-weight: 600;">{_("starting")}</div>
  <div class="progress-bar"><div class="progress-fill"></div></div>
  <div class="progress-label">{stage_name}</div>
  <div class="progress-pct">{pct}%</div>
  <div class="progress-detail">{detail}</div>
</div>"""
        display(HTML(html))

    def update(self, stage_index, detail=""):
        if stage_index < len(self.stages):
            name, start, end = self.stages[stage_index]
            pct = start
            self._update_display(pct, name, detail)

    def advance(self, stage_index, detail=""):
        if stage_index < len(self.stages):
            name, start, end = self.stages[stage_index]
            self._update_display(end, name, detail)


def run():
    if _in_colab():
        colab_locale = os.environ.get("PESQUISAI_LOCALE", "pt_BR")
        set_locale(colab_locale)

    progress = ProgressTracker()

    print("\n" + "=" * 50)
    print(f"  🧑‍🔬  {_('starting')}")
    print("=" * 50)

    folder_path = "/tmp/pesquisai_work"
    drive_url = "https://drive.google.com/drive/my-drive"

    try:
        progress.update(0, _("drive_mounting"))
        from setup_drive import mount_drive
        folder_path, drive_url = mount_drive()
        progress.advance(0)
    except Exception as e:
        logger.error("Falha na montagem do Drive: %s", e)
        print(f"\n❌ {_('drive_error')}")
        return

    try:
        progress.update(1, _("deps_installing"))
        from setup_dependencies import run_all as setup_deps
        setup_deps()
        progress.advance(1)
    except Exception as e:
        logger.error("Falha na instalação de dependências: %s", e)
        print(f"\n❌ {_('deps_error')}")

    try:
        progress.update(2, _("skills_installing"))
        from setup_skills import install_skills
        install_skills()
        progress.advance(2)
    except Exception as e:
        logger.error("Falha na instalação de skills: %s", e)
        print(f"\n❌ {_('skills_error')}")

    try:
        progress.update(3, _("progress_launch"))
        from launch_app import launch, set_drive_info
        from html_template import set_templates_dir
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        if os.path.isdir(templates_dir):
            set_templates_dir(templates_dir)
        set_drive_info(folder_path, drive_url)
    except Exception as e:
        logger.error("Falha ao configurar info do Drive para launch: %s", e)
        print(f"\n❌ {_('setup_configure_error')}")

    try:
        launch()
    except Exception as e:
        logger.error("Falha ao lançar interface: %s", e)
        print(f"\n❌ {_('launch_error')}")

    print()


if __name__ == "__main__":
    run()

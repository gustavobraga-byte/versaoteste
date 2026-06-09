"""Renderização de templates HTML para a interface web do PesquisAI."""

TEMPLATES_DIR = None


def set_templates_dir(path):
    global TEMPLATES_DIR
    TEMPLATES_DIR = path


def _load_template(name):
    if TEMPLATES_DIR:
        import os
        path = os.path.join(TEMPLATES_DIR, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
    return ""


def render_wrapper_html(terminal_url, drive_url):
    tpl = _load_template("wrapper.html")
    if tpl:
        return tpl.replace("{{TERMINAL_URL}}", terminal_url).replace("{{DRIVE_URL}}", drive_url)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PesquisAI</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0b0d0f; color: #dde4e8; font-family: 'DM Mono', monospace; }}
  .header {{ display: flex; align-items: center; justify-content: space-between;
    padding: 8px 20px; background: #131618; border-bottom: 1px solid #263035; }}
  .header h1 {{ font-size: 14px; color: #4fc3f7; font-weight: 600; }}
  .header a {{ color: #7e8f97; text-decoration: none; font-size: 12px; margin-left: 16px; }}
  .header a:hover {{ color: #4fc3f7; }}
  iframe {{ width: 100%; height: calc(100vh - 41px); border: none; }}
</style>
</head>
<body>
<div class="header">
  <h1>🔬 PesquisAI</h1>
  <div>
    <a href="{terminal_url}" target="_blank">Terminal</a>
    <a href="{drive_url}" target="_blank">Drive</a>
    <a href="/api/health">Status</a>
  </div>
</div>
<iframe src="{terminal_url}"></iframe>
</body>
</html>"""


def render_launch_button_html(banner_url):
    tpl = _load_template("launch_button.html")
    if tpl:
        return tpl.replace("{{BANNER_URL}}", banner_url)

    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@500;700&family=Syne:wght@700;800&display=swap');
@keyframes pulse-glow {{
  0%, 100% {{ box-shadow: 0 0 20px rgba(79,195,247,0.3), 0 4px 12px rgba(0,0,0,0.3); }}
  50% {{ box-shadow: 0 0 40px rgba(79,195,247,0.6), 0 6px 20px rgba(0,0,0,0.4); }}
}}
.btn-container {{
  display: flex; justify-content: center; padding: 20px; margin-top: 10px;
}}
.pesquisai-launch {{
  display: inline-flex; align-items: center; justify-content: center;
  gap: 16px; padding: 24px 56px;
  font-family: "Syne", sans-serif; font-size: 22px; font-weight: 800;
  letter-spacing: 0.08em; color: #0d0f10;
  background: linear-gradient(135deg, #4fc3f7 0%, #29b6f6 50%, #03a9f4 100%);
  border: none; border-radius: 14px; cursor: pointer; text-decoration: none;
  animation: pulse-glow 2.5s ease-in-out infinite;
}}
.pesquisai-launch:hover {{ transform: translateY(-4px) scale(1.02); filter: brightness(1.1); }}
.btn-main {{ font-size: 22px; font-weight: 800; }}
.btn-icon {{ font-size: 28px; }}
.arrow {{ font-size: 28px; transition: transform 0.2s ease; }}
.pesquisai-launch:hover .arrow {{ transform: translateX(8px); }}
</style>
<div class="btn-container">
  <a href="{banner_url}" target="_blank" class="pesquisai-launch">
    <span class="btn-icon">🚀</span>
    <span class="btn-main">ABRIR O PESQUISAI</span>
    <span class="arrow">→</span>
  </a>
</div>"""


def render_ready_badge_html():
    tpl = _load_template("ready_badge.html")
    if tpl:
        return tpl

    return """<style>
@keyframes glow {
    0%, 100% { box-shadow: 0 0 20px rgba(93, 186, 126, 0.3); }
    50% { box-shadow: 0 0 40px rgba(93, 186, 126, 0.6); }
}
.ready-container {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; padding: 20px 20px 0px 20px;
}
.ready-badge {
    display: inline-flex; align-items: center; gap: 12px;
    padding: 16px 32px; background: rgba(93, 186, 126, 0.12);
    border: 2px solid rgba(93, 186, 126, 0.4);
    border-radius: 12px; animation: glow 2s ease-in-out infinite;
}
.ready-icon { font-size: 28px; }
.ready-text {
    font-family: 'DM Mono', monospace; font-size: 18px;
    font-weight: 600; color: #5dba7e;
}
</style>
<div class="ready-container">
    <div class="ready-badge">
        <span class="ready-icon">✨</span>
        <span class="ready-text">PesquisAI pronto!</span>
    </div>
</div>"""


def render_loading_html():
    return """<style>
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
.loading-container {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 60px 20px;
}
.spinner {
    width: 56px; height: 56px;
    border: 4px solid rgba(79, 195, 247, 0.12);
    border-top-color: #4fc3f7;
    border-radius: 50%; animation: spin 1s linear infinite;
    margin-bottom: 24px;
}
.loading-text {
    color: #4fc3f7; font-family: monospace; font-size: 15px;
    animation: pulse 1.5s ease-in-out infinite;
}
</style>
<div class="loading-container">
    <div class="spinner"></div>
    <div class="loading-text" id="progress-text">Carregando o PesquisAI...</div>
</div>"""

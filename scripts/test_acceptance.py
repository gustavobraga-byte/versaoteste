"""test_acceptance.py — aceitação completa da web do UFVAI (dentro do wrapper).

Percorre o caminho real do usuário: abre a interface (wrapper com as duas
molduras), alterna para a web, confere o catálogo de modelos, os menus `/` e
`@` (habilidades), envia uma mensagem numa sessão nova e acompanha o aviso
"Trabalhando…" até ele sumir, além do botão de sessões e do tema.

    python3 scripts/test_acceptance.py
"""

import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

WRAPPER_HTML = Path("/tmp/pesquisai-wrapper/index.html")


def local_copy() -> str:
    """Cópia do wrapper com as URLs do Colab trocadas por localhost."""
    src = WRAPPER_HTML.read_text(encoding="utf-8", errors="replace")
    src = re.sub(r"https://8002-[^\"'\s]+", "http://127.0.0.1:8003", src)
    src = re.sub(r"https://8003-[^\"'\s]+", "http://127.0.0.1:8003", src)
    src = re.sub(r"https://8000-[^\"'\s]+", "http://127.0.0.1:8000", src)
    out = Path("/tmp/test-wrapper")
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(src, encoding="utf-8")
    return str(out / "index.html")


async def main():
    html = local_copy()
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
        await page.goto(f"http://127.0.0.1:8099/{html.split('/')[-1]}", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        # alterna para a web
        await page.evaluate("() => { const b=document.getElementById('console-toggle'); if(b) b.click(); }")
        await page.wait_for_timeout(7000)
        web = next((f for f in page.frames if ":8003" in f.url), None)
        if not web:
            print("✗ a moldura da web não carregou")
            return

        checks = []
        checks.append(("web carregada", True))
        checks.append(("sem rodapé próprio", await web.evaluate("() => !document.getElementById('footer')")))
        checks.append(("sem logo repetida", await web.evaluate("() => !document.querySelector('.top-logo')")))

        n_modelos = await web.evaluate(
            "() => { document.getElementById('model-pill').click();"
            " return document.querySelectorAll('.model-item').length; }")
        await web.evaluate("() => document.getElementById('model-close').click()")
        checks.append((f"modelos no seletor ({n_modelos})", n_modelos > 400))

        await web.evaluate("() => { const i=document.getElementById('input'); i.focus(); i.value='/';"
                           " i.dispatchEvent(new Event('input')); }")
        await page.wait_for_timeout(1200)
        n_cmd = await web.evaluate("() => document.querySelectorAll('.palette-item').length")
        checks.append((f"menu '/' ({n_cmd} itens)", n_cmd >= 10))

        await web.evaluate("() => { const i=document.getElementById('input'); i.focus(); i.value='@';"
                           " i.dispatchEvent(new Event('input')); }")
        await page.wait_for_timeout(2200)
        grupos = await web.evaluate("() => [...document.querySelectorAll('.palette-group')].map(e=>e.textContent.toUpperCase())")
        n_skills = await web.evaluate("() => document.querySelectorAll('.palette-item').length")
        checks.append((f"menu '@' com habilidades ({'HABILIDADES' in grupos}, {n_skills} itens)",
                       "HABILIDADES" in grupos))
        await web.evaluate("() => document.getElementById('input').value='';")

        # sessão nova + turno completo (o aviso deve sumir)
        await web.evaluate("() => document.getElementById('new-session').click()")
        await page.wait_for_timeout(2500)
        await web.evaluate("() => { const i=document.getElementById('input'); i.focus();"
                           " i.value='Responda apenas: ACEITE';"
                           " i.dispatchEvent(new Event('input')); }")
        await page.wait_for_timeout(400)
        await web.evaluate("() => document.getElementById('send-btn').click()")
        visivel_final = True
        for _ in range(80):
            visivel_final = await web.evaluate("() => !document.getElementById('status').hidden")
            if not visivel_final:
                break
            await page.wait_for_timeout(500)
        checks.append(("aviso 'Trabalhando…' some ao final", not visivel_final))

        # botão que oculta as sessões
        col_before = await web.evaluate("() => getComputedStyle(document.querySelector('.app')).gridTemplateColumns")
        await web.evaluate("() => document.getElementById('menu-btn').click()")
        await page.wait_for_timeout(600)
        col_after = await web.evaluate("() => getComputedStyle(document.querySelector('.app')).gridTemplateColumns")
        checks.append((f"botão oculta as sessões ({col_before} → {col_after})", col_before != col_after))

        # tema
        tema = await web.evaluate("() => document.documentElement.getAttribute('data-theme')")
        checks.append((f"tema aplicado ({tema})", tema in ("pesquisai", "pesquisai-light")))

        print("═══ aceitação ═══")
        for nome, ok in checks:
            print(f"  {'✓' if ok else '✗'} {nome}")
        print(f"  erros de console: {errors if errors else 'nenhum'}")
        await page.screenshot(path="/tmp/acceptance.png")
        await browser.close()


asyncio.run(main())

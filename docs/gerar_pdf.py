import markdown
from weasyprint import HTML
import os

md_path = "/content/drive/My Drive/PesquisAI/artigo_preco_cafe.md"
pdf_path = "/content/drive/My Drive/PesquisAI/artigo_preco_cafe.pdf"

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

html_content = markdown.markdown(md_content, extensions=["tables", "fenced_code"])

css = """
@page {
    size: A4;
    margin: 2.5cm 2cm;
}
body {
    font-family: 'DejaVu Serif', serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #222;
    text-align: justify;
}
h1 {
    font-family: 'DejaVu Sans', sans-serif;
    font-size: 20pt;
    color: #1a3c34;
    text-align: center;
    margin-bottom: 0.3cm;
    page-break-before: avoid;
}
h2 {
    font-family: 'DejaVu Sans', sans-serif;
    font-size: 14pt;
    color: #2d6a4f;
    border-bottom: 2px solid #2d6a4f;
    padding-bottom: 3px;
    margin-top: 1cm;
}
h3 {
    font-family: 'DejaVu Sans', sans-serif;
    font-size: 12pt;
    color: #40916c;
    margin-top: 0.6cm;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 0.5cm 0;
    font-size: 9.5pt;
}
th {
    background-color: #2d6a4f;
    color: white;
    padding: 6px 8px;
    font-family: 'DejaVu Sans', sans-serif;
}
td {
    padding: 4px 8px;
    border: 1px solid #ccc;
}
tr:nth-child(even) {
    background-color: #f0f7f4;
}
p {
    margin: 0.3cm 0;
}
strong {
    color: #1a3c34;
}
em {
    color: #555;
}
"""

html_full = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>
{html_content}
</body>
</html>"""

HTML(string=html_full).write_pdf(pdf_path)
print(f"PDF salvo em: {pdf_path}")

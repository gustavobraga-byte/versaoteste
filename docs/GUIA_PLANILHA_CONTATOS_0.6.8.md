# Guia rápido — Ativar captura de e-mails na planilha (v0.6.8)

**Planilha criada:** https://docs.google.com/spreadsheets/d/149XGyTfPbGs34Wrb8WHBPC8gmzRQKJzvTEmqXlshvgg/edit
**Arquivo Apps Script:** `/PesquisAI/APPS_SCRIPT_PLANILHA_CONTATO.gs` (também em docs/APPS_SCRIPT_PLANILHA_CONTATO.gs)
**Local no Drive:** `Meu Drive/PesquisAI/UFVAI — Contatos (0.6.8)` + `APPS_SCRIPT_PLANILHA_CONTATO.gs`

## Passo a passo (2 min, só precisa fazer UMA vez)
1. Abra a planilha acima.
2. Menu **Extensões → Apps Script** → apague tudo → cole o conteúdo de `APPS_SCRIPT_PLANILHA_CONTATO.gs`.
3. Clique em **Implantar → Nova implantação → Aplicativo da Web**
   - **Executar como:** Eu (gustavo.braga@ufv.br)
   - **Quem pode acessar:** Qualquer pessoa
   → **Implantar** (autorize com sua conta Google na primeira vez) → copie a URL `https://script.google.com/macros/s/.../exec`
4. Cole a URL em **um** dos lugares:
   - **Recomendado (UI):** No UFVAI, abra o painel **📊 Telemetria (Admin)** → campo **✉️ URL de contato** → cole → **Salvar**.
   - **Offline/.deb:** `mkdir -p ~/PesquisAI/config && echo 'export UFVAI_CONTACT_ENDPOINT="https://script.google.com/macros/s/.../exec"' >> ~/PesquisAI/config/ufvai.env`
   - **Colab:** antes de `from main import run`, faça `import os; os.environ["UFVAI_CONTACT_ENDPOINT"]="https://..."`

## Teste
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"product":"ufvai","email":"seu@teste.br","email_sha256":"abc","environment":"colab","app_version":"0.6.8","sent_at":"2026-08-24T21:56:00"}' \
  "https://script.google.com/macros/s/SEU_ID/exec"
```
→ Deve aparecer uma linha nova na planilha e, se `NOTIFICAR_POR_EMAIL=true`, você recebe e-mail.

## O que já foi feito automaticamente (v0.6.8)
- [x] Planilha criada em `Meu Drive/PesquisAI` com aba `Contatos UFVAI` e cabeçalho formatado
- [x] Linha de teste `teste-inicial@ufv.br` inserida para validar
- [x] Arquivo `APPS_SCRIPT_PLANILHA_CONTATO.gs` criado no Drive e em `docs/`
- [x] `TELEMETRY.md` atualizado com o novo SHEET_ID
- [ ] **Pendente do admin:** implantar o Web App (passo 3 acima) e colar a URL no painel

Após implantar, todo e-mail opt-in digitado na tela de Termos será gravado na planilha (e nunca no GA4, conforme LGPD). O GA4 continua recebendo só o contador anônimo `contact_optin`.

Dúvidas: `gustavo.braga@ufv.br`

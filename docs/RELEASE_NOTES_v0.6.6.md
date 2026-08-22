# 🚀 Release Notes — UFVAI v0.6.6

**Data:** 22/08/2026 · **Pacote:** `pesquisai_0.6.6-1_amd64.deb` · **Marca:** UFVAI (engine PesquisAI)

## 🖼️ Favicon na interface (incl. Colab)

- A interface agora exibe a **lupa dourada UFVAI** na aba do navegador:
  `<link rel="icon">` SVG + PNG 64px de fallback + apple-touch-icon.
- **Nova rota `/favicon.ico`** no servidor local (mesma whitelist offline-safe dos assets).
- **Correção específica do Colab**: sob o proxy (`/proxy/8001/`), links absolutos `/assets/…`
  apontavam para fora do app — um script injeta os favicons com o prefixo correto do pathname.
  O **logo da tela de Termos** migrou para caminho relativo e agora também aparece no Colab.

## ✉️ E-mail de contato opcional — telemetria é do desenvolvedor, com base legal LGPD

A telemetria serve para o **desenvolvedor** acompanhar adoção. Novo canal de contato, separado
do canal analítico e desenhado para não ferir a LGPD nem os Termos do Google:

| Camada | Decisão |
|---|---|
| Coleta | **Opt-in puro** na tela de Termos (campo em branco por padrão) — consentimento livre, informado e inequívoco (**art. 7º, I**) |
| Finalidade | Declarada no próprio formulário: contato/novidades do UFVAI (**art. 6º, I**) |
| Armazenamento | Local, `~/.config/ufvai_profile.json` **chmod 600**, com SHA-256 + carimbo do consentimento |
| Google Analytics | **NUNCA recebe o e-mail** (Termos do Google proíbem PII, mesmo com hash) — recebe só o contador anônimo `contact_optin` |
| Envio ao mantenedor | Somente se ele configurar `UFVAI_CONTACT_ENDPOINT` (HTTPS próprio, ex.: Apps Script) → POST `{product, email, email_sha256, environment, sent_at}` |
| Eliminação (**art. 18, VI**) | Campo esvaziado + Aceitar · remoção do arquivo · `POST /api/contact/delete` |

- Tela de Termos atualizada → **versão 3 dos Termos = re-consentimento** de todos os usuários.
- Painel Admin/telemetria mostra apenas estado mascarado (`jo***@dominio.br`) — nunca o endereço.

## 📄 Documentação

- `PRIVACY.md`: nova seção "E-mail de contato (v0.6.6)".
- `TELEMETRY.md`: Passo 9 com tutorial do endpoint Apps Script; tabela admin vê/nunca vê revisada.
- `AGENTS.md`: bloco de referências às variantes traduzidas (incluindo `agents/AGENTS.zh.md`);
  `agents/README.md` corrigido de 4 → **5 idiomas**.

## 🧪 Validação

- `py_compile` OK · pytest completo · smoke: `/favicon.ico`, `/api/consent` (com/sem e-mail),
  e-mail inválido rejeitado, `/api/contact/delete`.

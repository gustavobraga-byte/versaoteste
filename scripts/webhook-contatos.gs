/**
 * Google Apps Script — Webhook de Contatos UFVAI v0.6.9
 *
 * Este script recebe POSTs do UFVAI (opt-in de contato + heartbeat de
 * acesso ativo) e grava na planilha "Contatos UFVAI" do seu Google Drive.
 *
 * Payload esperado:
 *   {
 *     "product": "ufvai",
 *     "email": "usuario@dominio.br",
 *     "email_sha256": "abc123...",
 *     "environment": "colab" | "local",
 *     "app_version": "0.6.9",
 *     "sent_at": "2026-08-24T21:53:00",
 *     "flag": "novo_contato" | "usuario_ativo"
 *   }
 *   flag "novo_contato"  → primeiro aceite da tela de Termos (opt-in);
 *   flag "usuario_ativo" → reabertura: cada novo acesso do usuário já
 *   ativo (tela "Bem-vindo de volta" → e-mail + hora + flag na planilha).
 *
 * SEGURANÇA:
 * - Não usa planilha compartilhada (removido P0 #3)
 * - O endpoint (/exec) é público mas NÃO expõe dados existentes
 * - Validação básica: produto deve ser "ufvai", email obrigatório
 * - Limite de 1000 entradas (anti-abuso)
 *
 * COMO INSTALAR:
 * 1. Abra https://script.google.com
 * 2. Crie novo projeto → cole este código
 * 3. Crie uma planilha "Contatos UFVAI" no Drive
 * 4. Cole o ID da planilha em SPREADSHEET_ID abaixo
 * 5. Deploy → Nova implantação → App da Web
 *    - Executar como: Eu
 *    - Quem tem acesso: Qualquer pessoa
 * 6. Copie a URL /exec e configure:
 *    export UFVAI_CONTACT_ENDPOINT="https://script.google.com/macros/s/SEU_ID/exec"
 */

const SPREADSHEET_ID = "COLE_AQUI_O_ID_DA_PLANILHA";
const SHEET_NAME = "Contatos";
const MAX_ROWS = 1000;

function doPost(e) {
  try {
    // Parse do body JSON
    const data = JSON.parse(e.postData.contents);

    // Validação básica
    if (!data.email || !data.email.includes("@")) {
      return ContentService.createTextOutput(
        JSON.stringify({ ok: false, error: "email inválido" })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    if (data.product !== "ufvai") {
      return ContentService.createTextOutput(
        JSON.stringify({ ok: false, error: "produto inválido" })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    // Abre a planilha
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    let sheet = ss.getSheetByName(SHEET_NAME);

    // Cria a aba se não existir
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
      sheet.appendRow([
        "Timestamp",
        "Email",
        "Email SHA-256",
        "Ambiente",
        "Versão",
        "Flag",
      ]);
    }

    // Limite anti-abuso
    if (sheet.getLastRow() > MAX_ROWS) {
      return ContentService.createTextOutput(
        JSON.stringify({ ok: false, error: "limite de cadastros atingido" })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    // v0.6.9: flag distingue novo contato (opt-in) de usuário já ativo
    // (reabertura — tela "Bem-vindo de volta" → email + hora + flag)
    var flag = String(data.flag || "novo_contato");
    if (flag !== "novo_contato" && flag !== "usuario_ativo") { flag = "novo_contato"; }

    // Grava a linha (sem IP por privacidade)
    sheet.appendRow([
      data.sent_at || new Date().toISOString(),
      data.email,
      data.email_sha256 || "",
      data.environment || "",
      data.app_version || "",
      flag,
    ]);

    return ContentService.createTextOutput(
      JSON.stringify({ ok: true, message: "Contato registrado" })
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ ok: false, error: "Erro interno" })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Opcional: função para verificar se o endpoint está funcionando.
 * Acesse via GET no navegador.
 */
function doGet() {
  return ContentService.createTextOutput(
    JSON.stringify({ ok: true, service: "UFVAI Contact Webhook", version: "0.6.9" })
  ).setMimeType(ContentService.MimeType.JSON);
}

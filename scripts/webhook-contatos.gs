/**
 * Google Apps Script — Webhook de Contatos UFVAI v0.6.9-P03
 *
 * Este script recebe POSTs do UFVAI (opt-in de contato) e grava
 * na planilha "Contatos UFVAI" do seu Google Drive.
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
        "IP (removido)",
      ]);
    }

    // Limite anti-abuso
    if (sheet.getLastRow() > MAX_ROWS) {
      return ContentService.createTextOutput(
        JSON.stringify({ ok: false, error: "limite de cadastros atingido" })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    // Grava a linha (sem IP por privacidade)
    sheet.appendRow([
      data.sent_at || new Date().toISOString(),
      data.email,
      data.email_sha256 || "",
      data.environment || "",
      data.app_version || "",
      "",  // IP não é coletado
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
    JSON.stringify({ ok: true, service: "UFVAI Contact Webhook", version: "0.6.9-P03" })
  ).setMimeType(ContentService.MimeType.JSON);
}

/**
 * Google Apps Script — Webhook de Contatos UFVAI v0.6.10
 *
 * Este script recebe POSTs do UFVAI (opt-in de contato + heartbeat de
 * acesso ativo) e grava na planilha "Contatos UFVAI" do seu Google Drive.
 *
 * v0.6.10: adiciona colunas Nome (ao lado do e-mail) e IP do cliente.
 *
 * Payload esperado:
 *   {
 *     "product": "ufvai",
 *     "email": "usuario@dominio.br",
 *     "name": "Nome da Pessoa",
 *     "email_sha256": "abc123...",
 *     "ip": "200.1.2.3",
 *     "environment": "colab" | "local",
 *     "app_version": "0.6.10",
 *     "sent_at": "2026-09-01T13:45:00",
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
 * - Limite de 1000 entradas (anti-abuso) → aumentado para 5000 na v0.6.10
 *
 * COMO INSTALAR / ATUALIZAR:
 * 1. Abra https://script.google.com (projeto já implantado)
 * 2. Substitua TODO o código por esta versão v0.6.10
 * 3. Se a aba "Contatos" já existe com cabeçalho antigo (6 colunas), este
 *    script migra automaticamente: insere colunas Nome e IP e preserva dados.
 * 4. Salve (Ctrl+S) → Implantar → Gerenciar implantação → Editar → Nova versão → Implantar
 *    (mantém a mesma URL /exec — nada a reconfigurar no UFVAI)
 * 6. URL /exec configurada em:
 *    export UFVAI_CONTACT_ENDPOINT="https://script.google.com/macros/s/SEU_ID/exec"
 */

const SPREADSHEET_ID = "1TWVuKtApnuzrW59ZYymnjLTgMXa1Exo0XAZQHSfwoqE";
const SHEET_NAME = "Contatos";
const MAX_ROWS = 5000;

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

    // Cria a aba se não existir — cabeçalho v0.6.10 com Nome e IP
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
      sheet.appendRow([
        "Timestamp",
        "Email",
        "Nome",
        "Email SHA-256",
        "Ambiente",
        "Versão",
        "Flag",
        "IP",
      ]);
      // congela cabeçalho + formatação básica
      sheet.setFrozenRows(1);
      sheet.getRange(1,1,1,8).setFontWeight("bold").setBackground("#1F3864").setFontColor("#FFFFFF");
      sheet.setColumnWidth(1, 170); // Timestamp
      sheet.setColumnWidth(2, 220); // Email
      sheet.setColumnWidth(3, 160); // Nome
      sheet.setColumnWidth(4, 220); // SHA
      sheet.setColumnWidth(5, 90);  // Ambiente
      sheet.setColumnWidth(6, 70);  // Versão
      sheet.setColumnWidth(7, 120); // Flag
      sheet.setColumnWidth(8, 110); // IP
    } else {
      // Migração automática de cabeçalho antigo (v0.6.9: 6 colunas) → v0.6.10 (8 colunas)
      var header = sheet.getRange(1,1,1,Math.min(sheet.getLastColumn(), 8)).getValues()[0].join("|");
      if (header.indexOf("Nome") === -1 || header.indexOf("IP") === -1) {
        // preserva dados existentes: insere colunas 3 (Nome) e 8 (IP) se faltarem
        var lastCol = sheet.getLastColumn();
        // se só tem 6 colunas → precisa expandir para 8
        if (lastCol === 6) {
          // Insere "Nome" após Email (col 3) — desloca SHA etc para direita
          sheet.insertColumnAfter(2);
          sheet.getRange(1,3).setValue("Nome");
          // Agora tem 7 cols, insere IP no fim (col 8)
          sheet.getRange(1,8).setValue("IP");
          // re-aplica cabeçalho
          sheet.getRange(1,1,1,8).setFontWeight("bold").setBackground("#1F3864").setFontColor("#FFFFFF");
        } else if (lastCol === 7 && header.indexOf("IP") === -1) {
          sheet.getRange(1,8).setValue("IP");
        }
      }
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

    // v0.6.10: nome e ip
    var nome = String(data.name || data.nome || "").trim().substring(0, 100);
    var ip = String(data.ip || "").trim().substring(0, 45); // IPv6 max 45 chars

    // Grava a linha — ordem v0.6.10 com Nome e IP
    sheet.appendRow([
      data.sent_at || new Date().toISOString(),
      data.email,
      nome,
      data.email_sha256 || "",
      data.environment || "",
      data.app_version || "",
      flag,
      ip,
    ]);

    return ContentService.createTextOutput(
      JSON.stringify({ ok: true, message: "Contato registrado" })
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ ok: false, error: "Erro interno: " + err })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Opcional: função para verificar se o endpoint está funcionando.
 * Acesse via GET no navegador.
 */
function doGet() {
  return ContentService.createTextOutput(
    JSON.stringify({ ok: true, service: "UFVAI Contact Webhook", version: "0.6.10" })
  ).setMimeType(ContentService.MimeType.JSON);
}

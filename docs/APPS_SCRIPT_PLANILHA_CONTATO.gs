/**
 * UFVAI — Webhook de Contato Opt-in → Google Sheets
 * ===================================================
 * Recebe POST JSON do UFVAI (telemetry._forward_contact) e grava na planilha
 * "UFVAI — Contatos (0.6.8)" criada automaticamente.
 * 
 * Payload esperado (telemetry.py _forward_contact):
 * {
 *   "product": "ufvai",
 *   "email": "usuario@dominio.br",
 *   "email_sha256": "abc123...",
 *   "environment": "colab" | "local",
 *   "app_version": "0.6.9",
 *   "sent_at": "2026-08-24T21:53:00",
 *   "flag": "novo_contato" | "usuario_ativo"
 * }
 *
 * flag (v0.6.9):
 *   • "novo_contato"  — primeiro aceite da tela de Termos (opt-in);
 *   • "usuario_ativo" — reabertura: cada novo acesso do usuário já ativo
 *     (tela "Bem-vindo de volta" → heartbeat com e-mail + hora + flag).
 * 
 * Configuração (2 min):
 * 1. Abra a planilha: https://docs.google.com/spreadsheets/d/149XGyTfPbGs34Wrb8WHBPC8gmzRQKJzvTEmqXlshvgg/edit
 * 2. Menu Extensões → Apps Script → apague o código e cole ESTE arquivo inteiro.
 * 3. Edite SHEET_ID abaixo se usar outra planilha (ou mantenha o ID acima).
 * 4. Implantar → Nova implantação → Tipo: Aplicativo da Web
 *    - Executar como: Eu
 *    - Quem pode acessar: Qualquer pessoa  ← obrigatório (webhook público)
 *    → Copie a URL terminada em /exec
 * 5. Cole a URL no painel 📊 Telemetria (Admin) → campo "✉️ URL de contato" → Salvar
 *    ou em ~/PesquisAI/config/ufvai.env → UFVAI_CONTACT_ENDPOINT="URL"
 * 
 * Segurança: valida e-mail com regex simples; rejeita payload sem e-mail.
 * Auditoria: grava linha com timestamp do servidor + dados recebidos.
 * Notificação opcional por e-mail: descomente MailApp.sendEmail abaixo.
 */

var SHEET_ID = "149XGyTfPbGs34Wrb8WHBPC8gmzRQKJzvTEmqXlshvgg";
var SHEET_NAME = "Contatos UFVAI";
var NOTIFICAR_POR_EMAIL = false; // true = envia e-mail a cada novo contato
var EMAIL_DO_DEV = "gustavo.braga@ufv.br";

function doPost(e) {
  try {
    var body = {};
    if (e && e.postData && e.postData.contents) {
      body = JSON.parse(e.postData.contents);
    } else if (e && e.parameter) {
      body = e.parameter;
    } else {
      return response(200, {ok: false, message: "Payload vazio."});
    }

    var email = String(body.email || "").trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
      return response(200, {ok: false, message: "E-mail inválido."});
    }

    // Abrir planilha
    var ss = SHEET_ID ? SpreadsheetApp.openById(SHEET_ID) : SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(SHEET_NAME);
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
      sheet.appendRow(["Data/hora","E-mail","SHA-256","Ambiente","Versão","Produto","Flag"]);
    }
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(["Data/hora","E-mail","SHA-256","Ambiente","Versão","Produto","Flag"]);
    }

    var now = new Date();
    // v0.6.9: flag distingue novo contato (opt-in) de usuário já ativo (reabertura)
    var flag = String(body.flag || "novo_contato");
    if (flag !== "novo_contato" && flag !== "usuario_ativo") { flag = "novo_contato"; }
    var row = [
      body.sent_at || Utilities.formatDate(now, Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss"),
      email,
      String(body.email_sha256 || ""),
      String(body.environment || ""),
      String(body.app_version || body.version || ""),
      String(body.product || "ufvai"),
      flag
    ];
    sheet.appendRow(row);

    // Notificação opcional
    if (NOTIFICAR_POR_EMAIL && EMAIL_DO_DEV) {
      try {
        MailApp.sendEmail({
          to: EMAIL_DO_DEV,
          subject: "🧬 UFVAI — Novo contato opt-in: " + email,
          body: "Novo contato voluntário no UFVAI\n" +
                "-----------------------------------\n" +
                "E-mail:     " + email + "\n" +
                "SHA-256:    " + (body.email_sha256 || "—") + "\n" +
                "Ambiente:   " + (body.environment || "—") + "\n" +
                "Versão:     " + (body.app_version || body.version || "—") + "\n" +
                "Enviado em: " + (body.sent_at || now.toISOString()) + "\n\n" +
                "Planilha: https://docs.google.com/spreadsheets/d/" + SHEET_ID + "/edit"
        });
      } catch (err) {}
    }

    return response(200, {ok: true, message: "Contato registrado."});
  } catch (err) {
    return response(500, {ok: false, message: "Erro: " + err});
  }
}

function doGet(e) {
  return response(200, {ok: true, message: "UFVAI webhook ativo. Use POST."});
}

function response(code, obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// Teste manual: rode no editor do Apps Script e veja o log
function testar() {
  var e = {postData: {contents: JSON.stringify({
    product: "ufvai",
    email: "teste@ufv.br",
    email_sha256: "abc123",
    environment: "colab",
    app_version: "0.6.8",
    sent_at: new Date().toISOString()
  })}};
  var r = doPost(e);
  Logger.log(r.getContent());
}

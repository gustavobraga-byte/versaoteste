/**
 * APPS_SCRIPT_PLANILHA_CONTATO.gs — UFVAI
 * Canal de contato opt-in → Planilha Google do desenvolvedor.
 *
 * COMO USAR (resumo — guia completo em TELEMETRY.md §Passo 9):
 *   1. Crie uma planilha em https://sheets.new (ex.: "UFVAI — contatos");
 *   2. Extensões → Apps Script → apague tudo e cole ESTE arquivo;
 *   3. Substitua COLE_O_ID_DA_PLANILHA pelo ID da planilha
 *      (trecho entre /d/ e /edit na URL dela);
 *   4. Implantar → Nova implantação → App da Web
 *        Executar como: Eu  ·  Quem pode acessar: Qualquer pessoa
 *      → autorize sua conta (1ª vez) → copie a URL terminada em /exec;
 *   5. Cole a URL no painel 📊 Telemetria (Admin) do UFVAI → campo
 *      "✉️ URL de contato" → Salvar.
 *
 * Colunas gravadas: Data/hora · E-mail · SHA-256 · Ambiente · Versão do app
 * Newsletter (opcional): a linha "MailApp" abaixo envia um aviso por e-mail
 * a cada novo contato (cota gratuita do Gmail ≈ 100/dia). Apague a linha
 * se não quiser receber os avisos.
 */

var SHEET_ID = 'COLE_O_ID_DA_PLANILHA';          // ← obrigatório
var NOTIFY_EMAIL = 'gustavo.braga@ufv.br';       // ← opcional (avisos)

function doPost(e) {
  try {
    var d = JSON.parse(e.postData.contents);
    var sh = SpreadsheetApp.openById(SHEET_ID).getSheets()[0];

    // Cabeçalho na primeira execução
    if (sh.getLastRow() === 0) {
      sh.appendRow(['Data/hora', 'E-mail', 'SHA-256', 'Ambiente', 'Produto']);
    }

    sh.appendRow([
      new Date(),
      d.email || '',
      d.email_sha256 || '',
      d.environment || '',
      d.product || 'ufvai',
    ]);

    // Aviso por e-mail (newsletter) — comente para desativar
    if (NOTIFY_EMAIL) {
      MailApp.sendEmail(
        NOTIFY_EMAIL,
        'Novo contato UFVAI (' + (d.environment || '?') + ')',
        'E-mail: ' + (d.email || '') +
        '\nAmbiente: ' + (d.environment || '') +
        '\nRecebido em: ' + new Date().toLocaleString('pt-BR')
      );
    }

    return ContentService.createTextOutput('{"ok":true}')
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput('{"ok":false,"error":"' + err + '"}')
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Teste manual: rode doGet no editor (▶ Executar) para conferir a autorização
// e ver a URL de implantação nos registros.
function doGet() {
  Logger.log('URL de implantação termina em /exec — cole no painel Admin do UFVAI.');
}

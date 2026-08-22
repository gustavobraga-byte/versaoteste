# 📊 Telemetria do UFVAI — Como Funciona

> **Resumo em uma frase:** a telemetria é **opt-in** (só funciona se você marcar a caixa na tela de Termos), envia **apenas contadores anônimos de eventos** via Google Analytics 4 Measurement Protocol, **nunca envia conteúdo**, e pode ser desligada a qualquer momento.

---

## 1. Visão geral

| Aspecto | Como é |
|---|---|
| **Padrão** | ❌ **Desligada por padrão** — nada é enviado sem consentimento |
| **Consentimento** | Checkbox opcional na tela de Termos de Uso (1ª entrada) |
| **Tecnologia** | GA4 **Measurement Protocol** (envio *server-side*, sem cookies no navegador) |
| **Conteúdo enviado** | Nome do evento + parâmetros não-pessoais (tabela §3) |
| **O que NUNCA vai** | Prompts, respostas da IA, notas do vault, caminhos de arquivo, chaves de API, e-mails, IDs de conta Google |
| **Identificador** | UUID aleatório gerado localmente (`~/.config/ufvai_cid`) — não é vinculado a ninguém |
| **Kill-switch global** | `export UFVAI_TELEMETRY=0` desliga mesmo com consentimento ativo |
| **Código** | `pesquisai/telemetry.py` (~140 linhas, sem dependências externas) |

---

## 2. Fluxo completo (da instalação ao envio)

```
┌───────────────────────────────────────────────────────────────┐
│ 1ª execução no Colab                                          │
│   └─ launch() gera token de sessão e injeta o wrapper HTML    │
│      └─ Tela de Termos aparece (overlay bloqueante)           │
│                                                               │
│ Usuário marca:                                                │
│   [ ] Li e aceito os Termos (obrigatório p/ usar a UI)        │
│   [x] Opcional: permitir estatísticas anônimas  ← CONSENTIMENTO│
│   [Aceitar e começar]                                         │
│                                                               │
│ Navegador → POST /api/consent {accepted:true, analytics:true} │
│   ├─ Servidor grava ~/.config/ufvai_consent.json              │
│   │    {"accepted": true, "analytics": true, "version":...}   │
│   └─ telemetry.set_consent(True)                              │
└───────────────────────────────────────────────────────────────┘
                          │
                          ▼  (a partir daqui, eventos podem fluir)
┌───────────────────────────────────────────────────────────────┐
│ Acontecimento no app (ex.: usuário salva um backup)           │
│   └─ handler chama _tel_event("backup_created", {})           │
│      └─ telemetry.event():                                    │
│          1. enabled()?                                        │
│             ├─ UFVAI_TELEMETRY=0?  → descarta                 │
│             ├─ sem GA config?      → descarta                 │
│             └─ sem consentimento?  → descarta                 │
│          2. Monta payload JSON mínimo                         │
│          3. Thread daemon → POST HTTPS (timeout 3 s)          │
│             para google-analytics.com/mp/collect              │
│          Qualquer erro = silêncio total (o app nunca quebra)  │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. Eventos coletados e seus parâmetros

Todos os valores são categóricos/anônimos:

| Evento | Quando | Parâmetros |
|---|---|---|
| `app_started` | `launch()` conclui | `version`, `lang` (idioma), `colab` (true/false) |
| `terms_accepted` | aceite dos Termos | `analytics` (true/false — se o próprio opt-in foi marcado) |
| `provider_saved` | chave de provedor salva | `provider` (nome curto: `openai`, `gemini`…) |
| `provider_deleted` | chave removida | `provider` |
| `backup_created` | backup de sessão gravado no Drive | — |
| `session_restored` | sessão importada/restaurada | — |
| `lang_changed` | idioma trocado na UI | `lang` |
| `theme_changed` | tema claro/escuro | `theme` |
| `memory_note_saved` / `_created` / `_deleted` | operações na memória Obsidian | — |

> 🔍 **Auditoria:** cada chamada está visível com grep —
> `grep -rn "_tel_event" pesquisai/launch_app.py`

---

## 4. As três condições (todas obrigatórias para enviar)

```python
def enabled() -> bool:
    if kill_switch_active():   return False   # UFVAI_TELEMETRY=0
    if not configured():       return False   # faltam UFVAI_GA_* no ambiente
    return consented()                        # ~/.config/ufvai_consent.json.analytics == true
```

1. **Sem kill-switch** — `UFVAI_TELEMETRY=0` vence tudo.
2. **Com configuração do mantenedor** — o dono do projeto precisa definir as variáveis de ambiente:
   - `UFVAI_GA_MEASUREMENT_ID` (ex.: `G-XXXXXXXXXX`)
   - `UFVAI_GA_API_SECRET` (gerado no GA4: Admin → Data Streams → Measurement Protocol API secrets)
   
   Sem elas, a telemetria fica **inativa mesmo com consentimento** (privacidade por padrão em implantações terceiras).

   **Como definir no modo offline (.deb) — v0.6.2+:** crie o arquivo `~/PesquisAI/config/ufvai.env` (o launcher carrega-o antes de iniciar):
   ```bash
   mkdir -p ~/PesquisAI/config
   cat > ~/PesquisAI/config/ufvai.env <<'EOF'
   export UFVAI_GA_MEASUREMENT_ID=G-XXXXXXXXXX
   export UFVAI_GA_API_SECRET=SEU_SEGREDO_AQUI
   EOF
   chmod 600 ~/PesquisAI/config/ufvai.env
   ```
3. **Com consentimento do usuário** — checkbox da tela de Termos.

### Testando (DebugView — v0.6.2+)
1. No GA4: **Admin → DebugView** (deixe a página aberta).
2. Ative o modo debug e reinicie: `export UFVAI_TELEMETRY_DEBUG=1` antes de iniciar o UFVAI.
3. Os eventos (`terms_accepted`, `app_started`, `lang_changed`…) aparecem em tempo real no DebugView; **não gravam relatórios**. Sem a flag, os eventos vão para Relatórios → Tempo real (até alguns minutos de atraso).

> ⚠️ O Measurement Protocol exige internet. No modo 100% offline os eventos são descartados silenciosamente (thread daemon, timeout de 3 s).

---

## 5. Por que Measurement Protocol (server-side) e não o snippet gtag?

| Critério | MP server-side (escolhido) | gtag client-side |
|---|---|---|
| Cookies no navegador | **Nenhum** (_cid é UUID local) | Cookies `_ga` |
| Banner LGPD necessário | Consentimento já coberto pela tela de Termos | Banner dedicado recomendado |
| Bloqueadores de anúncios | Não interferem | Podem bloquear o script |
| Página carregada dentro do iframe Colab | Irrelevante (envio vem do Python) | Comportamento varia |
| Dados técnicos do browser (resolução etc.) | **Não coleta** | Coleta por padrão |
| Esforço de manutenção | 1 módulo Python | Snippet + CSP + testes de UI |

Trade-off honesto: perdemos métricas de *sessão/navegador* (tempo na página etc.). Ganhamos privacidade máxima e zero impacto no carregamento da UI. Métricas de audiência do **site** continuam podendo usar GA4 web à parte.

---

## 6. Como desligar (usuário)

1. **Na origem:** recusar o checkbox "estatísticas anônimas" na tela de Termos;
2. **Depois:** apagar `~/.config/ufvai_consent.json` ou regravar `"analytics": false`;
3. **Global/imediato:** `export UFVAI_TELEMETRY=0` (funciona até com consentimento ativo);
4. **Rede:** bloquear o domínio `www.google-analytics.com` — o módulo falha silenciosamente.

## 7. Como verificar (transparência)

```bash
# Estado atual do consentimento
cat ~/.config/ufvai_consent.json

# ID anônimo desta máquina
cat ~/.config/ufvai_cid

# Todos os pontos de coleta no código
grep -rn "_tel_event\|telemetry" pesquisai/ --include="*.py"
```

---

## 8. Garantias de projeto (resumo normativo)

- ✅ Opt-in explícito (LGPD Art. 7º/8º — consentimento livre, informado e inequívoco)
- ✅ Minimização de dados (nenhum dado pessoal/conteúdo trafega)
- ✅ Finalidade declarada (métricas agregadas de uso das funcionalidades)
- ✅ Revogação fácil a qualquer momento
- ✅ Fail-safe: telemetria nunca afeta funcionamento, performance perceptível ou estabilidade
- ❌ Não usa cookies de rastreamento, fingerprinting ou publicidade

*Dúvidas ou sugestões: abra uma issue em github.com/gustavobraga-byte/PesquisAI.*

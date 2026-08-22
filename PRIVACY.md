# 🔒 Privacidade no UFVAI

**Versão:** 1.0 · **Data:** 21/08/2026 · Aplica-se ao UFVAI/PesquisAI v0.6.0+

## Princípio central

> **Seus dados de pesquisa são seus.** O UFVAI processa notas, relatórios e o vault Obsidian
> **localmente na sua sessão (Colab ou máquina)** e no seu próprio Google Drive. O agente não
> envia conteúdo da memória para serviços externos.

## O que fica no SEU ambiente (nunca sai)

- Todo o vault Obsidian (`My Drive/PesquisAI/vault/`) — notas, hipóteses, referências;
- Prompts enviados ao agente e respostas geradas;
- Relatórios, figuras, datasets produzidos;
- Chaves de API — armazenadas **cifradas com Fernet (AES-CBC+HMAC)** em `backups/keys_store.json`;
  a chave de criptografia fica em arquivo separado (`keys_encryption_key.bin`).

⚠️ Ressalva honesta: quando você usa um provedor de IA (OpenAI, Google, Anthropic…), os prompts
daquela conversa trafegam para aquele provedor sob os termos **dele**. Isso é inerente ao uso de
LLMs em nuvem e não é controlado pelo UFVAI.

## O que pode sair do seu ambiente

| Dado | Destino | Quando | Como desligar |
|---|---|---|---|
| Contadores anônimos de uso +, se consentido, cookie `_ga` do navegador (gtag.js, `anonymize_ip`) | Google Analytics 4 (dois canais: página + eventos do app, mesmo ID) | **Somente se você aceitar** o opt-in na tela de Termos | `UFVAI_TELEMETRY=0` · revogar consentimento · ver `TELEMETRY.md` |
| Requisições a APIs públicas de dados (IBGE/SIDRA, NASA POWER, etc.) | Órgãos/fonte correspondentes | Quando uma skill consulta dados | Inerente à funcionalidade |
| Chamadas ao LLM do provedor escolhido | Provedor configurado por você | A cada interação com o agente | Não usar o provedor |

A telemetria **não inclui**: prompts, respostas, nomes de arquivos/projetos, conteúdo de notas,
endereços de e-mail, identificadores de conta. O cookie `_ga` (gtag.js client-side) só é criado
após o seu consentimento explícito na tela de Termos. Detalhamento completo: [`TELEMETRY.md`](TELEMETRY.md).

## Termos de Uso

Na primeira abertura da interface é exibida a tela de aceite dos Termos de Uso (com link para a
licença MIT). O aceite é registrado localmente (`~/.config/ufvai_consent.json`) e a telemetria,
se você autorizar, também.

## Seus direitos (LGPD)

A telemetria, quando ativa, trata dados pessoais em sentido amplo (o `client_id` aleatório pode,
em tese, ser reidentificado quando combinado a outros dados — por isso tratamos como dado pessoal
e usamos consentimento como base legal). Você tem, nos termos do **art. 18 da LGPD**:

1. Confirmação da existência de tratamento;
2. Acesso aos dados transmitidos (visível no próprio GA4/administração);
3. Correção de dados incompletos ou inexatos;
4. Anonimização, bloqueio ou eliminação de dados desnecessários;
5. Portabilidade;
6. Informação sobre compartilhamento (Google Analytics — transferência internacional, arts. 33–36);
7. Informação sobre a possibilidade de **não consentir** e suas consequências (nenhuma: o app
   funciona integralmente sem telemetria);
8. **Revogação do consentimento** a qualquer momento (`UFVAI_TELEMETRY=0` ou apagar
   `~/.config/ufvai_consent.json` e `~/.config/ufvai_cid`);
9. Oposição ao tratamento.

**Como exercer:** escreva para gustavo.braga@ufv.br (resposta imediata em formato simplificado; 
completa em até 15 dias, art. 19) ou acione o Encarregado institucional da UFV:
https://dgi.ufv.br/privacidade/. Dados que permanecem 100% no seu Drive estão sob seu controle
direto (exclusão, exportação) a qualquer momento.

**Registro das operações:** o mantenedor mantém registro simples das operações de telemetria
(eventos enviados, finalidade estatística, prazo de retenção do GA4), conforme art. 37 da LGPD.

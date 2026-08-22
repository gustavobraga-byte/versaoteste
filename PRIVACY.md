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
| Contadores anônimos de uso (eventos sem conteúdo) | Google Analytics 4 | **Somente se você aceitar** o opt-in na tela de Termos **e** o mantenedor tiver configurado as credenciais GA4 | `UFVAI_TELEMETRY=0` · ver `TELEMETRY.md` |
| Requisições a APIs públicas de dados (IBGE/SIDRA, NASA POWER, etc.) | Órgãos/fonte correspondentes | Quando uma skill consulta dados | Inerente à funcionalidade |
| Chamadas ao LLM do provedor escolhido | Provedor configurado por você | A cada interação com o agente | Não usar o provedor |

A telemetria **não inclui**: prompts, respostas, nomes de arquivos/projetos, conteúdo de notas,
endereços de e-mail, identificadores de conta. Detalhamento completo: [`TELEMETRY.md`](TELEMETRY.md).

## Termos de Uso

Na primeira abertura da interface é exibida a tela de aceite dos Termos de Uso (com link para a
licença MIT). O aceite é registrado localmente (`~/.config/ufvai_consent.json`) e a telemetria,
se você autorizar, também.

## Seus direitos (LGPD)

Como não coletamos dados pessoais identificáveis, não há base que exija acesso/eliminação junto
ao projeto. Dados que permanecem 100% no seu Drive estão sob seu controle direto (exclusão,
exportação) a qualquer momento. Dúvidas: gustavo.braga@ufv.br.

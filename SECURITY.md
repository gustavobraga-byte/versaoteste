# 🔒 Segurança — PesquisAI

## Reportando Vulnerabilidades

O PesquisAI é um software educacional e de pesquisa. Levamos a segurança a sério.

Se você encontrar uma vulnerabilidade de segurança, **por favor, não abra uma issue pública**. Em vez disso:

1. Envie um e-mail para **gustavo.braga@ufv.br** com:
   - Descrição detalhada da vulnerabilidade
   - Passos para reproduzir
   - Possível impacto
   - Sugestão de correção (se aplicável)

2. Aguarde o retorno antes de divulgar publicamente.

## Práticas de Segurança

### API Keys

- O PesquisAI **não envia** suas API keys para servidores externos.
- As keys são armazenadas localmente no seu Google Drive em `PesquisAI/backups/.keys.json`.
- **⚠️ Recomendação:** este arquivo contém suas chaves em texto plano. Proteja sua conta Google.

### Dados

- Todo processamento ocorre **localmente** na sua sessão do Google Colab.
- Nenhum dado é enviado para servidores do desenvolvedor.
- Arquivos gerados ficam exclusivamente na sua pasta `PesquisAI/` no Drive.

### LGPD (Lei nº 13.709/2018)

O PesquisAI segue princípios de *Privacy by Design*:
- **Minimização**: apenas dados necessários à tarefa são processados
- **Retenção**: você controla o que é salvo e por quanto tempo
- **Transparência**: você vê exatamente quais arquivos são lidos/gravados

## Boas Práticas para Usuários

1. 🔑 **Não compartilhe** chaves de API ou tokens
2. 🗑️ **Remova** o arquivo `.keys.json` do Drive quando não for mais necessário
3. 🔐 **Use senha forte** na sua conta Google
4. 👁️ **Revise** os arquivos gerados antes de compartilhá-los
5. 🔄 **Mantenha** o repositório atualizado

## Dependências

Manter as dependências atualizadas é essencial. Use:

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

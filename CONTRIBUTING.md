# Contribuindo com o PesquisAI

Obrigado por considerar contribuir! Este documento contém as diretrizes para contribuir com o projeto.

## Código de Conduta

Este projeto segue padrões éticos de pesquisa científica. Seja respeitoso, construtivo e profissional.

## Como Contribuir

### Reportando Bugs

1. Verifique se o bug já foi reportado nas [issues](https://github.com/gustavobraga-byte/PesquisAI/issues)
2. Abra uma nova issue com:
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs. observado
   - Logs relevantes (se aplicável)

### Sugerindo Melhorias

Abra uma issue com o rótulo `enhancement` descrevendo:
- O problema que você quer resolver
- Sua sugestão de solução
- Alternativas consideradas

### Pull Requests

1. Faça um fork do repositório
2. Crie uma branch descritiva:
   ```bash
   git checkout -b feature/nome-da-feature
   ```
3. Desenvolva seguindo os padrões do projeto
4. Teste suas alterações
5. Envie o PR com descrição clara do que mudou

## Padrões de Código

### Python
- Usar Python >= 3.10
- Seguir PEP 8
- Adicionar type hints em todas as funções
- Adicionar docstrings no estilo Google
- Nomes de variáveis e funções em inglês
- Mensagens para o usuário em português (ou via i18n)

### Organização de Módulos
- Cada módulo deve ter responsabilidade única
- Estados globais devem ser explicitamente documentados
- Módulos não devem ter dependências circulares

### Skills
Skills são módulos que conectam o agente a fontes de dados ou capacidades.
Para adicionar uma nova skill:
1. Crie o repositório da skill seguindo o padrão das skills existentes
2. Adicione o repositório em `setup_skills.py`
3. Documente no README

## Ambiente de Desenvolvimento

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/PesquisAI.git
cd PesquisAI

# (Opcional) Crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instale dependências
pip install -e .
```

## Executando Localmente

O PesquisAI foi projetado para rodar no Google Colab, mas pode ser testado localmente:

```bash
python -c "from main import run; run()"
```

Nota: funcionalidades do Google Drive não estarão disponíveis localmente.

## Estrutura do Projeto

```
PesquisAI/
├── main.py              # Entry point
├── launch_app.py        # Web interface (ttyd + HTTP wrapper)
├── constants.py         # Configurações compartilhadas
├── opencode_utils.py    # Utilitários do OpenCode
├── setup_drive.py       # Montagem do Google Drive
├── setup_dependencies.py # Instalação de dependências
├── setup_skills.py      # Instalação de skills
├── html_template.py     # Templates HTML
├── locale.py            # Internacionalização (i18n)
├── jokes.py             # Mensagens de loading
├── templates/           # Arquivos de template HTML
├── tests/               # Testes automatizados
├── docs/                # Documentação complementar
├── AGENTS.md            # Especificação do agente
└── MANUAL.md            # Manual do usuário
```

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a MIT License.

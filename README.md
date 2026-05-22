# 👨‍🔬 PesquisAI

Agente de IA para Pesquisadores Científicos, com foco em dados brasileiros (IBGE, DataSUS).

## Estrutura

O código foi modularizado para manter o notebook Colab o menor possível:

```
PesquisAI/
├── PesquisAI_Colab.ipynb   # Notebook mínimo para o Colab (apenas 1 célula de código)
├── main.py                  # Script principal que orquestra tudo
├── setup_dependencies.py    # Instala OpenCode e configura tema/agente
├── setup_skills.py          # Clona e instala as skills necessárias
├── setup_drive.py           # Monta Google Drive e configura diretório
├── launch_app.py            # Inicia ttyd, servidor web e frontend
└── README.md                # Este arquivo
```

## Como usar

1. **Faça upload de `PesquisAI_Colab.ipynb` para o Google Colab**
   - Ou hospede este repositório no GitHub e use o notebook diretamente

2. **No Colab, clique em `Ambiente de execução → Executar tudo`** (ou `Ctrl + F9`)

3. **Aguarde** - você verá "Carregando o PesquisAI..." até que tudo esteja pronto

4. **Clique no botão `Abrir o PesquisAI`** quando ele aparecer

## Vantagens desta estrutura

### ✅ Notebook Colab mínimo
- Apenas **1 célula de código** (em vez de várias células grandes)
- Todo o resto está no GitHub

### ✅ Mínimo de saídas
- Apenas um spinner animado "Carregando..." enquanto inicializa
- Quando tudo estiver pronto, aparece **apenas o botão** para abrir o app

### ✅ Código organizado
- Cada módulo tem uma responsabilidade única
- Fácil de manter e atualizar

## Para atualizar

Quando quiser mudar algo:
1. Edite os arquivos `.py` neste repositório
2. Faça push para o GitHub
3. O Colab automaticamente usará a versão mais próxima

## URLs padrão no repositório

Atualmente o notebook usa:
```
REPO_URL = "https://github.com/gustavobraga-byte/PesquisAI.git"
```

Se você hospedar em outro repositório, edite essa linha no `PesquisAI_Colab.ipynb`.

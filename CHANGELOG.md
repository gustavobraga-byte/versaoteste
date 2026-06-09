# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

## [1.0.0] — 2026-06-09

### Adicionado
- Projeto inicial do PesquisAI
- Skills: IBGE, DataSUS, científica, ABNT/UFV, análise qualitativa, dados Brasil, agroBR
- Interface web via ttyd com wrapper HTTP
- Sistema de backup/restore de sessões para o Google Drive
- Gerenciamento de chaves de API (provedores) com persistência no Drive
- Tema personalizado PesquisAI para OpenCode
- Manual completo (MANUAL.md) com instruções de uso
- Modelos de declaração de uso de IA (declaracao_uso_ia.md)
- Guia de citação (citacao_pesquisai.md)
- Disclaimers legais (disclaimer_pesquisai.md)

### Corrigido
- Módulo `html_template.py` ausente que impedia o lançamento
- Version mismatch entre AGENTS.md (v0.01) e constants.py (v1.0)
- Badge do Colab duplicado no README
- Seções duplicadas no MANUAL.md
- Código de carregamento de keys repetido 3 vezes no launch_app.py

# Grant Finder — SKILL.md

Esta skill é ativada quando o usuário pesquisar sobre editais, fomento, financiamento de pesquisa, bolsas, auxílios à pesquisa, chamadas públicas ou grant funding.

## Quando acionar

- "busque editais abertos"
- "fomento à pesquisa"
- "grant funding"
- "bolsas CNPq/CAPES/FAPEMIG"
- "auxílio à pesquisa"
- "financiamento para meu projeto"
- "submissão de proposta"
- "edital de pesquisa"
- "verifique elegibilidade para edital X"
- "orçamento para projeto de pesquisa"
- "minuta de proposta"

## Capacidades

1. **Busca em fontes oficiais** — 12+ agências de fomento (BR + internacional).
2. **Verificação de elegibilidade** — score 0-1 com razões, avisos e ações.
3. **Geração de orçamento** — rubricas conforme padrão da agência (custeio, capital, bolsas).
4. **Minutas de proposta** — seções padrão (Resumo, Justificativa, Objetivos, Metodologia, Cronograma, Equipe, Orçamento, Referências).

## Fontes verificadas

- **Brasil**: CNPq, CAPES, FAPEMIG, FAPESP, FINEP, FAPERJ, FAPERGS, FAPEAL, FAPEB, FAPEPI, FAPEAM, BNDES
- **Internacional**: NIH, NSF, ERC, Wellcome, Horizon Europe, CIHR, NHMRC

## Princípios de integridade

**REGRA ABSOLUTA — POLÍTICA DE ZERO-FABRICAÇÃO:**

1. SEMPRE declarar a data da consulta e a fonte.
2. Se a API oficial não retornar dado, declarar `[SEM DADOS SUFICIENTES]` e usar cache com data explícita.
3. Valores de bolsa são indicativos — SEMPRE conferir a portaria vigente no momento da submissão.
4. Prazos e valores de editais mudam — SEMPRE conferir o link oficial antes de submeter.
5. NUNCA inventar prazos, valores, requisitos ou agências.
6. Quando houver dúvida, preferir `[ESTIMATIVA FUNDAMENTADA]` com metodologia explícita.

## Outputs esperados

- Lista de editais compatíveis ordenada por score.
- Relatório de elegibilidade com razões, avisos, ações.
- Orçamento em Markdown (tabela) ou JSON.
- Minuta de proposta em Markdown (PT ou EN).

## Não faz

- Não simula chamada a uma API que falhou.
- Não "adivinha" prazos ou valores.
- Não cria DOI, número de edital ou URL falsa.
- Não submente propostas (apenas gera minutas).

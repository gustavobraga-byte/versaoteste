# 🧠 PesquisAI v0.5.1.2 — Botão "Memória Obsidian" na topbar

> **Data:** 2026-06-29
> **Tipo:** Feature (não-breaking)
> **Compatibilidade:** drop-in para v0.5.1.x (mesma API, mesmas dependências)

---

## ✨ Novidade

Um novo botão 🧠 **Memória Obsidian** foi adicionado à topbar do
PesquisAI, posicionado entre **Atalhos de Teclado** (⌨️) e
**Alternar tema** (◑). Clicar abre um overlay completo mostrando o
status, as estatísticas e as notas mais recentes do "segundo cérebro"
do agente (camada de memória persistente via vault Obsidian).

---

## 🎯 O que aparece no overlay

O overlay (`#memory-overlay`) mostra, em ordem:

1. **Cabeçalho**
   - Ícone 🧠 + título "Memória Obsidian" + subtítulo
   - **Badge de status** colorido (verde/âmbar/vermelho/cinza):
     - 🟢 Ativa
     - ⚪ Desativada (PESQUISAI_OBSIDIAN_VAULT não definida)
     - 🟡 Sem vault (variável definida, pasta não existe)
     - 🟡 Somente leitura
     - 🔴 Erro
   - Botão ✕ para fechar

2. **Mensagem amigável** (caixa com borda lateral colorida) explicando
   o status em linguagem natural

3. **Caminho do vault** (ex.: `/content/drive/My Drive/PesquisAI/vault`)

4. **Cards de estatísticas** (grid 2×2):
   - 📝 Notas (total)
   - 🏷️ Tags (total)
   - 🔗 Wikilinks (arestas do grafo)
   - 📏 Tamanho médio das notas (em chars)

5. **Daily notes recentes** (até 3, com 📅 e caminho)

6. **Notas recentes** (até 5, com título, caminho e tags como chips
   coloridos)

7. **Templates disponíveis** (até 10, como chips clicáveis)

8. **Rodapé**
   - Botão **↻ Atualizar** (força refetch, ignora cache)
   - Link **Abrir Drive** (abre a raiz do Google Drive)
   - Botão **Fechar**

---

## 🔧 O que foi modificado

### Backend (`pesquisai/launch_app.py`)

- **Novo endpoint** `GET /api/obsidian` que retorna o status da memória
  Obsidian em JSON. Usa o módulo `pesquisai.obsidian.ObsidianMemory`
  (v0.5.0+). Lê status, root, contadores, últimas 5 notas, últimas
  3 daily notes, e templates disponíveis.

### Frontend (`pesquisai/launch_app_responsive.py` e `launch_app_responsive_v041.py`)

- **Botão na topbar**: `<button id="memory-btn" onclick="openMemory()">`
  com ícone SVG de "cérebro" (path com linhas verticais + base)
- **Item no mobile menu** (drawer): "🧠 Memória Obsidian"
- **Overlay** `#memory-overlay` com 3 áreas (header / content / footer)
- **Funções JS**:
  - `openMemory(force?)` — abre overlay, com cache TTL de 5s
  - `closeMemory()` — fecha overlay
  - `renderMemory(d, dict?)` — renderiza JSON do backend em HTML
  - `openObsidianNote(path)` — heurística para abrir nota no Drive
- **Cores dinâmicas** no botão da topbar (verde quando ativa,
  vermelho em erro, etc.)
- **`closeMemory()` no handler de Escape**
- **19 chaves i18n** novas em 4 idiomas (pt_BR, en_US, es_ES, fr_FR)

### i18n (4 idiomas × 19 chaves = 76 strings)

| Chave | pt_BR | en_US | es_ES | fr_FR |
|---|---|---|---|---|
| `memory.title` | Memória Obsidian | Obsidian Memory | Memoria Obsidian | Mémoire Obsidian |
| `memory.subtitle` | Camada de memória persistente do agente | Agent's persistent memory layer | Capa de memoria persistente del agente | Couche de mémoire persistante de l'agent |
| `memory.tooltip` | Memória Obsidian (segundo cérebro) | Obsidian Memory (second brain) | Memoria Obsidian (segundo cerebro) | Mémoire Obsidian (deuxième cerveau) |
| `memory.status_ready` | 🟢 Ativa | 🟢 Active | 🟢 Activa | 🟢 Active |
| `memory.status_disabled` | ⚪ Desativada | ⚪ Disabled | ⚪ Desactivada | ⚪ Désactivée |
| `memory.status_no_vault` | 🟡 Sem vault | 🟡 No vault | 🟡 Sin vault | 🟡 Pas de vault |
| `memory.status_read_only` | 🟡 Somente leitura | 🟡 Read-only | 🟡 Solo lectura | 🟡 Lecture seule |
| `memory.status_error` | 🔴 Erro | 🔴 Error | 🔴 Error | 🔴 Erreur |
| `memory.notes_count` | Notas | Notes | Notas | Notes |
| `memory.tags_count` | Tags | Tags | Etiquetas | Étiquettes |
| `memory.links_count` | Wikilinks | Wikilinks | Wikienlaces | Wikiliens |
| `memory.avg_len` | Tam. médio | Avg. length | Tam. medio | Taille moy. |
| `memory.recent_daily` | Daily notes | Daily notes | Daily notes | Daily notes |
| `memory.recent_notes` | Notas recentes | Recent notes | Notas recientes | Notes récentes |
| `memory.no_notes` | Nenhuma nota ainda… | No notes yet… | Aún no hay notas… | Aucune note pour l'instant… |
| `memory.templates` | Templates | Templates | Plantillas | Modèles |
| `memory.open_vault` | Abrir Drive | Open Drive | Abrir Drive | Ouvrir Drive |
| `memory.refresh` | Atualizar | Refresh | Actualizar | Actualiser |
| `memory.notes_unit` | "" | "" | "" | "" |

---

## 📦 Arquivos do patch

| Arquivo | Linhas alteradas | Tipo |
|---|---|---|
| `pesquisai/launch_app.py` | +105 (após `/api/agents`) | Backend |
| `pesquisai/launch_app_responsive.py` | ~150 | Frontend |
| `pesquisai/launch_app_responsive_v041.py` | ~170 | Frontend |

> Nenhuma dependência nova. Nenhuma mudança breaking. 100% drop-in.

---

## 🧪 Testes incluídos

O patch inclui `validate.py` que executa **8 grupos de testes**:

1. ✅ Sintaxe Python dos 3 arquivos (`compile()` sem erros)
2. ✅ Sintaxe JS via `node --check` (6 funções: openMemory, closeMemory,
   renderMemory × 2 arquivos)
3. ✅ Backend: endpoint `/api/obsidian`, uso correto de
   `ObsidianMemory.from_env()`, `mem.stats()`, etc.
4. ✅ Botão na topbar: presença, ordem (shortcuts < memory < theme),
   `id="memory-btn"`, tooltip i18n
5. ✅ Overlay: 4 IDs HTML (`memory-overlay`, `memory-content`,
   `memory-status-badge`, `memory-open-drive`)
6. ✅ Item no mobile menu
7. ✅ `closeMemory()` no handler de Escape
8. ✅ i18n: 19 chaves `memory.*` em todos os 4 idiomas

**Total: 36+ asserções, todas passando.**

---

## 🛠️ Como aplicar

```bash
# 1. Backup (recomendado)
cp "/content/drive/My Drive/PesquisAI/pesquisai/launch_app.py" \
   "/content/drive/My Drive/PesquisAI/pesquisai/launch_app.py.bak.v0.5.1.2"
cp "/content/drive/My Drive/PesquisAI/pesquisai/launch_app_responsive.py" \
   "/content/drive/My Drive/PesquisAI/pesquisai/launch_app_responsive.py.bak.v0.5.1.2"
cp "/content/drive/My Drive/PesquisAI/pesquisai/launch_app_responsive_v041.py" \
   "/content/drive/My Drive/PesquisAI/pesquisai/launch_app_responsive_v041.py.bak.v0.5.1.2"

# 2. Aplique o patch (já está aplicado no zip)
cp launch_app.py \
   "/content/drive/My Drive/PesquisAI/pesquisai/launch_app.py"
cp launch_app_responsive.py \
   "/content/drive/My Drive/PesquisAI/pesquisai/launch_app_responsive.py"
cp launch_app_responsive_v041.py \
   "/content/drive/My Drive/PesquisAI/pesquisai/launch_app_responsive_v041.py"

# 3. Reinicie o PesquisAI (Ctrl+C + reexecute a célula de launch)
```

---

## 🔍 Como verificar

Após reiniciar, observe a topbar: deve aparecer um novo ícone 🧠
entre ⌨️ (Atalhos) e ◑ (Tema). Clicar deve abrir o overlay com:

- **🟢 Ativa** (se o vault está no Drive) com cards de estatísticas
- **⚪ Desativada** (se `PESQUISAI_OBSIDIAN_VAULT` não está definida)
  com mensagem explicativa
- **🔴 Erro** (se o módulo não está instalado) com botão "Abrir Drive"
  oculto

E o **botão da topbar muda de cor**:
- 🟢 verde = vault ativo e gravável
- 🟡 âmbar = sem vault ou read-only
- 🔴 vermelho = erro
- ⚪ cinza = desativado

---

## 📊 Resumo da versão

| Item | Valor |
|---|---|
| Versão | 0.5.1.1 → 0.5.1.2 |
| Tipo | feature (non-breaking) |
| Backend | +1 endpoint (`/api/obsidian`) |
| Frontend | +1 botão na topbar, +1 overlay, +4 funções JS |
| i18n | +19 chaves × 4 idiomas = 76 strings |
| Dependências | nenhuma |
| Linhas adicionadas | ~420 (somadas) |
| Compatibilidade | 100% drop-in |

---

*PesquisAI · v0.5.1.2 — feature · 2026-06-29*

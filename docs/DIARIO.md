# Diário do experimento

Registro de cada tarefa feita com IA (GDD, seção 11): o que foi pedido, o que a IA fez,
onde errou, correções manuais e quanto tempo levou.

## Modelo de entrada

```
## AAAA-MM-DD — Título da tarefa

- **Agente / modelo:**
- **Pedido:**
- **O que foi feito:**
- **O que deu errado:**
- **Correções manuais (o quê e quanto tempo):**
- **Tempo:**
- **Commits:**
```

---

## 2026-09-25 — Regras dos agentes + Marco 1 (grade 3D, câmera, esqueleto da simulação)

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai 4.2.3 ligado ao editor.
- **Pedido:**
  1. Criar `CLAUDE.md` e `AGENTS.md` com as regras fixas tiradas do GDD.
  2. Propor e implementar o primeiro marco: mapa plano em grade 3D, câmera estilo Albion
     (WASD, zoom na roda, Q/E em 90°), formas simples (cubos = recursos, cilindros = máquinas,
     cápsulas = aldeões) e o esqueleto da simulação com tick fixo separada da cena.
  3. Criar este diário e registrar a tarefa. Mostrar o plano antes de implementar.
- **O que foi feito:**
  - `CLAUDE.md` / `AGENTS.md` (idênticos) com stack, regra da simulação separada, dados em JSON,
    `dotnet build` obrigatório, tarefas pequenas, um commit por tarefa, pastas e estilo de código.
  - Simulação em C# puro (`src/Simulation/`, sem `using Godot`): `SimClock` (20 ticks/s, com teto
    de 5 ticks por frame), `SimWorld`, `WorldGrid`, entidades e `MapLoader`, que lê `data/maps/mapa_teste.json`.
  - Cena (`src/View/`, `scenes/Main.tscn`): `GameRoot` avança o relógio e roda os ticks; `WorldView`
    desenha o chão com grade (shader) e as formas com as cores da paleta do GDD; `CameraRig` é a
    câmera estilo Albion, com inclinação de 50° perto e 65° longe. Dois aldeões patrulham rotas na simulação
    e a cápsula interpola entre os ticks. Um rótulo de debug mostra tick, ticks/s e FPS.
  - Input map (`camera_*`) e cena principal configurados pelo MCP.
  - Verificado rodando o jogo pelo MCP: 20 ticks/s medidos, sem erros no log. Q girou exatamente 90°,
    o zoom afastou e aumentou a inclinação, e W moveu o foco na direção certa com a câmera girada.
- **O que deu errado:**
  - O `mv ~/Downloads/GDD.md` inicial falhou porque o arquivo ainda não estava lá. Ele foi colocado depois,
    à mão, pelo humano.
  - O GDD chegou com um comando de shell colado na última linha (`pbpaste > ... && head -3 ...`); removido.
  - Erro de compilação: a classe `GridMap` da simulação conflitou com `Godot.GridMap`. Renomeada
    para `WorldGrid` e registrada como armadilha de nomes.
  - Na chamada `bind_event` o MCP exige que a ação exista antes; `ensure_binding` resolve em uma chamada.
  - `input_sequence` do MCP recusou o formato de passos tentado; os testes usaram `input_action` avulso.
  - Um teste com a tecla W simulada (`input_key`) deslocou o foco numa direção inesperada; o teste
    controlado com `input_action` deu a direção correta. **Causa não identificada — confirmar no teclado real.**
- **Correções manuais (o quê e quanto tempo):** nenhuma no código. O humano moveu o GDD para `docs/` à mão.
- **Tempo:** cerca de 15 min de trabalho do agente (20:14–20:29), sem contar a revisão do plano.
- **Commits:** `a250651` (regras e diário) e o commit do marco 1.

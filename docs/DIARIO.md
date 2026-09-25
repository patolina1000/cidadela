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
    controlado com `input_action` deu a direção correta. *Resolvido na tarefa do Castelão:* o W foi enviado
    logo depois do Q, com o giro de 90° ainda animando, então a "frente" estava no meio do caminho. Não era bug.
- **Correções manuais (o quê e quanto tempo):** nenhuma no código. O humano moveu o GDD para `docs/` à mão.
- **Tempo:** cerca de 15 min de trabalho do agente (20:14–20:29), sem contar a revisão do plano.
- **Commits:** `a250651` (regras e diário) e o commit do marco 1.

---

## 2026-09-25 — GDD: personagem principal (o Castelão)

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, editando o GDD vivo no Claude Docs.
- **Pedido:** colocar no GDD um personagem principal que anda com WASD, com a câmera seguindo, e
  centrar o jogo nele. Pesquisar como Factorio e outros jogos de automação fazem isso.
- **O que foi feito:**
  - Nova seção 20 no GDD (Claude Docs + reexport em `docs/GDD.md`): o Castelão. Traz por que ter um
    personagem, a tabela de referências (Factorio, Factorio 2.0, The Riftbreaker, Necesse, Mindustry, Core Keeper),
    as regras (movimento, câmera, alcance de 10 células, trabalho manual, combate, morte, andares), a progressão
    por era (aprendizes → estandarte → olho arcano) e a regra técnica (posição na simulação).
  - Ajustes em outras seções: pilar 6, loop curto, controles de câmera (seção 12), item no MVP e pergunta em
    aberto marcada como decidida. "Perguntas em aberto" virou a seção 21.
  - `CLAUDE.md` / `AGENTS.md` passam a citar a seção 20.
- **O que deu errado:**
  - Duas páginas (Mindustry e Core Keeper no Fandom) deram erro 402 no fetch. As linhas da tabela foram reescritas
    para dizer só o que as páginas abertas confirmam, e a fonte da Mindustry trocou para a Miraheze.
  - O export do Claude Docs veio grande demais para a resposta da ferramenta (62 mil caracteres); decodificado do
    arquivo salvo com Python.
- **Correções manuais:** nenhuma.
- **Tempo:** cerca de 10 min.
- **Impacto no código:** o marco 1 tem câmera livre com WASD. Isso muda: WASD passa a mover o Castelão
  e a câmera o segue. Fica como próxima tarefa.

---

## 2026-09-25 — Castelão: personagem principal andando com WASD

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** criar o personagem principal e fazê-lo andar (GDD, seção 20).
- **O que foi feito:**
  - Simulação: `Castellan` (posição, posição anterior, direção, velocidade), fila de comandos
    (`ISimCommand` + `MoveCommand`) aplicada no começo de cada tick, e o Castelão preso dentro do mapa.
    A posição inicial e a velocidade (6 células/s) vêm do `mapa_teste.json`.
  - Cena: o `GameRoot` lê o WASD, gira a direção pelo giro da câmera e manda um `MoveCommand` só quando a
    direção muda. O `WorldView` desenha o Castelão como cápsula roxa (paleta) com "nariz" laranja apontando
    a direção. O `CameraRig` segue o Castelão com atraso suave; o movimento livre da câmera saiu.
  - Ações de input renomeadas: `camera_forward/back/left/right` → `move_*`.
  - `<Nullable>enable</Nullable>` no csproj (o código já usava anotações; o build dava 2 avisos).
  - Verificado rodando: W andou para -Z com a câmera sem giro; depois do Q, D andou para -Z (a "direita"
    girada); a câmera ficou centrada nele; 20 ticks/s, sem erros.
- **O que deu errado:**
  - Avisos CS8632 porque o projeto não tinha nullable ativado; resolvido no csproj.
  - `input_action` do MCP só muda o estado da ação e não gera evento, então o Q (lido em `_UnhandledInput`)
    não girou por esse caminho; com `input_key` funcionou.
- **Correções manuais:** nenhuma.
- **Tempo:** cerca de 3 min de relógio (20:36–20:38), segundo o `date` do terminal.
- **Fica para depois:** colisão com recursos e máquinas (hoje ele atravessa), alcance de 10 células, coleta.

---

## 2026-09-25 — Câmera toda no mouse

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** tirar o controle da câmera do teclado e deixar tudo no mouse.
- **O que foi feito:**
  - Giro: segurar o botão do meio e arrastar para os lados; cada 60 px (`RotateDragPixels`) dá um passo de 90°,
    mantendo a regra do GDD. Arrastar para a direita gira o mundo para a direita. O zoom continua na roda.
  - Removidas as ações `camera_rotate_left/right` (Q/E). O teclado fica só para o Castelão (WASD).
  - GDD atualizado (seções 12 e 20) no Claude Docs e reexportado.
  - Verificado: arrasto de 24 px não gira; arrasto de 70 px gira exatamente um passo.
- **O que deu errado:**
  - A primeira versão usava `motion.Relative`, que vem zerado nos eventos sintéticos do MCP; o teste não girava.
    Troquei para a diferença de posição do mouse, que funciona com mouse real e sintético.
  - Durante um teste, a câmera girou 6 passos e o Castelão andou cerca de 8 células sem comando meu: provavelmente
    o humano mexendo na janela do jogo ao mesmo tempo. O teste controlado seguinte deu o resultado esperado.
  - Tentei exportar o GDD com `maxBytes: 1` para forçar salvar em arquivo; foi recusado. Sem `maxBytes`, funcionou.
- **Correções manuais:** nenhuma.
- **Tempo:** cerca de 3 min de relógio (20:41–20:43).

---

## 2026-09-25 — Câmera copiada do Factorio

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** pesquisar como funciona a câmera do Factorio e copiar.
- **O que foi pesquisado:** no Factorio a câmera fica travada no personagem (sempre no centro), não gira e
  não arrasta no modo personagem; o jogador só mexe no zoom pela roda. Valores do jogo base, segundo o mod
  Zooming Reinvented: cerca de 1,1 por clique e afastamento máximo de cerca de 0,4.
- **O que foi feito:**
  - `CameraRig` reescrito: travado no Castelão sem atraso (o desenho dele já é interpolado entre ticks),
    sem giro, inclinação fixa em 55° e zoom de 0,4 a 2,5 com passo de 1,1 por clique (suavizado).
  - Saíram o giro com o botão do meio e a inclinação variável. O WASD agora é fixo no mundo
    (W = norte), e o código que girava a entrada pela câmera foi removido.
  - GDD (seções 12 e 20) atualizado no Claude Docs e reexportado, com as fontes.
  - Verificado: câmera na mesma posição do Castelão; D andou para leste; depois de 12 cliques de zoom para
    fora, a distância parou em 40 (= 16 / 0,4).
- **O que deu errado:** a wiki de controles do Factorio e duas páginas de mods não dão todos os números do jogo
  base; os valores de zoom vêm da descrição de um mod, que cita os valores do jogo base.
- **Correções manuais:** nenhuma.
- **Tempo:** cerca de 3 min de relógio (20:47–20:49), mais a pesquisa antes.

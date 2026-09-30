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

---

## 2026-09-25 — Câmera: espiar com o cursor e arrastar o mundo

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** a câmera travada podia atrapalhar a construção da base. Deixar o jogador mover a câmera
  pelo mouse, do jeito mais fluido que os jogos top-down usam.
- **O que foi pesquisado:** Nuclear Throne e Enter the Gungeon puxam a câmera para o cursor sem perder
  o personagem de vista; o mapa do Factorio se arrasta com o mouse; o guia "Scroll Back" (Itay Keren,
  GDC 2015) recomenda suavização contínua e nada de saltos.
- **O que foi feito:**
  - Espiar: a câmera se desloca na direção do cursor, até 4 células com o cursor na borda (mais com zoom
    afastado), suavizado. O Castelão continua travado; só o deslocamento é suavizado. O cálculo usa a
    posição do cursor na tela, não no chão, para a câmera não correr atrás de si mesma.
  - Arrastar: botão do meio agarra o ponto do chão sob o cursor e o mantém lá (raio da câmera até y = 0).
    A câmera fica solta, presa aos limites do mapa, e volta suavemente ao Castelão quando ele anda.
  - GDD (seções 12 e 20) atualizado e reexportado.
  - Verificado: cursor na borda direita → câmera 4 células a leste; arrasto de 200 px → 4,09 células,
    igual ao valor calculado para esse zoom; a câmera parou onde foi solta; W trouxe ela de volta ao Castelão.
- **O que deu errado:**
  - A primeira versão tinha inércia ao soltar (como mapas de celular). A velocidade era calculada pelo tempo
    do frame e os eventos chegavam em rajada, e a câmera deslizou até a borda do mapa. Corrigi a medição, mas
    decidi tirar a inércia: para construir, a câmera precisa parar onde foi solta.
  - Os eventos sintéticos do MCP e a posição real do cursor se misturam na primeira leitura; foi preciso
    esperar a suavização assentar antes de medir.
- **Correções manuais:** nenhuma.
- **Tempo:** cerca de 3 min de relógio (20:53–20:56), mais a pesquisa antes.

---

## 2026-09-25 — Giro da câmera no mouse + tela cheia

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** girar a câmera também pelo mouse e fazer o jogo ocupar sempre a tela toda.
- **O que foi feito:**
  - Giro no botão direito arrastado: gira livre seguindo o mouse (0,3° por pixel) e, ao soltar, encaixa
    suavemente no múltiplo de 90° mais próximo (regra do GDD sobre a leitura das esteiras). Só vira giro
    depois de 8 px de arrasto, para um clique direito simples ficar livre para "remover" no futuro.
  - O espiar com o cursor e o WASD voltaram a ser relativos ao giro da câmera.
  - Tela cheia (`display/window/size/mode = 3`) e interface que escala com a resolução
    (`stretch/mode = canvas_items`, `aspect = expand`).
  - GDD (seções 12 e 20) atualizado e reexportado.
  - Verificado: jogo em 3024×1890 (tela inteira do MacBook); arrasto curto girou livre até -41° e voltou a 0°
    ao soltar; arrasto longo encaixou em -90°; com -90°, W levou o Castelão para +X.
- **O que deu errado:** o primeiro teste de giro não girou. Com a escala da interface, os pixels dos eventos
  sintéticos viram menos pixels no jogo, e o primeiro movimento de 10 px ficou abaixo do limite de 8 px (só
  "armou" o giro). Com um movimento a mais, funcionou. Com o mouse real isso não acontece.
- **Correções manuais:** nenhuma.
- **Tempo:** cerca de 2 min de relógio (20:58–21:00), segundo o `date` do terminal.

---

## 2026-09-25 — Espiar com o cursor mais contido

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** a câmera se mexia demais com o mouse; mover só quando o jogador claramente quer ver mais
  para um lado, e só um pouco.
- **O que foi feito:**
  - Zona morta: com o cursor nos 60% centrais da tela (`LookAheadDeadZone = 0.6`), a câmera não se mexe.
  - Da zona morta até a borda, o deslocamento sobe com curva suave (smoothstep) até 2,5 células
    (antes 4, linear desde o centro). Suavização mais lenta (4, antes 6).
  - O cursor passou a vir dos eventos de movimento dentro do jogo; se o mouse sai da janela ou o jogo perde
    o foco, a câmera para de espiar e volta ao Castelão.
  - GDD (seção 12) atualizado e reexportado.
  - Verificado: cursor na zona morta → câmera exatamente sobre o Castelão.
- **O que deu errado:**
  - A câmera lia a posição global do mouse; com o cursor fora do jogo (o humano estava usando o mouse em
    outro lugar), ela ficava presa no máximo para um lado. Corrigido.
  - O teste da borda não pôde ser medido: o mouse real do humano, dentro do jogo, sobrescrevia o cursor
    simulado. **Pendente:** confirmar no uso real que a borda espia só um pouco.
- **Correções manuais:** nenhuma.
- **Tempo:** cerca de 21:03–21:04 de relógio.

---

## 2026-09-25 — Marco 2: o Castelão trabalha

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** próximo marco. Plano aprovado: testes da simulação, colisão, célula sob o cursor com alcance,
  coleta à mão com clique e inventário na tela.
- **O que foi feito:**
  - Testes: projeto xUnit em `tests/` (net10.0) que compila só `src/Simulation/`; ligado à solução, então
    `dotnet build` e `dotnet test` na raiz cobrem tudo. O jogo exclui `tests/**` da compilação. 20 testes:
    relógio, movimento, colisão, deslizar na parede, alcance, coleta, esgotar, JSON reais.
  - Dados: `data/resources.json` (nome, segundos por item, quantidade por nó) e `data/castellan.json`
    (velocidade, alcance 10, raio). O mapa guarda só onde o Castelão nasce.
  - Simulação: colisão círculo × célula, um eixo por vez (desliza nas paredes); `GatherCommand`; coleta 1 item
    por vez enquanto parado e no alcance; andar interrompe (como no Factorio); nó esgotado some e libera a célula;
    inventário por tipo.
  - Cena: destaque da célula sob o cursor (claro no alcance, mais forte sobre recurso, vermelho fora);
    clique esquerdo coleta; recursos esgotados somem; inventário e progresso na tela.
  - CLAUDE.md/AGENTS.md: `dotnet test` obrigatório ao mexer na simulação; GDD (seção 18): xUnit no lugar do GdUnit4.
  - Verificado no jogo: andar até as árvores, clicar → "Coletando Madeira", 15 madeiras em ~15 s; andar parou a
    coleta; o Castelão encostou nas árvores sem atravessar; destaque claro na árvore e vermelho longe.
- **O que deu errado:**
  - Nada quebrou. Os 20 testes passaram na primeira execução.
  - Para clicar na árvore pelo MCP, foi preciso calcular à mão a projeção da câmera até o pixel da tela.
  - Os aldeões ainda atravessam tudo (inclusive o Castelão); ficou fora do escopo.
- **Correções manuais:** nenhuma.
- **Tempo:** 21:17–21:21 de relógio.

---

## 2026-09-25 — Efeitos visuais do Castelão trabalhando

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** um "efeitinho" visual do Castelão fazendo as coisas.
- **O que foi feito (só na cena; a simulação não mudou):**
  - `CastellanVisual`: pivô nos pés; golpe de coleta sincronizado com o progresso do item (puxa para trás,
    bate para a frente e acerta quando o item cai); quica ao andar, pela distância andada; vira suave.
  - `Effects`: lascas (CPUParticles3D de cubinhos da cor do recurso) e texto flutuante "+1 Madeira" que sobe
    e some; os dois se apagam sozinhos.
  - Recursos: a cada item tirado, sacodem (achatam e voltam), soltam lascas e o "+1"; encolhem até 55% conforme
    esgotam; ao esgotar, estouram em mais lascas. Os efeitos nascem de comparar o restante com o frame anterior.
- **Verificado no jogo (pelos nós, porque a janela foi para segundo plano e os screenshots congelaram):**
  inclinação de 13,8° na fase de puxar; árvore em 77% do tamanho; lascas e "+1" criados a cada item e
  apagados depois.
- **O que deu errado:** o primeiro clique calculado pela projeção errou, porque a câmera ainda estava se
  movendo (espiar com o cursor); acertei mirando pelo screenshot. Sem screenshot em movimento para o diário.
- **Correções manuais:** nenhuma.
- **Tempo:** 21:23–21:25 de relógio.

---

## 2026-09-25 — Coletar só encostado no recurso

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** o Castelão precisa estar perto do recurso para coletar.
- **O que foi feito:**
  - Dois alcances separados em `data/castellan.json`: `reach` (10, construir e abrir máquinas) e
    `gatherReach` (1,0 do centro do corpo até a borda do recurso = encostado, de lado ou na diagonal).
  - `Castellan.CanGather`; a coleta começa e continua só com o Castelão encostado.
  - Destaque do cursor: recurso longe fica vermelho, recurso encostado fica claro forte.
  - Testes: 23 (novos: coletar de lado e na diagonal, longe demais mesmo dentro do alcance de construir,
    andar até a árvore e coletar). GDD (seção 20, "Alcance") atualizado e reexportado.
  - Verificado no jogo: a ~3 células o clique não coletou e o destaque ficou vermelho; encostado, coletou.
- **O que deu errado:** para o teste no jogo foi preciso recalcular o pixel da árvore várias vezes: a câmera
  espiava seguindo o mouse real do humano, e os screenshots congelavam com a janela em segundo plano.
- **Correções manuais:** nenhuma.
- **Tempo:** 21:31–21:33 de relógio.

---

## 2026-09-25 — Marco 3: construir

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** marco 3 aprovado: gastar itens para construir esteiras, baú e máquinas; prévia fantasma;
  R gira; desmontar devolve o custo; efeitos; testes.
- **O que foi feito:**
  - `data/buildings.json` (ordem = barra): esteira (1 madeira, não bloqueia), baú (4 madeira), serraria,
    fundição, forja. As máquinas do mapa viraram construções desse tipo (`Machine` saiu).
  - Simulação: `Building`, `Direction`, `BuildCheck` (fora do mapa, fora do alcance, ocupado — inclusive
    pelo corpo do Castelão para construções sólidas —, itens insuficientes), `BuildCommand` e
    `DeconstructCommand` (devolve 100%), `Inventory.Has/TryRemove`. 35 testes (12 novos).
  - Cena: modelos com silhueta própria por tipo (esteira com seta), prévia translúcida verde/vermelha,
    barra de construção clicável (teclas 1–9, borda verde no escolhido, apagada quando não dá para pagar),
    R gira, segurar e arrastar faz fileira, clique direito cancela ou desmonta, Esc cancela.
    Construção "brota" com poeira e "-1 Madeira"; desmontar estoura e mostra "+4 Madeira".
  - A câmera ganhou o evento de clique direito sem arrasto (o arrasto continua girando).
  - GDD (seção 20, regra "Construir") atualizado e reexportado.
  - Verificado no jogo: coletou 30 madeiras (a árvore esgotou), prévia verde com seta, R virou para leste,
    arrastar fez 3 esteiras, baú construído (-4), clique direito cancelou e o seguinte desmontou (+4).
- **O que deu errado:**
  - Erro de compilação: `Key - Key` dá `long` em C#; faltava um cast.
  - O botão escolhido na barra quase não se destacava com o tema padrão; ganhou borda e texto verdes.
  - Guiar o Castelão pelo MCP até a árvore levou várias tentativas (tempo variável entre comandos).
- **Correções manuais:** nenhuma.
- **Tempo:** 21:38–21:43 de relógio.

---

## 2026-09-25 — Animação de desmontar

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** uma pequena animação ao destruir (desmontar) as construções.
- **O que foi feito (só na cena):** a construção sacode (achata e estica), encolhe para dentro com um puxão
  e estoura em poeira; os itens devolvidos voam em arco (Bézier) até o Castelão, um cubinho da cor de cada
  recurso (até 4 por recurso), seguindo ele se andar. O texto "+8 Madeira +4 Pedra" continua.
- **Verificado no jogo:** desmontei a serraria do mapa; screenshots pegaram o achatamento e depois a poeira
  com os cubinhos saindo; inventário recebeu 8 madeiras e 4 pedras.
- **O que deu errado:** nada.
- **Tempo:** 21:47–21:48 de relógio.

---

## 2026-09-25 — Marco 4: esteiras que movem itens

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** marco 4 aprovado: itens andando nas esteiras até baús; o Castelão põe e recolhe itens.
- **O que foi feito:**
  - Simulação: `BeltLane` (fila da frente para trás, espaço mínimo 0,5 = 3 itens por esteira), `BeltItem`
    (progresso, posição e posição anterior para interpolar), tick das esteiras em duas fases (andar; depois
    passar para a esteira ou baú à frente; esteira de frente contra não aceita), baú com `Storage`,
    `InsertItemCommand` e `TakeFromChestCommand`; desmontar devolve o que estava em cima/dentro.
    `beltSpeed` (1,5) e `storage` em `data/buildings.json`. 46 testes (11 novos).
  - Cena: cubinhos da cor do recurso deslizando nas esteiras; inventário virou botões para segurar item na mão
    (borda verde); etiqueta sobre o baú sob o cursor com o conteúdo; clique no baú recolhe e os itens voam até
    o Castelão; linha de status diz o que está acontecendo.
  - GDD (seção 20, regra "Alimentar a fábrica") atualizado e reexportado.
  - Verificado no jogo: desmontei serraria e forja para ter itens; 4 esteiras para leste + baú; segurei madeira,
    pus 3 na primeira esteira, elas andaram e entraram no baú ("Baú / Madeira: 3"); recolhi e voltaram 3
    (com os cubinhos voando).
- **O que deu errado:** nada quebrou; os 46 testes passaram na primeira execução. Recolher do baú não tinha
  retorno visual; acrescentei os cubinhos voando.
- **Correções manuais:** nenhuma.
- **Tempo:** 21:49–21:53 de relógio.

---

## 2026-09-25 — Marco 5: máquinas que produzem

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** "pode ir para o próximo marco" (autorizado sem plano detalhado; o plano foi resumido na conversa).
- **O que foi feito:**
  - Dados: `data/items.json` (nome e cor de todos os itens; o código não tem mais cores fixas por recurso),
    `data/recipes.json` (serraria 1 madeira → 2 hastes / 2 s; fundição 2 ferros → 1 lingote / 3 s;
    forja 2 lingotes + 1 haste → 1 espada / 5 s). `resources.json` perdeu o nome (vem de items.json).
  - Simulação: `MachineState` (entrada até 2 ciclos, trabalha com tudo, saída até 5 ciclos e para),
    esteira que aponta para a máquina a abastece, a máquina empurra 1 item por tick para a esteira ou baú
    à sua frente, o Castelão põe à mão e recolhe a produção (`TakeAllCommand`, que substituiu
    `TakeFromChestCommand`), desmontar devolve entrada, saída e o ciclo em andamento. Validação das
    receitas no carregamento. 59 testes (13 novos).
  - Cena: seta de saída nas máquinas; lâmina da serraria gira e fundição/forja soltam fumaça quando trabalham;
    etiqueta da máquina com receita, entrada, pronto e estado ("Trabalhando 40%", "Esperando 2 Ferro",
    "Parada: saída cheia"); inventário com os 6 itens; recolher da máquina faz os itens voarem.
  - GDD (seção 5, "Como as máquinas funcionam") atualizado e reexportado.
  - Verificado no jogo: desmontei a forja (madeira e ferro); baú na frente da serraria; 2 madeiras à mão →
    serraria girando → "Baú / Haste: 4"; 4 ferros na fundição → fumaça → "Pronto: Lingote: 2";
    recolhi 2 lingotes.
- **O que deu errado:** string bruta do C# (`"""`) quebrada em duas linhas num teste (erro de sintaxe, corrigido).
  Recolher da máquina não tinha retorno visual; ganhou os itens voando.
- **Correções manuais:** nenhuma.
- **Tempo:** 21:55–22:00 de relógio.

---

## 2026-09-25 — Marco 6: aldeões trabalhando (lenhador, pedreiro, mineiro)

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** o humano redirecionou o marco 6 (eu tinha sugerido dia/noite e hordas): aldeões trabalhando como
  lenhador, pedreiro e minerador de ferro. Plano aprovado.
- **O que foi feito:**
  - Dados: 3 cabanas de trabalho em `data/buildings.json` (campo `job`: ofício, recurso, raio 12, capacidade 50)
    e `data/villagers.json` (velocidade 3, coleta 1,5× mais lenta, carga 5). O mapa começa com 3 aldeões livres.
  - Simulação: `GridPath` (A* em 8 direções, sem cortar quina, vários objetivos), `Villager` reescrito com
    tarefas (sem emprego, esperando, indo ao recurso, coletando, voltando), `Workplace` (trabalhador + guardado),
    atribuição automática do aldeão livre mais perto, cabana solta na esteira/baú da frente (código de
    "empurrar para frente" agora compartilhado com as máquinas), recolher e desmontar devolvem o guardado e a carga.
    75 testes (16 novos: caminho, ciclo de trabalho, carga, obstáculos, raio, cabana cheia, esteira, liberar e
    reatribuir).
  - Cena: aldeão com chapéu da cor do ofício, carga nas costas, golpe ao coletar, quicar e virar suave; cabanas
    com telhado da cor do recurso; etiqueta com guardado e o que o trabalhador está fazendo. Barra com 8 construções.
  - GDD (seção 6, "Trabalho básico") atualizado e reexportado.
  - Verificado no jogo: cabana do lenhador a meio caminho das árvores; o aldeão mais perto ganhou chapéu, foi,
    coletou ("+1 Madeira" nas árvores) e entregou ("Guardado: 10/50"); recolhi 10 madeiras da cabana.
- **O que deu errado:**
  - **Bug do marco 5 encontrado:** recolher a produção de uma máquina também esvaziava a entrada e o ciclo em
    andamento. Causa: um `str.replace` do meu script de edição trocou duas ocorrências do mesmo trecho no marco 5.
    Os testes não pegaram (o de recolher só olhava a saída). Corrigido, com teste de regressão; os scripts de
    edição agora exigem que cada trecho apareça uma única vez.
  - Clicar na cabana não recolhia: o `GameRoot` só recolhia de baús e máquinas. A simulação estava certa; o erro
    estava só na ligação com a entrada. Corrigido e verificado no jogo.
- **Correções manuais:** nenhuma.
- **Tempo:** 22:08–22:14 de relógio.

---

## 2026-09-25 — Arte: pipeline Meshy + protagonista (conceito → modelo com rig e animações)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte` (só `assets/` e `tools/`,
  sem Godot). Blender 5.1.1 em modo headless, uv 0.12, API da Meshy (documentação lida em docs.meshy.ai:
  llms-full.txt e openapi.yaml).
- **Pedido:**
  1. Pipeline em Python/uv (`tools/meshy_pipeline/`) que lê `tools/assets.json` e, por asset, gera em
     low-poly, texturiza, faz rig e animações (personagens) e baixa GLB; padronizar no Blender; folha de prévia.
  2. No meio do plano, o humano trocou o protagonista: sai o Castelão robusto, entra a personagem do conceito
     `assets/conceitos/protagonista.jpg`. Recortar frente e costas com Pillow, mostrar antes de gastar,
     gerar com Multi-Image to 3D em T-pose, rig + idle/walk/attack/work, cristal do peito como material
     emissivo separado.
  3. Decisões do humano: espelhar a mão que falta, apagar o cristal das costas, escala do jogo (opção A:
     aldeão e protagonista 0,8 m, construções 0,9 × 0,9 m de base, 1 célula = 1 m) e gerar só a
     protagonista antes do resto do lote.
- **O que foi feito:**
  - `.env` no `.gitignore` antes de tudo; a chave nunca foi impressa. Também ignorados: `.venv`, `state.json`
    e `assets/modelos/*/bruto/` (arquivos brutos da Meshy; lá eles expiram em 3 dias).
  - `tools/meshy_pipeline/crop_concept.py`: máscara por cor (a personagem é fria, o pergaminho é quente),
    maior região conectada por vista (some com cabeças isoladas, textos, setas e ícones), sem o brilho do
    cristal no papel. Correções no conceito: mão direita espelhada (com a faixa do pulso) colada no braço
    esquerdo nas duas vistas; cristal das costas coberto com o cabelo ao lado.
  - `tools/meshy_pipeline/pipeline.py`: saldo e estimativa sem gastar (padrão), `--run` para gerar, estado
    retomável, no máximo uma nova tentativa por etapa, trava de 450 créditos no código.
  - `tools/blender/normalize.py`: escala do jogo num nó raiz com o nome do asset (as animações não são
    tocadas), pivô no centro da base, frente em +Z do glTF, clipes renomeados, texturas em 512 px, material
    `Cristal` separado. `tools/blender/render_views.py` + `compare_sheet.py`: folha de comparação.
  - Resultado: `assets/modelos/protagonista/protagonista.glb` (984 KB): 2.974 faces, 1 malha com esqueleto,
    clipes `idle`, `walk`, `attack`, `work`, materiais `Material_1` (corpo) e `Cristal` (4 faces, textura de
    emissão só com os pixels do cristal, `emissiveStrength` 3). Tamanho em T-pose: 0,75 × 0,22 × 0,80 m.
    Prévia: `assets/previews/protagonista_comparacao.png`.
- **Chamadas e prompts usados:**
  - Multi-Image to 3D, sem prompt de texto (a textura vem das imagens): `image_urls` = frente, costas;
    `ai_model: latest` (Meshy 7.1), `pose_mode: t-pose`, `should_remesh: true`, `topology: triangle`,
    `target_polycount: 3000`, `image_enhancement: false` (para não reinterpretar o conceito),
    `remove_lighting: true`, textura 2k.
  - Rig: `input_task_id` do modelo, `height_meters: 1.4`. Animações num só GLB com `action_ids`
    [0 Idle, 30 Casual Walk, 97 Left Slash, 237 Charged Axe Chop].
  - Prompt-modelo da seção 17 guardado em `tools/assets.json` para o resto do lote (ainda não usado).
- **Créditos:** 47 (30 modelo + 5 rig + 12 animações), exatamente a estimativa. Saldo: 3.100 → 3.053.
- **Comparação conceito × modelo:**
  - ✅ Corpo pequeno e frágil: magra, membros finos, cabeça um pouco grande.
  - ✅ Pele azul-pálida.
  - ✅ Cabelo longo e liso azul-acinzentado, até a cintura nas costas; em cima fica mais "capacete" que no desenho.
  - ✅ Olhos grandes e vazios (brancos, sem pupila); a expressão triste sobreviveu.
  - ✅ Cristal azul no peito, no lugar certo; à noite só ele brilha. Em low-poly ele vira pintura sobre
    4 faces, não uma pedra em relevo.
  - ✅ Túnica e calça rasgadas cinza-azuladas, com a faixa na cintura. Os rasgos da barra ficaram mais
    simples; há um triângulo claro na frente da túnica (artefato da textura).
  - ✅ Faixas nos pulsos (na textura, visíveis de perto).
  - ✅ Pés descalços.
  - Diferenças: a pose três-quartos do conceito virou uma T-pose simétrica e mais ereta (sem a postura curvada).
    Não há contorno escuro, que vai ser trabalho do shader toon do jogo.
  - Animações: o walk ficou limpo e no lugar. O idle 0 é um balanço cansado que se curva bastante: combina
    com "frágil", mas é exagerado. Trocar custa 3 créditos (ex.: 11 "Idle 1" ou 12 "Idle 2"). O attack é um
    golpe com o braço e o work um golpe de machado agachado; ela não segura ferramenta.
- **O que deu errado:**
  - A Meshy mudou desde o GDD: `model_type: lowpoly` está obsoleto (agora é Smart Topology, `meshy-t2`), e o
    Multi-Image to 3D nem tem Smart Topology. Nele, low-poly é `should_remesh` + `target_polycount`.
  - O conceito é `.jpg`, não `.png`. Ele tinha dois defeitos que a Meshy copiaria: nas duas vistas falta a mão
    esquerda (na frente o braço termina num ícone), e o cristal aparece também nas costas. Corrigidos no recorte,
    com aprovação.
  - Recorte: a primeira máscara pegou o brilho do cristal no papel e perdeu o antebraço claro. O cabelo que
    cobre o cristal das costas saiu errado duas vezes: copiado de cima deixou uma mancha escura, e de baixo
    trouxe a ponta de uma mecha. Pegando do lado ficou natural.
  - Blender: a primeira exportação saiu minúscula e sem cristal. Culpei uma "Icosphere solta da Meshy", mas
    era o formato de osso que o **importador glTF do Blender** cria; resolvido com `disable_bone_shape=True`.
    O `bound_box` ignora a deformação do esqueleto (agora uso os vértices avaliados).
  - Cristal: amostrar só os vértices das faces achou 1 face (as faces são grandes e o cristal é pequeno).
    Agora amostro o interior de cada triângulo no UV.
  - A Meshy liga a textura de cor na emissão do material: o corpo inteiro brilharia à noite. A padronização
    agora desliga a emissão de todos os materiais importados; só o `Cristal` emite.
- **Para o agente do jogo:** a frente do modelo é +Z (`MODEL_FRONT` do Godot); os provisórios atuais olham
  para −Z. A escala está no nó raiz `protagonista` (0,57), não aplicada na malha. O brilho noturno sai de
  `Cristal` → `emission_energy_multiplier`.
- **Correções manuais:** nenhuma.
- **Tempo:** 22:24–22:53 de relógio (plano, documentação da Meshy, recorte, geração e padronização).
- **Pendente:** resto do lote 1 (aldeão, goblin, 6 construções, 3 recursos: cerca de 199 créditos) e a folha
  `assets/previews/lote1.png`, esperando aprovação da protagonista.

---

## 2026-09-25 — Arte: protagonista dentro do jogo (troca visual do Castelão)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** "consegue colocar dentro do game? para eu ver visualmente." Isso abre uma exceção à regra de
  não mexer no código do jogo.
- **O que foi feito:**
  - `src/View/CastellanVisual.cs`: se `assets/modelos/protagonista/protagonista.glb` existe, o Castelão é
    desenhado com o modelo (girado 180°, porque a frente de modelo é +Z e o Castelão olha para −Z) e toca
    `idle` parado, `walk` andando e `work` coletando, com transição de 0,15 s e os três em laço. Sem o modelo,
    continua a cápsula. A simulação não foi tocada.
  - Rodado pelo binário do Godot desta worktree (`--import` e `--write-movie`), sem o MCP/editor do outro
    agente. `dotnet build`: 0 erros, 0 avisos.
- **O que deu errado:**
  - No jogo ela apareceu quase preta. A Meshy não informa metalicidade, e no glTF a ausência vale 1 (metal).
    No Blender o fundo branco refletia e escondia o problema. `normalize.py` agora deixa todos os materiais
    foscos: metálico 0, rugosidade 0,8, reflexo neutro (vinha com fator 2), e continua sem emissão fora do
    `Cristal`.
  - O Godot importava também os GLB brutos: o pipeline agora cria `.gdignore` em `bruto/`.
- **Atenção para o merge:** esta branch mexe em `src/View/CastellanVisual.cs`, que é do agente do jogo.
  Os `.uid` que o Godot gerou em `src/Simulation/` ficaram fora do commit.
- **Correções manuais:** nenhuma.
- **Tempo:** 22:55–23:05 de relógio.

---

## 2026-09-25 — Arte: protagonista não encolhe e não desliza ao andar

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** ao andar, a personagem ficava menor, e o walk não casava com a velocidade (parecia deslizar).
  O humano escolheu manter o walk no ritmo natural e baixar a velocidade da personagem até casar com ele;
  a corrida será outro estado depois.
- **Causas encontradas:**
  - O clipe idle da Meshy (id 0) escala o quadril em 1,176, o corpo inteiro. O walk tem escala 1, então
    ela ficava maior parada e "encolhia" ao andar.
  - O walk anda naturalmente a 0,396 m/s na escala dela (0,8 m), e o jogo movia o Castelão a 6 m/s: a
    animação teria de tocar 15× mais rápido para não deslizar. A corrida grátis do rig (medida: 1,8 m/s)
    ficou para o estado de corrida.
- **O que foi feito:**
  - `normalize.py`: remove as trilhas de escala de todos os ossos em todos os clipes, mede a velocidade da
    passada do walk (mediana da velocidade com que o pé recua, na escala do jogo) e grava
    `assets/modelos/protagonista/protagonista.json` (`passada_walk_m_s: 0.396`).
  - `data/castellan.json`: `speed` de 6.0 para 0.4 célula/s, com o motivo no comentário.
  - `CastellanVisual`: lê a passada e ajusta o ritmo do walk (`SpeedScale`) pela velocidade real no chão,
    suavizado. A 0,4 fica em cerca de 1,0×, e ao frear numa parede os pés continuam casando com o chão.
  - `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 75 aprovados.
- **O que deu errado:**
  - A primeira forma de medir a passada deu valores instáveis (0,32 / 0,40 / 0,52 m/s): contar "pé no
    chão" pela altura falha porque o dedo sobe quando o calcanhar levanta. A trajetória quadro a quadro
    mostrou o padrão (pé recua devagar no apoio, avança rápido no ar); a mediana dos quadros de recuo deu
    0,396, batendo com a leitura feita à mão.
  - Não consegui simular a tecla W para gravar a caminhada no jogo (o macOS bloqueou o AppleEvent por falta
    de permissão de acessibilidade). Verifiquei no jogo só o tamanho no idle; a caminhada fica para o humano
    conferir jogando.
- **Atenção:** 0,4 célula/s é bem devagar (10 células em cerca de 25 s). Isso muda a jogabilidade até existir
  a corrida. `data/castellan.json` é do agente do jogo.
- **Correções manuais:** nenhuma.
- **Tempo:** 23:08–23:25 de relógio.

---

## 2026-09-25 — Câmera cinematográfica para analisar animações

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** uma câmera "cinematic" que, ao entrar, foca exclusivamente no personagem, máquina, inimigo ou
  aldeão, para analisar as animações. (Não havia arquivos de animação novos no repositório; entendi que eram
  as animações procedurais já feitas: golpe, quique, virar, lâmina, fumaça.)
- **O que foi feito (só na cena):**
  - `CameraRig`: modo cinematográfico — perto, ângulo baixo (18°), órbita automática de 14°/s, segue o alvo;
    roda aproxima, botão direito arrastado gira e muda a altura (retoma a órbita após 3 s); desfoque do fundo
    (profundidade de campo); distância, inclinação e altura sempre suavizadas, então entrar e sair não corta;
    ao sair, volta ao ângulo de antes. Sai sozinho se o alvo sumir.
  - `WorldView.FindFocus`: escolhe o alvo sob o cursor (Castelão/aldeão a menos de ~1 célula, senão construção
    ou recurso da célula), com legenda ao vivo (ex.: "Fundição — 2 Ferro → 1 Lingote (3 s) — Esperando 2 Ferro").
  - `CinematicOverlay`: faixas pretas animadas e legenda; a interface some. Tecla C entra/sai, Esc sai.
  - GDD (seção 12) atualizado e reexportado.
  - Verificado no jogo: Castelão (inclusive andando, a câmera acompanha), fundição e aldeão; ao sair, o giro
    voltou a 0 e a interface reapareceu.
- **O que deu errado:**
  - A primeira versão, ao sair, encaixava o giro no múltiplo de 90° mais perto de onde a órbita parou, e o
    mapa ficava virado. Agora devolve o giro de antes.
  - Um teste de foco no aldeão pegou o Castelão: a câmera ainda estava na transição da saída anterior e o pixel
    calculado não caiu no aldeão (sem nada sob o cursor, o padrão é o Castelão). Repetido com a câmera parada,
    funcionou.
- **Correções manuais:** nenhuma.
- **Tempo:** 23:11–23:15 de relógio.

---

## 2026-09-25 — Arte: caminhada da protagonista sem pernas cruzando e com braços mais fechados

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte` (já com a câmera
  cinematográfica da `master`).
- **Pedido:** na caminhada, os braços ficavam muito separados do corpo (robótico) e as pernas passavam uma
  por dentro da outra.
- **Medição (Blender, antes de mexer):**
  - Casual Walk (id 30): os pés cruzam a linha do meio (−0,058 da altura; negativo = cruzou).
  - Caminhada básica que vem grátis com o rig: pés separados (+0,141), mas braços ainda mais abertos
    (abertura lateral média de 28°, máximo de 44°).
  - Os braços abertos vêm do retarget: o clipe foi feito para um corpo mais largo que o dela.
- **O que foi feito (0 créditos):**
  - `tools/assets.json`: `walk_do_rig: true` e `fechar_bracos_graus: 18` na protagonista.
  - `normalize.py`: `use_rig_walk` troca o walk pela caminhada do rig (mesmos 24 ossos, no lugar);
    `close_arms` gira os ombros 18° para baixo, em volta do eixo frente-trás, em todas as chaves do walk.
    O sinal é escolhido pelo lado que abaixa a mão.
  - `pipeline.py`: baixa também a caminhada e a corrida grátis do rig (`bruto/`).
  - Resultado: pés +0,141 (não cruzam); abertura lateral média de 11° (máximo de 26°). Passada nova: 0,81 m/s
    (ciclo de 1,04 s), então `data/castellan.json` → `speed: 0.8`.
  - `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 75 aprovados.
- **O que deu errado:**
  - As chaves da caminhada do rig ficam em tempos fracionados (0,8; 1,8; ...). Na primeira versão eu gravei
    as chaves corrigidas em quadros inteiros, e a curva alternava entre chave corrigida e original (o braço
    tremeria). Agora regravo exatamente nos tempos originais.
  - A primeira métrica do braço (ângulo com a vertical) misturava o balanço para a frente com a abertura
    lateral; troquei pela abertura lateral.
- **Correções manuais:** nenhuma.
- **Tempo:** 23:40–23:58 de relógio.

---

## 2026-09-25 — Arte: animação de corrida da protagonista (clipe `run`)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** o humano aprovou a caminhada ("agora sim ficaram perfeitas") e pediu a animação de correr,
  já disponível para o agente do jogo criar o estado de corrida e o botão.
- **O que foi feito (0 créditos):**
  - A corrida é a grátis que veio com o rig (`bruto/corrida.glb`): no lugar, mesmos 24 ossos,
    ciclo de 0,67 s.
  - `tools/assets.json`: `clipes_do_rig` (walk e run) e `fechar_bracos_graus` por clipe (walk 18°, run 13°;
    na corrida os braços vão levantados para a frente, e fechar demais os enfiaria no peito).
  - `normalize.py`: `use_rig_clip` genérico; a passada de cada clipe vai para `protagonista.json`.
  - Medições: pés sem cruzar (+0,112 da altura); abertura lateral do braço média de 18° (era 24° na
    corrida bruta); passada de 2,525 m/s. A caminhada não mudou (11°, +0,141, 0,81 m/s).
  - A métrica do braço mudou para "quanto o braço sai do plano do corpo" (asin de x). A anterior quebrava
    com o braço levantado para a frente e dava 174°.
- **Para o agente do jogo:**
  - `assets/modelos/protagonista/protagonista.glb` tem os clipes `idle`, `walk`, `run`, `attack` e `work`.
    O `CastellanVisual` coloca em laço só idle, walk e work; o `run` precisa entrar nessa lista.
  - `protagonista.json`: `passada_walk_m_s` 0,81 e `passada_run_m_s` 2,525. Para não deslizar, o run deve
    tocar com `SpeedScale` = velocidade no chão ÷ 2,525, como o walk já faz com 0,81. A velocidade de corrida
    que casa com a animação a 1,0× é cerca de 2,5 células/s.
- **Correções manuais:** nenhuma.
- **Tempo:** 00:00–00:10 de relógio.

---

## 2026-09-26 — Arte: idle da protagonista refeito (ereta, só respirando)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** o idle da Meshy estava exagerado. Fazer um mais simples, "algo como respirar", mais ereta e
  olhando para a frente.
- **Decisão:** criar o idle no Blender em vez de testar outros da biblioteca da Meshy (3 créditos cada e
  sujeitos a defeito de retarget, como a escala de 1,176 do idle 0). Custo: 0 créditos.
- **O que foi feito:**
  - `normalize.py` → `breathing_idle`, com os números em `tools/assets.json` (`idle_respirando`):
    - pernas endireitadas: a malha da Meshy fica inclinada cerca de 12° para a frente (tornozelos atrás
      do quadril). Coxa e canela vão para a vertical, os pés voltam a ficar planos e o quadril é ajustado
      para os pés continuarem no chão;
    - braços baixados da T-pose (73°) com o cotovelo um pouco dobrado (12°): abertura lateral de 8°;
    - cabeça 8° mais levantada, mantendo a orientação (não balança nem olha para os lados);
    - respiração num ciclo de 3,5 s: a coluna se abre 4° para trás e os ombros sobem 5°.
  - Chave em todos os ossos: senão o Godot manteria nas pernas a pose do clipe anterior.
  - Medido: pés parados no chão durante todo o clipe; o ombro sobe 3,7 mm e a cabeça recua 8,5 mm ao
    inspirar. Visto no Blender (lado, ar solto e ar cheio) e numa gravação do jogo.
- **O que deu errado:** a primeira versão, com 1,5°, era sutil demais (o ombro subia 1,1 mm, invisível com
  a câmera de cima), os braços ficaram colados (3°) e a vista de lado mostrou o corpo inclinado, que vem
  da malha. As três coisas foram corrigidas com os números acima.
- **Correções manuais:** nenhuma.
- **Tempo:** 00:15–00:35 de relógio.

---

## 2026-09-25 — Estado de corrida (Shift)

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** a animação de corrida (run) já existe na protagonista e o personagem anda devagar demais;
  criar o estado de corrida com um botão.
- **Contexto:** na integração da arte (outra sessão, branch `arte` já na `master`), a velocidade do Castelão
  caiu de 6 para 0,8 célula/s para casar com a passada do walk; a corrida ficou anotada como "outro estado".
- **O que foi feito:**
  - `data/castellan.json`: `runSpeed` 2,5 células/s (passada natural do clipe run, 2,525 m/s do
    `protagonista.json`); o carregador exige `runSpeed` ≥ `speed`.
  - Simulação: `MoveCommand` leva "correndo"; `Castellan.IsRunning` (parado com Shift não conta).
    78 testes (3 novos).
  - Entrada: ação `run` no Shift; o comando só é reenviado quando a direção ou a corrida mudam.
  - Visual: `CastellanVisual` toca `run` correndo, com `speed_scale` pela velocidade real sobre a passada do run
    (mesma lógica que já existia para o walk).
  - GDD (seção 20, "Movimento") atualizado e reexportado; o export trouxe também a seção "Piso e chão" que a
    sessão de arte escreveu no documento vivo.
  - Verificado no jogo: Shift + A → clipe `run` (speed_scale 0,99) a 2,5 células/s; solta Shift → `walk` (1,01);
    solta A → `idle`. Na câmera cinematográfica, a pose de corrida aparece certinha.
- **O que deu errado:** na primeira execução o Castelão apareceu como a cápsula antiga: o editor aberto aqui não
  tinha importado o `protagonista.glb` novo (faltava o arquivo em `.godot/imported`). Não era erro de código;
  resolvido com um scan e reimportação pelo MCP.
- **Correções manuais:** nenhuma.
- **Tempo:** 23:29–23:31 de relógio.

---

## 2026-09-26 — Arte: idle da protagonista menos sutil, com detalhes

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** "um pouco menos sutil, coloque alguns detalhes."
- **O que foi feito (0 créditos):** em `idle_respirando` (`tools/assets.json`) e no `breathing_idle`:
  - respiração mais forte: peito de 4° para 6°, ombros de 5° para 7° (o ombro sobe 6,8 mm, antes 3,7 mm);
  - clipe com 2 respirações (7 s), e nele o peso do corpo passa de um lado para o outro uma vez: o tronco
    balança 1,5° (só o tronco; mexer no quadril levaria os pés junto);
  - a cabeça inclina 3° junto com o balanço e acena 1,5° ao soltar o ar;
  - ao inspirar, os braços vão 3° para a frente e os pulsos relaxam 5°.
  - Medido: pés parados no chão durante todo o clipe; o último quadro é igual ao primeiro (laço sem salto).
- **O que deu errado:** aspas duplas dentro do comentário do `assets.json` quebraram o JSON; troquei o texto.
- **Correções manuais:** nenhuma.
- **Tempo:** 00:45–00:55 de relógio.

---

## 2026-09-26 — Arte: sai a caminhada; corrida moderada (jog) e corrida muito rápida (sprint)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** a caminhada não tem motivo no jogo (é lenta). Ficam dois estados: correndo (moderado) e
  correndo muito rápido (gasta estamina; o agente do jogo vai fazer a estamina). A corrida atual vira a
  muito rápida; criar uma corrida moderada.
- **Escolha da corrida moderada:** o catálogo não tem "jog". Pelas prévias públicas (gratuitas), Run 2 (14)
  e Run 3 (15) são mais eretas, com braços baixos e passadas curtas. Gerei as duas sobre o rig existente
  (**6 créditos**) e medi:
  - Run 2: pés cruzam (−0,020 da altura), braço 23°, ciclo de 0,71 s;
  - **Run 3 (escolhida):** pés na linha, sem cruzar (−0,003), braço 29° → 19° depois de fechar 18°, ciclo de
    0,79 s.
- **O que foi feito:**
  - Pipeline: etapa `animacoes_extra` (animações pedidas depois sobre o mesmo rig, sem refazer as primeiras).
    O mapeamento dos clipes passou a usar o `key` da biblioteca (`Run_02`), que é o nome da ação no GLB; o
    `name` ("Run 2") não batia.
  - `normalize.py`: `import_extra_clips`, `descartar_clipes` (sai o `walk`) e passadas medidas para `jog` e
    `sprint`.
  - `protagonista.glb`: `idle`, `jog`, `sprint`, `attack`, `work`. `protagonista.json`:
    `passada_jog_m_s` 1,593 e `passada_sprint_m_s` 2,421. (A passada do sprint mediu 2,421, contra 2,525
    antes; vale a medição atual.)
  - Para o jogo continuar funcionando, a troca mínima: `CastellanVisual` usa `jog` no movimento normal e
    `sprint` com Shift; `data/castellan.json`: `speed` 1.6 e `runSpeed` 2.4 (as passadas).
  - `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 78 aprovados.
- **Créditos:** 6 (total do lote: 53; saldo: 3.047).
- **Para o agente do jogo:** a estamina e o nome dos estados ficam com ele. Os clipes são `jog` e `sprint`, e
  as passadas estão em `protagonista.json`.
- **Correções manuais:** nenhuma.
- **Tempo:** 01:00–01:25 de relógio.

---

## 2026-09-26 — Arte: inclinação do tronco nas duas corridas (análise de biomecânica)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** "não é ao contrário na vida real? Quando fica inclinado vai mais rápido? Analise bem."
- **Medição (Blender, antes):**

  | | jog (Run 3) | sprint | na vida real, a mais rápida tem |
  |---|---|---|---|
  | tronco inclinado | **28°** | 11° | um pouco mais (ver abaixo) |
  | cadência | 152 passos/min | 180 | mais ✔ |
  | passo | 0,63 m (1,8× a perna) | 0,81 m (2,3×) | mais longo ✔ |
  | calcanhar sobe | 0,71× a perna | 0,96× | mais alto ✔ |
  | amplitude dos braços | 110° | 122° | maior ✔ |
  | coxa à frente | 53° | 48° | maior ✘ (levemente invertido) |

- **Conclusão:** o humano tinha razão sobre a inclinação. Na corrida real, a grande inclinação (uns 45°)
  aparece só na arrancada (aceleração); em velocidade constante o corpo fica quase ereto, entre 5° e 15°,
  inclinado a partir do tornozelo. O que marca a velocidade é cadência, comprimento do passo, joelho e
  calcanhar altos e braços vigorosos. A Run 3 mantinha 28° constantes, uma postura de arrancada, e por
  isso parecia a mais rápida. Nos outros sinais, o sprint já era o mais rápido.
- **Decisão do humano:** jog com 8° e sprint com 16° (um pouco a mais para ler como mais rápida com a câmera
  de cima).
- **O que foi feito (0 créditos):** `inclinacao_tronco_graus` em `tools/assets.json` e `set_trunk_lean` no
  `normalize.py`. A correção desloca a inclinação média e preserva o balanço de cada passada; a rotação é
  dividida pelos três ossos da coluna e repetida até ficar a menos de 0,5° do alvo (o trecho quadril →
  coluna não gira). Pescoço e ombros mantêm a orientação no mundo. Resultado: jog com 9° (entre 7° e 10°),
  sprint com 16° (entre 13° e 19°); passadas, pés e braços iguais.
- **O que deu errado:** a primeira passada só chegou a 20° e 13° (o trecho do quadril entra na medida); virou
  um laço de correção. Ao endireitar o jog, os braços, que são filhos da coluna, subiram junto e as mãos
  chegavam ao rosto; resolvido mantendo a orientação dos ombros.
- **Correções manuais:** nenhuma.
- **Tempo:** 01:30–01:55 de relógio.

---

## 2026-09-26 — A protagonista só corre: saem o andar, a corrida moderada e o botão de correr

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte` (com permissão do humano para
  mexer no código do jogo).
- **Pedido:** o humano achou as duas corridas muito iguais. Tentei um trote novo (abaixo), e ele decidiu:
  "vamos esquecer o estado de andar, agora o personagem só corre, apague o estado de andar e retire o
  botão de correr".
- **Tentativa que não deu certo antes da decisão (13 créditos):** um trote gerado pela Text to Motion
  (`prime`, 6 s), aplicado no rig e cortado num laço no lugar no Blender (1,42 s; diferença de pose de
  menos de 1 cm por osso). Saiu um passo arrastado, não uma corrida: joelho a 18°, calcanhar a 0,21× a perna,
  passo de 0,23 m, braços parados na frente da barriga. Descartado. O pipeline ganhou `movimentos_texto`
  (Text to Motion + aplicação no rig) e o `normalize.py` o `import_motion_clip` (acha o ciclo, fecha o laço
  e tira o avanço do quadril), que ficam para outros usos.
- **O que foi feito:**
  - Arte: o GLB tem `idle`, `run`, `attack` e `work`. O `run` é a corrida aprovada (clipe do rig, braços
    fechados 13°, tronco 16°). `protagonista.json`: `passada_run_m_s` 2,421. `tools/assets.json` sem os
    clipes de trote.
  - Jogo (desfaz a corrida com Shift do commit `fb9b871`): sem a ação `run` no `project.godot`, sem
    `IsRunning`, `RunCellsPerSecond` e `runSpeed`, `MoveCommand` só com a direção. `CastellanVisual` toca
    `run` sempre que ela se move. `data/castellan.json`: `speed` 2.4 (a passada da corrida). GDD (seção 20)
    atualizado.
  - Testes: saíram os 3 da corrida com Shift e entrou `SpeedMustBePositive`. `dotnet build`: 0 erros,
    0 avisos. `dotnet test`: 76 aprovados.
- **Créditos:** 13 nesta etapa (total do lote: 66; saldo: 3.034).
- **Pendência:** o GDD foi editado aqui, mas não reexportado (o agente do jogo costuma reexportar).
- **Correções manuais:** nenhuma.
- **Tempo:** 02:00–02:40 de relógio.

---

## 2026-09-26 — Arte: texturas do chão e placas dos pisos construídos

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** texturas do chão natural (grama escura, terra, pedra, lama, areia de rio) e dos pisos
  construídos (tábuas, calçamento, rúnico) com a Text to Image da Meshy; repetíveis sem emenda (Python);
  512 px; placas de 1×1 m com 5 cm e bordas chanfradas no Blender; máscara de emissão das runas;
  prévias 4×4 com reprovação automática (até 2 tentativas por textura); limite de 150 créditos.
- **Prompts:** modelo do pedido ("seamless tileable top-down hand-painted texture, [TIPO], stylized dark
  whimsical medieval, flat lighting, no shadows, no perspective, no objects, muted earthy palette"), com
  [TIPO] e as cores da paleta da seção 17 em `tools/texturas.json` (na grama, "subtle swirls and small
  spiral patterns"; no rúnico, runas #9BC53D). Modelo de IA: `nano-banana-2` (6 créditos a imagem).
- **Créditos:** estimativa de 48 (máximo de 96); **gastei 96** (16 imagens). Saldo: 3.034 → 2.938.
- **O que foi feito:**
  - `tools/meshy_pipeline/textures.py`: gera, baixa (brutas em `assets/texturas/chao/bruto/`, fora do git),
    processa, mede, reprova, salva, faz a prévia e a máscara; `--reprocess` refaz tudo sem gerar.
  - Repetição sem emenda: o método "deslocar meia imagem e mesclar a cruz" deixa emendas retas onde a
    cruz encosta na borda (as duas versões têm emenda ali; o teste sintético mostrou). Troquei pela mistura
    de 4 cópias (original e deslocadas na horizontal, na vertical e nas duas), cada uma com peso zero
    exatamente nas suas linhas de emenda: sem emenda em lugar nenhum, com a original no centro. A cor
    mistura suave; o detalhe fino vem da cópia dominante, com fronteira entortada por ruído repetível.
    Antes, um nivelamento tira 75% das manchas maiores que 1/4 da imagem (senão a 4×4 forma listras).
    Se a imagem da IA já vem repetível, ela vai direto (misturar desalinhava as tábuas).
  - Checagem automática: percentil do degrau na junta entre as linhas da própria imagem (reprova
    acima de 95), contraste de detalhe na faixa misturada (reprova abaixo de 0,8) e **moldura** (borda
    lisa ou com brilho muito diferente do interior).
  - Escolhas (as duas tentativas vistas em 2×2): grama #2, terra #1, pedra #1, lama #2, areia #2, tábuas #2,
    calçamento #1, rúnico #2. O rúnico fica no modo "placa": é uma laje com borda própria e um círculo de
    runas, que é o certo para uma placa de 1×1 com chanfro; misturar picotava as runas.
  - Máscara de emissão: pixels perto do verde das runas e claros, normalizada (runas em 100%, 1,9% da
    área). No GLB, a emissão é a cor da textura × a máscara (as runas brilham na própria cor), força 3.
  - `tools/blender/floor_plates.py`: placa de 1 × 1 × 0,05 m, chanfro de 1,2 cm, base aberta (fica no
    chão), pivô no centro da base, UV de cima (o topo usa a textura inteira e as laterais a borda), fosca.
    30 triângulos. `--preview` renderiza 3×3 placas na câmera do jogo (e de noite no rúnico).
  - Saída: `assets/texturas/chao/*.png` (8 texturas + `piso_runico_emissao.png`),
    `assets/modelos/pisos/*.glb` (3), `assets/previews/piso/*_4x4.jpg` (8) e `*_placas_*.png` (4).
- **O que deu errado:**
  - **A primeira métrica de emenda reprovou tudo e custou 48 créditos à toa.** Ela comparava o pior degrau
    entre colunas com o degrau médio; em textura real, bordas de tábuas, rachaduras e juntas fazem linhas
    fortes de verdade. Eu a calibrei só numa imagem sintética de ruído antes de ligar a reprovação
    automática com nova geração. Lição: calibrar a reprovação em imagens reais (ou rodar a primeira
    tentativa sem regerar) antes de deixar o script gastar sozinho.
  - 5 das 16 imagens vieram com moldura (placa com borda): a primeira checagem não pegava, porque a
    moldura "combina consigo mesma" na junta. Virou a checagem de moldura, calibrada nas 16.
  - O Blender 5.1 avisa que `use_nodes` sai no 6.0: removido deste script e do `render_views.py`.
- **Atenção:** em 4×4, terra e pedra mostram a repetição do padrão (manchas e rachaduras); no jogo o
  shader mistura terrenos com ruído, o que disfarça. Se incomodar, dá para gerar em 2k e usar 1 textura
  para 2×2 células, ou gerar variações.
- **Correções manuais:** nenhuma.
- **Tempo:** 02:50–03:50 de relógio.

---

## 2026-09-26 — Chão com texturas no mundo (terrenos por célula, bordas orgânicas)

- **Agente / modelo:** Claude Code + Opus 5.5, na branch `arte`, levado para a `master` a pedido.
- **Pedido:** "implementa no master e no mundo para que eu possa ver, faça um design bonito".
- **O que foi feito:**
  - Simulação (o terreno é estado do mundo; o GDD prevê pisos mudando a velocidade):
    - `data/terrain.json`: 5 terrenos (grama escura, terra, pedra, lama, areia de rio) com a textura de cada
      um; a ordem é o índice guardado na célula.
    - `TerrainType`; `GameData.Terrains` e `Terrain(kind)` (o parâmetro é opcional: sem ele, o mapa é todo
      grama, e os testes antigos não mudam); `WorldGrid.TerrainAt`.
    - `MapLoader`: seção `terrain` do mapa, com um padrão e manchas por cima (círculo com `radius` ou
      retângulo com `width` e `height`; a última vence). `mapa_teste.json`: grama; margem de areia a oeste com
      lama perto; pátio de terra batida na base; chão de pedra em volta das rochas e do ferro.
    - 4 testes novos (sem terreno, círculo e retângulo com sobreposição, padrão, tipo desconhecido) e o
      teste dos dados reais conferindo o pátio. `dotnet test`: 80 aprovados.
  - Cena: `TerrainGround.gdshader` (substitui o `GridGround`):
    - as 5 texturas numa pilha (`Texture2DArray`) e um mapa de 1 pixel por célula com o índice;
    - fronteira orgânica: o terreno é procurado num ponto entortado por ruído repetível, com mistura curta
      entre as 4 células vizinhas;
    - contra a repetição: duas amostras de cada textura em escalas diferentes, alternadas por regiões de
      ruído, e manchas grandes de luz. Uma repetição da textura cobre 3 m;
    - grade só no modo construção (com uma construção escolhida), como diz o GDD.
  - `dotnet build`: 0 erros, 0 avisos. Visto numa gravação do jogo.
- **O que deu errado:** na primeira versão (textura a cada 2 m, amostra única), as manchas claras da terra
  formavam uma grade visível; resolvido com a segunda amostra e a escala de 3 m.
- **Fora desta tarefa:** os pisos construídos (tábuas, calçamento, rúnico) ainda não são construíveis; eles
  pedem uma camada de piso na simulação (convivendo com construções e esteiras) e o efeito na velocidade.
- **Correções manuais:** nenhuma.
- **Tempo:** 04:00–04:40 de relógio.

---

## 2026-09-26 — Arte: chão refeito na paleta nova (v2: escuro, dessaturado, calmo)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** as texturas do chão fugiram do tema (saturadas, claras, com detalhe demais). Refazer com a
  paleta nova do chão (terra escura #4A3B3A, terra arroxeada #3F3342, musgo acinzentado #4E5544, grama morta
  #5A5847, pedra fria #66636B, lama #2E2931, líquen roxo #6B4F7C): tons escuros e frios, pinceladas largas,
  pouco detalhe e contraste, espirais quase invisíveis, e o complemento de prompt "gothic whimsical dark
  forest floor, twilight, muted desaturated colors, low contrast, broad painterly strokes, no highlights".
  Prévias 4×4 lado a lado com as antigas. Limite de 100 créditos.
- **O que foi feito:**
  - A paleta não estava na minha cópia do GDD: acrescentada em "Piso e chão" (seção 17) com as regras.
  - `tools/texturas.json` virou a versão `v2`: estilo novo e cada terreno com as cores novas (grama em musgo
    acinzentado e grama morta; terra escura para arroxeada; pedra fria com líquen roxo; lama; areia de rio
    cinza-oliva). Os pisos construídos ficam presos à `v1` (não foram pedidos).
  - `textures.py`: estado, brutos e orçamento separados por versão (a `v1` continua recuperável).
  - Resultado: 4 aprovadas de primeira; a areia de rio na segunda (a primeira tinha emenda). A grama passou
    na checagem, mas no jogo as folhas pintadas e as espirais ainda chamavam atenção: usei a segunda tentativa
    com o prompt mais explícito ("almost uniform, soft broad strokes, no individual leaves, only a few very
    faint swirls"). Ficou a segunda.
  - Medido (textura antes → depois): saturação de 0,24–0,70 para 0,08–0,20; contraste de 0,035–0,125 para
    0,014–0,035; detalhe fino de 2,5 a 5 vezes menor; a areia foi de brilho 0,68 para 0,29. A grama ficou um
    pouco mais clara (0,20 → 0,24), porque o musgo acinzentado da paleta é mais claro que o verde escuro da v1.
  - Comparação: `assets/previews/piso/comparacao_chao_v1_v2.jpg` (antes à esquerda, depois à direita, com os
    números). As prévias 4×4 de cada textura foram atualizadas.
- **Créditos:** 42 (7 imagens). Saldo: 2.938 → 2.896.
- **Atenção:** no jogo o chão parece mais claro que a textura, por causa do sol da cena. Se precisar ficar
  mais escuro, é ajuste de luz ou de tom no shader, sem gerar imagem. Os pisos construídos (tábuas,
  calçamento, rúnico) ainda estão na paleta antiga.
- **Correções manuais:** nenhuma.
- **Tempo:** 04:50–05:20 de relógio.

---

## 2026-09-26 — Chão: grama ainda viva no jogo; ajuste de cor só no chão

- **Agente / modelo:** Claude Code + Opus 5.5, na branch `arte`.
- **Pedido:** "ainda tô achando essa grama muito verde, muito viva."
- **Medição (antes de mexer):** a textura estava na paleta (média #555648, saturação 0,16), mas **na tela**
  a grama saía #6A6144, com saturação 0,36 (o dobro) e matiz puxado para o amarelo (63° → 47°); a terra ia de
  0,20 para 0,39. A causa é a luz da cena (`scenes/Main.tscn`): ambiente cor de trigo (#C9B38A), sol
  amarelado e tonemap Filmic, que esquentam e saturam tudo. Isso combina com o "dia terroso e acolhedor" da
  seção 17, mas briga com a paleta fria do chão.
- **O que foi feito (0 créditos):** ajuste de cor só no chão, em `TerrainGround.gdshader` (saturação 0,65,
  tom frio 0,90 / 0,96 / 1,02, brilho 0,85), calibrado medindo a tela. A primeira tentativa (0,45 e tom mais
  azul) deixou a grama cinza-marrom (saturação 0,09, matiz 18°), longe do musgo. Resultado: grama na tela
  #555444 (matiz 57°, saturação 0,20, brilho 0,34), praticamente a "grama morta" da paleta (#5A5847); terra
  #322A26; areia #49483B. A luz dos personagens e construções não mudou.
- **Decisão em aberto para o humano:** esfriar a luz da cena inteira (crepúsculo) mudaria o visual de tudo,
  não só do chão; por isso ficou só no chão.
- **Correções manuais:** nenhuma.
- **Tempo:** 05:25–05:40 de relógio.

---

## 2026-09-26 — Clima de crepúsculo eterno

- **Agente / modelo:** Claude Code 2.1.265 + Opus 5.5, com o MCP godot-ai.
- **Pedido:** o dia agora é um crepúsculo eterno, frio, acinzentado e levemente roxo (GDD, seção 17): sol baixo e
  fraco, luz fria, sombras suaves; céu e ambiente roxo-acinzentados; névoa roxa escura mais densa longe;
  saturação ~0,7 e contraste maior; vinheta; se a protagonista sumir, luz azul do cristal do peito. Print antes e depois.
- **O que foi feito:**
  - `scenes/Main.tscn`: céu procedural roxo-acinzentado; luz ambiente roxo-acinzentada (energia 1,0); sol a 18°,
    cor (0,72; 0,78; 0,90), energia 0,85, disco angular 4° e blur 1,6 para sombras suaves; névoa por profundidade roxo
    escura (começa em 22, termina em 90, curva 1,6); ajuste de cor (saturação 0,7, contraste 1,15); bloom só acima de
    HDR 1,0; vinheta num shader de tela (`src/View/Vignette.gdshader`) por baixo da interface.
  - A protagonista sumia no chão escuro na visão normal: `CastellanVisual` triplica a emissão do material "Cristal"
    e prende uma luz azul suave (energia 0,85, alcance 2,3, sem sombra) no osso `Spine` (acompanha a corrida).
  - Prints em `docs/prints/clima_{antes,depois}_{visao,perto}.png`. GDD (seção 17) atualizado e reexportado.
- **O que deu errado:**
  - A cena não carregava: as texturas de chão e pisos da sessão de arte nunca tinham sido importadas por este editor
    (faltavam em `.godot/imported`); scan e reimportação pelo MCP não resolveram. Resolvido com
    `Godot --headless --import`. A importação trocou a compressão de 4 texturas dos pisos (detecção de 3D); desfiz
    nos `.import` para manter as configurações da arte.
  - A primeira versão ficou escura demais (grama quase preta) e a névoa começava antes da câmera (a 12, com a
    câmera a 16): subi ambiente e sol e empurrei a névoa para 22.
  - A primeira luz do cristal era forte demais de perto (chão quase branco); baixei de 1,3 para 0,85.
  - Screenshots de 1200 px passaram a falhar no transporte do MCP; os de 640 px funcionam.
- **Correções manuais:** nenhuma.
- **Tempo:** 00:41–00:44 de relógio (fora a importação).
- **Correção no mesmo dia:** o export do GDD trouxe de volta a linha "Movimento" com o Shift, porque a sessão de
  arte tinha mudado essa linha só no `docs/GDD.md` local (não no documento vivo). Levei a decisão dela ("a
  protagonista só corre") para o documento vivo e reexportei. Lição: antes de exportar, comparar o GDD local com o
  último commit para não apagar mudanças feitas só no arquivo.

---

## 2026-09-26 — Junção da `arte` com a `master` (chão v2 + crepúsculo eterno)

- **Agente / modelo:** Claude Code + Opus 5.5, na branch `arte`.
- **Pedido:** "dê merge na branch para eu ver a junção de tudo."
- **O que aconteceu:** a `master` tinha o "clima de crepúsculo eterno" do agente do jogo (luz fria, céu e
  névoa roxos, saturação 0,7 na cena). Juntei a `master` na `arte`; o único conflito foi no diário (entradas
  dos dois lados, mantidas). Com a luz nova, o ajuste de cor que eu tinha posto no chão (feito para
  compensar a luz quente) passou a esfriar e escurecer de novo: grama #1F1F2A, terra #09070F. Neutralizei o
  ajuste (saturação, tom e brilho em 1); o chão agora segue a paleta sob a luz fria: grama #29262C, terra
  #110A11, areia #211E28. Os três controles ficaram no shader, neutros.
- **Atenção:** sob o crepúsculo, a terra do pátio fica quase preta (brilho 0,07). Dá para clarear pelo
  `ground_brightness` do shader ou pela textura, se o humano quiser.
- `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 80 aprovados.
- **Tempo:** 05:45–06:00 de relógio.

---

## 2026-09-26 — Luz do cristal não ilumina mais o cabelo da protagonista

- **Agente / modelo:** Claude Code + Opus 5.5, na branch `arte` (código do agente do jogo, a pedido do humano).
- **Pedido:** o humano gostou do efeito de luz do crepúsculo, mas a luz estava "refletindo muito no
  personagem, no cabelo".
- **Causa:** a luz azul do cristal (`OmniLight3D` presa ao osso do peito, do commit do crepúsculo) fica a
  poucos centímetros do cabelo, que passa na frente do peito: iluminava e dava brilho especular forte no
  próprio cabelo e corpo.
- **O que foi feito:** a malha da protagonista vai para uma camada de render só dela (camada 20), e a luz do
  cristal ignora essa camada (`LightCullMask`); o reflexo especular dessa luz caiu para 0,1. Ela continua
  clareando o chão e o que está em volta; sol, ambiente e câmera continuam vendo a protagonista normalmente.
- **Medido na gravação do jogo (recorte centrado nela):** pixels muito claros no corpo de 3,0% para 1,6% (o
  que sobra é o cristal), tom azul no corpo de 0,113 para 0,089; o brilho azul no chão em volta continua.
- `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 80 aprovados.
- **Correções manuais:** nenhuma.
- **Tempo:** 06:05–06:20 de relógio.

---

## 2026-09-26 — Grama roxa (mais clara que a terra)

- **Agente / modelo:** Claude Code + Opus 5.5, na branch `arte`.
- **Pedido:** "esquece essa grama verde, deixa ela em tom de roxo mais claro que aquele roxo que o personagem
  principal tá pisando de começo" (a terra arroxeada do pátio).
- **O que foi feito (0 créditos):** em vez de gerar outra imagem, `textures.py` ganhou `recolorir`: repinta a
  textura com um degradê entre duas cores, e o brilho de cada pixel escolhe a cor (as pinceladas e o
  contraste baixo continuam). Grama: de terra arroxeada #3F3342 (escuro) a um roxo acinzentado #5E5268
  (claro). A primeira tentativa usou o líquen roxo #6B4F7C no claro e saiu roxo vivo demais na tela
  (saturação 0,50, pinceladas chamando atenção).
- **Medido na tela (câmera normal):** grama #251C33, brilho 0,20; terra do pátio #120B12, brilho 0,07 (a
  grama fica bem mais clara que a terra, como pedido). A névoa e a correção de cor da cena puxam tudo
  para o roxo; na tela a saturação da grama fica em 0,44.
- **Observação:** numa gravação o jogo apareceu na câmera cinematográfica sem ninguém apertar C; na seguinte,
  não. Não investiguei (é do agente do jogo); fica o registro.
- **Correções manuais:** nenhuma.
- **Tempo:** 06:25–06:40 de relógio.

---

## 2026-09-26 — Grama low-poly com vento

- **Agente / modelo:** Claude Code + Opus 5.5, na `master`.
- **Pedido:** tufos low-poly por código espalhados com MultiMesh, cores da paleta (grama morta, musgo
  acinzentado, alguns em líquen roxo, pontas mais claras), densidade por terreno, vento por shader com
  variação, grama some sob construções, baixa o bastante para não esconder a protagonista nem itens; conferir
  desempenho com o mapa cheio e mostrar print.
- **O que foi feito:**
  - `grassDensity` por terreno em `data/terrain.json` (grama 1; terra 0,15; pedra, lama e areia 0), lido e
    validado (0 a 1) em `GameData`.
  - `src/View/GrassField.cs`: um tufo de 4 folhas curvas (12 triângulos) gerado por código; um
    `MultiMeshInstance3D` por pedaço de 8×8 células, sem sombra. Até 9 tufos por célula, sorteio com semente
    por célula (o tufo volta igual), densidade interpolada entre células vizinhas para a borda não ficar
    quadrada. Cores 46% grama morta, 46% musgo, 8% líquen roxo, ±10% de brilho.
  - `src/View/Grass.gdshader`: balanço de rajada + tremor, fase pela posição e por um valor sorteado por tufo;
    a ponta mexe mais que a base. Pontas 1,6× mais claras.
  - Construção, remoção e recurso esgotado marcam o pedaço como sujo e ele é refeito no quadro seguinte.
  - Contagem de tufos no rótulo de depuração. `docs/.gdignore` para o Godot não importar os prints.
- **Desempenho (3024×1890):** sem grama 63–67 FPS; mapa de teste com 6.415 tufos 62–66 FPS; mapa 96×96 todo
  de grama (82.944 tufos, temporário, apagado) 59–61 FPS estáveis. A queda antiga de ~120 FPS vem do chão v2,
  névoa e brilho, não da grama.
- **Prints:** `docs/prints/grama_visao.png`, `docs/prints/grama_perto.png`.
- **Problemas:** cores lavadas (cor por instância precisa de `SrgbToLinear`); tufos pareciam estrelas vistos de
  cima (folhas mais em pé e finas); grama escura demais (clareei o shader); alta demais perto da protagonista
  (altura baixada para 0,05–0,1).
- **Fora do escopo por enquanto:** trilhas, pisos construídos e terreno de musgo ainda não existem; cada um só
  precisa do seu `grassDensity` no JSON.
- **GDD:** nota da grama na seção 17. A "Paleta do chão" da sessão de arte só existia no arquivo local; levei
  para o documento vivo também.
- `dotnet build`: 0 erros. `dotnet test`: 80 aprovados.

---

## 2026-09-26 — Junção na `master`: tufos de grama na cor da grama roxa

- **Agente / modelo:** Claude Code + Opus 5.5, na branch `arte`.
- **Pedido:** "junte todas as mudanças no principal".
- **O que foi feito:** a `master` tinha os tufos de grama 3D com vento do agente do jogo (`GrassField`), com
  cores da paleta antiga da grama (46% grama morta, 46% musgo acinzentado, 8% líquen roxo), que trariam o
  verde-oliva de volta sobre o chão roxo. Juntei a `master` na `arte` (conflito só no diário, mantido; o
  `Vignette.gdshader.uid` gerado aqui deu lugar ao da `master`) e alinhei os tufos à grama roxa: 50% roxo
  acinzentado (#5E5268), 35% o meio do degradê da textura, 15% líquen roxo. `Palette` ganhou `PurpleEarth` e
  `GrassPurple`. Depois, `master` avançada até a `arte`.
- **Medido na tela:** grama #251D34, terra #120B12. `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 80.
- **Tempo:** 06:45–07:00 de relógio.

---

## 2026-09-27 — Aldeão, parte 1: atlas de expressões

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** recortar o rosto das 9 cabeças do conceito (sem o cabelo, borda em degradê transparente) e
  montar um atlas 3×3 em `assets/texturas/aldeao/expressoes.png`, na ordem 1 distraído, 2 esforço, 3 feliz,
  4 sonolento, 5 dormindo, 6 espantado, 7 preocupado, 8 chorando, 9 bravo. A subseção "Aldeão:
  implementação v1" não está no GDD (nem na cópia da `master`); segui o pedido.
- **Atenção: os nomes dos conceitos vieram trocados.** `aldeao_cabelos.png` tem as 9 expressões e
  `aldeao_expressoes.png` tem as variações de cabelo em T-pose. Usei cada um pelo conteúdo.
- **Qual cabeça virou qual célula** (posição na folha: linha, coluna):

  | Célula | Expressão | Cabeça | Por quê |
  |---|---|---|---|
  | 1 | distraído | 2,2 | olhar parado para a frente, boca em "o" pequeno |
  | 2 | esforço | 3,2 | sobrancelhas tensas, dentes cerrados, ombros erguidos |
  | 3 | feliz | 1,2 | sorriso aberto |
  | 4 | sonolento | 2,1 | pálpebras caídas |
  | 5 | dormindo | 3,3 | olhos fechados, boca aberta |
  | 6 | espantado | 3,1 | olhos arregalados, boca em "O" grande |
  | 7 | preocupado | 2,3 | sobrancelhas erguidas, olhar desviado para cima |
  | 8 | chorando | 1,1 | lágrimas |
  | 9 | bravo | 1,3 | sobrancelhas franzidas |

- **O que foi feito (0 créditos):** `tools/meshy_pipeline/villager_faces.py` recorta um quadrado de 220 px
  centrado entre os olhos e a boca de cada cabeça (as sobrancelhas entram, porque fazem parte da expressão),
  aplica uma máscara oval com degradê até transparente e monta o atlas: 768 × 768 px, células de 256 px,
  fundo transparente. Prévia numerada sobre a cor da pele em `assets/previews/aldeao_expressoes.png`.
- **Limites:** alguns fios da franja passam sobre a testa e entram no recorte (a franja cobre as
  sobrancelhas no conceito); no "dormindo" a borda de baixo pega uma ponta do cabelo, quase toda apagada
  pelo degradê.
- **Correções manuais:** nenhuma.

---

## 2026-09-26 — Grama mais densa e miúda

- **Agente / modelo:** Claude Code + Opus 5.5, na `master`.
- **Pedido:** "estou achando muita pouca grama, queria uma grama densa e pequena."
- **O que foi feito:** até 36 tufos por célula (eram 9); tufos menores: altura 0,035–0,07 (era 0,05–0,1) e
  largura 0,4–0,65 (era 0,55–0,85). Cores roxas da sessão de arte mantidas.
- **Desempenho:** mapa de teste com 25.681 tufos (eram ~6.400) a 145 FPS no rótulo de depuração.
- **Print:** `docs/prints/grama_densa.png`. O print de perto não saiu: a janela do jogo estava em segundo plano
  e o MCP só devolvia o último quadro.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-26 — Grama no estilo Breath of the Wild

- **Agente / modelo:** Claude Code + Opus 5.5, na `master`.
- **Pedido:** "sabe a grama do zelda: The Legend of Zelda: Breath of the Wild? pronto." (depois de pedir grama
  densa e pequena).
- **O que foi feito** (o que marca a grama do BotW, trazido para o nosso crepúsculo e mantendo a grama baixa):
  - Tapete mais denso: até 64 tufos por célula (eram 36); ~45.700 tufos no mapa de teste.
  - Base escura (0,55) que some no chão e ponta clara (1,5): o campo parece contínuo.
  - Faixas de vento: ruído que desliza na direção do vento; onde passa, a grama deita e a ponta clareia.
    O tremor por tufo continua, mais fraco.
  - Manchas de altura por ruído (`FastNoiseLite`, 0,7× a 1,25×): trechos mais altos e mais baixos.
  - A grama se afasta e abaixa em volta da protagonista (a view passa a posição dela ao shader a cada quadro).
  - Malha do tufo indexada (36 → 20 vértices): o shader de vento roda menos vezes.
- **Desempenho (3024×1890):** sem grama 72 FPS; grama nova 49–55 FPS antes de indexar, ~58 depois.
  Não medi o mapa 96×96 cheio desta vez (seriam ~590 mil tufos; vai pedir corte por distância).
- **Prints:** `docs/prints/grama_botw_visao.png`, `docs/prints/grama_botw_perto.png`. Não consegui um print
  da protagonista dentro do gramado (ela ficou no pátio de terra); o gramado aparece ao fundo.
- **GDD:** parágrafo da grama na seção 17 reescrito com a referência ao BotW e as cores roxas atuais.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-26 — Grama trocada pelo asset "Stylized Grass Shader" (StayAtHomeDev) e 5× mais tufos

- **Agente / modelo:** Claude Code + Opus 5.5, na `master`.
- **Pedido:** "esqueça essa grama e use essa https://stayathomedev.itch.io/stylized-grass-shader"; no meio da
  tarefa: "aumente a quantidade em 5x de gramas."
- **O que foi feito:**
  - Baixei os dois pacotes do itch.io (grátis, "pague quanto quiser", licença MIT) e guardei em
    `assets/grama_stylized/` o shader, as malhas `grass.glb` e `grass2.glb` e a licença.
  - `GrassField` agora usa as malhas e o shader do asset (sem mudanças no shader): um MultiMeshInstance3D por
    malha em cada bloco de 8×8. Ficaram a densidade por terreno, a grama sumindo sob construções e as manchas
    de altura. Cores: ponta #C4B3D6, base #6A5B7C, manchas de ruído a cada 12 células.
  - Apaguei o nosso `Grass.gdshader` (vento BotW, afastar da protagonista): o shader do asset não tem vento.
  - Altura 0,08–0,13 (×0,75–1,2 nas manchas); com a nossa altura antiga a malha do asset virava pontinhos.
  - Até 120 tufos por célula (24 × 5, a pedido).
- **Desempenho (3024×1890):** 24/célula: ~17 mil tufos, 54–87 FPS (leituras instáveis; o humano estava
  jogando ao mesmo tempo). 120/célula: 85.881 tufos, ~33 FPS. A touceira `grass.glb` tem muitas folhas.
- **Problemas:** os `.res` do asset apontam para `res://grass.gdshader` (caminho do autor) e usam formato antigo
  de malha; troquei pelos `.glb`. O download pelo itch.io precisou do endpoint de download grátis.
  Um script headless do Godot para inspecionar as malhas travou; medi pelo jogo com um print temporário.
- **Prints:** `docs/prints/grama_stylized_visao.png`, `docs/prints/grama_stylized_perto.png`.
- **GDD:** parágrafo da grama na seção 17 reescrito para o asset.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-26 — Grama se mexe quando a protagonista passa

- **Agente / modelo:** Claude Code + Opus 5.5, na `master`.
- **Pedido:** "tem como fazer a grama se mover um pouco quando meu personagem passa por ela?"
- **O que foi feito:** copiei o shader do asset para `src/View/Grass.gdshader` (o original em
  `assets/grama_stylized` fica intacto; a licença MIT permite) e acrescentei o empurrão: num raio de ~0,45
  célula da protagonista, a grama se inclina para longe dela (a ponta mais que a base, pela altura no mundo)
  e abaixa até 40%. A view passa a posição dela ao shader a cada quadro (`GrassField.SetPusher`).
- **Verificação:** jogo rodando sem erros; nos prints de câmera cinemática andando, abre uma clareira em volta
  dos pés dela. `docs/prints/grama_empurrao.png`.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-26 — Sombra do sol mais curta (o resto da tentativa de desempenho foi desfeito)

- **Agente / modelo:** Claude Code + Opus 5.5, na `master`.
- **Pedido:** empurrão da grama só na câmera cinematográfica e jogo travado a 120 FPS com melhorias de desempenho.
- **O que foi tentado:** limite de 120 FPS, 3D em resolução menor com FSR (0,6), grama com visibilidade por
  distância, tufos mais largos e menos numerosos (120 → 24 por célula), empurrão só na cinematográfica e sombra
  do sol com 2 cascatas e alcance de 40. Chegou a ~120 FPS, mas mudou a grama.
- **Resultado:** o humano pediu para voltar tudo ("a quantidade de grama antes estava perfeita") e manter só a luz,
  de que gostou mais fraca. Ficou só a sombra do sol em `scenes/Main.tscn` (`directional_shadow_mode = 1`,
  `directional_shadow_max_distance = 40`); o resto voltou ao commit anterior.
- **Lição:** não trocar o visual (densidade e forma da grama) para ganhar desempenho sem perguntar antes.
- `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 80 aprovados (rodado durante a tentativa; sem mudança na simulação).

---

## 2026-09-26 — Desempenho, passo 0: medição (painel F3 e teclas de A/B)

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **Pedido:** análise completa de desempenho; meta 60 FPS estáveis em tela cheia na Retina (3024×1890) sem
  reduzir grama nem mudar o visual aprovado. Plano aprovado em 4 passos: medir, cortes sem mudança visual,
  trocas visuais só com aprovação, teste de estresse + arquitetura para escala.
- **O que foi feito:** `src/View/PerfOverlay.cs`, painel na tecla **F3** com FPS, ms por quadro, ms de CPU do
  jogo (cronometrado no GameRoot em volta de simulação + view), draw calls, primitivos, objetos, nós, VRAM e
  resolução 3D. Teclas **F4** grama, **F5** brilho, **F6** névoa, **F7** sombra do sol, **F8** chão,
  **F9** escala 3D (1 → 0,77 → 0,67 → 0,5 com FSR 2), **F10** pós-processo (ajuste de cor + vinheta).
- **Cuidados de medição:** no Metal não há profiler de GPU e o monitor `TIME_PROCESS` inclui a espera pela
  GPU (marcava 32 ms de "CPU"); por isso o painel mede a CPU do jogo por conta própria. O contador de
  primitivos do Godot não conta instâncias de MultiMesh (mostra 0,04 M com 8,6 M de triângulos de grama).
- **Números (mapa de teste 32×32, 85.881 tufos, 3024×1890, tudo ligado = base):**

  | Cena | FPS | ms/quadro |
  |---|---|---|
  | Base | 38–42 | 25–26 |
  | Sem grama | 63 | 15,9 |
  | Sem brilho | 37 | 27,0 |
  | Sem névoa | 35 | 28,6 |
  | Sem sombra do sol | 62 | 16,1 |
  | Sem chão | 63 | 15,9 |
  | Sem pós-processo | 37 | 27,0 |
  | Escala 3D 0,67 (FSR 2) | 40 | 25,0 |
  | Escala 3D 0,50 (FSR 2) | 49 | 20,4 |
  | Sem grama + sem sombra | 120 | 8,3 |
  | Sem grama + sem chão | 106 | 9,4 |
  | Sem sombra + sem chão (grama ligada) | 75 | 13,3 |

  CPU do jogo: 0,1–0,2 ms em todos os casos. O gargalo é 100% renderização.
- **Leitura:** os custos somam. Grama ≈ 10 ms com sombra e ≈ 5 ms sem (o custo é o número de fragmentos das
  8,6 M de triângulos minúsculos, cada um amostrando a sombra suave); sombra do sol ≈ 8 ms, quase tudo na
  filtragem suave por pixel dos receptores (sem grama, só o chão como receptor, tirar a sombra economiza 7,6 ms);
  chão ≈ 7 ms (shader pesado por pixel). Brilho, névoa e pós-processo custam ~0. Reduzir a resolução ajuda
  pouco (0,5 → 6 ms) porque o custo dominante não é por pixel e o FSR 2 tem custo próprio nessa resolução.
- **Próximos alvos, nesta ordem:** shader do chão (mesma imagem, menos amostras), filtragem da sombra
  (tamanho do atlas e qualidade do filtro, conferindo o visual), LOD da grama (malha simples quando o tufo
  tem poucos pixels; aprovado).
- `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 80 aprovados (sem mudança na simulação).

---

## 2026-09-26 — Desempenho 1: atlas da sombra do sol 4096 → 2048

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:** `rendering/lights_and_shadows/directional_shadow/size=2048` em `project.godot`. Com 2
  cascatas e alcance de 40, cada cascata ainda tem ~40 texels por célula, e o desfoque de 1,6 já suaviza a
  borda: sem diferença visível.
- **Medição (base tudo ligado, 3024×1890):** 25,5 ms (38–42 FPS) → **22,2 ms (45 FPS)**. Ganho ≈ 3 ms:
  a filtragem suave lê menos memória de sombra por pixel.
- **Medido, aguardando decisão do humano:** `light_angular_distance` do sol de 4° para 0° (desliga a
  penumbra que cresce com a distância, PCSS; o desfoque fixo de 1,6 continua): 22,2 → **17,9 ms (56 FPS)**,
  ganho ≈ 4,3 ms. Prints: `docs/prints/perf_sombra_com_penumbra.png` e `perf_sombra_sem_penumbra.png`.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-26 — Desempenho 2: LOD da grama por folha achatada; painel com V-Sync, penumbra e captura

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **Medição corrigida:** o V-Sync travava o quadro em múltiplos de 1/120 s e escondia a folga real; o painel
  ganhou **F2** (V-Sync), **F1** (penumbra PCSS do sol), **F11** (captura em resolução total em
  `docs/prints/captura_N.png`, porque o MCP só transporta 640 px), **F12** (LOD da grama) e um aviso
  "[JANELA SEM FOCO]" (em segundo plano o macOS reduz o jogo e as leituras não valem).
- **Números reais (V-Sync desligado, 3024×1890, atlas 2048, mapa de teste, 85.881 tufos):**

  | Cena | ms/quadro | FPS |
  |---|---|---|
  | Base (tudo ligado) | 22,2 | 45 |
  | Sem penumbra (PCSS) | 18,9 | 53 |
  | Sem grama | 11,1 | 90 |
  | Sem grama, sem sombra | 7,4 | 136 |
  | Sem grama, sem sombra, sem chão | 5,3 | 189 |
  | Nada (nem brilho, névoa, pós) | 3,7 | 273 |

  Custos: grama **11,1 ms**; sombra do sol no chão 3,7; shader do chão 2,1; brilho+névoa+pós 1,6; piso 3,7.
  CPU do jogo 0,1–0,2 ms. A grama é cara porque são 8,6 M de triângulos minúsculos: cada um ocupa pelo menos
  um bloco de 2×2 pixels na GPU e roda a filtragem de sombra por pixel.
- **LOD da grama, três tentativas:**
  1. Nível do import (130 → 13 triângulos): a touceira vira uma mancha. Reprovado (prints
     `perf_lod_13tris*.png`, apagados depois).
  2. Metade das folhas (130 → 65): 22,2 → 16,4 ms, mas o tapete fica visivelmente mais ralo a 50% de escala.
     Reprovado.
  3. **Folha achatada** (130 → 30, 72 → 26): todas as folhas ficam, nos mesmos lugares, largura e altura;
     cada tira curva de ~13 triângulos vira 3 (quad na base + ponta). De cima, a curva de uma folha de poucos
     pixels não aparece; a malha completa segue a menos de 11 unidades da câmera (cinematográfica e zoom
     máximo). Prints: `perf_lod_folha3.png` (câmera normal, 1:1), `perf_lod_folha3_meia.png` (50%),
     `perf_lod_folha3_perto.png` (cinematográfica, malha completa). Ligado por padrão; F12 desliga.
     Ainda sem medição limpa: o humano estava usando o jogo e a janela perdia o foco. Pela contagem de
     triângulos (menos que a tentativa 2) a estimativa é ≤ 16 ms (≥ 62 FPS) na cena base.
- **Implementação:** dois conjuntos de MultiMesh por bloco (perto/longe) com os mesmos tufos; o nó de cada
  bloco fica no centro dele porque o `VisibilityRange` mede a distância à origem do nó; troca com fade de 2.
- **Aguardando decisão:** penumbra PCSS (−3,3 ms; prints `perf_sombra_com_penumbra.png` /
  `perf_sombra_sem_penumbra.png`).
- `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 80 aprovados (sem mudança na simulação).

---

## 2026-09-26 — Desempenho 3: penumbra do sol desligada (aprovado) e medição limpa do LOD

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **Decisões do humano:** penumbra PCSS desligada, aprovada ("2 - aprovo"); LOD da grama aceito ("a única
  diferença que senti é que ficou mais escuro ou mais claro", sem preferência).
- **O que foi feito:** `light_angular_distance = 0.0` no sol (`scenes/Main.tscn`); o desfoque fixo de 1,6
  continua.
- **Medição limpa (janela com foco, V-Sync desligado, 3024×1890, 85.881 tufos, mapa de teste):**

  | Cena | ms/quadro | FPS |
  |---|---|---|
  | Início do dia (atlas 4096, penumbra, malha completa) | 25,5 | 38–42 |
  | Atlas 2048 | 22,2 | 45 |
  | + LOD por folha achatada | ~16 (estimado) | ~62 |
  | + penumbra desligada (**estado atual**) | **12,8** | **78** |
  | Estado atual com LOD desligado (F12) | 18,2 | 55 |

  O LOD sozinho vale 5,4 ms nesta cena; a penumbra, 3,3; o atlas, 3,3. Meta de 60 FPS estáveis em tela cheia
  na Retina atingida com toda a grama, sem mudar densidade, luz, névoa nem cores.
- **Sobre a diferença de brilho que o humano notou no LOD:** a folha achatada tem menos vértices, e o degradê
  do shader (UV.y) e as normais são interpolados entre menos pontos, então a folha fica um pouco mais uniforme.
- `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 80 aprovados (sem mudança na simulação).

---

## 2026-09-26 — Desempenho 4: cena de teste de estresse (5.000 inimigos, 500 máquinas, 10.000 itens)

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:**
  - `src/Simulation/StressWorld.cs` (C# puro, orientado a dados: um array por componente, sem objeto por
    entidade; RNG xorshift próprio, determinístico). Inimigos andam para pontos aleatórios do campo (1,6
    células/s); itens correm em 50 circuitos retangulares de esteira (1,875 células/s); máquinas paradas com
    um progresso. Campo 80×80. Testes em `tests/.../StressWorldTests.cs` (5 novos; total 85 aprovados).
  - `scenes/Stress.tscn` + `src/View/StressRoot.cs`: mesma luz, névoa e pós do jogo, chão liso, grama do
    `GrassField` no campo inteiro (468.000 tufos, esteiras e máquinas bloqueiam). Dois modos de desenho
    trocados pela tecla M: **nós** (um MeshInstance3D por entidade, malhas e materiais compartilhados,
    posicionado a cada quadro) e **MultiMesh** (um por tipo de malha e por pedaço de 8×8 células; a cada
    quadro só o buffer de transformações de cada pedaço é reescrito, com caixa justa por quadro para o
    culling). G esconde a grama, F2 V-Sync, F11 captura, roda aproxima, WASD anda.
- **Números (V-Sync desligado, 3024×1890, grama ligada; janela sem foco, o humano estava usando a máquina;
  as leituras se repetiram em duas rodadas):**

  | Câmera | Modo | ms/quadro | CPU simulação | CPU view | draw calls | objetos |
  |---|---|---|---|---|---|---|
  | distância 16 (a do jogo) | nós | 15,2 | 0,13 | 2,6 | 156 | 7.158 |
  | distância 16 | MultiMesh | 16,7 | 0,38 | 3,8 | 552 | 1.194 |
  | distância 28 | nós | 26,3 | 0,24 | 2,6 | 191 | 12.988 |
  | distância 28 | MultiMesh | 28,6 | 0,92 | 5,6 | 920 | 1.562 |

  (Com pedaços de 16×16, primeira rodada: MultiMesh 18,5 ms contra nós 14,9 a distância 16; sem grama, a
  distância 28: nós 16,4, MultiMesh 21,3.)
- **Leitura:**
  - A simulação orientada a dados custa 0,4–0,9 ms por tick para 15.500 entidades; sobra muito.
  - **Para entidades móveis com malhas simples, um nó por entidade é hoje o melhor dos dois:** o Forward+
    já agrupa MeshInstance3D iguais numa chamada instanciada (156 draw calls para 15.500 entidades) e faz
    culling exato por objeto, inclusive na sombra. O MultiMesh dinâmico paga o rebucketing e a cópia dos
    buffers na CPU (3,8–5,6 ms) e desenha instâncias fora da tela nos pedaços parcialmente visíveis.
  - Mover 15.500 nós custa 2,6 ms de CPU (~0,17 µs por entidade); esse custo cresce linear e passa a mandar
    perto de 40–60 mil entidades móveis. Aí o MultiMesh (ou o RenderingServer direto) volta a valer, mas com
    buffers escritos sem cópia e por pedaço só quando algo muda.
  - **O limite real é a GPU:** a distância 28, com ~13 mil objetos na tela, os dois modos ficam em 26–29 ms.
    Reduzir isso é LOD/impostor para inimigos longe, sombra só na cascata perto e menos fragmentos, não
    trocar de API.
  - Onde o MultiMesh ganha com folga é no que é **estático e numeroso**: grama (468 mil tufos em ~200 draw
    calls), pisos, muros, itens parados em esteiras.
- **Prints:** `docs/prints/estresse_perto.png`, `docs/prints/estresse_visao.png`.
- **Pendência:** repetir a tabela com a janela em foco (basta o humano abrir a cena e apertar F2 e M).
- `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 85 aprovados.

---

## 2026-09-26 — Desempenho 5: proposta de arquitetura para escala

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:** `docs/ARQUITETURA_ESCALA.md`: o que as medições dizem, simulação orientada a dados
  (arrays por componente, slots estáveis, grade espacial, flow field para hordas, esteiras como corredores),
  o que desenha cada coisa (MultiMesh por pedaço para o estático e numeroso; nó por entidade com malha
  compartilhada para móveis até ~30 mil; VAT para multidões animadas; RenderingServer direto acima de ~40
  mil), regras gerais (sem sombra de coisa pequena, LOD em tudo, triângulo pequeno é caro, chão barato),
  passos concretos em ordem e o que não fazer. Parágrafo-resumo na seção 13 do GDD apontando para o arquivo.
- Sem mudança de código.

---

## 2026-09-27 — Aldeão, parte 2: primeira variação (cabelo curto bagunçado) para aprovação

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** 5 variações do aldeão (uma por cabelo), Multi-Image to 3D com frente e costas em T-pose,
  low-poly; rig e animações idle, walk, carry, work (girar manivela) e sleep; metade da altura da
  protagonista, pivô na base, mesma frente; marcador "Rosto" na frente da cabeça; prévia a 55°.
  **Primeiro só uma variação**, para conferir se o rig automático aguenta o corpo fora do padrão.
- **Vistas:** `tools/meshy_pipeline/villager_views.py` recorta frente e costas das 5 variações (curto
  bagunçado, médio com franja, ondulado e rabo de cavalo em `aldeao_expressoes.png`, que tem os cabelos; o
  longo liso na folha principal) em `assets/conceitos/aldeao/vistas/`. Pedaços do papel presos entre o
  cabelo e o pescoço viram fundo (o aldeão não tem cor quente).
- **Animações (o catálogo da Meshy não tem carregar nem manivela):**
  - walk: a caminhada grátis que vem com o rig, com os braços abertos 8° (raspavam na barriga);
  - idle: a respiração feita no Blender (como a da protagonista), com os braços mais abertos por causa
    da barriga;
  - carry: a caminhada com os braços travados à frente, abraçando a carga (direções no espaço do
    tronco, acompanhando o balanço);
  - work: parado, as mãos seguem o círculo de uma manivela à frente do corpo (IK de dois ossos
    calculado à mão, gravado em chaves; 5 voltas em 7 s). Na primeira versão as mãos passavam na frente
    da boca (esconderiam a expressão); baixei a manivela, e ela ficou na altura do peito (braços curtos);
  - sleep: "Sleep Normally" (267) da biblioteca, deitado de costas; deitava 19,6 cm acima do chão (como
    numa cama) e foi baixado até encostar.
- **Rig automático: funcionou.** Na caminhada crua (antes de mexer) as pernas alternam sem cruzar,
  os braços balançam e não há rasgos nem torções; no sono o corpo redondo deita sem deformar. Só as mãos
  raspavam na barriga.
- **Marcador "Rosto":** no Blender, um objeto preso a um osso fica relativo à ponta do osso, e as pontas
  dos ossos da Meshy apontam para longe (o marcador saía longe da cabeça). Agora o `normalize.py` só mede
  a frente do rosto e, depois de exportar, acrescenta o nó "Rosto" direto no glTF, como filho da
  articulação `Head`, sem giro nem escala no espaço do modelo (+Z para fora do rosto) e com
  `extras.largura_m`. O osso `headfront` do rig fica na altura do pescoço, então o marcador vai a 35% da
  altura da cabeça (meio de olhos e boca). **Conferido no Godot:** vira `Node3D` dentro de um
  `BoneAttachment3D`, em (0; 0,296; 0,071) e acompanha a cabeça em walk, work e sleep. Largura: 0,104 m.
- **Resultado:** `assets/modelos/aldeao_curto_baguncado/aldeao_curto_baguncado.glb`, 0,34 × 0,17 × 0,40 m,
  clipes `idle`, `walk`, `carry`, `work`, `sleep`; passada de walk e carry 0,202 m/s (no JSON do modelo).
  Prévia a 55° ao lado da protagonista: `assets/previews/aldeoes.png`.
- **Ferramentas novas:** `tools/blender/inspect_clip.py` (quadros de frente e de lado e medidas de um
  clipe), `tools/blender/preview_sheet.py` + `tools/meshy_pipeline/label_sheet.py` (folha a 55° numerada).
- **Créditos:** 38 (30 modelo + 5 rig + 3 sono). Saldo: 2.896 → 2.858. As outras 4 variações: 152.
- **O que deu errado:** aspas duplas num comentário quebraram o `assets.json` de novo; a configuração vazia
  `"rosto": {}` contava como falsa e o marcador não era criado; a ferramenta de inspeção desenhava o
  marcador no lugar errado (o mesmo problema de ponta de osso no importador do Blender), e foi retirada.
- **Correções manuais:** nenhuma.
- **Tempo:** 12:10–13:40 de relógio.

---

## 2026-09-27 — Aldeão: mais 3 variações; o cabelo longo liso falhou na Meshy

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** "pode gerar" as outras 4 variações.
- **Resultado:** médio com franja, ondulado e rabo de cavalo geradas, com rig e os 5 clipes
  (`idle`, `walk`, `carry`, `work`, `sleep`) e o nó "Rosto"; todas com 0,40 m. Inspecionadas de frente e de
  lado: o rig funcionou nas três (pés não cruzam, nenhuma deformação estranha), cada cabelo se distingue.
  Larguras do rosto: 0,104 / 0,101 / 0,092 m.
- **Falhas da Meshy:** a primeira tentativa do médio com franja deu "erro inesperado" e a segunda passou;
  o **longo liso** deu o mesmo erro duas vezes e, pela regra (uma nova tentativa só), ficou para depois.
  Tarefa que falha não é cobrada.
- **Créditos:** 114 (3 × 38). Saldo: 2.858 → 2.744. Total do aldeão até aqui: 152.
- **Prévia:** `assets/previews/aldeoes.png` com a protagonista de referência e as 4 prontas, numeradas.
- **Correções manuais:** nenhuma.
- **Tempo:** 13:45–14:25 de relógio.

---

## 2026-09-27 — Aldeão modular: corpo-base careca + cabelos como peças

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** um corpo-base careca com um rig e um conjunto de animações só, e os cabelos como peças
  separadas, recortadas das variações já geradas (sem gerar nada novo); nós "Cabelo" e, acima dele,
  "Chapéu" presos à cabeça; prévia do corpo-base com cada cabelo a 55°.
- **Corpo-base (`aldeao_base`, 38 créditos):** a folha careca (renomeada para `aldeao_careca.png`) teve
  frente e costas recortadas e passou pelo Multi-Image to 3D, rig e sono, com os mesmos ajustes do curto
  bagunçado (idle, walk, carry, work, sleep, Rosto). O rig funcionou como nas variações (inspecionado). Nós
  presos à cabeça gravados no glTF e listados em `aldeao_base.json` (`encaixes`, espaço do modelo):
  Rosto (0; 0,308; 0,059), Cabelo no topo da cabeça (0; 0,400; −0,006) e Chapéu 12% da altura da cabeça
  acima (0; 0,417; −0,006). **Conferido no Godot:** os três viram filhos de `BoneAttachment3D`.
- **Cabelos (`tools/blender/extract_hair.py`, 0 créditos):** para cada variação, a malha em pose de repouso;
  cabelo = faces **escuras e saturadas** (limite de brilho por Otsu na cabeça; saturação no meio do caminho
  entre pele e cabelo), crescendo pela vizinhança a partir das de cima do pescoço; fechamento de 3 passos
  (fora do rosto) para cobrir reflexos claros; ilhas pequenas fora; buracos de até 12 arestas fechados. A
  cabeça da variação vai para a do corpo-base (base e topo iguais, folga de 3%) e todo vértice que cai dentro
  do couro cabeludo do corpo-base é empurrado para fora (+2 mm). Exportado em
  `assets/modelos/aldeao_cabelos/<var>.glb` com a origem no encaixe "Cabelo": no jogo, o cabelo vira filho
  desse nó sem ajuste. **Conferido no Godot:** o rabo de cavalo preso no Cabelo ocupa o topo e a nuca da
  cabeça e acompanha a caminhada.
- **O que deu errado no caminho:**
  - o glTF duplica vértices nas costuras de UV, e as faces não compartilhavam arestas: a vizinhança passou a
    ser pela posição dos vértices;
  - só o brilho deixava o crescimento escorrer pela pele sombreada do corpo; a saturação separa (o cabelo é
    mais saturado: 0,30 contra 0,19 no curto);
  - a cabeça careca, de formato um pouco diferente, atravessava o cabelo (manchas carecas na prévia);
    resolvido empurrando para fora os vértices de dentro.
- **Faltando:** o **longo liso**, que falhou duas vezes na Meshy, não tem modelo para recortar. Opções: tentar
  gerar a variação de novo (38 créditos se der certo) ou gerar só um cabelo.
- **Cabelos longos e corrente de ossos:** nos modelos da Meshy, o cabelo longo virou pouco volume: no ondulado
  e no rabo de cavalo a geometria de cabelo desce só até cerca de meia altura de cabeça abaixo do pescoço (o
  resto das pontas ficou pintado na textura do corpo). Presos rígidos à cabeça, eles quase não atravessam
  os ombros; no protótipo, aceitável. **Uma corrente de 2 a 3 ossos só valeria** para um cabelo longo de
  verdade (o longo liso, se for regerado, ou um rabo refeito mais comprido): balançaria com a corrida e
  evitaria atravessar as costas quando a cabeça gira. Para os 4 atuais, não compensa.
- **Prévia:** `assets/previews/aldeoes_modular.png` (corpo-base em idle com os 4 cabelos, numerados).
- **Ferramentas:** `extract_hair.py`, `preview_modular.py` (com `AZIMUTE` para ver de lado ou por trás).
- **Créditos:** 38. Total do aldeão: 190 (4 variações + corpo-base). Saldo: 2.706.
- **Correções manuais:** nenhuma.
- **Tempo:** 14:35–16:10 de relógio.

---

## 2026-09-27 — Aldeão modular: correções vistas no jogo (rosto, atlas, cabelos, nuca, longo liso)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** (1) rosto duplicado: apagar o rosto do corpo-base e limpar as bordas do atlas; (2) cabelos com
  buracos por trás; (3) triângulo cinza na nuca; (4) falta o longo liso; prévia de frente, costas e perfil.
- **1. Rosto do corpo-base (`erase_face` + `flatten_face` no `normalize.py`, config `apagar_rosto`):**
  - **O rosto era também forma, não só pintura:** num render cinza liso apareceram os olhos como bolas
    em órbitas fundas, nariz e boca em relevo. Pintar deixava as órbitas; alisar (Taubin) não achatava;
    projetar numa esfera dobrava triângulos.
  - **Solução:** as faces dentro de um elipsoide no rosto saem; o buraco é triangulado de novo no plano
    da frente (Delaunay com a borda como restrição + grade de pontos) e a profundidade de cada ponto é uma
    membrana presa na borda, estufada até a esfera da cabeça no meio. Faces novas 100% no osso Head, com a
    UV de um pixel de pele. Na textura, a região do rosto é pintada com a pele em volta (mediana de um anel,
    #96B1C3) pela posição 3D de cada pixel, incluindo 3 px além da borda das ilhas de UV (sangravam).
  - **O que deu errado:** (a) uma edição por script sobrescreveu o `normalize.py` (precedência de um
    `... if False else ...`); reconstruído da versão commitada mais o código do dia (o diff só acrescenta);
    (b) aumentar a região para os lados encostou nas orelhas, a borda virou um "8" e o passeio pela borda
    entrou em laço infinito (19 min de CPU); agora o passeio tem limite e a região só cresce para cima
    (`centro_altura` 0,41, `raio_altura` 0,36); (c) calota facetada mostrava a grade em xadrez: fica lisa.
  - **Limite:** a calota tem a cor lisa da pele, sem as manchas de pintura do resto da cabeça; o decal da
    expressão cobre quase toda.
- **Atlas de expressões:** agora só os traços ficam opacos (distância de cor até a pele, dentro de uma oval
  justa); pele, contorno do rosto, orelhas, pescoço e papel ficam transparentes. Sobra um fio fino no meio da
  testa em algumas células (faz parte do desenho).
- **2 e 3. Cabelos (`extract_hair.py`):**
  - **Triângulo na nuca = erro meu:** empurrar o cabelo para fora do couro cabeludo lançava um raio do
    centro da cabeça; perto do pescoço ele saía pelo pescoço, acertava o ombro e puxava o vértice até lá.
    Agora só vale raio que acerta a cabeça, e o deslocamento máximo é 1,2 cm.
  - **Limpeza:** solda de costuras, pedaços soltos fora, bordas (pontas) suavizadas, buracos fechados
    (inclusive a abertura de baixo), normais recalculadas, material com as duas faces visíveis. Remover
    "triângulos finos" como pontas quebradas tirava mecha de verdade (mechas são triângulos finos): ficou
    só para lascas extremas.
  - **Touca:** os buracos maiores eram falhas do próprio cabelo gerado. Cada cabelo ganhou uma touca: o
    couro cabeludo do corpo-base (sem rosto e orelhas), 1,5 mm para fora, na cor mediana do cabelo (convertida
    de sRGB para linear; sem isso saía quase branca), um pouco mais escura. Nenhuma pele aparece mais.
- **4. Longo liso:** a Meshy gerou desta vez (as falhas anteriores eram do serviço). Recortado como os outros;
  desce até 8 cm do chão.
- **Conferido no Godot:** os 5 cabelos carregam presos ao nó "Cabelo" do corpo-base, uma malha cada.
- **Prévia:** `assets/previews/aldeoes_correcao.png` (frente, costas e perfil, cada aldeão girado no lugar;
  `preview_modular.py` com `AZIMUTE`).
- **Resultado por cabelo:** curto, ondulado, longo liso e rabo de cavalo ficaram bons. **O médio com franja
  é fraco:** por trás a geração original quase não tinha mechas, e sobra a touca lisa (parece capacete).
  Proposta: gerar esse cabelo como peça própria.
- **Créditos:** 38 (longo liso). Total do aldeão: 228. Saldo: 2.668.
- **Correções manuais:** nenhuma.
- **Tempo:** 16:20–18:30 de relógio.

---

## 2026-09-27 — Aldeão modular, etapa 2: cabelo sorteado, expressão e descanso na simulação

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **Etapa 1 (merge da `arte`):** já estava feito, a `master` apontava para o mesmo commit da `arte`
  (`2cc1f0f`); nada a mesclar. O `docs/GDD.md` local tem uma exportação em texto puro não commitada (sem
  os títulos em markdown); ficou de fora dos commits, a reexportar em markdown do documento vivo.
- **Decisões do humano:** velocidade do aldeão pela opção (c): 1,2 células/s (era 3,0) com a animação
  limitada a 3×; se ficar ruim, o agente de arte faz um walk mais rápido. `sleep` ligado a um estado
  `Resting` que ainda nada dispara (a noite não existe), mais tecla de depuração na view. Coleta **não**
  usa o clipe `work`: coleta e trabalho de máquina terão animações próprias; até lá, coletando fica em
  `idle` com o golpe procedural do corpo.
- **O que foi feito:**
  - `VillagerExpression` (enum na ordem das células do atlas 3×3: distraído, esforço, feliz, sonolento,
    dormindo, espantado, preocupado, chorando, bravo).
  - `Villager.HairVariant` (1–5, fixo pelo id com uma mistura simples), `Villager.Expression` calculada a
    cada tick pela tabela do GDD com o que a simulação já sabe: dormindo (`Resting`), feliz por 3 s após
    entregar, esforço coletando ou levando carga, preocupado com a cabana cheia (mesmo parado com carga na
    mão), sonolento após 30 s ocioso, senão distraído. Espantado, chorando e bravo ficam sem gatilho.
  - `Villager.SetResting(bool)` para o futuro sistema de noite.
  - `data/villagers.json`: `speed` 1.2, com o porquê no comentário.
  - Testes: `VillagerLookTests` (6 novos; total 91 aprovados).
- **O que deu errado:** o teste de "feliz" usava uma árvore tão perto que o aldeão entregava de novo em
  menos de 3 s (comportamento certo; afastei a árvore no teste). "Preocupado" não aparecia porque, com a
  cabana cheia, o aldeão espera com carga sobrando e "carregando" vencia; agora esforço só vale coletando
  ou levando a carga.
- `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 91 aprovados.

---

## 2026-09-27 — Aldeão modular, etapa 3: o corpo-base no lugar da cápsula, com os clipes

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:** `VillagerVisual` reescrito: instancia `assets/modelos/aldeao_base/aldeao_base.glb`
  (girado 180°, como a protagonista), acha os encaixes "Rosto", "Cabelo" e "Chapéu" e lê `largura_m` dos
  extras do glTF (0,0898 m). Estados → clipes: parado idle, andando walk, andando com carga carry,
  descansando sleep; coletando fica em idle com o golpe procedural do pivô. walk e carry tocam no ritmo da
  velocidade real ÷ passada do JSON (0,207 m/s), com teto de 3×. A carga (cubinho) passou das costas para a
  frente do peito, onde o clipe carry abraça. Sem o modelo, cai numa cápsula pequena. Foco cinematográfico do
  aldeão baixado para a altura do modelo (0,25 a 1,8 de distância). Tecla **N** no painel de desempenho força
  o sleep em todos (só visual), para conferir o decal no clipe deitado.
- **Conferido no jogo:** os três aldeões aparecem com o modelo, sem aviso de encaixe faltando; idle respira;
  o sleep deita no chão. Prints: `docs/prints/aldeao_modelo_idle.png`, `aldeao_modelo_sleep.png`.
- **Import:** o editor marcou as texturas do aldeão como usadas em 3D (compressão VRAM); os `.import` mudados
  entram neste commit para não oscilar a cada abertura.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-27 — Aldeão modular, etapa 4: cabelos como peças no encaixe "Cabelo"

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:** `data/villager_looks.json` lista as 5 variações na ordem do sorteio (nome, modelo,
  versão sob chapéu). `src/View/VillagerLooks.cs` lê o JSON (System.Text.Json, porque os JSON de `data/` têm
  comentários que o `Json` do Godot não aceita), guarda as `PackedScene` dos GLB em cache e instancia a peça;
  arquivo ausente (o longo liso, variação 4) = careca com um aviso único. `VillagerVisual` põe a peça
  dentro do nó "Cabelo" na primeira atualização (a peça já vem com a origem no encaixe, sem ajuste). Um
  corpo, um rig e um `AnimationPlayer` por aldeão; o cabelo é só uma malha filha da cabeça.
- **Conferido no jogo:** os três aldeões saíram com cabelos diferentes (franja, curto), acompanhando a cabeça
  no idle. Print: `docs/prints/aldeao_cabelo.png`.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-27 — Aldeão modular, etapa 5: expressão por Decal no encaixe "Rosto"

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:** `VillagerLooks.FaceTexture` fatia o atlas `assets/texturas/aldeao/expressoes.png`
  (3×3, 256 px por célula) em 9 texturas na primeira vez (o `Decal` não lê região de atlas). `VillagerVisual`
  cria um `Decal` filho do encaixe "Rosto", girado 90° em X para projetar no −Z do encaixe (para dentro do
  rosto), com lado = `largura_m` × 1,15 e profundidade 0,08 (curta, para não alcançar a nuca); troca a
  textura quando `Villager.Expression` muda. O decal só atinge a camada 1 (o corpo): as peças de cabelo
  (e os chapéus, na etapa 6) ficam na camada 2, então o rosto nunca aparece sobre o cabelo.
- **Verificação visual pendente:** a janela do jogo ficou em segundo plano durante as capturas (o humano
  estava usando a máquina) e as três capturas F11 saíram idênticas. Falta conferir o decal nos cinco clipes
  (frente, costas, dormindo) e a orientação da textura (pode estar de cabeça para baixo: aí é girar o decal
  180° em Y).
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-27 — Aldeão modular, etapa 6: peças de cabeça (chapéus) em JSON, com a regra "cobre"

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:** `data/head_pieces.json` (peças com `kind`, `name`, `cobre` nenhum/parcial/total,
  `model` opcional em `assets/modelos/aldeao_chapeus/`, e `worker`: a peça que quem tem cabana veste).
  `VillagerLooks` lê o JSON (valor de `cobre` inválido dá `FormatException`), e `InstantiateHeadPiece` usa o
  GLB ou, sem modelo, uma forma provisória de chapéu de palha (aba larga + copa baixa, dois cilindros) na cor
  do recurso do ofício. `VillagerVisual.UpdateHat` põe a peça no encaixe "Chapéu" quando o aldeão ganha
  cabana e tira quando perde; regra: `nenhum` mostra o cabelo, `parcial` troca pela versão sob chapéu
  (`underHat` em `villager_looks.json`; nenhum cabelo tem ainda, então esconde), `total` esconde. Cabelo e
  chapéu ficam na camada 2, fora do alcance do decal do rosto.
- **Mapa de teste `data/maps/aldeoes_teste.json`:** cabana de lenhador com árvores perto e 4 aldeões, para ver
  walk, carry, chapéu e expressões sem preparar nada. `MapPath` do GameRoot aponta para ele **temporariamente**
  (volta ao `mapa_teste.json` no fim da tarefa).
- **Conferido no jogo (capturas F11 em resolução total):** o lenhador anda com o chapéu de palha e sem o
  cabelo por baixo; o decal do rosto aparece de frente (olhos e boca), acompanha a cabeça e não vaza para a
  nuca. Prints: `docs/prints/aldeao_chapeu_palha.png`, `aldeao_rosto_decal.png`. Ainda não conferi o decal
  no clipe `sleep` de perto nem a orientação exata (se a textura está de ponta-cabeça).
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-27 — Aldeão modular, etapa 7: desempenho com 50, 200 e 500 aldeões animados

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:** `VillagerVisual` ganhou um `DrawState` (posição, direção, cabelo, expressão, descanso,
  carga, ofício, coleta): o jogo monta a partir do `Villager`, a cena de estresse monta um sintético. Em
  `scenes/Stress.tscn` as teclas **0/1/2/3** criam 0/50/200/500 aldeões com o modelo completo (esqueleto
  animado em walk, cabelo, decal de expressão trocando a cada 4 s, metade com chapéu de palha, um quarto
  carregando), andando em círculos a 1,2 células/s em volta do ponto olhado; **H** esconde a horda de
  inimigos/itens/máquinas para medir só os aldeões sobre a grama. A cena força tela cheia ao abrir (a janela
  abria em 1152×648 pelo editor).
- **Números (V-Sync desligado, janela com foco, horda oculta, grama 468 mil tufos, câmera a 16 do chão).**
  Atenção: a tela cheia foi para o monitor externo, **3840×2160** (8,3 Mpx, mais que a Retina, 5,7 Mpx), então
  os valores são um teto conservador:

  | Aldeões animados | ms/quadro | FPS | draw calls | nós |
  |---|---|---|---|---|
  | 0 | 13,2 | 76 | 41 | 17.413 |
  | 50 | 14,5 | 69 | 265 | 18.318 |
  | 200 | 16,7 | 60 | 885 | 21.033 |
  | 500 (câmera a 6, zoom do humano; ~150 na tela) | 16,4 | 61 | 739 | 26.463 |
  | 500 idem, sem grama | 12,5 | 80 | 718 | 26.463 |

  500 a distância 16 não deu para medir: o humano estava usando o mouse na janela e o foco se perdia.
  Extrapolando o custo linear (≈ 17 µs por aldeão na tela por quadro, 50 → +1,3 ms, 200 → +3,5 ms), 500 na
  tela dariam ≈ 22 ms (≈ 45 FPS) em 4K, e um pouco melhor na Retina. A confirmar com a janela livre.
- **Onde está o custo:** CPU da view 2,4–3,6 ms (inclui atualizar os 500 `VillagerVisual`), simulação
  0,1–0,2 ms: sobra. O que cresce é a GPU: ~4,4 draw calls por aldeão (corpo com skinning, cabelo, aba e copa
  do chapéu, decal) e o skinning de 500 esqueletos.
- **Propostas se precisar de mais (não aplicadas, porque 200–500 na tela já ficam em ≥ 60 FPS):**
  1. `VisibilityRange`: além de ~20 unidades da câmera, trocar o corpo animado por uma malha estática (pose
     de walk congelada) ou um impostor; a câmera normal fica a 16, então só afeta o zoom mais afastado.
  2. Taxa de animação menor para quem está longe: `AnimationPlayer` em modo manual, avançando a 10–15 Hz para
     aldeões a mais de ~12 unidades (imperceptível de cima).
  3. Menos draw calls por aldeão: aba e copa do chapéu numa malha só; e, quando o chapéu de arte existir,
     cabelo + chapéu na mesma `MeshInstance3D` com duas superfícies.
  4. LOD de malha no import do corpo-base (o Godot gera; o esqueleto é o mesmo).
- **Prints:** `docs/prints/estresse_aldeoes_50.png`, `estresse_aldeoes_500.png`.
- `MapPath` do GameRoot voltou para `mapa_teste.json`.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-27 — Menu inicial

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **Pedido (tarefa 2 de 3):** tela no estilo do jogo (névoa roxa, escuro), protagonista em idle com o cristal
  brilhando e aldeões por perto; botões Novo jogo, Continuar (desativado sem save), Biografia, Configurações
  (esboço) e Sair.
- **Antes:** o GDD vivo foi exportado e comparado com o commit: sem diferenças. A `arte` não tem commits novos
  (o rosto apagado da textura ainda não chegou; a tarefa 1 espera).
- **O que foi feito:**
  - `scenes/Menu.tscn` (cena principal agora; `Main.tscn` continua sendo o jogo) com o mesmo céu, névoa e sol
    do jogo, e `src/View/MenuRoot.cs`: campo de grama 24×24, `CastellanVisual` no centro (idle e cristal
    aceso, sem simulação), 4 `VillagerVisual` com cabelos, expressões e chapéus variados via `DrawState`,
    câmera baixa com um balanço lento. Painel escuro à esquerda com os botões; o grupo fica à direita do
    centro para não ser coberto.
  - Continuar olha `GameFiles.HasSave()` (`user://save.json`); não existe sistema de save, então nasce
    desativado com dica "Nenhum jogo salvo.". Biografia abre `scenes/Biography.tscn` quando ela existir.
    Configurações: painel com Tela cheia e V-Sync funcionando e um volume desabilitado (não há som).
  - `src/View/GameFiles.cs`: caminhos dos JSON e `LoadData()`; o `StressRoot` passou a usar (tinha cópia).
  - `scenes/vignette_material.tres` para reaproveitar a vinheta fora do `Main.tscn`.
- **Conferido no jogo:** menu, painel de configurações e Novo jogo (carrega o jogo). O editor abriu `Main.tscn`
  no primeiro `project_run mode=main` (configuração antiga em memória); rodando a cena do menu direto, ok.
- **Prints:** `docs/prints/menu_inicial.png`, `menu_configuracoes.png`.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-27 — Biografia, etapa B: dados e textos

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:** `data/biography.json` com 6 categorias (Personagens, Máquinas, Construções, Armas e
  Itens, Recursos, Inimigos) e 16 entradas: cada uma com id, nome, categoria, descrição, história, modelo
  (`castellan`, `villager`, `building:<kind>`, `item:<kind>`, `resource:<kind>`), animações (botões do
  palco) e `descoberto` (tudo true por ora). Inimigos fica vazio com a frase "As hordas ainda não chegaram
  até aqui": não há inimigo no jogo nem modelo; inventar um seria arte.
- **Textos:** no tom de "História e mundo" (frases curtas, sugerir e não explicar; a Corrupção só por efeitos:
  o veio azul dentro dos troncos, a mancha do minério, o fumo que não chega ao céu). Apresentados ao humano
  para revisão antes de fechar a tarefa.
- Sem mudança de código. `dotnet build` não se aplica (só JSON).

---

## 2026-09-27 — Biografia, etapa C: a cena da enciclopédia com palco 3D

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **O que foi feito:**
  - `src/View/Biography.cs` lê `data/biography.json` (categorias, entradas; `descoberto` false vira "???" e
    botão desativado).
  - `scenes/Biography.tscn` + `src/View/BiographyRoot.cs`: mesma atmosfera do jogo; colunas categorias →
    entradas → palco → texto (nome, descrição, história). Palco: pátio de terra com grama em volta, pedestal,
    câmera em órbita (arrastar gira, roda aproxima; o delta vem da posição absoluta, porque eventos sintéticos
    de teste vêm sem `Relative`). Modelos: `CastellanVisual` (idle, com o cristal), `VillagerVisual`
    (dirigido por um `DrawState` parado, de frente para a câmera), `BuildingModels` para construções e
    máquinas, cubos de item e de recurso girando devagar.
  - Controles embaixo: clipes da entrada (protagonista: idle, run, work; aldeão: idle, walk, carry, work,
    sleep; máquinas: funcionando/parada, por enquanto só a lâmina e o pulso do modelo, a etapa D troca pelo
    mundo real); no aldeão, 9 expressões, 5 cabelos e um botão de chapéu.
  - Ganchos de prévia: `CastellanVisual.PlayClip`, `VillagerVisual.PreviewClip` (clipe forçado em 1×) e
    `VillagerVisual.ResetLook` (refaz cabelo e chapéu ao vivo). Esc ou "Voltar ao menu" voltam ao menu.
- **Conferido no jogo:** categorias, entradas, texto, giro por arrasto, troca de expressão (feliz), cabelo
  (ondulado) e clipe (walk). O aldeão nasceu de costas (direção padrão +Z) e foi virado para −Z; as
  fileiras de botões estouravam o painel de baixo e passaram a quebrar linha (`HFlowContainer`) num painel
  mais alto que ocupa também a coluna das entradas.
- **Prints:** `docs/prints/biografia_protagonista.png`, `biografia_aldeao.png`, `biografia_serraria.png`.
- `dotnet build`: 0 erros, 0 avisos. Sem mudança na simulação.

---

## 2026-09-27 — Biografia, etapa D: máquinas trabalhando de verdade no palco

- **Agente / modelo:** Claude Code + Fable 5.1, na `master`.
- **Simulação:** `SpawnItemCommand(cell, kind)` + `SimWorld.TrySpawnItem`: um item nasce na entrada de uma
  esteira sem Castelão nem alcance (alimentador do palco e de testes). 3 testes novos (`SpawnItemTests`);
  total 94 aprovados.
- **Palco:** para cada máquina, `BiographyRoot.BuildMachineWorld` monta um mundo 9×7 de terra pelo
  `MapLoader` (esteira de entrada x 1..3 → máquina em (4,3) virada para leste → esteira de saída x 5..7 →
  baú em (8,3); o Castelão fica escondido em (4,1) porque o mapa exige um), desenhado pelo próprio
  `WorldView` do jogo (esteiras, itens, pulso da máquina, fumaça). O alimentador faz nascer os insumos da
  receita na primeira esteira a cada 10 ticks, na proporção da receita (forja: lingote, lingote, haste).
  "Funcionando" alimenta; "parada" corta o insumo: a máquina termina o que tem na esteira e para de verdade.
  Um `VillagerVisual` fica ao sul da máquina, virado para ela, em `work` quando funciona e `idle` quando
  para: **só visual**, a simulação ainda não tem operador de máquina. A câmera das máquinas começa ao sul,
  para a esteira correr da esquerda para a direita.
- **Conferido no jogo:** Serraria com hastes saindo; Forja com lingotes e hastes na fila, fumaça e espada na
  saída; "parada" esvazia a fila e o aldeão volta ao idle. Prints: `docs/prints/biografia_serraria_funcionando.png`,
  `biografia_forja_funcionando.png`, `biografia_forja_parada.png`.
- **Medição:** a janela do jogo abre ora em 1152×648, ora em 3840×2160 (monitor do editor); as coordenadas dos
  cliques de teste mudam com isso. Anotado.
- `dotnet build`: 0 erros, 0 avisos. `dotnet test`: 94 aprovados.

---

## 2026-09-27 — Aldeão: máscara do rosto em malha (no lugar do decal) e proposta dos cabelos

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** o decal projetava o rosto nos fios de cabelo da frente. (1) Máscara do rosto em malha presa ao
  osso Head, com UV numa célula do atlas; conferir em todos os clipes. (2) Propor os 5 cabelos como peças
  próprias na Meshy, com o custo antes.
- **1. Máscara (`add_face_mask` no `normalize.py`, config `mascara_rosto`, 0 créditos):**
  - Grade 16×16 no plano da frente (0,85 da largura da cabeça = 12,7 cm, centro a 41% da altura da cabeça),
    projetada na superfície do rosto (raio de frente para trás) e afastada 2 mm pela normal. Só a oval dos
    traços fica (os cantos da célula são transparentes no atlas).
  - UV: exatamente a célula 1 do atlas (no Godot, x 0..1/3 e y 0..1/3); o jogo troca a célula pelo
    `uv1_offset` (1/3 por coluna e por linha). Material com o atlas, transparente.
  - Objeto "Rosto" com skin 100% no osso Head (segue a cabeça como a pele dela); substitui o nó vazio
    "Rosto" (a posição continua em `aldeao_base.json`).
  - **Conferido (`tools/blender/check_face_mask.py`):** distância de cada vértice até a pele, 12 instantes
    por clipe: idle, work e sleep entre +1,2 e +2,5 mm; walk e carry entre 0,0 e +2,0 mm (o ponto mais perto
    encosta, não atravessa). Primeira versão, quadrada: atravessava até 11 mm nos cantos (a grade saía da
    região do rosto presa só à cabeça e entrava na do pescoço) e sobrava uma aba abaixo do queixo; resolvido
    cortando para a oval. No Godot: `MeshInstance3D` "Rosto" filho do `Skeleton3D`, material transparente.
  - **Para o agente do jogo:** o "Rosto" agora é a malha, não um nó vazio para o decal.
- **2. Cabelos:** tentei montar vistas "só do cabelo" recortando o conceito pela cor; no desenho 2D a pele
  sombreada e o cabelo têm quase o mesmo azul e o recorte levou corpo e rosto junto (descartado). Proposta:
  Image to Image da Meshy (referências: frente e costas do conceito de cada cabelo) para gerar a peruca limpa
  de frente e de costas, e Multi-Image to 3D a partir delas; no Blender, encaixe na cabeça do corpo-base e
  checagem de que nada fica na frente da máscara. Custo: 42 por cabelo, 210 para os 5. Aguardando aprovação.
- **Créditos:** 0.
- **Correções manuais:** nenhuma.
- **Tempo:** 18:40–19:50 de relógio.

---

## 2026-09-27 — Aldeão: 5 cabelos gerados como perucas próprias

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** os 5 cabelos como peças próprias ("perucas") na Meshy, a partir das vistas do conceito, no
  tamanho da cabeça do corpo-base; nenhum fio na frente dos olhos nem sobre a máscara; fechados; bonitos de
  trás. Custo aprovado: 210 créditos.
- **Geração (`tools/meshy_pipeline/hair_pieces.py`, 210 créditos, nenhuma falha):** para cada cabelo,
  Image to Image (`nano-banana-2`, referências: vistas de frente e costas do conceito) com o prompt "só esse
  penteado, como peruca, sem cabeça nem rosto, franja acima das sobrancelhas, costas cheias", uma imagem de
  frente e uma de costas (6 + 6), e Multi-Image to 3D com as duas (30). As imagens de peruca saíram limpas:
  de frente, o rosto fica vazio.
- **Encaixe (`tools/blender/fit_hair.py`, 0 créditos):**
  - escala pela coroa: largura da peruca numa faixa perto do topo = 1,12 × a largura da cabeça na mesma
    faixa, com a faixa medida em altura de cabeça (medida em altura da peruca, no cabelo comprido ela caía
    nas orelhas e a peruca encolhia); topo pelo percentil 97 da altura (uma mecha espetada baixava tudo);
  - abertura do rosto: toda face na frente da cabeça dentro da oval da máscara (×1,08) sai;
  - fora do couro cabeludo: um campo de direções infla a camada perto da cabeça (até 2,5 cm da pele) o
    quanto for preciso para ficar 2 mm fora, deslocando as camadas juntas (empurrar vértice a vértice
    achatava as mechas numa película e abria frestas); a cortina de cabelo comprido, longe, não anda;
  - touca por baixo (couro cabeludo fora da abertura do rosto, 0,8 mm), texturizada com a UV do ponto mais
    próximo da peruca e o material dela: no longo liso, a nuca não tinha malha nenhuma e a touca lisa
    aparecia como mancha; agora aparecem fios. Buracos pequenos fechados, normais recalculadas, duas faces.
  - Sem rig: o cabelo é rígido, preso ao nó "Cabelo" (origem do GLB no encaixe).
- **Conferido:** cobertura de trás, dos lados e do topo entre 97% e 100% das direções a partir do centro da
  cabeça; no Godot, os 5 carregam no nó "Cabelo" do corpo-base, uma malha e um material cada.
- **Prévia:** `assets/previews/aldeoes_correcao2.png` (frente, costas e perfil, com a máscara do rosto).
- **Limites:** no longo liso, a nuca é a touca texturizada (lê como cabelo, mas um pouco embaralhada); o
  ondulado saiu mais claro que os outros (é a cor da peruca gerada).
- **Créditos:** 210. Total do aldeão: 438. Saldo: 2.458.
- **Correções manuais:** nenhuma.
- **Tempo:** 19:55–21:40 de relógio.

---

## 2026-09-27 — Expressões do aldeão pela máscara em malha (para testar na Biografia)

- **Agente / modelo:** Claude Code + Opus 5.5, na branch `arte` (código do agente do jogo, a pedido do humano).
- **Pedido:** "merge para eu testar na biografia".
- **O que foi feito:** o `VillagerVisual` procurava "Rosto" como nó para prender o decal; agora "Rosto" é a
  máscara em malha. Troca mínima: se "Rosto" é uma `MeshInstance3D`, cada aldeão ganha uma cópia do material
  dela e a expressão escolhe a célula do atlas pelo `uv1_offset` (coluna e linha de 1/3; a ordem de
  `VillagerExpression` é a ordem do atlas); o decal só é criado no modelo antigo (nó vazio).
- **Conferido:** `dotnet build` 0 erros e 0 avisos; `dotnet test` 94 aprovados; render no Godot com a célula
  "feliz" mostrando o sorriso na máscara, sem projeção no cabelo.
- Depois, `master` avançada até a `arte`.

---

## 2026-09-27 — Rosto do aldeão v3: traços 2D desenhados por código em dois planos (olhos e boca)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** refazer o rosto como em jogos estilizados: traços 2D limpos desenhados por código (SVG → PNG
  transparente), duas folhas (olhos com sobrancelhas; boca), dois planos presos ao osso Head, curvos, 1 mm
  acima da pele, cada um com UV numa célula; prévia de frente e a 55°. Esquecer os recortes da ilustração
  (a tentativa de tirar só os traços do conceito, interrompida, está no histórico do `villager_faces.py`).
- **Folhas (`tools/meshy_pipeline/face_sprites.py`, 0 créditos):** SVG por código, exportado com `cairosvg`
  (usa o cairo do Homebrew; o script se relança com `DYLD_FALLBACK_LIBRARY_PATH`). Olhos redondos com branco
  #E3E7EB, pupila #15171C com brilho, olheira suave (elipse desfocada, 28%), contorno #1B1E26 de 5 px,
  sobrancelhas finas, pálpebras como cortes com linha. `assets/texturas/aldeao/olhos.png` 3×3 de 512×256:
  distraído, esforço, feliz, sonolento, fechado, espantado, preocupado, chorando (lágrimas), bravo.
  `bocas.png` 3×2 de 256×128: neutra, entreaberta, sorriso, esforço (dentes cerrados), "o", triste. SVGs ao
  lado. Tudo centralizado no mesmo ponto em cada célula; fundo 100% transparente.
- **Planos (`add_face_planes` no `normalize.py`, config `planos_rosto`):** grade projetada na pele (raio de
  frente para trás) e afastada 1 mm pela normal, peso 1 no osso Head, UV na célula 1 da folha. Olhos:
  13,5 × 6,7 cm, centro a 44% da altura da cabeça; boca: 6,3 × 3,1 cm, a 24%. Substituem a máscara "Rosto".
- **Problemas e correções:**
  - a boca entrava até 1,4 mm na caminhada: a pele do queixo tinha peso do pescoço e do ombro. A pele
    debaixo de cada plano (acima da base da cabeça) passou a seguir 100% o osso Head, com borda suave; a
    célula da boca virou 2:1 para o plano não chegar ao queixo;
  - manchas de pele dentro dos olhos: a grade de 16×8 fazia cordas por baixo da pele facetada; agora 48×24
    (olhos) e 24×12 (boca);
  - a touca dos cabelos aparecia na frente dos planos: `fit_hair.py` abre o rosto pela oval que envolve os
    planos Olhos e Boca; os 5 cabelos foram reencaixados.
- **Conferido (`check_face_mask.py`):** em idle, walk, carry, work e sleep, olhos entre +0,02 e +1,0 mm da
  pele (o mais perto é a borda nas têmporas) e boca entre +0,93 e +1,0 mm: nenhum atravessa.
- **Jogo (`VillagerVisual`, a pedido anterior de testar na Biografia):** acha os planos "Olhos" e "Boca" e
  troca a célula de cada um pelo `uv1_offset` (olhos 1/3 × 1/3, boca 1/3 × 1/2). Mapa expressão → (olhos,
  boca): distraído (distraído, entreaberta), esforço (esforço, esforço), feliz (feliz, sorriso), sonolento
  (sonolento, neutra), dormindo (fechado, entreaberta), espantado (espantado, "o"), preocupado (preocupado,
  triste), chorando (chorando, triste), bravo (bravo, neutra). Modelos antigos continuam com o "Rosto".
  `dotnet build` 0 erros e 0 avisos; `dotnet test` 94 aprovados.
- **Prévia:** `assets/previews/rosto_v3.png` (as 9 combinações no modelo, de frente e a 55°, renderizada no
  Godot com SubViewport).
- **Atenção:** a 55° (câmera do jogo) a franja cobre a metade de cima dos olhos; a expressão lê pela boca e
  pela parte de baixo dos olhos. Se precisar ler melhor de cima, dá para descer um pouco os olhos ou
  encurtar a franja no encaixe.
- **Créditos:** 0.
- **Correções manuais:** nenhuma.

## 2026-09-27 — Aldeão: acabamento do corpo-base (pele, sombreado, couro cabeludo, queixo) e encaixe dos cabelos

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** 1) pele de cor única azul-pálida fosca, com degradê suave e oclusão leve, sem o remendo do rosto
  apagado; 2) normais suaves na cabeça e no corpo, sem facetas; 3) couro cabeludo pintado na cor escura do
  cabelo, com borda suave na testa; 4) cabelos justos na cabeça (sem vãos, franja na testa, sem cobrir os
  olhos); 5) tirar o caco pontudo do queixo. Prévia de frente, 3/4 e costas com os 5 cabelos.
- **Feito (`finish_skin` no `normalize.py`, config `acabamento_pele` no `assets.json`):**
  - funde vértices duplicados e subdivide só a cabeça (1 corte, suave); alisamento Taubin (24 passos, raio
    0,6 da cabeça) em volta do rosto, o que também some com o caco do queixo (sobra do tampão do rosto);
  - todas as faces suaves, sem arestas marcadas como duras;
  - cor por vértice: pele #9FB7CB × degradê de altura (12%) × oclusão (48 raios no hemisfério, força 0,35);
    acima da linha do cabelo (70% da cabeça na testa, 12% na nuca, borda suave de 8%, orelhas fora) mistura
    para #4B5A69; as cores são suavizadas entre vizinhos (6 vezes);
  - **o Godot ignora a cor de vértice do glTF** (`vertex_color_use_as_albedo` falso na importação), então a cor
    é assada numa textura de 1024 com UV nova (smart project), com 8 px de sangria. A textura antiga da Meshy
    (e o remendo do rosto) sai do material.
- **Cabelos (`fit_hair.py`):** o campo de inflar agora também puxa para dentro: a camada interna mais perto
  de cada direção vai para superfície + 1,5 mm (puxa até 2 cm, empurra até 8 cm), com a cortina de longe
  atenuada. Os 5 cabelos foram reencaixados na cabeça final.
- **Problemas e correções:**
  - rosto manchado: a oclusão com poucos raios fazia ruído; subiu para 48 raios e as cores passaram a ser
    suavizadas. O relevo que sobrava era da geometria, daí o alisamento mais forte;
  - com o alisamento mais forte, 1 vértice da borda do plano dos olhos (na têmpora, área transparente)
    encostou na pele (0,00 mm): numa concavidade, outra face ficava mais perto que a do raio. Agora cada
    ponto do plano garante a folga pelo ponto mais próximo da pele.
- **Conferido (`check_face_mask.py`):** em idle, walk, carry, work e sleep, olhos de +0,73 a +1,0 mm e boca de
  +0,98 a +1,0 mm da pele.
- **Prévia:** `assets/previews/aldeoes_acabamento.png` (Godot, SubViewport, câmera ortogonal perto).
- **O que ainda não ficou bom:** os cabelos da Meshy são cheios de mechas soltas; o ondulado deixa ver a
  touca na nuca e o longo_liso tem manchas da touca nas costas; no rabo_cavalo, a 3/4, uma mecha passa na
  frente da bochecha. O olho de trás, a 3/4, fica cortado pela silhueta da cabeça (é plano curvo na pele).
- **Créditos:** 0.
- **Correções manuais:** nenhuma.

---

## 2026-09-29 — Aldeão v2: preparação (merge, GDD, lista de remoção do v1 e plano do pipeline)

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`, sessão nova.
- **Pedido:** 1) `git merge master`, reexportar o GDD vivo e ler `docs/ESTADO_DO_PROJETO.md`; 2) listar (sem apagar)
  tudo do aldeão antigo na branch `arte`, separando as ferramentas genéricas do pipeline; 3) preparar o pipeline
  para o aldeão v2 (folhas técnicas: corpo careca sem rosto + 5 perucas em `assets/conceitos/aldeao_v2/`) com
  passo a passo e custo, sem gerar nada.
- **O que o repositório mostrava (diferente do pedido):**
  - `master` e `arte` estão no mesmo commit (`89736ff`): o merge não trouxe nada. Não existe a tag
    `aldeao-v1-arquivado` nem o arquivo `docs/ESTADO_DO_PROJETO.md`; o checkout principal só tem `.import`
    modificados. Ou o outro agente ainda não commitou, ou trabalhou em outra cópia.
  - Criei a tag `aldeao-v1-arquivado` em `89736ff` (o último estado com o aldeão v1 inteiro) para servir de
    arquivo antes da remoção. Se o outro agente criar a dele, uma das duas some.
  - O código do jogo ainda usa o aldeão v1: `src/View/VillagerVisual.cs` (`assets/modelos/aldeao_base/`),
    `src/View/VillagerLooks.cs` (`assets/modelos/aldeao_cabelos/`, `assets/texturas/aldeao/expressoes.png`),
    `data/villager_looks.json`, `data/head_pieces.json` e `data/biography.json`. Apagar os assets sem a mudança de
    código deixa o aldeão sem modelo no jogo; a remoção só deve ir para a `master` junto com essa mudança, ou o v2
    deve manter os mesmos caminhos (recomendado, ver plano).
- **GDD:** exportado do Claude Docs (rev 89, 68 KB): idêntico ao `docs/GDD.md` local, só a data do cabeçalho mudou.
  Nada no GDD fala do v2 ainda; a direção de arte do aldeão continua a de "Aldeão: implementação v1".
- **Lista de remoção do aldeão v1 (aguardando aprovação; nada foi apagado):**
  - Conceitos: `assets/conceitos/aldeao/` inteira (folha, careca, cabelos, expressões e `vistas/` com 12 recortes).
  - Modelos: `assets/modelos/aldeao_base/`, `aldeao_cabelos/`, `aldeao_curto_baguncado/`, `aldeao_medio_franja/`,
    `aldeao_ondulado/`, `aldeao_longo_liso/`, `aldeao_rabo_cavalo/` (GLB, JSON, texturas e `.import`). As pastas
    `bruto/` dentro delas (~125 MB) estão fora do git: a tag não as guarda; os brutos da Meshy expiram em 3 dias lá.
  - Texturas: `assets/texturas/aldeao/expressoes.png` (atlas recortado do conceito, substituído pelos planos).
  - Prévias: `assets/previews/aldeao_expressoes.png`, `aldeoes.png`, `aldeoes_modular.png`, `aldeoes_correcao.png`,
    `aldeoes_correcao2.png`, `aldeoes_acabamento.png`, `expressoes_tracos.png`, `rosto_v3.png`.
  - Ferramentas só do v1: `tools/meshy_pipeline/villager_views.py` (recortes das 5 variações do conceito),
    `villager_faces.py` (atlas de expressões do conceito), `hair_pieces.py` (perucas por Image to Image: as folhas
    novas já trazem as perucas prontas), `tools/blender/extract_hair.py` (cabelo recortado das variações,
    substituído pelas perucas); estado `hair_state.json` e as entradas `aldeao_*` do `state.json` (fora do git).
  - `tools/assets.json`: as 6 entradas `aldeao_base`, `aldeao_curto_baguncado`, `aldeao_medio_franja`,
    `aldeao_ondulado`, `aldeao_longo_liso`, `aldeao_rabo_cavalo` e a parte do `_comentario` sobre o v1.
- **O que fica (genérico ou reaproveitável no v2):**
  - Meshy: `pipeline.py` (gera, faz rig, anima, baixa), `textures.py`, `crop_concept.py` (recorte de vistas),
    `compare_sheet.py`, `label_sheet.py`, `face_sprites.py` (folhas de olhos e bocas por código, 0 créditos) e as
    folhas `assets/texturas/aldeao/olhos.*` e `bocas.*` que ele gera.
  - Blender: `normalize.py` (as funções do aldeão, como `finish_skin`, `add_face_planes`, `measure_head_top`,
    `carry_from_walk` e `crank_work`, só rodam quando o asset tem a chave no JSON: o v2 vai usá-las), `fit_hair.py`
    (encaixe de peruca no corpo-base), `check_face_mask.py`, `preview_modular.py`, `preview_sheet.py`,
    `render_views.py`, `inspect_clip.py`, `floor_plates.py`.
  - Separação proposta (sem mover nada ainda): os três de cabeça (`fit_hair.py`, `check_face_mask.py`,
    `preview_modular.py`) e o `face_sprites.py` são "personagem modular", não "aldeão v1"; ganham caminhos por
    parâmetro (hoje `aldeao_base` e `aldeao_cabelos` estão fixos neles) na primeira tarefa do v2.
- **Plano do pipeline do v2 (0 créditos até o passo 3):**
  1. Folhas em `assets/conceitos/aldeao_v2/` (o que colocar está no `LEIAME.md` da pasta). Se vierem com várias
     vistas por página, recorte por script em `vistas/`.
  2. `tools/assets.json`: entrada `aldeao_base` nova (mesmas chaves do v1 que continuam valendo: altura 0,4 m,
     rig a 1,0 m, sleep da biblioteca, walk do rig, idle/carry/work no Blender, `planos_rosto`, `nos_cabeca`;
     `apagar_rosto` sai, porque o corpo já vem sem rosto; `acabamento_pele` só se a textura da Meshy não vier
     chapada) e um tipo novo `peca` no `pipeline.py` para as 5 perucas (Multi-Image to 3D sem rig nem animação,
     brutos em `assets/modelos/aldeao_cabelos/bruto/`), no lugar do `hair_pieces.py`.
  3. Corpo: `pipeline.py --run --only aldeao_base` → `normalize.py aldeao_base` → `inspect_clip.py` e
     `render_views.py` + `compare_sheet.py` contra as folhas. Aprovação do corpo antes das perucas.
  4. Perucas: `pipeline.py --run --only cabelo_*` → `fit_hair.py` por variação → `preview_modular.py` (5 cabelos a
     55°) e `check_face_mask.py`.
  5. Conferência no jogo pela Biografia (screenshot) e diário. Mantendo os nomes `aldeao_base` e
     `aldeao_cabelos/<var>.glb`, o agente de código não precisa mudar nada.
- **Custo estimado (médias medidas no `state.json`: Multi-Image to 3D 30, rig 5, animação 3 por clipe):**
  corpo 38 créditos; 5 perucas 150; total 188. Com uma nova tentativa do corpo e duas de peruca, 286.
  Proposta de `limite_creditos`: 300. As folhas prontas dispensam o Image to Image do v1 (60 créditos a menos).
  O saldo atual não foi lido: a chave da Meshy fica no `.env` do checkout principal e a leitura foi barrada nesta
  sessão.
- **Feito neste commit:** tag, cabeçalho do GDD, `assets/conceitos/aldeao_v2/LEIAME.md`, esta entrada.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~50 min.

## 2026-09-29 — Aldeão v2: contrato arte × jogo recebido e plano do pipeline revisado

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** o Arthur trouxe o "Contrato aldeão v2" (interface entre arte e jogo). Guardado inteiro em
  `assets/modelos/aldeao_v2/CONTRATO.md`; o `LEIAME.md` das folhas foi alinhado a ele (perucas `cabelo_1..5`).
- **O que muda no plano da entrada anterior:**
  - caminhos novos: `assets/modelos/aldeao_v2/aldeao_corpo.glb`, `cabelos/cabelo_N.glb`, `rosto/olhos.png`,
    `boca.png`, `rosto.json`. Os caminhos do v1 não são mais reaproveitados: o agente de código muda o jogo para
    eles, então a remoção do v1 pode ir junto com essa mudança;
  - corpo e cabelos em **cor chapada, sem textura**: a Meshy sai em "mesh only" (20 créditos em vez de 30, tabela
    da API lida em 29/09/2026). Saem do pipeline `acabamento_pele`, `apagar_rosto` e a textura assada do v1;
  - o jogo cria os encaixes ("Cabelo", "Chapéu", "Peito"): saem `nos_cabeca` e o campo `encaixes` do JSON; os
    cabelos são exportados no espaço do corpo em pose de repouso, sem armature e sem pesos (o `fit_hair.py` hoje
    move a origem para o encaixe e exporta com o rig; muda);
  - limites de triângulos: corpo ≤ 2.500 (pedir `polycount` 2500 à Meshy e conferir; decimar se passar),
    cabelo ≤ 800 (a Meshy entrega ~3.000: decimar no Blender no `fit_hair.py`);
  - materiais com nome fixo: "pele" (corpo), "cabelo" (perucas), "rosto_olhos" e "rosto_boca" (retalhos);
  - retalhos "Olhos" e "Boca" com UV 0..1 na célula (no v1 a UV ficava na célula 1 e o jogo deslocava) e proporção
    igual à da célula: as folhas do v1 já são 2:1 (512×256 e 256×128), então os retalhos continuam 2:1;
  - `rosto.json` novo (formato do contrato): a parte do atlas (`colunas`, `linhas`, `celulaPx`, `margemPx`,
    `quadros`) vem do `face_sprites.py`, e `ossoCabeca` e `passadaWalk` vêm do `normalize.py`. No rig da Meshy o
    osso da cabeça se chama "Head" (conferido no GLB do v1);
  - clipes idle, walk, carry, work e sleep, todos em loop.
- **Mudanças de ferramenta a fazer quando as folhas chegarem (todas 0 créditos):**
  1. `pipeline.py`: campo `textura: false` por asset (`should_texture` falso), tipo `peca` (só Multi-Image to 3D,
     sem rig nem animação) e pasta de saída por asset (`aldeao_v2/`, `aldeao_v2/cabelos/bruto/`).
  2. `face_sprites.py`: saída em `assets/modelos/aldeao_v2/rosto/` (`olhos.png`, `boca.png`), margem transparente
     ≥ 8 px conferida por célula, e escrita da parte do atlas no `rosto.json`. Quadro 0 (padrão): olhos
     "distraido", boca "entreaberta" (o par padrão do v1); os outros na ordem do v1.
  3. `normalize.py`: modo "contrato v2" para o corpo: material único "pele" chapado, retalhos com UV 0..1 e
     materiais nomeados, sem encaixes, clipes em loop, `rosto.json` completado.
  4. `fit_hair.py`: encaixe na cabeça do corpo v2 (abertura em volta do retalho "Olhos"), decimação a ≤ 800
     triângulos, material "cabelo", exportação rígida no espaço do corpo.
  5. `check_face_mask.py` e `preview_modular.py`: caminhos do v2 por parâmetro; a prévia prende o cabelo ao osso
     "Head" compensando a pose de repouso, como o jogo.
- **Custo revisado (tabela de preços da API da Meshy, 29/09/2026):**
  corpo: Multi-Image to 3D só malha 20 + rig 5 + sleep 3 = 28; 5 perucas só malha: 100; total 128.
  Com uma nova tentativa do corpo e duas de peruca: 196. Proposta de `limite_creditos`: 200.
- **Pontos que assumi (avisar se for diferente):** o loop dos clipes vai marcado no GLB pelo sufixo `-loop` no
  nome (o Godot tira o sufixo e importa o clipe em loop; no v1 o loop ficava por conta do jogo); o quadro 0 dos
  atlas é o par distraído/entreaberta; a altura 0,40 m é conferida na prévia lado a lado com a protagonista.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~20 min.

## 2026-09-29 — Aldeão v2, partes A e B: estrutura, preparador de vistas e atlas de expressões

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`. Território: `assets/` e
  `tools/arte/`; nada em `src/`, `scenes/` ou `data/`.
- **Pedido:** ler o contrato oficial (`git show master:docs/aldeao_v2_contrato.md`, sem merge) e comparar com os
  três pontos assumidos ontem; criar a estrutura do v2 com um preparador de vistas (Parte A); gerar o atlas de
  expressões no formato do contrato, com prévia e mapa expressão → quadros (Parte B); parar antes da Meshy
  (Parte C). Reaproveitar o que servir dos scripts do v1 na tag `aldeao-v1-arquivado`.
- **Contrato oficial × o que eu tinha:** o texto é o mesmo que guardei ontem; a cópia em
  `assets/modelos/aldeao_v2/CONTRATO.md` saiu (a oficial é a da `master`). Dos três pontos assumidos: o contrato
  não diz como o loop é marcado (sigo com o sufixo `-loop` no GLB até ordem contrária); o quadro 0 é o padrão e
  passa a ser `aberto` / `entreaberta` (nomes do pedido, não os do v1); a altura 0,40 m é conferida lado a lado
  com a protagonista. Nada muda.
- **Estado da `master` (só lido):** o aldeão v1 foi removido inteiro no commit `edc1291` (116 arquivos em
  `assets/`, 8 scripts em `tools/`, código, dados e testes); `docs/ESTADO_DO_PROJETO.md` existe e pede que o
  modelo seja julgado na câmera do jogo desde a primeira versão. Na `arte` os arquivos do v1 ainda estão; no
  próximo merge da `master` o git os apaga sozinho (ninguém os mudou aqui).
- **Meshy (docs.meshy.ai, lidos em 29/09/2026), para a Parte C:** `POST /openapi/v1/image-to-3d` e
  `/openapi/v1/multi-image-to-3d` (1 a 4 imagens, a primeira é a frente). Parâmetros: `should_texture: false`
  (20 créditos em vez de 30), `pose_mode: "a-pose"` (ou `t-pose`), `should_remesh: true` + `topology: "triangle"`
  + `target_polycount` (100 a 300.000; 2.500 para o corpo, 800 para as perucas), `symmetry_mode: "auto"`,
  `ai_model: "latest"`. O GLB vem em `model_urls.glb` da tarefa concluída.
- **Parte A (`a35365a`):** pastas `assets/conceitos/aldeao_v2/{folhas,vistas}/`, `assets/modelos/aldeao_v2/`,
  `tools/arte/aldeao_v2/` com projeto uv próprio (`tools/arte/pyproject.toml`). `preparar_vistas.py` (reaproveita
  a ideia do `crop_concept.py` do v1, sem as correções manuais dele): fundo = cor mais comum da folha; figura =
  região que difere do fundo, com abertura para sumir linhas finas; descarta o que encosta na borda, molduras
  (região do tamanho da folha) e regiões pequenas (textos, setas); ordem de leitura; cada figura centrada num
  quadrado de 1024 px com 8% de margem e fundo #EBEBEB, mesma escala por folha; prévia por folha.
  Testado nas folhas antigas: na do aldeão v1 acha 5 figuras (cabeças, T-pose frente e costas, manivela) e o
  `--vistas frente:3,costas:4` escolhe as certas; na da protagonista, com fundo desenhado, só funciona com
  `--recorte` da região dos bonecos. As folhas do ChatGPT devem vir com fundo liso, então o caso normal é o
  simples.
- **Parte B:** `desenhar_rosto.py` desenha com o Pillow em 4x e reduz (LANCZOS), fundo transparente, e confere
  que nenhum quadro invade a margem de 16 px. Olhos 3×3 de 512×256 (2:1): aberto (0), fechado, meio_fechado,
  arregalado, feliz, apertado, preocupado, bravo, lagrima. Boca 4×2 de 256×128 (2:1, última célula vazia):
  entreaberta (0), sorriso, o, tensa, triste, brava, dormindo. Olhos desalinhados de propósito (o direito menor e
  8 px mais alto) e pupilas divergentes no `aberto`; brilho da pupila em #EDE6D6; traço #1B1E26 de 6 px;
  sobrancelhas finas em todos os quadros (sem elas preocupado e bravo não leem). `rosto.json` no formato do
  contrato, com `ossoCabeca` e `passadaWalk` vazios até o corpo existir, e a chave extra `expressoes`
  (proposta, fora do contrato): distraido = aberto + entreaberta, esforco = apertado + tensa, feliz = feliz +
  sorriso, sonolento = meio_fechado + entreaberta, dormindo = fechado + dormindo, espantado = arregalado + o,
  preocupado = preocupado + triste, chorando = lagrima + triste, bravo = bravo + brava.
  Prévia: `assets/previews/aldeao_v2/expressoes.png` (as 9 sobre um círculo cor de pele #9FB7CB).
- **O que deu errado:** `bincount` estourou com `uint8` (corrigido com `int64`); o fundo pela mediana da moldura
  falhava em pergaminho (trocado pela cor mais comum); a vinheta do pergaminho virava uma "figura" do tamanho da
  folha (regra da moldura); rótulos da prévia se sobrepunham (duas linhas).
- **Créditos:** 0. **Gerações na Meshy:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h 10.

## 2026-09-29 — Aldeão v2: estudo de direção do rosto (A Olheiras, B Vazio, C Tinta)

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** a prévia das expressões ficou infantil (emoji). Antes de refazer o atlas, escolher uma direção:
  três direções × três expressões (distraído, feliz, bravo), sobre pele #AEBFD3, em 256 px e 48 px, mais uma
  linha escurecida pelo crepúsculo (× #6A5B7C). Regras: sem sobrancelhas, emoção pelas pálpebras e pupilas,
  assimetria sempre, traço de tinta à mão em #1B1620, boca pequena e torta com interior escuro. Sem mudar o
  atlas, o `rosto.json` nem os nomes dos quadros.
- **Feito:** `tools/arte/aldeao_v2/estudo_rosto.py` (separado do `desenhar_rosto.py`), prévia em
  `assets/previews/aldeao_v2/estudo_rosto.png`. Traço de tinta: discos ao longo do caminho com raio e desvio
  lateral por ruído suave (soma de senos), espessura variável e leve irregularidade. Pálpebras: máscara de alfa
  recortada por uma curva que vai de borda a borda do olho, com inclinação e curvatura por expressão; a borda em
  tinta. Olhos assimétricos (o da direita menor e 7 px mais alto), pupilas apontando para lugares diferentes.
  A: esclera branco osso, pupila pequena, pálpebra superior cobrindo 1/3 no padrão, olheira #2B2140
  semitransparente desfocada. B: oval escuro sem esclera com um brilho fora de centro (posição diferente em cada
  olho); as pálpebras recortam o oval. C: contorno rabiscado em dois traços, sem esclera pintada (a pele aparece
  dentro), pupilas de tamanhos diferentes; a espiral do atordoado não entrou porque não há quadro atordoado no
  estudo. Bocas comuns: oval torto fora de centro (distraído), abertura fina com um canto subindo (feliz),
  abertura torta com três dentinhos tortos (bravo).
- **Problemas e correções:** a curva da pálpebra passava da borda do olho e deixava ganchos nas pontas (corrigido:
  a curva termina na elipse do olho, na altura do corte); no feliz, a pálpebra de cima curvada para baixo e a de
  baixo para cima faziam gravata-borboleta (a de cima ficou quase reta); a olheira estava grande demais (menor e
  mais desfocada).
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~35 min.

## 2026-09-29 — Aldeão v2: estudo 2 do rosto, quatro variações da direção A (mais adulto e mais triste)

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** o estudo 1 lembrou Roblox (olhos colados como adesivos, boca em ponto ou tracinho). Seguir da
  direção A (olheiras) com olho afundado: linha forte só na pálpebra de cima (grossa no meio, afinando nas
  pontas), pálpebra de baixo quase sem linha, esclera branco osso com a sombra da pálpebra no alto, tristeza como
  padrão (cantos externos caídos, pálpebra mais pesada por fora, pupilas para baixo e para o lado), olheiras mais
  fortes com borda definida por dentro e desfoque só por fora, cobrindo a bolsa; olhos mais afastados e mais
  baixos; boca só uma dobra fina no padrão. Quatro variações (A1 Fundos, A2 Caídos, A3 Sem boca, A4 Vidrados) ×
  quatro expressões (distraído, feliz como alívio cansado, bravo, chorando com risco escuro). O texto do pedido
  chegou cortado em "PRÉVIA: Não use fundo"; assumi "sem fundo chapado atrás do rosto" e desenhei cada rosto
  sobre uma cabeça oval com volume suave; 256 px e 48 px; linha de crepúsculo (× #6A5B7C).
- **Feito:** `tools/arte/aldeao_v2/estudo_rosto_a.py` (reusa o traço de tinta e o ruído do `estudo_rosto.py`),
  prévia em `assets/previews/aldeao_v2/estudo_rosto_a.png`. O olho é uma forma com canto de dentro e canto de
  fora caído (dois arcos); a pálpebra de cima é uma curva que cobre uma fração diferente em cada canto (mais por
  fora no padrão; mais por dentro no bravo); a linha dos cílios tem espessura por função (seno elevado a 0,55,
  mais pesada por fora); a pálpebra de baixo é um traço de 1 px a 37% de opacidade; a cavidade é uma faixa
  desfocada da cor da esclera misturada com o roxo, presa à esclera; a olheira é uma elipse com alfa parcial
  (borda nítida) mais um crescente de bolsa, e o desfoque é somado só por fora (máximo entre nítido e desfocado);
  a lágrima é um risco quase reto em #2B2140 afinando para baixo. A4 tem a linha de umidade clara na pálpebra
  de baixo e pupila pequena; A3 não tem boca no distraído nem no feliz.
- **Problemas e correções:** a primeira olheira era um bloco sólido, quase uma máscara (alfa menor, região
  nítida menor, bolsa como crescente em vez de elipse cheia); o risco da lágrima serpenteava (ondulação de 2,5 px
  para 0,7 px, mais comprido e quase vertical).
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~45 min.

## 2026-09-29 — Aldeão v2: atlas de expressões na direção A1 "Fundos" (aprovada), com três prévias

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** direção A1 aprovada; refazer o atlas inteiro nesse estilo com metas de silhueta por expressão
  (reconhecível a 48 px só pelas pálpebras e olheira), boca como variações da dobra fina (dentinhos com traço
  fino, nada de bloco preto), sombreado sem direção de luz, célula dos olhos contendo a olheira inteira com
  desfoque, bordas em alfa suave. Entregar `olhos.png`, `boca.png`, `rosto.json` (formato do contrato, mapa das 9)
  e três prévias; nomes de quadros mantidos.
- **Feito (`tools/arte/aldeao_v2/desenhar_rosto.py`, reescrito):** desenho em 6x num rosto de referência de 256 px
  e recorte de duas janelas: olhos (24, 78)–(232, 208) → célula **512×320** (8:5; a de 2:1 não cabia a olheira
  com desfoque nem a lágrima), boca (110, 170)–(174, 202) → célula 256×128 (2:1). Margem de 16 px conferida por
  célula (a lágrima estourou na primeira rodada; encurtada para 40 px). Olhos 3×3, boca 4×2. Silhuetas: aberto
  cobre 1/3 (mais por fora); meio_fechado 2/3 com a pupila meio escondida; fechado só a linha dos cílios grossa
  curvada para baixo; feliz com a pálpebra de baixo subindo 44% e a de cima leve (meia-lua deitada, linha de
  baixo mais forte para a silhueta); bravo reta e dura cobrindo metade, inclinada para o nariz; arregalado com
  o olho redondo (forma própria) e pupilas de 3 px; preocupado reto, canto interno mais alto, pálpebra de baixo
  um pouco erguida; apertado com as duas pálpebras fechando numa fenda; lagrima = preocupado + risco grosso
  (6,5 px afinando, #2B2140 com miolo em tinta) da olheira até a bochecha, mais curto no outro olho. Bocas: dobra
  fina fraca (entreaberta), dobra alongada com um canto subindo (sorriso), oval pequeno torto com o interior
  escuro (o), dobra apertada com três dentinhos de traço fino (tensa), dobra funda com cantos para baixo
  (triste), dobra entreaberta escura com dentinhos (brava), dobra frouxa com um respiro escuro (dormindo).
  As prévias montam o rosto a partir das CÉLULAS do atlas (não do desenho direto), então conferem o recorte.
- **rosto.json:** `olhos` 3×3 de [512, 320], `boca` 4×2 de [256, 128], `margemPx` 16, quadros com os índices
  já definidos, `ossoCabeca` e `passadaWalk` vazios até o corpo, `expressoes` com as 9 (chave extra proposta).
  As janelas do rosto (onde cada retalho fica na cabeça) estão no script, para o passo dos planos do corpo.
- **Prévias:** `assets/previews/aldeao_v2/expressoes.png` (9 sobre a esfera, 256 e 48 px),
  `expressoes_48px_crepusculo.png` (9 a 48 px × #6A5B7C, sem legenda), `piscar.png` (aberto → meio_fechado →
  fechado → meio_fechado → aberto).
- **O que ainda pode confundir a 48 px:** esforço, sonolento e bravo são três fendas; a diferença é a posição da
  fenda (meio, baixo, inclinada). Preocupado e chorando só se distinguem pelo risco da lágrima, de propósito.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h.

## 2026-09-29 — Aldeão v2: ajuste de bravo, preocupado e feliz pelo ângulo e abertura do olho

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** estilo aprovado, com 6 das 9 expressões e o piscar. No teste a 48 px no crepúsculo, bravo,
  preocupado e feliz viravam a fenda do sonolento. Ajustar só esses três pelo ângulo e pela abertura (bravo:
  linha reta e grossa a ~20° descendo para o nariz, cortando o topo da pupila, pupilas no canto interno, os dois
  olhos formando um V achatado; preocupado: só 1/4 coberto, inclinação contrária, V invertido, pupilas para cima
  e para o lado; feliz: pálpebra de cima quase aberta e a de baixo subindo em curva bem convexa, meia-lua); boca
  do espantado menor. Refazer a tira de 48 px e o atlas final com o `rosto.json`.
- **Causa:** a pálpebra "reta" do atlas anterior era uma reta entre os dois cantos do olho, então a inclinação
  vinha só da queda do canto externo (7 px) e não dava para controlar o ângulo.
- **Feito (`desenhar_rosto.py`):** pálpebra reta nova definida por altura no centro e ângulo, estendida além do
  olho e recortada pela forma dele (teste de ponto no polígono); a máscara é a forma com o piso multiplicada pelo
  "abaixo da linha"; a linha dos cílios sem afinar por fora (peso igual). Bravo: 44% no centro, +20°, pupilas a
  9 px para dentro, linha 5,4 px. Preocupado: 25%, -18°, pupilas (5, -6) e (2, -7), pálpebra de baixo erguida
  10%. Feliz: pálpebra de cima 6 a 10%, a de baixo sobe 52% com perfil convexo (seno^0,9) e linha de 2 px a 90%
  de opacidade. Boca do espantado: oval de 11×8 px em vez de 16×11. Chorando manteve a silhueta anterior, como
  aprovado. Todas as prévias foram regeradas pelo mesmo script (a tira de 48 px é a que importa).
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~25 min.

## 2026-09-29 — Aldeão v2: folhas do ChatGPT (passos 0 a 3); Meshy travada por falta da chave

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** passo 0, comparação antes/depois de feliz, preocupado e bravo a 96 px no crepúsculo; passo 1,
  identificar e renomear as 6 folhas (nomes `exec-*`) e relatar vistas, problemas para a Meshy, franja sobre o
  retalho "Olhos" e diferença de cabeça; passo 2, preparador no corpo, Meshy (só-frente × multi-imagem, sem
  textura, pose A, 2.500 triângulos, até 6 gerações) e folha de contato com a área dos retalhos marcada; passo 3,
  preparador nos cabelos e `PLANO_CABELOS.md`.
- **Onde estavam as folhas:** não em `assets/conceitos/aldeao_v2/folhas/` do worktree, mas em `assets/previews/`
  do checkout principal (`Projetos/cidadela`). Copiadas para a pasta certa e renomeadas pelo conteúdo (conferido
  olhando cada imagem): `aldeao_corpo_folha` (3 vistas), `cabelo_1_curto_baguncado` (mechas em folha),
  `cabelo_2_medio_franja_lado` (chanel, franja para um lado), `cabelo_3_ondulado` (volumoso até o queixo),
  `cabelo_4_longo_liso` (liso até os ombros, repartido no meio), `cabelo_5_rabo_de_cavalo` (cor da pele).
- **Passo 0 (`b6bbb1f`):** `comparar_ajuste.py` monta antes (atlas do commit `46195ba`) × depois a 96 px ×
  #6A5B7C: `assets/previews/aldeao_v2/comparacao_ajuste.png`.
- **Passo 1 (`3b74705`):** relatório no chat e resumido aqui. Corpo: frente, lado e costas consistentes, pose A,
  cabeça em ovo com 43% da altura (l/a 0,93; profundidade/altura 0,91), dobra pequena no peito perto do pescoço na
  frente (não retocada), na vista de lado a cabeça inclina um pouco para a frente. Cabelos: 4 vistas cada (a
  "lado" de 1, 2 e 3 é 3/4; de 4 e 5 é perfil), consistentes entre si; todas com cabeça, mais redonda que a do
  corpo (face visível l/a: 1 = 1,14; 2 = 1,11; 3 = 0,96; 4 = 0,95; 5 = 1,05). Franja sobre a janela dos olhos
  (28% a 83% da altura da cabeça): 2 e 3 invadem de um lado até ~50%; 4 invade só os cantos externos; 1 encosta
  no alto da janela; 5 livre. Folha 5 sem contraste cabelo/pele.
- **Passo 2 (este commit):** vistas do corpo em `assets/conceitos/aldeao_v2/vistas/` (prévia `_previa_aldeao_corpo_folha.png`).
  Ferramentas prontas: `meshy_corpo.py` (so_frente = Image to 3D; multi = Multi-Image com frente, lado, costas;
  `should_texture` falso, `pose_mode` a-pose, `should_remesh` + `target_polycount` 2500, trava de 6 gerações,
  estado fora do git), `render_corpo.py` (Blender headless: material chapado, frente, lado, 3/4, câmera do jogo
  e escala com a protagonista; mede a caixa da cabeça pelo pescoço e a lisura da área dos retalhos como desvio
  RMS/máximo de uma esfera ajustada) e `folha_contato.py` (monta a folha e marca as janelas dos olhos e da boca
  na frente). Testados no `aldeao_base.glb` do v1 como substituto (saída no scratchpad).
  **Não gerado:** a chave da Meshy não existe neste worktree (`tools/arte/.env` ou `tools/meshy_pipeline/.env`)
  nem no ambiente, e ler o `.env` do checkout principal foi barrado nesta sessão. Falta o humano copiar o
  arquivo; aí é `uv run meshy_corpo.py --run` e a folha de contato.
- **Passo 3 (commit seguinte):** vistas dos 5 cabelos em `vistas/` e `tools/arte/aldeao_v2/PLANO_CABELOS.md`
  (gerar cabeça + cabelo a 3.000; achar a cabeça por elipsoide ajustado ao rosto liso; classificar faces por
  distância; transformar o elipsoide da folha no da cabeça do corpo; empurrar para fora; abrir a janela dos
  olhos; decimar a ≤ 800 com orçamento por cabelo, o 1 em ~730; exportar rígido). Recomenda refazer a folha 5.
- **Créditos:** 0. **Gerações na Meshy:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h 40.

## 2026-09-29 — Aldeão v2, passo 2 concluído: corpo na Meshy (só-frente × multi-imagem) e folha de contato

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** com a chave copiada (ficou em `cidadela-arte/.env`, na raiz; `git check-ignore` confirma que `.env` é
  ignorado em qualquer pasta; o script passou a aceitar a raiz), gerar o corpo em duas entradas (até 6 gerações),
  renderizar e parar na folha de contato. Também: regra da franja no plano dos cabelos, restaurar os dois estudos
  do rosto apagados sem querer, e rodar o preparador na folha nova do rabo de cavalo.
- **Meshy (2 gerações, 40 créditos; saldo 2.458 → 2.418):** `so_frente` (Image to 3D com a frente) e `multi`
  (Multi-Image com frente, lado e costas), ambas `should_texture` falso, `pose_mode` a-pose, remesh em
  triângulos com `target_polycount` 2500, `symmetry_mode` auto, `ai_model` latest. As duas deram certo na
  primeira tentativa (~3 min cada). Brutos: `assets/conceitos/aldeao_v2/meshy/corpo_so_frente_1.glb` e
  `corpo_multi_1.glb` (~100 KB cada).
- **Folha de contato (`assets/previews/aldeao_v2/corpo_contato.png`):** por resultado, frente com as janelas dos
  retalhos marcadas (vermelho olhos, azul boca, cinza a caixa da cabeça), lado, 3/4, câmera do jogo a 55° e a
  frente com a protagonista ao lado em escala (aldeão a 0,40 m). Medidas (modelo escalado a 0,40 m):
  - so_frente: 2.611 triângulos; cabeça 154 × 178 mm (44% da altura); área dos olhos a 2,3 mm RMS de uma esfera
    ajustada, máximo 5,0 mm;
  - multi: 2.620 triângulos; cabeça 164 × 180 mm; área dos olhos 3,9 mm RMS, máximo 12,9 mm (tem uma ondulação);
  - a área da boca tem só 6 vértices nos dois (malha muito aberta ali), então a medida não vale; visualmente é
    lisa nos dois.
- **Leitura:** os dois passam de 2.500 triângulos (o remesh da Meshy não é exato): decimar na limpeza. O só-frente
  tem a cabeça mais lisa e mais próxima do ovo da folha; o multi respeita melhor a profundidade do corpo e a
  inclinação da cabeça da vista de lado, mas a dobra do peito perto do pescoço apareceu nele como uma área
  amassada (anotado para a limpeza), e a cabeça saiu maior e com a ondulação na testa. Nenhuma limpeza, rig ou
  animação feita.
- **Outros:** `PLANO_CABELOS.md` com a regra da franja (cobre no máximo a metade de cima de um olho; retalho
  "Olhos" não muda; folga mínima de 2 mm; nunca atravessa) e a nota da folha 5 refeita; `estudo_rosto.png` e
  `estudo_rosto_a.png` restaurados com `git checkout`; preparador rodado na folha nova do rabo de cavalo (cabelo
  escuro, 4 vistas consistentes; a "lado" é perfil).
- **Créditos:** 40. **Gerações na Meshy:** 2 de 6. **Correções manuais:** o humano copiou o `.env`. **Tempo:** ~40 min.

## 2026-09-29 — Aldeão v2, passo 4: limpeza do corpo escolhido (corpo_so_frente_1)

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** corpo só-frente escolhido (barriga redonda, rosto mais liso); sem gerar mais nada. Limpeza por script:
  escala 0,40 m, pés em y = 0, pivô entre os pés, frente +Z do glTF; simetria em X pelo lado melhor; alisar (meta
  na área dos olhos: RMS ≤ 1,5 mm e máximo ≤ 3 mm); corrigir a dobra do peito se aparecer; decimar a ≤ 2.500
  triângulos preservando as juntas; um material "pele". Folha de contato com sombreado suave.
- **Feito:** `tools/arte/aldeao_v2/corpo_lib.py` (funções comuns: importar, caixa da cabeça pelo pescoço,
  rugosidade do rosto, retalhos, cena) e `limpar_corpo.py`: malha única com duplicados fundidos; escala e pivô
  pelo contrato; simetria por bisseção em x = 0 + espelho com fusão (ficou o lado -x, o mais liso); cabeça
  subdividida uma vez e alisada por Taubin (λ 0,5, μ -0,53; 20 passos na cabeça, 6 no corpo, 25 extras na
  frente do peito abaixo do pescoço, onde a folha tinha a dobra); decimação por colapso com simetria e um grupo
  de vértices que segura ombros, cotovelos, quadris e joelhos (peso 0,12); material "pele" chapado; faces
  suaves. Saída: `assets/modelos/aldeao_v2/aldeao_corpo.glb` (ainda sem rig e sem retalhos) e
  `aldeao_corpo_limpeza.json`. `render_corpo.py` passou a usar a lib e a aceitar `suave`.
- **Métrica corrigida (importante para ler os números):** o "desvio de uma esfera" das folhas anteriores media o
  formato em ovo da cabeça, não o amassado (a janela dos olhos vai quase de orelha a orelha). A rugosidade agora
  é o desvio de um **elipsoide ajustado**. Com ela, a malha crua da Meshy já tinha RMS 0,48 mm e máximo 1,8 mm
  na área dos olhos: o aspecto de papel amassado das folhas anteriores era o **sombreado facetado** (faces
  planas), não a posição dos vértices. A limpeza terminou em RMS 0,54 mm e máximo 1,8 mm (dentro da meta), com
  2.424 triângulos, cabeça 155 × 180 mm, 244 triângulos na faixa dos joelhos. A dobra do peito não aparece.
- **Prévia:** `assets/previews/aldeao_v2/corpo_limpo_contato.png` (frente com as janelas, lado, 3/4, câmera do jogo,
  escala com a protagonista), sombreado suave.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~50 min.

## 2026-09-29 — Aldeão v2, passo 5: prova do rosto no corpo limpo (retalhos + atlas, câmera do jogo)

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** criar os retalhos "Olhos" e "Boca" na cabeça limpa, como no contrato, com o atlas final; renderizar
  as 9 expressões na câmera do jogo (55°) a 48 e 96 px de altura do aldeão, mais a linha de crepúsculo, em três
  variações: (a) janela atual, (b) janela dos olhos 10% mais alta, (c) cabeça inclinada 10° para cima na pose de
  repouso. Dizer qual lê melhor de cima. Sem rig nem animação.
- **Feito:** `face_patch` na `corpo_lib.py` (grade projetada na pele, 1,5 mm pela normal, UV 0..1, proporção da
  célula), `patch_material` (emissão + transparência pelo alfa do atlas, célula pelo nó Mapping), `prova_rosto.py`
  (Blender: 3 variações × 9 expressões, fundo transparente, 512 px) e `prova_rosto_folha.py` (montagem a 96 px,
  48 px e 48 px × #6A5B7C). Prévia: `assets/previews/aldeao_v2/prova_rosto.png`.
- **Problemas e correções:**
  - a janela dos olhos (97% da largura máxima da cabeça) cai fora da silhueta na altura dos olhos, onde o ovo é
    mais estreito: raios paralelos não achavam pele nos cantos. Raios convergentes de um ponto atrás da cabeça
    acharam, mas espremeram o retalho para metade da largura. Solução final: **projeção cilíndrica** em volta do
    eixo vertical da cabeça, cada coluna num ângulo até ±72° (corda igual à largura da janela): o retalho
    acompanha os lados da cabeça e toda coluna acha pele;
  - a primeira versão da variação c inclinou a cabeça para baixo (sinal da rotação); conferido pelo ponto mais à
    frente da cabeça, que agora sobe 10 mm.
- **Leitura (na folha):** de cima, a **c** lê melhor: a face vira para a câmera, os olhos ficam maiores e menos
  achatados. A **b** vem logo atrás: os olhos saem da base da silhueta e ficam no meio da área visível, sem mudar
  a postura. A **a** é a pior: os olhos ficam colados na borda de baixo da cabeça e a testa domina. A 48 px só o
  espantado (branco dos olhos) se distingue de longe em qualquer variação; a 96 px as nove leem nas três, com a
  c mais clara. A c fixa o queixo erguido na pose de repouso, o que muda o personagem; a b não muda nada.
  Sugestão: b, ou b com uns 5° de inclinação, se o queixo erguido agradar.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h.

## 2026-09-29 — Aldeão v2, passo 7: nova prova do rosto (tamanhos reais, janela por ângulo, olhos maiores, luz do jogo)

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** corpo limpo aprovado; variação b escolhida; a prova anterior deixou os olhos como fendas nas laterais
  (janela de 97% da largura, projeção até ±72°). Medir o tamanho real no jogo e usar na prova; janela dos olhos
  até ±35° e ±45° com a altura da b; olhos 30% maiores na célula; material fiel ao jogo; folha com as duas larguras
  (o texto do pedido chegou cortado no item 5; assumi: duas larguras × três zooms + linha de crepúsculo).
- **Tamanho real (`tools/arte/aldeao_v2/medir_zoom.py`):** a câmera do jogo (`CameraRig.cs`: perspectiva, FOV 45°
  vertical, inclinação 55°, 16 m no zoom 1, zoom 0,4 a 2,5) reproduzida no Blender em 3024×1890, medindo a
  caixa de pixels do modelo. Protagonista (GLB de 0,80 m): 28 / 68 / 179 px nos zooms 0,4 / 1 / 2,5. Aldeão de
  0,40 m: 19 / 44 / 112 px (medido direto; pela proporção 0,40/0,75 sobre a protagonista daria 15 / 36 / 95, mas
  a cabeça grande e a profundidade do corpo contam na caixa). Validação pelo godot-ai: o jogo abriu no menu
  (janela de 3840×2160), a captura em resolução cheia estourou o limite de 4 MB do MCP e a de 1024 px veio
  congelada com a janela em segundo plano; a medida usada é a do Blender, que é a mesma conta da câmera.
- **Atlas (`desenhar_rosto.py`):** olhos e olheiras 30% maiores (raios, pupilas, cílios) dentro da mesma célula,
  centros aproximados de 82/174 para 88/168 para caber com a olheira; rabo do desfoque cortado abaixo de 12/255;
  resíduo de 1 a 2 de alfa do LANCZOS na margem zerado. Formato do `rosto.json` e nomes dos quadros iguais.
- **Prova (`prova_rosto.py`, `prova_rosto_folha.py`):** `face_patch` aceita ângulo máximo: a largura vira a corda
  do ângulo e a altura segue a proporção 8:5 da célula, centrada na janela da b. Janela dos olhos: ±35° = 89 mm
  de largura; ±45° = 109 mm (antes: 146 mm a ±72°). Pele #AEBFD3 fosca (rugosidade 1, sem especular), sol frio
  fraco quase de cima, ambiente roxo-acinzentado; retalhos difusos com a mesma luz. Folha
  `assets/previews/aldeao_v2/prova_rosto_2.png`: 19, 44 e 112 px e 44 px × crepúsculo, para as duas larguras.
- **Leitura:** as duas tiram a cara de alienígena. A ±45° lê melhor a 44 px (olhos maiores e mais separados) e
  ainda fica inteira na frente do rosto; a ±35° junta os olhos demais. A 19 px nada lê em nenhuma. Sugestão: ±45°.
- **Créditos:** 0 nesta parte (o rig está no passo 6). **Correções manuais:** nenhuma. **Tempo:** ~1 h 20.

## 2026-09-29 — Aldeão v2, passo 6: rig da Meshy e dois clipes (idle-loop, run-loop) no corpo limpo

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** rig do Meshy no `aldeao_corpo.glb` aprovado (parar se rig + 2 animações passassem de 50 créditos);
  só idle e run, em loop com o sufixo `-loop`; run = corridinha desajeitada de passos curtos, a mais curta e
  pesada da biblioteca; registrar `ossoCabeca`, `ossoPeito` e `passadaRun` no `rosto.json`; sem os retalhos.
- **Preço (docs.meshy.ai):** rig 5, animação 3 por ação → 11 créditos previstos e gastos (saldo 2.418 → 2.407).
- **Biblioteca (`GET /openapi/v1/animations/library`, 678 ações, grátis):** candidatos de corrida vistos pelos
  GIFs de prévia (`preview_url`): Run_02 (23 quadros), Run_03 (25), RunFast (15), Lean_Forward_Sprint (16),
  Male_Head_Down_Charge (14), Quick_Walk, Skip_Forward, Unsteady_Walk, Penguin_walk (andares). Escolhido
  **512 Male_Head_Down_Charge**: o ciclo mais curto (14 quadros, 0,53 s) e o mais pesado (cabeça baixa, braços
  bombeando). Idle: **0 Idle** (4 s). Alternativa se a investida parecer exagerada: Run_02 por mais 3 créditos.
- **O que deu errado no rig:** `POST /v1/rigging` com `model_url` = data URI do GLB limpo respondeu 422 "Pose
  estimation failed" duas vezes (a 0,40 m e numa cópia a 1,0 m), sem cobrar. Saída: rig sobre a tarefa original
  da Meshy (`input_task_id` de corpo_so_frente_1, `height_meters` 1,0), como o v1 fazia, e **transferência de
  pesos** para a malha limpa no Blender (`montar_rig.py`: Data Transfer por face mais próxima, grupos por nome,
  0 vértices sem peso; a malha crua com rig e a limpa coincidem em < 0,5 mm na caixa).
- **Clipes:** a investida tem deslocamento de raiz (o quadril avança 0,785 m/s); tirei o avanço horizontal do
  quadril quadro a quadro (reta ajustada, balanço vertical mantido), e a **velocidade da raiz original virou a
  `passadaRun` = 0,785 m/s** (a medida pelos pés, método do v1, dá 0,502 m/s porque os pés deslizam na captura;
  fica registrada no `aldeao_corpo_rig.json`). Loop: idle fecha (0,6 cm somados em 5 ossos); run fecha a 9,3 cm
  somados (~2 cm por osso), aceitável para 13 quadros. Nomes: `idle-loop` e `run-loop`.
- **Exportação (duas armadilhas do Blender 5.1):** em modo ACTIONS as ações com slot saíam com 2 quadros
  constantes; em modo NLA_TRACKS (uma faixa por clipe, `action_slot` na strip, sem otimização de tamanho) saem
  todos os quadros (97 e 13); e o esqueleto precisa estar em `POSE`, não em `REST`, na hora de exportar, senão
  todos os quadros saem com a pose de repouso. Conferido lendo os acessores do GLB (rotação do LeftUpLeg varia).
- **Entregas:** `assets/modelos/aldeao_v2/aldeao_corpo.glb` (malha limpa + armature de 24 ossos + 2 clipes,
  material "pele", 2.424 triângulos, 0,40 m, sem retalhos), `aldeao_corpo_limpo.glb` (só a malha, entrada do
  rig; a limpeza passa a gravar nele), `aldeao_corpo_rig.json` (medidas), `rosto.json` com `ossoCabeca` "Head",
  `ossoPeito` "Spine02", `passadaRun` 0,785. Prévia `assets/previews/aldeao_v2/corpo_rig_clipes.png` (repouso,
  4 quadros do idle, 4 do run, câmera do jogo e de lado). Brutos em `assets/conceitos/aldeao_v2/meshy/rig/`
  (rig, animações, walking/running básicos grátis do rig).
- **Atenção na prévia:** na investida o corpo vai muito inclinado, com a cabeça na frente; de cima a cabeça cobre
  o corpo. É o jeito do clipe; se ler mal no jogo, Run_02 é a troca barata.
- **Créditos:** 11. **Gerações:** 1 rig (2 tentativas recusadas sem custo) + 1 tarefa de animação com 2 ações.
  **Correções manuais:** nenhuma. **Tempo:** ~1 h 30.

## 2026-09-29 — Aldeão v2, passo 8: retalhos "Olhos" e "Boca" no corpo com rig

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** janela dos olhos aprovada a ±45° (olhos no tamanho atual); colocar os retalhos no `aldeao_corpo.glb`
  com rig, peso 100% no osso "Head", e conferir nos quadros do idle e do run que acompanham a cabeça sem
  atravessar a pele.
- **Feito (`tools/arte/aldeao_v2/colocar_retalhos.py`; funções de rig fatoradas em `rig_lib.py`):** retalhos
  criados na pose de repouso (olhos ±45°, altura da b, 109 × 68 mm; boca na janela padrão), UV 0..1, grade
  32×20 e 16×8, materiais "rosto_olhos" e "rosto_boca" (atlas embutido como cor + alfa, foscos; o jogo troca pelo
  shader toon e escolhe a célula), grupo de vértices "Head" com peso 1 e modificador Armature; exportação pelas
  faixas NLA em pose ativa. Conferência por BVH nos quadros 0/24/48/72/96 do idle e 0/3/6/9/12 do run: distância
  com sinal de cada vértice dos retalhos à pele.
- **Problema e correção:** com folga de 1,5 mm e a pele livre, os olhos entravam até 0,8 mm na pele em três quadros
  do idle (a pele das têmporas segue em parte o pescoço; o retalho segue só o Head). Duas medidas: folga de
  **2 mm** (o máximo do contrato) e a pele da frente da cabeça sob as janelas, com 1,5 cm de margem e transição
  suave, passa a seguir **100% o osso Head** (como o v1 fazia). Resultado: folga mínima 1,83 mm e máxima 3,6 mm em
  todos os quadros conferidos; nunca atravessa. Também: um `flat_material` na prévia renomeava o material do
  corpo para "pele.001" no arquivo; removido (o material "pele" do arquivo fica).
- **Aviso de coordenadas:** `face_patch` passou a usar coordenadas de mundo (a malha reimportada é filha do
  armature com escala 0,004, e as coordenadas locais estavam 250× maiores).
- **Entrega:** `assets/modelos/aldeao_v2/aldeao_corpo.glb` (corpo + armature + idle-loop + run-loop + Olhos + Boca),
  `aldeao_corpo_retalhos.json` (janelas e folgas), prévias `assets/previews/aldeao_v2/retalhos_idle_jogo.png` e
  `retalhos_run_tres_quartos.png`.
- **Créditos:** 0 neste passo. **Correções manuais:** nenhuma. **Tempo:** ~50 min.

## 2026-09-29 — Aldeão v2, passo 9: GIFs de comparação de corridas e idles (9 créditos)

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** nem a investida (512) nem o idle (0) convenceram pelos quadros. Montar GIFs em loop: 3 a 4 corridas
  (512, Run_02, corrida e caminhada básicas grátis do rig; uma corridinha de passos curtos se houvesse) e 2 a 3
  idles (o atual e alternativas calmas de pés juntos, respiração e balanço, ou cochilo de pé). Cada opção em
  dois GIFs (câmera do jogo a 44 px ampliado 3× sem suavizar; de lado, maior), com o chão em grade deslizando na
  velocidade da passada. Até 10 créditos.
- **Escolha na biblioteca (pelos GIFs de prévia, grátis):** corridas: Run_02 (14). Não há na biblioteca uma
  corridinha de passos curtos com o corpo pouco inclinado; as demais corridas são atléticas ou investidas.
  Idles calmos de pés juntos: Idle_3 (243) e Idle_12 (252). Dozing_Elderly (38) parece sentado com as mãos nos
  joelhos, não cochilo de pé; Idle_02/03 gesticulam. Gerados num só pedido: **9 créditos** (saldo 2.407 → 2.398).
- **Ferramentas:** `gif_clipes.py` (Blender: importa cada opção, leva à escala do jogo, tira o avanço de raiz se
  houver, mede a passada pela raiz e pelos pés, renderiza cada quadro do ciclo na câmera do jogo e de lado a
  22° acima do chão, com um plano de grade de 10 cm que recua na velocidade da passada; idles com mais de 100
  quadros a cada 2) e `gif_montar.py` (GIFs com paleta única por opção; jogo = 44 px pela altura de repouso,
  ampliado 3× por vizinho mais próximo; lado = 256 px; folha `_opcoes.png` com um quadro e as medidas).
  As opções fora do `aldeao_corpo.glb` usam a malha crua da Meshy com rig (a limpa só tem os dois clipes atuais).
- **Medidas (chão = velocidade usada no GIF; laço = diferença entre último e primeiro quadro, 5 ossos):**
  512 atual 12 q, 0,50 s, pés 0,502 m/s, laço 9,3 cm; Run_02 17 q, 0,71 s, 0,353 m/s, 4,3 cm; corrida básica
  16 q, 0,67 s, 0,564 m/s, 0,8 cm; caminhada básica 25 q, 1,04 s, 0,193 m/s, 5,1 cm; idle atual 96 q, laço
  3,9 cm; Idle_3 239 q (10 s), 2,8 cm; Idle_12 144 q (6 s), 0,3 cm.
- **Correção de passada:** com o avanço de raiz removido, a velocidade em que os pés do 512 não deslizam é a
  medida pelos pés (0,502 m/s), não a do avanço original (0,785, que incluía escorregão): `rosto.json` passou a
  0,502 e o `montar_rig.py` usa a medida pelos pés.
- **Problemas e correções:** GIF do jogo com cores embaralhadas (quantização quadro a quadro com alfa; agora uma
  paleta por opção, sem alfa); a vista de lado ao nível do chão não mostrava a grade (câmera 22° acima).
- **Saída:** `assets/previews/aldeao_v2/clipes/<opção>_jogo.gif`, `<opção>_lado.gif` e `_opcoes.png` (3,9 MB).
- **Créditos:** 9. **Correções manuais:** nenhuma. **Tempo:** ~1 h 30 (metade em render).

## 2026-09-29 — Aldeão v2, passo 10: clipes trocados (Idle_3 e Run_02), laços fechados, passada refeita

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** idle-loop = Idle_3, run-loop = Run_02 no `aldeao_corpo.glb`, mantendo os retalhos e conferindo a
  folga; fechar os laços misturando os últimos quadros com os primeiros (meta: salto < 1 cm; antes 2,8 e
  4,3 cm); refazer a passada pelos pés; GIFs dos dois clipes corrigidos.
- **Feito:** `montar_rig.py` passou a ler `extras_14_243_252.glb` (mapa Idle_3 → idle-loop, Run_02 → run-loop) e
  ganhou `close_loop` (`rig_lib.py`): nos últimos 25% dos quadros (mínimo 4), cada curva é misturada com o valor
  do primeiro quadro com peso suave de 0 a 1, e os quaternions são alinhados em sinal quadro a quadro. Laço
  (soma em 5 ossos): idle 0,0 cm (60 quadros misturados de 239); run de 4,3 cm para **0,6 cm** (4 quadros de 17).
  Passada da Run_02 pelos pés: **0,383 m/s** (`rosto.json` atualizado). `colocar_retalhos.py` rodado de novo:
  folga dos retalhos entre 1,4 e 3,2 mm nos 6 quadros conferidos de cada clipe (na corrida a pele comprime até
  1,4 mm; nunca atravessa). Materiais: pele, rosto_olhos, rosto_boca.
- **GIFs:** `assets/previews/aldeao_v2/clipes_finais/idle_Idle_3_{jogo,lado}.gif` e `run_Run_02_{jogo,lado}.gif`
  (jogo a 44 px ampliado 3×; lado a 256 px; chão em grade na passada). O idle de 10 s vai a 12 fps.
- **Créditos:** 0 neste passo. **Correções manuais:** nenhuma. **Tempo:** ~30 min.

## 2026-09-29 — Aldeão v2, passo 11: piloto dos cabelos com o cabelo 4 (longo liso), 20 créditos

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** seguir o `PLANO_CABELOS.md` só com o cabelo 4: gerar na Meshy, extrair a peruca, encaixar na cabeça
  do corpo aprovado, abrir a janela dos olhos, decimar a ≤ 800; prévia em 44 e 112 px com crepúsculo; conferir
  com idle e run que o cabelo rígido não atravessa o corpo nem os retalhos; até 2 gerações.
- **Meshy (`meshy_cabelo.py`):** Multi-Image to 3D com frente, lado, costas e topo, só malha, remesh a 3.000,
  1 geração (20 créditos; saldo 2.398 → 2.378): `assets/conceitos/aldeao_v2/meshy/cabelos/cabelo_4_1.glb`,
  3.104 triângulos, cabeça + cabelo + um toco de pescoço que a Meshy inventou.
- **Extração (`extrair_peruca.py`), o que funcionou e o que não:**
  - o GLB da Meshy vem com os **vértices duplicados por face** (3.342 → 1.555 depois de fundir): sem fundir,
    cada triângulo é uma ilha, a decimação racha a malha e qualquer crescimento de região para. Custou três
    rodadas até perceber;
  - achar a cabeça da folha por ajuste de elipsoide **não fecha**: o rosto visível é uma faixa estreita entre as
    mechas, quase plana, e o ajuste (esfera, forma fixa, escala por eixo) diverge ou erra 1 cm. Para o piloto a
    cabeça da folha é ancorada em medidas da própria folha (`PRIOR[4]`: largura 75% e altura 74% da silhueta,
    topo 5% abaixo do topo) mais a frente do rosto medida no modelo, e o elipsoide da cabeça do corpo é mapeado
    com escala por eixo. Para os outros cabelos é preciso medir os mesmos três números em cada folha;
  - separar rosto de cabelo por **crescimento de região** a partir da frente dos olhos, só por arestas com menos
    de 32° (a linha do cabelo é viva) e sem sair mais de 2,5 cm do elipsoide: 446 faces de rosto + 161 do toco
    de pescoço removidas; sobra a peruca em 7 pedaços (24 faces soltas descartadas);
  - encaixe: 25 vértices empurrados para fora do corpo (+1,5 mm) e 39 para 2 mm do retalho dos olhos; franja:
    nenhuma face abaixo da linha dos olhos (o repartido no meio deixa o rosto livre);
  - decimação 2.473 → **759 triângulos**; material "cabelo" #4B5A69; exportação rígida no espaço do corpo em
    repouso: `assets/modelos/aldeao_v2/cabelos/cabelo_4.glb` (+ `cabelo_4_relatorio.json`).
- **Conferência:** repouso: 0,46 mm do corpo (pior ponto nos ombros, z 0,195 m: as pontas encostam nos ombros)
  e 1,87 mm do retalho dos olhos (14 vértices de franja na frente dele). Idle: 1,5 mm do corpo. **Run: as
  mechas entram até 37 mm nos ombros e braços** (z 0,166 m), porque o cabelo é rígido no Head e os braços
  balançam por dentro das mechas; peruca e retalhos seguem o mesmo osso, então a folga entre eles é a do
  repouso em todo quadro. Saídas possíveis: encurtar as pontas até o queixo (muda o desenho), ou aceitar (a
  44 px na câmera do jogo o braço some sob a mecha). Decisão do Arthur.
- **Prévia:** `assets/previews/aldeao_v2/cabelo_4_previa.png` (frente, lado, 3/4, jogo; 112 px, 44 px e 44 px ×
  crepúsculo; rosto distraído).
- **Créditos:** 20. **Gerações:** 1 de 2. **Correções manuais:** nenhuma. **Tempo:** ~2 h.

## 2026-09-29 — Aldeão v2, passo 12a: cabelo 1 (curto bagunçado), 20 créditos

- **Agente / modelo:** Claude Code + Fable 5.1, agente de ARTE na branch `arte`.
- **Pedido:** os outros 4 cabelos pelo método do piloto, medindo as três âncoras da cabeça em cada folha; cabelo 1
  com pontas finas: mostrar antes de simplificar demais se não couber em 800 triângulos.
- **Âncoras medidas nas vistas de frente (largura da cabeça / silhueta, altura / silhueta, topo abaixo do topo):**
  1: 0,78 / 0,80 / 0,10; 2: 0,75 / 0,83 / 0,06; 3: 0,70 / 0,82 / 0,07; 5: 0,88 / 0,86 / 0,05 (o 4 ficou 0,75 /
  0,74 / 0,05). Vêm da face visível e do queixo medidos pelo preparador, mais a espessura estimada da calota.
  A semente do crescimento de região passou para a altura da boca (38%), onde nunca há franja.
- **Cabelo 1:** Meshy 1 geração (saldo 2.378 → 2.358); 3.357 vértices fundidos em 1.554; rosto = 20% das faces
  (631 de rosto + 13 do toco de pescoço removidas); 5 pedaços (7 faces soltas fora); 22 faces de franja apagadas
  abaixo da linha dos olhos; decimação 2.430 → **759 triângulos**. Folga: repouso 1,5 mm do corpo e 1,5 mm do
  retalho dos olhos (32 vértices de franja na frente dele); idle 1,6 mm; run 1,2 mm (nada atravessa: cabelo
  curto não chega aos ombros). Comparação 2.400 × 800 triângulos a 44 e 112 px em
  `assets/previews/aldeao_v2/cabelo_1_decimacao.png`: a 44 px igual; a 112 px as pontas em folha só ficam um pouco
  mais macias, sem virar bolota. Fiquei com 800. Prévia: `cabelo_1_previa.png`.
- **Plano:** `PLANO_CABELOS.md` ganhou a seção de problemas conhecidos (pontas nos ombros/braços na corrida,
  aceito; rever no zoom máximo; âncoras por folha; vértices duplicados).
- **Créditos:** 20. **Tempo:** ~30 min.

## 2026-09-29 — Aldeão v2, passo 12b: cabelo 2 (chanel com franja de lado), 20 créditos

- **Cabelo 2:** 1 geração (saldo 2.358 → 2.338); 3.240 vértices fundidos em 1.547; rosto 18% (564 + 28 do
  pescoço); 9 pedaços (45 faces soltas fora); **65 faces de franja apagadas** abaixo da linha do centro dos olhos
  (sobra a franja sobre a metade de cima de um olho; o outro fica livre); 36 vértices empurrados a 2,5 mm do
  retalho; 2.387 → **759 triângulos**. Folga: repouso 0,95 mm do corpo e **2,45 mm do retalho dos olhos**; idle
  1,2 mm; run -21,7 mm nos ombros (z 0,185; problema conhecido, aceito). Prévia `cabelo_2_previa.png`.
- **Ajuste comum:** a folga-alvo ao retalho subiu de 2,0 para 2,5 mm porque a decimação move os vértices depois
  do empurrão (o cabelo 1 ficava em 1,5 mm; refeito: 2,27 mm; o 4 será refeito no fim com os demais).
- **Créditos:** 20. **Tempo:** ~20 min.

## 2026-09-29 — Aldeão v2, passo 12c: cabelo 3 (ondulado volumoso), 20 créditos

- **Cabelo 3:** 1 geração (saldo 2.338 → 2.318); 3.084 vértices fundidos em 1.562; rosto 13% (404 + 36 do
  pescoço); 3 pedaços (36 faces soltas fora); 29 faces de franja apagadas abaixo da linha dos olhos; 30 vértices
  empurrados a 2,5 mm do retalho; 2.615 → **760 triângulos**. Folga: repouso 1,1 mm do corpo e **2,48 mm do
  retalho dos olhos**; idle -3,0 mm nos ombros (z 0,203: as ondas até o queixo tocam os ombros quando a cabeça
  balança); run -30 mm nos ombros (z 0,174; problema conhecido, aceito). Prévia `cabelo_3_previa.png`.
- **Créditos:** 20. **Tempo:** ~10 min.

## 2026-09-29 — Aldeão v2, passo 12d/12e: cabelo 5 (rabo de cavalo), cabelo 4 refeito, prévia conjunta e GDD

- **Cabelo 5:** 1 geração (saldo 2.318 → 2.298); 3.203 vértices fundidos em 1.555; rosto 16% (483 faces; sem
  toco de pescoço); 1 pedaço só; 7 faces apagadas na frente dos olhos; 2.616 → **758 triângulos**. O rabo é
  rígido no Head: na corrida fica a **35 mm das costas** no pior quadro (11 mm no idle); corpo 0,3 mm no run.
- **Passe final de folga:** a decimação move vértices, então o empurrão para fora do corpo (1,5 mm) e do
  retalho (2,5 mm) roda de novo depois dela. Os 5 cabelos refeitos: em repouso todos a 1,5 mm do corpo e
  **2,5 mm do retalho dos olhos**; 758 a 760 triângulos. No run, os que descem até os ombros entram neles
  (2: -22 mm, 3: -30 mm, 4: -37 mm; problema conhecido, aceito); 1 e 5 não entram.
- **Prévia conjunta:** `assets/previews/aldeao_v2/cabelos_conjunta.png` (frente, lado, 3/4, jogo × 5 cabelos ×
  112 px, 44 px, 44 px no crepúsculo). Prévias individuais `cabelo_N_previa.png`.
- **GDD:** subseção "Aldeão: implementação v2 (29/09/2026, aprovado)" inserida no GDD vivo do Claude Docs
  (rev 90) logo após a v1: corpo, rosto A1 e janela ±45°, retalhos, clipes Idle_3 e Run_02, cabelos, tamanhos
  em tela medidos e custo (160 créditos). Reexportado para `docs/GDD.md` (só essa subseção e a data mudaram).
- **Créditos:** 20 (cabelo 5); etapa dos cabelos: 100. **Correções manuais:** nenhuma. **Tempo:** ~40 min.

## 2026-09-29 — Encerramento do dia (agente de arte, branch `arte`)

- **Pronto do aldeão v2:** contrato arte × jogo lido e seguido; atlas de expressões na direção A1 (`rosto/olhos.png`,
  `boca.png`, `rosto.json` com as 9 expressões, `ossoCabeca`, `ossoPeito`, `passadaRun`); corpo gerado na Meshy,
  limpo (2.424 triângulos, material "pele", 0,40 m), com rig da Meshy, clipes `idle-loop` (Idle_3) e `run-loop`
  (Run_02) em laço fechado e os retalhos "Olhos" (±45°, altura b) e "Boca" presos ao Head, tudo em
  `assets/modelos/aldeao_v2/aldeao_corpo.glb`; 5 perucas em `cabelos/cabelo_1..5.glb` (758 a 760 triângulos,
  material "cabelo", rígidas no Head, franja sobre no máximo a metade de cima de um olho, 2,5 mm do retalho);
  prévias e GIFs em `assets/previews/aldeao_v2/`; ferramentas em `tools/arte/aldeao_v2/` (preparador de vistas,
  atlas, limpeza, rig, retalhos, extração de perucas, GIFs, prévias); GDD vivo com a subseção
  "Aldeão: implementação v2" e reexportado.
- **Pendente:** integração no jogo pelo agente de código (`aldeao_corpo.glb`, os 5 cabelos, `rosto.json` e a regra
  da franja no contrato); julgamento final no jogo com cabelo e shader toon; problema conhecido das mechas
  longas nos ombros e braços na corrida, a rever no zoom máximo; `cabelo_N_sob_chapeu.glb` (previsto no contrato,
  não começado); `passadaWalk` do contrato não existe porque o aldeão só tem idle e run (o contrato cita walk;
  o agente do jogo decide se muda). A remoção do aldeão v1 na `arte` acontece sozinha no próximo merge da
  `master` (ela já o removeu no commit `edc1291`).
- **Créditos da Meshy gastos hoje no v2:** **160** (corpo 40: só-frente e multi-imagem; rig 5 + clipes 6 + clipes
  extras 9 = 20; cabelos 5 × 20 = 100). Saldo final 2.298. Sem correções manuais além de copiar o `.env`.
- Os quatro `.import` soltos em `docs/prints/` (prints do agente de jogo) entram neste commit para a árvore ficar
  limpa.

## 2026-09-29 — Protagonista v2, passo 1: referências da v1 para as folhas do ChatGPT

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** refazer a protagonista (v2) pelo processo do aldeão v2. Primeiro passo, sem gerar nada na Meshy:
  renders da v1 (`assets/modelos/protagonista/protagonista.glb`) em repouso, com a textura original e o cristal
  com a emissão normal, para servir de referência às folhas do ChatGPT.
- **Feito:** `tools/arte/protagonista_v2/prot_lib.py` (importa em repouso, regiões por osso, câmera do jogo e
  material toon por nós; reaproveita o `corpo_lib.py` do aldeão) e `referencia_v1.py` (Blender headless).
  Câmera ortográfica, mesma escala nas três vistas (0,80 m = 1.536 px num quadro de 2.048), frente, perfil
  esquerdo (câmera em +X do Blender, o lado do osso LeftHand) e costas; close da cabeça em 1.024, do osso `neck`
  ao topo. Luz: mundo branco 0,85 + sol fraco e largo sem sombra; fundo #D9D9D9 visto só pela câmera (nó Light
  Path), sem texto. Cristal com a força de emissão do GLB (3,0), sem o reforço de 3× que o jogo aplica.
  Saída: `assets/conceitos/protagonista_v2/referencia/v1_{frente,lado,costas,cabeca_frente,cabeca_lado}.png`;
  pasta `assets/conceitos/protagonista_v2/folhas/` criada (com `.gitkeep`) para as folhas.
- **O que deu errado:** o primeiro close de lado saiu fora do centro, porque a caixa da cabeça incluía o cabelo
  longo das costas (preso ao Head); o recorte passou a ir do pescoço ao topo. Um "Icosphere" de 2 m que aparece ao
  importar não é do GLB: é a forma de osso que o importador do Blender cria (desligada com `disable_bone_shape`).
- **Observação:** a pose de repouso da v1 é T (braços na horizontal), não A como a do aldeão v2.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~30 min.

## 2026-09-29 — Protagonista v2, passo 3: medidas da v1

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** triângulos por material e por região (osso de maior peso), altura e cores médias de pele e cabelo
  na textura, em `assets/previews/protagonista_v2/v1_medidas.json`. Feito antes do passo 2 porque a coluna (b) da
  folha de diagnóstico usa a cor da pele medida.
- **Feito:** `tools/arte/protagonista_v2/medir_v1.py` (Blender headless, pose de repouso).
- **Medidas:** altura **0,80 m**; **2.974 triângulos** (Material_1 2.970, Cristal 4). Por região, pelo osso
  dominante de cada triângulo (soma dos pesos dos 3 vértices): cabeça/cabelo **383** (13%), tronco **709** (24%,
  inclui os 4 do cristal), braços e mãos **786** (26%), pernas e pés **1.096** (37%). A cabeça tem pouco: parte
  do cabelo longo segue os ossos do tronco. Para comparar: o aldeão v2 tem 2.424 no corpo + ~760 no cabelo.
- **Cores (textura):** pele **#91ADB7**, cabelo **#75929F**. A textura da Meshy é um atlas em cacos, então as
  amostras vêm da geometria: pele = triângulos com osso dominante mão ou pé (descalça; os antebraços têm faixas),
  273 triângulos, 9.559 texels; cabelo = cabeça acima do osso `neck` com normal para trás ou para cima (nuca e
  topo, onde só há cabelo), 117 triângulos, 5.739 texels. Cada triângulo é rasterizado na UV; média em espaço linear.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~20 min.

## 2026-09-29 — Protagonista v2, passo 2: folha de diagnóstico da v1 na câmera do jogo

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** folha na câmera do jogo (CameraRig.cs reproduzido no Blender), nos zooms 0,4 / 1 / 2,5, com três
  colunas: (a) v1 com textura como no jogo, (b) v1 sem textura, chapada na cor média da pele e sombreada como o
  `Toon.gdshaderinc`, (c) aldeão v2 (corpo + cabelo 4) com o mesmo sombreado; luz fosca, fraca e fria de cima;
  linha extra multiplicada por #6A5B7C.
- **Feito:** `tools/arte/protagonista_v2/diagnostico_v1.py` (Blender headless) e `montar_diagnostico.py` (PIL).
  Câmera: perspectiva, pitch 55°, FOV vertical 45°, 16 m ÷ zoom, 3024×1890, olhando o chão sob o personagem.
  Toon por nós (`prot_lib.toon_material`): meio-Lambert, 3 faixas, piso 0,35, vezes a luz, mais o ambiente,
  como emissão (o mundo não soma luz). Luz: direção do crepúsculo das prévias do aldeão (quase de cima, um pouco
  da frente), cor fria (0,72; 0,78; 0,95) × 0,75; ambiente roxo-acinzentado × 0,6. Coluna (a): material do GLB
  sob um sol e um mundo iguais, cristal com o reforço de 3× do `CastellanVisual.cs`. Coluna (b): #91ADB7 (passo 3)
  em tudo, cristal incluído. Coluna (c): pele #AEBFD3, cabelo #6F7F96, retalhos "Olhos" e "Boca" no quadro 0 do atlas.
  Mesmo recorte nas três colunas de cada zoom, em pixels reais da tela (sem ampliar); a linha de crepúsculo é o zoom 1.
- **Saída:** `assets/previews/protagonista_v2/v1_diagnostico.png`. Altura em tela: v1 **28 / 68 / 179 px**,
  aldeão v2 com cabelo **21 / 48 / 122 px** (zooms 0,4 / 1 / 2,5).
- **Leitura:** com a textura, a v1 lê pelo contraste interno (roupa escura, rosto e mãos claros, cristal); chapada,
  sobra uma silhueta clara sem rosto e com poucas faixas, porque com a luz de cima quase toda a frente cai na faixa
  mais clara. O aldeão v2 lê melhor a 48 px pelo rosto em retalho e pelo cabelo mais escuro que a pele.
  No crepúsculo, a v1 some no chão; o cristal é o que sobra dela no zoom 1.
- **Escolhas minhas (avisar se for diferente):** pose de repouso (T) nas três colunas, e não um quadro do idle,
  para não precisar prender o cabelo rígido do aldeão ao osso; fundo do chão #4E4A58, o mesmo das prévias do aldeão.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~40 min.

## 2026-09-29 — Prova de operação, passo 1: auditoria do esqueleto do aldeão v2

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** prova técnica de que o aldeão v2 (e a protagonista v2, pelo mesmo método) aceita máquinas operadas
  sem um v3. Passo 1: auditar `aldeao_corpo.glb` (escala, unidades, rolagens, pose de repouso, o que complica
  IK/retarget, mãos). Nenhum arquivo aprovado alterado; tudo em pastas novas.
- **Feito:** `tools/arte/prova_operacao/auditoria.py` (Blender headless + JSON cru do GLB) →
  `assets/previews/prova_operacao/auditoria.json`, `mao_esquerda.png`, `mao_direita.png`; relatório
  `auditoria.md`.
- **Achados:** Armature com escala 0,004 e juntas em unidades de 4 mm (Hips a 31 unidades); malhas também nessa
  unidade; só a posição do Hips varia nos clipes. O importador do Blender cria os ossos 250× compridos (sem a
  escala do pai); a direção (+Y para o filho, estilo Mixamo) está certa. Rolagens ±90° nos braços; pernas com
  rolagens assimétricas; esqueleto assimétrico (antebraço 51,7 × 48,6 mm). Pose A, braços a 44°; ombro ao punho
  103 mm (25% da altura). Mãos em luva, sem dedos nem ossos de dedo, forma de punho meio fechado.
- **O que deu errado:** o primeiro close das mãos estourou no branco (luz do `setup_scene`); exposição −1,2.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~40 min.

## 2026-09-29 — Prova de operação, passo 2: normalização da escala numa cópia

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** aplicar a escala do Armature (1, em metros) numa cópia, tocar idle-loop e run-loop nas duas versões e
  medir a maior diferença de vértice em 0/25/50/75% do clipe; dizer se é segura e o que mudaria no jogo.
- **Feito:** `tools/arte/prova_operacao/normalizar.py`: ossos (`armature.data.transform`) e malhas filhas
  (`mesh.transform`) multiplicados por 0,004, escala do objeto 1, e as 144 curvas de posição dos ossos (24 ossos ×
  3 eixos × 2 clipes) multiplicadas por 0,004 (estão no espaço do osso, em unidades de 4 mm); rotações intactas.
  Exportado como o `montar_rig.py` (NLA, POSE, sem otimização): `assets/modelos/prova_operacao/aldeao_normalizado.glb`.
  O `aldeao_corpo.glb` aprovado não foi tocado.
- **Resultado (`assets/previews/prova_operacao/normalizacao.json`):** nó Armature do glTF sem escala; vértices
  correspondentes (por posição em repouso; o exportador separou 2 vértices do corpo, 2.557 → 2.559) diferem no
  máximo **0,0085 mm** (idle 0,005; run 0,0085) nos 8 quadros; cabeças dos ossos ≤ 0,0074 mm; repouso no mundo
  dos ossos de encaixe (Head, Spine02) ≤ 0,004 mm. A rotação de repouso aparece com 0,04°, ruído de ponto flutuante
  ao tirar a rotação de uma matriz com escala 0,004 (os vértices provam que é < 0,002°).
- **Leitura:** a normalização é segura, é só troca de unidade. No jogo nada muda no código: o encaixe usa
  `GetBoneGlobalRest(osso)⁻¹ × skeletonInModel⁻¹`, e `skeletonInModel` perde o 0,004 ao mesmo tempo que o repouso
  passa a metros; cabelos (no espaço do corpo) e retalhos (skinned) seguem iguais; nenhum número do `src/View`
  depende da escala. O que muda: valores em espaço de osso passam a metros (posição do Hips nos clipes, IK por
  código), e o importador do Blender passa a criar ossos com comprimento de verdade.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~30 min.

## 2026-09-29 — Prova de operação, passo 3: clipe "girar_roda-loop" por IK no Blender (sem Meshy)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** roda provisória vertical (eixo horizontal na altura do peito, uma alça em cada face a 0,10 m do
  eixo, defasadas 180°); aldeão com o esqueleto aprovado (sem normalizar), pés fixos, as duas mãos na alça por IK
  durante uma volta, tronco acompanhando pouco, sem avanço de raiz; laço fechado < 1 cm; exportar só esqueleto +
  clipe, a roda e `clipes.json`. Se as mãos não fecharem, registrar exatamente por quê.
- **Feito (`tools/arte/prova_operacao/girar_roda.py`):**
  1. comprimento real nos ossos do braço (braço e antebraço até o filho; mão até o centro da palma), mudando só
     `length`: repouso muda 0,00002° e 0,005 mm, ou seja, nada;
  2. IK nas duas mãos (cadeia mão-antebraço-braço, ponta no centro da palma, sem esticar, rigidez 0,5 na mão),
     polo no cotovelo com ângulo escolhido por lado (sai diferente em cada lado por causa das rolagens de ±90°);
  3. tronco: metade em Spine02, metade em Spine01, inclinação de 4° a 12° (mais com a alça embaixo), giro de ±8° e
     flexão lateral de ±4° para o lado da alça; Hips parado (faixa de posição 0);
  4. 48 quadros a 24 fps (1 volta = 2 s, escolha minha), bake visual; laço 0,0 cm sem misturar nada;
  5. alça: manopla de 12 mm de raio na ponta de uma haste de 5 cm; cada mão de um lado da manopla (±18 mm);
     plano das manoplas a 10,3 cm dos ombros, pelo perfil da barriga + 32 mm de folga; eixo a 0,19 m.
- **Entregas:** `assets/modelos/prova_operacao/clipes/girar_roda.glb` (só esqueleto + `girar_roda-loop`; conferido na
  reimportação: 1 objeto ARMATURE), `roda.glb` (pivô no eixo, frente +Z = face da alça A; alça A no topo e B embaixo
  na fase 0; material "madeira" #4A3B3A), `clipes.json` (2,0 s; fase 0 = alça A no topo; conta em 0,5 = alça A
  passa embaixo, escolha minha; ângulo da roda −360° × fase em volta do +Z; lado oposto toca o clipe ao contrário
  com fase 0,5 − t). Medidas em `assets/previews/prova_operacao/girar_roda.json`.
- **O problema (a informação que importa): as mãos NÃO fecham na alça de 0,10 m.** Não é escala nem rolagem: é a
  proporção. Ombro à palma = 123 mm; a manopla fica a ≥ 103 mm dos ombros para não entrar na barriga (que avança
  65 mm); um círculo de 0,10 m no peito desce à altura do joelho. Falta até **35,4 mm** (pior no quadro 29, fase
  0,58: alça embaixo, do lado oposto à mão direita); só 1 dos 48 quadros fica a ≤ 5 mm. Varredura com o mesmo
  método: raio 0,05 → 0 mm; **0,06 → 2,3 mm**; 0,07 → 9,7 mm; 0,08 → 19 mm; 0,10 → 35 mm.
- **Variante (extra, para provar o método):** raio 0,06 m em `assets/modelos/prova_operacao/variante_r06/` (mesmos
  arquivos): fecha nos 48 quadros, falta máxima 2,5 mm. Nenhum arquivo aprovado mudou.
- **O que deu errado:** a primeira versão do giro do tronco tinha os sinais embolados; reescrita antes de rodar.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h 30.

## 2026-09-29 — Prova de operação, passo 4: GIFs com dois aldeões na mesma roda

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** GIFs na câmera do jogo (aldeão a 112 px) e de lado (256 px), dois aldeões em lados opostos da
  mesma roda, o segundo com fase +0,5, mais a versão × #6A5B7C.
- **Feito:** `tools/arte/prova_operacao/gif_roda.py` (Blender: dois `aldeao_corpo.glb` aprovados, cabelos 1 e 3
  rígidos no Head, clipe tirado do `girar_roda.glb`, toon do `prot_lib`) e `gif_roda_montar.py` (PIL). Câmera do
  jogo no zoom 2,5, em pixels reais; lado ortográfico a 640 px/m, 22° acima do chão; 48 quadros a 24 fps.
- **Fase do segundo aldeão:** do outro lado, a alça B gira no sentido oposto visto por ele. Com "+0,5" tocado para
  a frente, as mãos só coincidem com a alça em 2 instantes; o certo é tocar o mesmo clipe **ao contrário, com fase
  0,5 − t**. Os GIFs usam isso (anotado no `clipes.json`).
- **Conferência na cena dos GIFs:** faltas palma-manopla iguais às do bake nos dois aldeões (raio 0,10: 35,4 mm;
  raio 0,06: 2,5 mm): o clipe exportado sem malha serve no arquivo aprovado, nos dois lados.
- **Saída:** `assets/previews/prova_operacao/roda_{jogo,lado}.gif` e `_crepusculo.gif` (raio pedido, 0,10 m) e os
  mesmos em `variante_r06/` (0,06 m); medidas em `roda_gif_medidas.json`.
- **O que deu errado:** na primeira rodada a cena ficou 19 cm abaixo do chão (centralizei a roda também em z);
  corrigido para centralizar só em x/y.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~40 min.

## 2026-09-29 — Aldeão v2: prévias restauradas e normalização oficial da escala (Armature em metros)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** restaurar as 19 prévias apagadas no disco; normalizar agora o `aldeao_corpo.glb` aprovado (escala 1, em
  metros), mantendo nomes; conferir vértices (< 0,01 mm), folga dos retalhos (1,4 a 3,2 mm) e cabelos; substituir só
  se tudo passar.
- **Prévias:** `git checkout` das 19; `git status` limpo; nada a commitar (eram iguais às do repositório).
- **Feito:** `rig_lib.apply_armature_scale` (o método da prova, agora geral: malhas com qualquer inversa de pai),
  `rig_lib.export_rig_glb` (NLA, POSE, sem otimizar), as funções de folga movidas do `colocar_retalhos.py` para o
  `rig_lib`, `tools/arte/aldeao_v2/conferir_corpo.py` (compara dois GLBs do corpo: nomes, vértices, folga dos
  retalhos, cabelos presos como o jogo prende) e `normalizar_corpo.py` (normaliza num temporário, confere e só então
  substitui). Relatório: `assets/modelos/aldeao_v2/aldeao_corpo_normalizacao.json`.
- **Conferência (todas as metas passaram; o aprovado foi substituído):**
  - vértices (corpo, Olhos, Boca), 0/25/50/75% de idle-loop e run-loop: **0,0085 mm** no máximo;
  - folga dos retalhos nos 12 quadros do `colocar_retalhos.py`: **1,40 a 3,16 mm**, igual à do arquivo antigo;
  - cabelos 1 a 5 presos pela fórmula do `VillagerVisual.Socket` nos mesmos 8 quadros: **0,0012 mm**; todos a 1,5 mm
    do corpo em repouso;
  - nomes iguais (clipes `idle-loop`, `run-loop`; materiais `pele`, `rosto_olhos`, `rosto_boca`; malhas `aldeao_corpo`,
    `Olhos`, `Boca`; 24 ossos); nó Armature do glTF sem escala (translação de 6,6 mm mantida).
- **rosto.json:** nada muda. `ossoCabeca` e `ossoPeito` são nomes; `passadaRun` (0,383 m/s) foi medida no mundo;
  o atlas é em pixels.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~40 min.

## 2026-09-29 — Aldeão v2: processo exporta normalizado (montar_rig + colocar_retalhos) e prova de reprodução

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** `montar_rig.py` e `colocar_retalhos.py` exportando já normalizados; rodar os dois do zero e provar
  que reproduzem o arquivo normalizado (mesma diferença máxima).
- **Feito:** os dois chamam `rig_lib.apply_armature_scale` antes de exportar (no `colocar_retalhos` não faz nada
  se a entrada já vier em metros) e aceitam caminhos de saída opcionais (`montar_rig.py -- <saida>`, que então não
  mexe no `rosto.json`; `colocar_retalhos.py -- <prévia> <entrada> <saida>`). Sem argumentos gravam no aprovado,
  como antes. O `colocar_retalhos` usa as funções de folga do `rig_lib` (mesmo código).
- **Resultado do zero (saídas temporárias; relatório `assets/modelos/aldeao_v2/aldeao_corpo_reproducao.json`):**
  nó Armature sem escala; mesmos nomes; passada 0,383 m/s; folga dos retalhos 1,40 a 3,16 mm (igual); cabelos
  0,0012 mm; corpo 0,0003 mm; Boca 0,0001 mm. **Olhos: 0,27 mm** em 21 dos 693 vértices, a coluna central inteira
  do retalho (ângulo 0, sobre a costura da simetria em x = 0). Então a meta "mesma diferença máxima" (< 0,01 mm)
  **não foi atingida** nesse retalho.
- **Investigação:** duas execuções do zero saem idênticas byte a byte (o processo é determinístico); refazer o
  retalho sobre o aprovado antigo, ainda em escala 0,004, dá a mesma diferença (0,2731 mm), então **não é da
  normalização**. O aprovado foi gerado em 29/09 às ~02:57 com os mesmos scripts e entradas (nenhum mudou desde
  então), mas a coluna central dele não sai igual hoje. A causa provável é o raio da coluna do meio, que cai
  exatamente na aresta da costura e fica sensível a detalhes da malha de entrada; não achei qual. Efeito: 0,27 mm
  num retalho a 1,4–3,2 mm da pele, invisível; a folga medida é a mesma.
- **Não troquei o aprovado pelo refeito:** isso muda o arquivo aprovado em 0,27 mm e pede o aval do Arthur. Se
  trocar, a partir daí o processo reproduz o aprovado byte a byte.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h.

## 2026-09-29 — Aldeão v2: regra de ergonomia (ergonomia.json) e script de medida reutilizável

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** `assets/modelos/aldeao_v2/ergonomia.json` com o que uma máquina precisa respeitar (alturas de peito,
  ombros e quadril; alcance ombro-palma; avanço da barriga; distância mínima da alça aos ombros; maior raio de
  manivela no peito em que as mãos fecham; nota do método) e o script de medida para qualquer corpo.
- **Feito:** as funções de IK do `girar_roda.py` foram para `tools/arte/prova_operacao/operacao_lib.py`
  (generalizadas: escala do mundo do armature, que inclui um nó pai; corpo achado sozinho). O `girar_roda.py`
  usa a lib e, rodado numa pasta temporária sobre o corpo já normalizado, dá exatamente os números da prova (mesma
  varredura, polos −180°/−45°, falta de 35,4 mm, 0,06 m). Script novo: `medir_ergonomia.py -- <corpo.glb> <saida.json>`
  (a folga e a pegada da mão saem da espessura medida da mão; o polo escala com o alcance; varredura de raio a
  cada 5 mm até o alcance). Testado na protagonista v1 (escala 0,0057 no mundo) só para ver que roda; saída
  fora do repositório.
- **Aldeão v2 (`ergonomia.json`):** altura 0,40; quadril 0,124; peito 0,194; ombros 0,213; alcance ombro-palma
  0,1228 / 0,1225 (esq./dir.); barriga avança 64 mm à frente dos ombros (66 mm à frente do pivô, a 0,137 m);
  distância mínima da manopla aos ombros 0,099 m no raio recomendado (0,102 m no raio 0,10); raio máximo no
  peito: **0,06 m recomendado** (falta 0,1 mm). O limite de 5 mm da prova vai até 0,065 m com passo de 5 mm, mas ali a
  mão já fica 3,7 mm fora, por isso o JSON traz os dois números e recomenda 0,06.
- **Observação para a protagonista:** na v1, o cabelo longo preso aos ossos do tronco entra na medida da "barriga";
  na v2 vale conferir isso quando o corpo existir.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~45 min.

## 2026-09-29 — Aldeão v2: aprovado trocado pela saída do processo (reprodução byte a byte)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** com o aval do Arthur, trocar o `aldeao_corpo.glb` aprovado pela versão refeita do zero, depois de
  conferir; rodar o processo mais uma vez e confirmar que sai idêntico byte a byte; registrar o hash.
- **Conferência (refeito × aprovado anterior, `conferir_corpo.py`, que agora dá a diferença por malha):** corpo
  **0,0087 mm**, Boca **0,0012 mm**; Olhos **0,273 mm** em 21 vértices, todos com x entre −0,05 e +0,14 mm (a coluna
  central, como esperado); folga dos retalhos **1,40 a 3,16 mm** nos dois; cabelos 1 a 5 **0,0012 mm** (todos a 1,5 mm
  do corpo); mesmos nomes de ossos, clipes, materiais e malhas; nó Armature sem escala. Tudo como esperado, então o
  aprovado foi trocado.
- **Segunda execução do zero** (`montar_rig.py -- <tmp>` e `colocar_retalhos.py -- <prévia> <tmp> <tmp>`): **idêntica
  byte a byte** ao novo aprovado (`cmp`).
- **Hash (SHA-256) do `assets/modelos/aldeao_v2/aldeao_corpo.glb`:**
  `11c7d12bc4c522808546f61f3136031e2fce0cc6ccf9e789abd02779d110febf` (988.156 bytes).
- Os relatórios ao lado (`aldeao_corpo_rig.json`, `aldeao_corpo_retalhos.json`) foram trocados pelos da execução nova
  (só ruído de ponto flutuante e o campo `normalizacao`); `aldeao_corpo_reproducao.json` registra a troca e o hash.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~15 min.

## 2026-09-29 — Prova de operação: clipes reexportados pelo contrato de animação (metros, t = 0, 24 fps)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** o jogo contornou três problemas dos clipes da prova (escala 0,004, primeira chave em 1/24 s,
  reamostragem a 30 fps); corrigir na origem pelo contrato novo (`docs/animacao_contrato.md`, lido do disco da
  worktree do `master`, onde ainda não está commitado) e conferir.
- **Feito:** `operacao_lib.export_clip` (esqueleto só, Armature em metros por `rig_lib.apply_armature_scale`, chaves
  deslocadas para começar no quadro 0, cena a 24 fps, uma faixa NLA por ação, POSE) e `gltf_clip_times` (lê do GLB
  os tempos das chaves e a escala do nó); `reexportar_clipes.py` (reexporta sem refazer o IK, no mesmo lugar);
  `conferir_clipes.py` (confere contra o corpo aprovado, com o corpo no posto e a roda física girando como no jogo).
- **Arquivos (raiz e `variante_r06`, `clipes/girar_roda.glb`):** antes, Armature 0,004 e chaves de 0,0417 a
  2,0417 s; agora nó Armature sem escala, **chaves de 0 a 2,0 s, 49 chaves, 24 fps**, sem malha.
- **Conferência (`assets/previews/prova_operacao/[variante_r06/]conferencia_clipes.json`):** mesmos 24 ossos;
  repouso igual ao do `aldeao_corpo.glb` a **0,0054 mm** e 0,00002°; palma-manopla nos 48 quadros igual à de antes
  a **0,1 mm** (arredondamento): raiz 35,4 mm (antes 35,4), variante **2,4 mm** (antes 2,5).
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~40 min.

## 2026-09-29 — Prova de operação: girar_roda.py exporta pelo contrato e gera um clipe por posto

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido (passo 4 do pedido):** `operacao_lib.py` e `girar_roda.py` exportando sempre pelo contrato (metros, t = 0,
  24 fps). Feito antes do passo 2 porque o clipe do posto B sai deste script.
- **Feito:** `operacao_lib.export_clip` (commit anterior) passa a ser a única saída de clipe do `girar_roda.py`; o bake
  vai do quadro 0 ao 48 (quadro = fase da roda × 48); a cena exporta a 24 fps. O script gera **um clipe por posto**:
  para cada posto, cena nova com o corpo aprovado, IK para a manopla da alça daquele posto (A: fase p; B: a alça B,
  que para o aldeão do outro lado está na fase 0,5 − p do círculo dele), bake, laço e exportação num GLB próprio.
  O `clipes.json` sai com um bloco por posto (posição e giro em relação à roda, fórmula da fase sem inverter).
  Uma conferência interna (assert) coloca cada posto em volta da roda física e confere que a manopla cai no alvo.
- **Pendência:** o `gif_roda.py` (GIFs da prova) ainda usa o atalho de tocar o clipe A ao contrário e a primeira
  chave no quadro 1; precisa ser atualizado antes de refazer os GIFs.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~30 min.

## 2026-09-29 — Prova de operação: clipe próprio do posto B (girar_roda_b-loop) e clipes.json por posto

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** clipe por IK para o aldeão B, do outro lado, segurando a alça B; a fase continua a da roda; clipes.json
  da variante_r06 com um bloco por posto; palma-manopla dos dois postos nos 48 quadros.
- **Feito:** `girar_roda.py` rodado na variante (0,06 m) e na raiz (0,10 m). Cada posto num GLB próprio:
  `clipes/girar_roda.glb` (`girar_roda-loop`, posto A) e `clipes/girar_roda_b.glb` (`girar_roda_b-loop`, posto B),
  mais limpo para o jogo carregar só o clipe do posto ocupado. Os dois: nó Armature sem escala, sem malha, chaves de
  0 a 2,0 s, 49 chaves, 24 fps, laço 0,0 cm, Hips parado. A raiz ganhou o mesmo formato.
- **Postos (espaço da roda, glTF: pivô no eixo, eixo +Z; posição = pés):** A em (0; −0,19; +0,1751), giro 180°
  (olha para −Z, a face da alça A); B em (0; −0,19; −0,1751), giro 0°. Fase: quadro = fase da roda × 48, igual nos dois.
  Na raiz, ±0,178.
- **Conferência independente (`conferir_clipes.py`: corpo aprovado posto em cada posto, roda física girando
  −360° × fase, manopla da alça do posto):** repouso igual ao do corpo a 0,0001 mm; palma-manopla nos 48 quadros:
  variante **A 2,4 mm, B 2,4 mm** no pior quadro; raiz A 35,4 mm, B 35,4 mm (o problema de alcance conhecido).
  Contra o atalho antigo (B tocando A ao contrário), a diferença é de 0,1 mm, como esperado com a roda simétrica.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~30 min.

## 2026-09-29 — .import de assets/ gerados pelo Godot sem janela (clipes a 24 fps)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** gerar com `godot --headless --import` os `.import` que faltam em `assets/`, com `animation/fps = 24` nos
  GLBs de clipe; commitar; conferir os clipes e o `.import` do corpo.
- **Cuidado antes de gerar:** a `arte` estava 33 commits atrás do `master` (e nenhum à frente), e o `master` já
  versiona `.import` de 80 arquivos que existem aqui (aldeão v2: conceitos, meshy, cabelos, rosto, corpo, prévias,
  mais as 2 texturas extraídas do corpo, `aldeao_corpo_boca.png` e `_olhos.png`). Gerar de novo daria outros `uid` e
  conflito no merge, então esses **82 arquivos vieram do `master` por `git checkout master -- <arquivo>`**, idênticos
  (sem merge). O aldeão v1, que o `master` já apagou, tem `.gdignore` nas pastas brutas e não foi tocado; nenhum
  arquivo versionado mudou com o import.
- **Gerados agora (Godot 4.7.2 mono, `godot-mono --headless --import --path .`):** 17 `.import` e 2 texturas
  extraídas: referências da protagonista v2 (5), `v1_diagnostico.png`, closes das mãos (2), `aldeao_normalizado.glb`
  e as texturas `aldeao_normalizado_boca.png`/`_olhos.png` com os seus `.import`, `roda.glb` (raiz e variante) e os 4
  GLBs de clipe. Na worktree do `master` a maioria já existia sem versionar: os `uid` batem; os dos 2 PNGs extraídos
  foram trocados pela versão de lá (compressão VRAM, que o Godot aplica ao detectar uso em 3D).
- **Clipes:** `animation/fps=24` nos 4 (`clipes/girar_roda.glb`, `clipes/girar_roda_b.glb`, raiz e variante),
  reimportados. Conferido carregando no Godot: 2,0 s, primeira chave em 0, chaves a cada 0,0417 s (1/24), laço
  ligado, esqueleto em escala 1 (48 chaves por trilha: o otimizador do importador tira uma redundante).
- **Corpo:** `aldeao_corpo.glb.import` idêntico ao do `master`. Observação: ele está com `animation/fps=30`, então o
  Godot reamostra o `idle` e o `run` do corpo a 30 fps (chaves a cada 0,0333 s); não mudei por não estar no pedido.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~40 min.

## 2026-09-29 — Corpo do aldeão v2 importado a 24 fps

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** com o aval do Arthur (a regra de 24 fps do contrato de animação vale também para o corpo), mudar só
  `animation/fps` para 24 no `aldeao_corpo.glb.import` e reimportar só esse arquivo; o GLB não muda.
- **Feito:** uma linha no `.import` (`animation/fps=30` → `24`); cache do corpo apagado em `.godot/imported` e
  `godot-mono --headless --import`; nenhum outro arquivo mudou; sha256 do GLB continua
  `11c7d12bc4c522808546f61f3136031e2fce0cc6ccf9e789abd02779d110febf`.
- **Conferência no Godot:** `idle` 10,0 s e `run` 0,75 s (as mesmas de antes), loop ligado, todas as chaves de todas as
  trilhas em múltiplos de 1/24 s a partir de 0 (antes: 1/30 s).
- **Achado:** dentro do GLB do corpo as chaves começam em 1/24 s (quadro 1 do Blender), não em 0; o corpo foi
  exportado antes da regra "primeira chave em t = 0". O importador cria uma chave em 0 igual à de 1/24 s: no `run`,
  22 de 22 trilhas de rotação repetem a pose no começo: a mesma pose aparece em 0 e em 1/24 s (0,75 s é o mesmo
  instante que 0 no laço), ou seja, **1 quadro parado a mais em cada ciclo** (~42 ms a 1×; o ciclo tem 19 amostras
  em vez de 18). No `idle`,
  8 de 22 trilhas (10 s, quase invisível). Corrigir pede reexportar o corpo com as chaves a partir de 0 (o
  `montar_rig.py` pelo `export_clip` do contrato), o que muda o sha256 do aprovado: fica para o aval do Arthur.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~15 min.

## 2026-09-29 — Aldeão v2: corpo reexportado com as chaves a partir de t = 0 (processo pelo contrato)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** com o aval do Arthur, o `montar_rig.py` e o `colocar_retalhos.py` exportam os clipes do corpo com a
  primeira chave em t = 0 pelo mesmo caminho do `operacao_lib.export_clip`; rodar do zero, conferir contra o aprovado
  (quadro k do novo contra k+1 do atual) e substituir se tudo passar; segunda execução byte a byte; sha256 novo.
- **Feito:** `rig_lib.export_contract_glb` (Armature em metros, chaves de cada ação deslocadas para o quadro 0, cena
  a 24 fps, uma faixa NLA por ação a partir do 0, POSE) é agora a única saída de GLB com animação: o
  `operacao_lib.export_clip` a chama só com o armature; o `montar_rig.py` e o `colocar_retalhos.py` a chamam com as
  malhas; `export_rig_glb` virou um nome antigo dela. `conferir_corpo.py` passou a comparar **todos** os quadros,
  alinhados pelo começo de cada clipe, e a registrar duração e laço.
- **O que deu errado:** a primeira conferência deu 67 mm. Era erro meu no `conferir_corpo.py`: o quadro da cena é um
  só, e os dois arquivos eram avaliados depois de o segundo receber o seu quadro. Corrigido: cada arquivo é avaliado
  logo depois de receber o quadro. Um teste à parte confirmou antes que o quadro k do novo = k+1 do antigo (0,0 mm).
- **Conferência (novo × aprovado anterior `11c7d12b…`):** 240 quadros do idle e 18 do run: vértices de corpo, Olhos e
  Boca **0,0 mm**; cabelos 1 a 5 **0,0 mm** (1,5 mm do corpo); mesmos quadros de duração (idle 240, run 18), laço igual
  (run 0,59 cm somados em 5 ossos, idle 0,0); passada **0,383 m/s**; folga dos retalhos **1,40 a 3,16 mm**; mesmos
  nomes; Armature sem escala. Chaves no GLB: idle de 0 a 9,9583 s, run de 0 a 0,7083 s (antes: de 1/24 s a 10,0 e a
  0,75 s; o ciclo é o mesmo, só começa um quadro antes).
- **Troca e reprodução:** aprovado substituído; segunda execução do zero **idêntica byte a byte**.
  **sha256 novo: `3138cbf652d0d840c2ab911b676bb20d3116f14172e15163c8232a3fa74b49a2`** (988.148 bytes), registrado no
  `aldeao_corpo_reproducao.json` (com o histórico). Relatórios `aldeao_corpo_rig.json` e `_retalhos.json` trocados
  pelos da execução nova. O contrato de animação (na `master`) cita o sha antigo: o agente do jogo atualiza.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~50 min.

## 2026-09-29 — Otimizador de animação do importador do Godot desligado (corpo e clipes)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** desligar o otimizador de animação do importador no `.import` do `aldeao_corpo.glb` e dos 4 GLBs de clipe
  da prova, mantendo `animation/fps = 24`; reimportar sem janela; conferir que as trilhas têm todas as chaves e que o
  run do corpo não repete pose no começo.
- **A opção certa no Godot 4.7:** `optimizer/enabled` é opção do nó AnimationPlayer da cena importada (achei o nome
  nas strings do binário 4.7.2; a categoria é a dos nós), então vai em
  `_subresources={"nodes": {"PATH:AnimationPlayer": {"optimizer/enabled": false}}}` (o AnimationPlayer é filho direto da
  raiz nos 5 GLBs, conferido no Godot). Nos 5 `.import` só o `_subresources` mudou; `animation/fps=24` ficou.
- **Conferência no Godot (depois de reimportar os 5):**
  - clipes da prova: todas as trilhas com **49 chaves** (antes 48), 2,0 s, loop ligado, chaves em múltiplos de 1/24 s;
  - corpo: `idle` 240 chaves em todas as 23 trilhas (9,958 s), `run` **18 chaves** em todas as 23 trilhas (0,708 s), loop
    ligado, chaves em múltiplos de 1/24 s; no `run`, **nenhuma** das 22 rotações repete a pose entre as chaves 0 e 1
    (antes: 22 de 22, pela chave inventada em t = 0). O número de chaves no Godot é igual ao do arquivo (49, 240, 18):
    nenhuma chave é criada nem tirada. As poucas rotações quase paradas no começo do `idle` e dos clipes da prova são do
    próprio clipe (ossos que quase não mexem naquele instante).
- **Observação:** outra opção, `animation/remove_immutable_tracks=true` (global, não mexi), tira as trilhas constantes:
  por isso o Godot mostra 10 a 12 trilhas nos clipes e 23 no corpo, contra 72 canais no arquivo (posição e escala
  constantes dos ossos). Os clipes da prova ainda têm 1 ou 2 trilhas de escala quase 1 (ruído do bake do Blender).
  Se um dia uma troca de clipe herdar a pose de um osso que o clipe novo não anima, é essa opção que se revê.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~30 min.

## 2026-09-29 — tools/arte/godot_import.py: .import de GLB com animação pelo contrato

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Contexto:** o jogo provou que osso sem trilha congela na pose do clipe anterior: com
  `animation/remove_immutable_tracks = true` o importador apaga as trilhas que não mudam, e o `girar_roda` chegava sem
  pernas, pescoço, cabeça, Spine, ombro esquerdo e posição do quadril. Regra aprovada: todo clipe, e o corpo, define a
  pose inteira.
- **Feito:** `tools/arte/godot_import.py` (Python 3 puro): `conferir` lista o que está fora do contrato (sai com 1) e
  `corrigir` escreve só o que falta: `animation/fps=24`, `animation/remove_immutable_tracks=false` e
  `_subresources → nodes → "PATH:AnimationPlayer" → "optimizer/enabled": false` (mescla com o que já houver no
  `_subresources`, no formato em que o Godot grava). O resto do `.import` fica igual. Recusa `_subresources` com tipos do
  Godot que não são JSON (ex.: `Transform3D(...)`), pedindo correção à mão; exige o `.import` já gerado pelo Godot.
- **Testes (em cópias temporárias):** num `.import` padrão, corrige as três coisas e nada mais (diff de 3 trechos);
  rodar de novo não muda nada; com um `Transform3D` no `_subresources`, recusa. `conferir` nos 5 GLBs com animação:
  só `remove_immutable_tracks = true` fora do contrato.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~20 min.

## 2026-09-29 — Corpo e clipes da prova importados com a pose inteira (trilhas constantes mantidas)

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** rodar o `godot_import.py` no `aldeao_corpo.glb` e nos 4 GLBs de clipe da prova, reimportar sem janela e
  conferir no Godot: rotação dos 24 ossos e posição do Hips em todo clipe; chaves inteiras a 24 fps a partir de 0; GLB
  do corpo sem mudança.
- **Feito:** `godot_import.py corrigir` nos 5 (só `animation/remove_immutable_tracks` estava fora: true → false; uma
  linha por `.import`); `conferir` depois: os 5 ok. Cache dos 5 apagado em `.godot/imported` e
  `godot-mono --headless --import`.
- **Conferência no Godot:** nos 4 clipes da prova (`girar_roda`, `girar_roda_b`, raiz e variante) e nos 2 do corpo
  (`idle`, `run`): **rotação para os 24 ossos** do esqueleto (nenhum faltando), **posição do Hips** presente, **72
  trilhas** (rotação, posição e escala dos 24 ossos, antes 10 a 12 nos clipes e 23 no corpo), todas com as chaves
  inteiras: **49** nos clipes (0 a 2,0 s), **240** no idle (0 a 9,958 s), **18** no run (0 a 0,708 s), todas em múltiplos
  de 1/24 s a partir de 0, loop ligado.
- **GLB do corpo sem mudança:** sha256 `3138cbf652d0d840c2ab911b676bb20d3116f14172e15163c8232a3fa74b49a2`.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~15 min.

## 2026-09-29 — Protagonista v2: recorte das vistas das folhas do corpo e dos chifres

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** começar a protagonista v2 pelo processo do aldeão v2 (contrato `docs/protagonista_v2_contrato.md`, lido
  na `master`): recortar as vistas das folhas aprovadas `corpo.png` (frente, perfil esquerdo, costas, pose A) e
  `chifres.png` (frente, perfil esquerdo, costas, topo, sobre busto careca), fundo uniforme, mesma escala por folha.
- **Feito:** `tools/arte/aldeao_v2/preparar_vistas.py` sem cópia, com `--folha`, `--saida` e **`--limiar 8`**. Saída
  em `assets/conceitos/protagonista_v2/vistas/`: `corpo_{frente,lado,costas}.png`,
  `chifres_{frente,lado,costas,topo}.png` e as prévias `_previa_corpo.png`, `_previa_chifres.png` (quadros de 1024 px,
  fundo #EBEBEB).
- **O que deu errado:** com o limiar padrão (28) a pele pálida iluminada (só 15 a 23 níveis acima do fundo #DCDCDC)
  virava fundo: 6 figuras no corpo (cabeças separadas no pescoço) e 5 nos chifres (o chifre do perfil solto da cabeça).
  O fundo das folhas é liso (±1,5 nível), então o limiar 8 separa bem: 3 e 4 figuras, pescoço, mãos e pontas dos
  chifres inteiros (conferido nas prévias).
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~15 min.

## 2026-09-29 — Protagonista v2: folha de conferência dos recortes

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** folha com cada vista e a altura em px; dizer se as três vistas do corpo batem (altura, ombros, pés), se a
  frente da cabeça está lisa e se as quatro vistas dos chifres são coerentes.
- **Feito:** `tools/arte/protagonista_v2/conferir_recortes.py` → `assets/previews/protagonista_v2/recortes.png` e
  `recortes.json` (as vistas de cada folha já estão na mesma escala; as medidas são no quadro de 1024 px).
- **Corpo:** altura 857 / 860 / 858 px (frente/perfil/costas), **0,3%**; cabeça (topo ao pescoço) 132 / 137 / 131 px;
  ombros (maior largura da faixa central de 3% a 8% da altura abaixo do pescoço) 174 / 171 px frente/costas, **1,7%**;
  pés: distância entre os centros 203 / 199 px, **2,1%** (23,7% e 23,1% da altura), largura 69–72 / 67–69 px; no perfil
  o pé tem 125 px (14,5% da altura), calcanhar 8,1% atrás do eixo da cabeça e ponta 6,4% à frente. As três batem.
- **Rosto:** liso. Na elipse do rosto, depois de tirar o sombreado suave (ajuste quadrático), o tom varia 1,96 níveis
  (desvio padrão), máximo 7,3; passa-alta (tom − desfoque de 5 px) no máximo 4,3 níveis, sem nenhuma marca de olho,
  nariz ou boca (esses dariam dezenas de níveis). O busto dos chifres, em escala maior, dá 1,74 / 2,8. Cabeça do corpo
  e do busto com a mesma proporção (largura/altura 0,87 e 0,86).
- **Chifres:** frente, perfil e costas coerentes; o **topo não**. Os chifres são assimétricos de propósito na folha (o
  direito dela é 32% mais alto que o esquerdo na frente), e as costas repetem isso espelhado. Altura do esquerdo:
  131 px na frente, 153 nas costas, 147 no perfil (11% a 15% de diferença; nas costas os dois chifres saem ~12% maiores,
  provavelmente perspectiva da imagem, com as pontas inclinadas para trás, mais perto da câmera). Distância entre os
  chifres: 370 / 381 / 346 px (frente/costas/topo, 6,5%). **Frente para trás: 182 px no perfil contra 304 e 241 px no
  topo (50%)**: no topo os chifres correm ao longo da cabeça por quase todo o comprimento dela, e no perfil ocupam cerca
  de um terço. Recomendação: gerar na Meshy com frente, perfil e costas e deixar o topo de fora (como no plano dos
  cabelos do aldeão: o topo só entra se o resultado vier errado).
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~45 min.

## 2026-09-29 — Protagonista v2: recortes do cabelo e proporção da cabeça nas três folhas

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** preparador na folha refeita e aprovada do cabelo (frente, perfil esquerdo, costas, topo, sobre busto
  careca); cabelo na folha de conferência; coerência das quatro vistas; largura ÷ altura da cabeça nas três folhas.
- **Feito:** `preparar_vistas.py --limiar 8` → `vistas/cabelo_{frente,lado,costas,topo}.png` (4 figuras inteiras);
  `conferir_recortes.py` com a fileira do cabelo e as medidas novas; folha `cabelo.png` versionada.
- **O que deu errado e foi corrigido no caminho:**
  - o preparador centraliza cada vista no seu quadro, então posição (y) não se compara entre vistas de alturas
    diferentes; as posições do cabelo passaram a ser medidas na folha original (mesma escala e chão), e os tamanhos no
    quadro de 1024;
  - a borda da silhueta, onde o escuro (cabelo, chifre) se mistura com o fundo, contava como pele e puxava o "topo"
    da cabeça para a ponta dos chifres e para o alto do cabelo: o topo passou a vir da pele estrita (clara e azulada),
    e as larguras e o queixo, da pele normal (a estrita cortaria o sombreado da borda das cabeças carecas);
  - dois métodos descartados: elipse nas bordas laterais (errava 0,08 a 0,10 nas carecas: a cabeça em ovo é mais larga
    em cima) e o ajuste do perfil da cabeça do corpo às bordas visíveis (errava 9% na altura dos chifres e punha o topo
    do cabelo abaixo da linha do cabelo).
  - A proporção que dei na entrada anterior (0,87 e 0,86, com o "pescoço" como fim da cabeça) fica substituída: o
    pescoço é comprido e a linha mais estreita escorrega nele; o marco agora é o queixo.
- **Cabelo:** frente, perfil e costas coerentes. Na folha original, topo do cabelo em 38,7 / 29,8 / 31,7 px (dif. 2,8%
  da altura da cabeça); fundo no perfil e nas costas 730 / 757 px (comprimento 3,6%; nas costas a ponta do meio desce
  mais); na frente o cabelo some atrás do busto (fica todo atrás dos ombros, como pede o contrato); largura 363 / 369 px
  frente/costas (1,6%). O **topo não bate**: 22% mais estreito que as costas e 39% mais longo de frente para trás que o
  perfil, a mesma incoerência do topo dos chifres; nas duas folhas o "topo" parece uma vista oblíqua de cima e de trás
  (alonga o que vai para trás). Recomendação igual: Meshy com frente, perfil e costas.
- **Cabeça, largura máxima ÷ (topo ao queixo), vista de frente:** corpo **0,935**; chifres **0,889** (a cabeça do busto
  é ~5% mais estreita em relação à altura que a do corpo); cabelo: o alto do crânio está coberto, então só dá a faixa
  **0,694** (topo da cabeça no topo do cabelo) a **0,782** (na linha do cabelo), com a largura do rosto visível. Se o
  busto do cabelo tem mesmo a cabeça do corpo, o cabelo cobre cerca de 25 a 45 px de cada lado da testa (no quadro de
  1024) e a calota é fina; a folha sozinha não prova isso. Para a extração: chifres com escala por eixo (~5% mais largo
  que alto); cabelo com âncoras medidas à mão, como no aldeão (`PRIOR` do `extrair_peruca.py`).
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h.

## 2026-09-29 — Visor de arte, passo 1: servidor local

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** servidor só com biblioteca padrão, em 127.0.0.1:8765, entregando só `tools/arte/visor/` e `assets/`;
  recusar a raiz, o `.env` e `..`; testar.
- **Feito:** `tools/arte/visor/servir.py` (lista de pastas permitidas; recusa com 403 arquivos ocultos, `..` mesmo
  codificado uma ou duas vezes, barra invertida, pastas e o que um link simbólico levar para fora; `/` redireciona
  para o visor; sem cache; só aceita `Host` 127.0.0.1/localhost, contra DNS rebinding). `testar_servidor.py` sobe o
  servidor, faz 27 pedidos crus por socket (para o cliente não limpar o `..`) e derruba no fim: 0 falhas, e nada fica
  escutando na 8765.
- **O que deu errado:** `/assets/` dava 404 (é pasta, não arquivo); passou a 403 explícito. O teste da porta pela
  rede não rodava (o nome da máquina resolvia para 127.0.0.1); passou a descobrir o IP da interface de saída.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~20 min.

## 2026-09-29 — Visor de arte, passo 2: página com imagem, GIF e GLB em 3D

- **Pedido:** `index.html` com three.js em versão fixa; lê `assets/previews/visor.json` a cada 2 s; mais novo em
  destaque e lista dos anteriores; imagem/GIF em tamanho real com zoom; GLB em 3D com câmera orbital, vistas, câmera
  do jogo, toon de 3 faixas, luz fria de cima, fundo #4E4A58, crepúsculo, clipes e GLBs "junto".
- **Feito:** `tools/arte/visor/index.html`, `visor.js`, `visor.css`, `personagens.json` e three.js **r169** copiado em
  `vendor/` (módulo, GLTFLoader, OrbitControls, BufferGeometryUtils, licença MIT): funciona sem internet.
  - Toon: `ShaderMaterial` com a conta do `Toon.gdshaderinc` (meio-Lambert, `floor(ndl·3)/2`, piso 0,35 por
    personagem no `personagens.json`), com pele (skinning). Cores pelo nome do material, dos contratos: aldeão pele
    #AEBFD3 e cabelo #6F7F96; protagonista pele #91ADB7, cabelo #4B5A69, chifre #2B2140, tecido #3F3342, cristal
    emissivo. Retalhos do rosto como o `VillagerFace.gdshader`: UV cru + célula da grade do `rosto.json`, quadro 0.
  - Luz: cores do sol e do ambiente do `scenes/Main.tscn`, sol vindo de cima (65°). Aproximação, sem calibrar.
  - "Junto": peça rígida vai para o osso do encaixe (cabelo/chifre → Head, cristal → Spine) compensando o repouso no
    espaço do Armature, como o jogo faz com `GetBoneGlobalRest`; corpo com esqueleto vai ao lado; GLB só de clipes
    empresta as animações ao principal.
  - Câmera do jogo: `CameraRig.cs` (55°, FOV 45°, 16 m ÷ zoom, olhando o chão sob o personagem pela frente),
    desenhada em 3024×1890 e encaixada na caixa, ou 1:1 com rolagem; mostra a altura do personagem em px.
  - Crepúsculo: camada `multiply` de #6A5B7C sobre imagem ou 3D; lembrado por visitante.
- **Conferido no portal "Visor"** (servidor subido só para o teste): cabelo 4 preso na cabeça durante idle e run,
  rosto no lugar, faixas visíveis, clipes tocam/pausam/repouso, imagem em tamanho real. Aldeão com cabelo, em
  repouso: **19 / 48 / 123 px** nos zooms 0,4 / 1 / 2,5 (a nota 01 dá 19 / 44 / 112 px, só o corpo).
- **O que deu errado:** a altura em px pela caixa envolvente saía 24 / 61 / 153 px (a profundidade da caixa entra na
  projeção inclinada); passou a projetar vértice a vértice, já com a pose do clipe.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h.

## 2026-09-29 — Visor de arte, passo 3: publicar.py

- **Pedido:** `publicar.py <caminho> <tipo> "<titulo>" "<nota>" [--junto a.glb b.glb]` acrescentando ao `visor.json`.
- **Feito:** `tools/arte/visor/publicar.py` (só biblioteca padrão). Valida que o arquivo existe, fica em `assets/`
  (o que o servidor entrega), não passa por pasta oculta e tem extensão do tipo (imagem: png/jpg/webp; gif; glb);
  `--junto` só com glb. Grava `quando` local em segundos (desempata se dois caírem no mesmo segundo) e troca o
  arquivo de uma vez, para o visor nunca ler JSON pela metade. Conferido: recusa `.env`, `docs/GDD.md`,
  `assets/../.env`, PNG como glb e `--junto` em imagem, sem criar o `visor.json`.
- **Daqui em diante toda prévia vai para o visor por este script.**
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~10 min.

## 2026-09-29 — Visor de arte, passo 4: primeiro conteúdo

- **Pedido:** publicar a folha de conferência dos recortes e o `aldeao_corpo.glb` com o `cabelo_4` junto, como prova
  do 3D, dos clipes e da câmera do jogo.
- **Feito:** dois itens em `assets/previews/visor.json` pelo `publicar.py`. No portal "Visor" do Maestri: o visor
  trocou sozinho para o item novo na sondagem; conferência em tamanho real; aldeão com cabelo 4 no osso Head, idle e
  run tocando, câmera do jogo nos três zooms, 1:1 desenhando 3024×1890 pixels de tela (1512×945 CSS com dpr 2).
  Servidor derrubado no fim; o portal fica aberto no canvas apontando para http://127.0.0.1:8765/.
- **Pendente:** calibrar a luz do visor contra uma captura do jogo (hoje é aproximação com as cores do
  `Main.tscn` e o sol de cima); o piso 0,5 e a borda fria da protagonista ainda não existem no shader do jogo, então
  o visor usa 0,35 para os dois.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~15 min.

## 2026-09-29 — Protagonista v2, passo 2A: corpo na Meshy, só a frente

- **Agente / modelo:** Claude Code + Opus 5.5, agente de ARTE na branch `arte`.
- **Pedido:** corpo na Meshy, teto de 3 gerações e 60 créditos (aval do Arthur em 29/09/2026); geração A com
  `corpo_frente.png`, sem textura, pose A; brutos em `assets/modelos/protagonista_v2/meshy/` com id e custo.
- **Feito:** `tools/arte/protagonista_v2/meshy_corpo.py`, com os parâmetros do corpo aprovado do aldeão
  (`ai_model` latest, sem textura, `a-pose`, remesh em triângulos, alvo 2.500, simetria automática). Travas: 3
  gerações, 60 créditos contados no estado, saldo e custo previsto conferidos antes de cada geração; a 3ª só sai com
  `--reserva`. O registro público (ids, créditos, parâmetros; sem chave) vai em `meshy/corpo_meshy.json`.
- **Geração A:** tarefa `01a0efa8-beea-71aa-806a-73567944494f` (image-to-3d), **20 créditos** (saldo 2.298 → 2.278).
  `corpo_a_frente_1.glb`, 124 KB, 2.602 triângulos brutos, uma malha sem material, 1,90 m de altura bruta.
- **Créditos:** 20 (acumulado nesta parte: 20/60). **Correções manuais:** nenhuma. **Tempo:** ~15 min.

## 2026-09-29 — Protagonista v2, passo 2B: corpo na Meshy, frente + perfil + costas

- **Geração B:** tarefa `01a0efaa-2e6e-72fb-a1a6-8d343e404f45` (multi-image-to-3d, `corpo_frente`, `corpo_lado`,
  `corpo_costas`, sem o topo), mesmos parâmetros da A, **20 créditos** (saldo 2.278 → 2.258).
  `corpo_b_multi_1.glb`, 124 KB, 2.620 triângulos brutos, uma malha sem material, 1,90 m de altura bruta.
- A reserva (3ª geração) **não foi usada**: nenhuma das duas falhou tecnicamente no download (a conferência
  visual vem na folha de contato).
- **Créditos:** 20 (acumulado nesta parte: 40/60). **Correções manuais:** nenhuma. **Tempo:** ~5 min.

## 2026-09-29 — Protagonista v2, passo 2C: folha de contato dos corpos brutos

- **Pedido:** uma fileira por geração (frente, lado, 3/4, câmera do jogo nos três zooms), aldeão v2 ao lado,
  protagonista a 0,80 m, material fosco chapado, luz baixa e fria de cima, versão crepúsculo; altura em px, triângulos,
  cabeça contra a folha (0,935), mãos, pés, simetria e anatomia marcada.
- **Feito:** `render_meshy.py` (Blender; toon do `prot_lib`, luz do diagnóstico aprovado da v1; câmera do jogo em
  3024×1890 e altura por projeção de vértices) e `folha_meshy.py` (recortes 1:1 da câmera do jogo; cabeça pelo
  mesmo `head_profile` do `conferir_recortes.py`). Saída: `assets/previews/protagonista_v2/meshy_corpo.png`,
  `meshy_corpo_crepusculo.png` e `meshy_corpo.json`; notas em `tools/arte/protagonista_v2/notas_meshy_corpo.json`.
- **Medidas (A / B):** triângulos 2.602 / 2.620; câmera do jogo 32 / 81 / 215 e 32 / 80 / 212 px (alvo 28 / 68 / 179);
  cabeça L÷A 0,915 / 0,901 (folha 0,935); cabeça 14,0% / 14,1% da altura (folha 14,4%); simetria: espelho a 4,3 mm
  em média nas duas (p95 ~10,7 mm). O aldeão ao lado mede 17 / 43 / 111 px (nota 01: 19 / 44 / 112): a medida está
  calibrada.
- **Observação para o Diretor:** a 0,80 m do contrato a protagonista sai ~19% acima do alvo em px nos três zooms
  (215 contra 179). O alvo pede 1,6× a altura do aldeão; o contrato dá 2×. Um dos dois precisa mudar (0,80 m → ~0,67 m
  bate o alvo); não mudei nada.
- **O que deu errado e foi corrigido:** a projeção e a "direita da câmera" usavam a `matrix_world` da câmera antes de o
  Blender atualizar a cena (px absurdos e aldeão atrás da protagonista no perfil); passou a atualizar a cena ao criar a
  câmera. A troca de ponto por vírgula nos números não mexe mais nas vírgulas do texto.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h.

## 2026-09-29 — Protagonista v2, passo 2D: folha e corpos brutos no visor

- **Feito:** publicados no visor os dois GLBs brutos (com o aldeão v2 junto), a folha de contato e a versão
  crepúsculo; o portal "Visor" ficou na folha. Para o GLB bruto (1,90 m, sem material) aparecer em escala, o
  `publicar.py` ganhou `--altura` (o visor normaliza o principal a essa altura, pés no chão, como o
  `render_meshy.py`) e o visor pinta material sem nome com a pele do personagem.
- **Nota:** o servidor do visor já estava no ar pelo terminal "Visor" (processo `servir.py` desta worktree); não mexi
  nele.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~15 min.

## 2026-09-29 — Protagonista v2: estudo de proporção da cabeça (só prévia)

- **Pedido:** medir cabeça ÷ altura da v1 nas referências; sobre o bruto B, sem salvar GLB, cabeça escalada a partir
  da base do pescoço para 14% (atual), 18% e a proporção da v1, em 0,80 m e 0,67 m; folha com frente e câmera do jogo
  (0,4 / 1 / 2,5), aldeão v2 ao lado, px medidos, crepúsculo e a v1 renderizada como referência.
- **Feito:** `medir_cabeca_v1.py` (Blender: topo = ponto mais alto; queixo = vértice mais baixo do rosto, osso Head, metade
  da frente, perto da linha do meio; linhas conferidas sobre `v1_frente.png` e `v1_lado.png`), `estudo_cabeca.py`
  (marcos do B na máscara de frente e montagem da folha) e `render_estudo_cabeca.py` (Blender: deforma só na memória;
  cabeça escalada acima da base do pescoço com uma faixa de 1,5 cm que só alarga, depois a figura inteira à altura
  pedida). Saída: `assets/previews/protagonista_v2/estudo_cabeca.png`, `_crepusculo.png` e `.json`. O `render_meshy.py`
  ganhou a guarda `if __name__ == "__main__"` (é importado pelo estudo).
- **Medidas (topo ao queixo ÷ altura):** v1 **18,8%** (0,80 m, cabeça 15,0 cm, com o cabelo do topo), aldeão v2 **44,4%**,
  bruto B **14,1%**. Como 18% e 18,8% quase coincidem, acrescentei **22%** (a estimativa do Diretor). Fatores da cabeça:
  1,35× (18%), 1,43× (v1), 1,77× (22%). Câmera do jogo: todas as variações a 0,80 m dão ~31 / 80 / 212 px; a 0,67 m,
  ~26 / 67 / 175 px; a v1 dá **26 / 67 / 178 px**.
- **Correção do que eu disse no passo 2C:** o alvo de 179 px não pede ~0,67 m. A v1 tem os mesmos 0,80 m do contrato e
  dá 178 px; o B a 0,80 m dá 212 px porque a câmera a 55° soma a profundidade: na projeção a v1 ocupa 0,451 m (cabeça
  pendendo para a frente, pés que não avançam) e o B 0,544 m (ereto, nuca atrás, dedos dos pés 6,5 cm à frente); a razão
  1,21 é a dos px. Os px na câmera dependem da pose e ficam para depois do rig.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h 15 min.

## 2026-09-29 — Prova de operação: gif_roda.py com um clipe por posto (pendência do aldeão)

- **Pedido:** o `gif_roda.py` ainda tocava o clipe A ao contrário no posto B (atalho proibido pelo contrato); usar um
  clipe por posto (`girar_roda-loop` e `girar_roda_b-loop`), posicionado pela fase da peça, como o jogo; refazer os GIFs
  e comparar com os antigos. Sem mexer no corpo aprovado (sha256 3138cbf6… conferido) nem nos clipes.
- **Feito:** a cena sai do `clipes.json`: cada aldeão na posição e no giro do seu posto no espaço da roda
  (glTF → Blender), cada um com a sua ação importada do seu GLB de clipe; os dois pela mesma fase, quadro = fase × 48;
  a roda gira −360° × fase em volta do +Z do glTF. A cena inteira é girada −90° em Z para o enquadramento ficar o dos
  GIFs anteriores. Refeitos os GIFs de `assets/previews/prova_operacao/` e de `variante_r06/`, com as medidas.
- **O que deu errado e foi corrigido:** o script já não rodava com o `clipes.json` atual (o raio mudou de `roda` para
  `peca`); e a segunda metade da pendência: o clipe importado começa no quadro 0 (t = 0), então `frame_set(1 + t)`
  deixava os aldeões 1 quadro (7,5°) atrás da roda — as faltas palma-manopla subiam de 34/35 para 36/37 mm. Com
  quadro = fase × 48 voltaram exatamente às antigas.
- **Comparação com os antigos:** **nada mudou visualmente.** Diferença máxima de 1 pixel por quadro (limiar 24 níveis)
  nas quatro animações (jogo e lado, raio 0,10 e 0,06), sem defasagem de fase; faltas palma-manopla iguais
  (0,10 m: 34,3 / 35,4 mm; 0,06 m: 1,5 / 2,4 mm, antes 2,5). O clipe próprio do B reproduz a pose que o atalho dava.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~40 min.

## 2026-09-29 — Protagonista v2, passo 3A: limpeza do corpo (B, cabeça 18%, 0,80 m)

- **Pedido:** limpar o bruto B com o aval do Arthur (cabeça 18%, 0,80 m): escala, simetria, cabeça escalada a partir da
  base do pescoço, Taubin com passe extra nas pernas, tirar clavícula/esterno/joelhos marcados e a borda do short
  gravada, um pouco de glúteo e costas no perfil, 8 regiões + roupa_intima, materiais pele e tecido, mãos meio fechadas,
  ≤ 2.500 triângulos, frente da cabeça lisa. Sem rosto e sem rig.
- **Feito:** `tools/arte/protagonista_v2/limpar_corpo.py` → `assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb`
  (sem rig) e `protagonista_corpo_limpeza.json`. Fundidos 2.141 vértices duplicados da Meshy; simetria pelo lado +x
  (frente da cabeça mais lisa); cabeça × 1,355 a partir da base do pescoço (marcos do estudo ebb6705) e o corpo inteiro
  × 0,940 de volta a 0,80 m → **cabeça 18,05%**; glúteo até 6 mm para trás e lombar 3 mm para dentro (só deslocando
  vértices); Taubin 6 passes no corpo, +10 nas pernas, +25 na clavícula/esterno, joelhos, cotovelos, bordas do short e
  base do pescoço; mãos fora do alisamento; cabeça subdividida e 90 passes; decimação com simetria segurando juntas e
  mãos; cortes retos no cós e na bainha (a borda pele/tecido). Normais suaves da malha inteira copiadas para as peças.
- **Resultado:** 0,80 m, **2.474 triângulos**: cabeca 386, tronco 394, bracos 284, maos 442, quadril 32, roupa_intima
  462, coxas 232, canelas 136, pes 106. Materiais "pele" #91ADB7 e "tecido" #3F3342, 9 malhas com os nomes do contrato.
- **Frente da cabeça:** a medida do aldeão (desvio contra elipsoide) não serve para a cabeça em ovo com queixo (dá 3 mm
  de RMS só pelo formato); criei uma que só pega calombos: resíduo de uma superfície cúbica na janela do rosto (±45°, do
  queixo a 70% da cabeça): **RMS 0,76 mm, máx 1,64 mm** depois de decimar (antes de decimar, com a cabeça densa, 0,93 /
  4,49 mm no canto do queixo; a meta de 0,5 / 1,5 mm não chegou em 90 passes). A olho, lisa.
- **Escolhas (não estavam no pedido):** `roupa_intima` é o próprio short (material tecido) e `quadril` é a faixa de
  pele da bacia acima do cós, sem casca duplicada (a calça esconde as duas juntas no `equipment.json`); as outras
  bordas de região seguem as faces (só aparecem com a roupa que esconde a região; cortá-las retas custava ~700
  triângulos). As mãos ficaram com 18% do orçamento para manter o meio fechado.
- **O que deu errado e foi corrigido:** cortes retos em todas as bordas somavam 896 triângulos (e o do ombro pegava a
  cabeça); ficaram só os do short. A primeira medida da cabeça (a do aldeão) não convergia por causa do formato.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~1 h 30 min.

## 2026-09-29 — Protagonista v2, passo 3B: folha de contato do corpo limpo

- **Feito:** `render_limpo.py` (Blender: frente, lado, costas, 3/4 com o aldeão ao lado; câmera do jogo nos três zooms;
  regiões pintadas; máscara) e `folha_limpo.py` → `assets/previews/protagonista_v2/corpo_limpo.png`, `_crepusculo.png` e
  `.json`. Publicados no visor a folha, a versão crepúsculo e o GLB limpo com o aldeão junto; portal "Visor" na folha.
- **Medidas:** 0,800 m; 2.474 triângulos; cabeça 18,05% pela conta e **18,3% pela silhueta** (head_profile das folhas);
  câmera do jogo 31 / 80 / 211 px (aldeão 17 / 43 / 111). Como no estudo, a diferença para o alvo de 179 px é a pose
  (A, ereta) e não a altura; volta a medir depois do rig.
- **Pendente:** `ergonomia.json` — o `medir_ergonomia.py` precisa do rig (ossos Hips, Spine, braços e IK); sai logo
  depois do rig, que não fazia parte desta tarefa.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~30 min.

## 2026-09-29 — Protagonista v2, passo 3C: triângulos das mãos para a cabeça

- **Pedido:** mãos (442, 18%, quase somem de cima) para ~200 mantendo o meio fechado; a sobra para a cabeça, que domina
  na câmera do jogo e estava facetada (386); sem mudar os 18%; total ≤ 2.500.
- **Feito:** a decimação do `limpar_corpo.py` passou a ser por orçamento, em três etapas (mãos 200, cabeça 620, resto do
  corpo 1.350 com as juntas seguras), cada uma com as outras partes travadas (peso 0 no grupo de vértices trava de
  verdade). Depois, 4 passes de Taubin só nas mãos, para tirar as pontas da decimação.
- **Resultado:** cabeca **652**, maos **226**, tronco 382, bracos 264, quadril 36, roupa_intima 458, coxas 228, canelas 136,
  pes 98 = **2.480**; cabeça 18,05%, 0,80 m. Frente da cabeça (calombos na janela ±45°): RMS 0,98 mm, máx 2,75 mm — a
  janela agora tem 51 vértices (antes 17), então a medida enxerga mais; a olho, crânio e frente mais redondos.
- **O que deu errado e foi corrigido:** pesos diferentes para mãos e cabeça numa decimação só davam resultado caótico
  (cabeça 1.236 e mãos 16; quadril sumindo; pesos diferentes com o mesmo resultado) — daí as etapas. Um Taubin extra na
  cabeça depois de decimar piorou a medida (1,14 / 3,78 mm) sem ganho visível; ficou de fora.
- **Créditos:** 0. **Correções manuais:** nenhuma. **Tempo:** ~45 min.

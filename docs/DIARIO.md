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

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

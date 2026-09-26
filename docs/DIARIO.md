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

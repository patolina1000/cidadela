# Cenário — proposta de objetos do mundo (29/09/2026)

Proposta do agente CENÁRIO para o Diretor e o Arthur. Não é contrato: o contrato vai para `docs/` no master só depois
do "manda".

## Ponto de partida (master, sem mudanças)

- **Célula = 1 m** (`WorldView.CellCenter`: centro em x+0,5, z+0,5). Um nó de recurso ocupa uma célula.
- Hoje cada recurso é um cubo de 0,8 m (base no chão, cor do item em `data/items.json`): madeira #6B5B4B,
  pedra #A89F91, ferro #1E2A3A. Coletar encolhe o cubo até 55 % e ele sacode; esgotado, estoura e some, e a
  grama volta.
- Escala de referência: aldeão 0,40 m, protagonista 0,80 m, cabana de ofício ~0,83 m, fundição ~1,16 m.
- Câmera: 55°, FOV 45°, 16 m ÷ zoom (0,4 a 2,5). No zoom 0,4 um metro dá ~47 px em 3024×1890: tudo abaixo de
  ~4 cm vira 2 px e some, então não entra.

## Objetos que o GDD pede

| Objeto | Base no GDD | Agora? |
| --- | --- | --- |
| Árvore (madeira) | seções 4 e 10, recurso do MVP | **sim, piloto** |
| Pedra (pedreira) | seções 4 e 10, recurso do MVP | sim, depois da árvore |
| Veio de ferro | seções 4 e 10, recurso do MVP; "Piso e chão": minério é mancha no chão + pedrinhas 3D | sim |
| Veios de cobre, estanho, carvão; cristal de mana | seção 4, eras seguintes | não (mesma família do veio de ferro, trocando a cor) |
| Ervas e cogumelos | seção 4, "hortas e florestas" | não (quando a alquimia entrar) |
| Enfeites | o GDD **não** pede arbustos, tocos soltos nem flores | não; só o toco como estado de esgotado (abaixo) |

## Ficha por objeto

| | Árvore | Pedra | Veio de ferro |
| --- | --- | --- | --- |
| Pegada | 1 célula; tronco perto do centro, copa ≤ 1,1 m de diâmetro (pode passar um pouco da célula) | 1 célula, 0,7–0,9 m | 1 célula, 0,7–0,9 m |
| Altura | **2,1–2,6 m**, copa a partir de ≥ 1,0 m (revisão 3) | 0,35–0,55 m | 0,30–0,45 m |
| Triângulos | ≤ 400 | ≤ 200 (piloto: 76–112) | ≤ 200 (piloto: 68–104) |
| Cores | tronco terra #4A3B3A, lama #2E2931 ou terra arroxeada #3F3342; copa musgo acinzentado #4E5544 ou líquen roxo #6B4F7C | pedra fria #66636B, sombra lama #2E2931, uma com tampa de musgo #4E5544 | rocha lama #2E2931 + pedra fria #66636B; lascas de minério azul meia-noite #1E2A3A (a cor do ferro no jogo) |
| Variações | 4: gota, dupla, tufos, alta (tronco torto torcido, ponta da copa dobrada); sorteio 30/30/10/30 % | 4 seixos macios: bloco com tampa de musgo, dupla, pilha em espiral, laje | 4: leque, cruzado, coroa, torre (lascas facetadas sobre rocha macia) |
| Esgotado | **toco** (malha própria, ~40 triângulos) no lugar ou some, como hoje | some; opcional: 2–3 lascas chatas no chão | **fica a mancha no chão** (tipo de terreno, GDD "Piso e chão"); a rocha some |

O que fazer ao esgotar é regra de jogo: fica para o Diretor e o Arthur. O mais simples é continuar sumindo
como hoje; o toco e a mancha só entram se forem pedidos.

**Altura da árvore (revisão 3, pedido do Arthur):** os personagens não podem alcançar as folhas, então a copa
começa a ≥ 1,0 m (acima da protagonista, 0,80 m) e a árvore fica com 2,1–2,6 m, com ~1 m de tronco livre. A 55°
ela esconde quem está ~1 m atrás (medido: 0–3 % do corpo aparece); a 0,5 m o personagem aparece por baixo da copa
e a 2 m volta a aparecer. O JOGO vai esmaecer a copa com personagem atrás. (Proposta inicial era 1,3–1,7 m.)

## Contrato de cenário: regras gerais propostas

1. **Unidades e eixos:** metros; 1 célula = 1 m; Y para cima; **frente +Z** (glTF). Transformações aplicadas.
2. **Pivô no centro da base:** a origem é o ponto do chão no centro da célula; nada abaixo de y = 0 além de 2 cm
   de "raiz" enterrada para não flutuar em chão irregular.
3. **Qualquer giro serve:** o objeto não pode ter lado feio; o jogo sorteia o giro em Y (0–360°) e a escala
   (0,9–1,1) por instância, além da variação. Isso multiplica a variedade sem arquivo novo.
4. **Arquivos:** `assets/cenario/<objeto>/<objeto>_<n>.glb`, um nó raiz, uma malha, sem esqueleto nem animação
   (balanço de vento, se vier, é shader no jogo). Estado esgotado em arquivo próprio (`arvore_toco_<n>.glb`).
5. **Material chapado por cor:** um material por papel (`tronco`, `copa`, `pedra`, `minerio`), cor da paleta da
   seção 17 no `baseColorFactor` (linear), fosco (roughness 1, metallic 0), **sem textura pintada**. O jogo pode
   trocar pelo seu shader toon lendo o nome do material.
6. **Detalhe:** formas grandes; nenhuma peça mais fina que ~5 cm (some no zoom 0,4); orçamento de triângulos da
   ficha acima; normais suaves nas massas redondas (copa, rocha) e facetadas onde a faceta é o desenho (tronco
   torcido).
7. **LOD:** o LOD0 é o modelo; o Godot gera os LODs na importação (`meshes/generate_lods`), que basta nessas
   contagens. Tudo vai em MultiMesh por tipo e pedaço do mapa (GDD seção 13).
8. **Sombra:** só as massas grandes (copa, tronco, rocha) projetam sombra, na cascata perto; lascas e toco não.
9. **Prova antes de aprovar:** folha de contato na câmera do jogo (3024×1890, zooms 0,4 / 1 / 2,5), com aldeão e
   protagonista ao lado, grupo misturado, personagem atrás e versão crepúsculo × #6A5B7C.

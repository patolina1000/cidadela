# CONTRATO CENÁRIO — interface entre arte (cenário) e jogo — RASCUNHO

Rascunho do agente CENÁRIO (29/09/2026), feito a partir de `assets/cenario/PROPOSTA.md`. Só vale depois do manda do
Arthur; então o JOGO grava em `docs/cenario_contrato.md` no master.

Mudanças só com aval do Arthur: quem precisar mudar algo, para e pergunta.

## ENTREGAS DO CENÁRIO

- `assets/cenario/cenario.json`: manifesto (famílias, variações, pesos, alturas, triângulos, borda, sombra).
- `assets/cenario/arvore/arvore_1.glb` … `arvore_4.glb`; `assets/cenario/pedra/pedra_1.glb` … `pedra_4.glb`;
  `assets/cenario/veio/veio_1.glb` … `veio_4.glb`.
- Opcionais, se o Arthur escolher deixar restos: `arvore/toco_1.glb` … `toco_4.glb`, `veio/mancha_1.glb`, `mancha_2.glb`.
- `assets/cenario/verificacao.json` (saída de `tools/arte/cenario/verificar.py`, que confere as regras abaixo).

## ESCALA E ORIENTAÇÃO

- Metros; 1 célula = 1 m. Y para cima, frente +Z do glTF; transformação do nó identidade.
- Pivô no centro da base: a origem é o ponto do chão no centro da célula; o centro da caixa do que toca o chão fica
  a menos de 12 cm da origem.
- Até 6 cm enterrados abaixo de y = 0 (a árvore inclinada afunda o pé do lado para onde tomba); nada flutua.
- Nenhum lado é "o de frente": o jogo sorteia por instância o giro em Y (0–360°) e a escala (0,9–1,1).

## MALHA E MATERIAIS

- Um nó, uma malha; sem esqueleto, animação nem textura. Balanço de vento, se vier, é shader no jogo.
- Materiais nomeados pelo papel, cor chapada no `baseColorFactor`, fosco (roughness 1, metallic 0):
  `tronco`, `copa`, `pedra`, `minerio`, `madeira` (o corte do toco), `musgo` (a tampa da pedra 1).
  O jogo troca pelo shader toon lendo o nome.
- Nenhuma peça mais fina que ~5 cm (some no zoom 0,4). Normais suaves nas massas redondas (copa, pedra, rocha do
  veio); facetadas no tronco torcido, nas lascas de minério e no toco.

## FAMÍLIAS

| Recurso | Variações | Altura | Triângulos | Cores |
| --- | --- | --- | --- | --- |
| wood (árvore) | 1 gota, 2 dupla, 3 tufos, 4 alta | 2,10–2,63 m; copa a partir de ≥ 1,0 m | ≤ 400 (176–328) | tronco #4A3B3A, #2E2931 ou #3F3342; copa musgo #4E5544 (1, 2, 4) ou líquen #6B4F7C (3) |
| stone (pedra) | 1 bloco com musgo, 2 dupla, 3 pilha, 4 laje | 0,40–0,54 m | ≤ 200 (76–112) | pedra #57535F; musgo #4E5544 |
| iron (veio) | 1 leque, 2 cruzado, 3 coroa, 4 torre | 0,34–0,44 m | ≤ 200 (68–104) | rocha #2E2931; minério #1E2A3A |

- Pegada: 1 célula (a do nó). Só a copa passa da célula, até 1,06 m no pior giro (a 4, alta); `overhang` no
  manifesto. A copa começa acima da protagonista (0,80 m): os personagens passam por baixo.

## SORTEIO

- Por célula de recurso, pelo `weight` do manifesto: árvore 30 / 30 / 10 / 30 % (líquen raro), pedra e veio 25 %
  cada.

## BORDA FRIA E SOMBRA

- Borda de luz fria do toon (opção b, aprovada pelo Arthur) nos materiais listados em `coldRim`: copa; pedra e musgo;
  rocha e minério do veio; manchas. Tronco e toco sem borda. A borda ainda não existe no `Toon.gdshaderinc`: é
  tarefa do JOGO; a arte a aproximou no Blender (faixa dura, cor do sol frio × 0,10).
- Projetam sombra só as massas grandes (`castsShadow`: árvore, pedra, veio), na cascata perto; toco e mancha não.
- O JOGO esmaece a copa quando um personagem está atrás dela (a ~1 m atrás, a árvore esconde de 97 a 100 % do corpo
  no zoom 1).

## LOD

- O GLB é o LOD0. Basta o LOD automático do Godot na importação (`meshes/generate_lods`, ligado por padrão). Um LOD
  próprio de ~50 % não compensa: no zoom 0,4 (o mais longe), o triângulo mediano tem 17–42 px² (árvore, pedra, veio)
  e os 10 % menores ainda 5–16 px², longe da faixa cara (< ~4 px², um quadrado de 2×2); cortar pela metade quadraria
  a copa de 8 lados. Só o toco e a mancha têm triângulos menores (as raízes e lascas, 1,4–2,7 px² nos 10 % menores),
  mas somam 30–42 triângulos e não projetam sombra.
- Tudo vai em MultiMesh por tipo e pedaço do mapa (GDD, seção 13).

## ESGOTADO (decisão do Arthur, opcional)

- Sem decisão, o nó some ao esgotar (como hoje) e a grama volta.
- Toco: `depleted.pick = "sameIndex"`: o toco do mesmo índice da árvore, no mesmo giro e escala da instância.
- Mancha do veio: sorteio 50 / 50 entre placa e lascas. A pedra esgotada some.

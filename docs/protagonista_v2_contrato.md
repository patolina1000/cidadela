# CONTRATO PROTAGONISTA V2 — interface entre arte e jogo

Mudanças só com aval do Arthur: quem precisar mudar algo, para e pergunta.

Vale junto com `docs/animacao_contrato.md` (esqueleto, clipes, operação, ergonomia e encaixes). O inventário do
que a v1 deixa para trás está em `docs/protagonista_v2_inventario.md`.

## ENTREGAS DA ARTE

Tudo em `assets/modelos/protagonista_v2/`:

- `protagonista_corpo.glb`;
- `cabelo.glb`, `chifres.glb`, `cristal.glb`;
- `rosto/olhos.png`, `rosto/boca.png`, `rosto/rosto.json`;
- `clipes/clipes.json`;
- `ergonomia.json`;
- o sha256 do corpo aprovado, registrado ao lado dele.

## ESCALA E ORIENTAÇÃO

- Metros. Altura de 0,80 m, que mantém 28 / 68 / 179 px nos zooms 0,4 / 1 / 2,5.
- Pés em y = 0, pivô entre os pés.
- Frente para +Z do glTF. O jogo gira 180° ao instanciar.

## CORPO

- No máximo 2.500 triângulos, somando todas as regiões.
- Dividido em 8 malhas no mesmo esqueleto, que o jogo pode esconder: "cabeca", "tronco", "bracos", "maos",
  "quadril", "coxas", "canelas", "pes".
- Roupa íntima (short de pano) numa malha própria, "roupa_intima", junto do quadril.
- Materiais chapados: "pele" e "tecido".
- Careca, sem rosto, sem cristal.
- Mãos meio fechadas na malha.
- A arte NÃO exporta encaixes; quem cria é o jogo.

## ESQUELETO

- Rig da Meshy, 24 ossos, pelo contrato de animação.
- `ossoCabeca`: "Head".
- `ossoPeito`: "Spine", o osso de cima da coluna, onde fica o cristal. O aldeão usa "Spine02"; essa questão
  fica em aberto só para ele.

## ROSTO

- Retalhos "Olhos" e "Boca", como no aldeão:
  - a 2 mm da pele;
  - peso 100% no osso Head, e a pele da frente da cabeça também;
  - janela até ±45°;
  - materiais "rosto_olhos" e "rosto_boca".
- Atlas próprio, com identidade diferente da do aldeão:
  - olhos amendoados, sem pupila;
  - 3 cílios longos no canto externo;
  - olheira mais funda;
  - fissura fina sob o olho esquerdo;
  - boca reta e curta.
- Expressões iniciais: "neutra_cansada" (padrão), "esforco", "dor", "piscar" e "olhar_cristal".
- `rosto.json` no formato do aldeão (`docs/aldeao_v2_contrato.md`, seção ATLAS).

## CABELO

- Longo, uma malha, no máximo 1.000 triângulos, material "cabelo".
- COM pesos: a calota 100% no Head e a parte de trás em gradiente por neck, Spine e Spine01.
- Todo atrás dos ombros. Nunca atravessa os braços nos clipes aprovados.

## CHIFRES

- Rígidos, no máximo 300 triângulos o par, material "chifre", no espaço do corpo em repouso.
- O jogo prende no encaixe "Chifres" (osso Head).
- NUNCA somem: nenhuma peça de cabeça os esconde.

## CRISTAL

- No máximo 60 triângulos, material "Cristal", o único emissivo.
- O jogo prende no encaixe "Peito" (osso Spine).
- Mantém a luz azul e a camada de render própria da v1 (`docs/protagonista_v2_inventario.md`, seção 5).
- Toda peça de tronco deixa uma janela no peito ou declara quantos mm o cristal avança (`cristalFrente_mm`).

## SHADER

- O mesmo `Toon.gdshaderinc` do aldeão, com dois parâmetros novos: borda de luz fria (fresnel em faixa) e piso de
  sombra.
- A protagonista usa a borda ligada e o piso por volta de 0,5. O aldeão fica como está: borda desligada, piso 0,35.
- Sem transparência real.

## CORES (provisórias, decididas na prévia, ficam em data/)

- pele #91ADB7 (medida na v1)
- cabelo mais escuro que a pele, ponto de partida #4B5A69
- chifre #2B2140
- tecido da roupa íntima #3F3342

## CLIPES

- No corpo: `idle-loop` e `run-loop`. Ela só corre.
- A passada vai em `passada_m_s`, no `clipes/clipes.json`.
- A `speed` de `data/castellan.json` será reajustada pela passada nova.

## EQUIPAMENTO (estrutura agora, peças depois)

A estrutura em dados está em `data/equipment.json`.

- Roupas são malhas com pesos no mesmo esqueleto, no espaço do corpo em repouso.
- Cada peça declara as regiões do corpo que esconde.
- Armas, escudo, elmo e chapéu são rígidos, presos aos encaixes do contrato de animação: "MaoDireita",
  "MaoEsquerda", "Costas" e "Chapéu".
- Arma: empunhadura na origem, lâmina ou haste para +Y, frente +Z. As de duas mãos trazem um nó "Apoio", onde vai a
  segunda mão.
- Cada arma declara uma postura: "desarmada", "uma_mao", "duas_maos", "arco", "cajado", "escudo" ou "magia_leve".
  - Os clipes seguem o padrão `idle_<postura>` e `run_<postura>`, com a desarmada como reserva.
  - A parte de cima do corpo muda por postura, com filtro por osso. As pernas são compartilhadas.
- Ao operar máquina, a arma vai para "Costas".
- Peças de cabeça declaram "cobre" (nenhum, parcial ou total) só para o cabelo. Os chifres, nunca.
- A capa fica por baixo do cabelo.
- Limites de triângulos:

  | Peça | Triângulos |
  |---|---|
  | calça | 600 |
  | túnica | 700 |
  | robe | 900 |
  | capa | 500 |
  | sapato | 200 |
  | bota | 300 |
  | sandália | 200 |
  | armadura de pé | 400 |
  | chapéu | 400 |
  | elmo | 500 |
  | arma de uma mão | 400 |
  | arma de duas mãos e cajado | 500 |
  | arco | 400 |
  | varinha | 150 |
  | tomo | 250 |
  | escudo | 300 |

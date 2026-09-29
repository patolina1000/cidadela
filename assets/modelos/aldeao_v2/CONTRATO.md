# Contrato do aldeão v2 — interface entre arte e jogo

Texto do Arthur, recebido em 29/09/2026. Mudanças só com aval dele: quem precisar mudar algo, para e pergunta.
A pasta `assets/modelos/aldeao_v2/` recebe as entregas listadas aqui; as folhas de entrada ficam em
`assets/conceitos/aldeao_v2/`.

## Entregas da arte

- `assets/modelos/aldeao_v2/aldeao_corpo.glb`
- `assets/modelos/aldeao_v2/cabelos/cabelo_1.glb` … `cabelo_5.glb` (depois: `cabelo_N_sob_chapeu.glb`)
- `assets/modelos/aldeao_v2/rosto/olhos.png`, `boca.png`, `rosto.json`

## Escala e orientação

- Metros. Pés em y = 0, pivô entre os pés.
- Mesma direção de frente da protagonista e do aldeão v1.
- Altura aproximada de 0,40 m (bate na cintura da protagonista, que tem ~0,75 m). Ajustar vendo os dois lado a lado.

## Corpo

- Uma malha com no máximo 2.500 triângulos.
- Um único material chamado "pele", cor chapada e sem textura. O jogo troca pelo shader toon e pinta a cor definida em `data/`.
- Careca, sem rosto, sem cristal.

## Esqueleto

- Rig do Meshy.
- O nome do osso da cabeça vai registrado em `rosto.json`, no campo `ossoCabeca`.

## Clipes

- idle, walk, carry, work, sleep (mesmos nomes do v1), todos em loop.
- A passada natural do walk, em m/s, vai registrada em `rosto.json`, no campo `passadaWalk`.

## Rosto

- Duas malhas dentro de `aldeao_corpo.glb`, chamadas "Olhos" e "Boca".
- São retalhos levemente curvos que acompanham a frente da cabeça, afastados 1 a 2 mm da pele, com peso 100% no osso da cabeça.
- UV de 0 a 1 cobrindo uma célula do atlas. Materiais "rosto_olhos" e "rosto_boca".
- A proporção de cada retalho é igual à proporção da célula do seu atlas.

## Atlas

- Grade fixa, com margem transparente de pelo menos 8 px em volta de cada célula.
- `rosto.json` segue este formato:

```json
{ "olhos": { "colunas": 0, "linhas": 0, "celulaPx": [0, 0], "margemPx": 0, "quadros": { "nome": 0 } },
  "boca":  { "colunas": 0, "linhas": 0, "celulaPx": [0, 0], "margemPx": 0, "quadros": { "nome": 0 } },
  "ossoCabeca": "...",
  "passadaWalk": 0.0 }
```

- O índice 0 é o quadro padrão.

## Cabelos

- Uma malha cada, com no máximo 800 triângulos.
- Um único material chamado "cabelo", cor chapada. Rígidos, sem pesos de osso.
- Modelados no MESMO espaço do corpo em pose de repouso. O jogo prende no encaixe "Cabelo" compensando a pose de repouso global do osso da cabeça.
- Nenhum cabelo cobre o retalho "Olhos".

## Encaixes que o jogo cria

- No osso da cabeça: "Cabelo" e "Chapéu".
- No peito: "Peito" (cristal da classe, uso futuro).

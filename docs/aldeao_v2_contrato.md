# CONTRATO ALDEÃO V2 — interface entre arte e jogo

Mudanças só com aval do Arthur: quem precisar mudar algo, para e pergunta.

## ENTREGAS DA ARTE

- assets/modelos/aldeao_v2/aldeao_corpo.glb
- assets/modelos/aldeao_v2/cabelos/cabelo_1.glb … cabelo_5.glb (depois: cabelo_N_sob_chapeu.glb)
- assets/modelos/aldeao_v2/rosto/olhos.png, boca.png, rosto.json

## ESCALA E ORIENTAÇÃO

- Metros. Pés em y = 0, pivô entre os pés.
- Mesma direção de frente da protagonista e do aldeão v1.
- Altura aproximada de 0,40 m (bate na cintura da protagonista, que tem ~0,75 m). Ajustar vendo os dois lado a lado.

## CORPO

- Uma malha com no máximo 2.500 triângulos.
- Um único material chamado "pele", cor chapada e sem textura. O jogo troca pelo shader toon e pinta a cor definida em data/.
- Careca, sem rosto, sem cristal.

## ESQUELETO

- Rig do Meshy.
- O nome do osso da cabeça vai registrado em rosto.json, no campo "ossoCabeca".

## CLIPES

- idle, walk, carry, work, sleep (mesmos nomes do v1), todos em loop.
- A passada natural do walk, em m/s, vai registrada em rosto.json, no campo "passadaWalk".

## ROSTO

- Duas malhas dentro de aldeao_corpo.glb, chamadas "Olhos" e "Boca".
- São retalhos levemente curvos que acompanham a frente da cabeça, afastados 1 a 2 mm da pele, com peso 100% no osso da cabeça.
- UV de 0 a 1 cobrindo uma célula do atlas. Materiais "rosto_olhos" e "rosto_boca".
- A proporção de cada retalho é igual à proporção da célula do seu atlas.

## ATLAS

- Grade fixa, com margem transparente de pelo menos 8 px em volta de cada célula.
- rosto.json segue este formato:
  ```
  { "olhos": {colunas, linhas, celulaPx:[l,a], margemPx, quadros:{nome:índice}},
    "boca": {...}, "ossoCabeca": "...", "passadaWalk": 0.0 }
  ```
- O índice 0 é o quadro padrão.

## CABELOS

- Uma malha cada, com no máximo 800 triângulos.
- Um único material chamado "cabelo", cor chapada. Rígidos, sem pesos de osso.
- Modelados no MESMO espaço do corpo em pose de repouso. O jogo prende no encaixe "Cabelo" compensando a pose de repouso global do osso da cabeça.
- Nenhum cabelo cobre o retalho "Olhos".

## ENCAIXES QUE O JOGO CRIA

- No osso da cabeça: "Cabelo" e "Chapéu".
- No peito: "Peito" (cristal da classe, uso futuro).

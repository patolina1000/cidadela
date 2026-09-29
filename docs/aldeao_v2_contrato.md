# CONTRATO ALDEÃO V2 — interface entre arte e jogo

Mudanças só com aval do Arthur: quem precisar mudar algo, para e pergunta.

## ENTREGAS DA ARTE

- assets/modelos/aldeao_v2/aldeao_corpo.glb
- assets/modelos/aldeao_v2/cabelos/cabelo_1.glb … cabelo_5.glb (depois: cabelo_N_sob_chapeu.glb)
- assets/modelos/aldeao_v2/rosto/olhos.png, boca.png, rosto.json

## ESCALA E ORIENTAÇÃO

- Metros. Pés em y = 0, pivô entre os pés.
- Frente para +Z do glTF, como a protagonista. O jogo gira 180° ao instanciar.
- Altura aproximada de 0,40 m (bate na cintura da protagonista, que tem ~0,75 m). Ajustar vendo os dois lado a lado.

## CORPO

- Uma malha com no máximo 2.500 triângulos.
- Um único material chamado "pele", cor chapada e sem textura. O jogo troca pelo shader toon.
- Careca, sem rosto, sem cristal.
- A arte NÃO exporta nós de encaixe (Cabelo, Chapéu, Peito); quem cria é o jogo.

## ESQUELETO

- Rig do Meshy.
- rosto.json registra "ossoCabeca" e "ossoPeito".

## CLIPES

- idle, run, os dois em loop, marcados no GLB com o sufixo -loop (o Godot tira o sufixo ao importar).
  (Mudança de 29/09/2026: carry, work e sleep entram depois.)
- A passada natural do run, em m/s, vai registrada em rosto.json, no campo "passadaRun".

## ROSTO

- Duas malhas dentro de aldeao_corpo.glb, chamadas "Olhos" e "Boca".
- São retalhos levemente curvos que acompanham a frente da cabeça, afastados 1 a 2 mm da pele, com peso 100% no osso da cabeça.
- UV de 0 a 1 cobrindo uma célula inteira do atlas. Materiais "rosto_olhos" e "rosto_boca".
- A proporção de cada retalho é igual à proporção da célula do seu atlas.

## ATLAS

- Grade fixa.
- celulaPx é o passo da grade e já INCLUI a margem.
- margemPx (mínimo 8) é a borda transparente dentro de cada célula; o desenho fica só na área útil.
- O retalho mostra a célula inteira.
- rosto.json segue este formato:
  ```
  { "olhos": {colunas, linhas, celulaPx:[l,a], margemPx, quadros:{nome:índice}},
    "boca": {mesmo formato},
    "expressoes": {nome: {olhos, boca}},
    "ossoCabeca": "...", "ossoPeito": "...", "passadaRun": 0.0 }
  ```
- O índice 0 é o quadro padrão: olhos "distraido" e boca "entreaberta".

## CABELOS

- Uma malha cada, com no máximo 800 triângulos.
- Um único material chamado "cabelo", cor chapada. Rígidos, sem pesos de osso.
- Modelados no MESMO espaço do corpo em pose de repouso. O jogo prende no encaixe "Cabelo" compensando GetBoneGlobalRest do osso da cabeça.
- No máximo 2 cabelos (hoje o 2 e o 3) podem cobrir até a metade de cima de um olho; o retalho não muda; o cabelo mantém folga mínima de 2 mm e nunca atravessa o retalho.
  (Mudança de 29/09/2026; antes: "Nenhum cabelo cobre o retalho Olhos".)

## CORES (provisórias, ficam em data/villager_looks.json)

- pele #AEBFD3 (azul-pálido fosco)
- cabelo #6F7F96 (azul-acinzentado)

## ENCAIXES QUE O JOGO CRIA

- No ossoCabeca: "Cabelo" e "Chapéu".
- No ossoPeito: "Peito" (cristal da classe, uso futuro).

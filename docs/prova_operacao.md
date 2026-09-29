# PROVA DE OPERAÇÃO — aldeões girando uma roda

Registro de 29/09/2026. A prova vive em `scenes/tests/ProvaOperacao.tscn` (código em
`src/View/ProvaOperacaoRoot.cs` e `src/View/ExternalClips.cs`). Os arquivos da arte estão em
`assets/modelos/prova_operacao/variante_r06/` (roda, clipe `girar_roda` e `clipes.json`), e as medidas do Blender
em `assets/previews/prova_operacao/variante_r06/girar_roda.json`. Nada disto está na simulação ainda.

**Controles da cena:** 1 e 2 tiram ou devolvem cada aldeão · − e = mudam o mínimo de operadores · Espaço pausa a
roda · roda do mouse aproxima · Q e E giram a câmera · Esc volta ao menu.

## 1. O QUE A PROVA MOSTROU

1. **Um clipe feito por IK no Blender funciona no jogo sem mexer no corpo.** O clipe vem num GLB separado, só com
   esqueleto e animação, e entra no AnimationPlayer do aldeão como uma biblioteca nova ("operacao/girar_roda").
   Os 24 ossos do clipe têm os mesmos nomes, a mesma hierarquia e o mesmo repouso do corpo (0,04°).
2. **Posicionar pelo estado da máquina dá mãos presas à manopla.** O aldeão não toca o clipe solto: a cada quadro
   o jogo busca o quadro que corresponde à fase da roda. Com a roda pausada nos 48 quadros do clipe, a palma
   fica no máximo a **3,6 mm** do alvo (o Blender mede 2,5 mm no mesmo pior quadro). Entre os quadros chega a
   5,8 mm; girando, o pior de cada volta fica em 3,7 mm. Num aldeão de 0,40 m, isso não se vê.
3. **A roda manda, o aldeão segue.** Se a roda desacelera, para ou volta a girar, as mãos acompanham, porque o
   quadro vem da fase e não do tempo. Com 1 ou 2 operadores a velocidade visual é a mesma.
4. **Tirar e devolver um operador é só trocar de modo.** Fora do posto ele volta ao idle; ao voltar, entra direto
   no quadro da fase com 0,2 s de mistura (152 mm de distância no primeiro quadro, 4 mm aos 0,2 s).
5. **O golpe é um instante do clipe.** A arte marcou a fração 0,5 do `girar_roda` (a alça passa embaixo, fim da
   empurrada). Contando quando o quadro passa por ali, os golpes batem exatamente com as voltas.
6. **Um clipe serve os dois lados, provisoriamente.** O aldeão B, do outro lado, segura a alça B (180° depois, na
   face de trás) e toca o mesmo clipe ao contrário, com fase 0,5 − t. Funciona porque a roda é simétrica e os
   dois postos têm a mesma geometria. **A regra final é um clipe por posto, gerado por IK para aquele posto**;
   tocar ao contrário é só um atalho desta prova.
7. **Três problemas de arquivo apareceram e foram contornados no código:**
   - o clipe foi exportado antes da normalização do aldeão (Armature em 0,004): as translações vêm 250 vezes
     maiores e a classe converte pela razão entre as escalas dos esqueletos;
   - o Blender põe o quadro 1 em 1/24 s e o importador do Godot reamostra a partir de 0, então o clipe importado
     fica um quadro mais longo, com o começo parado (7,5 mm de erro). A classe corta o começo com a duração do
     `clipes.json`;
   - o importador reamostra a 30 fps um clipe feito a 24 fps. Isso explica o 1,1 mm que sobra contra o Blender.

## 2. O QUE O CÓDIGO DE ANIMAÇÃO VAI PRECISAR (aldeão e protagonista)

Quando as máquinas vierem, a animação dos dois personagens precisa de cinco coisas. As três primeiras já existem
na prova; as duas últimas não.

1. **Posicionar por fase.** Um clipe de operação é posicionado pela fase da máquina, nunca tocado solto. Hoje:
   `VillagerVisual.PosedClip` e `PosedPhase` (o player é avançado à mão: volta dt antes do tempo da fase e avança
   dt). A fase vem da simulação, interpolada entre ticks como a posição. A protagonista precisa do mesmo modo em
   `CastellanVisual`.
2. **Eventos de golpe.** Cada clipe de trabalho declara em que fração acontece o golpe (hoje `conta_na_fracao`
   no `clipes.json`; pode haver mais de um por ciclo). A view usa o instante para som, partícula e o "tranco" da
   peça; a simulação usa a mesma fração para contar trabalho (seção 3). Os dois precisam ler a fração do mesmo
   lugar.
3. **Clipes de arquivos separados.** Cada máquina traz o seu GLB de clipes (um por posto), carregado por
   `ExternalClips` no corpo que ocupa o posto, sem regravar o corpo. Regras para a arte:
   - o esqueleto do clipe no mesmo espaço do corpo (Armature em metros); a conversão de escala fica como
     segurança, não como regra;
   - o ciclo começando em 0 s, ou a duração real registrada no JSON do clipe;
   - `animation/fps` igual ao do clipe no `.import` (24), para o Godot não reamostrar.
4. **Reações curtas.** Tomar dano, levar susto, comemorar: clipes de 0,3 a 1 s que tocam por cima do que o
   personagem estiver fazendo e voltam sozinhos. No operador, a reação não pode tirar as mãos da manopla por
   mais que um instante. Pede um mixer por camadas (`AnimationTree`) ou um clipe aditivo, e não troca de clipe.
5. **Camadas por parte do corpo, para armas.** Pernas correndo, braços segurando e usando a arma. Precisa de
   máscaras por grupo de ossos (quadril para baixo e tronco para cima), com os clipes de ataque só na camada de
   cima. É o mesmo mecanismo das reações.

## 3. O QUE A SIMULAÇÃO VAI PRECISAR (só escrito; nada implementado)

Tudo em ticks de 20/s, sem Godot, com os números em `data/`.

- **Máquina com fase.** Estado da máquina: fase acumulada (voltas), velocidade atual, velocidade de trabalho e
  aceleração (por tick). Com operadores suficientes, a velocidade vai à de trabalho; abaixo do mínimo, desacelera
  até parar. A view só lê a fase e a interpola.
- **Postos.** Cada máquina tem uma lista de postos; cada posto tem posição, orientação, o clipe daquele posto e
  quem o ocupa.
  - **Postos independentes:** cada operador produz sozinho (dois pilões lado a lado). A máquina anda enquanto
    houver alguém; cada posto conta os seus golpes.
  - **Postos acoplados:** todos movem a mesma peça (a roda desta prova). Uma fase só; `minimoOperadores` decide
    se gira; a velocidade não depende de quantos há acima do mínimo (decisão desta prova, a confirmar no
    balanceamento).
- **Estados do aldeão:**
  - **operando:** preso ao posto; a expressão é "esforço";
  - **ferido:** sai do posto (hoje simulado pelas teclas 1 e 2) e fica fora por um tempo ou até ser curado; a
    expressão é "chorando" (tabela do GDD);
  - **esperando:** está no posto, mas a máquina não anda (falta operador, entrada ou saída cheia). Fica sem
    golpes, a expressão é "preocupado" (proposta; o GDD usa "preocupado" para a cabana cheia), e o clipe fica
    parado no quadro da fase.
- **Trabalho por golpe.** A máquina produz por golpe, não por tempo: cada vez que a fase passa pela fração de um
  golpe, soma trabalho, e a receita pede N golpes. A velocidade de trabalho e o número de golpes por receita
  ficam no JSON da máquina. Com isso, tirar um operador de uma máquina acoplada acima do mínimo não muda a
  produção, e abaixo do mínimo a produção para junto com a roda.

## 4. REGRA DE ERGONOMIA

- As máquinas respeitam `assets/modelos/aldeao_v2/ergonomia.json`, medido no corpo do aldeão v2:
  - manivela com eixo horizontal **na altura do peito (0,194 m)**;
  - raio de **até 0,06 m** (o recomendado: a mão encosta na manopla em todas as fases; 0,065 m ainda fecha a
    5 mm, e com 0,10 m as mãos ficam de 33 a 35 mm fora);
  - manopla a cerca de 0,10 m dos ombros, livre da barriga em todo o círculo, com as duas mãos a ±18 mm do centro.
- Uma máquina que o aldeão opera é desenhada a partir dessas medidas, e não o contrário. Se uma máquina precisar
  de uma roda maior, ela ganha uma manivela menor ligada à roda, ou mais operadores.
- **A protagonista, com o dobro da altura do aldeão, terá o seu próprio `ergonomia.json`**, medido no corpo da v2
  quando ele existir. Não vale escalar os números do aldeão: as proporções dos dois corpos são diferentes.
  Máquinas que ela opera usam o arquivo dela.

## 5. PENDÊNCIAS PARA A ARTE

- Reexportar os clipes de `prova_operacao/` com a Armature normalizada (escala 1), como o corpo.
- Pôr `animation/fps = 24` no `.import` dos GLBs de clipe.
- Fazer o clipe do posto B por IK, para trocar a regra provisória 0,5 − t.
- Commitar os `.import` e as texturas extraídas que o Godot gerou em `assets/`. Esses arquivos ficaram sem versionar
  na `master`.

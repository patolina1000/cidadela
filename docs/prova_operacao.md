# PROVA DE OPERAÇÃO — aldeões girando uma roda

Registro de 29/09/2026, atualizado com os clipes da arte feitos pelo contrato (`docs/animacao_contrato.md`). A prova
vive em `scenes/tests/ProvaOperacao.tscn` (código em `src/View/ProvaOperacaoRoot.cs` e `src/View/ExternalClips.cs`).
Os arquivos da arte estão em `assets/modelos/prova_operacao/variante_r06/`: a roda, um clipe por posto
(`clipes/girar_roda.glb` para o posto A, `clipes/girar_roda_b.glb` para o B) e o `clipes.json` com um bloco por
posto. As medidas do Blender estão em `assets/previews/prova_operacao/variante_r06/`. Nada disto está na simulação
ainda.

**Controles da cena:** 1 e 2 tiram ou devolvem cada aldeão · − e = mudam o mínimo de operadores · Espaço pausa a
roda · roda do mouse aproxima · Q e E giram a câmera · Esc volta ao menu.

## 1. O QUE A PROVA MOSTROU

1. **Um clipe feito por IK no Blender funciona no jogo sem mexer no corpo.** Cada clipe vem num GLB separado, só
   com esqueleto e animação, e entra no AnimationPlayer do aldeão como uma biblioteca nova
   ("operacao_A/girar_roda"). O `ExternalClips` é estrito: nada é convertido nem cortado, e um clipe fora do
   contrato é recusado com aviso. O clipe antigo da prova, feito antes da normalização, foi recusado por dois
   motivos: a Armature em escala 0,004 e a duração de 2,0417 s contra os 2,0 s do `clipes.json`.
2. **Posicionar pelo estado da máquina dá mãos presas à manopla.** O aldeão não toca o clipe solto: a cada quadro
   o jogo busca o quadro que corresponde à fase da roda (quadro = fase × 48, sem inverter nem defasar). Distância
   palma-manopla, pior mão:

   | Clipe | 48 quadros, roda pausada | entre quadros | girando |
   |---|---|---|---|
   | lido com as 49 chaves, postos A / B | 2,44 / 2,44 mm | 2,43 / 2,43 mm | 2,45 / 2,45 mm |
   | importado pelo editor hoje, postos A / B | 3,89 / 3,43 mm | 3,88 / 3,38 mm | 3,91 / 3,44 mm |

   Com as 49 chaves, o jogo reproduz o Blender (2,4 a 2,5 mm, no mesmo pior quadro: 28 no A e 44 no B). A
   diferença do importado vem do otimizador de animação do importador do Godot, ligado por padrão, que apaga
   chaves com perda (as trilhas ficam com 36 a 48 chaves). Desligá-lo no `.import` dos clipes resolve (seção 5).
   Num aldeão de 0,40 m, nenhum dos dois se vê.
3. **A roda manda, o aldeão segue.** Se a roda desacelera, para ou volta a girar, as mãos acompanham, porque o
   quadro vem da fase e não do tempo. Com 1 ou 2 operadores a velocidade visual é a mesma.
4. **Tirar e devolver um operador é só trocar de modo.** Fora do posto ele volta ao idle; ao voltar, entra direto
   no quadro da fase com 0,2 s de mistura (152 mm de distância no primeiro quadro, 4 mm aos 0,2 s).
5. **O golpe é um instante do clipe.** A arte marcou a fração 0,5 (a alça A passa embaixo, fim da empurrada do
   posto A). Contando quando a fase da roda passa por ali, os golpes batem exatamente com as voltas.
6. **Um clipe por posto: provado.** Cada posto tem o seu clipe, gerado por IK para a geometria dele. O posto B
   usa `girar_roda_b.glb` com a mesma fórmula de fase do A e fica a 2,4 mm, como o A. Tocar o clipe de outro
   posto ao contrário ou espelhado não vale em produção (contrato de animação, "OPERAÇÃO").

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
   `ExternalClips` no corpo que ocupa o posto, sem regravar o corpo. O formato está no contrato de animação:
   esqueleto igual ao do corpo, em metros; primeira chave em t = 0; 24 fps também no `.import`.
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

Feito: clipes reexportados em metros e com a primeira chave em t = 0, `animation/fps = 24` no `.import`, clipe
do posto B por IK e os `.import` gerados commitados na `arte`.

Falta:
- Desligar o otimizador de animação no `.import` dos clipes (`_subresources`), para o jogo ter as 49 chaves e os
  2,4 mm do Blender. Vale como regra nova do contrato de animação, se o Arthur aprovar.
- Commitar o `.import` do corpo com `animation/fps = 24`. Ele está modificado na worktree da arte, mas não
  commitado; na `master` continua em 30.
- Clipes do corpo (`run-loop` e `idle-loop`): a primeira chave está em t = 1/24 s. O Godot recria a chave em 0
  igual à de 1/24, então cada volta do run ganha um quadro parado (0,75 s em vez de 0,708 s). No ciclo real, a
  24 fps, a passada medida no Godot é 0,383 m/s, a mesma do `rosto.json`.

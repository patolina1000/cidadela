# Auditoria do esqueleto do aldeão v2 (`aldeao_corpo.glb`)

Prova técnica para máquinas operadas (29/09/2026). Só leitura: o arquivo aprovado não foi alterado.
Números em `auditoria.json` (gerado por `tools/arte/prova_operacao/auditoria.py`); closes das mãos em
`mao_esquerda.png` e `mao_direita.png`.

## 1. Escala e unidades

- O nó `Armature` do glTF tem **escala 0,004** (uniforme) e translação (0; 0; −0,0066) m: o esqueleto está 6,6 mm
  para trás (−Z do glTF). Nenhuma junta tem escala própria (todas 1).
- As juntas ficam numa unidade em que **1 = 4 mm** (250 unidades por metro): o Hips está a 31,0 unidades do chão
  (0,124 m), o antebraço esquerdo mede 12,9 unidades (51,7 mm). É a unidade do rig da Meshy (feito a 1,0 m de
  altura em cm) vezes a redução para 0,40 m, que ficou no objeto Armature e não nos ossos.
- As duas malhas skinned (corpo, Olhos, Boca) são filhas do Armature com transformação identidade: os vértices
  também estão nessa unidade de 4 mm, e a escala 0,004 do pai os leva ao tamanho certo.
- Clipes: os 24 ossos têm canais de rotação, posição e escala. Só a **posição do Hips** varia (idle até 1,7
  unidades ≈ 7 mm; run até 2,8 unidades ≈ 11 mm); a escala é sempre 1. Toda posição de osso num clipe está em
  unidades de 4 mm.
- **Comprimento dos ossos no Blender:** o glTF não guarda a ponta (tail) dos ossos. O importador do Blender
  estima o comprimento pela distância até o filho, mas sem levar a escala do pai em conta, e os ossos entram
  **250× compridos demais** (Hips com 7,0 m, antebraço com 12,9 m no mundo). A direção está certa (ver 2);
  só o comprimento é falso. No Godot isso não existe (lá osso não tem ponta).

## 2. Orientação, rolagem e pose de repouso

- Convenção tipo Mixamo: o **+Y local de cada junta aponta para o filho** (conferido osso a osso: o eixo Y
  coincide com a direção até o filho). Nomes sem prefixo (`Hips`, `Spine02`, `Spine01`, `Spine`, `neck`, `Head`,
  `LeftShoulder`, `LeftArm`, `LeftForeArm`, `LeftHand`, pernas até `LeftToeBase`; mais `head_end` e `headfront`).
- Rolagens (graus, como o Blender as mostra): coluna e pescoço quase 0 (−1 a −4); ombros ±180; braço, antebraço
  e mão ±90 (esq. −91,8 / −90,2 / −83,1; dir. +91,2 / +91,0 / +90,9); Hips −147 (o eixo Y dele aponta para o lado
  e para baixo, porque os filhos saem em direções diferentes). **Pernas assimétricas:** coxa −27,4 / +25,1,
  canela +7,3 / +15,4, pé −39,5 / +29,7.
- **O esqueleto não é simétrico** (a malha é): o rig foi feito na malha crua da Meshy e os pesos foram passados
  para a malha limpa. Distância até o filho, esq. / dir.: clavícula 29,7 / 31,8 mm, braço 54,9 / 55,4 mm,
  **antebraço 51,7 / 48,6 mm (6%)**, coxa 49,2 / 47,7 mm, pé 29,1 / 30,7 mm.
- Pose de repouso: **pose A**, braços a **44° abaixo da horizontal** e 8° a 9° para trás. Ombro ao punho: **103 mm**
  (esq.) e **101 mm** (dir.), num personagem de 400 mm: 25% da altura (um humano tem ~33%). Alturas: Hips 124 mm,
  Spine02 (`ossoPeito`) 152 mm, Spine01 180 mm, Spine 209 mm, ombros 213 mm, Head 246 mm.

## 3. O que isso complica para clipes que não vêm da Meshy

**IK no Blender**
- Os ossos 250× compridos quebram o IK: a ponta da cadeia fica a metros do punho. Solução proposta (testada no passo 3):
  em modo de edição, encurtar cada osso até o filho **sem mudar direção nem rolagem** (a matriz de repouso não
  muda, então os clipes continuam valendo). A mão, que não tem
  filho, ganha o comprimento até o centro da palma.
- Rolagens de ±90° nos braços, diferentes entre os lados: o ângulo do polo do IK (cotovelo) tem que ser achado
  por lado; não existe um valor único.
- Tudo o que se escreve em posição de osso (quadril, deslocamentos) está em unidades de 4 mm: 1 cm = 2,5 unidades.
  Alvos e polos como objetos no mundo funcionam em metros normalmente.

**Retarget (Uthana ou outro serviço)** — não testado (sem créditos); riscos pelo que o arquivo tem:
- A escala no nó Armature com juntas em unidades de 4 mm: um importador que ignore ou "assente" a escala do nó
  pode ler o personagem com 100 m, ou ler a posição do quadril 250× maior (o quadril voa). É o risco mais simples de
  eliminar: normalizar (passo 2).
- Braços curtos (25% da altura) e cabeça grande: um clipe humano retargetado **não leva a mão aonde a mão humana
  vai** (mãos juntas na frente, mão na cabeça, segurar alça). Todo contato precisa ser corrigido com IK depois do
  retarget. Isso não depende de escala nem de rolagem: é a proporção do boneco.
- Assimetria de até 3 mm no antebraço: contatos espelhados (as duas mãos na mesma alça) ficam desalinhados.
- Pose A: os serviços costumam aceitar, mas a pose de repouso precisa estar no arquivo (está: os ossos em repouso
  são a pose A).

**IK no Godot**
- O jogo já prende peças compensando `GetBoneGlobalRest` e a transformação do esqueleto no modelo (inclui o 0,004),
  então encaixes e IK por nós-alvo no mundo funcionam como estão.
- O que complica: qualquer número em espaço de osso ou de esqueleto (deslocar o quadril, distância do polo,
  `set_bone_pose_position`) está em unidades de 4 mm; e o +Y para o filho bate com o que os modificadores de IK
  do Godot esperam, mas o polo do cotovelo precisa de direção por lado, por causa das rolagens de ±90°.

## 4. Mãos

- **Mãos em luva, sem dedos e sem ossos de dedo:** um bloco arredondado com um toco de polegar, na forma de uma
  mão meio fechada (não dá para abrir nem fechar; a forma é da malha). Caixa de 39 × 63 × 37 mm, ~100 vértices por mão.
- Para segurar uma alça isso ajuda: o bloco já lê como punho. A alça tem que caber "dentro" do punho visualmente
  (≥ 12 mm de diâmetro) e o contato é pelo centro da palma.
- Closes a 512 px: `mao_esquerda.png`, `mao_direita.png`.

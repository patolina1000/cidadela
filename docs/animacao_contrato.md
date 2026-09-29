# CONTRATO DE ANIMAÇÃO — comum ao aldeão e à protagonista

Mudanças só com aval do Arthur: quem precisar mudar algo, para e pergunta.

Vale junto com o contrato de cada personagem (hoje `docs/aldeao_v2_contrato.md`). Nasce da prova de operação
(`docs/prova_operacao.md`, 29/09/2026). O objetivo é que nenhum dos dois corpos precise de um v3 quando as
máquinas vierem.

## ESQUELETO

- Rig da Meshy, 24 ossos.
- Nomes, hierarquia e pose de repouso ficam congelados por corpo depois da aprovação. Nunca rigar de novo.
- Armature com escala 1, em metros.
- O sha256 do corpo aprovado fica registrado ao lado dele, na pasta do corpo.
- Hoje: `assets/modelos/aldeao_v2/aldeao_corpo.glb`, sha256
  `3138cbf652d0d840c2ab911b676bb20d3116f14172e15163c8232a3fa74b49a2` (reexportado com as chaves a partir de t = 0;
  antes, `11c7d12b…`).

## CORPO

- O GLB do corpo carrega só os clipes base do contrato do personagem. Hoje são `idle-loop` e `run-loop`.

## CLIPES NOVOS

- Ficam em GLBs separados, só com esqueleto e animação, em `assets/modelos/<corpo>/clipes/<nome>.glb`.
- Usam o mesmo esqueleto do corpo: nomes e hierarquia iguais, repouso igual a 0,01 mm.
- O jogo os acrescenta ao corpo como uma AnimationLibrary nova, sem mexer no GLB do corpo (`ExternalClips`).

## FORMATO DO CLIPE

- Sem avanço de raiz.
- Primeira chave em t = 0.
- 24 fps.
- Laço fechado, com salto menor que 1 cm.
- Sufixo `-loop` para laço. O Godot tira o sufixo ao importar.
- O `.import` do clipe fixa `animation/fps = 24`. A ARTE gera e commita esse `.import`, rodando o Godot sem janela
  na worktree da arte.
- A regra de 24 fps vale também para o `.import` do corpo (os clipes base que ele carrega).
- O otimizador de animação do importador fica desligado no `.import` de todo clipe e do corpo
  (`_subresources` → `nodes` → `PATH:AnimationPlayer` → `optimizer/enabled = false`), porque ele apaga chaves
  com perda.
- Todo clipe, e o corpo, define a pose inteira: trilhas dos 24 ossos no arquivo e
  `animation/remove_immutable_tracks = false` no `.import`. Camadas por parte do corpo, quando vierem, são feitas
  com filtro por osso, nunca com trilhas faltando.
- O `.import` de clipe e de corpo é escrito e conferido por `tools/arte/godot_import.py`.

## clipes.json

- Um em cada pasta de clipes, com um bloco por clipe; em operação, um clipe (e um bloco) por posto. Formato
  entregue pela arte na prova (`assets/modelos/prova_operacao/variante_r06/clipes.json`):
  ```
  { "girar_roda-loop": {
      "arquivo": "clipes/girar_roda.glb",
      "duracao_s": 2.0, "quadros": 48, "fps": 24,
      "passada_m_s": 0.0,                 // só em locomoção
      "conta_na_fracao": 0.5,             // só se tiver golpe
      "conta_significa": "o que acontece nesse instante",
      "posto": {                          // só em operação
        "nome": "A", "alca": "A",
        "posicao_m": [0.0, -0.19, 0.1751],  // pés do aldeão no espaço da peça
        "giro_em_y_graus": 180.0,           // 0 = aldeão olhando +Z da peça
        "fase": "quadro = fase_da_peca × quadros; primeira chave em t = 0; sem inverter nem defasar",
        "referencia": "espaço da peça (glTF): pivô no eixo, eixo em +Z"
      },
      "peca": {                           // só em operação
        "arquivo": "roda.glb", "raio_alca_m": 0.06,
        "giro": "−360° × fase em volta do +Z local (fase 0 = alça A no topo)"
      },
      "falta_max_mm": 2.5                 // medido no Blender
  } }
  ```
- Passada:
  - no aldeão v2 ela continua como `passadaRun` no `rosto.json` (contrato do aldeão);
  - corpos novos (a protagonista v2 e os seguintes) usam `passada_m_s` no `clipes.json`.

## OPERAÇÃO

- Um clipe POR POSTO, gerado por IK para a geometria daquele posto. Tocar ao contrário ou espelhar não vale em
  produção. A regra 0,5 − t do aldeão B foi só um atalho da prova.
- O clipe é posicionado pela fase da peça (seek). Nunca é tocado solto.
- O golpe é a fração `conta_na_fracao` do clipe.

## ERGONOMIA

- Cada corpo publica `assets/modelos/<corpo>/ergonomia.json`, medido por
  `tools/arte/prova_operacao/medir_ergonomia.py`.
- As máquinas são desenhadas a partir dele, e não o contrário.
- A protagonista terá o dela, medido no corpo dela. Os números do aldeão não se escalam.

## ENCAIXES

- O jogo cria os encaixes; a arte não os exporta.
- Nomes reservados:
  - "Cabelo" e "Chapéu", no osso da cabeça;
  - "Peito";
  - "MaoDireita" (RightHand) e "MaoEsquerda" (LeftHand);
  - "Costas" (Spine01);
  - "Chifres", só na protagonista.
- Osso do "Peito": o `ossoPeito` do aldeão é `Spine02`, o osso de BAIXO da coluna no rig da Meshy. A protagonista
  v1 usava `Spine`, o de cima. Qual vale para o Peito fica em aberto até o cristal de classe.

## O JOGO É ESTRITO

- Em vigor desde 29/09/2026: o `ExternalClips` não converte escala nem corta o começo. Ele recusa, com um aviso
  que lista os motivos, clipe com:
  - Armature em escala diferente da do corpo;
  - ossos diferentes dos do corpo;
  - repouso diferente em mais de 0,01 mm;
  - primeira chave fora de t = 0;
  - falta de trilha de rotação para algum osso do esqueleto do corpo (depois de importado).
- O importador do Godot sempre recria uma chave em t = 0, segurando o primeiro quadro. Por isso um clipe com o
  começo atrasado é pego pela duração: se ela passar de meio quadro de diferença para a `duracao_s` do
  `clipes.json`, o clipe é recusado.

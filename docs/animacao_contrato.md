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
  `11c7d12bc4c522808546f61f3136031e2fce0cc6ccf9e789abd02779d110febf`.

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

## clipes.json

- Um em cada pasta de clipes, com uma entrada por clipe:
  ```
  { "<nome>": {
      "duracao_s": 0.0, "quadros": 0, "fps": 24,
      "passada_m_s": 0.0,          // só em locomoção
      "conta_na_fracao": 0.0,      // só se tiver golpe
      "posto": {                   // só em operação
        "posicao_m": [x, y, z], "giro_em_y_graus": 0.0,   // posto em relação à peça
        "fase": "fórmula que liga a fase da peça ao quadro do clipe"
      }
  } }
  ```

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

- Hoje o `ExternalClips` converte a escala do clipe e corta o começo, porque os clipes da prova vieram fora deste
  formato.
- Quando os clipes da arte chegarem no formato novo, ele deixa de converter e de cortar. Passa a recusar, com
  aviso, clipe com escala ou repouso diferente do corpo.

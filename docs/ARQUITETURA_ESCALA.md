# Arquitetura para escala (milhares de inimigos, máquinas e itens)

Proposta técnica de 26/09/2026, escrita depois da análise de desempenho e do teste de estresse
(`scenes/Stress.tscn`; números no `DIARIO.md`). Complementa as seções 13 e 14 do GDD. Meta: 60 FPS estáveis
em tela cheia na Retina (3024×1890) no MacBook Pro M4 base, com milhares de entidades na tela.

## 1. O que as medições dizem

| Fato medido | Consequência |
|---|---|
| CPU do jogo hoje: 0,1–0,2 ms por quadro; simulação de estresse com 15.500 entidades: 0,4–0,9 ms por tick | A simulação em C# puro tem folga de sobra; não é onde o esforço deve ir primeiro. |
| GPU: grama 11 ms (antes do LOD), sombra 3,7, chão 2,1, pós 1,6; piso 3,7 ms | Tudo que importa é custo de renderização: fragmentos, sombra, triângulos minúsculos. |
| 15.500 nós móveis: 2,6 ms de CPU e o Forward+ já instancia malhas iguais (156 draw calls) | Um nó por entidade aguenta até dezenas de milhares de entidades **móveis**; não é o gargalo até lá. |
| MultiMesh dinâmico refeito por quadro: 3,8–5,6 ms de CPU e culling mais grosso | MultiMesh por quadro só compensa acima de ~40–60 mil entidades móveis, e escrito sem cópia. |
| Grama estática: 468 mil tufos em ~200 draw calls com MultiMesh por pedaço | Para o que é estático e numeroso, MultiMesh por pedaço é a resposta certa. |

## 2. Simulação: orientada a dados, sem nó do Godot

- **Uma tabela por tipo de entidade, um array por componente** (como o `StressWorld`): `X[]`, `Z[]`,
  `PrevX[]`, `PrevZ[]`, `Yaw[]`, `Kind[]`, `Hp[]`, `State[]`... O tick percorre arrays contíguos, sem
  ponteiros nem alocações; é o que deixa 5.000 inimigos custarem menos de 1 ms.
- **Identidade por índice estável** (slot) com lista de livres; a view guarda o mesmo índice. Remover =
  marcar o slot e reaproveitá-lo; nada de `List.Remove` no meio do tick.
- **Grade espacial de células** (já existe `_buildingByCell`) para vizinhança: inimigo procura alvo e
  colisão só nas células ao redor. Para hordas, um *flow field* por alvo (um mapa de direções calculado
  quando o alvo muda) em vez de A* por inimigo: custo independente do número de inimigos.
- **Esteiras como corredores** (Factorio): cada trecho reto guarda os itens numa fila ordenada por
  distância; mover = somar a velocidade a um único deslocamento por trecho e resolver só o item da frente.
  10.000 itens viram poucas centenas de trechos.
- Máquinas: só as que têm receita ativa entram numa lista de "acordadas"; máquina parada não gasta tick.
- Determinismo continua (mesma semente, mesmo resultado), o que permite testes de regressão em xUnit para
  cada sistema com milhares de entidades, sem abrir o jogo.

## 3. View: o que desenha cada coisa

| O que | Como desenhar | Por quê |
|---|---|---|
| Grama, pisos, muros, decoração | **MultiMesh por tipo e por pedaço** (8×8 células), reescrito só quando o pedaço muda; LOD por distância (`VisibilityRange`) | Estático e numeroso; já em uso na grama |
| Itens em esteiras | MultiMesh por tipo de item e por pedaço; o buffer do pedaço só é reescrito nos quadros em que a esteira anda (todo tick) — ou, melhor, **posição calculada no shader**: o instance data guarda trecho + deslocamento inicial e o vertex shader anda com o TIME | Tira os 10.000 itens da CPU por quadro |
| Inimigos, aldeões (até ~30 mil móveis) | **Um nó por entidade** com malha e material compartilhados (o Forward+ instancia sozinho); transform escrito só para quem mudou; `VisibilityRange` para trocar por impostor longe | Medido: mais barato que MultiMesh dinâmico nessa faixa, e mantém culling exato |
| Multidões animadas (inimigos com esqueleto) | **VAT (vertex animation texture)**: as poses das animações são gravadas numa textura; a malha é estática e o vertex shader lê a pose pelo tempo e pela animação em `INSTANCE_CUSTOM`. Serve tanto para nó por entidade quanto para MultiMesh | Milhares de esqueletos animados na CPU (`AnimationPlayer` + `Skeleton3D`) não escalam; VAT custa zero de CPU |
| Acima de ~40 mil móveis | MultiMesh por pedaço com o buffer escrito direto no `RenderingServer` (`multimesh_set_buffer`) a partir de um `float[]` persistente, só nos pedaços que mudaram | Aí a soma dos nós passa a pesar |

Regras que valem para todos:
- **Nenhuma sombra projetada por coisas pequenas** (itens, grama, projéteis). Sombra só na cascata perto
  (`directional_shadow_max_distance = 40`, já feito), sem penumbra PCSS (já feito).
- **LOD em tudo que tem muitos triângulos**: a grama já usa duas malhas (completa até 11 unidades, folha
  achatada além); inimigos e máquinas ganham 2–3 níveis no import (`Mesh LOD` automático do Godot).
- **Triângulo pequeno é caro** na GPU do Mac (blocos de 2×2 pixels): malhas longe devem ter poucos
  triângulos grandes, não muitos pequenos. Impostor (um quad com a silhueta) para o que está a mais de
  ~25 unidades.
- **Nada de shader caro no chão**: o chão é a maior área da tela; hoje custa 2,1 ms e pode cair
  pré-calculando a mistura de terrenos numa textura por pedaço quando o mapa muda.

## 4. Passos concretos, em ordem

1. Migrar `BeltItems` para corredores + MultiMesh por pedaço (ou posição no shader). Medir com 10.000 itens.
2. Inimigos: tabela orientada a dados no `SimWorld` (a partir do `StressWorld`), flow field por alvo, nó
   por entidade com malha compartilhada, impostor além de 25 unidades. Medir com 5.000.
3. VAT para a animação dos inimigos (script de bake no Blender + shader), quando existir o modelo.
4. Chão: mistura pré-calculada por pedaço.
5. Repetir o teste de estresse a cada passo e anotar no diário.

## 5. O que não fazer

- Não trocar o renderizador (Mobile) nem baixar a resolução 3D sem medir e sem aprovação: os ganhos
  medidos vieram de sombra e triângulos, não de pixels.
- Não usar `CharacterBody3D`/física do Godot para inimigos: a simulação já resolve movimento e colisão em
  arrays; o Godot só desenha.
- Não criar/destruir nós durante a horda: pool de nós por tipo, ligando e desligando `Visible`.

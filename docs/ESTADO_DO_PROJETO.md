# Estado do projeto — 29/09/2026

Diagnóstico escrito pela IA (Claude Code + Fable 5.1) a pedido do humano, depois de remover o aldeão v1.
Base: o GDD vivo (exportado hoje), o `docs/DIARIO.md` (69 entradas, 25 a 27/09), o código e o histórico do git
(87 commits). Onde há opinião, está marcada como tal.

## 1. Resumo

Em três dias de trabalho o projeto tem uma fábrica jogável pequena (coletar, construir, esteiras, três máquinas,
baús), uma protagonista com modelo e animações aprovadas, um mundo com clima e chão próprios, menu, enciclopédia,
painel de desempenho e uma arquitetura medida para escala. **Não tem ainda o que faz o jogo ser o jogo:** noite,
horda, combate, Coração da Cidadela e aldeões. Pelo MVP da seção 10 do GDD, estimo **cerca de 40% pronto**, com a
metade mais arriscada (o loop dia/noite) inteira pela frente.

## 2. Pronto × MVP (GDD, seção 10)

| Item do MVP | Estado | O que existe | O que falta |
| --- | --- | --- | --- |
| Mapa 3D, câmera top-down, modelos por IA | **Pronto** | Grade 32×32 com terrenos em JSON, chão com shader, grama do asset da StayAtHomeDev, crepúsculo eterno, câmera tipo Factorio (espiar, arrastar, girar em 90°, zoom), câmera cinematográfica, protagonista da Meshy com idle/run/attack/work | Máquinas, recursos e cabanas ainda são formas geométricas (o pipeline da Meshy está pronto para elas; 12 assets listados em `tools/assets.json`) |
| 3 recursos, esteiras e 5 máquinas | **Parcial** | Madeira, pedra e ferro; esteiras com curvas, fila e entrega em baús e máquinas; serraria, fundição e forja com receita em JSON; 3 cabanas de trabalho | 2 máquinas; mais de uma receita por máquina; cabanas sem trabalhador |
| Cadeia ferro → espada → soldado | **Parcial** | Ferro → lingote → espada, funcionando de ponta a ponta com esteiras | Soldado: não há aldeão, escola nem equipamento |
| Cadeia madeira → flechas → torre de arqueiros | **Não começou** | Madeira → haste (serraria) | Ponta, montagem, flecha, torre, arqueiro |
| Ciclo dia/noite, 10 noites, 2 inimigos | **Não começou** | Só a horda sintética da cena de estresse (5.000 cápsulas andando, sem IA) | Relógio do dia, spawn, IA de caminho, dano, Coração, derrota |
| O Castelão: anda, coleta, constrói, luta, renasce | **Parcial** | Anda (só corre), coleta encostado, constrói com prévia e barra, alimenta e recolhe, desmonta | Luta, vida, morte e renascimento no Coração |

Fora do MVP, mas feito: menu inicial, Biografia com palco 3D e máquinas trabalhando de verdade, painel de
desempenho (F1–F12), cena de estresse com dois modos de desenho, `docs/ARQUITETURA_ESCALA.md`, pipeline
Meshy + Blender em Python, texturas de chão e placas de piso (ainda não construíveis).

Números de hoje: 78 testes de simulação, 1.631 linhas em `src/Simulation`, 3.611 em `src/View`, 2.999 de Python
nas ferramentas; 60 FPS ou mais em 3024×1890 com toda a grama.

## 3. Como o projeto está caminhando

### Pontos fortes

- **A regra nº 1 foi respeitada em todas as tarefas.** A simulação é C# puro, testável, e a view só lê. Isso
  permitiu que 5 marcos de simulação (Castelão, construir, esteiras, máquinas, aldeões) passassem nos testes na
  primeira execução, e que a cena de estresse medisse 15.500 entidades em menos de 1 ms por tick.
- **Dados em JSON desde o início.** Custos, receitas, velocidades, terrenos, biografia. Balancear não exige código.
- **Disciplina de processo.** Tarefas pequenas, um commit por tarefa, diário com o que deu errado. O diário já
  cumpre o objetivo da seção 11 (medir a IA), com detalhe raro de encontrar.
- **Desempenho medido cedo, com método.** O painel F3, o V-Sync desligado, o aviso de janela sem foco e o LOD por
  folha achatada levaram de 38 para 78 FPS sem tocar no visual aprovado. Há um plano escrito para 30 a 40 mil
  entidades.
- **Arte da protagonista aprovada e integrada**, com passada medida para os pés não deslizarem: o pipeline
  conceito → Meshy → Blender → Godot funciona para personagens.

### Riscos

1. **O loop central ainda não existe.** Noite, horda, combate e Coração são zero linhas. Tudo o que foi validado
   até agora (câmera, esteiras, máquinas) é o "dia"; se a "noite" não for divertida, o resto não segura o jogo.
   A meta da fase 1 do GDD ("amigos jogam 30 min e querem continuar") não pode ser testada ainda.
2. **O aldeão consumiu muito e não fechou.** 21 entradas do diário de arte e 438 créditos da Meshy (de 642 gastos
   no total) em cinco abordagens de rosto (decal → máscara em malha → planos 2D), três de cabelo (recorte →
   touca → perucas) e uma de pele; o resultado final ainda tinha "mechas soltas, touca aparecendo, olho cortado".
   A causa, na minha leitura: o modelo foi refinado de perto (prévias no Blender e SubViewport) enquanto a câmera
   do jogo o vê a 55° e 16 unidades de distância, de onde a franja cobre os olhos. O acabamento precisa ser
   julgado na câmera do jogo desde a primeira versão.
3. **Tendência a polir antes de fechar.** Grama (6 iterações), clima, texturas v1 e v2, rosto do aldeão: são
   escolhas legítimas do humano, mas cada uma empurrou o loop dia/noite. Vale decidir uma cota: por exemplo,
   a cada tarefa de visual, uma de loop.
4. **Dois agentes em paralelo (arte na `arte`, jogo na `master`) geraram atritos.** O GDD local divergiu do vivo
   duas vezes (uma reexportação apagou a decisão "só corre"); o agente de arte mexeu em código do jogo três vezes
   com permissão; `.import` oscilam entre os dois editores. Funcionou, mas exige a checagem "GDD local = commit"
   antes de reexportar (já anotada no diário) e merge frequente.
5. **Orçamento de GPU já usado pela grama.** A cena base fica em 12,8 ms de 16,7 disponíveis a 60 FPS, antes de
   existir horda, torres, tochas e sombras de noite. O plano de escala diz o que fazer (nada pequeno projeta
   sombra, LOD em tudo), mas ainda não foi aplicado a inimigos.

### Dívidas técnicas (por ordem de importância)

- **Duas simulações.** `SimWorld` (objetos, listas, A* por aldeão) e `StressWorld` (arrays por componente). O
  `ARQUITETURA_ESCALA.md` propõe migrar a primeira para o estilo da segunda; ninguém começou. A horda deve nascer
  já no estilo de arrays, ou a migração vai custar o dobro.
- **`WorldView.cs` com 657 linhas e muitas responsabilidades** (chão, recursos, construções, itens, etiquetas,
  foco, efeitos). Vai crescer com inimigos e torres; vale quebrar em `TerrainView`, `BuildingsView`,
  `ItemsView`, `LabelsView`.
- **Itens em esteiras são um `MeshInstance3D` por item.** Funciona para dezenas; o plano de escala manda MultiMesh
  por pedaço. Só vira problema com centenas de esteiras.
- **Cabanas de trabalho órfãs.** Com o aldeão fora, a cabana existe, custa recursos e não faz nada. Está marcada
  "aguardando o novo aldeão" em 6 lugares (`Workplace`, `SimWorld.TickWorkplaces`, `WorldView.WorkplaceLines`,
  `buildings.json`, `mapa_teste.json`, `BiographyRoot`). Se o desenho novo (GDD, "Gameplay v1": carregadores e
  operadores) não usar cabanas, elas devem sair.
- **Uma receita por máquina** (validação em `GameData.Parse`). A seção 5 do GDD pede cadeias de 5 a 10 etapas.
- **Sem save.** O botão Continuar do menu olha um arquivo que nada escreve.
- **`tools/blender/normalize.py` com cerca de 700 linhas só do aldeão v1** (rosto, pele, planos, manivela,
  carregar) que ficaram dormentes; podar quando o aldeão novo definir o que precisa.
- **`BiographyRoot` monta um mapa JSON à mão** para o palco das máquinas; melhor um `MapLoader` que aceite um
  objeto em memória.
- **O GDD tem a subseção "Aldeão: implementação v1"** descrevendo o que hoje não existe no código. Não foi tocada
  por ordem do humano; precisa ser reescrita junto com o aldeão novo.

## 4. Quanto foi feito por IA e onde a IA teve dificuldade

**Tudo o que está no repositório foi escrito por IA.** Nas 69 entradas do diário, "Correções manuais: nenhuma"
aparece em todas as que têm o campo (43); a única intervenção humana registrada foi mover o GDD para `docs/` no
primeiro dia. O humano dirigiu, aprovou, reprovou e testou jogando. Agentes: 53 entradas com Opus 5.5, 16 com
Fable 5.1; 21 entradas foram do agente de arte na branch `arte`. Ritmo: 33 commits em 25/09, 26 em 26/09, 26 em
27/09. Tarefas de simulação levaram de 2 a 6 minutos de relógio cada; as de arte, de 20 minutos a 2 horas.

### Onde a IA foi bem

- Sistemas de simulação com testes (marcos 2 a 6): passaram de primeira, sem correção manual.
- Pesquisa antes de implementar (câmera do Factorio, Nuclear Throne, biomecânica da corrida): decisões com fonte.
- Diagnóstico de desempenho: achou que o gargalo era GPU, mediu cada custo e ganhou 2× sem mudar o visual.
- Pipeline de arte da protagonista: recorte do conceito, correção da mão que faltava, escala, passada, materiais.

### Onde a IA teve dificuldade (do diário)

1. **Rosto e cabelo do aldeão** (ver risco 2): muitas tentativas, pouco critério de parada. A IA propôs cada
   abordagem seguinte com convicção; faltou dizer cedo "de cima não vai ler; simplifique".
2. **Medir desempenho no Mac:** V-Sync escondendo a folga, janela em segundo plano congelando o jogo, MCP só
   transportando 640 px, monitor 4K em vez da Retina. Cada armadilha custou uma rodada de medição.
3. **Testar pelo MCP:** cliques calculados pela projeção da câmera erravam com a câmera espiando o cursor real do
   humano; as coordenadas mudam com a resolução da janela (1152×648 ou 3840×2160). Hoje: as coordenadas de clique
   são em pixels da janela, não do viewport lógico.
4. **Gastar créditos sem calibrar:** a primeira métrica de emenda das texturas, calibrada só em ruído sintético,
   reprovou tudo e custou 48 créditos.
5. **Edição por script sem checar unicidade:** um `str.replace` trocou dois trechos e criou um bug que os testes
   não pegaram (marco 5). Corrigido com a regra "cada trecho aparece uma vez", usada até hoje.
6. **Sincronização entre GDD local e vivo:** duas vezes o export apagou mudanças feitas só num dos lados.
7. **Ferramentas e ambiente:** `GridMap` conflitando com `Godot.GridMap`; importador glTF do Blender criando
   formas de osso; Godot ignorando cor de vértice do glTF; assets do itch.io com caminhos do autor.

## 5. Próximos passos, em ordem

### 1. Aldeão novo (já decidido)

Proposta de como integrar ao que ficou:

**Antes de gerar qualquer coisa (GDD):** fechar três decisões que hoje estão em conflito ou em aberto no GDD:
cristal no peito (seção 6 diz sim, "O Primeiro Aldeão" diz não; a proposta de "nasce ao se formar" está lá, sem
decisão), roupas (nenhuma, pelo texto), e **como o rosto vai ler a 55° e 16 unidades**. Sugestão: expressão
por cor e postura (cristal, pose, balão de ícone) e não por traços finos do rosto; os traços ficam para a
Biografia e a câmera cinematográfica.

**Arte, do simples para o complexo:** um corpo só, com cabelo e roupa no próprio modelo (nada modular na
primeira versão), altura 0,4 m, frente +Z, pivô na base, um rig e cinco clipes (idle, walk, carry, work, sleep),
passada medida no JSON como na protagonista. Aprovar o conceito 2D de frente e costas antes da Meshy, e conferir
o modelo **dentro do jogo, na câmera normal**, antes de qualquer acabamento. Variedade (cabelo, chapéu por ofício)
só depois de aprovado, e só se ler de cima. Teto de créditos por tentativa acordado antes.

**Simulação:** `Villager` novo em `src/Simulation/`, com um contrato mínimo para a view: `Position`,
`PreviousPosition`, `Facing`, um enum de estado (parado, andando, carregando, trabalhando, descansando), carga e
expressão. Os pontos de encaixe existem e estão marcados "aguardando o novo aldeão": lista e tick em `SimWorld`,
seção `villagers` do mapa em `MapLoader`, `Workplace.Worker` (ou o operador de máquina e o carregador da
"Gameplay v1" do GDD, no lugar das cabanas), e testes em `tests/` no molde dos que saíram. Recomendo já nascer
no estilo de arrays do `ARQUITETURA_ESCALA.md` se a meta for centenas de aldeões; se for dezenas, uma classe
simples como a v1 serve.

**View:** `VillagerVisual` novo lendo só o contrato acima (a v1 tinha um `DrawState` que servia ao jogo, ao menu,
à Biografia e ao estresse; vale repetir a ideia). Encaixes: `WorldView.Build/Render/FindFocus/AnimatedNodes`,
entrada "villager" e botões na `BiographyRoot`, os aldeões em volta da protagonista no `MenuRoot`, e as teclas
0/1/2/3 na cena de estresse para medir o custo com 50/200/500.

**Ordem sugerida:** GDD → conceito aprovado → modelo + rig + clipes conferidos no jogo → simulação com testes →
view → Biografia, menu e estresse → GDD ("Aldeão: implementação v2").

### 2. Operador de máquina e carregador

O GDD ("fábricas e aldeões são inseparáveis") diz que máquina sem aldeão para. É a primeira mecânica do aldeão
novo, e substitui ou complementa as cabanas. Decidir aqui o destino das cabanas.

### 3. Noite mínima: relógio, um inimigo, o Coração e o Castelão lutando

Fechar o loop do GDD com o menor conjunto: dia de N minutos, o Coração da Cidadela como construção que perde,
goblin com caminho direto ao Coração (flow field, já no estilo de arrays), vida e ataque do Castelão, derrota e
renascimento. Só depois disso o jogo pode ser testado por 30 minutos como pede a fase 1.

### 4. Cadeia de munição: flecha e torre de arqueiros

Ponta na forja, montagem, torre que consome flechas. Primeira defesa automática.

### 5. Escola e soldado

Aldeão + espada + tempo → soldado. Fecha "ferro → espada → soldado" do MVP.

### 6. Arte das construções e recursos pela Meshy

Os 12 assets de `tools/assets.json` (cerca de 200 créditos), quando as formas simples começarem a atrapalhar a
leitura.

### 7. Save, segunda receita por máquina, quebra do `WorldView`

Dívidas que não bloqueiam o loop, mas bloqueiam a fase 2.

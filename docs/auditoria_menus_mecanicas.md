# Auditoria: menus e mecânicas × GDD (29/09/2026)

Feita pelo agente JOGO a pedido do Diretor. Comparei `scenes/Menu.tscn`, `Biography.tscn`, `Main.tscn` e o código
(`src/View`, `src/Simulation`) com o GDD: seção 3 (pausa e velocidade), seção 12 (câmera, menu inicial, Biografia,
Configurações), seção 20 (Castelão) e o que o `docs/DIARIO.md` deixou pendente nas mecânicas já feitas.
Fora do escopo: noite, horda, combate, Coração, andares e cadeias novas (ainda não começaram; ver
`docs/ESTADO_DO_PROJETO.md`).

Legenda: **[decidido]** = o GDD já decide, só falta fazer. **[Arthur]** = precisa de decisão antes.

## Lacunas e defeitos, em ordem de valor

1. **Não há pausa nem velocidade 1x/2x/3x** (seção 3). O `SimClock` só converte tempo real em ticks.
   **[decidido]** — feito em 531df05.
2. **Do jogo não se volta ao menu nem se sai.** No `Main.tscn` o Esc só solta o que está na mão ou sai da
   cinematográfica; não há menu de pausa. A única saída é fechar a janela. **[decidido pelo pedido]** — feito em
   1fa6a14.
3. **Configurações não são salvas.** Tela cheia e V-Sync funcionam no painel do menu, mas voltam ao padrão a cada
   abertura, e o painel só existe no menu inicial. **[decidido]** (seção 12: "esboço: tela cheia e V-Sync") — feito no
   commit das configurações (`user://settings.cfg`).
4. **Conflito de teclas no GDD: 1, 2, 3.** A seção 20 dá 1–9 à barra de construção; a seção 12 sugere "PageUp/PageDown
   (ou 1, 2, 3)" para os andares; o pedido sugeria 1/2/3 para a velocidade. Hoje 1–9 é a barra. Para a velocidade
   usei `-` e `=` (a tecla do `+`) e Espaço para pausar; andares ficam com PageUp/PageDown quando existirem.
   **[Arthur]**: confirmar essas teclas e riscar o "(ou 1, 2, 3)" dos andares no GDD.
5. **Menu inicial sem aldeões.** O GDD diz "a protagonista em idle com o cristal aceso e aldeões por perto"; o
   `MenuRoot` ainda diz "aguardando o novo aldeão", mas o aldeão v2 já está no jogo. **[decidido]**, 0 crédito
   (é pôr 3 ou 4 `VillagerVisual` como no jogo). Feito na tarefa 2.
6. **Construir e mexer no mundo durante a pausa.** O GDD não diz. Escolhi o mais simples: na pausa, cliques e teclas
   que mudam o mundo (construir, coletar, desmontar, pôr item, WASD) são ignorados; câmera, zoom, giro e
   cinematográfica continuam. **[Arthur]**: jogos como RimWorld deixam planejar na pausa; aqui não há
   "planta" (blueprint) ainda, então construir na pausa seria construir instantâneo.
7. **Castelão não fabrica à mão** (seção 20, "Trabalho manual": "fabrica itens simples à mão, devagar"). Não existe
   receita manual nem tela de fabricação. **[Arthur]**: quais receitas são de mão, onde aparecem (barra, tecla) e
   o tempo.
8. **Aldeões: "seguem o protagonista quando chamados"** e **atributos visíveis ao passar o mouse** (GDD, "Gameplay
   v1") não existem; eles só trabalham nas cabanas. **[Arthur]**: tecla ou ação de chamar, e se a v1 ainda vale
   depois do v2 (o GDD marca a v1 como "não definitivo").
9. **Aldeões atravessam tudo, inclusive o Castelão** (diário, marco 2: "ficou fora do escopo"). **[Arthur]**: com
   centenas de aldeões, colisão entre eles custa caro; decidir se colidem com construções, com o Castelão ou com
   nada.
10. **Clipes do aldeão que faltam** (diário, fechamento de 29/09): `carry`, `work`, `sleep`; hoje o estado
    "carregando" reusa o `run`. **[decidido]**, mas é tarefa de arte (créditos), não de jogo.
11. **Cabelos "sob chapéu" não entregues:** a regra "cobre: parcial" hoje esconde o cabelo inteiro. **[decidido]**,
    tarefa de arte.
12. **Uma receita por máquina** (`GameData.Parse` recusa mais). Serraria, fundição e forja fazem uma coisa cada.
    **[decidido]** pela seção 5 (cadeias de 5 a 10 etapas), mas precisa das receitas: **[Arthur]**.
13. **Continuar do menu sem save.** O botão fica desativado corretamente (nada escreve `user://save.json`).
    Sistema de save: **[Arthur]** (quando entra no plano).
14. **Volume desativado nas Configurações.** O painel mostra um volume sem efeito (não há som). Não está no esboço do
    GDD; deixei como estava. **[Arthur]**: tirar até existir som, ou manter como lembrete.
15. **Debug na tela do jogo.** A linha de cima (ticks, FPS, patamar dos aldeões, V e B) aparece sempre para quem
    joga. É útil agora; **[Arthur]**: esconder atrás do F3 quando amigos forem testar (meta da fase 1).

16. **Caixa de seleção desmarcada quase invisível.** No painel de Configurações, com o tema padrão do Godot, a caixa
    do V-Sync desligado some no fundo escuro (só o texto aparece; ver `docs/prints/polimento_configuracoes_salvas.png`).
    Defeito visual pequeno; corrigir é dar um ícone próprio às caixas. **[Arthur]** só se quiser um tema de UI
    próprio; senão, faço junto do próximo polimento.
17. **Palco da Biografia com faixas.** No print `docs/prints/polimento_biografia.png` o palco 3D aparece como um
    retângulo mais claro no alto, com a protagonista passando da borda de baixo para o painel das animações.
    Pode ser o enquadramento do SubViewport; é visual, então **[Arthur]** diz se incomoda antes de eu mexer.
    (A Biografia ainda mostra a protagonista v1, o que é esperado até a v2 chegar.)

Prints desta auditoria: `docs/prints/jogo_pausado.png`, `menu_pausa.png`, `polimento_menu_inicial.png`,
`polimento_configuracoes_salvas.png`, `polimento_biografia.png` (960×540, capturas do godot-ai).

## Conferido e em dia com o GDD

- Câmera (seção 12): espiar pelo cursor, arrastar com o meio, zoom 1,1 com máximo 0,4, giro com encaixe em 90°,
  inclinação 55°, cinematográfica com C/Esc e legenda.
- Menu inicial: Novo jogo, Continuar desativado sem save, Biografia, Configurações, Sair; crepúsculo do jogo,
  protagonista em idle com cristal.
- Biografia: categorias, entradas de `data/biography.json`, palco 3D girável, botões de animação, máquinas
  trabalhando num mundo pequeno, "← Voltar ao menu" e Esc.
- Castelão (seção 20): WASD relativo à câmera, só corre (2,4 cél/s de `castellan.json`), alcance 10, coleta
  encostado, barra 1–9 com prévia verde/vermelha, R gira, arrastar faz fileira, direito desmonta com 100% de volta,
  itens na mão, baú recolhe tudo, esteiras de 3 itens a 1,5 cél/s com curva e fila.

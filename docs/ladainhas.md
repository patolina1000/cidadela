# LADAINHAS — aldeões programados (ordem do Arthur, 30/09/2026)

> **REGRA ABSOLUTA (Arthur, 30/09/2026): O ALDEÃO NÃO FAZ NADA SOZINHO.** Sem ladainha, ele fica parado. Ele só vai a um
> posto, carrega, colhe ou opera porque a ladainha dele manda. Nenhuma construção chama, atribui ou move aldeão por conta
> própria.

Cópia fiel de `~/Projetos/cidadela-diretor/especificacoes/ladainhas.md` (Diretor), com o que o estudo do Autonauts
(`~/Projetos/cidadela-diretor/estudos/autonauts.md`) trouxe. Números em `data/`. Esteiras e mariposas arquivadas na tag
`esteiras-mariposas-arquivadas`.

## Mudança de rumo: sem esteiras

O jogo não terá esteiras nem mariposas nesta versão. Toda a automação é feita por ALDEÕES PROGRAMADOS operando máquinas. Os aldeões recebem programas (nome provisório: LADAINHAS) e os repetem. Referência principal: Autonauts (ensinar robôs fazendo a tarefa na frente deles e depois editar o programa em blocos, como no Scratch).

**Motivo:** todo jogo de automação tem esteira; programar aldeões é a identidade do Cidadela. Está na história: o aldeão "não pensa em causas, só em repetições" e "segue o protagonista como uma sombra".

## O que continua valendo

- Rede de torres de mana no estilo da rede elétrica do Factorio.
- Relicário, Mina de cristal, Poço, Purificador, Barreiro, Oleiro e Cristal-mãe, com os números de `docs/linha_energia.md` e `docs/linha_aldeoes.md`.
- Toda máquina precisa de mana e de alguém no posto. Nenhuma máquina anda sozinha, e os aldeões trabalham até o fim.
- Pesos dos itens (pesado, leve; médio em aberto) e as ações à mão da protagonista.
- O aldeão se forma de casca + fragmento puro + mana.

## O que muda nas duas linhas

- As máquinas guardam o que recebem e o que produzem. Tudo entra e sai pela mão de alguém: aldeão ou protagonista.
- Todo transporte é feito por aldeões seguindo ladainhas. O baú vira o ponto de troca entre eles.
- O aldeão nasce VAZIO: sai do Cristal-mãe e fica parado ao lado dele, sem ir para posto nenhum, até receber uma ladainha. Isso substitui o "vai sozinho para o posto vazio".
- Carga por viagem: pesado 1 por ponto de Força; leve 10.

## Atributos do aldeão

- **Força:** carga de pesados; no futuro, máquinas pesadas e espada.
- **Agilidade:** velocidade de andar (+10% por ponto acima de 1); no futuro, arco.
- **Inteligência:** tamanho da ladainha e quais comandos ele entende.
- O nível 1 nasce com 1 em tudo. Subir atributos (poções, escola) é outra linha: NÃO implementar agora.

## Comandos (nomes provisórios) e requisito de Inteligência

**Inteligência 1:** ladainha de até 6 comandos, que se repete sempre do início.
- Ir até [construção, recurso ou lugar]
- Pegar [item] de [lugar]
- Pôr [item] em [lugar]
- Colher, arrancar ou cavar [recurso mais perto, dentro de um raio]
- Operar [máquina] até [ficar sem insumo ou com a saída cheia]
- Esperar [segundos]

**Inteligência 2:** até 12 comandos.
- Quando [condição] … Senão …
- Repita … até que [condição]
- Condições: mãos cheias ou vazias; [lugar] tem ou não tem [item]; [máquina] precisa de [item]; rede com pouca mana; é noite.

## Ensinar

1. **Por demonstração (primeiro):** a protagonista escolhe um aldeão e aperta "Ensinar". O que ela faz (ir, pegar, pôr, colher, operar) vira comandos. Aperta "Pronto", e o aldeão começa a repetir.
2. **Editor em blocos (depois):** ver e ajustar a ladainha de um aldeão (trocar alvo, apagar comando, pôr condição).
3. **Copiar** a ladainha de um aldeão para outros (versão 1: de graça, com seleção de vários). A ladainha como item de pergaminho fica EM ABERTO, para decidir depois.

Se a ladainha usa um comando que a Inteligência do aldeão não alcança, ou é longa demais, ele não aceita, e a interface diz por quê.

## Estados visíveis do aldeão

- sem ladainha (parado);
- trabalhando (comando atual);
- travado (qual comando e por quê: sem item, lugar cheio, sem caminho, não aguenta o peso).

## Técnico

- As ladainhas rodam na simulação, em ticks fixos, deterministas, um comando por vez por aldeão, com o GridPath existente.
- Ladainhas salvas como dados (JSON) para testes e mapas.
- Medir FPS com 50, 200 e 500 aldeões executando ladainhas, fora do editor, em 3024×1890.

## Testes com o Arthur (quando chegarmos lá)

- **A) Mínimo de aldeões:** as duas linhas montadas, com os aldeões mínimos já carregando ladainhas prontas do JSON. Mostrar tudo andando sozinho.
- **B) Zero aldeões:** o Arthur forma o primeiro aldeão à mão e ensina a primeira ladainha por demonstração.

## Ajustes do Arthur ao plano (30/09/2026)

1. **Postos de máquina ficam**, inclusive os acoplados (serra de dois homens, prova de operação): são o lugar onde o
   operador encosta. O aldeão só ocupa um posto quando a ladainha dele tem "Operar [máquina]". A chamada automática
   para postos sai de vez.
2. **Cabanas e Posto de Carregadores:** sai todo comportamento automático deles, mas NÃO são apagados. Ficam como LUGARES
   que a ladainha pode citar ("colha tora perto da Cabana do Lenhador", "ponha na Cabana"), definindo a área de busca e o
   estoque. A cabana nunca dá ordem a ninguém. Sem cabana citada, vale o raio de 8 células em volta de onde o comando foi
   gravado. Entra num passo próprio, logo depois de "copiar ladainhas".
3. **Blocos na tela desde o começo:** as ladainhas são programação no estilo Scratch. Junto dos estados visíveis, clicar
   num aldeão mostra a ladainha dele desenhada em BLOCOS (encaixes, cor por tipo de comando, o comando atual aceso), só
   para ver. O editor em blocos aproveita o mesmo desenho.

## Do estudo do Autonauts (Diretor, 30/09/2026)

### O que as ladainhas copiam

- **Gravar a intenção, não a coordenada:** "colher a árvore mais próxima dentro do raio". O "achar mais próximo" existe desde a Inteligência 1; sem ele, 6 comandos não servem para nada.
- **Área presa a um objeto do mundo:** um marco ou estandarte da aldeia. Mover o marco move todos os aldeões ligados a ele.
- **Reserva de alvo:** dois aldeões não disputam a mesma árvore nem o mesmo item.
- **Repetir sempre do início na Inteligência 1:** sem loop para esquecer.
- **Copiar de graça**, como já está na especificação. A protagonista "recita" a ladainha para outros aldeões.

### O que as ladainhas evitam

- **Nunca travar calado.** Sobre a cabeça do aldeão: qual comando ele está fazendo e, se parou, por quê, em palavras do jogo ("não acho árvore no raio", "mãos cheias", "baú cheio", "sem caminho", "pesado demais"). É o estado "travado" da especificação, e é o ponto mais importante.
- **Não obrigar a regravar.** O editor em blocos deixa trocar alvo, raio e ordem sem andar pelo mapa.
- **Estado inicial previsível.** Ao começar uma ladainha, o aldeão solta o que carrega num baú ou no chão, para a Inteligência 1, que não tem condições, não travar como o balde do Autonauts.
- **Nada de laço girando à toa.** Quando falta alvo, o aldeão espera um pouco mais a cada tentativa. Isso protege o FPS com centenas de aldeões.
- **Pathing que não congela.** Se não há caminho, ele avisa ("sem caminho") e tenta de novo depois.

### Três decisões pequenas

1. **"Quando" e "repita até" gastam 1 comando cada**, como o loop do Autonauts. Os comandos dentro deles contam à parte.
2. **"Se falhar, pule"** (o "exit on fail") fica como ideia para a Inteligência 2 ou 3; não entra na versão 1.
3. **"Cheio"** quer dizer cheio de verdade (100%), mostrado na interface. Sem os 95% escondidos.

## Ideias guardadas

**Mariposas de cristal** (voltar depois das ladainhas; não implementar agora):
- Carregadoras que NÃO são programadas: fazem transporte simples sozinhas, e muito bem.
- Só levam itens leves; os pesados continuam com os aldeões.
- Vão atrás da luz das torres de mana: só trabalham dentro da área da rede e, sem mana, pousam.
- Papel no jogo: aliviar o transporte simples mais para frente, deixando as ladainhas para o trabalho que exige aldeão.
- Motivo do Arthur: deixam o mundo mais mágico.
- O código antigo delas fica arquivado na tag `esteiras-mariposas-arquivadas`, como o das esteiras.

# LINHA DA ENERGIA — especificação (ordem do Arthur, 30/09/2026)

Cópia fiel de `~/Projetos/cidadela-diretor/especificacoes/linha_energia.md` (Diretor). Números iniciais, todos em
`data/`. Substitui a linha da flecha de ferro (arquivada na tag `linha-flecha-arquivada`).

## Mudança de rumo

- Torque e a linha da flecha foram descartados.
- A energia é MANA, numa rede de torres no estilo da rede elétrica do Factorio.
- A primeira linha complexa é a LINHA DA ENERGIA. A segunda (depois, não agora) será a linha dos aldeões.

## Regras do jogo

- Os aldeões trabalham nas máquinas até o fim. Nenhuma máquina anda sozinha. A progressão é dos aldeões (especialização, velocidade, autonomia), e eles serão uma linha de produção própria.
- A energia nunca é infinita: sempre depende de linhas de produção.
- O jogador começa com ZERO aldeões e precisa conseguir montar a linha da energia sozinho, com a protagonista, que pode operar qualquer máquina.

## Regras da linha

1. Toda máquina precisa de mana chegando E de alguém no posto (a protagonista ou um aldeão). Saiu do posto, a máquina para.
2. O Relicário é a exceção: queima sozinho o que tiver dentro; alguém só o abastece.
3. Peso dos itens (campo "peso" em `data/items.json`: "pesado", "medio", "leve"):
   - pesado: só nas costas (ou carroça, que ainda não existe); nunca em esteira nem em mariposa;
   - leve: esteira e mariposa; nas costas também, mas é ineficiente;
   - medio: EM ABERTO, não implementar.
   Itens desta linha: tora, pedra e fragmento podre são pesados; jarro d'água e fragmento puro são leves.
4. Item só entra e sai de máquina por mariposa ou pela mão de alguém (protagonista ou carregador). As máquinas não soltam nada sozinhas.
5. Esteira não gasta mana e não tem operador.
6. Rede de mana como a rede elétrica do Factorio:
   - torres se ligam sozinhas às vizinhas ao alcance do fio;
   - a área de abastecimento alimenta o que encosta nela;
   - redes separadas são independentes;
   - faltou mana, TODOS os consumidores da rede recebem a mesma fração e ficam mais lentos por igual; nada trava.
   Reaproveitar a ideia do grafo de somas da antiga rede de torque, recalculado só quando algo entra ou sai.
7. Pesos nas costas por viagem: pesado 1, leve 10.

## Ações à mão da protagonista

- colher tora ou pedra: 2 s, 1 item;
- arrancar cristal podre do veio: 4 s, 1 fragmento podre;
- purificar com as mãos: 6 s, 2 podres → 1 puro, SEM água (só ela faz);
- operar máquina: encostar e apertar E assume o posto; E de novo ou andar sai;
- pôr e tirar itens das máquinas à mão.

## Mapa

Veio de cristal podre (esgota), árvores, pedras, água, e o Cristal-mãe perto do início.

## Construções

| Construção | Custo | Mana | Posto | Faz |
|---|---|---|---|---|
| Relicário | 10 pedras + 5 puros | gera 10/s | nenhum | queima 1 puro a cada 20 s |
| Torre pequena de mana | 2 toras + 1 puro | 0 | nenhum | fio até 7 células; abastece área 5×5 |
| Mina de cristal (sobre o veio) | 10 pedras + 5 toras | 2/s | 1 | 1 podre a cada 5 s, guardado nela |
| Poço (ao lado da água) | 10 pedras | 1/s | 1 | 1 jarro d'água a cada 8 s |
| Purificador | 5 pedras + 5 toras + 2 puros | 3/s | 1 | 2 podres + 1 jarro → 1 puro em 10 s |
| Mariposa de cristal nível 1 | 1 puro | 0,1/s parada, 0,5/s voando | nenhum | só itens leves; pega da célula de trás e põe na da frente; 1,2 s por item; sem mana, pousa |
| Mariposa nível 2 | a definir | igual | nenhum | igual, passando por cima de 1 célula (alcance 2) |
| Esteira | 1 tora por célula | 0 | nenhum | leva itens leves |
| Baú | 5 toras | 0 | nenhum | guarda qualquer item |
| Cristal-mãe | já existe no mapa | consome o que sobrar | nenhum | por enquanto só acumula mana, com barra de carga; formar aldeões é a linha 2, NÃO implementar |

## Fluxo

- Mina → Purificador: podre nas costas (carregador ou protagonista).
- Poço → mariposa → esteira → mariposa → Purificador.
- Purificador → mariposa → esteira → mariposa → Relicário.
- Relicário → torres → máquinas, mariposas e Cristal-mãe.

Conta esperada: 1 Relicário = 10 mana/s com 3 puros/min; as máquinas gastam cerca de 6 mana/s; sobram perto de 4 mana/s para o Cristal-mãe.

## Feedback visual mínimo (formas provisórias, sem arte nova)

- estado de cada máquina: trabalhando, falta insumo (qual), sem operador, sem mana, saída cheia;
- barra de progresso da receita;
- fios de luz azul-fria entre as torres, que piscam com a rede fraca;
- mariposa como pontinho de luz batendo asas entre as duas células;
- no HUD: geração × consumo da rede e a carga do Cristal-mãe;
- Alt mostra todos os estados; mouse em cima mostra receita, operador, mana e o que falta;
- barra de construção só com as construções desta linha.

## Implementação (passos pequenos, um commit cada, com build, testes, diário e push)

1. pesos dos itens;
2. rede de torres;
3. máquinas e Relicário;
4. mariposas;
5. ações à mão e operar posto;
6. carregadores com pesos;
7. feedback visual;
8. cenas de teste.

Testes automáticos da simulação para a rede (fração por igual, redes separadas), as mariposas (recusam pesado), os postos e a conta de mana.

## Testes com o Arthur (nesta ordem)

- **A) Mínimo de aldeões:** `scenes/tests/LinhaEnergia.tscn` com `data/maps/linha_energia.json`; a linha inteira já montada, com o Relicário começando com 3 puros; 4 aldeões: operadores da mina, do poço e do purificador, e 1 carregador para os podres. Mostrar a linha andando sozinha, com a sobra de mana chegando ao Cristal-mãe. Medir a sobra real de mana e o FPS.
- **B) Zero aldeões:** outro mapa, só recursos, água, veio e o Cristal-mãe, nada construído. O Arthur joga e monta tudo com a protagonista.

Para cada teste, o JOGO abre o Godot com a cena pelo godot-ai e avisa que está pronto para jogar.

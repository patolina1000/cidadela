# LINHA DA ENERGIA — especificação (ordem do Arthur, 30/09/2026)

Cópia fiel de `~/Projetos/cidadela-diretor/especificacoes/linha_energia.md` (Diretor). Números iniciais, todos em
`data/`. Substitui a linha da flecha de ferro (arquivada na tag `linha-flecha-arquivada`).

> **ATUALIZADO em 30/09/2026 (mudança de rumo: ladainhas, `docs/ladainhas.md`).** Sem esteiras e sem mariposas
> (arquivadas na tag `esteiras-mariposas-arquivadas`). Todo transporte é feito por aldeões seguindo ladainhas; o baú é o
> ponto de troca entre eles. As máquinas guardam o que recebem e o que produzem: tudo entra e sai pela mão de um aldeão ou
> da protagonista. O aldeão formado nasce vazio. Carga por viagem: pesado 1 por ponto de Força, leve 10. As partes que
> falavam de esteira e mariposa foram tiradas ou reescritas abaixo; o resto segue a especificação original.

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
   - pesado: nas costas (ou carroça, que ainda não existe), 1 por ponto de Força;
   - leve: nas costas, 10 por viagem;
   - medio: EM ABERTO, não implementar.
   Itens desta linha: tora, pedra e fragmento podre são pesados; jarro d'água e fragmento puro são leves.
4. Item só entra e sai de máquina pela mão de alguém (protagonista ou aldeão). As máquinas guardam o que recebem e o que
   produzem e não soltam nada sozinhas.
5. (Esteira: descartada em 30/09.)
6. Rede de mana como a rede elétrica do Factorio:
   - torres se ligam sozinhas às vizinhas ao alcance do fio;
   - a área de abastecimento alimenta o que encosta nela;
   - redes separadas são independentes;
   - faltou mana, TODOS os consumidores da rede recebem a mesma fração e ficam mais lentos por igual; nada trava.
   Reaproveitar a ideia do grafo de somas da antiga rede de torque, recalculado só quando algo entra ou sai.
7. Pesos nas costas por viagem: pesado 1 por ponto de Força (o aldeão nasce com Força 1), leve 10.

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
| Baú | 5 toras | 0 | nenhum | guarda qualquer item; o ponto de troca entre os aldeões |
| Cristal-mãe | já existe no mapa | 4/s enquanto forma | nenhum | forma aldeões (linha 2, `docs/linha_aldeoes.md`); não guarda mais mana |

Mariposas e esteira saíram desta tabela em 30/09 (as mariposas voltam depois das ladainhas, como carregadoras não
programadas: `docs/ladainhas.md`, "Ideias guardadas").

## Fluxo

Todo transporte é feito por aldeões seguindo ladainhas (ou pela protagonista); o baú é o ponto de troca.

- Mina → Purificador: podre nas costas (aldeão ou protagonista).
- Poço → Purificador: jarro nas costas (aldeão ou protagonista), 10 por viagem.
- Purificador → Relicário: puro nas costas, 10 por viagem.
- Relicário → torres → máquinas e Cristal-mãe.

Conta esperada: 1 Relicário = 10 mana/s com 3 puros/min; as máquinas gastam cerca de 6 mana/s; sobram perto de 4 mana/s (antes iam para o Cristal-mãe; hoje ele gasta formando aldeões e a sobra se perde).

## Feedback visual mínimo (formas provisórias, sem arte nova)

- estado de cada máquina: trabalhando, falta insumo (qual), sem operador, sem mana, saída cheia;
- barra de progresso da receita;
- fios de luz azul-fria entre as torres, que piscam com a rede fraca;
- no HUD: geração × consumo da rede e a carga do Cristal-mãe;
- Alt mostra todos os estados; mouse em cima mostra receita, operador, mana e o que falta;
- barra de construção só com as construções desta linha.

## Implementação (passos pequenos, um commit cada, com build, testes, diário e push) — feita até 8e426d4; esteiras e mariposas descartadas depois

1. pesos dos itens;
2. rede de torres;
3. máquinas e Relicário;
4. mariposas (descartadas em 30/09);
5. ações à mão e operar posto;
6. carregadores com pesos;
7. feedback visual;
8. cenas de teste.

Testes automáticos da simulação para a rede (fração por igual, redes separadas), os postos e a conta de mana (os das mariposas saíram com elas).

## Testes com o Arthur (nesta ordem) — substituídos pelos de `docs/ladainhas.md`

- **A) Mínimo de aldeões:** `scenes/tests/LinhaEnergia.tscn` com `data/maps/linha_energia.json`; a linha inteira já montada, com o Relicário começando com 3 puros; 4 aldeões: operadores da mina, do poço e do purificador, e 1 carregador para os podres. Mostrar a linha andando sozinha, com a sobra de mana chegando ao Cristal-mãe. Medir a sobra real de mana e o FPS.
- **B) Zero aldeões:** outro mapa, só recursos, água, veio e o Cristal-mãe, nada construído. O Arthur joga e monta tudo com a protagonista.

Para cada teste, o JOGO abre o Godot com a cena pelo godot-ai e avisa que está pronto para jogar.

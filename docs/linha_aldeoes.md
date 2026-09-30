# LINHA 2: FORMAR ALDEÕES — especificação (ordem do Arthur, 30/09/2026)

Cópia fiel de `~/Projetos/cidadela-diretor/especificacoes/linha_aldeoes.md` (Diretor). Números iniciais, todos em
`data/`. Continua a linha da energia (`docs/linha_energia.md`).

> **ATUALIZADO em 30/09/2026 (mudança de rumo: ladainhas, `docs/ladainhas.md`).** Sem esteiras e sem mariposas
> (arquivadas na tag `esteiras-mariposas-arquivadas`). Todo transporte é feito por aldeões seguindo ladainhas; o baú é o
> ponto de troca entre eles. As máquinas guardam o que recebem e o que produzem: tudo entra e sai pela mão de um aldeão ou
> da protagonista. O aldeão formado nasce vazio. Carga por viagem: pesado 1 por ponto de Força, leve 10. As partes que
> falavam de esteira e mariposa foram tiradas ou reescritas abaixo; o resto segue a especificação original.

## O processo aprovado

- A casca de barro é o corpo.
- O fragmento puro vira o cristal do peito.
- A mana é o sopro.

## Itens novos

- argila: pesado;
- casca: pesado.

Seguem as mesmas regras de peso da linha da energia: pesado nas costas, 1 por ponto de Força.

## Mapa

- Células de MARGEM: terra encostada na água, onde se cava argila.
- O mapa da linha da energia ganha um trecho de margem perto do Poço.

## Construções

| Construção | Custo | Mana | Posto | Faz |
|---|---|---|---|---|
| Barreiro (em célula de margem) | 10 pedras | 1/s | 1 | 1 argila a cada 6 s, guardada nele |
| Oleiro | 10 pedras + 5 toras | 2/s | 1 | 2 argilas + 1 jarro d'água → 1 casca em 15 s |
| Cristal-mãe (já existe) | — | 4/s enquanto forma | nenhum | 1 casca + 1 fragmento puro + 150 s de mana (600 no total) → 1 aldeão nível 1 |

## Cristal-mãe

- Substitui o "só acumula mana" da linha da energia.
- Guarda até 2 cascas e 2 puros; forma um aldeão por vez.
- Recebe a casca e o puro pela mão de um aldeão (com ladainha) ou da protagonista.
- Com a rede fraca, forma mais devagar, pela mesma fração das outras máquinas.
- O aldeão nasce VAZIO: sai do Cristal-mãe e fica parado ao lado dele, sem ir para posto nenhum, até receber uma ladainha
  (`docs/ladainhas.md`; substitui o "vai sozinho para o posto vazio mais perto").

## Fluxo

- Barreiro → argila nas costas → Oleiro.
- Poço → jarro nas costas → Oleiro. O jarro agora é disputado entre Purificador e Oleiro.
- Oleiro → casca nas costas → Cristal-mãe.
- Purificador → puro nas costas → Cristal-mãe. O puro agora é disputado entre Relicário e Cristal-mãe.
- Todo transporte por aldeões com ladainhas (ou pela protagonista); o baú é o ponto de troca.

## Ações à mão da protagonista (além das da linha da energia)

- cavar argila na margem: 3 s, 1 argila;
- moldar casca com as mãos: 20 s, 2 argilas, precisa estar a até 2 células da água (sem jarro);
- pôr casca e puro no Cristal-mãe.

Com isso ela forma o primeiro aldeão sem nenhuma máquina.

## Tensão esperada

1 Relicário (10 mana/s) não sustenta as duas linhas inteiras (cerca de 6 + 3 + 4 = 13 mana/s). Isso é DE PROPÓSITO: o jogador precisa de um segundo Relicário, e portanto de mais fragmentos. Medir e registrar.

## Visual provisório (sem arte nova)

- Dentro do Cristal-mãe, a forma escura de um aldeão que vai clareando com a barra de carga.
- Estados do Barreiro, do Oleiro e do Cristal-mãe iguais aos das outras máquinas (sem casca, sem puro, sem mana).

## Testes automáticos da simulação

- O Cristal-mãe só forma com casca + puro + mana, e forma mais devagar com a rede fraca.
- O aldeão nasce vazio e fica parado ao lado do Cristal-mãe.
- Argila e casca são pesadas (1 por ponto de Força por viagem).
- Moldar à mão exige água perto.

## Testes com o Arthur (substituem os anteriores) — agora substituídos pelos de `docs/ladainhas.md`

- **A) Mínimo de aldeões:** as duas linhas montadas, 2 Relicários, e os aldeões mínimos para tudo andar (operadores da mina, do poço, do purificador, do barreiro e do oleiro; carregadores para os pesados). Dizer quantos foram. Medir: tempo entre aldeões novos, sobra ou falta de mana e FPS.
- **B) Zero aldeões:** só recursos, água, margem, veio e o Cristal-mãe. O Arthur forma o primeiro aldeão à mão e monta tudo com a protagonista.

Para cada teste, o JOGO abre o Godot com a cena pelo godot-ai, e o Diretor avisa o Arthur que está pronto para jogar.

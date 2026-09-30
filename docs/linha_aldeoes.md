# LINHA 2: FORMAR ALDEÕES — especificação (ordem do Arthur, 30/09/2026)

Cópia fiel de `~/Projetos/cidadela-diretor/especificacoes/linha_aldeoes.md` (Diretor). Números iniciais, todos em
`data/`. Continua a linha da energia (`docs/linha_energia.md`).

## O processo aprovado

- A casca de barro é o corpo.
- O fragmento puro vira o cristal do peito.
- A mana é o sopro.

## Itens novos

- argila: pesado;
- casca: pesado.

Seguem as mesmas regras de peso da linha da energia: pesado só nas costas, nunca em esteira nem em mariposa.

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
- Recebe a casca à mão ou por carregador (pesado) e o puro por mariposa ou à mão.
- Com a rede fraca, forma mais devagar, pela mesma fração das outras máquinas.
- O aldeão nasce LIVRE ao lado do cristal e vai sozinho para o posto vazio mais perto (comportamento que já existe).

## Fluxo

- Barreiro → argila nas costas → Oleiro.
- Poço → mariposa → esteira → mariposa → Oleiro. O jarro agora é disputado entre Purificador e Oleiro.
- Oleiro → casca nas costas → Cristal-mãe.
- Purificador → mariposa → esteira → mariposa → Cristal-mãe. O puro agora é disputado entre Relicário e Cristal-mãe.

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
- O aldeão nasce livre e ocupa um posto vazio.
- Argila e casca são recusadas por esteira e por mariposa.
- Moldar à mão exige água perto.

## Testes com o Arthur (substituem os anteriores)

- **A) Mínimo de aldeões:** as duas linhas montadas, 2 Relicários, e os aldeões mínimos para tudo andar (operadores da mina, do poço, do purificador, do barreiro e do oleiro; carregadores para os pesados). Dizer quantos foram. Medir: tempo entre aldeões novos, sobra ou falta de mana e FPS.
- **B) Zero aldeões:** só recursos, água, margem, veio e o Cristal-mãe. O Arthur forma o primeiro aldeão à mão e monta tudo com a protagonista.

Para cada teste, o JOGO abre o Godot com a cena pelo godot-ai, e o Diretor avisa o Arthur que está pronto para jogar.

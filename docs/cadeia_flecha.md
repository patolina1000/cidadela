# Cadeia da flecha de ferro (era do torque)

Primeira linha complexa do jogo, pedida pelo Arthur em 30/09/2026. Inteira e jogável, sem animação de personagem nem
arte nova (formas simples, como os provisórios), mas com feedback visual claro. Todos os números ficam em `data/`.

**Regra do jogo:** o produto (flecha) é necessário o jogo inteiro; o que muda de era em era é o processo
(torque → vapor → mana). Esta é a era do **torque**: força de gente girando manivela e de roda d'água.

## A linha

```
 floresta ─(lenhador)→ baú de toras ─(carregador)→ Serraria ──haste──→┐
                                    └(carregador)→ Carvoaria ─carvão─→ Fundição ─lingote→ Bigorna ─ponta→ Mesa de ──flecha→ Arsenal
 veio ─(mineiro)→ baú de minério ──(carregador)──────────────────────→ Fundição            emplumar
                                                     Galinheiro ──pena──────────────────────→┘
 rio ── Roda d'água ══ eixo ══ fole da Fundição e manivelas de esteira
```

| Máquina | Receita | Tempo | Postos | Observação |
| --- | --- | --- | --- | --- |
| Serraria (existe) | 1 tora → 4 hastes | 8 s | 2, acoplados (serra de dois homens) | só anda com os 2 |
| Carvoaria (nova) | 10 toras → 20 carvões | 120 s | 0 | queima sozinha |
| Fundição (existe) | 1 minério + 1 carvão → 1 lingote | 15 s | 1 (fundidor) | com eixo girando: fole sozinho, +50% de velocidade |
| Bigorna (nova) | 1 lingote → 3 pontas | 15 s | 1 (ferreiro) | |
| Galinheiro (novo) | nada → 1 pena | 10 s | 1 (cuidador) | sem cuidador, para |
| Mesa de emplumar (nova) | 1 haste + 1 ponta + 2 penas → 2 flechas | 10 s | 1 | |
| Arsenal (novo) | guarda flechas | | | depósito (como o baú) |
| Forja da espada (existe) | 2 lingotes + 1 haste → 1 espada | 5 s | 0 | continua; a haste que sobra pode ir para ela |

## Regras

1. **Bruto x processado.** Tora (madeira), pedra e minério de ferro são **brutos** (`"raw": true` em `data/items.json`):
   não entram em esteira. Andam só nas costas dos carregadores ou do Castelão. O que sai da primeira etapa (serraria,
   carvoaria, fundição) cabe na esteira. Cabana que tem um baú à frente continua soltando o bruto nele.
2. **Postos** (`"posts"` em `data/buildings.json`, com o nome do ofício e a ferramenta). Ao construir, o aldeão livre mais
   perto ocupa cada posto (como nas cabanas). O posto só conta quando o aldeão **chegou** e está encostado na máquina.
   Posto vazio = máquina parada (a serraria precisa dos dois). Desmontar libera os aldeões.
3. **Carregadores** (escolha: o jeito mais simples). Uma construção nova, o **Posto de Carregadores**, com N vagas e um
   raio (`data/buildings.json`). Cada carregador repete: acha, dentro do raio do posto, uma máquina que ainda aceita um
   item bruto da receita dela e uma fonte que tenha esse item (baú ou cabana), busca até a carga dele e entrega. Sobra na
   mão fica para a próxima máquina que aceitar. A cabana continua como está (o lenhador e o mineiro coletam e guardam).
4. **Torque** (`"torque"` em `data/buildings.json`). A **Roda d'água** só se constrói em célula de **água** (terreno novo `water`, que
   bloqueia a passagem e as outras construções). O **Eixo** é uma construção em linha, baixa e não sólida (dá para passar
   por cima, como na esteira), que liga a rotação às 4 vizinhas. Rede = roda, eixos e consumidores ligados
   por vizinhança (grafo com somas, sem simular peça por peça: lição do Create). Cada rede soma a força das rodas e a
   demanda dos consumidores (fole da fundição e manivelas ligadas). Força ≥ demanda: a rede inteira gira; menos: a rede
   inteira para (sobrecarga, como no Create). A rede é recalculada só quando uma construção entra ou sai.
5. **Esteiras movidas a torque.** Uma **linha** de esteira é o conjunto de esteiras ligadas pelo fluxo (uma apontando para
   a outra). Cada linha precisa de **Manivela**: construção nova, com 1 posto, que aponta para uma esteira (a frente dela,
   R gira). Manivela ativa = aldeão no posto **ou** eixo girando ligado a ela. Cada manivela ativa move até 12 células de
   esteira (`crankCells` em `data/buildings.json`); a linha anda se a soma das manivelas ativas dela cobre o tamanho da linha.
   Linha sem manivela ativa (ou comprida demais) **para**: os itens ficam onde estão.
   `"powered": true` na esteira liga a regra (os testes antigos, com esteira própria sem o campo, continuam livres); o
   palco da Biografia é vitrine: `"freeMachines": true` no mapa (máquinas sem posto e esteiras sem manivela).
6. **Estados da máquina** (simulação, lidos pela cena): trabalhando; falta insumo (qual item); posto vazio (quantos de
   quantos); saída cheia; sem torque (manivela, eixo e roda).

## Feedback visual (sem animação de personagem)

- **Placa sobre cada máquina:** cor + ícone do estado. Verde = trabalhando; âmbar + ícone do item = falta insumo;
  cinza + silhueta "1/2" = posto vazio; vermelho = saída cheia; azul apagado = sem torque.
- **Barra de progresso** da receita sobre a máquina.
- **Aldeão no posto:** ícone da ferramenta sobre a cabeça (serra, martelo, fole, pena, manivela, cesto).
- **Eixo, roda e manivela** giram quando têm força; parados, ficam imóveis e escuros.
- **Esteira andando x parada:** as marcas da esteira deslizam quando anda; parada, ficam escuras e os itens param.
- **Alt:** placas de todas as máquinas e ícones dos aldeões (modo informação do GDD). **Mouse em cima:** receita,
  postos (quem está e quem falta), velocidade (com ou sem fole), o que falta, torque da rede (força/demanda) e tamanho
  da linha de esteira contra o que as manivelas movem.

## Barra de construção

Passa de 9 itens (17). Solução simples: **duas páginas de 9**, na ordem de `data/buildings.json`; **Tab** troca de página
(e um botão na ponta da barra mostra "1/2"); as teclas 1–9 escolhem dentro da página aberta. Página 1: logística e
fontes (esteira, manivela, eixo, roda d'água, baú, arsenal, posto de carregadores, cabanas do lenhador e do mineiro).
Página 2: cabana do pedreiro e as máquinas.

## Cena de teste

`scenes/tests/LinhaFlecha.tscn` com `data/maps/linha_flecha.json`: um rio, a linha inteira montada, árvores e veios
perto das cabanas e ~14 aldeões (2 cabanas + 2 carregadores + 2 serradores + fundidor + ferreiro + cuidador +
emplumador + 2 manivelas com gente; as outras linhas giram pelo eixo da roda). Tudo também é construível pela barra.

## Passos (um commit cada, com build, testes, diário e push)

0. Este documento.
1. Itens e bruto: itens novos (carvão, ponta, pena, flecha), `raw`, esteira recusa bruto.
2. Máquinas e receitas: carvoaria, bigorna, galinheiro, mesa de emplumar, arsenal; números novos; receita sem entrada.
3. Postos: `posts` nas máquinas, aldeão ocupa, máquina só anda com todos, desmontar libera.
4. Carregadores: Posto de Carregadores e o ciclo buscar → entregar.
5. Torque e eixo: água, roda d'água, eixo, rede com somas, fole da fundição.
6. Manivela e esteiras: linhas, manivela com posto ou eixo, 12 células.
7. Feedback visual: placas, barras, ícones de ferramenta, giros, esteira parada, Alt, mouse, barra em 2 páginas.
8. Cena de teste, prints e FPS em 3024×1890 fora do editor.

## Decisões tomadas sem estar na especificação (as mais simples)

- A tora continua sendo o item `wood` (nome na tela passa a "Tora"); o minério continua `iron` (nome "Minério de ferro").
- Todos os postos de uma máquina precisam estar ocupados (vale para a serraria e para as de 1 posto).
- O Castelão também pode abastecer qualquer máquina à mão, inclusive com bruto (já funcionava).
- Rede de torque sobrecarregada para inteira (não reparte força).
- Eixo liga nas 4 direções (não tem orientação); roda, eixo, fundição e manivela são os nós da rede.
- A manivela move a linha da esteira à frente dela; a mesma linha pode ter várias manivelas somando células.

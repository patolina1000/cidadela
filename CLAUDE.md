# Cidadela — regras do projeto para agentes de IA

> Este arquivo existe em duas cópias idênticas: `CLAUDE.md` (Claude Code) e `AGENTS.md` (Codex).
> Ao mudar um, copie para o outro no mesmo commit.

Jogo de automação medieval com defesa de hordas (estilo Factorio + tower defense).
O design completo está em `docs/GDD.md`. Leia as seções relevantes antes de cada tarefa;
as mais importantes para código são a 10 (MVP), a 12 (câmera e andares), a 13 (engine), a 17 (arte) e a 20 (personagem principal, o Castelão).

**Como o projeto funciona:** o humano dirige e revisa; a IA implementa. Não invente design:
se algo não está no GDD nem no pedido, pergunte ou escolha o mais simples e diga o que escolheu.

## Stack

- **Godot 4.7 .NET (4.7.2) com C#.** Todo o código do jogo é C#. GDScript só existe no addon `addons/godot_ai/`, que não deve ser editado.
- .NET SDK 10 instalado; o projeto compila para `net8.0` (definido pelo Godot.NET.Sdk).
- O editor Godot fica aberto e conectado pelo MCP **godot-ai**: use-o para abrir cenas, rodar o jogo, ler logs e tirar screenshots.

## Regra nº 1: simulação separada dos gráficos

- A simulação (mundo, itens, receitas, esteiras, aldeões, inimigos) roda em **ticks fixos de 20 por segundo** (50 ms), independente do FPS.
- O código de simulação fica em `src/Simulation/` e é **C# puro: nunca `using Godot`**. Isso o mantém testável sem abrir o jogo e rápido para milhares de itens.
- Os nós do Godot (`src/View/`) **só leem** o estado da simulação e desenham. Eles podem interpolar entre ticks para suavizar o movimento, mas nunca alteram o estado diretamente.
- A entrada do jogador que muda o mundo (construir, remover etc.) vira um comando entregue à simulação, que o aplica no próximo tick.

## Dados em JSON

- Receitas, máquinas, inimigos, mapas e balanceamento ficam em arquivos JSON dentro de `data/`, nunca fixos no código.
- Números de design (velocidades, custos, tempos) vêm dos JSON; o código só tem constantes técnicas (ex.: taxa de ticks).

## Fluxo de trabalho obrigatório

1. **Tarefas pequenas.** Uma tarefa = uma coisa bem descrita ("esteira que move itens entre dois pontos", não "sistema de automação"). Se o pedido for grande, proponha a divisão antes de começar.
2. **Rode `dotnet build` depois de cada mudança em C#** e corrija todos os erros (e avisos novos) antes de seguir. O godot-ai não compila C# nem mostra erros de compilação.
3. Depois de compilar, rode o jogo pelo MCP e confira os logs; tire screenshot quando a mudança for visual.
4. **Um commit por tarefa concluída**, com mensagem em português descrevendo o que mudou.
5. **Registre cada tarefa em `docs/DIARIO.md`:** o que foi pedido, o que foi feito, o que deu errado, correções manuais e tempo gasto.
6. Não use `sudo`.

## Estrutura de pastas

```
src/Simulation/   C# puro: estado e regras do jogo (sem Godot)
src/View/         nós Godot que desenham o estado e leem a entrada
scenes/           cenas .tscn
data/             JSON de receitas, mapas, inimigos, balanceamento
docs/             GDD, diário do experimento
addons/           plugins de terceiros (não editar)
```

## Estilo de código

- Nomes de código (classes, métodos, variáveis, arquivos .cs) em **inglês**; textos do jogo, comentários de design e documentação em **português**.
- Namespaces: `Cidadela.Simulation` e `Cidadela.View`.
- Uma classe pública por arquivo, com o mesmo nome do arquivo. Classes de nó Godot são `partial`.
- `PascalCase` para tipos e membros públicos, `_camelCase` para campos privados.
- Comentários curtos, só onde o "porquê" não é óbvio.

## Arte (enquanto for protótipo)

- Formas geométricas simples: cubos = recursos, cilindros = máquinas, cápsulas = aldeões.
- Cores chapadas da paleta da seção 17 do GDD. Nada de arte final ainda.

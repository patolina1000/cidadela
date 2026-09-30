"""Gera assets/cenario/cenario.json (manifesto de entrega do cenário) a partir de verificacao.json.

Rode depois de verificar.py. Os números (altura, triângulos, caixa) vêm da verificação dos GLBs; os pesos, as bordas
e as sombras são as decisões registradas aqui. Formato no estilo dos JSON do jogo (data/*.json): comentários //,
chaves em inglês; a chave de cada família é o id do recurso em data/resources.json.

Uso: uv run --project tools/arte tools/arte/cenario/manifesto.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

FAMILIAS = [
    # (id do recurso, família, prefixo dos arquivos, pesos, materiais com borda fria, projeta sombra, comentário)
    # Copa sem borda fria: o Arthur viu no jogo e não gostou do brilho em volta das folhas (tarefa 8, 29/09/2026).
    ("wood", "árvore", "arvore/arvore_", [0.3, 0.3, 0.1, 0.3], [], True,
     "1 gota, 2 dupla, 3 tufos (líquen roxo, destaque raro), 4 alta. Copa a partir de ≥ 1,0 m (fora do alcance)."),
    ("stone", "pedra", "pedra/pedra_", [0.25] * 4, ["pedra", "musgo"], True,
     "1 bloco com tampa de musgo, 2 dupla, 3 pilha em espiral, 4 laje. Pedra escurecida #57535F."),
    ("iron", "veio de ferro", "veio/veio_", [0.25] * 4, ["pedra", "minerio"], True,
     "1 leque, 2 cruzado, 3 coroa, 4 torre. Rocha lama #2E2931, lascas #1E2A3A."),
]
ESGOTADO = {
    "wood": ("arvore/toco_", "sameIndex", [], False,
             "Toco da própria árvore (mesmo índice, mesmo giro e escala da instância)."),
    "iron": ("veio/mancha_", [0.5, 0.5], ["pedra", "minerio"], False, "1 placa com lascas, 2 só lascas."),
}


def variant(v, weight, rim, shadow):
    sobra = max(0.0, v["raio_m"] - 0.5)  # o pior giro: o jogo sorteia o giro em Y por instância
    return (f'{{ "file": "{v["arquivo"]}", "weight": {weight}, "height": {v["altura_m"]}, "cells": 1, '
            f'"overhang": {round(sobra, 2)}, "triangles": {v["triangulos"]}, '
            f'"coldRim": {json.dumps(rim)}, "castsShadow": {str(shadow).lower()} }}')


def main():
    ver = {Path(r["arquivo"]).name: r for r in
           json.loads((ROOT / "assets/cenario/verificacao.json").read_text())["arquivos"]}
    out = [
        "{",
        "  // Manifesto do cenário (objetos do mundo), gerado por tools/arte/cenario/manifesto.py. RASCUNHO até o manda do",
        "  // Arthur; regras em assets/cenario/cenario_contrato_rascunho.md. A chave é o id do recurso (data/resources.json).",
        "  // weight: peso do sorteio da variação por célula (soma 1). height: metros. cells: pegada em células (1 = a célula",
        "  // do nó). overhang: quanto a malha pode passar da borda da célula, em metros, no pior giro (a copa inclinada). triangles: LOD0; o LOD",
        "  // automático do Godot basta (verificacao.json). coldRim: materiais que levam a borda de luz fria do toon (opção b);",
        "  // a copa das árvores ficou SEM borda (o Arthur não gostou no jogo, 29/09/2026); pedra e veio seguem com ela por",
        "  // enquanto. castsShadow: só as massas grandes projetam sombra (GDD, seção 13).",
        "  // O jogo sorteia também o giro em Y (0–360°) e a escala (0,9–1,1) por instância.",
        "  // depleted: o que fica quando o recurso esgota. OPCIONAL: a decisão é do Arthur; sem ela, o nó some (como hoje).",
    ]
    for n, (res, fam, pref, pesos, rim, shadow, nota) in enumerate(FAMILIAS):
        out.append(f'  "{res}": {{')
        out.append(f"    // {fam}: {nota}")
        out.append('    "variants": [')
        rows = [variant(ver[f"{Path(pref).name}{i}.glb"], pesos[i - 1], rim, shadow) for i in range(1, 5)]
        out += [f"      {r}," for r in rows[:-1]] + [f"      {rows[-1]}"]
        if res in ESGOTADO:
            epref, epesos, erim, eshadow, enota = ESGOTADO[res]
            files = sorted(k for k in ver if k.startswith(Path(epref).name))
            out.append("    ],")
            out.append(f"    // Esgotado (opcional): {enota}")
            out.append('    "depleted": {')
            if epesos == "sameIndex":
                out.append('      "pick": "sameIndex",')
                erows = [variant(ver[f], "null", erim, eshadow) for f in files]
            else:
                out.append('      "pick": "weight",')
                erows = [variant(ver[f], epesos[i], erim, eshadow) for i, f in enumerate(files)]
            out.append('      "variants": [')
            out += [f"        {r}," for r in erows[:-1]] + [f"        {erows[-1]}"]
            out.append("      ]")
            out.append("    }")
        else:
            out.append("    ]")
            out.append("    // Esgotado: some (nenhuma opção pedida para a pedra).")
        out.append("  }" + ("," if n < len(FAMILIAS) - 1 else ""))
    out.append("}")
    text = "\n".join(out) + "\n"
    (ROOT / "assets/cenario/cenario.json").write_text(text)
    print(text)


if __name__ == "__main__":
    main()

"""Veio de ferro piloto do cenário: 4 variações da mesma família, por script, semente por variação.

Família: rocha baixa, escura e macia (lama) com lascas de minério grandes e facetadas (azul meia-noite, a cor do ferro no
jogo) saindo tortas para os lados, gordas o bastante para aparecer no zoom 0,4 (tarefa 4); de cima, as lascas são o que distingue o veio da pedra. 0,30–0,45 m,
≤ 200 triângulos, material chapado sem textura. Metros, frente +Z no GLB, pivô no centro da base.

Uso, na raiz da worktree:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/veio.py
Saída: assets/cenario/veio/veio_1..4.glb e veio_relatorio.json.
"""

import math
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cenario_lib import PALETA, ROOT, block, export, join, material, write_report  # noqa: E402

OUT = ROOT / "assets/cenario/veio"
MAX_TRIS = 200

# Rochas: semi-eixos, centro, inclinação, giro. Lascas: semi-eixos da base, centro, inclinação (para fora),
# giro (para que lado tomba) e quanto a ponta se alonga.
VARIACOES = [
    {
        "nome": "leque", "semente": 201,
        "rochas": [{"size": (0.34, 0.28, 0.20), "center": (0, 0, 0.09), "tilt": 6, "yaw": 0}],
        "lascas": [
            {"size": (0.14, 0.13, 0.14), "center": (0.02, 0.0, 0.21), "tilt": 8, "yaw": 0, "ponta": 0.63},
            {"size": (0.13, 0.10, 0.13), "center": (0.13, 0.04, 0.18), "tilt": 38, "yaw": 20, "ponta": 0.56},
            {"size": (0.13, 0.10, 0.11), "center": (-0.10, 0.07, 0.17), "tilt": 34, "yaw": 150, "ponta": 0.56},
        ],
    },
    {
        "nome": "cruzado", "semente": 211,
        "rochas": [
            {"size": (0.26, 0.22, 0.18), "center": (-0.10, 0, 0.08), "tilt": 5, "yaw": 0},
            {"size": (0.20, 0.17, 0.15), "center": (0.16, 0.06, 0.07), "tilt": -8, "yaw": 50},
        ],
        "lascas": [
            {"size": (0.17, 0.14, 0.16), "center": (-0.06, 0.0, 0.20), "tilt": 30, "yaw": 10, "ponta": 0.70},
            {"size": (0.14, 0.13, 0.15), "center": (0.10, 0.03, 0.18), "tilt": 32, "yaw": 190, "ponta": 0.70},
        ],
    },
    {
        # Coroa em espiral: lascas pequenas em volta, cada uma tombando um pouco mais que a anterior.
        "nome": "coroa", "semente": 223,
        "rochas": [{"size": (0.36, 0.32, 0.14), "center": (0, 0, 0.06), "tilt": 3, "yaw": 0}],
        "lascas": [
            {"size": (0.13, 0.10, 0.10), "center": (0.10, 0.02, 0.17), "tilt": 15, "yaw": 0, "ponta": 0.56},
            {"size": (0.13, 0.10, 0.11), "center": (-0.02, 0.11, 0.17), "tilt": 25, "yaw": 90, "ponta": 0.56},
            {"size": (0.13, 0.10, 0.13), "center": (-0.11, -0.02, 0.17), "tilt": 35, "yaw": 180, "ponta": 0.63},
            {"size": (0.13, 0.10, 0.14), "center": (0.01, -0.11, 0.17), "tilt": 45, "yaw": 270, "ponta": 0.63},
        ],
    },
    {
        "nome": "torre", "semente": 239,
        "rochas": [{"size": (0.24, 0.22, 0.18), "center": (-0.08, 0.02, 0.08), "tilt": 8, "yaw": 20}],
        "lascas": [
            {"size": (0.18, 0.17, 0.20), "center": (0.06, 0.0, 0.15), "tilt": 14, "yaw": 0, "ponta": 0.49},
            {"size": (0.13, 0.10, 0.13), "center": (0.16, 0.08, 0.10), "tilt": 40, "yaw": 40, "ponta": 0.56},
        ],
    },
]


def build(spec, index):
    rng = random.Random(spec["semente"])
    rocha = material("pedra", PALETA["lama"])
    minerio = material("minerio", PALETA["meia_noite"])
    parts = []
    for i, r in enumerate(spec["rochas"]):
        o = block(rng, r["size"], r["center"], 20, r["tilt"], r["yaw"], 20, name=f"rocha_{i}")
        o.data.materials.append(rocha)
        parts.append(o)
    for i, l in enumerate(spec["lascas"]):
        o = block(rng, l["size"], l["center"], 9, l["tilt"], l["yaw"], 30, jitter=0.1, point_z=l["ponta"],
                  name=f"lasca_{i}", smooth=False)
        o.data.materials.append(minerio)
        parts.append(o)
    obj = join(parts, f"veio_{index}")
    obj.rotation_euler = (0.0, 0.0, math.radians(rng.uniform(0, 360)))  # lado sorteado pela semente
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return obj


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, spec in enumerate(VARIACOES, start=1):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = build(spec, index)
        rows.append(export(obj, OUT / f"veio_{index}.glb", MAX_TRIS, {
            "nome": spec["nome"], "semente": spec["semente"],
            "cores": {"pedra": PALETA["lama"], "minerio": PALETA["meia_noite"]}}))
    write_report(OUT / "veio_relatorio.json", "tools/arte/cenario/veio.py", rows)


main()

"""Mancha do veio esgotado (opção de estado esgotado, para o Arthur decidir): 2 opções, ≤ 40 triângulos.

1 placa: laje baixa e macia de rocha (lama) com 2 lascas de minério quebradas deitadas por cima.
2 lascas: só 3 lascas quebradas deitadas no chão, sem rocha.
Mesmas cores do veio vivo (#2E2931 e #1E2A3A), material chapado, metros, frente +Z, pivô no centro da base.

Uso, na raiz da worktree:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/mancha.py
Saída: assets/cenario/veio/mancha_1..2.glb e mancha_relatorio.json.
"""

import math
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cenario_lib import PALETA, ROOT, block, export, join, material, write_report  # noqa: E402

OUT = ROOT / "assets/cenario/veio"
MAX_TRIS = 40

# Lasca quebrada: bloco pontudo deitado (inclinação ~80°), curto.
VARIACOES = [
    {
        "nome": "placa", "semente": 301,
        "placa": {"size": (0.30, 0.25, 0.04), "center": (0, 0, 0.0), "pontos": 10},
        "lascas": [
            {"size": (0.08, 0.06, 0.07), "center": (0.06, 0.02, 0.05), "tilt": 80, "yaw": 20},
            {"size": (0.07, 0.05, 0.06), "center": (-0.10, -0.05, 0.045), "tilt": 76, "yaw": 200},
        ],
    },
    {
        "nome": "lascas", "semente": 311,
        "placa": None,
        "lascas": [
            {"size": (0.08, 0.06, 0.08), "center": (0.07, 0.03, 0.03), "tilt": 82, "yaw": 10},
            {"size": (0.07, 0.05, 0.07), "center": (-0.08, 0.06, 0.03), "tilt": 78, "yaw": 130},
            {"size": (0.07, 0.05, 0.06), "center": (0.0, -0.10, 0.03), "tilt": 84, "yaw": 250},
        ],
    },
]


def build(spec, index):
    rng = random.Random(spec["semente"])
    parts = []
    if spec["placa"]:
        p = spec["placa"]
        o = block(rng, p["size"], p["center"], p["pontos"], 4, 0, 10, name="placa")
        o.data.materials.append(material("pedra", PALETA["lama"]))
        parts.append(o)
    minerio = material("minerio", PALETA["meia_noite"])
    for i, l in enumerate(spec["lascas"]):
        o = block(rng, l["size"], l["center"], 6, l["tilt"], l["yaw"], 0, jitter=0.1, point_z=0.4,
                  name=f"lasca_{i}", smooth=False)
        o.data.materials.append(minerio)
        parts.append(o)
    obj = join(parts, f"mancha_{index}")
    obj.rotation_euler = (0.0, 0.0, math.radians(rng.uniform(0, 360)))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return obj


def main():
    rows = []
    for index, spec in enumerate(VARIACOES, start=1):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = build(spec, index)
        rows.append(export(obj, OUT / f"mancha_{index}.glb", MAX_TRIS, {
            "nome": spec["nome"], "semente": spec["semente"],
            "cores": {"pedra": PALETA["lama"], "minerio": PALETA["meia_noite"]}}))
    write_report(OUT / "mancha_relatorio.json", "tools/arte/cenario/mancha.py", rows)


main()

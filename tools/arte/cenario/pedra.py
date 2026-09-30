"""Pedra piloto do cenário (recurso pedra): 4 variações da mesma família, por script, semente por variação.

Família: seixos grandes e macios de pedra fria, tortos (inclinados, camadas de cima giradas: espiral sutil),
assentados no chão; uma variação com tampa de musgo. 0,35–0,55 m, ≤ 200 triângulos, material chapado sem textura.
Metros, frente +Z no GLB, pivô no centro da base. Proposta em assets/cenario/PROPOSTA.md.

Uso, na raiz da worktree:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/pedra.py
Saída: assets/cenario/pedra/pedra_1..4.glb e pedra_relatorio.json.
"""

import math
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cenario_lib import PALETA, ROOT, block, export, join, material, write_report  # noqa: E402

OUT = ROOT / "assets/cenario/pedra"
MAX_TRIS = 200

# Cada bloco: semi-eixos (m), centro, inclinação, giro, torção das camadas (graus), pontos da casca, papel.
VARIACOES = [
    {
        "nome": "bloco", "semente": 101,
        "blocos": [
            {"size": (0.34, 0.27, 0.25), "center": (0, 0, 0.19), "tilt": 14, "yaw": 20, "twist": 35, "pontos": 24},
            {"size": (0.20, 0.17, 0.05), "center": (-0.05, 0.02, 0.43), "tilt": 14, "yaw": 20, "twist": 0,
             "pontos": 20, "papel": "musgo"},
        ],
    },
    {
        "nome": "dupla", "semente": 113,
        "blocos": [
            {"size": (0.30, 0.25, 0.21), "center": (-0.09, 0, 0.16), "tilt": 8, "yaw": 0, "twist": 25, "pontos": 23},
            {"size": (0.16, 0.14, 0.22), "center": (0.22, 0.06, 0.19), "tilt": -24, "yaw": 40, "twist": 30,
             "pontos": 21},
        ],
    },
    {
        # Pilha torta em espiral: cada pedra menor e girada em relação à de baixo.
        "nome": "pilha", "semente": 127,
        "blocos": [
            {"size": (0.30, 0.26, 0.14), "center": (0, 0, 0.11), "tilt": 5, "yaw": 0, "twist": 20, "pontos": 23},
            {"size": (0.22, 0.18, 0.11), "center": (0.05, 0.02, 0.30), "tilt": -10, "yaw": 50, "twist": 20,
             "pontos": 21},
            {"size": (0.14, 0.12, 0.10), "center": (0.0, 0.06, 0.45), "tilt": 14, "yaw": 100, "twist": 20,
             "pontos": 20},
        ],
    },
    {
        "nome": "laje", "semente": 139,
        "blocos": [
            {"size": (0.34, 0.24, 0.12), "center": (0.05, 0, 0.21), "tilt": -30, "yaw": 10, "twist": 15,
             "pontos": 22},
            {"size": (0.20, 0.18, 0.14), "center": (-0.18, 0.05, 0.10), "tilt": 10, "yaw": 60, "twist": 25,
             "pontos": 21},
        ],
    },
]


def build(spec, index):
    rng = random.Random(spec["semente"])
    mats = {"pedra": material("pedra", PALETA["pedra_fria"]), "musgo": material("musgo", PALETA["musgo"])}
    parts = []
    for i, b in enumerate(spec["blocos"]):
        o = block(rng, b["size"], b["center"], b["pontos"], b["tilt"], b["yaw"], b["twist"], name=f"bloco_{i}")
        o.data.materials.append(mats[b.get("papel", "pedra")])
        parts.append(o)
    obj = join(parts, f"pedra_{index}")
    obj.rotation_euler = (0.0, 0.0, math.radians(rng.uniform(0, 360)))  # lado sorteado pela semente
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return obj


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, spec in enumerate(VARIACOES, start=1):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = build(spec, index)
        rows.append(export(obj, OUT / f"pedra_{index}.glb", MAX_TRIS, {
            "nome": spec["nome"], "semente": spec["semente"],
            "cores": {m.name: PALETA["pedra_fria"] if m.name == "pedra" else PALETA["musgo"]
                      for m in obj.data.materials}}))
    write_report(OUT / "pedra_relatorio.json", "tools/arte/cenario/pedra.py", rows)


main()

"""Estudo de proporção, passo 1: cabeça ÷ altura da v1 e do aldeão v2, pelo esqueleto (Blender headless).

Topo = ponto mais alto da figura (com cabelo); queixo = vértice mais baixo do rosto: osso de maior peso Head
(ou head_end/headfront), na metade da frente da cabeça e a até 12% da largura da cabeça da linha do meio (o
cabelo da v1 cai pelos lados e pelas costas, não na frente do queixo); pés = ponto mais baixo.
Também devolve as linhas em pixels nas referências v1_frente.png e v1_lado.png (referencia_v1.py: figura com
1536 px num quadro de 2048, centrada na caixa), para conferir a olho.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/medir_cabeca_v1.py -- <saida.json>
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import ROOT, V1, load_rest, mesh_objects, mesh_points  # noqa: E402

ALDEAO = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
HEAD_BONES = ("Head", "head_end", "headfront")
BODY_PX, BODY_FRAME = 1536, 2048  # referencia_v1.py


def head_vertices(objects) -> np.ndarray:
    out = []
    for obj in mesh_objects(objects):
        if obj.name in ("Olhos", "Boca"):  # retalhos do rosto do aldeão
            continue
        names = [g.name for g in obj.vertex_groups]
        for v in obj.data.vertices:
            if v.groups and names[max(v.groups, key=lambda g: g.weight).group] in HEAD_BONES:
                p = obj.matrix_world @ v.co
                out.append((p.x, p.y, p.z))
    return np.array(out)


def measure(objects) -> dict:
    pts = mesh_points(objects)
    low, high = pts.min(axis=0), pts.max(axis=0)
    head = head_vertices(objects)
    hx0, hx1 = head[:, 0].min(), head[:, 0].max()
    cx, cy = (hx0 + hx1) / 2, (head[:, 1].min() + head[:, 1].max()) / 2
    # Frente = -Y do Blender (+Z do glTF).
    face = head[(head[:, 1] < cy) & (np.abs(head[:, 0] - cx) < 0.12 * (hx1 - hx0))]
    chin = float(face[:, 2].min())
    top, feet = float(high[2]), float(low[2])
    return {"altura_m": round(top - feet, 4), "topo_z": top, "queixo_z": chin, "pes_z": feet,
            "cabeca_m": round(top - chin, 4), "cabeca_sobre_altura": round((top - chin) / (top - feet), 3),
            "centro_z": float((low[2] + high[2]) / 2)}


def main() -> None:
    out = Path(sys.argv[sys.argv.index("--") + 1:][0])
    result = {}
    for name, path in (("v1", V1), ("aldeao", ALDEAO)):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        result[name] = measure(load_rest(path))
    v1 = result["v1"]
    # Linhas nas referências: z -> linha da imagem (ortográfica, figura com BODY_PX de altura, centrada).
    k = BODY_PX / v1["altura_m"]
    row = lambda z: round(BODY_FRAME / 2 - (z - v1["centro_z"]) * k, 1)  # noqa: E731
    v1["referencia_linhas_px"] = {"topo": row(v1["topo_z"]), "queixo": row(v1["queixo_z"]), "pes": row(v1["pes_z"])}
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("CABECA " + json.dumps(result))


main()

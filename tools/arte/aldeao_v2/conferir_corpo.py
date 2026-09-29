"""Confere dois GLBs do corpo do aldeão v2 (ex.: aprovado × normalizado, ou normalizado × refeito pelo processo),
em Blender headless. Mede:
1. nomes: ossos, clipes, materiais, malhas; escala do nó Armature no glTF;
2. maior distância entre vértices correspondentes (corpo, Olhos, Boca; correspondência pela posição em repouso)
   nos quadros de 0, 25, 50 e 75% de idle-loop e run-loop, em mm;
3. folga dos retalhos Olhos e Boca à pele (mm, com sinal) nos 6 quadros por clipe que o colocar_retalhos.py confere;
4. cabelos 1 a 5 presos como o jogo prende (encaixe no osso Head compensando o repouso global do osso e a
   transformação do esqueleto): maior diferença de vértice entre os dois arquivos nos mesmos quadros do item 2, e a
   menor distância do cabelo ao corpo em repouso.
Também importado como módulo (normalizar_corpo.py).

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/conferir_corpo.py -- <a.glb> <b.glb> <saida.json>
"""

import json
import struct
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import kdtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpo_lib import ROOT, import_glb  # noqa: E402
from rig_lib import clearance, evaluated_points, play, signed_distances  # noqa: E402

CLIPS = ("idle-loop", "run-loop")
FRACTIONS = (0.0, 0.25, 0.5, 0.75)
CHECK_POINTS = 6  # colocar_retalhos.py
HAIRS = [ROOT / f"assets/modelos/aldeao_v2/cabelos/cabelo_{n}.glb" for n in range(1, 6)]
HEAD = "Head"


def gltf_armature(path: Path) -> dict:
    b = path.read_bytes()
    n = struct.unpack("<I", b[12:16])[0]
    node = next(x for x in json.loads(b[20:20 + n])["nodes"] if x.get("name") == "Armature")
    return {k: node.get(k) for k in ("scale", "translation", "rotation")}


def load(path: Path) -> dict:
    before = set(bpy.data.actions)
    objs = import_glb(path)
    arm = next(o for o in objs if o.type == "ARMATURE")
    meshes = {o.name.split(".")[0]: o for o in objs if o.type == "MESH"}
    actions = {a.name.split(".")[0]: a for a in bpy.data.actions if a not in before}
    return {"arm": arm, "meshes": meshes, "actions": actions,
            "materials": sorted({m.name.split(".")[0] for o in meshes.values() for m in o.data.materials}),
            "bones": [b.name for b in arm.data.bones]}


def set_frame(x, clip, frame):
    play(x["arm"], x["actions"][clip])
    bpy.context.scene.frame_set(frame)


def hair_matrix(x):
    """Encaixe do jogo: esqueleto × pose global do osso × repouso global⁻¹ × esqueleto⁻¹ (VillagerVisual.Socket)."""
    arm = x["arm"]
    return arm.matrix_world @ arm.pose.bones[HEAD].matrix @ arm.data.bones[HEAD].matrix_local.inverted() @ arm.matrix_world.inverted()


def compare(a_path: Path, b_path: Path) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    a, b = load(a_path), load(b_path)
    hairs = []
    for h in HAIRS:
        obj = next(o for o in import_glb(h) if o.type == "MESH")
        hairs.append((h.stem, np.array([(obj.matrix_world @ v.co)[:] for v in obj.data.vertices]), obj))
        obj.hide_render = True
    out = {"a": str(a_path), "b": str(b_path),
           "gltf_armature": {"a": gltf_armature(a_path), "b": gltf_armature(b_path)},
           "escala_objeto_armature": [a["arm"].scale[0], b["arm"].scale[0]],
           "nomes_iguais": {"ossos": a["bones"] == b["bones"], "clipes": sorted(a["actions"]) == sorted(b["actions"]),
                            "materiais": a["materials"] == b["materials"],
                            "malhas": sorted(a["meshes"]) == sorted(b["meshes"])},
           "nomes": {"clipes": sorted(b["actions"]), "materiais": b["materials"], "malhas": sorted(b["meshes"])}}

    for x in (a, b):
        x["arm"].data.pose_position = "REST"
    bpy.context.view_layer.update()
    names = sorted(set(a["meshes"]) & set(b["meshes"]))
    maps, rest_gap, rest_x = {}, 0.0, {}
    for n in names:
        pa, pb = evaluated_points(a["meshes"][n]), evaluated_points(b["meshes"][n])
        tree = kdtree.KDTree(len(pb))
        for i, p in enumerate(pb):
            tree.insert(p, i)
        tree.balance()
        found = [tree.find(p) for p in pa]
        maps[n] = np.array([f[1] for f in found])
        rest_x[n] = pa[:, 0]
        rest_gap = max(rest_gap, max(f[2] for f in found))
    out["vertices"] = {n: [len(a["meshes"][n].data.vertices), len(b["meshes"][n].data.vertices)] for n in names}
    out["repouso_max_mm"] = round(rest_gap * 1000, 5)
    body_b = b["meshes"]["aldeao_corpo"]
    out["cabelos_repouso_min_ate_corpo_mm"] = {name: round(min(signed_distances(body_b, [obj.matrix_world @ v.co for v in obj.data.vertices])), 2)
                                               for name, _, obj in hairs}
    for x in (a, b):
        x["arm"].data.pose_position = "POSE"

    verts, hair_rows, per_mesh = {}, {}, {}
    for clip in CLIPS:
        start, end = a["actions"][clip].frame_range
        for f in FRACTIONS:
            frame = int(round(start + f * (end - start)))
            set_frame(a, clip, frame)
            set_frame(b, clip, frame)
            per = {}
            for n in names:
                d = np.linalg.norm(evaluated_points(a["meshes"][n]) - evaluated_points(b["meshes"][n])[maps[n]], axis=1)
                per[n] = float(d.max())
                over = int((d > 1e-5).sum())
                per_mesh.setdefault(n, {"max_mm": 0.0, "vertices_acima_0_01_mm": 0, "coluna_x_mm": None})
                if per[n] * 1000 > per_mesh[n]["max_mm"]:
                    per_mesh[n]["max_mm"] = round(per[n] * 1000, 5)
                    per_mesh[n]["vertices_acima_0_01_mm"] = over
                    if over:  # onde ficam os que diferem, em x no repouso (a costura da simetria é x = 0)
                        xs = rest_x[n][d > 1e-5]
                        per_mesh[n]["coluna_x_mm"] = [round(float(xs.min()) * 1000, 2), round(float(xs.max()) * 1000, 2)]
            vmax = max(per.values())
            ha, hb = np.array(hair_matrix(a)), np.array(hair_matrix(b))
            hmax = 0.0
            for _, pts, _ in hairs:
                h4 = np.c_[pts, np.ones(len(pts))]
                hmax = max(hmax, float(np.linalg.norm((h4 @ ha.T - h4 @ hb.T)[:, :3], axis=1).max()))
            key = f"{clip}@{int(f * 100)}%"
            verts[key] = round(vmax * 1000, 5)
            hair_rows[key] = round(hmax * 1000, 5)
    out["vertices_max_mm_por_quadro"] = verts
    out["vertices_max_mm"] = max(verts.values())
    out["vertices_por_malha"] = per_mesh
    out["cabelos_max_mm_por_quadro"] = hair_rows
    out["cabelos_max_mm"] = max(hair_rows.values())

    gaps = {}
    for label, x in (("a", a), ("b", b)):
        rows = {}
        for clip in CLIPS:
            s0, s1 = (int(v) for v in x["actions"][clip].frame_range)
            for f in [s0 + (s1 - s0) * i // (CHECK_POINTS - 1) for i in range(CHECK_POINTS)]:
                set_frame(x, clip, f)
                rows[f"{clip}@{f}"] = {p: [round(v, 2) for v in clearance(x["meshes"]["aldeao_corpo"], x["meshes"][p])] for p in ("Olhos", "Boca")}
        gaps[label] = {"por_quadro": rows,
                       "min_mm": min(v[0] for r in rows.values() for v in r.values()),
                       "max_mm": max(v[1] for r in rows.values() for v in r.values())}
    out["folga_retalhos"] = gaps
    return out


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    report = compare(Path(args[0]), Path(args[1]))
    Path(args[2]).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("CONFERENCIA " + json.dumps({k: v for k, v in report.items() if not k.endswith("por_quadro") and k != "folga_retalhos"},
                                      ensure_ascii=False))
    print("FOLGA " + json.dumps({k: [v["min_mm"], v["max_mm"]] for k, v in report["folga_retalhos"].items()}))


if __name__ == "__main__":
    main()

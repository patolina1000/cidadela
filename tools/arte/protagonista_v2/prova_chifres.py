"""Prova dos chifres (piloto) da protagonista v2 (Blender headless).

- Bruto: o busto da Meshy com as ilhas de chifre coloridas (o par escolhido em roxo, a duplicata de trás em vermelho),
  frente, perfil e topo.
- Peça extraída (chifres.glb) sobre a cabeça do corpo final (protagonista_corpo.glb em repouso, com os retalhos no quadro
  padrão e o cristal): close de frente, perfil, 3/4 e costas; frente e 3/4 inteiras com o aldeão; câmera do jogo nos zooms
  0,4 / 1 / 2,5. Toon e luz do render_meshy.py.
- "Orelha de gato": de frente, o eixo principal de cada chifre (PCA no plano x-z) e o ângulo dele com a vertical; a ponta
  em relação ao topo da cabeça.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/prova_chifres.py -- <pasta> <glb_meshy>
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
from chifres_lib import head_ellipsoid, horn_islands, merged_mesh, neck_z  # noqa: E402
from prot_lib import GAME_H, GAME_W, ROOT, eevee_scene, game_camera, hex_linear, import_glb, load_rest, mesh_objects, mesh_points, render, toon_material  # noqa: E402,E501
from render_meshy import AMBIENT_RGB, SUN_RGB, camera_right, light_dir, load_villager, ortho_camera, projected, root_of  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo.glb"
HORNS = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--chifres=")),
                   ROOT / "assets/modelos/protagonista_v2/chifres.glb")).resolve()
GEM = ROOT / "assets/modelos/protagonista_v2/cristal.glb"
ROSTO = ROOT / "assets/modelos/protagonista_v2/rosto"
COLORS = {"pele": "#91ADB7", "tecido": "#3F3342", "chifre": "#2B2140", "Cristal": "#8FE3FF"}
ZOOMS = (0.4, 1.0, 2.5)
SIDE_M = 0.45


def raw_views(out, glb):
    scene = eevee_scene(transparent=True)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    bust = merged_mesh(import_glb(glb))
    pts = np.array([v.co[:] for v in bust.data.vertices])
    nz = neck_z(pts)
    c, r = head_ellipsoid(pts, nz + 0.05 * np.ptp(pts[:, 2]))
    islands, _ = horn_islands(bust, c, r, nz)
    fc = np.array([p.center[:] for p in bust.data.polygons])
    mats = {k: toon_material(k, light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(h))
            for k, h in (("cabeca", "#B8C4CE"), ("escolhido", "#5A3F86"), ("descartado", "#C0503C"))}
    for m in mats.values():
        bust.data.materials.append(m)
    for comp in islands:
        n = ((fc[comp] - c) / r).mean(axis=0)
        idx = 1 if (n[2] > 0 and n[1] < 0.3) else (2 if n[2] > 0 else 0)
        for i in comp:
            bust.data.polygons[i].material_index = idx
    lo, hi = pts.min(0), pts.max(0)
    ctr, size = Vector(((lo + hi) / 2).tolist()), float(np.ptp(pts, axis=0).max()) * 1.05
    scene.render.resolution_x = scene.render.resolution_y = 768
    for name, d in (("bruto_frente", Vector((0, -1, 0))), ("bruto_lado", Vector((1, 0, 0))), ("bruto_topo", Vector((0, -0.001, 1)))):
        cam = ortho_camera(scene, d, ctr, size)
        render(scene, out / f"{name}.png")
        bpy.data.objects.remove(cam)


def cat_ear(horns):
    """Eixo principal de cada chifre de frente (x-z) e de lado (y-z): ângulo com a vertical (0 = em pé)."""
    v = np.array([(horns.matrix_world @ x.co)[:] for x in horns.data.vertices])
    out = {}
    for side, name in ((-1, "direito"), (1, "esquerdo")):
        p = v[v[:, 0] * side > 0]
        base = p[p[:, 2] < np.percentile(p[:, 2], 15)].mean(axis=0)
        tip = p[p[:, 2] > np.percentile(p[:, 2], 90)].mean(axis=0)
        axis = tip - base
        front = math.degrees(math.atan2(abs(axis[0]), axis[2]))  # de frente: para fora
        side_ang = math.degrees(math.atan2(axis[1], axis[2]))  # de lado: + = para trás
        out[name] = {"inclinacao_de_frente_graus": round(front, 1), "inclinacao_de_lado_graus_para_tras": round(side_ang, 1),
                     "ponta_z_m": round(float(p[:, 2].max()), 4), "base_z_m": round(float(base[2]), 4),
                     "sai_para_fora_mm": round(float(abs(p[:, 0]).max() - abs(base[0])) * 1000, 1)}
    return out


def main() -> None:
    args = [a for a in sys.argv[sys.argv.index("--") + 1:] if not a.startswith("--")]
    out, glb = Path(args[0]), Path(args[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    raw_views(out, glb)

    scene = eevee_scene(transparent=True)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    body = load_rest(BODY)
    rosto = json.loads((ROSTO / "rosto.json").read_text())
    mats = {k: toon_material(k, light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(h)) for k, h in COLORS.items()}
    for key, obj_name in (("olhos", "Olhos"), ("boca", "Boca")):
        grid = rosto[key]
        mats[obj_name] = toon_material(f"rosto_{key}", light_dir(), SUN_RGB, AMBIENT_RGB,
                                       image=bpy.data.images.load(str(ROSTO / f"{key}.png")), cell=(0, grid["colunas"], grid["linhas"]))
    extras = [o for o in import_glb(HORNS) + import_glb(GEM) if o.type == "MESH"]
    for o in mesh_objects(body) + extras:
        base = o.name.split(".")[0]
        mname = o.data.materials[0].name.split(".")[0] if o.data.materials else "pele"
        m = mats.get(base) or mats.get(mname) or mats["pele"]
        o.data.materials.clear()
        o.data.materials.append(m)
    root_of(body + extras, "protagonista")
    horns = next(o for o in extras if o.name.startswith("chifres"))
    info = {"orelha_de_gato": cat_ear(horns), "jogo": {}}
    vill, vroot = load_villager()
    bpy.context.view_layer.update()
    head_c = Vector((0, 0, 0.73))
    scene.render.resolution_x = scene.render.resolution_y = 768
    for view, d in (("frente", Vector((0, -1, 0))), ("lado", Vector((1, 0, 0))), ("tres_quartos", Vector((1, -1, 0.3))),
                    ("costas", Vector((0, 1, 0)))):
        vroot.location = (5, 0, 0)  # fora do close
        bpy.context.view_layer.update()
        cam = ortho_camera(scene, d, head_c, 0.24)
        render(scene, out / f"cabeca_{view}.png")
        bpy.data.objects.remove(cam)
    for view, d in (("frente", Vector((0, -1, 0))), ("tres_quartos", Vector((1, -1, 0)))):
        scene.render.resolution_x = scene.render.resolution_y = 1024
        cam = ortho_camera(scene, d, Vector((0, 0, 0)), 1.0)
        right = camera_right(cam)
        vroot.location = right * SIDE_M
        bpy.context.view_layer.update()
        cam.location = right * (SIDE_M / 2) + Vector((0, 0, 0.46)) + d.normalized() * 10
        bpy.context.view_layer.update()
        render(scene, out / f"corpo_{view}.png")
        bpy.data.objects.remove(cam)
    vroot.location = (SIDE_M, 0, 0)
    bpy.context.view_layer.update()
    ppts = mesh_points(mesh_objects(body) + extras)
    vpts = mesh_points(vill)
    hpts = mesh_points([horns])
    for zoom in ZOOMS:
        cam = game_camera(scene, zoom)
        bpy.context.view_layer.update()
        pp, vp, hp = projected(scene, cam, ppts), projected(scene, cam, vpts), projected(scene, cam, hpts)
        both = np.vstack([pp, vp])
        head = pp[ppts[:, 2] > 0.6]
        info["jogo"][str(zoom)] = {"chifres_px": [round(float(np.ptp(hp[:, 0])), 1), round(float(np.ptp(hp[:, 1])), 1)],
                                   "caixa_px": [float(both[:, 0].min()), float(both[:, 1].min()), float(both[:, 0].max()), float(both[:, 1].max())],
                                   "cabeca_centro_px": [float(head[:, 0].mean()), float(head[:, 1].mean())], "tela": [GAME_W, GAME_H]}
        render(scene, out / f"jogo_{zoom}.png")
        bpy.data.objects.remove(cam)
    (out / "prova_chifres.json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n")
    print("PROVA " + json.dumps(info["orelha_de_gato"], ensure_ascii=False), json.dumps({z: j["chifres_px"] for z, j in info["jogo"].items()}))


main()

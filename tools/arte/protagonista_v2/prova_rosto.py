"""Protagonista v2, passo 4: prova do rosto no corpo limpo, ANTES do rig (Blender headless).

Para cada variação do estudo_rosto.py: retalhos "Olhos" e "Boca" como no aldeão (corpo_lib.face_patch): curvos, a
2 mm da pele, cilíndricos em volta do eixo da cabeça; olhos até ±45° e na janela 10% mais alta, boca na janela padrão;
UV 0..1 na célula única do estudo. Material toon com alfa misturado (o mesmo Toon.gdshaderinc da pele, como o
VillagerFace.gdshader); pele #91ADB7, tecido #3F3342, luz do render_meshy.py. O peso 100% no Head fica para o rig.
Vistas: frente e 3/4 ortográficas com o aldeão v2 ao lado, close da cabeça (frente e 3/4) e câmera do jogo
(CameraRig.cs) nos zooms 0,4 / 1 / 2,5 em 3024×1890.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/prova_rosto.py -- <pasta>
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
from corpo_lib import EYES_FRAC, MOUTH_FRAC, face_patch, head_box, window_rect  # noqa: E402
from prot_lib import GAME_H, GAME_W, ROOT, eevee_scene, game_camera, hex_linear, import_glb, mesh_objects, mesh_points, render, toon_material  # noqa: E402,E501
from render_meshy import AMBIENT_RGB, SUN_RGB, camera_right, light_dir, load_villager, ortho_camera, projected, root_of  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
STUDY = ROOT / "assets/previews/protagonista_v2/rosto_estudo"
COLORS = {"pele": "#91ADB7", "tecido": "#3F3342"}
OFFSET = 0.002
RAISE = 0.10
PHI_MAX = 45
ZOOMS = (0.4, 1.0, 2.5)
SIDE_M = 0.45


def main() -> None:
    out = Path(sys.argv[sys.argv.index("--") + 1:][0])
    out.mkdir(parents=True, exist_ok=True)
    variants = json.loads((STUDY / "variacoes.json").read_text())
    scene = eevee_scene(transparent=True)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    prot = import_glb(BODY)
    mats = {k: toon_material(k, light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(v)) for k, v in COLORS.items()}
    for obj in mesh_objects(prot):
        m = obj.data.materials[0].name.split(".")[0] if obj.data.materials else "pele"
        obj.data.materials.clear()
        obj.data.materials.append(mats.get(m, mats["pele"]))
    root_of(prot, "protagonista")
    vill, vroot = load_villager()
    bpy.context.view_layer.update()
    head_obj = next(o for o in mesh_objects(prot) if o.name.split(".")[0] == "cabeca")
    pts = mesh_points(prot)
    box = head_box(pts)
    info = {"cabeca": box, "variacoes": {}}

    for name in variants:
        eyes = face_patch(head_obj, "Olhos", window_rect(box, EYES_FRAC, RAISE), 1, 1, OFFSET, grid=(32, 20), phi_max_deg=PHI_MAX)
        mouth = face_patch(head_obj, "Boca", window_rect(box, MOUTH_FRAC), 1, 1, OFFSET, grid=(16, 8))
        for patch, key in ((eyes, "olhos"), (mouth, "boca")):
            img = bpy.data.images.load(str(STUDY / f"{name}_{key}.png"))
            patch.data.materials.append(toon_material(f"rosto_{key}_{name}", light_dir(), SUN_RGB, AMBIENT_RGB, image=img,
                                                      cell=(0, 1, 1)))
        v = {"janela_olhos": list(eyes["janela"]), "janela_boca": list(mouth["janela"]), "jogo": {}}

        # frente e 3/4 com o aldeão à direita da câmera; close da cabeça sem o aldeão
        for view, d in (("frente", Vector((0, -1, 0))), ("tres_quartos", Vector((1, -1, 0)))):
            scene.render.resolution_x = scene.render.resolution_y = 1024
            cam = ortho_camera(scene, d, Vector((0, 0, 0)), 1.0)
            right = camera_right(cam)
            vroot.location = right * SIDE_M
            bpy.context.view_layer.update()
            cam.location = right * (SIDE_M / 2) + Vector((0, 0, 0.46)) + d.normalized() * 10
            bpy.context.view_layer.update()
            render(scene, out / f"{name}_{view}.png")
            bpy.data.objects.remove(cam)
            cz = (box["z"][0] + box["z"][1]) / 2
            cam = ortho_camera(scene, d, Vector((0, 0, cz)), 0.2)
            render(scene, out / f"{name}_cabeca_{view}.png")
            bpy.data.objects.remove(cam)

        vroot.location = (SIDE_M, 0, 0)
        bpy.context.view_layer.update()
        ppts, vpts = mesh_points(prot), mesh_points(vill)
        for zoom in ZOOMS:
            cam = game_camera(scene, zoom)
            bpy.context.view_layer.update()
            pp, vp = projected(scene, cam, ppts), projected(scene, cam, vpts)
            both = np.vstack([pp, vp])
            hp = projected(scene, cam, pts[pts[:, 2] >= box["z"][0]])
            v["jogo"][str(zoom)] = {
                "protagonista_px": round(float(pp[:, 1].max() - pp[:, 1].min()), 1),
                "cabeca_px": [round(float(hp[:, 0].max() - hp[:, 0].min()), 1), round(float(hp[:, 1].max() - hp[:, 1].min()), 1)],
                "caixa_px": [float(both[:, 0].min()), float(both[:, 1].min()), float(both[:, 0].max()), float(both[:, 1].max())],
                "cabeca_caixa_px": [float(hp[:, 0].min()), float(hp[:, 1].min()), float(hp[:, 0].max()), float(hp[:, 1].max())],
                "tela": [GAME_W, GAME_H]}
            render(scene, out / f"{name}_jogo_{zoom}.png")
            bpy.data.objects.remove(cam)
        info["variacoes"][name] = v
        for patch in (eyes, mouth):
            bpy.data.objects.remove(patch)
        print("VAR " + name + " " + json.dumps({z: j["cabeca_px"] for z, j in v["jogo"].items()}), flush=True)
    (out / "prova.json").write_text(json.dumps(info, indent=2) + "\n")


main()

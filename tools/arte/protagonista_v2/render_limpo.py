"""Passo 3: renders do corpo limpo da protagonista para a folha de contato (Blender headless).

Toon chapado pelas cores dos materiais do contrato (pele #91ADB7, tecido #3F3342), luz do render_meshy.py (fraca,
fria, quase de cima), sempre com o aldeão v2 ao lado (só o corpo). Vistas: frente, lado (perfil esquerdo), costas,
3/4 (ortográficas, mesma escala) e câmera do jogo (CameraRig.cs) nos zooms 0,4 / 1 / 2,5, com a altura em px por
projeção de vértices; mais frente e lado com as 9 regiões pintadas e a frente da protagonista sozinha (máscara para
medir a cabeça pela silhueta, como nas folhas).

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/render_limpo.py -- <pasta> [corpo.glb]
"""

import colorsys
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import GAME_H, GAME_W, ROOT, eevee_scene, game_camera, hex_linear, import_glb, mesh_objects, mesh_points, render, toon_material  # noqa: E402,E501
from render_meshy import AMBIENT_RGB, SUN_RGB, camera_right, light_dir, load_villager, ortho_camera, projected, root_of  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
COLORS = {"pele": "#91ADB7", "tecido": "#3F3342"}
REGIONS = ["cabeca", "tronco", "bracos", "maos", "quadril", "roupa_intima", "coxas", "canelas", "pes"]
ZOOMS = (0.4, 1.0, 2.5)
ORTHO = 1.0
SIDE_M = 0.45
HEIGHT = 0.80


def region_hex(i: int) -> str:
    r, g, b = colorsys.hsv_to_rgb(i / len(REGIONS), 0.55, 0.85)
    return "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))


def paint(objects, by_region: bool) -> None:
    cache = {}
    for obj in mesh_objects(objects):
        name = obj.name.split(".")[0]
        if by_region:
            key = region_hex(REGIONS.index(name)) if name in REGIONS else "#FF00FF"
        else:
            mat = obj.data.materials[0].name.split(".")[0] if obj.data.materials else "pele"
            key = COLORS.get(mat, COLORS["pele"])
        if key not in cache:
            cache[key] = toon_material(f"m_{key}", light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(key))
        obj.data.materials.clear()
        obj.data.materials.append(cache[key])


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    out = Path(args[0])
    body = Path(args[1]).resolve() if len(args) > 1 else BODY
    out.mkdir(parents=True, exist_ok=True)
    scene = eevee_scene(transparent=True)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    prot = import_glb(body)
    root_of(prot, "protagonista")
    paint(prot, by_region=False)
    vill, vroot = load_villager()
    bpy.context.view_layer.update()
    ppts = mesh_points(prot)
    info = {"corpo": str(body.relative_to(ROOT)), "altura_m": round(float(ppts[:, 2].max() - ppts[:, 2].min()), 4),
            "triangulos": {}, "jogo": {}}
    for obj in mesh_objects(prot):
        obj.data.calc_loop_triangles()
        info["triangulos"][obj.name.split(".")[0]] = len(obj.data.loop_triangles)
    info["triangulos_total"] = sum(info["triangulos"].values())

    def views(prefix):
        for view, d in (("frente", Vector((0, -1, 0))), ("lado", Vector((1, 0, 0))), ("costas", Vector((0, 1, 0))),
                        ("tres_quartos", Vector((1, -1, 0)))):
            scene.render.resolution_x = scene.render.resolution_y = 1024
            cam = ortho_camera(scene, d, Vector((0, 0, 0)), ORTHO)
            right = camera_right(cam)
            vroot.location = right * SIDE_M
            bpy.context.view_layer.update()
            c = right * (SIDE_M / 2) + Vector((0, 0, ORTHO / 2 - 0.04))
            cam.location = c + d.normalized() * 10
            bpy.context.view_layer.update()
            render(scene, out / f"{prefix}{view}.png")
            bpy.data.objects.remove(cam)

    views("")
    vroot.location = (SIDE_M, 0, 0)
    bpy.context.view_layer.update()
    vpts = mesh_points(vill)
    for zoom in ZOOMS:
        cam = game_camera(scene, zoom)
        bpy.context.view_layer.update()
        pp, vp = projected(scene, cam, ppts), projected(scene, cam, vpts)
        both = np.vstack([pp, vp])
        info["jogo"][str(zoom)] = {
            "protagonista_px": round(float(pp[:, 1].max() - pp[:, 1].min()), 1),
            "aldeao_px": round(float(vp[:, 1].max() - vp[:, 1].min()), 1),
            "caixa_px": [float(both[:, 0].min()), float(both[:, 1].min()), float(both[:, 0].max()), float(both[:, 1].max())],
            "tela": [GAME_W, GAME_H]}
        render(scene, out / f"jogo_{zoom}.png")
        bpy.data.objects.remove(cam)

    # Máscara (só a protagonista, mesmo quadro do render_meshy: 0,88 m em 1024, centro z = 0,40).
    for o in vill:
        o.hide_render = True
    scene.render.resolution_x = scene.render.resolution_y = 1024
    cam = ortho_camera(scene, Vector((0, -1, 0)), Vector((0, 0, HEIGHT / 2)), HEIGHT * 1.1)
    render(scene, out / "mascara.png")
    bpy.data.objects.remove(cam)

    # Regiões pintadas (sem o aldeão).
    paint(prot, by_region=True)
    for view, d in (("frente", Vector((0, -1, 0))), ("lado", Vector((1, 0, 0))), ("costas", Vector((0, 1, 0)))):
        cam = ortho_camera(scene, d, Vector((0, 0, HEIGHT / 2)), HEIGHT * 1.1)
        render(scene, out / f"regioes_{view}.png")
        bpy.data.objects.remove(cam)
    info["cores_regioes"] = {r: region_hex(i) for i, r in enumerate(REGIONS)}
    (out / "render.json").write_text(json.dumps(info, indent=2) + "\n")
    print("RENDER " + json.dumps({k: v for k, v in info.items() if k != "jogo"}))
    print("PX " + json.dumps({z: (v["protagonista_px"], v["aldeao_px"]) for z, v in info["jogo"].items()}))


main()

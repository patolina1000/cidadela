"""Protagonista v2, passo 6: prova do atlas do rosto (Blender headless), antes do rig.

Retalhos "Olhos" e "Boca" nas janelas da b3 aprovada (corpo_lib.face_patch na malha "cabeca": 2 mm da pele, olhos até
±45° e janela 10% da cabeça mais alta, boca 12% mais alta), material toon com alfa, uma célula do atlas por quadro
(rosto.json). Para cada expressão: close da cabeça de frente e 3/4, e a câmera do jogo no zoom 2,5 com o aldeão ao
lado. Para o GIF do piscar, os quadros aberto, meio_fechado e fechado em close e no zoom 2,5.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/prova_atlas.py -- <pasta>
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
from render_meshy import AMBIENT_RGB, SUN_RGB, light_dir, load_villager, ortho_camera, projected, root_of  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
ROSTO = ROOT / "assets/modelos/protagonista_v2/rosto"
COLORS = {"pele": "#91ADB7", "tecido": "#3F3342"}
OFFSET, EYES_RAISE, MOUTH_RAISE, PHI_MAX = 0.002, 0.10, 0.12, 45  # b3
SIDE_M = 0.45
ZOOM = 2.5


def main() -> None:
    out = Path(sys.argv[sys.argv.index("--") + 1:][0])
    out.mkdir(parents=True, exist_ok=True)
    rosto = json.loads((ROSTO / "rosto.json").read_text())
    scene = eevee_scene(transparent=True)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    prot = import_glb(BODY)
    mats = {k: toon_material(k, light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(c)) for k, c in COLORS.items()}
    for obj in mesh_objects(prot):
        m = obj.data.materials[0].name.split(".")[0] if obj.data.materials else "pele"
        obj.data.materials.clear()
        obj.data.materials.append(mats.get(m, mats["pele"]))
    root_of(prot, "protagonista")
    vill, vroot = load_villager()
    bpy.context.view_layer.update()
    head_obj = next(o for o in mesh_objects(prot) if o.name.split(".")[0] == "cabeca")
    box = head_box(mesh_points(prot))
    eyes = face_patch(head_obj, "Olhos", window_rect(box, EYES_FRAC, EYES_RAISE), 1, 1, OFFSET, grid=(32, 20), phi_max_deg=PHI_MAX)
    mouth = face_patch(head_obj, "Boca", window_rect(box, MOUTH_FRAC, MOUTH_RAISE), 1, 1, OFFSET, grid=(16, 8))
    frames = {}
    for key, patch in (("olhos", eyes), ("boca", mouth)):
        grid = rosto[key]
        img = bpy.data.images.load(str(ROSTO / f"{key}.png"))
        frames[key] = {name: toon_material(f"rosto_{key}_{name}", light_dir(), SUN_RGB, AMBIENT_RGB, image=img,
                                           cell=(idx, grid["colunas"], grid["linhas"]))
                       for name, idx in grid["quadros"].items()}
        patch.data.materials.append(next(iter(frames[key].values())))

    def show(eye_frame, mouth_frame):
        eyes.data.materials[0] = frames["olhos"][eye_frame]
        mouth.data.materials[0] = frames["boca"][mouth_frame]

    cz = (box["z"][0] + box["z"][1]) / 2
    size = 1.25 * (box["z"][1] - box["z"][0])
    vroot.location = (SIDE_M, 0, 0)
    bpy.context.view_layer.update()
    pts, vpts = mesh_points(prot), mesh_points(vill)
    cam_game = game_camera(scene, ZOOM)
    bpy.context.view_layer.update()
    pp, vp = projected(scene, cam_game, pts), projected(scene, cam_game, vpts)
    hp = projected(scene, cam_game, pts[(pts[:, 2] >= box["z"][0]) & (np.abs(pts[:, 0]) < 0.12)])
    both = np.vstack([pp, vp])
    info = {"janela_olhos": list(eyes["janela"]), "janela_boca": list(mouth["janela"]), "cabeca": box,
            "jogo": {"zoom": ZOOM, "caixa_px": [float(both[:, 0].min()), float(both[:, 1].min()), float(both[:, 0].max()), float(both[:, 1].max())],
                     "cabeca_caixa_px": [float(hp[:, 0].min()), float(hp[:, 1].min()), float(hp[:, 0].max()), float(hp[:, 1].max())],
                     "tela": [GAME_W, GAME_H]}}
    bpy.data.objects.remove(cam_game)

    def shoot(tag):
        scene.render.resolution_x = scene.render.resolution_y = 1024
        for view, d in (("frente", Vector((0, -1, 0))), ("tres_quartos", Vector((1, -1, 0)))):
            cam = ortho_camera(scene, d, Vector((0, 0, cz)), size)
            render(scene, out / f"{tag}_cabeca_{view}.png")
            bpy.data.objects.remove(cam)
        cam = game_camera(scene, ZOOM)
        render(scene, out / f"{tag}_jogo.png")
        bpy.data.objects.remove(cam)

    for name, spec in rosto["expressoes"].items():
        show(spec["olhos"], spec["boca"])
        shoot(name)
    for frame in ("meio_fechado",):  # o quadro do meio do piscar (aberto e fechado já saíram)
        show(frame, rosto["expressoes"]["neutra_cansada"]["boca"])
        shoot(f"piscar_{frame}")
    (out / "prova_atlas.json").write_text(json.dumps(info, indent=2) + "\n")
    print("ATLAS ok")


main()

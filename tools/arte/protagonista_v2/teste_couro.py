"""Teste automático: pele do couro cabeludo à mostra (meta zero). Blender headless.

Monta a cena como o prova_cabelo.py (corpo final, cabelo, chifres no Head, cristal). Pinta de vermelho puro (emissão) só as
faces do couro cabeludo da malha "cabeca" (cabelo_lib.scalp_mask, borda recuada 4 mm para a própria linha do cabelo não
contar) e de preto todo o resto (cabelo, chifres, corpo, rosto). Renderiza a cabeça em 10 direções (frente, costas, perfis,
quatro 3/4, de cima e de cima pela frente) e a câmera do jogo nos zooms 0,4 / 1 / 2,5; em repouso e em quadros da corrida e
do idle. Conta os pixels vermelhos de cada imagem.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/teste_couro.py -- <pasta> [--cabelo=... --chifres=...] [--guardar]
Saída: <pasta>/teste_couro.json e as imagens com pele à mostra (se houver).
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
from cabelo_lib import scalp_mask  # noqa: E402
from prova_cabelo import build  # noqa: E402
from prot_lib import eevee_scene, game_camera, mesh_points, render  # noqa: E402
from render_meshy import ortho_camera  # noqa: E402
from rig_lib import play  # noqa: E402

VIEWS = {"frente": (0, -1, 0.1), "costas": (0, 1, 0.1), "perfil_esq": (1, 0, 0.1), "perfil_dir": (-1, 0, 0.1),
         "tq_frente_esq": (1, -1, 0.4), "tq_frente_dir": (-1, -1, 0.4), "tq_costas_esq": (1, 1, 0.4), "tq_costas_dir": (-1, 1, 0.4),
         "cima": (0, -0.02, 1), "cima_frente": (0, -0.6, 1)}
ZOOMS = (0.4, 1.0, 2.5)
FRAMES = {"run-loop": (0, 5, 10, 15), "idle-loop": (0, 90, 180)}


def emission(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out, em = nt.nodes.new("ShaderNodeOutputMaterial"), nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1)
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def red_pixels(path):
    img = bpy.data.images.load(str(path))
    px = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    return int(((px[:, :, 0] > 0.5) & (px[:, :, 1] < 0.2) & (px[:, :, 2] < 0.2) & (px[:, :, 3] > 0.5)).sum())


def main() -> None:
    out = Path([a for a in sys.argv[sys.argv.index("--") + 1:] if not a.startswith("--")][0])
    out.mkdir(parents=True, exist_ok=True)
    scene = eevee_scene(transparent=True)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.view_settings.view_transform = "Standard"
    armature, meshes = build(scene)
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    head = next(o for o in meshes if o.name.split(".")[0] == "cabeca")
    eyes = next(o for o in meshes if o.name.split(".")[0] == "Olhos")
    hp = np.array([(head.matrix_world @ v.co)[:] for v in head.data.vertices])
    ep = np.array([(eyes.matrix_world @ v.co)[:] for v in eyes.data.vertices])
    from chifres_lib import head_ellipsoid
    cb, _ = head_ellipsoid(hp, hp[:, 2].min() + 0.05 * np.ptp(hp[:, 2]))
    mask = scalp_mask(hp, cb, float(ep[:, 2].max()), float(hp[:, 2].max()), float(hp[:, 2].min()), shrink=0.004)
    red, black = emission("pele_do_couro", (1, 0, 0)), emission("resto", (0, 0, 0))
    for o in meshes:
        o.data.materials.clear()
        o.data.materials.append(black)
    head.data.materials.append(red)
    scalp_faces = 0
    for p in head.data.polygons:
        if all(mask[i] for i in p.vertices):
            p.material_index = 1
            scalp_faces += 1
    result = {"faces_do_couro": scalp_faces, "imagens": {}}
    head_c = Vector((0, 0.01, 0.72))

    def shoot_all(tag):
        scene.render.resolution_x = scene.render.resolution_y = 512
        for name, d in VIEWS.items():
            cam = ortho_camera(scene, Vector(d), head_c, 0.3)
            path = out / f"{tag}_{name}.png"
            render(scene, path)
            result["imagens"][f"{tag}_{name}"] = red_pixels(path)
            bpy.data.objects.remove(cam)
        for z in ZOOMS:
            cam = game_camera(scene, z)
            path = out / f"{tag}_jogo_{z}.png"
            render(scene, path)
            result["imagens"][f"{tag}_jogo_{z}"] = red_pixels(path)
            bpy.data.objects.remove(cam)

    shoot_all("repouso")
    armature.data.pose_position = "POSE"
    for clip, frames in FRAMES.items():
        play(armature, bpy.data.actions[clip])
        for f in frames:
            scene.frame_set(f)
            shoot_all(f"{clip}@{f}")
    result["total_pixels_de_pele"] = sum(result["imagens"].values())
    result["imagens_com_pele"] = {k: v for k, v in result["imagens"].items() if v}
    if "--guardar" not in sys.argv:
        for k, v in result["imagens"].items():
            if not v:
                (out / f"{k}.png").unlink(missing_ok=True)
    (out / "teste_couro.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print("TESTE " + json.dumps({"total": result["total_pixels_de_pele"], "com_pele": result["imagens_com_pele"], "faces": scalp_faces}))


main()

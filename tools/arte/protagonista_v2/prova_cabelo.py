"""Prova do cabelo da protagonista v2 (Blender headless): corpo final + cabelo.glb + chifres.glb + cristal.glb, toon e luz
do render_meshy.py, rosto no quadro padrão. Vistas: close da cabeça (frente, perfil, costas, 3/4, topo) e o corpo
inteiro (frente, perfil, costas, 3/4), com o aldeão e a v1 ao lado; câmera do jogo nos zooms 0,4 / 1 / 2,5.
Com --clipe=<nome>:<n>: renderiza n quadros do clipe (jogo e lado) para o GIF com cabelo.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/prova_cabelo.py -- <pasta> [--clipe=run-loop:19]
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
from prot_lib import GAME_H, GAME_W, ROOT, V1, eevee_scene, game_camera, hex_linear, import_glb, load_rest, mesh_objects, mesh_points, render, toon_material  # noqa: E402,E501
from render_meshy import AMBIENT_RGB, SUN_EULER, SUN_RGB, light_dir, load_villager, ortho_camera, projected, root_of  # noqa: E402
from rig_lib import play  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo.glb"
HAIR = ROOT / "assets/modelos/protagonista_v2/cabelo.glb"
HORNS = ROOT / "assets/modelos/protagonista_v2/chifres.glb"
GEM = ROOT / "assets/modelos/protagonista_v2/cristal.glb"
ROSTO = ROOT / "assets/modelos/protagonista_v2/rosto"
COLORS = {"pele": "#91ADB7", "tecido": "#3F3342", "chifre": "#2B2140", "cabelo": "#4B5A69", "Cristal": "#8FE3FF"}
ZOOMS = (0.4, 1.0, 2.5)
ALDEAO_X, V1_X = 0.42, -0.62


def build(scene):
    objs = import_glb(BODY)
    armature = next(o for o in objs if o.type == "ARMATURE")
    for t in armature.animation_data.nla_tracks:
        t.mute = True
    armature.animation_data.action = None
    armature.data.pose_position = "REST"  # prender as peças no repouso: senão elas ficam onde o osso estava na pose
    bpy.context.view_layer.update()
    hair_objs = import_glb(HAIR)
    hair_arm = next(o for o in hair_objs if o.type == "ARMATURE")
    hair = next(o for o in hair_objs if o.type == "MESH")
    world = hair.matrix_world.copy()  # o cabelo passa para o esqueleto do corpo (mesmos nomes de ossos)
    hair.parent = armature
    hair.matrix_world = world
    for m in hair.modifiers:
        if m.type == "ARMATURE":
            m.object = armature
    bpy.data.objects.remove(hair_arm)
    rosto = json.loads((ROSTO / "rosto.json").read_text())
    mats = {k: toon_material(k, light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(h)) for k, h in COLORS.items()}
    for key, name in (("olhos", "Olhos"), ("boca", "Boca")):
        g = rosto[key]
        mats[name] = toon_material(f"rosto_{key}", light_dir(), SUN_RGB, AMBIENT_RGB,
                                   image=bpy.data.images.load(str(ROSTO / f"{key}.png")), cell=(0, g["colunas"], g["linhas"]))
    rigid = [o for o in import_glb(HORNS) + import_glb(GEM) if o.type == "MESH"]
    for o in rigid:  # chifres no Head e cristal no Spine, compensando o repouso (como o jogo)
        bone = "Head" if o.name.startswith("chifres") else "Spine"
        w = o.matrix_world.copy()
        o.parent = armature
        o.parent_type = "BONE"
        o.parent_bone = bone
        bpy.context.view_layer.update()
        o.matrix_world = w
    meshes = mesh_objects(objs) + [hair] + rigid
    for o in meshes:
        base = o.name.split(".")[0]
        mname = o.data.materials[0].name.split(".")[0] if o.data.materials else "pele"
        mat = mats.get(base) or mats.get(mname) or mats["pele"]
        o.data.materials.clear()
        o.data.materials.append(mat)
    return armature, meshes


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    out = Path([a for a in args if not a.startswith("--")][0])
    clip = next((a.split("=", 1)[1] for a in args if a.startswith("--clipe=")), None)
    out.mkdir(parents=True, exist_ok=True)
    scene = eevee_scene(transparent=True)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    armature, meshes = build(scene)
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()

    if clip:
        name, n = clip.split(":")
        armature.data.pose_position = "POSE"
        action = bpy.data.actions[name]
        play(armature, action)
        a, b = (int(x) for x in action.frame_range)
        frames = sorted({a + round((b - a) * i / int(n)) for i in range(int(n))})
        scene.render.resolution_x = scene.render.resolution_y = 512
        for f in frames:
            scene.frame_set(f)
            for view, d in (("lado", Vector((1, 0, 0.35))), ("costas", Vector((0.35, 1, 0.3))), ("jogo", Vector((0, -math.cos(math.radians(55)), math.sin(math.radians(55)))))):
                cam = ortho_camera(scene, d, Vector((0, 0, 0.42)), 1.05)
                render(scene, out / f"{name}_{view}_{f:03d}.png")
                bpy.data.objects.remove(cam)
        return

    head_c = Vector((0, 0.01, 0.70))
    scene.render.resolution_x = scene.render.resolution_y = 768
    for view, d in (("frente", Vector((0, -1, 0))), ("lado", Vector((1, 0, 0))), ("costas", Vector((0, 1, 0))),
                    ("tres_quartos", Vector((1, -1, 0.3))), ("topo", Vector((0, -0.25, 1)))):
        cam = ortho_camera(scene, d, head_c, 0.34)
        render(scene, out / f"cabeca_{view}.png")
        bpy.data.objects.remove(cam)
    for view, d in (("frente", Vector((0, -1, 0))), ("lado", Vector((1, 0, 0))), ("costas", Vector((0, 1, 0))), ("tres_quartos", Vector((1, -1, 0.2)))):
        cam = ortho_camera(scene, d, Vector((0, 0, 0.42)), 0.95)
        render(scene, out / f"corpo_{view}.png")
        bpy.data.objects.remove(cam)
    # câmera do jogo com o aldeão e a v1 ao lado (a v1 com a textura dela e luz de verdade)
    vill, vroot = load_villager()
    vroot.location = (ALDEAO_X, 0, 0)
    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sun.data.energy, sun.data.color, sun.rotation_euler = 1.0, SUN_RGB, SUN_EULER
    scene.collection.objects.link(sun)
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*AMBIENT_RGB, 1)
    bg.inputs["Strength"].default_value = 1.0  # só o PBR da v1 usa; o toon é emissivo
    v1 = load_rest(V1)
    root_of(v1, "v1").location = (V1_X, 0, 0)
    bpy.context.view_layer.update()
    info = {"jogo": {}}
    ppts, allp = mesh_points(meshes), mesh_points(meshes + vill + mesh_objects(v1))
    for zoom in ZOOMS:
        cam = game_camera(scene, zoom)
        bpy.context.view_layer.update()
        pp, ap = projected(scene, cam, ppts), projected(scene, cam, allp)
        info["jogo"][str(zoom)] = {"protagonista_px": round(float(np.ptp(pp[:, 1])), 1),
                                   "caixa_px": [float(ap[:, 0].min()), float(ap[:, 1].min()), float(ap[:, 0].max()), float(ap[:, 1].max())],
                                   "cabeca_centro_px": [float(pp[ppts[:, 2] > 0.62][:, 0].mean()), float(pp[ppts[:, 2] > 0.62][:, 1].mean())],
                                   "tela": [GAME_W, GAME_H]}
        render(scene, out / f"jogo_{zoom}.png")
        bpy.data.objects.remove(cam)
    (out / "prova_cabelo.json").write_text(json.dumps(info, indent=2) + "\n")
    print("PROVA ok")


main()

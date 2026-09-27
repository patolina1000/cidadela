"""Prévia do aldeão modular: o corpo-base com cada cabelo, na câmera do jogo (55°), numerados.

Cada cópia do corpo-base toca o mesmo quadro do clipe; o cabelo (assets/modelos/aldeao_cabelos/<var>.glb,
com a origem no encaixe "Cabelo") acompanha o osso da cabeça naquele quadro, como no jogo.

Uso:
  Blender -b --factory-startup --python tools/blender/preview_modular.py -- <saida.png> <clipe> <var1> [<var2> ...]
  (variável AZIMUTE em graus gira a câmera em volta: 0 = de frente, como no jogo; 180 = por trás)
"""

import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = "aldeao_base"
GAME_TILT_DEGREES = 55  # GDD, seção 12
SPACING = 0.55  # m entre os aldeões
WIDTH, HEIGHT = 1800, 620


def imported(path: Path) -> list:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), disable_bone_shape=True)
    return [o for o in bpy.data.objects if o not in before]


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    out, clip, variants = Path(args[0]), args[1], args[2:]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("fundo")
    scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.15, 0.19, 1)
    gx, gy, gz = json.loads((ROOT / "assets/modelos" / BASE / f"{BASE}.json").read_text())["encaixes"]["Cabelo"]
    anchor = Vector((gx, -gz, gy))  # glTF -> Blender

    labels = []
    for i, variant in enumerate(variants):
        x = (i - (len(variants) - 1) / 2) * SPACING
        objs = imported(ROOT / "assets/modelos" / BASE / f"{BASE}.glb")
        root = next(o for o in objs if o.parent is None and o.type == "EMPTY")
        root.location.x += x
        armature = next(o for o in objs if o.type == "ARMATURE")
        action = [a for a in bpy.data.actions if a.name.split(".")[0] == clip][-1]
        armature.animation_data_create()
        armature.animation_data.action = action
        if action.slots:
            armature.animation_data.action_slot = action.slots[0]
        start, end = action.frame_range
        scene.frame_set(int((start + end) / 2))
        # Giro e posição da cabeça neste quadro em relação à pose de repouso, no mundo.
        head = armature.pose.bones["Head"]
        posed = armature.matrix_world @ head.matrix
        rest = armature.matrix_world @ head.bone.matrix_local
        delta = posed @ rest.inverted()
        hair_objs = [o for o in imported(ROOT / "assets/modelos/aldeao_cabelos" / f"{variant}.glb") if o.type == "MESH"]
        for hair in hair_objs:
            hair.matrix_world = delta @ Matrix.Translation(anchor + Vector((x, 0, 0)))
        labels.append({"texto": f"{i + 1}. {variant}", "x": x})

    bpy.ops.mesh.primitive_plane_add(size=len(variants) * SPACING + 2)
    floor = bpy.context.active_object
    grid = bpy.data.materials.new("chao")
    nodes, links = grid.node_tree.nodes, grid.node_tree.links
    checker = nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = len(variants) * SPACING + 2
    checker.inputs["Color1"].default_value = (0.30, 0.28, 0.33, 1)
    checker.inputs["Color2"].default_value = (0.26, 0.24, 0.29, 1)
    links.new(checker.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])
    floor.data.materials.append(grid)
    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(40), 0, math.radians(20))
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = len(variants) * SPACING + 0.2
    tilt = math.radians(GAME_TILT_DEGREES)
    target = Vector((0, 0, 0.2))
    azimuth = math.radians(float(os.environ.get("AZIMUTE", "0")))
    horizontal = Vector((math.sin(azimuth), -math.cos(azimuth), 0)) * math.cos(tilt)
    cam.location = target + (horizontal + Vector((0, 0, math.sin(tilt)))) * 10
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    for label in labels:
        label["x"] = round((0.5 + label["x"] / cam.data.ortho_scale) * WIDTH)
    out.with_suffix(".json").write_text(json.dumps(labels, ensure_ascii=False))


main()

"""Folha de prévia: vários modelos padronizados lado a lado, na câmera do jogo (55°), numerados.

Cada modelo aparece num quadro do clipe escolhido (padrão: meio do idle), sobre um chão cinza com a
grade de 1 m. Os números são escritos depois, com o Pillow, embaixo de cada modelo.

Uso:
  Blender -b --factory-startup --python tools/blender/preview_sheet.py -- <saida.png> <clipe> <nome1> [<nome2> ...]
  (um nome com prefixo "ref:" entra na fila como referência de tamanho, sem número)
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
GAME_TILT_DEGREES = 55  # GDD, seção 12
SPACING = 0.9  # m entre os modelos
WIDTH, HEIGHT = 1800, 700


def import_model(name: str, x: float, clip: str) -> None:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / "assets/modelos" / name / f"{name}.glb"), disable_bone_shape=True)
    imported = [o for o in bpy.data.objects if o not in before]
    root = next(o for o in imported if o.parent is None and o.type == "EMPTY")
    root.location.x += x
    armature = next((o for o in imported if o.type == "ARMATURE"), None)
    if armature is None:
        return
    # Cada importação traz as ações com sufixo (.001...): pega a do próprio arquivo pelo nome base.
    candidates = [a for a in bpy.data.actions if a.name.split(".")[0] == clip and a not in _used]
    action = candidates[-1] if candidates else None
    if action:
        _used.add(action)
        armature.animation_data_create()
        armature.animation_data.action = action
        if action.slots:
            armature.animation_data.action_slot = action.slots[0]


_used: set = set()


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    out, clip, names = Path(args[0]), args[1], args[2:]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("fundo")
    scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.15, 0.19, 1)

    positions = []
    for i, name in enumerate(names):
        x = (i - (len(names) - 1) / 2) * SPACING
        import_model(name.removeprefix("ref:"), x, clip)
        positions.append((name, x))
    frame = None
    for action in _used:
        start, end = action.frame_range
        frame = int((start + end) / 2)
    if frame is not None:
        scene.frame_set(frame)

    bpy.ops.mesh.primitive_plane_add(size=len(names) * SPACING + 2)
    floor = bpy.context.active_object
    grid = bpy.data.materials.new("chao")
    nodes, links = grid.node_tree.nodes, grid.node_tree.links
    checker = nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = len(names) * SPACING + 2
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
    cam.data.ortho_scale = len(names) * SPACING + 0.4
    tilt = math.radians(GAME_TILT_DEGREES)
    target = Vector((0, 0, 0.25))
    cam.location = target + Vector((0, -math.cos(tilt), math.sin(tilt))) * 10
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    # Onde cada modelo cai na imagem, para numerar depois.
    labels = []
    number = 0
    for name, x in positions:
        if name.startswith("ref:"):
            label = name.removeprefix("ref:") + " (referência)"
        else:
            number += 1
            label = f"{number}. {name}"
        u = 0.5 + x / cam.data.ortho_scale
        labels.append({"texto": label, "x": round(u * WIDTH)})
    out.with_suffix(".json").write_text(json.dumps(labels, ensure_ascii=False))


main()

"""Renderiza um asset padronizado de frente, de costas e na câmera do jogo (55°).

Serve para comparar o modelo com o conceito. Frente = +Z do glTF (-Y no Blender).

Uso:
  Blender -b --factory-startup --python tools/blender/render_views.py -- <nome> <pasta_saida>
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
RESOLUTION = 1024
GAME_TILT_DEGREES = 55  # GDD, seção 12
BACKGROUND = (1.0, 1.0, 1.0)


def setup_scene(glb: Path) -> tuple[Vector, Vector]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb), disable_bone_shape=True)
    scene = bpy.context.scene
    scene.render.resolution_x = scene.render.resolution_y = RESOLUTION
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("fundo")
    world.color = BACKGROUND
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (*BACKGROUND, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(40), 0, math.radians(-30))
    scene.collection.objects.link(sun)

    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"
    bpy.context.view_layer.update()
    # Vértices deformados pelo esqueleto: o bound_box do objeto ignora a pose e a escala do rig.
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            evaluated = obj.evaluated_get(depsgraph)
            points += [obj.matrix_world @ v.co for v in evaluated.to_mesh().vertices]
            evaluated.to_mesh_clear()
    low = Vector(min(p[i] for p in points) for i in range(3))
    high = Vector(max(p[i] for p in points) for i in range(3))
    return low, high


def camera(scene, location: Vector, target: Vector, ortho_size: float | None) -> None:
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    if ortho_size:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho_size
    scene.camera = cam


def render(path: Path) -> None:
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(bpy.context.scene.camera)
    print(f"  {path}")


def main() -> None:
    name, out = sys.argv[sys.argv.index("--") + 1:][:2]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    low, high = setup_scene(ROOT / "assets/modelos" / name / f"{name}.glb")
    scene = bpy.context.scene
    center = (low + high) / 2
    size = max(high - low) * 1.1
    distance = size * 3

    camera(scene, center + Vector((0, -distance, 0)), center, size)
    render(out / f"{name}_frente.png")
    camera(scene, center + Vector((0, distance, 0)), center, size)
    render(out / f"{name}_costas.png")

    # Câmera do jogo: inclinada 55° acima do chão, vindo da frente, em pose de repouso.
    tilt = math.radians(GAME_TILT_DEGREES)
    offset = Vector((0, -math.cos(tilt), math.sin(tilt))) * distance
    camera(scene, center + offset, center, size)
    render(out / f"{name}_jogo.png")

    # Um quadro do meio de cada animação, na câmera do jogo.
    armature = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if armature:
        armature.data.pose_position = "POSE"
        armature.animation_data_create()
        for action in bpy.data.actions:
            armature.animation_data.action = action
            if action.slots:
                armature.animation_data.action_slot = action.slots[0]
            start, end = action.frame_range
            scene.frame_set(int((start + end) / 2))
            camera(scene, center + offset, center, size)
            render(out / f"{name}_clipe_{action.name}.png")
        armature.data.pose_position = "REST"
        scene.frame_set(0)

    # Noite: luz fraca e azulada, para ver se só o cristal brilha.
    world = scene.world.node_tree.nodes["Background"]
    world.inputs["Color"].default_value = (0.02, 0.02, 0.05, 1)
    world.inputs["Strength"].default_value = 1.0
    bpy.data.objects["sol"].data.energy = 0.05
    camera(scene, center + Vector((0, -distance, 0)), center, size)
    render(out / f"{name}_noite.png")


main()

"""Confere a máscara do rosto em todos os clipes: distância de cada vértice até a pele da cabeça.

Para cada clipe, em QUADROS instantes, mede a distância (com sinal: negativo = dentro da cabeça) do
vértice da máscara até o ponto mais próximo do corpo, em mm na escala do jogo, e salva um quadro de
frente e um de perfil ampliados na cabeça.

Uso:
  Blender -b --factory-startup --python tools/blender/check_face_mask.py -- <modelo.glb> <pasta_saida>
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

FRAMES = 12


def main() -> None:
    glb, out = sys.argv[sys.argv.index("--") + 1:][:2]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb, disable_bone_shape=True)
    scene = bpy.context.scene
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    planes = [o for o in bpy.data.objects if o.type == "MESH" and o.name.split(".")[0] in ("Rosto", "Olhos", "Boca")]
    body = next(o for o in bpy.data.objects if o.type == "MESH" and o not in planes)
    armature.animation_data_create()
    worst = []
    scene.render.resolution_x = scene.render.resolution_y = 320
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN"))
    sun.data.energy = 3
    sun.rotation_euler = (0.8, 0, -0.4)
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    for clip in ("idle", "walk", "carry", "work", "sleep"):
        action = next(a for a in bpy.data.actions if a.name == clip)
        armature.animation_data.action = action
        if action.slots:
            armature.animation_data.action_slot = action.slots[0]
        start, end = action.frame_range
        distances = {o.name: [] for o in planes}
        for k in range(FRAMES):
            scene.frame_set(int(start + (end - start) * k / FRAMES))
            depsgraph = bpy.context.evaluated_depsgraph_get()
            body_mesh = body.evaluated_get(depsgraph).to_mesh()
            tree = BVHTree.FromPolygons([body.matrix_world @ v.co for v in body_mesh.vertices],
                                        [p.vertices[:] for p in body_mesh.polygons])
            body.evaluated_get(depsgraph).to_mesh_clear()
            for plane in planes:
                plane_mesh = plane.evaluated_get(depsgraph).to_mesh()
                for v in plane_mesh.vertices:
                    point = plane.matrix_world @ v.co
                    nearest, normal, _, dist = tree.find_nearest(point)
                    sign = 1 if (point - nearest).dot(normal) >= 0 else -1
                    distances[plane.name].append(sign * dist * 1000)
                plane.evaluated_get(depsgraph).to_mesh_clear()
        for name, values in distances.items():
            low, high = min(values), max(values)
            worst.append((clip, low, high))
            print(f"PLANO {name:6s} {clip:6s}: distância até a pele de {low:+.2f} a {high:+.2f} mm "
                  f"({'ok' if low > 0.2 and high < 6 else 'VERIFICAR'})")
        # Quadro do meio, frente e perfil, ampliado na cabeça.
        scene.frame_set(int((start + end) / 2))
        head = armature.matrix_world @ armature.pose.bones["Head"].matrix.to_translation()
        cam.data.ortho_scale = 0.2
        for label, direction, rotation in (("frente", Vector((0, -1, 0)), (math.pi / 2, 0, 0)),
                                           ("perfil", Vector((1, 0, 0)), (math.pi / 2, 0, math.pi / 2))):
            cam.location = head + Vector((0, 0, 0.05)) + direction * 2
            cam.rotation_euler = rotation
            scene.render.filepath = str(out / f"{clip}_{label}.png")
            bpy.ops.render.render(write_still=True)


main()

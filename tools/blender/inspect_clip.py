"""Inspeciona um clipe de animação: quadros de frente e de lado, e medidas simples de deformação.

Serve para conferir o rig automático e as animações sem abrir o jogo. Imprime a lista de clipes do
arquivo, a menor separação entre joelhos e entre pés (fração da altura; negativo = cruzou) e a
abertura lateral dos braços; salva <saida>/<clipe>_frente.png e _lado.png (4 quadros cada).

Uso:
  Blender -b --factory-startup --python tools/blender/inspect_clip.py -- <arquivo.glb> <clipe> <pasta_saida>
  (<clipe> é um trecho do nome da ação, sem diferenciar maiúsculas; "-" usa a ação ativa do arquivo)
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

FRAMES = 4
TILE = 320
LEG_BONES = ("LeftLeg", "RightLeg", "LeftFoot", "RightFoot")


def main() -> None:
    glb, clip, out = sys.argv[sys.argv.index("--") + 1:][:3]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb, disable_bone_shape=True)
    print("CLIPES", [a.name for a in bpy.data.actions])

    scene = bpy.context.scene
    scene.render.resolution_x = scene.render.resolution_y = TILE
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("fundo")
    scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sun.data.energy = 3
    sun.rotation_euler = (0.7, 0, -0.5)
    scene.collection.objects.link(sun)

    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    armature.animation_data_create()
    action = armature.animation_data.action if clip == "-" else next(
        a for a in bpy.data.actions if clip.lower() in a.name.lower())
    armature.animation_data.action = action
    if action.slots:
        armature.animation_data.action_slot = action.slots[0]

    def at(bone: str) -> Vector:
        return armature.matrix_world @ armature.pose.bones[bone].head

    start, end = action.frame_range
    # Altura de pé (pose de repouso): num clipe deitado, o primeiro quadro não serve de régua.
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    height = at("Head").z - min(at("LeftToeBase").z, at("RightToeBase").z)
    armature.data.pose_position = "POSE"
    knees, feet, arms = [], [], []
    for frame in range(int(start), int(end) + 1):
        scene.frame_set(frame)
        knees.append(at("LeftLeg").x - at("RightLeg").x)
        feet.append(at("LeftFoot").x - at("RightFoot").x)
        for side in ("Left", "Right"):
            upper = (at(f"{side}ForeArm") - at(f"{side}Arm")).normalized()
            arms.append(math.degrees(math.asin(min(1.0, abs(upper.x)))))
    sign = 1 if knees[0] > 0 else -1
    print(f"MEDIDAS {action.name}: {(end - start) / 24:.2f} s | menor separação joelhos "
          f"{min(sign * k for k in knees) / height:+.3f}, pés {min(sign * f for f in feet) / height:+.3f} "
          f"(fração da altura; < 0 = cruzou) | abertura lateral do braço média {sum(arms) / len(arms):.0f}° "
          f"máx {max(arms):.0f}°")

    # Enquadramento: caixa da malha deformada em todos os quadros amostrados (serve em pé e deitado).
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for k in range(FRAMES):
        scene.frame_set(int(start + (end - start) * k / FRAMES))
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for obj in (o for o in bpy.data.objects if o.type == "MESH"):
            mesh = obj.evaluated_get(depsgraph).to_mesh()
            points += [obj.matrix_world @ v.co for v in mesh.vertices]
            obj.evaluated_get(depsgraph).to_mesh_clear()
    low = Vector(min(p[i] for p in points) for i in range(3))
    high = Vector(max(p[i] for p in points) for i in range(3))
    center, size = (low + high) / 2, max(high - low) * 1.1

    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    for label, direction, rotation in (("frente", Vector((0, -1, 0)), (math.pi / 2, 0, 0)),
                                       ("lado", Vector((1, 0, 0)), (math.pi / 2, 0, math.pi / 2))):
        for k in range(FRAMES):
            scene.frame_set(int(start + (end - start) * k / FRAMES))
            cam.data.ortho_scale = size
            cam.location = center + direction * size * 10
            cam.rotation_euler = rotation
            scene.render.filepath = str(out / f"{action.name.replace('|', '_')}_{label}_{k}.png")
            bpy.ops.render.render(write_still=True)


main()

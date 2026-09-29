"""Passo 1: referências da protagonista v1 para as folhas do ChatGPT (Blender headless).
Pose de repouso, textura original e o cristal com a emissão do GLB (sem o reforço de 3× que o jogo aplica).
Câmera ortográfica, a mesma escala nas três vistas de corpo (frente, perfil esquerdo, costas), personagem com
~1536 px de altura num quadro de 2048; close da cabeça de frente e de lado em 1024. Luz uniforme e suave (mundo
branco + sol fraco e largo sem sombra), fundo #D9D9D9 liso (só a câmera o vê), sem texto.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/referencia_v1.py
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import ROOT, V1, eevee_scene, load_rest, mesh_objects, mesh_points, region_vertices, render, srgb_to_linear  # noqa: E402

OUT = ROOT / "assets/conceitos/protagonista_v2/referencia"
BODY_PX, BODY_FRAME = 1536, 2048
HEAD_FRAME = 1024
BG = srgb_to_linear(0xD9 / 255)


def lights(scene) -> None:
    nt = scene.world.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    lit = nodes.new("ShaderNodeBackground")
    lit.inputs["Color"].default_value = (1, 1, 1, 1)
    lit.inputs["Strength"].default_value = 0.85
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (BG, BG, BG, 1)
    bg.inputs["Strength"].default_value = 1.0
    path = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(lit.outputs[0], mix.inputs[1])
    links.new(bg.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sun.data.energy = 0.9
    sun.data.angle = math.radians(60)
    sun.data.use_shadow = False
    sun.rotation_euler = (math.radians(35), 0, math.radians(-25))
    scene.collection.objects.link(sun)


def shoot(scene, center: Vector, direction: Vector, ortho: float, size: int, path: Path) -> None:
    scene.render.resolution_x = scene.render.resolution_y = size
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    cam.data.clip_end = 100
    cam.location = center + direction.normalized() * 10
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    render(scene, path)
    bpy.data.objects.remove(cam)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scene = eevee_scene(transparent=False)
    lights(scene)
    objects = load_rest(V1)
    pts = mesh_points(objects)
    low, high = pts.min(axis=0), pts.max(axis=0)
    height = float(high[2] - low[2])
    center = Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (low[2] + high[2]) / 2))
    ortho = height * BODY_FRAME / BODY_PX
    # Olha para -Y do Blender (+Z do glTF); a esquerda dela fica em +X.
    front, left, back = Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 1, 0))
    shoot(scene, center, front, ortho, BODY_FRAME, OUT / "v1_frente.png")
    shoot(scene, center, left, ortho, BODY_FRAME, OUT / "v1_lado.png")
    shoot(scene, center, back, ortho, BODY_FRAME, OUT / "v1_costas.png")

    # Close: do osso do pescoço ao topo; em x/y, a caixa dos vértices da cabeça acima do pescoço (o cabelo longo
    # que desce pelas costas não entra no enquadramento).
    arm = next(o for o in objects if o.type == "ARMATURE")
    neck_z = (arm.matrix_world @ arm.data.bones["neck"].head_local).z
    body = mesh_objects(objects)[0]
    head = region_vertices(body, "cabeca_cabelo")
    head = head[head[:, 2] >= neck_z]
    hlow, hhigh = head.min(axis=0), head.max(axis=0)
    hc = Vector(((hlow[0] + hhigh[0]) / 2, (hlow[1] + hhigh[1]) / 2, (neck_z + high[2]) / 2))
    hsize = float(max(hhigh[0] - hlow[0], hhigh[1] - hlow[1], high[2] - neck_z)) * 1.3
    shoot(scene, hc, front, hsize, HEAD_FRAME, OUT / "v1_cabeca_frente.png")
    shoot(scene, hc, left, hsize, HEAD_FRAME, OUT / "v1_cabeca_lado.png")
    print(f"altura {height:.3f} m, ortho corpo {ortho:.4f} m, cabeça {hsize:.4f} m")


main()

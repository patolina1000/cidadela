"""Passo 2: renders da folha de diagnóstico da protagonista v1 na câmera do jogo (Blender headless).
Câmera do CameraRig.cs (perspectiva, pitch 55°, FOV vertical 45°, 16 m / zoom, 3024x1890), olhando o chão sob
o personagem, que fica de frente para ela; zooms 0,4, 1 e 2,5. Pose de repouso nas três colunas:
  a) v1 com textura, como no jogo: material do GLB (PBR), cristal com o reforço de 3× do CastellanVisual.cs;
  b) v1 sem textura: um material chapado na cor média da pele medida (v1_medidas.json), sombreado toon;
  c) aldeão v2 (aldeao_corpo.glb + cabelos/cabelo_4.glb, pele #AEBFD3, cabelo #6F7F96, retalhos do rosto no
     quadro 0 do atlas), sombreado toon.
Toon = Toon.gdshaderinc (meio-Lambert, 3 faixas, piso 0,35) + ambiente. Luz fosca, fraca e fria vinda de cima
e um pouco da frente (a mesma direção do crepúsculo das prévias do aldeão); ambiente roxo-acinzentado.
Saída: <pasta>/<coluna>_<zoom>.png com fundo transparente; a montagem é do montar_diagnostico.py.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/diagnostico_v1.py -- <pasta>
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import (ROOT, V1, eevee_scene, game_camera, hex_linear, load_rest, mesh_objects, render,  # noqa: E402
                      toon_material)

ZOOMS = (0.4, 1.0, 2.5)
ALDEAO = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
CABELO = ROOT / "assets/modelos/aldeao_v2/cabelos/cabelo_4.glb"
ROSTO = ROOT / "assets/modelos/aldeao_v2/rosto"
MEDIDAS = ROOT / "assets/previews/protagonista_v2/v1_medidas.json"
PELE_ALDEAO, CABELO_ALDEAO = "#AEBFD3", "#6F7F96"
CRYSTAL_BOOST = 3.0  # CastellanVisual.CrystalEmissionBoost

SUN_EULER = Euler((math.radians(28), 0, math.radians(-20)))  # corpo_lib.twilight_lights
SUN_RGB = tuple(c * 0.75 for c in (0.72, 0.78, 0.95))  # fria e fraca
AMBIENT_RGB = tuple(c * 0.6 for c in (0.36, 0.33, 0.44))  # roxo-acinzentado


def light_dir() -> Vector:
    """Direção para a luz (o sol do Blender ilumina ao longo do seu -Z local)."""
    return (SUN_EULER.to_matrix() @ Vector((0, 0, 1))).normalized()


def pbr_lights(scene) -> None:
    """Coluna a: o material do GLB sob a mesma luz, com sol e mundo de verdade."""
    sun = bpy.data.objects.new("crepusculo", bpy.data.lights.new("crepusculo", "SUN"))
    sun.data.energy = 1.0
    sun.data.color = SUN_RGB
    sun.data.angle = math.radians(20)
    sun.rotation_euler = SUN_EULER
    scene.collection.objects.link(sun)
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*AMBIENT_RGB, 1)
    bg.inputs["Strength"].default_value = 1.0


def dark_world(scene) -> None:
    """Colunas b e c: o toon é emissivo; o mundo não pode somar luz."""
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0


def column_a(scene) -> None:
    pbr_lights(scene)
    objects = load_rest(V1)
    for obj in mesh_objects(objects):
        for mat in obj.data.materials:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if mat.name == "Cristal" and bsdf is not None:
                bsdf.inputs["Emission Strength"].default_value *= CRYSTAL_BOOST


def column_b(scene) -> None:
    dark_world(scene)
    skin = json.loads(MEDIDAS.read_text())["cores_textura"]["pele"]["hex"]
    mat = toon_material("pele_v1", light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(skin))
    for obj in mesh_objects(load_rest(V1)):
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def column_c(scene) -> None:
    dark_world(scene)
    rosto = json.loads((ROSTO / "rosto.json").read_text())
    skin = toon_material("pele", light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(PELE_ALDEAO))
    hair = toon_material("cabelo", light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(CABELO_ALDEAO))
    patches = {}
    for key, name in (("olhos", "Olhos"), ("boca", "Boca")):
        info = rosto[key]
        img = bpy.data.images.load(str(ROSTO / f"{key}.png"))
        patches[name] = toon_material(f"rosto_{key}", light_dir(), SUN_RGB, AMBIENT_RGB, image=img,
                                      cell=(0, info["colunas"], info["linhas"]))
    for obj in mesh_objects(load_rest(ALDEAO)):
        mat = patches.get(obj.name, skin)
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    for obj in mesh_objects(load_rest(CABELO)):
        obj.data.materials.clear()
        obj.data.materials.append(hair)


COLUMNS = {"a_v1_textura": column_a, "b_v1_chapada": column_b, "c_aldeao_v2": column_c}


def main() -> None:
    out = Path(sys.argv[sys.argv.index("--") + 1])
    out.mkdir(parents=True, exist_ok=True)
    for name, build in COLUMNS.items():
        scene = eevee_scene(transparent=True)
        build(scene)
        for zoom in ZOOMS:
            cam = game_camera(scene, zoom)
            render(scene, out / f"{name}_{zoom}.png")
            bpy.data.objects.remove(cam)


main()

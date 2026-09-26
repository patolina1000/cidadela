"""Placas dos pisos construídos (GDD, seção 17, "Piso e chão"), em Blender headless.

Para cada textura do grupo "piso" em tools/texturas.json: placa de 1 x 1 m (uma célula) com 5 cm
de altura e bordas chanfradas, pivô no centro da base, textura de assets/texturas/chao/ no topo
(as laterais usam a borda da mesma textura, por projeção de cima). Se a textura tem máscara de
emissão (<nome>_emissao.png), o material brilha só nela, na cor da própria textura.
Exporta assets/modelos/pisos/<nome>.glb e, com --preview, renderiza uma grade 3x3 de cada placa
na câmera do jogo em assets/previews/piso/<nome>_placas.png.

Uso:
  Blender -b --factory-startup --python tools/blender/floor_plates.py -- [--preview]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
TEXTURES = ROOT / "assets/texturas/chao"
OUT_DIR = ROOT / "assets/modelos/pisos"
PREVIEW_DIR = ROOT / "assets/previews/piso"

SIZE = 1.0  # m: uma célula
HEIGHT = 0.05  # m
CHAMFER = 0.012  # m
ROUGHNESS = 0.9
EMISSION_STRENGTH = 3.0
GAME_TILT_DEGREES = 55  # GDD, seção 12


def build_plate(name: str) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(SIZE, SIZE, HEIGHT), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, HEIGHT / 2), verts=bm.verts)  # pivô no centro da base
    top_and_sides = [e for e in bm.edges if not all(v.co.z < 1e-6 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=top_and_sides, offset=CHAMFER, segments=1, affect="EDGES", profile=0.5)
    # A base fica embaixo do chão e não aparece: some com ela.
    bottom = [f for f in bm.faces if f.normal.z < -0.99]
    bmesh.ops.delete(bm, geom=bottom, context="FACES_ONLY")
    uv = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for loop in face.loops:
            loop[uv].uv = (loop.vert.co.x / SIZE + 0.5, loop.vert.co.y / SIZE + 0.5)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def image(path: Path) -> bpy.types.Image:
    img = bpy.data.images.load(str(path))
    img.pack()
    return img


def glow_image(name: str, base: bpy.types.Image, mask_path: Path) -> bpy.types.Image:
    """Emissão = cor da textura x máscara: as runas brilham na própria cor, o resto fica apagado."""
    mask = bpy.data.images.load(str(mask_path))
    w, h = base.size
    color = np.empty(w * h * 4, dtype=np.float32)
    base.pixels.foreach_get(color)
    alpha = np.empty(w * h * 4, dtype=np.float32)
    mask.pixels.foreach_get(alpha)
    color = color.reshape(-1, 4)
    color[:, :3] *= alpha.reshape(-1, 4)[:, :1]
    color[:, 3] = 1.0
    glow = bpy.data.images.new(f"{name}_emissao", w, h)
    glow.pixels.foreach_set(color.ravel())
    glow.pack()
    return glow


def material(name: str, has_mask: bool) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = ROUGHNESS
    base = image(TEXTURES / f"{name}.png")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = base
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if has_mask:
        glow = nodes.new("ShaderNodeTexImage")
        glow.image = glow_image(name, base, TEXTURES / f"{name}_emissao.png")
        links.new(glow.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = EMISSION_STRENGTH
    return mat


def export(obj: bpy.types.Object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True)
    print(f"  {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


def render_grid(obj: bpy.types.Object, path: Path) -> None:
    """Grade 3x3 da placa na câmera do jogo (55°), de dia; o rúnico também de noite."""
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 900, 600
    scene.view_settings.view_transform = "Standard"
    copies = []
    for x in (-1, 0, 1):
        for y in (-1, 0, 1):
            copy = obj.copy()
            copy.location = (x * SIZE, y * SIZE, 0)
            scene.collection.objects.link(copy)
            copies.append(copy)
    world = bpy.data.worlds.new("mundo")
    scene.world = world
    background = world.node_tree.nodes["Background"]
    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sun.rotation_euler = (math.radians(40), 0, math.radians(30))
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(cam)
    tilt = math.radians(GAME_TILT_DEGREES)
    cam.location = Vector((0, -math.cos(tilt), math.sin(tilt))) * 5
    cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    shots = [("dia", (0.55, 0.5, 0.45, 1), 1.0, 3.0)]
    if any(m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value > 0 for m in obj.data.materials):
        shots.append(("noite", (0.03, 0.03, 0.06, 1), 1.0, 0.05))
    for label, color, strength, energy in shots:
        background.inputs["Color"].default_value = color
        background.inputs["Strength"].default_value = strength
        sun.data.energy = energy
        out = path.with_name(f"{path.stem}_{label}.png")
        scene.render.filepath = str(out)
        bpy.ops.render.render(write_still=True)
        print(f"  {out.relative_to(ROOT)}")
    for copy in copies:
        bpy.data.objects.remove(copy)
    for thing in (sun, cam):
        bpy.data.objects.remove(thing)


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    config = json.loads((ROOT / "tools/texturas.json").read_text())
    for entry in config["texturas"]:
        if entry["grupo"] != "piso":
            continue
        name = entry["nome"]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        print(f"== {name}")
        obj = build_plate(name)
        obj.data.materials.append(material(name, (TEXTURES / f"{name}_emissao.png").exists()))
        export(obj, OUT_DIR / f"{name}.glb")
        if "--preview" in args:
            render_grid(obj, PREVIEW_DIR / f"{name}_placas.png")


main()

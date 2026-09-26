"""Padroniza um asset baixado da Meshy para o jogo (Blender em modo headless).

- escala do jogo (tools/assets.json, altura_m; 1 célula = 1 m);
- pivô no centro da base;
- frente virada para +Z do glTF (-Y no Blender), a frente de modelo do Godot;
- personagens: clipes renomeados para idle, walk, attack, work;
- texturas reduzidas para 512 px (GDD, seção 17);
- cristal_emissivo: as faces do cristal ganham o material separado "Cristal", com
  uma textura de emissão que só acende os pixels do cristal.

Uso:
  Blender -b --factory-startup --python tools/blender/normalize.py -- <nome>
"""

import json
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
TEXTURE_SIZE = 512
FOOTPRINT = 0.9  # base máxima de construções e recursos, para caber em 1 célula com folga
CRYSTAL_MATERIAL = "Cristal"
CRYSTAL_EMISSION_STRENGTH = 3.0
MATTE_ROUGHNESS = 0.8  # fosco, como textura pintada à mão
# O cristal fica no peito: faixa de altura (fração da altura total) e perto do eixo central.
CHEST_BAND = (0.50, 0.85)
CHEST_HALF_WIDTH = 0.15  # fração da altura
CRYSTAL_FACE_FRACTION = 0.10  # fração mínima de pixels de cristal para a face entrar no material


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path: Path) -> list:
    # Sem a Icosphere que o importador cria para desenhar os ossos: ela entraria nas medidas.
    bpy.ops.import_scene.gltf(filepath=str(path), disable_bone_shape=True)
    return list(bpy.context.selected_objects)


def meshes() -> list:
    return [o for o in bpy.data.objects if o.type == "MESH"]


def world_bounds() -> tuple[Vector, Vector]:
    """Caixa do modelo como é desenhado (malha deformada pelo esqueleto em pose de repouso)."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in meshes():
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        coords = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", coords)
        coords = coords.reshape(-1, 3)
        matrix = np.array(obj.matrix_world)
        points.append(coords @ matrix[:3, :3].T + matrix[:3, 3])
        evaluated.to_mesh_clear()
    allpoints = np.concatenate(points)
    return Vector(allpoints.min(axis=0)), Vector(allpoints.max(axis=0))


def add_root(name: str) -> bpy.types.Object:
    """Um nó raiz com o nome do asset segura escala e pivô sem mexer nas animações."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    for obj in list(bpy.data.objects):
        if obj is not root and obj.parent is None:
            obj.parent = root
    return root


def fit(root: bpy.types.Object, asset: dict) -> None:
    low, high = world_bounds()
    size = high - low
    scale = asset["altura_m"] / size.z
    if asset["tipo"] != "personagem":
        scale = min(scale, FOOTPRINT / max(size.x, size.y))
    root.scale = (scale, scale, scale)
    center = (low + high) / 2
    root.location = (-center.x * scale, -center.y * scale, -low.z * scale)
    bpy.context.view_layer.update()
    low, high = world_bounds()
    print(f"  tamanho final: {high.x - low.x:.2f} x {high.y - low.y:.2f} x {high.z - low.z:.2f} m")


def rename_clips(raw: Path) -> None:
    clips = {slug(k): v for k, v in json.loads((raw / "animacoes.json").read_text()).items()}
    for action in list(bpy.data.actions):
        match = next((ours for theirs, ours in clips.items() if theirs in slug(action.name)), None)
        if match is None:
            print(f"  aviso: clipe sem nome nosso: {action.name}")
            continue
        print(f"  clipe {action.name} -> {match}")
        action.name = match
        action.use_fake_user = True


def matte_materials() -> None:
    """Corrige os materiais da Meshy para o estilo pintado do jogo.

    - A Meshy liga a textura de cor na emissão: o modelo brilharia inteiro à noite.
    - Ela não informa metalicidade, e no glTF isso vale 1: no jogo, sem reflexos, o modelo fica preto.
    - O reflexo especular vem dobrado (fator 2).
    """
    for material in bpy.data.materials:
        for node in material.node_tree.nodes if material.node_tree else []:
            if node.type == "BSDF_PRINCIPLED":
                for name in ("Emission Color", "Metallic", "Roughness", "Specular Tint"):
                    for link in list(node.inputs[name].links):
                        material.node_tree.links.remove(link)
                node.inputs["Emission Color"].default_value = (0, 0, 0, 1)
                node.inputs["Emission Strength"].default_value = 0.0
                node.inputs["Metallic"].default_value = 0.0
                node.inputs["Roughness"].default_value = MATTE_ROUGHNESS
                node.inputs["Specular Tint"].default_value = (1, 1, 1, 1)


def shrink_textures() -> None:
    for image in bpy.data.images:
        if image.size[0] > TEXTURE_SIZE:
            image.scale(TEXTURE_SIZE, TEXTURE_SIZE)


def base_color_image(material: bpy.types.Material) -> bpy.types.Image | None:
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            links = node.inputs["Base Color"].links
            if links and links[0].from_node.type == "TEX_IMAGE":
                return links[0].from_node.image
    return None


def triangle_texels(corners: list, width: int, height: int) -> np.ndarray:
    """Texels (x, y) cobertos por um triângulo de UV, por amostragem baricêntrica densa."""
    a, b, c = (np.array([u % 1 * width, v % 1 * height]) for u, v in corners)
    (ux, uy), (vx, vy) = b - a, c - a
    area = abs(ux * vy - uy * vx) / 2
    steps = int(max(8, np.sqrt(area) * 2))
    i, j = np.meshgrid(np.arange(steps + 1), np.arange(steps + 1))
    keep = i + j <= steps
    wa, wb = i[keep] / steps, j[keep] / steps
    points = np.outer(wa, a) + np.outer(wb, b) + np.outer(1 - wa - wb, c)
    texels = np.unique(points.astype(int), axis=0)
    return np.clip(texels, 0, [width - 1, height - 1])


def crystal_pixels(pixels: np.ndarray) -> np.ndarray:
    """Pixels azul-saturados e claros: o cristal. A pele e o cabelo são azuis, mas pálidos."""
    r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    return (b > 0.70) & (b - r > 0.40) & (g > 0.45)


def make_crystal_material(asset_name: str) -> None:
    obj = max(meshes(), key=lambda o: len(o.data.polygons))
    mesh = obj.data
    source = mesh.materials[0]
    image = base_color_image(source)
    if image is None:
        print("  aviso: sem textura de cor; cristal não separado")
        return
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, 4)
    is_crystal = crystal_pixels(pixels)

    # Posição de cada face na pose de repouso (coordenadas do mundo). As faces são grandes
    # perto do cristal, então amostramos o interior de cada triângulo no UV, não só os vértices.
    low, high = world_bounds()
    tall = high.z - low.z
    matrix = obj.matrix_world
    uv = mesh.uv_layers.active.data
    front_y = (low.y + high.y) / 2
    mid_x = (low.x + high.x) / 2
    mesh.calc_loop_triangles()
    picked = set()
    lit = np.zeros((height, width), dtype=bool)
    for tri in mesh.loop_triangles:
        center = matrix @ tri.center
        if not (CHEST_BAND[0] <= (center.z - low.z) / tall <= CHEST_BAND[1]):
            continue
        if abs(center.x - mid_x) > CHEST_HALF_WIDTH * tall or center.y > front_y:
            continue
        texels = triangle_texels([uv[l].uv for l in tri.loops], width, height)
        hits = is_crystal[texels[:, 1], texels[:, 0]]
        if hits.mean() >= CRYSTAL_FACE_FRACTION:
            picked.add(tri.polygon_index)
            lit[texels[hits, 1], texels[hits, 0]] = True
    if not picked:
        print("  aviso: nenhuma face do cristal encontrada no peito")
        return

    # Emissão: só os pixels do cristal dentro das faces escolhidas.
    emission = np.zeros_like(pixels)
    emission[..., 3] = 1.0
    emission[lit, :3] = pixels[lit, :3]
    glow = bpy.data.images.new(f"{asset_name}_cristal_emissao", width, height)
    glow.pixels.foreach_set(emission.ravel())
    glow.pack()

    crystal = source.copy()
    crystal.name = CRYSTAL_MATERIAL
    nodes, links = crystal.node_tree.nodes, crystal.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = glow
    links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = CRYSTAL_EMISSION_STRENGTH
    mesh.materials.append(crystal)
    slot = len(mesh.materials) - 1
    for index in picked:
        mesh.polygons[index].material_index = slot
    print(f"  cristal: {len(picked)} faces, {int(lit.sum())} pixels emissivos")


def export(root: bpy.types.Object, path: Path, animated: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        export_yup=True,
        export_animations=animated,
        export_animation_mode="ACTIONS",
    )
    print(f"  exportado {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


def main() -> None:
    name = sys.argv[sys.argv.index("--") + 1]
    config = json.loads((ROOT / "tools/assets.json").read_text())
    asset = next(a for a in config["assets"] if a["nome"] == name)
    folder = ROOT / "assets/modelos" / name
    raw = folder / "bruto"
    character = asset["tipo"] == "personagem"
    print(f"== {name}")

    reset_scene()
    import_glb(raw / ("animacoes.glb" if character else "modelo.glb"))
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"  # medidas e cristal na pose de repouso
    bpy.context.view_layer.update()

    matte_materials()
    if character:
        rename_clips(raw)
    if asset.get("cristal_emissivo"):
        make_crystal_material(name)
    shrink_textures()
    root = add_root(name)
    fit(root, asset)
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "POSE"
    export(root, folder / f"{name}.glb", animated=character)


main()

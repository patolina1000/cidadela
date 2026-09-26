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
import math
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
TEXTURE_SIZE = 512
FOOTPRINT = 0.9  # base máxima de construções e recursos, para caber em 1 célula com folga
CRYSTAL_MATERIAL = "Cristal"
CRYSTAL_EMISSION_STRENGTH = 3.0
STRIDE_BONES = ("LeftToeBase", "RightToeBase")
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


def use_rig_clip(raw: Path, clip: str, file: str) -> None:
    """Usa um clipe grátis que veio com o rig (mesmos ossos) como <clip>, trocando o que houver."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(raw / file), disable_bone_shape=True)
    imported = [o for o in bpy.data.objects if o not in before]
    source = next(o for o in imported if o.type == "ARMATURE")
    action = source.animation_data.action
    for obj in imported:
        bpy.data.objects.remove(obj)
    if clip in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[clip])
    action.name = clip
    action.use_fake_user = True
    print(f"  {clip}: clipe do rig ({file})")


def close_arms(clip: str, degrees: float) -> None:
    """Gira os ombros para baixo, em volta do eixo frente-trás, em todos os quadros do clipe."""
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    armature.data.pose_position = "POSE"
    armature.animation_data_create()
    action = bpy.data.actions[clip]
    armature.animation_data.action = action
    if action.slots:
        armature.animation_data.action_slot = action.slots[0]
    scene = bpy.context.scene
    # Eixo frente-trás do mundo, no espaço do esqueleto (onde vivem as matrizes dos ossos).
    axis = (armature.matrix_world.inverted().to_3x3() @ Vector((0, 1, 0))).normalized()
    for side in ("Left", "Right"):
        bone = armature.pose.bones[f"{side}Arm"]
        bone.rotation_mode = "QUATERNION"
        path = f'pose.bones["{bone.name}"].rotation_quaternion'
        curves = [c for bag in channelbags(action) for c in bag.fcurves if c.data_path == path]
        # As chaves podem estar em tempos fracionados (a caminhada do rig começa em 0,8):
        # regravar nos mesmos tempos, senão a curva alterna entre chave corrigida e original.
        times = sorted({k.co.x for c in curves for k in c.keyframe_points})
        original = {}
        for time in times:
            set_time(scene, time)
            original[time] = bone.matrix.copy()
        # O sinal que abaixa a mão depende do lado: testa na primeira chave.
        set_time(scene, times[0])
        best = None
        for sign in (1, -1):
            turned = rotate_about_head(original[times[0]], axis, sign * math.radians(degrees))
            tail_z = (armature.matrix_world @ (turned @ Vector((0, bone.bone.length, 0)))).z
            if best is None or tail_z < best[1]:
                best = (sign, tail_z)
        angle = best[0] * math.radians(degrees)
        corrected = {}
        for time in times:
            set_time(scene, time)
            bone.matrix = rotate_about_head(original[time], axis, angle)
            bpy.context.view_layer.update()
            corrected[time] = bone.rotation_quaternion.copy()
        for curve in curves:
            index = curve.array_index
            curve.keyframe_points.clear()
            for time in times:
                curve.keyframe_points.insert(time, corrected[time][index], options={"FAST"})
    armature.animation_data.action = None
    armature.data.pose_position = "REST"
    scene.frame_set(0)
    print(f"  braços fechados em {degrees:g}° no {clip}")


def channelbags(action: bpy.types.Action) -> list:
    return [bag for layer in action.layers for strip in layer.strips for bag in strip.channelbags]


def set_time(scene: bpy.types.Scene, time: float) -> None:
    scene.frame_set(int(math.floor(time)), subframe=time - math.floor(time))


def rotate_about_head(matrix: Matrix, axis: Vector, angle: float) -> Matrix:
    head = matrix.to_translation()
    return (Matrix.Translation(head) @ Matrix.Rotation(angle, 4, axis)
            @ Matrix.Translation(-head) @ matrix)


def remove_bone_scale_tracks() -> None:
    """Ossos não mudam de tamanho. O idle 0 da Meshy escala o quadril em 1,176, e a personagem
    parecia encolher ao sair do idle para o walk."""
    for action in bpy.data.actions:
        for bag in channelbags(action):
            for curve in [c for c in bag.fcurves if c.data_path.endswith(".scale")]:
                bag.fcurves.remove(curve)


def measure_stride(clip: str) -> float:
    """Velocidade (m/s, já na escala do jogo) com que o pé de apoio recua no clipe feito no lugar.

    É a velocidade de chão em que a animação não desliza.
    """
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    armature.data.pose_position = "POSE"
    armature.animation_data_create()
    action = bpy.data.actions[clip]
    armature.animation_data.action = action
    if action.slots:
        armature.animation_data.action_slot = action.slots[0]
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    start, end = (int(f) for f in action.frame_range)
    track = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        track.append({b: (armature.matrix_world @ armature.pose.bones[b].head).copy() for b in STRIDE_BONES})
    # A frente é -Y: no apoio o pé recua devagar (+Y); no ar ele avança rápido (-Y).
    # Altura não serve para achar o apoio, porque o dedo sobe quando o calcanhar levanta.
    speeds = [
        (now[b].y - before[b].y) * fps
        for before, now in zip(track, track[1:])
        for b in STRIDE_BONES
        if now[b].y > before[b].y
    ]
    armature.animation_data.action = None
    armature.data.pose_position = "REST"
    scene.frame_set(0)
    return float(np.median(speeds))  # mediana: ignora os picos na virada do passo


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
        for clip, file in asset.get("clipes_do_rig", {}).items():
            use_rig_clip(raw, clip, file)
        remove_bone_scale_tracks()
        for clip, degrees in asset.get("fechar_bracos_graus", {}).items():
            close_arms(clip, degrees)
    if asset.get("cristal_emissivo"):
        make_crystal_material(name)
    shrink_textures()
    root = add_root(name)
    fit(root, asset)
    if character:
        # O jogo lê isto para tocar walk e run no ritmo da velocidade real, sem deslizar.
        info = {}
        for clip in ("walk", "run"):
            if clip in bpy.data.actions:
                stride = measure_stride(clip)
                info[f"passada_{clip}_m_s"] = round(stride, 3)
                print(f"  passada do {clip}: {stride:.3f} m/s")
        (folder / f"{name}.json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n")
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "POSE"
    export(root, folder / f"{name}.glb", animated=character)


main()

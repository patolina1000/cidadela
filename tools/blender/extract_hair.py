"""Recorta o cabelo de uma variação do aldeão e o encaixa na cabeça do corpo-base careca.

Nada é gerado: o cabelo sai da malha já padronizada da variação (assets/modelos/aldeao_<var>/).
1. Malha em pose de repouso, com a textura: cada face ganha o brilho médio da textura nela.
2. Cabelo = faces escuras (limite de Otsu entre pele clara e cabelo escuro, só na cabeça). A semente é o
   cabelo acima do pescoço; dela cresce pelas faces escuras vizinhas (franja e rabo que descem entram;
   pupilas e contornos dos olhos, soltos, ficam de fora). Ilhas pequenas saem; buracos pequenos fecham.
3. Alinhamento: a base (osso Head) e o topo (head_end) da cabeça da variação vão para os do corpo-base;
   uma folga (FOLGA) afasta o cabelo do couro cabeludo.
4. Exporta assets/modelos/aldeao_cabelos/<var>.glb com a origem no encaixe "Cabelo" do corpo-base
   (posição em aldeao_base.json): no jogo, o cabelo vira filho desse nó, sem ajuste.

Uso:
  Blender -b --factory-startup --python tools/blender/extract_hair.py -- <var> [<var> ...]
"""

import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = "aldeao_base"
OUT_DIR = ROOT / "assets/modelos/aldeao_cabelos"
FOLGA = 1.03  # o cabelo cresce 3% em volta do centro da cabeça para não afundar no couro cabeludo
MIN_ISLAND = 0.02  # ilhas com menos que isso das faces do cabelo são descartadas
MAX_HOLE_SIDES = 12  # buracos com até tantas arestas são fechados (a abertura de baixo fica)
SAMPLES = 6  # amostras por face na textura
DESCIDA = 1.5  # abaixo do pescoço, o cabelo desce no máximo isso da altura da cabeça (rabo e pontas longas)
FECHAMENTO = 3  # passos do fechamento que preenche reflexos claros no meio do cabelo
# Rosto protegido do fechamento (frações da altura da cabeça): profundidade a partir da frente,
# meia largura e altura acima do pescoço.
FACE_DEPTH, FACE_HALF_WIDTH, FACE_TOP = 0.35, 0.32, 0.62
SCALP_MARGIN = 0.002  # m: o cabelo fica pelo menos isso fora do couro cabeludo do corpo-base


def load(name: str) -> bpy.types.Object:
    """Importa o GLB padronizado e devolve o esqueleto, em pose de repouso."""
    bpy.ops.import_scene.gltf(filepath=str(ROOT / "assets/modelos" / name / f"{name}.glb"), disable_bone_shape=True)
    armature = next(o for o in bpy.context.selected_objects if o.type == "ARMATURE")
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    return armature


def head_frame(armature: bpy.types.Object) -> tuple[Vector, Vector]:
    """Base (osso Head, altura do pescoço) e topo (head_end) da cabeça, no mundo."""
    bones = armature.pose.bones
    return armature.matrix_world @ bones["Head"].head, armature.matrix_world @ bones["head_end"].head


def rest_copy(armature: bpy.types.Object) -> bpy.types.Object:
    """Cópia estática da malha na pose de repouso, em coordenadas do mundo, com UV e materiais."""
    source = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == armature)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), depsgraph=depsgraph)
    mesh.transform(source.matrix_world)
    copy = bpy.data.objects.new("cabelo", mesh)
    bpy.context.scene.collection.objects.link(copy)
    return copy


def face_colors(obj: bpy.types.Object) -> tuple[np.ndarray, np.ndarray]:
    """Brilho e saturação médios da textura em cada face (amostras espalhadas dentro da face)."""
    mesh = obj.data
    image = next(n.image for m in mesh.materials for n in m.node_tree.nodes if n.type == "TEX_IMAGE")
    w, h = image.size
    pixels = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    rgb = pixels.reshape(h, w, 4)[..., :3]
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    high, low = rgb.max(axis=-1), rgb.min(axis=-1)
    sat = np.where(high > 0, (high - low) / np.maximum(high, 1e-6), 0)
    uv = mesh.uv_layers.active.data
    rng = np.random.default_rng(0)
    weights = rng.dirichlet(np.ones(3), SAMPLES)
    mesh.calc_loop_triangles()
    per_face = np.zeros(len(mesh.polygons))
    per_face_sat = np.zeros(len(mesh.polygons))
    count = np.zeros(len(mesh.polygons))
    for tri in mesh.loop_triangles:
        corners = np.array([uv[l].uv[:] for l in tri.loops])
        for wgt in weights:
            u, v = (wgt @ corners) % 1.0
            y, x = min(int(v * h), h - 1), min(int(u * w), w - 1)
            per_face[tri.polygon_index] += lum[y, x]
            per_face_sat[tri.polygon_index] += sat[y, x]
            count[tri.polygon_index] += 1
    return per_face / np.maximum(count, 1), per_face_sat / np.maximum(count, 1)


def otsu(values: np.ndarray) -> float:
    hist, edges = np.histogram(values, bins=64)
    centers = (edges[:-1] + edges[1:]) / 2
    best, threshold = -1.0, centers[len(centers) // 2]
    for i in range(1, len(hist)):
        w0, w1 = hist[:i].sum(), hist[i:].sum()
        if w0 == 0 or w1 == 0:
            continue
        m0 = (hist[:i] * centers[:i]).sum() / w0
        m1 = (hist[i:] * centers[i:]).sum() / w1
        between = w0 * w1 * (m0 - m1) ** 2
        if between > best:
            best, threshold = between, centers[i]
    return float(threshold)


def select_hair(obj: bpy.types.Object, neck_z: float, head_height: float) -> set:
    """Faces do cabelo: escuras e saturadas (o cabelo é mais escuro e mais saturado que a pele; a pele
    sombreada do corpo é escura mas pouco saturada), crescendo a partir das de cima do pescoço e
    descendo no máximo DESCIDA da altura da cabeça abaixo dele (rabo e pontas; não entra no tronco)."""
    mesh = obj.data
    brightness, saturation = face_colors(obj)
    centers = np.array([p.center[:] for p in mesh.polygons])
    head = centers[:, 2] > neck_z
    threshold = otsu(brightness[head])
    darker = brightness < threshold
    # Saturação: metade do caminho entre a pele (faces claras da cabeça) e o cabelo (escuras).
    sat_threshold = (np.median(saturation[head & darker]) + np.median(saturation[head & ~darker])) / 2
    reach = centers[:, 2] > neck_z - DESCIDA * head_height
    dark = darker & (saturation > sat_threshold) & reach
    # Vizinhança pela posição dos vértices: o glTF duplica vértices em cada costura de UV, e as
    # faces não compartilham arestas na malha.
    coords = [tuple(round(c, 6) for c in v.co) for v in mesh.vertices]
    by_edge: dict = {}
    for poly in mesh.polygons:
        keys = [coords[i] for i in poly.vertices]
        for a, b in zip(keys, keys[1:] + keys[:1]):
            by_edge.setdefault(frozenset((a, b)), []).append(poly.index)
    neighbors = [[] for _ in mesh.polygons]
    for faces in by_edge.values():
        for f in faces:
            neighbors[f].extend(x for x in faces if x != f)
    seed = {i for i in range(len(mesh.polygons)) if dark[i] and head[i]}
    # Crescimento pelas faces escuras vizinhas, a partir do cabelo acima do pescoço.
    components, seen = [], set()
    for start in seed:
        if start in seen:
            continue
        stack, component = [start], set()
        seen.add(start)
        while stack:
            face = stack.pop()
            component.add(face)
            for other in neighbors[face]:
                if other not in seen and dark[other]:
                    seen.add(other)
                    stack.append(other)
        components.append(component)
    total = sum(len(c) for c in components)
    hair = set().union(*[c for c in components if len(c) >= MIN_ISLAND * total])
    # Fechamento: cresce e depois encolhe FECHAMENTO passos pela vizinhança, dentro da cabeça e fora
    # do rosto. Preenche mechas claras (reflexos) cercadas de cabelo sem avançar sobre a pele aberta.
    center_x = centers[head][:, 0].mean()
    front_y = centers[head][:, 1].min()
    face = ((centers[:, 1] < front_y + FACE_DEPTH * head_height)
            & (np.abs(centers[:, 0] - center_x) < FACE_HALF_WIDTH * head_height)
            & (centers[:, 2] < neck_z + FACE_TOP * head_height))
    allowed = reach & ~face
    closed = set(hair)
    for _ in range(FECHAMENTO):
        closed |= {n for f in closed for n in neighbors[f] if allowed[n]}
    for _ in range(FECHAMENTO):
        closed = {f for f in closed if all(n in closed for n in neighbors[f]) or f in hair}
    print(f"  fechamento: {len(closed) - len(hair)} faces de reflexo incluídas")
    hair = closed
    print(f"  limites: brilho < {threshold:.2f}, saturação > {sat_threshold:.2f}; {len(components)} regiões, "
          f"{len(hair)} faces de cabelo de {len(mesh.polygons)}")
    return hair


def keep_faces(obj: bpy.types.Object, faces: set) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in faces], context="FACES")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # Fecha buracos pequenos (falhas entre faces); a abertura grande de baixo assenta na cabeça.
    boundary = [e for e in bm.edges if e.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=boundary, sides=MAX_HOLE_SIDES)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    print(f"  {len(filled['faces'])} buracos pequenos fechados")


def push_outside(hair: bpy.types.Object, base_armature: bpy.types.Object, center: Vector, anchor: Vector) -> None:
    """Todo vértice do cabelo que cai dentro (ou colado) da cabeça do corpo-base vai para a superfície
    dela mais SCALP_MARGIN, na direção do centro da cabeça; o resto não muda. Sem isso a cabeça careca,
    de formato um pouco diferente, atravessa o cabelo."""
    from mathutils.bvhtree import BVHTree
    source = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == base_armature)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), depsgraph=depsgraph)
    mesh.transform(source.matrix_world)
    tree = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [p.vertices[:] for p in mesh.polygons])
    bpy.data.meshes.remove(mesh)
    moved = 0
    for v in hair.data.vertices:
        world = v.co + anchor
        direction = (world - center).normalized()
        hit = tree.ray_cast(center, direction)
        if hit[0] is None:
            continue
        surface = (hit[0] - center).length + SCALP_MARGIN
        if (world - center).length < surface:
            v.co = center + direction * surface - anchor
            moved += 1
    print(f"  {moved} vértices empurrados para fora do couro cabeludo")


def main() -> None:
    variants = sys.argv[sys.argv.index("--") + 1:]
    base_info = json.loads((ROOT / "assets/modelos" / BASE / f"{BASE}.json").read_text())
    gx, gy, gz = base_info["encaixes"]["Cabelo"]
    anchor = Vector((gx, -gz, gy))  # glTF (Y para cima) -> Blender (Z para cima)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for variant in variants:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        base_armature = load(BASE)
        base_low, base_top = head_frame(base_armature)
        armature = load(f"aldeao_{variant}")
        low, top = head_frame(armature)
        hair = rest_copy(armature)
        print(f"== {variant}")
        keep_faces(hair, select_hair(hair, low.z, top.z - low.z))
        # Cabeça da variação -> cabeça do corpo-base, com folga em volta do centro da cabeça.
        scale = (base_top.z - base_low.z) / (top.z - low.z)
        center = (base_low + base_top) / 2
        for v in hair.data.vertices:
            p = base_low + (v.co - low) * scale
            v.co = center + (p - center) * FOLGA - anchor
        push_outside(hair, base_armature, center, anchor)
        for material in hair.data.materials:
            material.use_backface_culling = False
        for obj in list(bpy.data.objects):
            if obj is not hair:
                bpy.data.objects.remove(obj)
        hair.name = f"cabelo_{variant}"
        path = OUT_DIR / f"{variant}.glb"
        bpy.ops.object.select_all(action="DESELECT")
        hair.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True)
        print(f"  {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB, {len(hair.data.polygons)} faces)")


main()

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
MAX_PUSH = 0.012  # m: um vértice nunca é empurrado mais que isso (senão é um erro de raio)
WELD = 2e-4  # m: vértices mais próximos que isso viram um só (costuras de UV do glTF)
LOOSE_PIECE = 0.03  # pedaços soltos com menos que isso das faces do cabelo saem
SLIVER = 80.0  # só lascas extremas (mechas são triângulos finos de propósito; 12 tirava cabelo)
TIP_SMOOTH = 3  # passadas de suavização nas bordas (pontas)
# Touca (frações da altura da cabeça): começa CAP_BOTTOM acima da base; rosto e orelhas ficam de fora
# abaixo da linha do cabelo (CAP_HAIRLINE); afastada CAP_OFFSET do couro cabeludo, um pouco mais escura.
CAP_BOTTOM, CAP_HAIRLINE, CAP_FACE_DEPTH, CAP_EAR_X = 0.1, 0.72, 0.45, 0.42
CAP_OFFSET = 0.0015  # m
CAP_SHADE = 0.75


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


def push_outside(hair: bpy.types.Object, base_armature: bpy.types.Object, center: Vector, anchor: Vector,
                 head_radius: float, neck_z: float) -> None:
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
        # Só couro cabeludo: raio que sai pelo pescoço acertaria o ombro e puxaria o vértice até lá
        # (eram os triângulos compridos na nuca).
        if hit[0] is None or (hit[0] - center).length > head_radius * 1.3 or hit[0].z < neck_z:
            continue
        surface = (hit[0] - center).length + SCALP_MARGIN
        if surface - (world - center).length > MAX_PUSH:
            continue
        if (world - center).length < surface:
            v.co = center + direction * surface - anchor
            moved += 1
    print(f"  {moved} vértices empurrados para fora do couro cabeludo")


def clean_hair(hair: bpy.types.Object) -> None:
    """Limpa o cabelo recortado: solda costuras, tira pedaços soltos e pontas quebradas (triângulos
    finos demais), suaviza as bordas, fecha todos os buracos (inclusive a abertura de baixo, que
    encostava na cabeça) e recalcula as normais para fora."""
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=WELD)
    # Pontas quebradas: triângulos muito finos e compridos.
    slivers = []
    for f in bm.faces:
        edges = [e.calc_length() for e in f.edges]
        longest = max(edges)
        if longest > 0 and f.calc_area() > 0:
            height = 2 * f.calc_area() / longest
            if longest / max(height, 1e-9) > SLIVER:
                slivers.append(f)
    bmesh.ops.delete(bm, geom=slivers, context="FACES")
    # Pedaços soltos.
    pieces, seen = [], set()
    for f in bm.faces:
        if f in seen:
            continue
        piece, stack = [], [f]
        seen.add(f)
        while stack:
            face = stack.pop()
            piece.append(face)
            for e in face.edges:
                for other in e.link_faces:
                    if other not in seen:
                        seen.add(other)
                        stack.append(other)
        pieces.append(piece)
    total = sum(len(p) for p in pieces)
    loose = [f for p in pieces if len(p) < LOOSE_PIECE * total for f in p]
    bmesh.ops.delete(bm, geom=loose, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # Bordas (pontas): suaviza para tirar o serrilhado antes de fechar.
    rim = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
    for _ in range(TIP_SMOOTH):
        bmesh.ops.smooth_vert(bm, verts=rim, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    holes = len({e for e in bm.edges if e.is_boundary})
    filled = bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)["faces"]
    bmesh.ops.triangulate(bm, faces=filled, quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    left = len([e for e in bm.edges if e.is_boundary])
    bm.to_mesh(hair.data)
    bm.free()
    print(f"  limpeza: {len(slivers)} pontas finas e {len(loose)} faces soltas removidas; "
          f"{len(filled)} tampas em {holes} arestas de borda; sobram {left} arestas abertas")


def mean_hair_color(obj: bpy.types.Object) -> tuple:
    """Cor média do cabelo (média da textura nos cantos das faces que sobraram)."""
    mesh = obj.data
    image = next(n.image for m in mesh.materials for n in m.node_tree.nodes if n.type == "TEX_IMAGE")
    w, h = image.size
    pixels = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(h, w, 4)
    uv = mesh.uv_layers.active.data
    samples = [pixels[min(int((uv[l].uv[1] % 1) * h), h - 1), min(int((uv[l].uv[0] % 1) * w), w - 1), :3]
               for p in mesh.polygons for l in p.loop_indices]
    srgb = np.median(np.array(samples), axis=0)
    # Os pixels da textura estão em sRGB; a cor do material é linear.
    return tuple(np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4))


def add_scalp_cap(hair: bpy.types.Object, base_armature: bpy.types.Object, anchor: Vector,
                  low: Vector, top: Vector, color: tuple) -> None:
    """Touca: o couro cabeludo do corpo-base (sem o rosto e sem as orelhas), afastado CAP_OFFSET, na cor
    do cabelo. Fica por baixo das mechas: buracos do cabelo gerado mostram cabelo, não pele."""
    source = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == base_armature)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), depsgraph=depsgraph)
    mesh.transform(source.matrix_world)
    height = top.z - low.z
    front_y = min(v.co.y for v in mesh.vertices if v.co.z > low.z)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    keep = set()
    for f in bm.faces:
        c = f.calc_center_median()
        if c.z < low.z + CAP_BOTTOM * height:
            continue
        # Rosto (frente, abaixo da linha do cabelo) e orelhas (lados, meia altura) ficam de fora.
        face = c.y < front_y + CAP_FACE_DEPTH * height and c.z < low.z + CAP_HAIRLINE * height
        ear = abs(c.x - low.x) > CAP_EAR_X * height and c.z < low.z + CAP_HAIRLINE * height
        if not face and not ear:
            keep.add(f)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=WELD)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * CAP_OFFSET - anchor
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    material = bpy.data.materials.new("touca")
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*[c * CAP_SHADE for c in color], 1)
    bsdf.inputs["Roughness"].default_value = 0.8
    material.use_backface_culling = False
    mesh.materials.clear()
    mesh.materials.append(material)
    cap = bpy.data.objects.new("touca", mesh)
    bpy.context.scene.collection.objects.link(cap)
    # Junta a touca ao cabelo (um objeto só, dois materiais).
    bpy.ops.object.select_all(action="DESELECT")
    cap.select_set(True)
    hair.select_set(True)
    bpy.context.view_layer.objects.active = hair
    bpy.ops.object.join()
    print(f"  touca: {len(mesh.polygons)} faces na cor do cabelo")


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
        push_outside(hair, base_armature, center, anchor, (base_top - base_low).length * 0.6, base_low.z)
        clean_hair(hair)
        add_scalp_cap(hair, base_armature, anchor, base_low, base_top, mean_hair_color(hair))
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

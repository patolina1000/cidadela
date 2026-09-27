"""Encaixa as perucas geradas na Meshy (hair_pieces.py) na cabeça do corpo-base do aldeão.

1. Escala a peruca para LARGURA x a largura da cabeça e põe o topo dela TOPO acima do topo da cabeça,
   centrada em x e com o meio da profundidade no meio da cabeça.
2. Abertura do rosto: toda face na frente da cabeça cujo centro cai dentro da oval da máscara "Rosto"
   (ampliada por FOLGA_ROSTO) sai: nenhum fio fica na frente dos olhos nem cobre a máscara.
3. Nenhum vértice fica dentro do couro cabeludo: os que caem dentro vão para fora (+MARGEM), só na cabeça.
4. Fecha buracos pequenos, recalcula normais, material com as duas faces visíveis.
Exporta assets/modelos/aldeao_cabelos/<var>.glb com a origem no encaixe "Cabelo" (aldeao_base.json).

Uso:
  Blender -b --factory-startup --python tools/blender/fit_hair.py -- <var> [<var> ...]
"""

import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = "aldeao_base"
HAIRS = ROOT / "assets/modelos/aldeao_cabelos"
LARGURA = 1.12  # largura da coroa da peruca / largura da cabeça na mesma faixa
CORA = (0.12, 0.22)  # faixa da coroa, em fração da altura a partir do topo
TOPO = 0.006  # m acima do topo da cabeça
FOLGA_ROSTO = 1.08  # a abertura do rosto é a oval da máscara ampliada nisso
MARGEM = 0.002  # m fora do couro cabeludo
MAX_PUSH = 0.08  # m: o raio que sai pelo pescoço já é barrado; a nuca redonda do corpo-base engolia até 5 cm
MAX_HOLE_SIDES = 16
INFLA_PASSO = 10  # graus entre as direções do campo de inflar
PERTO = 0.025  # m: camada da peruca até isso fora da pele é a que encosta na cabeça
TOUCA_AFASTAMENTO = 0.0008  # m (abaixo do cabelo, que fica a 2 mm)
TOUCA_SOMBRA = 0.75


def base_head() -> dict:
    """Medidas da cabeça do corpo-base em pose de repouso (mundo do Blender = espaço do modelo)."""
    bpy.ops.import_scene.gltf(filepath=str(ROOT / "assets/modelos" / BASE / f"{BASE}.glb"), disable_bone_shape=True)
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    def world_points(obj):
        mesh = obj.evaluated_get(depsgraph).to_mesh()
        pts = [obj.matrix_world @ v.co for v in mesh.vertices]
        polys = [p.vertices[:] for p in mesh.polygons]
        obj.evaluated_get(depsgraph).to_mesh_clear()
        return pts, polys

    mask = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Rosto"))
    body = next(o for o in bpy.data.objects if o.type == "MESH" and o is not mask)
    body_pts, body_polys = world_points(body)
    mask_pts, _ = world_points(mask)
    neck = armature.matrix_world @ armature.pose.bones["Head"].head
    top = max(p.z for p in body_pts)
    head = [p for p in body_pts if p.z > neck.z]
    mid_z = (neck.z + top) / 2
    ring = [p for p in head if abs(p.z - mid_z) < (top - neck.z) * 0.08]
    crown_band = [p.x for p in head if top - CORA[1] * (top - neck.z) < p.z < top - CORA[0] * (top - neck.z)]
    info = {
        "neck_z": neck.z, "top": top, "crown": max(crown_band) - min(crown_band),
        "width": max(p.x for p in ring) - min(p.x for p in ring),
        "center": Vector((sum(p.x for p in ring) / len(ring), sum(p.y for p in ring) / len(ring), mid_z)),
        "mask_min": Vector([min(p[i] for p in mask_pts) for i in range(3)]),
        "mask_max": Vector([max(p[i] for p in mask_pts) for i in range(3)]),
        "tree": BVHTree.FromPolygons(body_pts, body_polys),
        "body_pts": body_pts, "body_polys": body_polys,
    }
    gx, gy, gz = json.loads((ROOT / "assets/modelos" / BASE / f"{BASE}.json").read_text())["encaixes"]["Cabelo"]
    info["anchor"] = Vector((gx, -gz, gy))  # glTF -> Blender
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    return info


def hair_color(mesh: bpy.types.Mesh) -> tuple:
    """Cor mediana da textura do cabelo, em linear (os pixels vêm em sRGB)."""
    import numpy as np
    image = next(n.image for m in mesh.materials for n in m.node_tree.nodes if n.type == "TEX_IMAGE")
    w, h = image.size
    pixels = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(h, w, 4)
    uv = mesh.uv_layers.active.data
    samples = np.array([pixels[min(int((uv[l].uv[1] % 1) * h), h - 1), min(int((uv[l].uv[0] % 1) * w), w - 1), :3]
                        for p in mesh.polygons for l in p.loop_indices])
    srgb = np.median(samples, axis=0)
    return tuple(np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4) * TOUCA_SOMBRA)


def scalp_cap(head: dict, color: tuple) -> bpy.types.Object:
    """Touca por baixo da peruca: couro cabeludo do corpo-base fora da abertura do rosto e das orelhas,
    TOUCA_AFASTAMENTO para fora, na cor do cabelo. As frestas entre as mechas mostram cabelo, não pele."""
    lo, hi = head["mask_min"], head["mask_max"]
    cx, cz = (lo.x + hi.x) / 2, (lo.z + hi.z) / 2
    rx, rz = (hi.x - lo.x) / 2 * FOLGA_ROSTO, (hi.z - lo.z) / 2 * FOLGA_ROSTO
    height = head["top"] - head["neck_z"]
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in head["body_pts"]]
    for poly in head["body_polys"]:
        try:
            bm.faces.new([verts[i] for i in poly])
        except ValueError:
            pass
    keep = []
    for f in bm.faces:
        c = f.calc_center_median()
        if c.z < head["neck_z"] + 0.1 * height:
            continue
        face = c.y < head["center"].y and ((c.x - cx) / rx) ** 2 + ((c.z - cz) / rz) ** 2 < 1
        ear = abs(c.x - head["center"].x) > 0.42 * height and c.z < head["neck_z"] + 0.72 * height
        if not face and not ear:
            keep.append(f)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * TOUCA_AFASTAMENTO
    mesh = bpy.data.meshes.new("touca")
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    material = bpy.data.materials.new("touca")
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = 0.8
    material.use_backface_culling = False
    mesh.materials.append(material)
    cap = bpy.data.objects.new("touca", mesh)
    bpy.context.scene.collection.objects.link(cap)
    return cap


def inflate(bm: bmesh.types.BMesh, head: dict) -> int:
    import numpy as np
    center = head["center"]
    points = np.array([v.co[:] for v in bm.verts]) - np.array(center[:])
    radius = np.linalg.norm(points, axis=1)
    dirs = points / np.maximum(radius[:, None], 1e-9)
    az = np.degrees(np.arctan2(dirs[:, 0], dirs[:, 1])) % 360
    el = np.degrees(np.arcsin(np.clip(dirs[:, 2], -1, 1)))
    step = INFLA_PASSO
    n_az, n_el = int(360 / step), int(180 / step)
    ia = (az / step).astype(int) % n_az
    ie = np.clip(((el + 90) / step).astype(int), 0, n_el - 1)
    need = np.zeros((n_el, n_az))
    surface_at = np.zeros((n_el, n_az))
    for e in range(n_el):
        for a in range(n_az):
            elev = np.radians(-90 + (e + 0.5) * step)
            azim = np.radians((a + 0.5) * step)
            d = Vector((np.sin(azim) * np.cos(elev), np.cos(azim) * np.cos(elev), np.sin(elev)))
            hit, _, _, _ = head["tree"].ray_cast(center, d)
            if hit is None or hit.z < head["neck_z"]:
                continue
            surface = (hit - center).length + MARGEM
            surface_at[e, a] = surface
            # Só a camada perto da cabeça conta: mechas penduradas longe (cortina do cabelo comprido) na
            # mesma direção não podem esconder a camada colada à nuca, que está por dentro.
            near = (ia == a) & (ie == e) & (radius < surface + PERTO)
            if not near.any():
                continue
            need[e, a] = max(0.0, min(surface - radius[near].max(), MAX_PUSH))
    # Suaviza o campo (sem degraus entre direções vizinhas), sem baixar os picos.
    for _ in range(2):
        smooth = (need + np.roll(need, 1, 1) + np.roll(need, -1, 1)
                  + np.vstack([need[:1], need[:-1]]) + np.vstack([need[1:], need[-1:]])) / 5
        need = np.maximum(need, smooth)
    shift = need[ie, ia]
    # A cortina longe da cabeça não anda; perto dela, anda tudo; entre os dois, transição suave.
    gap = radius - surface_at[ie, ia]
    fade = np.clip(1 - (gap - PERTO) / PERTO, 0, 1)
    shift = shift * np.where(surface_at[ie, ia] > 0, fade, 0)
    for v, delta, direction in zip(bm.verts, shift, dirs):
        if delta > 0:
            v.co += Vector(direction) * float(delta)
    return int((shift > 0).sum())


def texture_cap_from_hair(cap: bpy.types.Object, hair: bpy.types.Object) -> None:
    """A touca usa o material do cabelo: cada vértice pega a UV do ponto mais próximo da peruca. Nas
    frestas e nos buracos do cabelo gerado aparecem fios, não uma superfície lisa."""
    from mathutils.geometry import barycentric_transform
    mesh = hair.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    tris = list(mesh.loop_triangles)
    tree = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [t.vertices[:] for t in tris])
    cap_mesh = cap.data
    cap_uv = cap_mesh.uv_layers.new(name="UVMap")
    per_vertex = {}
    for v in cap_mesh.vertices:
        location, _, index, _ = tree.find_nearest(v.co)
        t = tris[index]
        a, b, c = (mesh.vertices[i].co for i in t.vertices)
        ua, ub, uc = (Vector((*uv[l].uv, 0)) for l in t.loops)
        per_vertex[v.index] = barycentric_transform(location, a, b, c, ua, ub, uc).to_2d()
    for loop in cap_mesh.loops:
        cap_uv.data[loop.index].uv = per_vertex[loop.vertex_index]
    cap_mesh.materials.clear()
    cap_mesh.materials.append(mesh.materials[0])


def fit(variant: str, head: dict) -> None:
    bpy.ops.import_scene.gltf(filepath=str(HAIRS / "bruto" / f"{variant}.glb"))
    parts = [o for o in bpy.data.objects if o.type == "MESH"]
    for obj in parts[1:]:
        obj.select_set(True)
    hair = parts[0]
    if len(parts) > 1:
        bpy.context.view_layer.objects.active = hair
        hair.select_set(True)
        bpy.ops.object.join()
    mesh = hair.data
    mesh.transform(hair.matrix_world)
    hair.matrix_world = Matrix.Identity(4)
    hair.parent = None
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    # Escala pela coroa: largura da peruca numa faixa perto do topo = largura da cabeça na mesma faixa
    # (mechas soltas dos lados e rabos não entram na medida).
    # A faixa é medida em altura de CABEÇA (não da peruca: no cabelo comprido ela cairia na altura das
    # orelhas, onde o cabelo é largo, e a coroa afundava na cabeça). Como a altura da cabeça em unidades
    # da peruca depende da escala, recalcula algumas vezes.
    top_raw = sorted(zs)[int(len(zs) * 0.97)]
    head_height = head["top"] - head["neck_z"]
    scale = LARGURA * head["width"] / (max(xs) - min(xs))
    for _ in range(6):
        span = head_height / scale
        band = [v.co.x for v in mesh.vertices if top_raw - CORA[1] * span < v.co.z < top_raw - CORA[0] * span]
        scale = head["crown"] / (max(band) - min(band)) * LARGURA
    target = Vector((head["center"].x, head["center"].y, head["top"] + TOPO))
    # Topo da peruca pelo percentil 97 da altura: uma mecha espetada para cima não pode baixar a peruca
    # inteira (a coroa de trás ficava descoberta).
    top_z = sorted(zs)[int(len(zs) * 0.97)]
    source = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, top_z))
    for v in mesh.vertices:
        v.co = target + (v.co - source) * scale

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # Abertura do rosto: faces na frente da cabeça dentro da oval da máscara.
    lo, hi = head["mask_min"], head["mask_max"]
    cx, cz = (lo.x + hi.x) / 2, (lo.z + hi.z) / 2
    rx, rz = (hi.x - lo.x) / 2 * FOLGA_ROSTO, (hi.z - lo.z) / 2 * FOLGA_ROSTO
    in_front = [f for f in bm.faces
                if f.calc_center_median().y < head["center"].y
                and ((f.calc_center_median().x - cx) / rx) ** 2 + ((f.calc_center_median().z - cz) / rz) ** 2 < 1]
    bmesh.ops.delete(bm, geom=in_front, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # Fora do couro cabeludo, inflando a peruca: para cada direção a partir do centro da cabeça, quanto a
    # camada mais externa precisa sair para ficar MARGEM fora da pele; a coluna inteira (camadas de dentro
    # e de fora) anda isso, e a espessura e a sobreposição das mechas se mantêm.
    pushed = inflate(bm, head)
    boundary = [e for e in bm.edges if e.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=boundary, sides=MAX_HOLE_SIDES)["faces"]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    open_edges = len([e for e in bm.edges if e.is_boundary])
    for v in bm.verts:
        v.co -= head["anchor"]
    bm.to_mesh(mesh)
    bm.free()
    for material in mesh.materials:
        material.use_backface_culling = False
    cap = scalp_cap(head, hair_color(mesh))
    for v in cap.data.vertices:
        v.co -= head["anchor"]
    texture_cap_from_hair(cap, hair)
    bpy.ops.object.select_all(action="DESELECT")
    cap.select_set(True)
    hair.select_set(True)
    bpy.context.view_layer.objects.active = hair
    bpy.ops.object.join()
    hair.name = f"cabelo_{variant}"
    for obj in list(bpy.data.objects):
        if obj is not hair:
            bpy.data.objects.remove(obj)
    path = HAIRS / f"{variant}.glb"
    bpy.ops.object.select_all(action="DESELECT")
    hair.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True)
    print(f"== {variant}: escala {scale:.3f}, {len(in_front)} faces tiradas da frente do rosto, "
          f"{pushed} vértices para fora do couro cabeludo, {len(filled)} buracos fechados, "
          f"{open_edges} arestas abertas (a abertura do rosto), {len(mesh.polygons)} faces, "
          f"{path.stat().st_size // 1024} KB")


def main() -> None:
    variants = sys.argv[sys.argv.index("--") + 1:]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    head = base_head()
    for variant in variants:
        fit(variant, head)
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj)


main()

"""Passo 4: limpeza do corpo escolhido (corpo_so_frente_1.glb) em Blender headless.

1. Uma malha só, vértices duplicados fundidos, normais recalculadas.
2. Escala 0,40 m, pés em z = 0 (y = 0 no glTF), pivô entre os pés, frente para -Y do Blender (+Z do glTF).
3. Simetria em X: fica o lado cuja área do rosto é mais lisa; o outro é o espelho.
4. Alisamento de Taubin (preserva volume): a cabeça é subdividida uma vez e alisada forte; o corpo, leve; a
   frente do peito perto do pescoço (a dobra da folha) recebe passos extras. Meta na área dos olhos: RMS ≤ 1,5
   mm e máximo ≤ 3 mm em relação a uma esfera ajustada; os passos da cabeça sobem até bater a meta.
5. Decimação para ≤ 2.500 triângulos com simetria, com um grupo de vértices que segura as juntas (ombros,
   cotovelos, quadris, joelhos).
6. Um material "pele", cor chapada, sem textura; faces suaves. Exporta assets/modelos/aldeao_v2/aldeao_corpo.glb
   (ainda sem rig) e aldeao_corpo_limpeza.json com as medidas.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/limpar_corpo.py -- [entrada.glb] [saida.glb]
"""

import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpo_lib import ROOT, HEIGHT_M, SKIN, face_flatness, flat_material, head_box, import_glb, mesh_points, set_smooth, triangle_count  # noqa: E402

DEFAULT_IN = ROOT / "assets/conceitos/aldeao_v2/meshy/corpo_so_frente_1.glb"
DEFAULT_OUT = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
MAX_TRIANGLES = 2500
TARGET_RMS_MM, TARGET_MAX_MM = 1.5, 3.0
HEAD_PASSES, HEAD_PASSES_MAX, BODY_PASSES, CHEST_PASSES = 20, 80, 6, 25
LAMBDA, MU = 0.5, -0.53
NECK_BLEND = 0.03  # m: transição do peso de alisamento no pescoço
JOINT_WEIGHT = 0.12  # peso de decimação nas juntas (menor = decima menos)


def single_object(objects):
    meshes = [o for o in objects if o.type == "MESH"]
    for o in objects:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.name = obj.data.name = "aldeao_corpo"
    return obj


def normalize(obj):
    pts = np.array([v.co[:] for v in obj.data.vertices])
    low, high = pts.min(axis=0), pts.max(axis=0)
    scale = HEIGHT_M / (high[2] - low[2])
    feet = pts[pts[:, 2] < low[2] + (high[2] - low[2]) * 0.03]
    cx, cy = (feet[:, 0].min() + feet[:, 0].max()) / 2, (feet[:, 1].min() + feet[:, 1].max()) / 2
    for v in obj.data.vertices:
        v.co = Vector(((v.co.x - cx) * scale, (v.co.y - cy) * scale, (v.co.z - low[2]) * scale))


def points(obj):
    return np.array([v.co[:] for v in obj.data.vertices])


def symmetrize(obj, keep_positive: bool):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=keep_positive, clear_outer=not keep_positive, dist=1e-6)
    bm.to_mesh(obj.data)
    bm.free()
    mod = obj.modifiers.new("espelho", "MIRROR")
    mod.use_axis[0] = True
    mod.use_mirror_merge = True
    mod.merge_threshold = 1e-4
    mod.use_clip = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def side_quality(pts, box):
    """RMS da área dos olhos em cada metade (x > 0 e x < 0), para escolher o lado mais liso."""
    out = {}
    for name, sel in (("+x", pts[pts[:, 0] >= 0]), ("-x", pts[pts[:, 0] <= 0])):
        flat = face_flatness(np.vstack([sel, sel * [-1, 1, 1]]), box)
        out[name] = flat["olhos"].get("rms_mm", 99)
    return out


def subdivide_region(obj, mask):
    """Subdivide uma vez as faces cujos vértices estão todos na região (mask por índice de vértice)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    faces = [f for f in bm.faces if all(mask[v.index] for v in f.verts)]
    edges = list({e for f in faces for e in f.edges})
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True, smooth=0.0)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def taubin(obj, weight_fn, passes):
    """Alisamento de Taubin (lambda | mu) ponderado por vértice; a cada passo os pesos vêm de weight_fn(pos)."""
    mesh = obj.data
    n = len(mesh.vertices)
    pos = np.array([v.co[:] for v in mesh.vertices])
    edges = np.array([e.vertices[:] for e in mesh.edges])
    deg = np.bincount(edges.ravel(), minlength=n).astype(float)
    deg[deg == 0] = 1
    w = weight_fn(pos)[:, None]
    for _ in range(passes):
        for factor in (LAMBDA, MU):
            acc = np.zeros_like(pos)
            np.add.at(acc, edges[:, 0], pos[edges[:, 1]])
            np.add.at(acc, edges[:, 1], pos[edges[:, 0]])
            pos += factor * w * (acc / deg[:, None] - pos)
    for v, p in zip(mesh.vertices, pos):
        v.co = p


def region_weights(box, head_w=1.0, body_w=0.0, chest_w=0.0):
    neck = box["pescoco_z"]
    ymid = (box["y"][0] + box["y"][1]) / 2

    def fn(pos):
        t = np.clip((pos[:, 2] - (neck - NECK_BLEND)) / (2 * NECK_BLEND), 0, 1)
        w = body_w + (head_w - body_w) * t
        if chest_w:
            # frente do peito logo abaixo do pescoço (onde a folha tinha a dobra)
            chest = (pos[:, 2] < neck) & (pos[:, 2] > neck - 0.06) & (pos[:, 1] < ymid) & (np.abs(pos[:, 0]) < 0.05)
            w = np.where(chest, np.maximum(w, chest_w), w)
        return w
    return fn


def joint_weights(obj, box):
    """Grupo 'decimar': 1 no corpo, JOINT_WEIGHT nas juntas (elas colapsam menos)."""
    pts = points(obj)
    low, high = pts.min(axis=0), pts.max(axis=0)
    h = high[2] - low[2]
    z = (pts[:, 2] - low[2]) / h
    ax = np.abs(pts[:, 0])
    torso_half = np.percentile(ax[(z > 0.45) & (z < 0.55)], 80)
    hand_x = ax[(z > 0.35) & (z < 0.65)].max()
    joints = np.zeros(len(pts), bool)
    joints |= (z > 0.36) & (z < 0.46)  # quadris
    joints |= (z > 0.12) & (z < 0.24)  # joelhos
    joints |= (z > 0.58) & (z < 0.70) & (ax > torso_half * 0.75)  # ombros
    joints |= (z > 0.40) & (z < 0.56) & (ax > (torso_half + hand_x) / 2 * 0.85) & (ax < hand_x * 0.92)  # cotovelos
    group = obj.vertex_groups.new(name="decimar")
    group.add([i for i in range(len(pts)) if not joints[i]], 1.0, "REPLACE")
    group.add([i for i in range(len(pts)) if joints[i]], JOINT_WEIGHT, "REPLACE")
    return joints


def decimate(obj, max_triangles):
    obj.data.calc_loop_triangles()
    tris = len(obj.data.loop_triangles)
    if tris <= max_triangles:
        return
    mod = obj.modifiers.new("decimar", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = max_triangles / tris * 0.97
    mod.use_collapse_triangulate = True
    mod.use_symmetry = True
    mod.symmetry_axis = "X"
    mod.vertex_group = "decimar"
    mod.vertex_group_factor = 4.0
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    src = Path(args[0]) if args else DEFAULT_IN
    dst = Path(args[1]) if len(args) > 1 else DEFAULT_OUT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = single_object(import_glb(src))
    report = {"entrada": str(src.relative_to(ROOT)), "triangulos_entrada": triangle_count([obj])}

    normalize(obj)
    box = head_box(points(obj))
    report["antes"] = face_flatness(points(obj), box)
    sides = side_quality(points(obj), box)
    keep_positive = sides["+x"] <= sides["-x"]
    symmetrize(obj, keep_positive)
    report["simetria"] = {"lado_mantido": "+x" if keep_positive else "-x", "rms_por_lado_mm": sides}

    box = head_box(points(obj))
    pts = points(obj)
    head_mask = pts[:, 2] >= box["pescoco_z"] - NECK_BLEND
    subdivide_region(obj, head_mask)
    taubin(obj, region_weights(box, head_w=0.0, body_w=1.0, chest_w=0.0), BODY_PASSES)
    taubin(obj, region_weights(box, head_w=0.0, body_w=0.0, chest_w=1.0), CHEST_PASSES)
    passes = 0
    while True:
        taubin(obj, region_weights(box, head_w=1.0, body_w=0.0), HEAD_PASSES if passes == 0 else 10)
        passes += HEAD_PASSES if passes == 0 else 10
        box = head_box(points(obj))
        flat = face_flatness(points(obj), box)
        ok = flat["olhos"].get("rms_mm", 99) <= TARGET_RMS_MM and flat["olhos"].get("max_mm", 99) <= TARGET_MAX_MM
        if ok or passes >= HEAD_PASSES_MAX:
            break
    report["alisamento"] = {"passos_cabeca": passes, "passos_corpo": BODY_PASSES, "passos_peito": CHEST_PASSES, "rosto_antes_decimar": flat}

    joints = joint_weights(obj, box)
    decimate(obj, MAX_TRIANGLES)
    normalize(obj)  # o alisamento encolhe um nada: escala e pés de novo
    box = head_box(points(obj))
    pts = points(obj)
    flat = face_flatness(pts, box)
    obj.data.calc_loop_triangles()
    tris = obj.data.loop_triangles
    centers = np.array([np.mean([obj.data.vertices[i].co[:] for i in t.vertices], axis=0) for t in tris])
    low, high = pts.min(axis=0), pts.max(axis=0)
    zc = (centers[:, 2] - low[2]) / (high[2] - low[2])
    knees = int(((zc > 0.12) & (zc < 0.24)).sum())
    report["depois"] = {"triangulos": len(tris), "vertices": len(obj.data.vertices), "rosto": flat, "cabeca": box,
                        "juntas_vertices_marcados": int(joints.sum()), "triangulos_na_faixa_dos_joelhos": knees,
                        "altura_m": float(high[2] - low[2]), "pes_z_min": float(low[2])}

    flat_material([obj], SKIN, "pele")
    set_smooth([obj], True)
    obj.vertex_groups.clear()
    dst.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(dst), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_materials="EXPORT", export_animations=False, export_skins=False)
    dst.with_name(dst.stem + "_limpeza.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))


main()

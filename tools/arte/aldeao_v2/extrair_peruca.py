"""Passo 11 (piloto): extrai a peruca do modelo cabeça + cabelo da Meshy e encaixa na cabeça do corpo aprovado.

1. Corpo com rig em pose de repouso: elipsoide da cabeça (centro + 3 raios, ajuste algébrico aos vértices acima
   do pescoço). Retalhos "Olhos" e "Boca" ficam para as conferências.
2. Modelo do cabelo: uma malha. A cabeça da folha é achada ajustando ao rosto liso (frente, parte de baixo) um
   elipsoide com a MESMA forma do da cabeça do corpo, só escala uniforme + centro (4 parâmetros, Gauss-Newton),
   refinado com os pontos que caem perto dele.
3. Tudo é levado ao espaço do corpo: p' = c_corpo + (p - c_folha) / s. Face cujo centro fica a mais de MARGEM do
   elipsoide da cabeça do corpo é cabelo; o resto (a cabeça da folha) sai. Pedaços soltos pequenos saem.
4. Vértices da peruca dentro da cabeça do corpo (BVH) vão para a superfície + FOLGA; perto dos retalhos, folga de
   FOLGA_RETALHO. Regra da franja: face de cabelo na frente do retalho "Olhos" abaixo da linha do centro dos
   olhos é apagada (a franja cobre no máximo a metade de cima do olho).
5. Decimação até ≤ MAX_TRIS, material "cabelo", exportação rígida no espaço do corpo em repouso.
6. Conferência: distância mínima da peruca ao corpo e aos retalhos em repouso e em quadros do idle e do run
   (a peruca segue o osso Head como bloco rígido). Renders para a prévia.

Uso:
  Blender -b --factory-startup --python extrair_peruca.py -- <N> <glb_meshy> <pasta_previa>
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpo_lib import ROOT, ROSTO, SKIN, game_camera_offset, head_box, import_glb, load_rosto, set_cell, set_smooth, setup_scene, shoot, twilight_lights  # noqa: E402
from rig_lib import play  # noqa: E402

BODY = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
OUT_DIR = ROOT / "assets/modelos/aldeao_v2/cabelos"
HAIR_COLOR = (0.294, 0.353, 0.412, 1.0)  # #4B5A69
MAX_TRIS = 800
DIHEDRAL_DEG = 32  # aresta mais viva que isso separa rosto de cabelo (linha do cabelo, franja)
LOOSE_GUARD = 0.025  # m: o rosto crescido nunca sai mais que isso do elipsoide da cabeça
CLEARANCE, PATCH_CLEARANCE = 0.0015, 0.0025  # m (retalho: 2,5 mm de alvo para sobrar >= 2 mm depois da decimação)
HEAD_BONE = "Head"
CHECK_POINTS = 5
# (largura da cabeça / largura da silhueta, altura da cabeça / altura da silhueta, topo da cabeça abaixo do topo da
# silhueta / altura), medidos nas folhas em 29/09/2026.
# Medidas em 29/09/2026 (vistas de frente): face visível e queixo pelo preparador; a cabeça é um pouco mais larga
# que a face visível onde o cabelo cobre as laterais (2, 3) e quase igual onde não cobre (1, 5).
PRIOR = {1: (0.78, 0.80, 0.10), 2: (0.75, 0.83, 0.06), 3: (0.70, 0.82, 0.07), 4: (0.75, 0.74, 0.05), 5: (0.88, 0.86, 0.05)}
SEED_HEIGHT = 0.38  # fração da altura do modelo onde a semente do rosto é tomada (boca/queixo: nunca tem franja)


def world_points(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    m = ev.to_mesh()
    pts = np.array([[p.x, p.y, p.z] for p in (obj.matrix_world @ v.co for v in m.vertices)])
    ev.to_mesh_clear()
    return pts


def bvh_of(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    m = ev.to_mesh()
    verts = [obj.matrix_world @ v.co for v in m.vertices]
    polys = [p.vertices[:] for p in m.polygons]
    normals = [(obj.matrix_world.to_3x3() @ p.normal).normalized() for p in m.polygons]
    tree = BVHTree.FromPolygons(verts, polys)
    ev.to_mesh_clear()
    return tree, normals


def signed_distances(tree, normals, pts, near=None):
    """Distância com sinal ao objeto; com `near`, só conta pontos a menos de `near` metros (para os retalhos,
    onde o sinal só faz sentido perto: atrás da cabeça o 'lado de trás' do retalho não significa nada)."""
    out = []
    for p in pts:
        loc, normal, index, dist = tree.find_nearest(Vector(p))
        if loc is None or (near is not None and dist > near):
            continue
        sign = 1 if (Vector(p) - loc).dot(normals[index]) >= 0 else -1
        out.append(sign * dist)
    return np.array(out) if out else np.array([float("inf")])


def fit_ellipsoid(pts):
    """Elipsoide alinhado aos eixos: A x² + B y² + C z² + D x + E y + F z = 1 -> centro e raios."""
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    M = np.c_[x * x, y * y, z * z, x, y, z]
    A, B, C, D, E, F = np.linalg.lstsq(M, np.ones(len(pts)), rcond=None)[0]
    center = np.array([-D / (2 * A), -E / (2 * B), -F / (2 * C)])
    k = 1 + D * D / (4 * A) + E * E / (4 * B) + F * F / (4 * C)
    radii = np.sqrt(np.array([k / A, k / B, k / C]))
    return center, radii


def fit_sphere(pts):
    """Esfera por mínimos quadrados (linear): centro e raio. Bem condicionada num casquete de rosto."""
    A = np.c_[2 * pts, np.ones(len(pts))]
    c, *_ = np.linalg.lstsq(A, (pts ** 2).sum(axis=1), rcond=None)
    center = c[:3]
    return center, math.sqrt(c[3] + (center ** 2).sum())


def fit_scaled(pts, radii, center0, s0, iters=30, s_bounds=(0.8, 1.25), c_box=None):
    """Ajusta centro e escala uniforme de um elipsoide de forma fixa (raios `radii`) aos pontos, com a escala
    presa a [s0*lo, s0*hi] e o centro a uma caixa em volta de center0 (um casquete quase plano puxaria a
    escala para o infinito)."""
    c, s = center0.astype(float).copy(), float(s0)
    lo, hi = s0 * s_bounds[0], s0 * s_bounds[1]

    def residual(c, s):
        return np.linalg.norm((pts - c) / (s * radii), axis=1) - 1

    for _ in range(iters):
        r0 = residual(c, s)
        J = np.zeros((len(pts), 4))
        eps = 1e-4
        for i in range(3):
            dc = np.zeros(3)
            dc[i] = eps
            J[:, i] = (residual(c + dc, s) - r0) / eps
        J[:, 3] = (residual(c, s + eps) - r0) / eps
        step, *_ = np.linalg.lstsq(J, -r0, rcond=None)
        c += step[:3]
        s = min(max(s + step[3], lo), hi)
        if c_box is not None:
            c = np.clip(c, center0 - c_box, center0 + c_box)
        if np.linalg.norm(step) < 1e-7:
            break
    return c, s, float(np.sqrt((residual(c, s) ** 2).mean()))


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    n, src, preview = int(args[0]), ROOT / args[1], Path(args[2])
    max_tris = int(args[3]) if len(args) > 3 else MAX_TRIS
    suffix = args[4] if len(args) > 4 else ""
    preview.mkdir(parents=True, exist_ok=True)
    scene = setup_scene(512, transparent=True)
    twilight_lights(scene)
    report = {"cabelo": n, "fonte": args[1]}

    # 1. corpo em repouso
    body_objs = import_glb(BODY)
    armature = next(o for o in body_objs if o.type == "ARMATURE")
    body = next(o for o in body_objs if o.name == "aldeao_corpo")
    eyes = next(o for o in body_objs if o.name == "Olhos")
    mouth = next(o for o in body_objs if o.name == "Boca")
    armature.data.pose_position = "REST"
    for t in armature.animation_data.nla_tracks:
        t.mute = True
    armature.animation_data.action = None
    bpy.context.view_layer.update()
    bpts = world_points(body)
    box = head_box(bpts)
    head_pts = bpts[bpts[:, 2] >= box["pescoco_z"]]
    c_body, r_body = fit_ellipsoid(head_pts)
    report["cabeca_corpo"] = {"centro": c_body.round(4).tolist(), "raios_mm": (r_body * 1000).round(1).tolist()}

    # 2. modelo do cabelo -> uma malha
    hair_objs = [o for o in import_glb(src) if o.type == "MESH"]
    for o in hair_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = hair_objs[0]
    if len(hair_objs) > 1:
        bpy.ops.object.join()
    hair = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    hair.name = hair.data.name = f"cabelo_{n}"
    bm0 = bmesh.new()  # a Meshy exporta vértices duplicados por face: sem fundir, cada triângulo é uma ilha
    bm0.from_mesh(hair.data)
    n_before = len(bm0.verts)
    bmesh.ops.remove_doubles(bm0, verts=bm0.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm0, faces=bm0.faces)
    bm0.to_mesh(hair.data)
    bm0.free()
    report["vertices_fundidos"] = [n_before, len(hair.data.vertices)]
    hpts = np.array([v.co[:] for v in hair.data.vertices])
    low, high = hpts.min(axis=0), hpts.max(axis=0)
    size = high - low
    report["modelo_meshy"] = {"triangulos": sum(len(p.vertices) - 2 for p in hair.data.polygons), "caixa": size.round(4).tolist()}
    # rosto liso: em cada fatia de altura entre 22% e 62% do modelo, só os pontos mais à frente (as mechas
    # ficam ao lado e abaixo do rosto, nunca na frente dele), numa faixa central em x.
    xc = (low[0] + high[0]) / 2
    band = hpts[(hpts[:, 2] > low[2] + size[2] * 0.22) & (hpts[:, 2] < low[2] + size[2] * 0.62) & (np.abs(hpts[:, 0] - xc) < size[0] * 0.22)]
    rows = []
    for z0 in np.linspace(band[:, 2].min(), band[:, 2].max(), 24):
        sl = band[np.abs(band[:, 2] - z0) < size[2] * 0.012]
        if len(sl):
            rows.append(sl[sl[:, 1] < sl[:, 1].min() + size[1] * 0.06])
    face = np.vstack(rows)
    # Cabeça da folha por medidas da própria folha (o ajuste automático não fecha: o rosto visível é uma
    # faixa estreita entre as mechas e não fixa a largura nem a profundidade da cabeça). PRIOR[n] = (largura da
    # cabeça / largura da silhueta, altura da cabeça / altura da silhueta, topo da cabeça abaixo do topo da
    # silhueta / altura), lidos na folha; a frente do rosto na altura dos olhos vem do modelo.
    prior_w, prior_h, prior_top = PRIOR[n]
    head_w, head_h = prior_w * size[0], prior_h * size[2]
    eye_band = face[np.abs(face[:, 2] - (low[2] + size[2] * 0.48)) < size[2] * 0.06]
    y_front = float((eye_band if len(eye_band) else face)[:, 1].min())
    scale_axes = np.array([head_w / (2 * r_body[0]), head_w / (2 * r_body[0]), head_h / (2 * r_body[2])])
    c_gen = np.array([xc, y_front + scale_axes[1] * float(r_body[1]), high[2] - prior_top * size[2] - head_h / 2])
    rms = float(np.sqrt(((np.linalg.norm((face - c_gen) / (scale_axes * r_body), axis=1) - 1) ** 2).mean()))
    report["cabeca_folha"] = {"centro": c_gen.round(4).tolist(),
                              "escala_xy": round(float(scale_axes[0]), 4), "escala_z": round(float(scale_axes[2]), 4), "rms": round(rms, 4), "pontos_rosto": int(len(face)),
                              "altura_cabeca_estimada": round(2 * float(scale_axes[2]) * float(r_body[2]), 4), "altura_modelo": round(float(size[2]), 4)}
    if not (0.3 * size[2] < 2 * scale_axes[2] * r_body[2] < 1.1 * size[2]) or not (low <= c_gen).all() or not (c_gen <= high).all():
        raise RuntimeError(f"ajuste da cabeça da folha fora do plausível: {report['cabeca_folha']}")

    # 3. para o espaço do corpo e classificação
    for v in hair.data.vertices:
        p = (np.array(v.co[:]) - c_gen) / scale_axes + c_body
        v.co = Vector(p.tolist())
    mapped = np.array([v.co[:] for v in hair.data.vertices])
    report["peruca_no_corpo_caixa"] = [mapped.min(axis=0).round(3).tolist(), mapped.max(axis=0).round(3).tolist()]
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    # Cabeça = região do rosto crescida a partir da frente (altura dos olhos), atravessando só arestas suaves
    # (a linha do cabelo é uma aresta viva) e sem se afastar demais do elipsoide da cabeça (guarda solta).
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    seed_band = face[np.abs(face[:, 2] - (low[2] + size[2] * SEED_HEIGHT)) < size[2] * 0.06]
    seed_y = float((seed_band if len(seed_band) else face)[:, 1].min())
    eye_point = Vector((xc, seed_y, low[2] + size[2] * SEED_HEIGHT))
    eye_point = Vector(((np.array(eye_point[:]) - c_gen) / scale_axes + c_body).tolist())
    dists = []
    for f in bm.faces:
        cen = np.array(f.calc_center_median()[:])
        dists.append((np.linalg.norm((cen - c_body) / r_body) - 1) * np.min(r_body))
    dists_m = np.array(dists)
    seeds = sorted(bm.faces, key=lambda f: (f.calc_center_median() - eye_point).length)[:12]
    region, stack = set(seeds), list(seeds)
    while stack:
        f = stack.pop()
        for e in f.edges:
            for g in e.link_faces:
                if g in region:
                    continue
                if f.normal.angle(g.normal, 0.0) > math.radians(DIHEDRAL_DEG):
                    continue
                if abs(dists_m[g.index]) > LOOSE_GUARD:
                    continue
                region.add(g)
                stack.append(g)
    doomed = list(region)
    dists = dists_m * 1000
    report["distancia_faces_mm"] = {"min": round(float(dists.min()), 1), "mediana": round(float(np.median(dists)), 1), "max": round(float(dists.max()), 1), "fracao_rosto": round(len(region) / len(bm.faces), 3)}
    print("PARCIAL " + json.dumps(report), flush=True)
    chin_z = c_body[2] - 0.85 * r_body[2]
    neck = [f for f in bm.faces if f not in doomed and f.calc_center_median().z < chin_z
            and math.hypot(f.calc_center_median().x - c_body[0], f.calc_center_median().y - c_body[1]) < 0.7 * r_body[0]]
    report["faces_cabeca_removidas"] = len(doomed)
    report["faces_pescoco_removidas"] = len(neck)
    doomed += neck
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # pedaços soltos pequenos
    seen, comps = set(), []
    for f in bm.faces:
        if f in seen:
            continue
        stack, comp = [f], []
        seen.add(f)
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h not in seen:
                        seen.add(h)
                        stack.append(h)
        comps.append(comp)
    biggest = max(len(c) for c in comps)
    small = [f for c in comps if len(c) < biggest * 0.02 for f in c]
    bmesh.ops.delete(bm, geom=small, context="FACES")
    report["pedacos"] = {"total": len(comps), "removidos_faces": len(small)}
    bm.to_mesh(hair.data)
    bm.free()

    # 4. empurrar para fora do corpo e dos retalhos; regra da franja
    tree_b, nrm_b = bvh_of(body)
    tree_e, nrm_e = bvh_of(eyes)
    eye_pts = world_points(eyes)
    eye_top, eye_bottom = eye_pts[:, 2].max(), eye_pts[:, 2].min()
    eye_line = eye_top - 0.35 * (eye_top - eye_bottom)  # centro dos olhos no atlas: 35% abaixo do topo da janela
    ex0, ex1 = eye_pts[:, 0].min(), eye_pts[:, 0].max()
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    doomed = []
    for f in bm.faces:
        cen = f.calc_center_median()
        if ex0 <= cen.x <= ex1 and eye_bottom - 0.005 <= cen.z < eye_line and cen.y < c_body[1]:
            loc, normal, index, dist = tree_e.find_nearest(cen)
            if dist < 0.012:  # na frente do retalho, abaixo da linha dos olhos
                doomed.append(f)
    report["faces_franja_removidas"] = len(doomed)
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    pushed_b = pushed_e = 0
    for _ in range(3):
        for v in bm.verts:
            loc, normal, index, dist = tree_b.find_nearest(v.co)
            if loc is None:
                continue
            inside = (v.co - loc).dot(nrm_b[index]) < 0
            if inside or dist < CLEARANCE:
                v.co = loc + nrm_b[index] * CLEARANCE
                pushed_b += 1
            loc, normal, index, dist = tree_e.find_nearest(v.co, PATCH_CLEARANCE * 3)
            if loc is not None:
                behind = (v.co - loc).dot(nrm_e[index]) < 0
                if behind or dist < PATCH_CLEARANCE:
                    v.co = loc + nrm_e[index] * PATCH_CLEARANCE
                    pushed_e += 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(hair.data)
    bm.free()
    report["empurrados"] = {"corpo": pushed_b, "retalho_olhos": pushed_e}

    # 5. decimação e material
    hair.data.calc_loop_triangles()
    before = len(hair.data.loop_triangles)
    bpy.context.view_layer.objects.active = hair
    for _ in range(4):
        hair.data.calc_loop_triangles()
        tris = len(hair.data.loop_triangles)
        if tris <= max_tris:
            break
        mod = hair.modifiers.new("decimar", "DECIMATE")
        mod.ratio = max_tris / tris * 0.95
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    hair.data.calc_loop_triangles()
    report["triangulos"] = {"cabelo_antes": before, "final": len(hair.data.loop_triangles)}
    hair.data.materials.clear()
    mat = bpy.data.materials.new("cabelo")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = HAIR_COLOR
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    hair.data.materials.append(mat)
    set_smooth([hair], True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"cabelo_{n}{suffix}.glb"
    bpy.ops.object.select_all(action="DESELECT")
    hair.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", use_selection=True, export_yup=True, export_animations=False, export_skins=False)
    report["saida"] = str(out.relative_to(ROOT))

    # 6. conferência em repouso e nos clipes (peruca rígida no Head)
    hpts = world_points(hair)

    def in_front_of_eyes(pts):  # só o cabelo que está na frente do retalho dos olhos (mesma faixa em x e z, mais à frente)
        sel = (pts[:, 0] > ex0 + 0.004) & (pts[:, 0] < ex1 - 0.004) & (pts[:, 2] > eye_bottom) & (pts[:, 2] < eye_top) & (pts[:, 1] < c_body[1])
        return pts[sel]

    def worst_body(pts):
        d = signed_distances(tree_b, nrm_b, pts)
        i = int(np.argmin(d))
        return round(float(d[i]) * 1000, 2), round(float(pts[i][2]), 3)

    wb, wz = worst_body(hpts)
    fe = in_front_of_eyes(hpts)
    report["folga_mm"] = {"repouso": {"corpo": wb, "corpo_z_do_pior": wz, "olhos": round(float(signed_distances(tree_e, nrm_e, fe).min()) * 1000, 2) if len(fe) else None, "vertices_na_frente_dos_olhos": int(len(fe))}}
    head_rest = armature.matrix_world @ armature.data.bones[HEAD_BONE].matrix_local
    armature.data.pose_position = "POSE"
    for clip in ("idle-loop", "run-loop"):
        action = bpy.data.actions[clip]
        play(armature, action)
        a, b = (int(x) for x in action.frame_range)
        worst_b, worst_z, worst_back = 1e9, None, 1e9
        for f in [a + (b - a) * i // (CHECK_POINTS - 1) for i in range(CHECK_POINTS)]:
            scene.frame_set(f)
            head_pose = armature.matrix_world @ armature.pose.bones[HEAD_BONE].matrix
            delta = head_pose @ head_rest.inverted()
            moved = np.array([[q.x, q.y, q.z] for q in (delta @ Vector(p) for p in hpts)])
            tb, nb = bvh_of(body)
            te, ne = bvh_of(eyes)
            db = signed_distances(tb, nb, moved)
            if db.min() < worst_b:
                worst_b, worst_z = float(db.min()), round(float(moved[int(np.argmin(db))][2]), 3)
            back = moved[:, 1] > c_body[1] + 0.6 * r_body[1]  # cabelo atrás da cabeça (nuca, rabo)
            if back.any():
                worst_back = min(worst_back, float(db[back].min()))
        # Olhos: peruca e retalhos seguem o mesmo osso (Head) como bloco rígido, então a folga entre eles é a
        # do repouso em todos os quadros; só o corpo (ombros, braços, tronco) muda em relação à peruca.
        report["folga_mm"][clip] = {"corpo": round(worst_b * 1000, 2), "corpo_z_do_pior": worst_z, "atras_da_cabeca": round(worst_back * 1000, 2) if worst_back < 1e8 else None,
                                    "olhos": "igual ao repouso (rígidos no mesmo osso)"}
    armature.animation_data.action = None
    armature.data.pose_position = "REST"
    scene.frame_set(0)

    # renders para a prévia (rosto distraído)
    rosto = load_rosto()
    for mat_name, cfg, frame in (("rosto_olhos", rosto["olhos"], "aberto"), ("rosto_boca", rosto["boca"], "entreaberta")):
        m = bpy.data.materials.get(mat_name)
        if m and m.node_tree:
            mapping = next((nd for nd in m.node_tree.nodes if nd.type == "MAPPING"), None)
            if mapping:
                idx = cfg["quadros"][frame]
                mapping.inputs["Location"].default_value = (idx % cfg["colunas"] / cfg["colunas"], 1 - (idx // cfg["colunas"] + 1) / cfg["linhas"], 0)
    bpy.context.view_layer.update()
    set_smooth([body], True)
    center = Vector(((bpts[:, 0].min() + bpts[:, 0].max()) / 2, (bpts[:, 1].min() + bpts[:, 1].max()) / 2, (bpts[:, 2].min() + bpts[:, 2].max()) / 2))
    shoot(scene, center + Vector((0, -3, 0)), center, 0.6, preview / "frente.png")
    shoot(scene, center + Vector((3, 0, 0)), center, 0.6, preview / "lado.png")
    shoot(scene, center + Vector((2.1, -2.1, 0.5)), center, 0.6, preview / "tres_quartos.png")
    shoot(scene, center + game_camera_offset(3), center, 0.6, preview / "jogo.png")
    (preview / "relatorio.json").write_text(json.dumps(report, indent=2) + "\n")
    print("RELATORIO " + json.dumps(report))


main()

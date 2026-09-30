"""Protagonista v2: cabelo longo com pesos, a partir do busto + cabelo da Meshy (Blender headless).

1. Corpo final (protagonista_corpo.glb) em repouso: elipsoide da cabeça (chifres_lib.head_ellipsoid), retalhos Olhos e
   Boca, chifres.glb (20° e 1,3×). O busto da Meshy numa malha (vértices fundidos).
2. Encaixe: o rosto do busto aparece inteiro de frente (risca no meio, sem franja): o elipsoide da cabeça do corpo (a
   mesma forma, só centro e escala: fit_scaled do aldeão) é ajustado aos pontos do rosto virados para a frente; p' =
   c_corpo + (p - c_ajuste) / s.
3. Pele do busto (rosto, pescoço, ombros) = região crescida a partir do meio do rosto só por arestas suaves (a linha do
   cabelo é uma aresta viva); acima do queixo, sem se afastar mais que GUARD da pele do corpo. O resto é cabelo; ilhas
   pequenas saem.
4. Janela dos olhos aberta: sai o cabelo na frente do rosto dentro da janela do retalho "Olhos" (±45°, com margem).
   Chifres: sai o cabelo que fica dentro do volume deles (os chifres atravessam o cabelo e nunca somem).
5. Mechas fundidas (vértices a menos de 1 mm) e decimação a ≤ MAX_TRIS. DEPOIS: folga de 2 mm do corpo e dos retalhos
   (vértice dentro ou perto demais vai para fora pela normal da pele) e o corte dos chifres refeito.
6. Pesos: calota (acima do pescoço) 100% Head; abaixo, gradiente por neck, Spine e Spine01 pela altura das cabeças dos
   ossos em repouso; abaixo do Spine01, 100% Spine01. Material "cabelo" #4B5A69, liso.
7. Conferência: nos quadros da corrida e do idle, a menor distância com sinal do cabelo ao corpo (braços, costas).
Exporta cabelo.glb com o armature (sem clipes) pelo contrato (rig_lib.export_contract_glb), no espaço do corpo em repouso.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/extrair_cabelo.py -- <glb_meshy>
Saída: assets/modelos/protagonista_v2/cabelo.glb e cabelo.json
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
from cabelo_lib import scalp_mask  # noqa: E402
from chifres_lib import head_ellipsoid, merged_mesh  # noqa: E402
from corpo_lib import ROOT, import_glb  # noqa: E402
from rig_lib import export_contract_glb, play  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo.glb"
HORNS = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--chifres=")), ROOT / "assets/modelos/protagonista_v2/chifres.glb")).resolve()
OUT = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--saida=")), ROOT / "assets/modelos/protagonista_v2/cabelo.glb")).resolve()
COLOR = "#4B5A69"
MAX_TRIS = 1000
DIHEDRAL_DEG = 30
GUARD = 0.025  # m: a pele do busto não se afasta mais que isto da pele do corpo (como o LOOSE_GUARD do aldeão)
HAIRLINE = 0.20
FACE_HALF_DEG = 60  # acima do queixo, a pele do busto fica a no máximo este ângulo da frente  # a pele não sobe além do topo da janela dos olhos + esta fração até o topo da cabeça (a risca não vaza)
CLEARANCE = 0.002  # m, do corpo e dos retalhos, depois da decimação
SCALP_CLEARANCE = 0.003  # m, na calota (acima do queixo), medida também no meio das faces
HORN_REACH = 0.02  # m: dentro do chifre = lado de dentro da face mais próxima, a até esta distância
EYE_MARGIN = 0.006  # m em volta da janela dos olhos
MERGE_DIST = 0.001
BORDER_PASSES = 6
HOLE_SIDES = 24
CAP_OFFSET = 0.004  # m: calota por código, casca da pele do couro cabeludo afastada isto (por baixo das mechas)
CAP_TRIS = 140
CAP_TUCK = 0.01
HORN_RING = 0.012
CAP_SIDE_DROP = 0.008
CAP_NECK_DROP = 0.008  # m: na nuca a calota desce além da borda do teste (a cabeça inclina no idle)  # m: a calota cobre a pele até isto de cada chifre  # m da borda da calota até o afastamento cheio
VOLUME = 0.003  # m: as mechas de cima vão para fora (volume), da altura dos olhos para cima, crescendo até o topo  # furos com até este número de arestas são fechados antes da decimação
PATCHES = ("Olhos", "Boca")
WEIGHT_BONES = ("Head", "neck", "Spine", "Spine01")
CHECK_POINTS = 8
ARM_ROUNDS, ARM_GAP = 12, 0.002  # rodadas da correção dos braços; folga pedida em todos os quadros


def srgb_lin(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def fit_scaled(pts, radii, center0, s0, iters=40, s_bounds=(0.8, 1.25), c_box=None):
    """Centro e escala uniforme de um elipsoide de forma fixa ajustados aos pontos (o do aldeao_v2/extrair_peruca.py)."""
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


def evaluated_bvh(objs):
    """BVH (mundo) das malhas avaliadas (pose atual) e as normais das faces."""
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, normals = [], [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        m = ev.to_mesh()
        off = len(verts)
        verts += [o.matrix_world @ v.co for v in m.vertices]
        polys += [[off + i for i in p.vertices] for p in m.polygons]
        normals += [(o.matrix_world.to_3x3() @ p.normal).normalized() for p in m.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys), normals


def signed(tree, normals, p):
    loc, _n, idx, dist = tree.find_nearest(p)
    return (dist if (p - loc).dot(normals[idx]) >= 0 else -dist), loc, normals[idx]


def boundary_loops(bm):
    """Laços de arestas de borda (componentes conexas)."""
    seen, loops = set(), []
    for e in bm.edges:
        if not e.is_boundary or e in seen:
            continue
        comp, st = [], [e]
        seen.add(e)
        while st:
            x = st.pop()
            comp.append(x)
            for v in x.verts:
                for y in v.link_edges:
                    if y.is_boundary and y not in seen:
                        seen.add(y)
                        st.append(y)
        loops.append(comp)
    return loops


def close_holes(bm):
    """Fecha os furos pequenos (a separação da pele e a fusão das mechas deixam centenas): cada laço de borda com até
    HOLE_SIDES arestas vira faces. Os laços grandes (a abertura do rosto, a janela dos olhos, os cortes dos chifres) ficam."""
    for _ in range(3):
        small = [e for loop in boundary_loops(bm) if len(loop) <= HOLE_SIDES for e in loop]
        if not small:
            break
        bmesh.ops.holes_fill(bm, edges=small, sides=HOLE_SIDES)
        bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def build_cap(head, eyes, cb, report, horn_tree=None):
    """Calota por código: as faces do couro cabeludo (cabelo_lib.scalp_mask, borda recuada 2 mm para ficar por baixo da
    linha do cabelo da Meshy) copiadas da malha da cabeça e afastadas CAP_OFFSET pela normal, decimadas a CAP_TRIS. Garante
    que nenhuma pele do couro cabeludo aparece entre as mechas nem em volta da base dos chifres."""
    mw = head.matrix_world
    pts = np.array([(mw @ v.co)[:] for v in head.data.vertices])
    ep = np.array([(eyes.matrix_world @ v.co)[:] for v in eyes.data.vertices])
    # nas laterais a calota desce CAP_SIDE_DROP abaixo da borda do teste (o idle vira a cabeça e a pele dali, com peso do
    # pescoço, desliza em relação à calota, que é 100% Head); a linha do cabelo da testa não muda
    mask = scalp_mask(pts, cb, float(ep[:, 2].max()), float(pts[:, 2].max()), float(pts[:, 2].min()), shrink=0.002,
                      eye_mid_z=float(ep[:, 2].max()) - 0.02 - CAP_SIDE_DROP, neck_drop=CAP_NECK_DROP)
    if horn_tree is not None:  # anel em volta da base dos chifres, mesmo onde a base encosta na linha do cabelo
        ring = np.array([horn_tree.find_nearest(Vector(p.tolist()))[3] < HORN_RING for p in pts])
        mask = mask | ring
        report["anel_dos_chifres_vertices"] = int(ring.sum())
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.transform(mw)
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(mask[v.index] for v in f.verts)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # a borda encosta na pele (sem fresta para espiar por baixo de lado); o afastamento sobe até CAP_OFFSET a 1 cm da borda
    edge_pts = np.array([v.co[:] for v in bm.verts if v.is_boundary]) if any(v.is_boundary for v in bm.verts) else np.zeros((0, 3))
    for v in bm.verts:
        d = float(np.linalg.norm(edge_pts - np.array(v.co[:]), axis=1).min()) if len(edge_pts) else 1.0
        v.co = v.co + v.normal * max(0.0005, CAP_OFFSET * min(1.0, d / CAP_TUCK))
    mesh = bpy.data.meshes.new("calota")
    bm.to_mesh(mesh)
    bm.free()
    cap = bpy.data.objects.new("calota", mesh)
    bpy.context.scene.collection.objects.link(cap)
    mesh.calc_loop_triangles()
    before = len(mesh.loop_triangles)
    if before > CAP_TRIS:
        # a borda não encolhe: vértices de borda com peso 0 no grupo da decimação (peso 0 trava)
        edge_count = {}
        for p in mesh.polygons:
            for k in p.edge_keys:
                edge_count[k] = edge_count.get(k, 0) + 1
        border = {i for k, n in edge_count.items() if n == 1 for i in k}
        g = cap.vertex_groups.new(name="decimar")
        g.add([v.index for v in mesh.vertices if v.index not in border], 1.0, "REPLACE")
        g.add(list(border), 0.0, "REPLACE")
        mod = cap.modifiers.new("decimar", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = CAP_TRIS / before
        mod.use_collapse_triangulate = True
        mod.vertex_group = "decimar"
        mod.vertex_group_factor = 10.0
        bpy.context.view_layer.objects.active = cap
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mesh.calc_loop_triangles()
    cap.vertex_groups.clear()
    report["calota"] = {"faces_da_pele": int(before), "triangulos": len(mesh.loop_triangles), "afastamento_mm": CAP_OFFSET * 1000}
    return cap


def add_volume(mesh, cb, eye_top_z, head_top_z):
    """Mechas de cima para fora, pela direção a partir do centro da cabeça: 0 na altura dos olhos, VOLUME no topo."""
    n = 0
    c = Vector(cb.tolist())
    for v in mesh.vertices:
        t = (v.co.z - eye_top_z) / max(head_top_z - eye_top_z, 1e-6)
        if t <= 0:
            continue
        d = (v.co - c).normalized()
        v.co += d * VOLUME * min(t, 1.0)
        n += 1
    mesh.update()
    return n


def copy_skin_weights(hair, head, indices):
    """A calota segue a pele de baixo dela: cada vértice copia os pesos do vértice mais próximo da malha da cabeça (em repouso).
    Com 100% Head, a pele atrás da orelha (com peso do pescoço) furava a calota quando o idle vira a cabeça."""
    from mathutils.kdtree import KDTree
    hv = [head.matrix_world @ v.co for v in head.data.vertices]
    kd = KDTree(len(hv))
    for i, p in enumerate(hv):
        kd.insert(p, i)
    kd.balance()
    names = {g.index: g.name for g in head.vertex_groups}
    n = 0
    for i in indices:
        v = hair.data.vertices[i]
        _co, j, _d = kd.find(hair.matrix_world @ v.co)
        src = [(names[g.group], g.weight) for g in head.data.vertices[j].groups if g.weight > 1e-4]
        total = sum(w for _, w in src) or 1.0
        for g in list(v.groups):
            hair.vertex_groups[g.group].remove([i])
        for name, w in src:
            grp = hair.vertex_groups.get(name) or hair.vertex_groups.new(name=name)
            grp.add([i], w / total, "REPLACE")
        n += 1
    return n


def join_into(hair, other):
    bpy.ops.object.select_all(action="DESELECT")
    other.select_set(True)
    hair.select_set(True)
    bpy.context.view_layer.objects.active = hair
    bpy.ops.object.join()


def smooth_borders(obj, passes=BORDER_PASSES):
    """Suaviza a borda aberta (linha do cabelo, janela dos olhos): cada vértice de borda anda para a média dos seus dois
    vizinhos de borda. Os dentes que a separação da pele deixa viram uma curva. Devolve quantos vértices de borda há."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    border = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
    nbrs = {v: [e.other_vert(v) for e in v.link_edges if e.is_boundary] for v in border}
    for _ in range(passes):
        new = {v: (v.co + sum((u.co for u in nbrs[v]), Vector())) / (1 + len(nbrs[v])) for v in border if len(nbrs[v]) == 2}
        for v, co in new.items():
            v.co = co
    bm.to_mesh(obj.data)
    bm.free()
    return len(border)


def push_clearance(mesh, body_tree, body_normals, patch_tree, patch_normals, chin_z):
    """Folga do corpo e dos retalhos, só perto da superfície (longe dela o sinal em relação a uma malha aberta não vale),
    nos vértices e no meio das faces (triângulos grandes cortam a curva do crânio): rodadas em que a face que ainda fica
    perto demais empurra os seus vértices para fora. Devolve quantos empurrões."""
    pushed = 0
    for _ in range(6):
        moved = 0
        for v in mesh.vertices:
            for tree, normals, reach, gap in ((body_tree, body_normals, 0.03, SCALP_CLEARANCE if v.co.z > chin_z else CLEARANCE),
                                              (patch_tree, patch_normals, 0.01, CLEARANCE)):
                if tree.find_nearest(v.co)[3] > reach:
                    continue
                d, loc, n = signed(tree, normals, v.co.copy())
                if d < gap:
                    v.co = loc + n * gap
                    moved += 1
        for p in mesh.polygons:
            c = sum((mesh.vertices[i].co for i in p.vertices), Vector()) / len(p.vertices)
            if body_tree.find_nearest(c)[3] > 0.03:
                continue
            d, loc, n = signed(body_tree, body_normals, c)
            gap = SCALP_CLEARANCE if c.z > chin_z else CLEARANCE
            if d < gap:
                for i in p.vertices:
                    mesh.vertices[i].co += n * (gap - d)
                moved += 1
        pushed += moved
        if not moved:
            break
    mesh.update()
    return pushed


def clip_frames(action, every):
    a, z = (int(x) for x in action.frame_range)
    return list(range(a, z + 1, every)) + ([z] if (z - a) % every else [])


def crossings(hair, armature, others, frames_by_clip, gap):
    """Vértices do cabelo a menos de `gap` (ou dentro) de alguma parte do corpo sem a cabeça, em algum quadro dos clipes.
    Devolve {índice: pior distância} e a lista (quadro, pior mm, vértices dentro)."""
    bad, rows = {}, []
    for clip, frames in frames_by_clip.items():
        play(armature, bpy.data.actions[clip])
        for f in frames:
            bpy.context.scene.frame_set(f)
            tree, normals = evaluated_bvh(others)
            dg = bpy.context.evaluated_depsgraph_get()
            ev = hair.evaluated_get(dg)
            m = ev.to_mesh()
            worst, inside = 0.03, 0
            for v in m.vertices:
                p = hair.matrix_world @ v.co
                if tree.find_nearest(p)[3] > 0.03:
                    continue
                d = signed(tree, normals, p)[0]
                worst = min(worst, d)
                inside += d < 0
                if d < gap:
                    bad[v.index] = min(bad.get(v.index, 1.0), d)
            ev.to_mesh_clear()
            rows.append((f"{clip}@{f}", round(worst * 1000, 1), inside))
    return bad, rows


def pull_in(mesh, bad, radius=0.03, step=0.12):
    """No repouso, puxa para a linha do meio das costas (x -> 0) e um pouco para trás a região em volta dos vértices que
    cruzam o corpo, com queda suave até `radius`."""
    idx = np.array(list(bad))
    co = np.array([v.co[:] for v in mesh.vertices])
    src = co[idx]
    moved = 0
    for i, v in enumerate(mesh.vertices):
        d = np.linalg.norm(src - co[i], axis=1).min()
        if d >= radius:
            continue
        w = (1 - d / radius) ** 2
        v.co.x -= v.co.x * step * w
        v.co.y += 0.004 * w  # para trás (+Y do Blender é as costas)
        moved += 1
    mesh.update()
    return moved


def inside_horn(tree, normals, p):
    """Ponto dentro do volume do chifre: perto dele e do lado de dentro da face mais próxima. Os chifres correm rentes ao
    crânio: cortar por distância abria um rasgo no cabelo ao longo deles; assim o chifre só sai do cabelo onde o atravessa."""
    loc, _n, idx, dist = tree.find_nearest(p)
    return loc is not None and dist < HORN_REACH and (p - loc).dot(normals[idx]) < 0


def main() -> None:
    src = Path([a for a in sys.argv[sys.argv.index("--") + 1:] if not a.startswith("--")][0]).resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {"bruto": str(src.relative_to(ROOT))}

    # 1. corpo em repouso
    objs = import_glb(BODY)
    armature = next(o for o in objs if o.type == "ARMATURE")
    ad = armature.animation_data
    if ad:
        ad.action = None
        for t in ad.nla_tracks:
            t.mute = True
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    body = [o for o in objs if o.type == "MESH" and o.name.split(".")[0] not in PATCHES]
    patches = [o for o in objs if o.type == "MESH" and o.name.split(".")[0] in PATCHES]
    head = next(o for o in body if o.name.split(".")[0] == "cabeca")
    hp = np.array([(head.matrix_world @ v.co)[:] for v in head.data.vertices])
    cb, rb = head_ellipsoid(hp, hp[:, 2].min() + 0.05 * np.ptp(hp[:, 2]))
    body_tree, body_normals = evaluated_bvh(body)
    patch_tree, patch_normals = evaluated_bvh(patches)
    horns = [o for o in import_glb(HORNS) if o.type == "MESH"]
    horn_tree, horn_normals = evaluated_bvh(horns)
    eyes = next(o for o in patches if o.name.split(".")[0] == "Olhos")
    ep = np.array([(eyes.matrix_world @ v.co)[:] for v in eyes.data.vertices])
    eye_box = (ep.min(axis=0) - EYE_MARGIN, ep.max(axis=0) + EYE_MARGIN)
    bones = {b.name: (armature.matrix_world @ b.head_local) for b in armature.data.bones}
    chin_z = float(hp[:, 2].min()) + 0.18 * float(np.ptp(hp[:, 2]))

    # 2. busto -> espaço do corpo
    hair = merged_mesh(import_glb(src))
    hair.name = hair.data.name = "cabelo"
    hair.data.update()
    fc = np.array([p.center[:] for p in hair.data.polygons])
    fn = np.array([p.normal[:] for p in hair.data.polygons])
    top_z = float(fc[:, 2].max())
    front = (fn[:, 1] < -0.6) & (np.abs(fc[:, 0]) < 0.22 * np.ptp(fc[:, 0]) / 1.18)
    # rosto: a faixa de frente entre o queixo (onde a frente recua) e a testa
    zs = np.linspace(fc[:, 2].min(), top_z, 120)
    fronty = [fc[front & (np.abs(fc[:, 2] - z) < 0.02), 1].min() if (front & (np.abs(fc[:, 2] - z) < 0.02)).any() else np.nan for z in zs]
    fronty = np.array(fronty)
    deepest = int(np.nanargmin(fronty))
    chin_i = next(i for i in range(deepest, -1, -1) if not np.isnan(fronty[i]) and fronty[i] > fronty[deepest] * 0.55)
    chin_model = float(zs[chin_i])
    face = fc[front & (fc[:, 2] > chin_model + 0.07) & (fc[:, 2] < top_z - 0.25)]
    head_h_model = top_z - chin_model
    s0 = head_h_model / float(hp[:, 2].max() - chin_z)
    c0 = np.array([0.0, float(fronty[deepest]) + rb[1] * s0, chin_model + (cb[2] - chin_z) * s0])
    c, s, rms = fit_scaled(face, rb, c0, s0, c_box=np.array([0.05, 0.15, 0.15]))
    report["encaixe"] = {"pontos_rosto": int(len(face)), "escala": round(s, 4), "centro_modelo": np.round(c, 4).tolist(), "rms": round(rms, 4),
                         "queixo_modelo_z": round(chin_model, 4)}
    for v in hair.data.vertices:
        v.co = Vector((cb + (np.array(v.co[:]) - c) / s).tolist())

    # 3. pele do busto: cresce do meio do rosto por arestas suaves
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    # sementes: meio do rosto, peito e alto dos ombros do busto (o vinco queixo/pescoço para o crescimento do rosto)
    centers = {f: f.calc_center_median() for f in bm.faces}
    low_z = min(c.z for c in centers.values())
    seed_pts = [Vector((0.0, float(cb[1] - rb[1]), float(cb[2] - 0.2 * rb[2])))]
    bottom = [f for f, c in centers.items() if c.z < low_z + 0.01]
    if bottom:
        chest = min(bottom, key=lambda f: centers[f].y)
        seed_pts.append(centers[chest].copy())
    seeds = []
    for pt in seed_pts:
        seeds += sorted(bm.faces, key=lambda f: (centers[f] - pt).length)[:12]
    dist_cache = {}

    def near_body(f):
        if f.index not in dist_cache:
            d, _, _ = signed(body_tree, body_normals, f.calc_center_median())
            dist_cache[f.index] = d
        return abs(dist_cache[f.index]) <= GUARD

    hairline_z = float(eye_box[1][2] + HAIRLINE * (hp[:, 2].max() - eye_box[1][2]))
    back_y = float(cb[1] + 0.1 * rb[1])

    def allowed(g):
        c = centers[g]
        if c.z > chin_z and (c.z > hairline_z or c.y > back_y):
            return False  # calota e metade de trás da cabeça são cabelo
        if c.z > chin_z and abs(math.degrees(math.atan2(c.x - cb[0], -(c.y - cb[1])))) > FACE_HALF_DEG:
            return False  # têmporas e lados da cabeça são cabelo
        return near_body(g)

    region, stack = set(seeds), list(seeds)
    while stack:
        f = stack.pop()
        for e in f.edges:
            for g in e.link_faces:
                if g in region or f.normal.angle(g.normal, 0.0) > math.radians(DIHEDRAL_DEG):
                    continue
                if not allowed(g):
                    continue
                region.add(g)
                stack.append(g)
    report["faces_pele_do_busto"] = len(region)
    doomed = set(region)
    # rosto: pele do busto que ficou fora da guarda (queixo e bochechas do busto não batem com o corpo) — faces viradas
    # para a frente, entre as têmporas, do queixo até o topo da janela dos olhos, perto da pele do corpo
    face_left = [f for f, c in centers.items() if f not in doomed and f.normal.y < -0.45 and abs(c.x) < 0.8 * rb[0]
                 and chin_z - 0.01 < c.z < eye_box[1][2] and c.y < cb[1]
                 and body_tree.find_nearest(c)[3] < 0.015]
    doomed |= set(face_left)
    report["faces_do_rosto_do_busto_restantes"] = len(face_left)
    # "todo atrás dos ombros": abaixo do queixo, nada na frente do pescoço
    neck_y = float(bones["neck"].y)
    front_below = [f for f, c in centers.items() if c.z < chin_z and c.y < neck_y]
    doomed |= set(front_below)
    report["faces_na_frente_abaixo_do_queixo"] = len(front_below)
    # abaixo do queixo o cabelo cai: faces quase horizontais são sobra dos ombros do busto (mais largos que os do corpo)
    flaps = [f for f, c in centers.items() if f not in doomed and c.z < chin_z - 0.01 and abs(f.normal.z) > 0.75]
    doomed |= set(flaps)
    report["abas_horizontais_removidas"] = len(flaps)

    # 4. janela dos olhos e chifres
    eye_c = (eye_box[0] + eye_box[1]) / 2
    for f in bm.faces:
        p = f.calc_center_median()
        a = np.array(p[:])
        if (eye_box[0][0] <= a[0] <= eye_box[1][0]) and (eye_box[0][2] <= a[2] <= eye_box[1][2]) and a[1] < eye_c[1] + 0.01:
            doomed.add(f)
        if inside_horn(horn_tree, horn_normals, p) and signed(body_tree, body_normals, p)[0] > 0:
            doomed.add(f)  # só fora da pele: por baixo do chifre, dentro do crânio, é a base aberta dele
    bmesh.ops.delete(bm, geom=list(doomed), context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # ilhas pequenas saem
    bm.faces.ensure_lookup_table()
    seen, comps = set(), []
    for f in bm.faces:
        if f in seen:
            continue
        comp, st = [], [f]
        seen.add(f)
        while st:
            g = st.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h not in seen:
                        seen.add(h)
                        st.append(h)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    small = [f for comp in comps if len(comp) < 0.02 * len(comps[0]) for f in comp]
    report["ilhas"] = {"total": len(comps), "maior": len(comps[0]), "removidas_faces": len(small)}
    bmesh.ops.delete(bm, geom=small, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")

    # 5. mechas fundidas e decimação
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DIST)
    report["lacos_de_borda_antes_de_fechar"] = len(boundary_loops(bm))
    close_holes(bm)
    report["lacos_de_borda_depois_de_fechar"] = len(boundary_loops(bm))
    bm.to_mesh(hair.data)
    bm.free()
    hair.data.calc_loop_triangles()
    report["triangulos_antes"] = len(hair.data.loop_triangles)
    cap = build_cap(head, eyes, cb, report, horn_tree)
    budget = MAX_TRIS - report["calota"]["triangulos"] - 12
    if len(hair.data.loop_triangles) > budget:
        mod = hair.modifiers.new("decimar", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = budget / len(hair.data.loop_triangles) * 0.97
        mod.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = hair
        bpy.ops.object.modifier_apply(modifier=mod.name)

    # DEPOIS da decimação: borda suavizada, volume, a calota junta, folga do corpo e dos retalhos, e o corte dos chifres
    report["hairline_suavizada_vertices"] = smooth_borders(hair)
    report["volume_vertices"] = add_volume(hair.data, cb, float(eye_box[1][2]), float(hp[:, 2].max()))
    pushed = push_clearance(hair.data, body_tree, body_normals, patch_tree, patch_normals, chin_z)
    report["vertices_empurrados_para_a_folga"] = pushed
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    cut = [f for f in bm.faces if inside_horn(horn_tree, horn_normals, f.calc_center_median())
           and signed(body_tree, body_normals, f.calc_center_median())[0] > 0]
    bmesh.ops.delete(bm, geom=cut, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(hair.data)
    bm.free()
    report["faces_cortadas_pelos_chifres_depois"] = len(cut)
    # a calota entra depois do corte dos chifres: ela fica inteira (a parte dentro do chifre nunca aparece), então não há pele
    # entre o cabelo e a base dele
    report["calota"]["empurroes_de_folga"] = push_clearance(cap.data, body_tree, body_normals, patch_tree, patch_normals, chin_z)
    cap_range = (len(hair.data.vertices), len(hair.data.vertices) + len(cap.data.vertices))
    join_into(hair, cap)
    hair.data.calc_loop_triangles()
    report["triangulos"] = len(hair.data.loop_triangles)
    assert report["triangulos"] <= MAX_TRIS, report
    # sem UV: o cabelo é chapado, e as costuras de UV da Meshy fazem o exportador glTF dividir os vértices (bordas abertas e
    # sombreamento quebrado em centenas de laços)
    while hair.data.uv_layers:
        hair.data.uv_layers.remove(hair.data.uv_layers[0])
    for p in hair.data.polygons:
        p.use_smooth = True
    mat = bpy.data.materials.new("cabelo")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb_lin(COLOR)
    b.inputs["Roughness"].default_value = 1.0
    hair.data.materials.clear()
    hair.data.materials.append(mat)
    for o in horns:
        bpy.data.objects.remove(o)

    # 6. pesos por altura
    zb = {n: bones[n].z for n in WEIGHT_BONES}
    neck_top = float(hp[:, 2].min())  # onde a malha da cabeça começa: calota 100% Head daqui para cima
    ladder = [("Head", neck_top), ("neck", zb["neck"]), ("Spine", zb["Spine"]), ("Spine01", zb["Spine01"])]
    groups = {n: hair.vertex_groups.new(name=n) for n in WEIGHT_BONES}
    for v in hair.data.vertices:
        z = (hair.matrix_world @ v.co).z
        if z >= ladder[0][1]:
            groups["Head"].add([v.index], 1.0, "REPLACE")
            continue
        if z <= ladder[-1][1]:
            groups["Spine01"].add([v.index], 1.0, "REPLACE")
            continue
        for (a, za), (b2, zb2) in zip(ladder, ladder[1:]):
            if zb2 <= z <= za:
                t = (za - z) / max(za - zb2, 1e-6)
                groups[a].add([v.index], 1.0 - t, "REPLACE")
                groups[b2].add([v.index], t, "REPLACE")
                break
    report["pesos"] = {"degraus_z_m": {n: round(z, 4) for n, z in ladder}}
    report["pesos"]["calota_copiada_da_pele"] = copy_skin_weights(hair, head, range(*cap_range))
    hair.parent = armature
    hair.matrix_parent_inverse = armature.matrix_world.inverted()
    hair.modifiers.new("Armature", "ARMATURE").object = armature

    # 7. braços e costas: nada do cabelo dentro do corpo (sem a cabeça) em nenhum quadro; a região que cruza é puxada para
    # o meio das costas no repouso, com a folga refeita, em rodadas
    armature.data.pose_position = "POSE"
    others = [o for o in body if o.name.split(".")[0] != "cabeca"]
    frames = {"run-loop": clip_frames(bpy.data.actions["run-loop"], 1), "idle-loop": clip_frames(bpy.data.actions["idle-loop"], 10)}
    rounds = []
    for _ in range(ARM_ROUNDS):
        bad, rows = crossings(hair, armature, others, frames, ARM_GAP)
        rounds.append({"vertices": len(bad), "pior_mm": min(r[1] for r in rows)})
        if not bad:
            break
        armature.data.pose_position = "REST"
        bpy.context.view_layer.update()
        rounds[-1]["movidos"] = pull_in(hair.data, bad)
        push_clearance(hair.data, body_tree, body_normals, patch_tree, patch_normals, chin_z)
        armature.data.pose_position = "POSE"
    report["correcao_bracos"] = rounds
    bad, rows = crossings(hair, armature, others, frames, 0.0)
    report["folga_nos_clipes"] = {k: {"min_mm": w, "vertices_dentro": n} for k, w, n in rows}
    report["pior_mm"] = min(r[1] for r in rows)
    report["pior_quadro"] = min(rows, key=lambda r: r[1])[0]
    report["vertices_dentro_max"] = max(r[2] for r in rows)

    # exportação: armature + cabelo, sem clipes, pelo contrato
    armature.animation_data.action = None
    for t in armature.animation_data.nla_tracks:
        t.mute = True
    armature.data.pose_position = "REST"
    for o in body + patches:
        bpy.data.objects.remove(o)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    bpy.context.scene.frame_set(0)
    report["exportacao"] = export_contract_glb(armature, [armature, hair], OUT, actions=[])
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("CABELO " + json.dumps({k: v for k, v in report.items() if k != "folga_nos_clipes"}, ensure_ascii=False))


main()

"""Funções dos chifres da protagonista v2 (Blender): separar do busto careca da Meshy as peças que saltam da cabeça.

A cabeça do busto é lisa: um elipsoide (eixos alinhados) ajustado aos vértices do crânio, com os pontos que ficam muito
fora descartados em rodadas (os chifres), descreve a cabeça; faces cujo centro fica acima de LIMIAR no raio normalizado
são de chifre; as ilhas conexas dessas faces são as peças.
"""

import bmesh
import bpy
import numpy as np


def merged_mesh(objects):
    """Uma malha, vértices duplicados da Meshy fundidos (sem isso cada triângulo é uma ilha)."""
    meshes = [o for o in objects if o.type == "MESH"]
    for o in objects:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action="DESELECT")
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
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def fit_axis_ellipsoid(pts):
    """Elipsoide de eixos alinhados: a x² + b y² + c z² + d x + e y + f z = 1 (mínimos quadrados)."""
    x, y, z = pts.T
    A = np.stack([x * x, y * y, z * z, x, y, z], axis=1)
    coef, *_ = np.linalg.lstsq(A, np.ones(len(pts)), rcond=None)
    a, b, c, d, e, f = coef
    center = np.array([-d / (2 * a), -e / (2 * b), -f / (2 * c)])
    k = 1 + a * center[0] ** 2 + b * center[1] ** 2 + c * center[2] ** 2
    radii = np.sqrt(k / np.array([a, b, c]))
    return center, radii


def head_ellipsoid(pts, z_from, rounds=6, keep=1.04):
    """Ajusta ao crânio (z >= z_from) descartando, em rodadas, os pontos com raio normalizado > keep (os chifres)."""
    sel = pts[pts[:, 2] >= z_from]
    for _ in range(rounds):
        center, radii = fit_axis_ellipsoid(sel)
        r = np.linalg.norm((sel - center) / radii, axis=1)
        sel = sel[r <= keep]
    return fit_axis_ellipsoid(sel)


def horn_islands(obj, center, radii, z_from, threshold=1.07, min_faces=20):
    """Ilhas de faces fora do elipsoide (raio normalizado do centro da face > threshold), acima de z_from."""
    mesh = obj.data
    fc = np.array([p.center[:] for p in mesh.polygons])
    r = np.linalg.norm((fc - center) / radii, axis=1)
    out = (r > threshold) & (fc[:, 2] >= z_from)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    seen, islands = set(), []
    for i in np.nonzero(out)[0]:
        if i in seen:
            continue
        stack, comp = [int(i)], []
        seen.add(int(i))
        while stack:
            f = bm.faces[stack.pop()]
            comp.append(f.index)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen and out[g.index]:
                        seen.add(g.index)
                        stack.append(g.index)
        if len(comp) >= min_faces:
            islands.append(comp)
    bm.free()
    return islands, r


def neck_z(pts):
    """Pescoço do busto: a fatia mais estreita (largura em x) entre 35% e 75% da altura."""
    lo, hi = pts[:, 2].min(), pts[:, 2].max()
    best = None
    for f in np.linspace(0.35, 0.75, 81):
        z = lo + f * (hi - lo)
        band = pts[np.abs(pts[:, 2] - z) < (hi - lo) * 0.01]
        if len(band) < 5:
            continue
        w = np.ptp(band[:, 0])
        if best is None or w < best[0]:
            best = (w, z)
    return best[1]

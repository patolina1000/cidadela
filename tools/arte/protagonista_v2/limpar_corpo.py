"""Protagonista v2, passo 3: limpeza do corpo escolhido (bruto B, corpo_b_multi_1.glb) em Blender headless.
Aval do Arthur em 29/09/2026: geração B, cabeça 18% da altura, 0,80 m. Sem rosto e sem rig.

1. Uma malha, vértices duplicados fundidos; 0,80 m, pés em z = 0, pivô entre os pés, frente -Y do Blender (+Z glTF).
2. Simetria em X (fica o lado com a frente da cabeça mais lisa).
3. Cabeça escalada a partir da base do pescoço até 18% da altura, como no estudo (render_estudo_cabeca.py, marcos
   de assets/previews/protagonista_v2/estudo_cabeca.json), e a figura inteira de volta a 0,80 m.
4. Perfil: um pouco de glúteo (até 6 mm para trás) e de curva lombar (3 mm para dentro), só deslocando vértices.
5. Taubin (preserva volume): corpo leve, pernas com passe extra, passes fortes onde a folha tinha anatomia marcada
   (clavícula e esterno, joelhos) e nas bordas do short gravadas; mãos fora (meio fechadas, preservadas). Cabeça
   subdividida e alisada até a frente ficar lisa para os retalhos (RMS ≤ 1,5 mm, máx ≤ 3 mm, medida do aldeão).
6. Decimação com simetria segurando juntas e mãos; depois cortes retos no cós e na bainha do short (borda limpa
   entre pele e tecido). Total ≤ 2.500 triângulos.
7. Regiões do contrato por posição: cabeca, tronco, bracos, maos, quadril, roupa_intima, coxas, canelas, pes.
   roupa_intima = o short (material "tecido"); quadril = a faixa de pele da bacia acima do cós (a calça esconde as
   duas juntas, data/equipment.json). Normais suaves calculadas na malha inteira e copiadas para as peças (sem
   costura de luz nas bordas).
Saída: assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb (sem rig) e protagonista_corpo_limpeza.json.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/limpar_corpo.py
"""

import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
from corpo_lib import ROOT, face_flatness, head_box, import_glb  # noqa: E402

SRC = ROOT / "assets/modelos/protagonista_v2/meshy/corpo_b_multi_1.glb"
DST = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
STUDY = ROOT / "assets/previews/protagonista_v2/estudo_cabeca.json"
HEIGHT = 0.80
HEAD_RATIO = 0.18
RAMP = 0.015
MAX_TRIANGLES = 2500
# Orçamento da decimação por parte (antes dos cortes do short, que somam ~220 no corpo): as mãos quase somem de cima,
# a cabeça domina na câmera do jogo e leva a sobra.
POST_HEAD_PASSES, POST_HAND_PASSES = 0, 4  # na cabeça piorava a frente (medida e olho)
BUDGETS = {"maos": 200, "cabeca": 620, "corpo": 1350}  # + ~85 na borda entre as partes
TARGET_RMS_MM, TARGET_MAX_MM = 0.5, 1.5  # calombos na janela do rosto (face_roughness)
LAMBDA, MU = 0.5, -0.53
PELE, TECIDO = "#91ADB7", "#3F3342"

# Marcos do bruto B a 0,80 m, antes de escalar a cabeça (régua em 2 cm: frente, lado e costas).
Z = {"cos": 0.50, "quadril_topo": 0.52, "bainha": 0.355, "joelho": 0.215, "tornozelo": 0.05, "axila": 0.595,
     "punho": 0.405, "gluteo": 0.405, "lombar": 0.51, "clavicula": (0.56, 0.645), "cotovelo": (0.46, 0.52)}
ARM_X_LOW, ARM_X_SHOULDER = 0.095, 0.062  # |x| a partir do qual é braço: abaixo do cós / da axila para cima
HAND_X = 0.15


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


def pts_of(obj):
    return np.array([v.co[:] for v in obj.data.vertices])


def set_pts(obj, p):
    obj.data.vertices.foreach_set("co", np.asarray(p, dtype=np.float64).ravel())
    obj.data.update()


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
    return obj


def cleanup(obj, dist):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def normalize(obj, height=HEIGHT):
    p = pts_of(obj)
    low, high = p.min(axis=0), p.max(axis=0)
    s = height / (high[2] - low[2])
    feet = p[p[:, 2] < low[2] + (high[2] - low[2]) * 0.03]
    c = np.array([(feet[:, 0].min() + feet[:, 0].max()) / 2, (feet[:, 1].min() + feet[:, 1].max()) / 2, low[2]])
    set_pts(obj, (p - c) * s)


def symmetrize(obj, keep_positive):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=keep_positive,
                           clear_outer=not keep_positive, dist=1e-6)
    bm.to_mesh(obj.data)
    bm.free()
    mod = obj.modifiers.new("espelho", "MIRROR")
    mod.use_axis[0] = True
    mod.use_mirror_merge = True
    mod.merge_threshold = 1e-4
    mod.use_clip = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    cleanup(obj, 1e-5)


def side_rms(p):
    out = {}
    for name, sel in (("+x", p[p[:, 0] >= 0]), ("-x", p[p[:, 0] <= 0])):
        both = np.vstack([sel, sel * [-1, 1, 1]])
        out[name] = face_flatness(both, head_box(both))["olhos"].get("rms_mm", 99)
    return out


def scale_head(obj, marks):
    """Cabeça uniforme a partir da base do pescoço (faixa de RAMP abaixo só alarga em x/y) e volta a 0,80 m."""
    base, top, chin = marks["base_pescoco_z"], marks["topo_z"], marks["queixo_z"]
    s = HEAD_RATIO * base / ((top - chin) - HEAD_RATIO * (top - base))
    p = pts_of(obj)
    ring = p[np.abs(p[:, 2] - base) < 0.004]
    pivot = np.array([ring[:, 0].mean(), ring[:, 1].mean(), base])
    above = p[:, 2] >= base
    p[above] = pivot + (p[above] - pivot) * s
    band = (p[:, 2] < base) & (p[:, 2] > base - RAMP)
    w = (p[band, 2] - (base - RAMP)) / RAMP
    p[band, :2] = pivot[:2] + (p[band, :2] - pivot[:2]) * (1 + (s - 1) * w)[:, None]
    k = HEIGHT / p[:, 2].max()
    set_pts(obj, p * k)
    return s, k


def is_arm(p, k):
    """Braço por posição (pose A): de lado do tronco abaixo do cós, e do ombro para fora da axila para cima."""
    ax, z = np.abs(p[:, 0]), p[:, 2]
    low = (z < Z["axila"] * k) & (ax > ARM_X_LOW * k)
    high = (z >= (Z["axila"] - 0.02) * k) & (z < 0.68 * k) & (ax > ARM_X_SHOULDER * k)
    return low | high


def is_hand(p, k):
    return is_arm(p, k) & (p[:, 2] < Z["punho"] * k) & (np.abs(p[:, 0]) > HAND_X * k)


def gauss(x, c, s):
    return np.exp(-((x - c) / s) ** 2)


def shape_profile(obj, k):
    """Glúteo um pouco para trás (+Y) e curva lombar um pouco para dentro; nenhum vértice novo."""
    p = pts_of(obj)
    body = ~is_arm(p, k)
    pel = p[body & (p[:, 2] > 0.36 * k) & (p[:, 2] < 0.52 * k)]
    yc = (pel[:, 1].min() + pel[:, 1].max()) / 2
    back = np.clip((p[:, 1] - yc) / (0.03 * k), 0, 1) * body
    ax = np.abs(p[:, 0])
    glute = 0.006 * k * gauss(p[:, 2], Z["gluteo"] * k, 0.035 * k) * gauss(ax, 0.03 * k, 0.035 * k)
    lumbar = -0.003 * k * gauss(p[:, 2], Z["lombar"] * k, 0.03 * k) * gauss(p[:, 0], 0, 0.045 * k)
    p[:, 1] += back * (glute + lumbar)
    set_pts(obj, p)


def subdivide(obj, mask):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    faces = [f for f in bm.faces if all(mask[v.index] for v in f.verts)]
    edges = list({e for f in faces for e in f.edges})
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True, smooth=0.0)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def taubin(obj, weights, passes):
    mesh = obj.data
    n = len(mesh.vertices)
    pos = pts_of(obj)
    edges = np.array([e.vertices[:] for e in mesh.edges])
    deg = np.bincount(edges.ravel(), minlength=n).astype(float)
    deg[deg == 0] = 1
    w = weights[:, None]
    for _ in range(passes):
        for f in (LAMBDA, MU):
            acc = np.zeros_like(pos)
            np.add.at(acc, edges[:, 0], pos[edges[:, 1]])
            np.add.at(acc, edges[:, 1], pos[edges[:, 0]])
            pos += f * w * (acc / deg[:, None] - pos)
    set_pts(obj, pos)


def smooth_body(obj, k, neck_z, base_z):
    p = pts_of(obj)
    z, ax = p[:, 2], np.abs(p[:, 0])
    hand = is_hand(p, k)
    arm = is_arm(p, k)
    body = (z < neck_z - 0.01).astype(float)
    body[hand] = 0
    taubin(obj, body, 6)
    legs = ((z < Z["bainha"] * k + 0.01) & ~arm).astype(float)
    taubin(obj, legs, 10)
    ymid = np.median(p[(z > Z["clavicula"][0] * k) & (z < Z["clavicula"][1] * k) & ~arm, 1])
    chest = (z > Z["clavicula"][0] * k) & (z < Z["clavicula"][1] * k) & (p[:, 1] < ymid) & (ax < 0.075 * k)
    knees = (z > (Z["joelho"] - 0.035) * k) & (z < (Z["joelho"] + 0.035) * k) & ~arm
    hems = ((np.abs(z - Z["bainha"] * k) < 0.02 * k) | (np.abs(z - Z["cos"] * k) < 0.02 * k)) & ~arm
    elbows = arm & ~hand & (z > Z["cotovelo"][0] * k) & (z < Z["cotovelo"][1] * k)
    neck = (np.abs(z - base_z) < 0.02) & ~arm  # dobra da escala da cabeça
    taubin(obj, (chest | knees | hems | elbows | neck).astype(float), 25)
    return {"marcados": {"clavicula_esterno": int(chest.sum()), "joelhos": int(knees.sum()),
                         "bordas_do_short": int(hems.sum()), "cotovelos": int(elbows.sum()),
                         "base_do_pescoco": int(neck.sum()), "maos_fora": int(hand.sum())}}


def face_roughness(p, chin_z):
    """Calombos na janela do rosto (contrato: ±45° em volta da frente), do queixo até 70% da cabeça: resíduo de
    uma superfície cúbica y = f(x, z) ajustada aos vértices da janela. Mede só o que não é o formato (ovo, queixo)."""
    top = p[:, 2].max()
    head = p[p[:, 2] >= chin_z]
    cx, cy = (head[:, 0].min() + head[:, 0].max()) / 2, (head[:, 1].min() + head[:, 1].max()) / 2
    ang = np.degrees(np.arctan2(p[:, 0] - cx, -(p[:, 1] - cy)))  # 0 = de frente (-Y)
    win = (np.abs(ang) <= 45) & (p[:, 2] >= chin_z) & (p[:, 2] <= chin_z + 0.7 * (top - chin_z)) & (p[:, 1] < cy)
    w = p[win]
    x, z = (w[:, 0] - cx) / 0.05, (w[:, 2] - chin_z) / 0.05
    a = np.stack([np.ones_like(x), x, z, x * x, x * z, z * z, x ** 3, x * x * z, x * z * z, z ** 3], axis=1)
    coef, *_ = np.linalg.lstsq(a, w[:, 1], rcond=None)
    r = (w[:, 1] - a @ coef) * 1000
    return {"pontos": int(win.sum()), "rms_mm": round(float(np.sqrt((r ** 2).mean())), 2), "max_mm": round(float(np.abs(r).max()), 2)}


def smooth_head(obj, base_z, chin_z):
    p = pts_of(obj)
    subdivide(obj, p[:, 2] >= base_z - 0.02)
    passes = 0
    while True:
        p = pts_of(obj)
        w = np.clip((p[:, 2] - (base_z - 0.015)) / 0.02, 0, 1)
        step = 20 if passes == 0 else 10
        taubin(obj, w, step)
        passes += step
        rough = face_roughness(pts_of(obj), chin_z)
        if (rough["rms_mm"] <= TARGET_RMS_MM and rough["max_mm"] <= TARGET_MAX_MM) or passes >= 90:
            return passes, rough


def region_masks(obj, k, neck_z):
    p = pts_of(obj)
    z, ax = p[:, 2], np.abs(p[:, 0])
    arm, hand = is_arm(p, k), is_hand(p, k)
    joints = np.zeros(len(p), bool)
    joints |= (z > neck_z - 0.03) & (z < neck_z + 0.01)  # pescoço
    joints |= (z > (Z["axila"] - 0.04) * k) & (z < 0.66 * k) & (ax > 0.045 * k)  # ombros
    joints |= arm & (z > Z["cotovelo"][0] * k) & (z < Z["cotovelo"][1] * k)  # cotovelos
    joints |= arm & (z > (Z["punho"] - 0.015) * k) & (z < (Z["punho"] + 0.02) * k)  # punhos
    joints |= ~arm & (z > (Z["bainha"] - 0.02) * k) & (z < (Z["cos"] - 0.06) * k)  # quadris
    joints |= ~arm & (np.abs(z - Z["joelho"] * k) < 0.035 * k)  # joelhos
    joints |= ~arm & (np.abs(z - Z["tornozelo"] * k) < 0.02 * k)  # tornozelos
    head = z >= neck_z
    return {"maos": hand, "cabeca": head & ~hand, "corpo": ~hand & ~head}, joints


def tri_counts(obj, masks):
    obj.data.calc_loop_triangles()
    out = {name: 0 for name in masks}
    for t in obj.data.loop_triangles:
        for name, m in masks.items():
            if all(m[i] for i in t.vertices):
                out[name] += 1
                break
    return out, len(obj.data.loop_triangles)


def decimate_part(obj, weight, remove):
    """Uma etapa de decimação: só colapsa onde o peso > 0 (peso 0 trava o vértice), até tirar `remove` triângulos."""
    obj.data.calc_loop_triangles()
    tris = len(obj.data.loop_triangles)
    if remove <= 0:
        return
    g = obj.vertex_groups.new(name="decimar")
    for w in np.unique(weight):
        g.add([int(i) for i in np.nonzero(weight == w)[0]], float(w), "REPLACE")
    mod = obj.modifiers.new("decimar", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = (tris - remove) / tris
    mod.use_collapse_triangulate = True
    mod.use_symmetry = True
    mod.symmetry_axis = "X"
    mod.vertex_group = "decimar"
    mod.vertex_group_factor = 4.0
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.vertex_groups.clear()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def decimate(obj, k, neck_z, budgets):
    """Decimação por orçamento, em etapas: mãos, cabeça e o resto do corpo (com as juntas seguras), cada etapa com as
    outras partes travadas. Assim a conta de triângulos de cada parte é a pedida, e não o que os pesos derem."""
    steps = []
    for part in ("maos", "cabeca", "corpo"):
        masks, joints = region_masks(obj, k, neck_z)
        counts, _ = tri_counts(obj, masks)
        weight = np.where(masks[part], np.where(joints & (part == "corpo"), 0.12, 1.0), 0.0)
        decimate_part(obj, weight, counts[part] - budgets[part])
        after, total = tri_counts(obj, region_masks(obj, k, neck_z)[0])
        steps.append({"parte": part, "antes": counts, "depois": after, "total": total})
    return steps


def cut_short(obj, k):
    """Cortes retos (planos horizontais) no cós e na bainha, só no tronco e nas pernas: a troca de pele para tecido é a
    única borda de região que aparece com o corpo inteiro visível. As outras bordas seguem as faces (ficam sob a roupa
    que esconde a região; cortá-las custaria ~700 triângulos)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    added = []
    for zc in (Z["cos"] * k, Z["bainha"] * k):
        before = sum(len(f.verts) - 2 for f in bm.faces)
        faces = [f for f in bm.faces if not is_arm(np.array([f.calc_center_median()[:]]), k)[0]]
        geom = list({e for f in faces for e in f.edges}) + faces + list({v for f in faces for v in f.verts})
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, zc), plane_no=(0, 0, 1), dist=1e-5)
        added.append(sum(len(f.verts) - 2 for f in bm.faces) - before)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    return added


def wrist_planes(obj, k):
    """Plano do punho de cada lado: pelo centro do braço na altura do punho, normal na direção do antebraço."""
    p = pts_of(obj)
    planes = []
    for sign in (1, -1):
        side = is_arm(p, k) & (sign * p[:, 0] > 0)
        wrist = p[side & (np.abs(p[:, 2] - Z["punho"] * k) < 0.006)].mean(axis=0)
        elbow = p[side & (np.abs(p[:, 2] - sum(Z["cotovelo"]) / 2 * k) < 0.006)].mean(axis=0)
        planes.append((wrist, (wrist - elbow) / np.linalg.norm(wrist - elbow)))
    return planes


def hand_side(c, k, wrist_planes):
    return np.array([any(np.dot(ci - w, d) > 0 and np.sign(ci[0]) == np.sign(w[0]) for w, d in wrist_planes) for ci in c])


def regions(obj, k, neck_z, planes):
    """Região de cada face pelo centro."""
    obj.data.calc_loop_triangles()
    c = np.array([f.center[:] for f in obj.data.polygons])
    z = c[:, 2]
    arm = is_arm(c, k)
    hand = arm & hand_side(c, k, planes)
    reg = np.full(len(c), "tronco", dtype=object)
    reg[z >= neck_z] = "cabeca"
    reg[~arm & (z < Z["quadril_topo"] * k)] = "quadril"
    reg[~arm & (z < Z["cos"] * k)] = "roupa_intima"
    reg[~arm & (z < Z["bainha"] * k)] = "coxas"
    reg[~arm & (z < Z["joelho"] * k)] = "canelas"
    reg[~arm & (z < Z["tornozelo"] * k)] = "pes"
    reg[arm & (z < neck_z)] = "bracos"
    reg[hand] = "maos"
    return reg


def split(obj, reg, mats):
    """Separa por região; cada peça leva as normais suaves da malha inteira (bordas sem costura de luz)."""
    mesh = obj.data
    vnorm = np.array([v.normal[:] for v in mesh.vertices])
    vpos = pts_of(obj)
    names = ["cabeca", "tronco", "bracos", "maos", "quadril", "roupa_intima", "coxas", "canelas", "pes"]
    out = {}
    for name in names:
        idx = [i for i, r in enumerate(reg) if r == name]
        if not idx:
            continue
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        keep = set(idx)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        new = bpy.data.meshes.new(name)
        bm.to_mesh(new)
        bm.free()
        piece = bpy.data.objects.new(name, new)
        bpy.context.scene.collection.objects.link(piece)
        new.materials.append(mats["tecido" if name == "roupa_intima" else "pele"])
        for f in new.polygons:
            f.use_smooth = True
        # normal de cada vértice = a do vértice na mesma posição da malha inteira
        p = pts_of(piece)
        d = ((p[:, None, :] - vpos[None, :, :]) ** 2).sum(axis=2)
        new.normals_split_custom_set_from_vertices([tuple(vnorm[j]) for j in d.argmin(axis=1)])
        new.calc_loop_triangles()
        out[name] = {"triangulos": len(new.loop_triangles), "vertices": len(new.vertices)}
    bpy.data.objects.remove(obj)
    return out


def material(name, hexcolor):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb(hexcolor)
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.0
    return m


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = single_object(import_glb(SRC))
    report = {"entrada": str(SRC.relative_to(ROOT)), "triangulos_entrada": len(obj.data.polygons)}
    normalize(obj)
    before = len(obj.data.vertices)
    cleanup(obj, 1e-5)
    report["vertices_fundidos"] = before - len(obj.data.vertices)

    sides = side_rms(pts_of(obj))
    keep_positive = sides["+x"] <= sides["-x"]
    symmetrize(obj, keep_positive)
    normalize(obj)
    report["simetria"] = {"lado_mantido": "+x" if keep_positive else "-x", "rms_frente_da_cabeca_mm": sides}

    marks = json.loads(STUDY.read_text())["marcos_bruto_b"]
    s, k = scale_head(obj, marks)
    neck_z = (marks["base_pescoco_z"] + s * (marks["pescoco_z"] - marks["base_pescoco_z"])) * k
    chin_z = (marks["base_pescoco_z"] + s * (marks["queixo_z"] - marks["base_pescoco_z"])) * k
    report["cabeca"] = {"fator": round(s, 4), "escala_do_corpo_k": round(k, 4), "pescoco_z": round(neck_z, 4),
                        "queixo_z": round(chin_z, 4)}

    shape_profile(obj, k)
    base_z = marks["base_pescoco_z"] * k
    report["alisamento"] = smooth_body(obj, k, neck_z, base_z)
    passes, rough = smooth_head(obj, base_z, chin_z)
    report["alisamento"]["passos_cabeca"] = passes
    report["alisamento"]["rosto_calombos_antes_de_decimar"] = rough
    report["decimacao"] = decimate(obj, k, neck_z, BUDGETS)
    # Depois de decimar: a cabeça (que domina de cima) e as mãos passam por um Taubin leve, sem mudar a contagem:
    # tira os entalhes que a decimação deixa na frente da cabeça e as pontas das mãos.
    p = pts_of(obj)
    head_w = np.clip((p[:, 2] - (base_z - 0.01)) / 0.02, 0, 1)
    taubin(obj, head_w, POST_HEAD_PASSES)
    taubin(obj, is_hand(pts_of(obj), k).astype(float), POST_HAND_PASSES)
    report["alisamento"]["depois_de_decimar"] = {"passos_cabeca": POST_HEAD_PASSES, "passos_maos": POST_HAND_PASSES}
    report["cortes_do_short_triangulos"] = cut_short(obj, k)
    planes = wrist_planes(obj, k)
    report["punhos"] = [{"ponto": [round(float(x), 4) for x in w], "normal": [round(float(x), 3) for x in d]} for w, d in planes]
    normalize(obj)  # o alisamento encolhe um nada
    p = pts_of(obj)
    report["rosto_calombos"] = face_roughness(p, chin_z)
    report["rosto_medida_do_aldeao_elipsoide"] = face_flatness(p, head_box(p))["olhos"]
    top = float(p[:, 2].max())
    report["altura_m"] = round(top, 4)
    report["cabeca_sobre_altura"] = round((top - chin_z) / top, 4)

    mats = {"pele": material("pele", PELE), "tecido": material("tecido", TECIDO)}
    for f in obj.data.polygons:
        f.use_smooth = True
    obj.data.update()
    reg = regions(obj, k, neck_z, planes)
    report["regioes"] = split(obj, reg, mats)
    report["triangulos_total"] = sum(r["triangulos"] for r in report["regioes"].values())
    assert report["triangulos_total"] <= MAX_TRIANGLES, report["triangulos_total"]

    bpy.ops.object.select_all(action="SELECT")
    DST.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(DST), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_materials="EXPORT", export_animations=False, export_skins=False,
                              export_normals=True)
    DST.with_name("protagonista_corpo_limpeza.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("LIMPEZA " + json.dumps(report, ensure_ascii=False))


main()

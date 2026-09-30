"""Protagonista v2: extrai os chifres do busto da Meshy e encaixa na cabeça do corpo limpo em repouso (Blender headless).

1. Busto da Meshy numa malha (vértices fundidos). Elipsoide do crânio do busto (chifres descartados em rodadas).
2. Ilhas de faces que saltam do elipsoide (chifres_lib). A geração 1 veio com QUATRO chifres: a Meshy pôs os da vista
   de frente e os da vista de costas em profundidades diferentes. Ficam as ilhas do par da frente (y normalizado < 0,3),
   que bate com o perfil da folha (o chifre logo à frente do meio do crânio); as de trás e o queixo saem.
3. Cada chifre ganha BASE_RINGS anéis de faces do crânio em volta da base (entra no crânio) e é levado ao crânio
   do corpo: p' = c_corpo + (p - c_busto) * (r_corpo / r_busto), escala por eixo (o busto é ~5% mais estreito).
   Vértices da base que ficariam fora da pele do corpo são puxados para dentro até EMBED do raio (sem fresta).
4. Inclinação ajustável (--inclinacao=N graus para trás, em volta do eixo X pela base de cada chifre; 0 = como na folha)
   e tamanho (--escala=S, cada chifre em volta do centro da própria base; a base volta a assentar no crânio).
   Decisão do Arthur em 29/09/2026: 20° para trás e 1,3×.
5. Decimação do par a ≤ MAX_TRIS, facetado, material "chifre" #2B2140, rígido, no espaço do corpo em repouso.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/extrair_chifres.py -- <glb_meshy> [--inclinacao=N] [--escala=S] [--saida=arquivo.glb]
Saída: assets/modelos/protagonista_v2/chifres.glb e chifres.json
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
from chifres_lib import head_ellipsoid, horn_islands, merged_mesh, neck_z  # noqa: E402
from corpo_lib import ROOT, import_glb  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
OUT = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--saida=")),
                ROOT / "assets/modelos/protagonista_v2/chifres.glb")).resolve()
COLOR = "#2B2140"
MAX_TRIS = 300
BASE_RINGS = 2  # anéis de faces do crânio em volta de cada chifre (a base entra no crânio)
EMBED = 0.97  # base puxada para dentro até este raio normalizado do crânio do corpo
SCALE = float(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--escala=")), 1.0))  # tamanho, pela base
SEAT_R = 1.03  # depois de escalar: o que fica até este raio normalizado volta para EMBED (base assentada)
TILT_DEG = float(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--inclinacao=")), 0.0))  # + = para trás
FRONT_MAX_Y = 0.3  # ilhas com centro (y normalizado) atrás disto são a duplicata da vista de costas


def srgb_lin(h):
    h = h.lstrip("#")
    return tuple(((int(h[i:i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 if int(h[i:i + 2], 16) / 255 > 0.04045
                 else int(h[i:i + 2], 16) / 255 / 12.92 for i in (0, 2, 4)) + (1.0,)


def main() -> None:
    src = Path([a for a in sys.argv[sys.argv.index("--") + 1:] if not a.startswith("--")][0]).resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body = [o for o in import_glb(BODY) if o.type == "MESH"]
    head = next(o for o in body if o.name.split(".")[0] == "cabeca")
    hp = np.array([(head.matrix_world @ v.co)[:] for v in head.data.vertices])
    cb, rb = head_ellipsoid(hp, hp[:, 2].min() + 0.05 * np.ptp(hp[:, 2]))  # cabeça do corpo do pescoço para cima
    for o in body:
        bpy.data.objects.remove(o)

    bust = merged_mesh(import_glb(src))
    pts = np.array([v.co[:] for v in bust.data.vertices])
    nz = neck_z(pts)
    # o mesmo ajuste nos dois: a cabeça do pescoço para cima (uma calota sozinha não define o elipsoide)
    cseg, rseg = head_ellipsoid(pts, nz + 0.05 * np.ptp(pts[:, 2]))
    cs, rs = cseg, rseg
    islands, rad = horn_islands(bust, cseg, rseg, nz)
    fc = np.array([p.center[:] for p in bust.data.polygons])
    chosen = []
    for comp in islands:
        n = ((fc[comp] - cseg) / rseg).mean(axis=0)
        if n[2] > 0 and n[1] < FRONT_MAX_Y:
            chosen.append((comp, n))
    assert len(chosen) == 2, f"esperava 2 chifres na frente, achei {len(chosen)}"
    report = {"bruto": str(src.relative_to(ROOT)), "saida": str(OUT), "ilhas": len(islands), "aneis_da_base": BASE_RINGS, "escolhidas_centro_norm": [np.round(n, 2).tolist() for _, n in chosen],
              "cabeca_busto": {"centro": np.round(cs, 4).tolist(), "raios": np.round(rs, 4).tolist()},
              "cabeca_corpo": {"centro": np.round(cb, 4).tolist(), "raios": np.round(rb, 4).tolist()},
              "escala_por_eixo": np.round(rb / rs, 5).tolist()}

    # base: faces vizinhas até BASE_R entram (o chifre sai de dentro do crânio)
    bm = bmesh.new()
    bm.from_mesh(bust.data)
    bm.faces.ensure_lookup_table()
    keep = set()
    for comp, _ in chosen:
        region = set(comp)
        frontier = list(comp)
        for _ in range(BASE_RINGS):  # só alguns anéis: o crânio inteiro tem raio perto de 1
            nxt = []
            for i in frontier:
                for e in bm.faces[i].edges:
                    for g in e.link_faces:
                        if g.index not in region:
                            region.add(g.index)
                            nxt.append(g.index)
            frontier = nxt
        keep |= region
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # espaço do corpo, escala por eixo; base para dentro do crânio do corpo
    moved = 0
    for v in bm.verts:
        p = cb + (np.array(v.co[:]) - cs) * (rb / rs)
        n = (p - cb) / rb
        r = np.linalg.norm(n)
        if r < 1.0:  # dentro ou na pele: afunda até EMBED
            p = cb + n / r * min(r, EMBED) * rb
            moved += 1
        v.co = Vector(p.tolist())
    report["vertices_da_base_afundados"] = moved
    if TILT_DEG:
        for comp_verts in [bm.verts]:  # inclinação: em volta do X, pelo ponto mais baixo de cada lado
            for side in (1, -1):
                vs = [v for v in comp_verts if v.co.x * side > 0]
                pivot = min(vs, key=lambda v: v.co.z).co.copy()
                # rotação em X: ângulo negativo leva a ponta para +Y do Blender (para trás)
                rot = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(-TILT_DEG), 4, "X") @ Matrix.Translation(-pivot)
                for v in vs:
                    v.co = rot @ v.co
    if SCALE != 1.0:  # cada chifre cresce em volta do centro da própria base; a base é reassentada no crânio
        seated = 0
        for side in (1, -1):
            vs = [v for v in bm.verts if v.co.x * side > 0]
            base = [v for v in vs if np.linalg.norm((np.array(v.co[:]) - cb) / rb) < 1.0]
            pivot = sum((v.co for v in base), Vector()) / max(1, len(base))
            for v in vs:
                v.co = pivot + (v.co - pivot) * SCALE
            for v in vs:
                n = (np.array(v.co[:]) - cb) / rb
                r = np.linalg.norm(n)
                if r < SEAT_R:
                    v.co = Vector((cb + n / r * min(r, EMBED) * rb).tolist())
                    seated += 1
        report["vertices_reassentados"] = seated
    report["escala"] = SCALE
    mesh = bpy.data.meshes.new("chifres")
    bm.to_mesh(mesh)
    bm.free()
    horns = bpy.data.objects.new("chifres", mesh)
    bpy.context.scene.collection.objects.link(horns)
    bpy.data.objects.remove(bust)
    mesh.calc_loop_triangles()
    report["triangulos_antes"] = len(mesh.loop_triangles)
    if len(mesh.loop_triangles) > MAX_TRIS:
        mod = horns.modifiers.new("decimar", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = MAX_TRIS / len(mesh.loop_triangles) * 0.97
        mod.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = horns
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mesh.calc_loop_triangles()
    report["triangulos"] = len(mesh.loop_triangles)
    assert report["triangulos"] <= MAX_TRIS, report
    for p in mesh.polygons:
        p.use_smooth = False  # facetado, como cristal escurecido
    mat = bpy.data.materials.new("chifre")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb_lin(COLOR)
    b.inputs["Roughness"].default_value = 0.8
    mesh.materials.append(mat)
    v = np.array([x.co[:] for x in mesh.vertices])
    report["caixa_blender_m"] = [np.round(v.min(0), 4).tolist(), np.round(v.max(0), 4).tolist()]
    report["por_lado"] = {("direito" if s < 0 else "esquerdo"): {"altura_mm": round(float(np.ptp(v[v[:, 0] * s > 0][:, 2])) * 1000, 1),
                                                                 "topo_z_m": round(float(v[v[:, 0] * s > 0][:, 2].max()), 4)}
                          for s in (-1, 1)}
    report["topo_da_cabeca_z_m"] = round(float(hp[:, 2].max()), 4)
    report["inclinacao_graus"] = TILT_DEG
    bpy.ops.object.select_all(action="DESELECT")
    horns.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_materials="EXPORT")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("CHIFRES " + json.dumps(report, ensure_ascii=False))


main()

"""Toco de árvore (opção de estado esgotado, para o Arthur decidir): um por variação da árvore revisão 3.

O toco é a base da própria árvore: arvore.build refaz a árvore com a mesma semente (mesma torção, inclinação e giro)
e ela é cortada na altura do toco, com 3 raízes curtas saindo do pé. A borda do corte fica serrilhada (dentes alternados, lascado à Tim Burton) e a
face de cima leva a cor da madeira do jogo (#6B5B4B, data/items.json), que é o que se vê de cima.
≤ 60 triângulos, 0,10–0,20 m. Metros, frente +Z, pivô no centro da base.

Uso, na raiz da worktree:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/toco.py
Saída: assets/cenario/arvore/toco_1..4.glb e toco_relatorio.json.
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arvore import VARIACOES, build, material  # noqa: E402
from cenario_lib import ROOT, block, export, join, write_report  # noqa: E402

OUT = ROOT / "assets/cenario/arvore"
MAX_TRIS = 60
CORTE = "#6B5B4B"  # madeira (data/items.json)
ALTURA = {"gota": 0.11, "dupla": 0.14, "tufos": 0.13, "alta": 0.10}  # corte; os dentes sobem mais 5 cm
DENTE = 0.05
RAIZES = 3  # raízes curtas e pontudas saindo do pé: sem elas o toco parece um bloco de madeira


def cut(obj, height):
    """Corta a árvore em z = height, serrilha a borda e fecha com um leque na cor da madeira."""
    mat_corte = material("corte", CORTE)
    obj.data.materials.append(mat_corte)
    corte_idx = len(obj.data.materials) - 1
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, height), plane_no=(0, 0, 1), clear_outer=True)
    # sobra só a base do tronco; o laço aberto de cima é o do corte (o de baixo fica enterrado no chão)
    bm.edges.ensure_lookup_table()
    top = [e for e in bm.edges if e.is_boundary and all(abs(v.co.z - height) < 1e-3 for v in e.verts)]
    loop, e0 = [], top[0]
    v = e0.verts[0]
    used = set()
    while True:
        loop.append(v)
        nxt = [e for e in v.link_edges if e in top and e not in used]
        if not nxt:
            break
        used.add(nxt[0])
        v = nxt[0].other_vert(v)
        if v is loop[0]:
            break
    center = sum((x.co for x in loop), Vector()) / len(loop)
    for i, x in enumerate(loop):
        if i % 2 == 0:
            x.co.z += DENTE
    c = bm.verts.new(center - Vector((0, 0, 0.01)))  # miolo um pouco fundo
    for a, b in zip(loop, loop[1:] + loop[:1]):
        f = bm.faces.new((a, b, c))
        f.material_index = corte_idx
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    # tira do GLB o material da copa, que não sobrou em nenhuma face
    used_idx = {p.material_index for p in obj.data.polygons}
    for i in reversed(range(len(obj.data.materials))):
        if i not in used_idx:
            obj.data.materials.pop(index=i)


def roots(obj, seed):
    """Raízes: lascas pontudas quase deitadas, saindo do pé para fora em ângulos sorteados, na cor do tronco."""
    rng = random.Random(seed)
    tronco = next(m for m in obj.data.materials if m.name.startswith("tronco"))
    r_pe = max(math.hypot(v.co.x, v.co.y) for v in obj.data.vertices if v.co.z < 0.03)
    parts = [obj]
    start = rng.uniform(0, 360)
    for k in range(RAIZES):
        a = math.radians(start + k * 360 / RAIZES + rng.uniform(-25, 25))
        size = (0.045, 0.035, rng.uniform(0.07, 0.10))
        c = (math.cos(a) * r_pe * 0.8, math.sin(a) * r_pe * 0.8, 0.025)
        o = block(rng, size, c, 5, 72, math.degrees(a), 0, jitter=0.1, point_z=0.5, name=f"raiz_{k}", smooth=False)
        o.data.materials.append(tronco)
        parts.append(o)
    return join(parts, obj.name)


def main():
    rows = []
    for index, spec in enumerate(VARIACOES, start=1):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = build(spec, index)
        cut(obj, ALTURA[spec["nome"]])
        obj.name = obj.data.name = f"toco_{index}"
        obj = roots(obj, spec["semente"])
        rows.append(export(obj, OUT / f"toco_{index}.glb", MAX_TRIS, {
            "nome": spec["nome"], "semente": spec["semente"], "corte_m": ALTURA[spec["nome"]],
            "cores": {"tronco": None, "corte": CORTE}}))
    write_report(OUT / "toco_relatorio.json", "tools/arte/cenario/toco.py", rows)


main()

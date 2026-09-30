"""Árvore piloto do cenário: 4 variações da mesma família, geradas por script (reproduzível, semente por variação).

Família: tronco torto e torcido (as facetas fazem uma espiral sutil), copa em poucas massas grandes em forma de gota
com a ponta enrolada. Cores chapadas da paleta do GDD (seção 17), sem textura. Metros, frente +Z no GLB, pivô no
centro da base. Proposta em assets/cenario/PROPOSTA.md.

Uso, na raiz da worktree:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/arvore.py
Saída: assets/cenario/arvore/arvore_1..4.glb e arvore_relatorio.json.
"""

import json
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/cenario/arvore"
MAX_TRIS = 400

PALETA = {  # GDD, seção 17
    "terra": "#4A3B3A",
    "terra_roxa": "#3F3342",
    "lama": "#2E2931",
    "musgo": "#4E5544",
    "liquen": "#6B4F7C",
}

# Cada massa da copa: base (x, y, z) e topo relativos ao chão, raio máximo, onde fica a barriga (0..1 da altura),
# quanto a ponta enrola (m) e para que lado (graus), giro das facetas (graus, a espiral) e lados.
VARIACOES = [
    {
        "nome": "gota", "semente": 11, "tronco": "terra", "copa": "musgo",
        "troncos": [{"de": (0, 0, -0.02), "ate": (0.06, 0.02, 0.72), "r": 0.075, "entorta": 0.05, "giro": 80}],
        "massas": [
            {"base": (0.04, 0.02, 0.42), "topo": 1.50, "r": 0.46, "barriga": 0.30, "enrola": 0.22, "lado": 200},
            {"base": (-0.30, 0.10, 0.52), "topo": 0.90, "r": 0.20, "barriga": 0.45, "enrola": 0.06, "lado": 150,
             "lados": 6, "aneis": 4},
        ],
    },
    {
        "nome": "dupla", "semente": 23, "tronco": "lama", "copa": "musgo",
        "troncos": [{"de": (0, 0, -0.02), "ate": (-0.05, 0.03, 0.95), "r": 0.07, "entorta": 0.06, "giro": 70}],
        "massas": [
            {"base": (0.0, 0.0, 0.42), "topo": 1.00, "r": 0.47, "barriga": 0.42, "enrola": 0.0, "lado": 0,
             "ponta": 0.55},
            {"base": (-0.06, 0.05, 0.90), "topo": 1.60, "r": 0.30, "barriga": 0.30, "enrola": 0.18, "lado": 20},
        ],
    },
    {
        "nome": "tufos", "semente": 37, "tronco": "terra_roxa", "copa": "liquen",
        "troncos": [
            {"de": (0, 0, -0.02), "ate": (0.02, 0.0, 0.52), "r": 0.08, "entorta": 0.04, "giro": 60},
            {"de": (0.02, 0.0, 0.48), "ate": (0.26, 0.06, 0.82), "r": 0.05, "entorta": 0.05, "giro": 50, "lados": 5},
            {"de": (0.02, 0.0, 0.48), "ate": (-0.22, -0.08, 0.92), "r": 0.05, "entorta": 0.05, "giro": -50,
             "lados": 5},
        ],
        "massas": [
            {"base": (0.26, 0.06, 0.62), "topo": 1.12, "r": 0.29, "barriga": 0.40, "enrola": 0.08, "lado": 0,
             "lados": 7, "aneis": 5},
            {"base": (-0.22, -0.08, 0.72), "topo": 1.36, "r": 0.30, "barriga": 0.38, "enrola": 0.12, "lado": 160,
             "lados": 7, "aneis": 5},
            {"base": (0.02, 0.22, 0.66), "topo": 1.05, "r": 0.24, "barriga": 0.42, "enrola": 0.06, "lado": 80,
             "lados": 6, "aneis": 5},
        ],
    },
    {
        "nome": "alta", "semente": 53, "tronco": "lama", "copa": "musgo",
        "troncos": [{"de": (0, 0, -0.02), "ate": (-0.08, -0.03, 0.90), "r": 0.065, "entorta": 0.09, "giro": 110}],
        "massas": [
            {"base": (-0.06, -0.02, 0.55), "topo": 1.72, "r": 0.36, "barriga": 0.26, "enrola": 0.32, "lado": 30},
            {"base": (0.20, 0.08, 0.62), "topo": 0.98, "r": 0.17, "barriga": 0.45, "enrola": 0.05, "lado": 330,
             "lados": 6, "aneis": 4},
        ],
    },
]


def linear(hex_color: str) -> tuple:
    """Hex sRGB para a cor linear que o glTF guarda no baseColorFactor."""
    out = []
    for i in (1, 3, 5):
        c = int(hex_color[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def material(nome: str, hex_color: str):
    mat = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = linear(hex_color)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    return mat


def frames(path):
    """Referenciais ao longo do eixo (transporte paralelo), para os anéis não torcerem sozinhos."""
    tangents = []
    for i in range(len(path)):
        a, b = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        tangents.append((b - a).normalized())
    ref = Vector((1, 0, 0))
    out = []
    for t in tangents:
        n = (ref - t * ref.dot(t)).normalized()
        out.append((n, t.cross(n)))
        ref = n
    return out


def lathe(path, radii, sides, twist_deg, rng, jitter, top_point=True, bottom_point=False, name="peca"):
    """Tubo por anéis ao longo de um eixo torto. Raio 0 no fim vira ponta (um vértice só)."""
    bm = bmesh.new()
    rings = []
    fr = frames(path)
    for i, (p, r) in enumerate(zip(path, radii)):
        if r <= 1e-4:
            rings.append([bm.verts.new(p)])
            continue
        n, b = fr[i]
        twist = math.radians(twist_deg) * i / max(len(path) - 1, 1)
        ring = []
        for k in range(sides):
            a = twist + 2 * math.pi * k / sides
            rr = r * (1 + rng.uniform(-jitter, jitter))
            ring.append(bm.verts.new(p + (n * math.cos(a) + b * math.sin(a)) * rr))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1:
            for k in range(sides):
                bm.faces.new((r0[0], r1[(k + 1) % sides], r1[k]))
        elif len(r1) == 1:
            for k in range(sides):
                bm.faces.new((r0[k], r0[(k + 1) % sides], r1[0]))
        else:
            for k in range(sides):
                bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def trunk(spec, rng, idx):
    """Tronco ou galho: eixo com barriga para um lado, raio afinando, pé alargado, facetas torcidas."""
    a, b = Vector(spec["de"]), Vector(spec["ate"])
    segs = 4
    side = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized()
    path, radii = [], []
    for i in range(segs + 1):
        t = i / segs
        p = a.lerp(b, t) + side * spec["entorta"] * math.sin(math.pi * t) * (1 if t < 0.6 else -0.3)
        path.append(p)
        r = spec["r"] * (1 - 0.45 * t)
        if i == 0 and spec["de"][2] < 0:
            r *= 1.45  # pé alargado: a árvore "segura" o chão
        radii.append(r)
    obj = lathe(path, radii, spec.get("lados", 6), spec["giro"], rng, 0.06, name=f"tronco_{idx}")
    for p in obj.data.polygons:
        p.use_smooth = False  # faceta é o desenho: a torção vira espiral
    return obj


def mass(spec, rng, idx):
    """Massa da copa: gota torta de anéis, barriga embaixo, ponta que enrola para um lado."""
    base = Vector(spec["base"])
    height = spec["topo"] - base.z
    rings = spec.get("aneis", 6)
    sides = spec.get("lados", 8)
    belly = spec["barriga"]
    tip = spec.get("ponta", 0.0)  # 0 = ponta fina; > 0 = topo arredondado
    lado = math.radians(spec["lado"])
    curl_dir = Vector((math.cos(lado), math.sin(lado), 0))
    path, radii = [base.copy()], [0.0]
    for i in range(1, rings + 1):
        u = i / (rings + 1)
        if u <= belly:
            prof = math.sin(0.5 * math.pi * u / belly) ** 0.8
        else:
            v = (u - belly) / (1 - belly)
            prof = (1 - v) ** (1.3 - 0.8 * tip) * (1 - 0.15 * v)
            prof = max(prof, tip * 0.35 * (1 - v ** 3))
        # a ponta enrola: desloca o eixo cada vez mais para o lado e o abaixa um pouco no fim
        p = base + Vector((0, 0, height * u)) + curl_dir * spec["enrola"] * u ** 3
        path.append(p)
        radii.append(spec["r"] * prof)
    top = base + Vector((0, 0, height)) + curl_dir * spec["enrola"] - Vector((0, 0, 0.5 * spec["enrola"] ** 2))
    path.append(top)
    radii.append(0.0)
    twist = rng.choice((-1, 1)) * rng.uniform(25, 45)
    obj = lathe(path, radii, sides, twist, rng, 0.07, name=f"copa_{idx}")
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def triangles(obj) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def build(spec, index):
    rng = random.Random(spec["semente"])
    mat_t = material(f"tronco_{spec['tronco']}", PALETA[spec["tronco"]])
    mat_c = material(f"copa_{spec['copa']}", PALETA[spec["copa"]])
    parts = []
    for i, t in enumerate(spec["troncos"]):
        o = trunk(t, rng, i)
        o.data.materials.append(mat_t)
        parts.append(o)
    for i, m in enumerate(spec["massas"]):
        o = mass(m, rng, i)
        o.data.materials.append(mat_c)
        parts.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = f"arvore_{index}"
    # Nomes de material só pelo papel (contrato proposto): tronco e copa.
    mat_t.name, mat_c.name = "tronco", "copa"
    return obj


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"fonte": "tools/arte/cenario/arvore.py", "unidade": "m", "frente": "+Z", "variacoes": []}
    for index, spec in enumerate(VARIACOES, start=1):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = build(spec, index)
        tris = triangles(obj)
        assert tris <= MAX_TRIS, f"{obj.name}: {tris} triângulos > {MAX_TRIS}"
        xs = [v.co.x for v in obj.data.vertices]
        ys = [v.co.y for v in obj.data.vertices]
        zs = [v.co.z for v in obj.data.vertices]
        path = OUT / f"arvore_{index}.glb"
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                                  export_apply=True, export_animations=False, export_skins=False)
        # Blender -Y é a frente +Z do glTF: a pegada vai em metros no chão, x e z do jogo.
        report["variacoes"].append({
            "arquivo": path.name, "nome": spec["nome"], "semente": spec["semente"], "triangulos": tris,
            "altura_m": round(max(zs), 3),
            "pegada_x_m": [round(min(xs), 3), round(max(xs), 3)],
            "pegada_z_m": [round(-max(ys), 3), round(-min(ys), 3)],
            "cores": {"tronco": PALETA[spec["tronco"]], "copa": PALETA[spec["copa"]]},
        })
        print(f"{path.name}: {spec['nome']}, {tris} triângulos, {max(zs):.2f} m", flush=True)
    (OUT / "arvore_relatorio.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


main()

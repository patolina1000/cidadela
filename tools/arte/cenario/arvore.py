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
# Revisão 3 (pedido do Arthur): a copa fica fora do alcance dos personagens (protagonista 0,80 m, aldeão 0,40 m).
# As massas abaixo são desenhadas na escala da revisão 2; build() sobe a copa para começar em COPA_BAIXO e a
# aumenta por ESCALA_COPA, e o tronco se alonga até ela (fica visível embaixo). Forma e torção não mudam.
COPA_BAIXO = 1.10
ESCALA_COPA = 1.35
COPA_MIN = 1.0  # nenhum vértice da copa abaixo disto, já com a inclinação

PALETA = {  # GDD, seção 17
    "terra": "#4A3B3A",
    "terra_roxa": "#3F3342",
    "lama": "#2E2931",
    "musgo": "#4E5544",
    "liquen": "#6B4F7C",
}

# A árvore é desenhada inclinando para +X ("inclina", graus) e no fim gira em Z pelo ângulo sorteado pela semente.
# Cada massa da copa: base (x, y, z), comprimento ao longo do eixo, raio máximo, barriga (0..1 do comprimento),
# quanto o eixo dobra até a ponta ("dobra", graus; > 90 cai como chapéu de bruxa) e para que lado ("lado", graus,
# 0 = para onde a árvore inclina), "assim" (quanto um lado da massa é mais gordo que o outro), lados e anéis.
VARIACOES = [
    {
        "nome": "gota", "semente": 11, "inclina": 8, "tronco": "terra", "copa": "musgo",
        "troncos": [{"de": (0, 0, -0.02), "ate": (0.0, 0.0, 0.72), "r": 0.075, "entorta": 0.06, "giro": 80}],
        "massas": [
            {"base": (0.0, 0.0, 0.42), "comp": 1.10, "r": 0.46, "barriga": 0.30, "dobra": 60, "lado": 180,
             "assim": 0.14},
            {"base": (-0.28, 0.14, 0.50), "comp": 0.38, "r": 0.20, "barriga": 0.45, "dobra": 35, "lado": 140,
             "assim": 0.1, "lados": 6, "aneis": 4},
        ],
    },
    {
        "nome": "dupla", "semente": 23, "inclina": 6, "tronco": "lama", "copa": "musgo",
        "troncos": [{"de": (0, 0, -0.02), "ate": (0.0, 0.0, 0.95), "r": 0.07, "entorta": 0.07, "giro": 70}],
        "massas": [
            {"base": (0.0, 0.0, 0.42), "comp": 0.58, "r": 0.47, "barriga": 0.42, "dobra": 10, "lado": 90,
             "assim": 0.16, "ponta": 0.55},
            {"base": (0.02, 0.05, 0.90), "comp": 0.72, "r": 0.30, "barriga": 0.30, "dobra": 65, "lado": 200,
             "assim": 0.12},
        ],
    },
    {
        "nome": "tufos", "semente": 37, "inclina": 5, "tronco": "terra_roxa", "copa": "liquen",
        "troncos": [
            {"de": (0, 0, -0.02), "ate": (0.02, 0.0, 0.52), "r": 0.08, "entorta": 0.04, "giro": 60},
            {"de": (0.02, 0.0, 0.48), "ate": (0.28, 0.06, 0.80), "r": 0.05, "entorta": 0.05, "giro": 50, "lados": 5},
            {"de": (0.02, 0.0, 0.48), "ate": (-0.20, -0.08, 0.94), "r": 0.05, "entorta": 0.05, "giro": -50,
             "lados": 5},
        ],
        "massas": [
            {"base": (0.28, 0.06, 0.60), "comp": 0.50, "r": 0.29, "barriga": 0.40, "dobra": 45, "lado": 10,
             "assim": 0.14, "lados": 7, "aneis": 5},
            {"base": (-0.20, -0.08, 0.74), "comp": 0.62, "r": 0.30, "barriga": 0.38, "dobra": 55, "lado": 170,
             "assim": 0.14, "lados": 7, "aneis": 5},
            {"base": (0.02, 0.22, 0.66), "comp": 0.40, "r": 0.24, "barriga": 0.42, "dobra": 35, "lado": 80,
             "assim": 0.12, "lados": 6, "aneis": 5},
        ],
    },
    {
        # Chapéu de bruxa dobrado: fina, a mais inclinada, a ponta passa da horizontal e cai.
        "nome": "alta", "semente": 53, "inclina": 12, "tronco": "lama", "copa": "musgo",
        "troncos": [{"de": (0, 0, -0.02), "ate": (0.0, 0.0, 0.85), "r": 0.058, "entorta": 0.08, "giro": 110}],
        "massas": [
            {"base": (0.0, 0.0, 0.52), "comp": 1.62, "r": 0.27, "barriga": 0.20, "dobra": 125, "lado": 0,
             "assim": 0.1, "aneis": 8},
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


def lathe(path, radii, sides, twist_deg, rng, jitter, asym=0.0, asym_deg=0.0, name="peca"):
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
            rr = r * (1 + rng.uniform(-jitter, jitter)) * (1 + asym * math.cos(a - math.radians(asym_deg)))
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
    """Massa da copa: gota torta de anéis, barriga embaixo, eixo que dobra para um lado até a ponta."""
    base = Vector(spec["base"])
    length = spec["comp"]
    rings = spec.get("aneis", 6)
    sides = spec.get("lados", 8)
    belly = spec["barriga"]
    tip = spec.get("ponta", 0.0)  # 0 = ponta fina; > 0 = topo arredondado
    lado = math.radians(spec["lado"])
    side = Vector((math.cos(lado), math.sin(lado), 0))
    bend = math.radians(spec["dobra"])
    n = rings + 1
    path, radii = [base.copy()], [0.0]
    p = base.copy()
    for i in range(1, n + 1):
        u = i / n
        # o eixo sobe e vai virando para o lado: dobra pouco embaixo e muito na ponta
        theta = bend * (u - 0.5 / n) ** 2.2
        p = p + (Vector((0, 0, math.cos(theta))) + side * math.sin(theta)) * (length / n)
        if i == n:
            prof = 0.0
        elif u <= belly:
            prof = math.sin(0.5 * math.pi * u / belly) ** 0.8
        else:
            v = (u - belly) / (1 - belly)
            prof = (1 - v) ** (1.3 - 0.8 * tip) * (1 - 0.15 * v)
            prof = max(prof, tip * 0.35 * (1 - v ** 3))
        path.append(p.copy())
        radii.append(spec["r"] * prof)
    twist = rng.choice((-1, 1)) * rng.uniform(25, 45)
    obj = lathe(path, radii, sides, twist, rng, 0.07, spec.get("assim", 0.0), rng.uniform(0, 360),
                name=f"copa_{idx}")
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def triangles(obj) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def lift(spec):
    """Revisão 3: copa mais alta e maior, tronco mais comprido e grosso, mantendo o desenho da revisão 2."""
    zc = min(m["base"][2] for m in spec["massas"])
    up = lambda p: (p[0] * ESCALA_COPA, p[1] * ESCALA_COPA, COPA_BAIXO + (p[2] - zc) * ESCALA_COPA)
    out = dict(spec)
    out["massas"] = [dict(m, base=up(m["base"]), comp=m["comp"] * ESCALA_COPA, r=m["r"] * ESCALA_COPA)
                     for m in spec["massas"]]
    out["troncos"] = [dict(t, de=t["de"] if t["de"][2] < 0 else up(t["de"]), ate=up(t["ate"]),
                           r=t["r"] * ESCALA_COPA, entorta=t["entorta"] * ESCALA_COPA) for t in spec["troncos"]]
    return out


def build(spec, index):
    spec = lift(spec)
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
    # Torta de propósito: inclina para +X em volta do pé e gira para o lado sorteado pela semente.
    obj.rotation_euler = (0.0, math.radians(spec["inclina"]), math.radians(rng.uniform(0, 360)))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
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
        copa_idx = [i for i, m in enumerate(obj.data.materials) if m.name == "copa"][0]
        copa_z = min(obj.data.vertices[v].co.z for p in obj.data.polygons if p.material_index == copa_idx
                     for v in p.vertices)
        assert copa_z >= COPA_MIN, f"{obj.name}: copa desce a {copa_z:.2f} m"
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
            "arquivo": path.name, "nome": spec["nome"], "semente": spec["semente"], "triangulos": tris, "inclinacao_graus": spec["inclina"],
            "altura_m": round(max(zs), 3), "copa_baixo_m": round(copa_z, 3),
            "pegada_x_m": [round(min(xs), 3), round(max(xs), 3)],
            "pegada_z_m": [round(-max(ys), 3), round(-min(ys), 3)],
            "cores": {"tronco": PALETA[spec["tronco"]], "copa": PALETA[spec["copa"]]},
        })
        print(f"{path.name}: {spec['nome']}, {tris} triângulos, {max(zs):.2f} m, copa de {copa_z:.2f} m", flush=True)
    (OUT / "arvore_relatorio.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":  # toco.py importa build daqui para cortar o toco da própria árvore
    main()

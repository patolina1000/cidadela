"""Protagonista v2: o cristal do peito, por código (Blender headless). Contrato, seção CRISTAL: no máximo 60
triângulos, material "Cristal", o único emissivo, preso ao encaixe "Peito" (osso Spine), com a luz azul e a camada
de render da v1 (docs/protagonista_v2_inventario.md, seção 5; isso é do jogo).

A v1 tinha um losango chato de 4 triângulos, 27 × 52 mm, 4 cm abaixo do Spine, emissão ciano #4C9DB7 (pico #8DF1FC),
força 3 (o jogo ainda multiplica por 3). A v2 é uma gema de verdade: prisma hexagonal alongado com duas pontas
(6 + 12 + 6 = 24 triângulos), 30 × 58 mm, 16 mm de fundo, no meio do esterno na altura da axila, meio encaixada na pele
e inclinada 15° para cima (a câmera do jogo vem de cima, a 55°). No espaço do corpo limpo em repouso (como o cabelo
do aldeão: o jogo prende no encaixe compensando o repouso do osso).

Saída: assets/modelos/protagonista_v2/cristal.glb e cristal.json (medidas, cores e a luz da v1 para o jogo).

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/cristal.py
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import ROOT, import_glb, mesh_objects  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
CLEAN = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpeza.json"
OUT = ROOT / "assets/modelos/protagonista_v2/cristal.glb"
WIDTH, HEIGHT, DEPTH = 0.030, 0.058, 0.016  # m
TIP = 0.30  # fração da altura em cada ponta
TILT_DEG = 15  # topo inclinado para trás: a face da frente olha um pouco para cima
EMBED = 0.40  # fração do fundo dentro da pele
BASE = "#8FE3FF"  # cor da gema (a v1 era branca com textura de emissão)
EMISSION = "#4CC3FF"  # entre a média (#4C9DB7) e o pico (#8DF1FC) da emissão da v1, mais saturada
EMISSION_STRENGTH = 3.0  # como a v1; o jogo multiplica por 3 (CastellanVisual.CrystalEmissionBoost)
LIGHT_V1 = {"cor": [0.35, 0.55, 1.0], "energia": 0.85, "alcance_m": 2.3, "atenuacao": 1.4, "sombra": False,
            "especular": 0.1, "camada_propria": 20}


def srgb_lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def gem_mesh() -> bpy.types.Object:
    """Prisma hexagonal alongado em pé (eixo Z), com pontas; hexágono achatado na profundidade (Y)."""
    bm = bmesh.new()
    half = HEIGHT / 2
    ring_z = half * (1 - 2 * TIP)
    rings = []
    for z in (ring_z, -ring_z):
        ring = []
        for k in range(6):
            a = math.radians(60 * k)
            ring.append(bm.verts.new((WIDTH / 2 * math.cos(a), DEPTH / 2 * math.sin(a), z)))
        rings.append(ring)
    top, bot = bm.verts.new((0, 0, half)), bm.verts.new((0, 0, -half))
    up, down = rings
    for k in range(6):
        n = (k + 1) % 6
        bm.faces.new((top, up[k], up[n]))
        bm.faces.new((up[k], down[k], down[n]))
        bm.faces.new((up[k], down[n], up[n]))
        bm.faces.new((bot, down[n], down[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("cristal")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("cristal", mesh)
    bpy.context.scene.collection.objects.link(obj)
    for p in mesh.polygons:
        p.use_smooth = False  # facetado: cada face pega a luz de um jeito
    return obj


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body = import_glb(BODY)
    torso = next(o for o in mesh_objects(body) if o.name.split(".")[0] == "tronco")
    clean = json.loads(CLEAN.read_text())
    k = clean["cabeca"]["escala_do_corpo_k"]
    z = 0.595 * k  # altura da axila do bruto B × a escala do corpo (limpar_corpo.Z["axila"])
    # frente do esterno na linha do meio: raio de frente (-Y) para trás
    dg = bpy.context.evaluated_depsgraph_get()
    inv = torso.matrix_world.inverted()
    hit, loc, normal, _ = torso.ray_cast(inv @ Vector((0, -1.0, z)), inv.to_3x3() @ Vector((0, 1, 0)), depsgraph=dg)
    if not hit:
        raise RuntimeError("o raio não achou o peito")
    front = torso.matrix_world @ loc
    for o in body:
        bpy.data.objects.remove(o)

    gem = gem_mesh()
    center = Vector((0, front.y + DEPTH * (0.5 - EMBED), z))
    gem.matrix_world = Matrix.Translation(center) @ Matrix.Rotation(math.radians(-TILT_DEG), 4, "X")
    bpy.context.view_layer.objects.active = gem
    gem.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    mat = bpy.data.materials.new("Cristal")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*srgb_lin(BASE), 1)
    b.inputs["Roughness"].default_value = 0.35
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Emission Color"].default_value = (*srgb_lin(EMISSION), 1)
    b.inputs["Emission Strength"].default_value = EMISSION_STRENGTH
    gem.data.materials.append(mat)
    gem.data.calc_loop_triangles()
    tris = len(gem.data.loop_triangles)
    assert tris <= 60, tris

    pts = np.array([v.co[:] for v in gem.data.vertices])
    bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_materials="EXPORT", export_animations=False, export_skins=False)
    info = {
        "arquivo": str(OUT.relative_to(ROOT)), "triangulos": tris, "material": "Cristal",
        "tamanho_mm": {"largura": WIDTH * 1000, "altura": HEIGHT * 1000, "fundo": DEPTH * 1000},
        "centro_blender_m": [round(c, 4) for c in center], "centro_gltf_m": [round(center.x, 4), round(center.z, 4), round(-center.y, 4)],
        "frente_do_peito_gltf_z_m": round(-front.y, 4), "avanca_da_pele_mm": round((front.y - float(pts[:, 1].min())) * 1000, 1),
        "inclinacao_graus": TILT_DEG, "cor_base": BASE, "emissao": EMISSION, "forca_emissao": EMISSION_STRENGTH,
        "espaco": "corpo limpo em repouso (protagonista_corpo_limpo.glb), metros, frente +Z do glTF; o jogo prende no encaixe Peito (osso Spine) compensando o repouso",
        "luz_da_v1_para_o_jogo": LIGHT_V1,
        "caixa_blender_m": [np.round(pts.min(0), 4).tolist(), np.round(pts.max(0), 4).tolist()],
    }
    OUT.with_suffix(".json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n")
    print("CRISTAL " + json.dumps(info, ensure_ascii=False))


main()

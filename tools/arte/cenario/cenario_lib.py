"""Peças comuns dos objetos do cenário feitos por script no Blender (pedra, veio; a árvore tem as suas em arvore.py).

Blocos low-poly: casca convexa de poucos pontos sorteados num elipsoide torto, com a base cortada no chão; normais
suaves (seixo, do mesmo jeito macio da copa da árvore) ou facetadas (lasca de minério).
"""

import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]

PALETA = {  # GDD, seção 17
    "pedra_fria": "#66636B",
    # Tarefa 4: a pedra fria competia com os personagens (a coisa mais clara do mapa); a pedra do recurso usa este,
    # o meio entre #66636B e #4E4A58 (o fundo do visor), autorizado pelo Diretor.
    "pedra_escura": "#57535F",
    "terra_roxa": "#3F3342",
    "lama": "#2E2931",
    "musgo": "#4E5544",
    "meia_noite": "#1E2A3A",  # a cor do ferro em data/items.json
}


def linear(hex_color: str) -> tuple:
    """Hex sRGB para a cor linear que o glTF guarda no baseColorFactor."""
    out = []
    for i in (1, 3, 5):
        c = int(hex_color[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def material(nome: str, hex_color: str):
    """Material chapado e fosco, nomeado pelo papel (contrato proposto)."""
    mat = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = linear(hex_color)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    return mat


def block(rng, size, center=(0, 0, 0), points=12, tilt_deg=0.0, yaw_deg=0.0, twist_deg=0.0, jitter=0.18,
          sink=0.02, name="bloco", point_z=0.0, smooth=True):
    """Bloco facetado: casca convexa de pontos num elipsoide (size = semi-eixos), inclinado e girado.

    twist_deg gira as camadas de cima em relação às de baixo (espiral sutil); point_z > 0 puxa o topo para uma ponta
    (lasca de minério). Tudo abaixo de -sink é achatado no chão, para o bloco assentar sem flutuar.
    """
    bm = bmesh.new()
    sx, sy, sz = size
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(points):
        # pontos espalhados por igual na esfera (espiral de Fibonacci) e sacudidos: facetas grandes e desiguais
        z = 1 - 2 * (i + 0.5) / points
        r = math.sqrt(max(0.0, 1 - z * z))
        a = golden * i + rng.uniform(-0.4, 0.4) + math.radians(twist_deg) * (z + 1) / 2
        k = 1 + rng.uniform(-jitter, jitter)
        p = Vector((math.cos(a) * r * sx * k, math.sin(a) * r * sy * k, z * sz * k))
        if point_z > 0 and z > 0.6:
            p.x *= 0.35
            p.y *= 0.35
            p.z += point_z * sz
        bm.verts.new(p)
    if point_z > 0:
        bm.verts.new(Vector((0, 0, sz * (1 + point_z))))
    bmesh.ops.convex_hull(bm, input=bm.verts)
    rot = (Matrix.Rotation(math.radians(yaw_deg), 4, "Z") @ Matrix.Rotation(math.radians(tilt_deg), 4, "Y"))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ rot, verts=bm.verts)
    for v in bm.verts:
        if v.co.z < -sink:
            v.co.z = -sink
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.004)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=0.002)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for p in obj.data.polygons:
        p.use_smooth = smooth  # suave = seixo macio, como a copa; facetado = lasca de cristal
    return obj


def join(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = name
    return obj


def triangles(obj) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def export(obj, path: Path, max_tris: int, extra=None) -> dict:
    """Exporta GLB (metros, frente +Z, pivô no centro da base) e devolve a linha do relatório."""
    tris = triangles(obj)
    assert tris <= max_tris, f"{obj.name}: {tris} triângulos > {max_tris}"
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_animations=False, export_skins=False)
    row = {"arquivo": path.name, "triangulos": tris, "altura_m": round(max(zs), 3),
           "pegada_x_m": [round(min(xs), 3), round(max(xs), 3)],
           "pegada_z_m": [round(-max(ys), 3), round(-min(ys), 3)]}
    row.update(extra or {})
    print(f"{path.name}: {tris} triângulos, {max(zs):.2f} m", flush=True)
    return row


def write_report(path: Path, source: str, rows: list):
    report = {"fonte": source, "unidade": "m", "frente": "+Z", "variacoes": rows}
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

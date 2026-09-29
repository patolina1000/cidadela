"""Passo 3: medidas da protagonista v1 (Blender headless), em pose de repouso.
- triângulos por material e por região (osso de maior peso de cada triângulo: soma dos pesos dos 3 vértices);
- altura;
- cor média da pele e do cabelo na textura, em hex. A textura da Meshy é um atlas em cacos, então as amostras
  vêm da geometria: pele = triângulos cujo osso dominante é mão ou pé (descalça; antebraços têm faixas);
  cabelo = triângulos da região da cabeça acima do pescoço virados para trás ou para cima (nuca e topo, onde
  só há cabelo). Cada triângulo é rasterizado na UV e os texels são somados uma vez só; média em espaço linear.

Saída: assets/previews/protagonista_v2/v1_medidas.json

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/medir_v1.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import BONE_REGION, REGIONS, ROOT, V1, load_rest, mesh_objects, mesh_points, triangle_bones  # noqa: E402

OUT = ROOT / "assets/previews/protagonista_v2/v1_medidas.json"
SKIN_BONES = {"LeftHand", "RightHand", "LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase"}


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_hex(rgb) -> str:
    c = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
    return "#" + "".join(f"{int(round(float(v) * 255)):02X}" for v in np.clip(c, 0, 1))


def rasterize(mask: np.ndarray, uv_tri: np.ndarray) -> None:
    """Marca os texels cujo centro cai dentro do triângulo (UV com v para cima; linha 0 da imagem em baixo)."""
    h, w = mask.shape
    p = uv_tri * [w, h]
    x0, y0 = np.floor(p.min(axis=0)).astype(int)
    x1, y1 = np.ceil(p.max(axis=0)).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)
    if x1 <= x0 or y1 <= y0:
        return
    xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
    (ax, ay), (bx, by), (cx, cy) = p
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(d) < 1e-12:
        return
    l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d
    l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d
    inside = (l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)
    mask[y0:y1, x0:x1] |= inside


def main() -> None:
    objects = load_rest(V1)
    body = mesh_objects(objects)[0]
    arm = next(o for o in objects if o.type == "ARMATURE")
    mats, bones = triangle_bones(body)
    names = [m.name for m in body.data.materials]
    pts = mesh_points(objects)
    height = float(pts[:, 2].max() - pts[:, 2].min())

    by_mat = Counter(names[m] for m in mats)
    by_region = Counter(BONE_REGION.get(b, "outro") for b in bones)
    by_region_mat = {r: dict(Counter(names[m] for m, b in zip(mats, bones) if BONE_REGION.get(b) == r)) for r in REGIONS}

    # Texels de pele e de cabelo.
    tex_node = next(n for n in body.data.materials["Material_1"].node_tree.nodes if n.type == "TEX_IMAGE")
    img = tex_node.image
    w, h = img.size
    pix = np.array(img.pixels[:]).reshape(h, w, 4)[:, :, :3]
    uv = body.data.uv_layers.active.data
    neck_z = (arm.matrix_world @ arm.data.bones["neck"].head_local).z
    mw, nm = body.matrix_world, body.matrix_world.to_3x3()
    masks = {"pele": np.zeros((h, w), bool), "cabelo": np.zeros((h, w), bool)}
    counts = Counter()
    for t, m, b in zip(body.data.loop_triangles, mats, bones):
        if names[m] != "Material_1":
            continue
        cls = None
        if b in SKIN_BONES:
            cls = "pele"
        elif BONE_REGION.get(b) == "cabeca_cabelo":
            center = mw @ t.center
            n = (nm @ t.normal).normalized()
            if center.z > neck_z and (n.y > 0.35 or n.z > 0.7):  # costas (+Y) ou topo
                cls = "cabelo"
        if cls:
            counts[cls] += 1
            rasterize(masks[cls], np.array([uv[i].uv[:] for i in t.loops]))
    colors = {}
    for cls, mask in masks.items():
        lin = srgb_to_linear(pix[mask]).mean(axis=0)
        colors[cls] = {"hex": linear_to_hex(lin), "triangulos_amostrados": counts[cls], "texels": int(mask.sum())}

    result = {
        "glb": str(V1.relative_to(ROOT)),
        "pose": "repouso (T)",
        "altura_m": round(height, 3),
        "triangulos_total": len(mats),
        "triangulos_por_material": dict(by_mat),
        "triangulos_por_regiao": {r: by_region.get(r, 0) for r in (*REGIONS, "outro") if by_region.get(r, 0) or r != "outro"},
        "triangulos_por_regiao_e_material": by_region_mat,
        "regioes": {r: list(b) for r, b in REGIONS.items()},
        "cores_textura": colors,
        "metodo_cores": "pele: triângulos com osso dominante mão ou pé; cabelo: região da cabeça acima do osso neck, "
                        "normal para trás (y > 0,35) ou para cima (z > 0,7); texels rasterizados pela UV, média linear",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print("MEDIDAS " + json.dumps(result, ensure_ascii=False))


main()

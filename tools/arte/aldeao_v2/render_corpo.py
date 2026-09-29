"""Renderiza um GLB bruto da Meshy (corpo do aldeão v2) em Blender headless, com material chapado cor de pele:
frente, lado, 3/4, câmera do jogo (55°) e a frente com a protagonista ao lado em escala (aldeão a 0,40 m,
protagonista como está, ~0,75 m). Sem limpeza, rig ou animação. Também mede a cabeça e a lisura da área do rosto.

Saída: <pasta>/<nome>_{frente,lado,tres_quartos,jogo,escala}.png e <nome>_medidas.json com a caixa da cabeça
na imagem de frente (para marcar os retalhos) e o desvio da área do rosto em relação a uma esfera ajustada.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/render_corpo.py -- <glb> <pasta_saida> [suave]
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpo_lib import (EYES_FRAC, GAME_TILT, HEIGHT_M, MOUTH_FRAC, ROOT, SKIN, face_flatness, flat_material,  # noqa: E402
                       head_box, import_glb, mesh_points, set_smooth, setup_scene, shoot, triangle_count)

PROTAGONIST = ROOT / "assets/modelos/protagonista/protagonista.glb"
RESOLUTION = 1024


def normalize(objects, height: float) -> tuple:
    """Escala para a altura pedida, pés em z = 0, centro x/y na origem (Blender: z para cima)."""
    pts = mesh_points(objects)
    low, high = pts.min(axis=0), pts.max(axis=0)
    scale = height / (high[2] - low[2])
    root = bpy.data.objects.new("raiz", None)
    bpy.context.scene.collection.objects.link(root)
    for obj in objects:
        if obj.parent is None:
            obj.parent = root
    root.scale = (scale,) * 3
    root.location = (-(low[0] + high[0]) / 2 * scale, -(low[1] + high[1]) / 2 * scale, -low[2] * scale)
    bpy.context.view_layer.update()
    pts = mesh_points(objects)
    return pts, pts.min(axis=0), pts.max(axis=0)


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    glb, out = Path(args[0]), Path(args[1])
    smooth = len(args) > 2 and args[2] == "suave"
    out.mkdir(parents=True, exist_ok=True)
    name = glb.stem
    scene = setup_scene(RESOLUTION)
    objects = import_glb(glb)
    for obj in objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"
    flat_material(objects, SKIN)
    set_smooth(objects, smooth)
    pts, low, high = normalize(objects, HEIGHT_M)
    box = head_box(pts)
    flat = face_flatness(pts, box)
    tris = triangle_count(objects)

    center = Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (low[2] + high[2]) / 2))
    size = float(max(high - low)) * 1.15
    dist = size * 4
    views = {}
    views["frente"] = shoot(scene, center + Vector((0, -dist, 0)), center, size, out / f"{name}_frente.png")
    views["lado"] = shoot(scene, center + Vector((dist, 0, 0)), center, size, out / f"{name}_lado.png")
    d = dist / math.sqrt(2)
    views["tres_quartos"] = shoot(scene, center + Vector((d, -d, 0)), center, size, out / f"{name}_tres_quartos.png")
    tilt = math.radians(GAME_TILT)
    views["jogo"] = shoot(scene, center + Vector((0, -math.cos(tilt), math.sin(tilt))) * dist, center, size, out / f"{name}_jogo.png")

    # Escala: protagonista ao lado, como está (o normalize dela já é o do jogo).
    prot = import_glb(PROTAGONIST) if PROTAGONIST.exists() else []
    for obj in prot:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"
    if prot:
        flat_material(prot, (0.55, 0.62, 0.72, 1))
        proot = bpy.data.objects.new("raiz_prot", None)
        scene.collection.objects.link(proot)
        for obj in prot:
            if obj.parent is None:
                obj.parent = proot
        proot.location = (0.55, 0, 0)
        bpy.context.view_layer.update()
        ppts = mesh_points(prot)
        allp = np.vstack([pts, ppts])
        lo, hi = allp.min(axis=0), allp.max(axis=0)
        c = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))
        s = float(max(hi - lo)) * 1.15
        views["escala"] = shoot(scene, c + Vector((0, -s * 4, 0)), c, s, out / f"{name}_escala.png")
        views["escala"]["altura_protagonista_m"] = float(ppts[:, 2].max() - ppts[:, 2].min())

    measures = {"glb": str(glb), "triangulos": int(tris), "altura_m": HEIGHT_M, "caixa_total": [low.tolist(), high.tolist()],
                "cabeca": box, "rosto": flat, "vistas": views}
    (out / f"{name}_medidas.json").write_text(json.dumps(measures, indent=2) + "\n")
    print(json.dumps({"triangulos": int(tris), "cabeca": box, "rosto": flat}, indent=1))


main()

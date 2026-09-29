"""Passo 5: prova do rosto no corpo limpo, antes de qualquer rig (Blender headless).

Cria os retalhos "Olhos" e "Boca" na cabeça (curvos, 1,5 mm da pele, proporção da célula do atlas, UV 0..1) com
o atlas final aplicado (material sem luz) e renderiza as 9 expressões na câmera do jogo (55°) em três variações:
  a) janela dos olhos na posição atual;
  b) janela dos olhos subida 10% da altura da cabeça;
  c) posição atual, com a cabeça inclinada 10° para cima na pose de repouso.
Saída: <pasta>/<variação>_<expressão>.png (fundo transparente) e <pasta>/prova.json. A montagem em 48 e 96 px
e a linha de crepúsculo são do prova_rosto_folha.py.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/prova_rosto.py -- <pasta_saida>
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpo_lib import (EYES_FRAC, MOUTH_FRAC, ROOT, ROSTO, SKIN, face_patch, flat_material, game_camera_offset,  # noqa: E402
                       head_box, import_glb, load_rosto, patch_material, set_cell, set_smooth, setup_scene, shoot, window_rect)

BODY = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
RESOLUTION = 512
ORTHO = 0.55  # m: enquadra o aldeão de 0,40 m
PATCH_OFFSET = 0.0015
RAISE_B = 0.10  # fração da altura da cabeça
TILT_C = 10  # graus, cabeça para cima
NECK_BLEND = 0.03


def points(obj):
    return np.array([v.co[:] for v in obj.data.vertices])


def tilt_head(objects, box, degrees):
    """Gira o que está acima do pescoço em torno do eixo X que passa pelo centro do pescoço; transição suave."""
    neck_z = box["pescoco_z"]
    pivot = Vector((0, (box["y"][0] + box["y"][1]) / 2, neck_z))
    for obj in objects:
        for v in obj.data.vertices:
            t = min(max((v.co.z - (neck_z - NECK_BLEND)) / (2 * NECK_BLEND), 0), 1)
            if t <= 0:
                continue
            rot = Matrix.Rotation(math.radians(degrees) * t, 4, "X")
            v.co = pivot + rot @ (v.co - pivot)


def main() -> None:
    out = Path(sys.argv[sys.argv.index("--") + 1])
    out.mkdir(parents=True, exist_ok=True)
    rosto = load_rosto()
    eyes_cfg, mouth_cfg = rosto["olhos"], rosto["boca"]
    info = {"variacoes": {}}
    for variant in ("a", "b", "c"):
        scene = setup_scene(RESOLUTION, transparent=True)
        body = [o for o in import_glb(BODY) if o.type == "MESH"][0]
        flat_material([body], SKIN)
        set_smooth([body], True)
        box = head_box(points(body))
        raise_frac = RAISE_B if variant == "b" else 0.0
        eyes = face_patch(body, "Olhos", window_rect(box, EYES_FRAC, raise_frac), eyes_cfg["colunas"], eyes_cfg["linhas"], PATCH_OFFSET, grid=(32, 20))
        mouth = face_patch(body, "Boca", window_rect(box, MOUTH_FRAC), mouth_cfg["colunas"], mouth_cfg["linhas"], PATCH_OFFSET, grid=(16, 8))
        mat_e = patch_material("rosto_olhos", ROSTO / "olhos.png", eyes_cfg["colunas"], eyes_cfg["linhas"])
        mat_m = patch_material("rosto_boca", ROSTO / "boca.png", mouth_cfg["colunas"], mouth_cfg["linhas"])
        eyes.data.materials.append(mat_e)
        mouth.data.materials.append(mat_m)
        if variant == "c":
            nose_before = min((v.co.copy() for v in body.data.vertices if v.co.z > box["pescoco_z"]), key=lambda c: c.y)
            tilt_head([body, eyes, mouth], box, TILT_C)  # rotação positiva em X: a frente (-Y) sobe
            nose_after = min((v.co.copy() for v in body.data.vertices if v.co.z > box["pescoco_z"]), key=lambda c: c.y)
            info["variacoes"]["c_frente_subiu_m"] = round(nose_after.z - nose_before.z, 4)
        pts = points(body)
        low, high = pts.min(axis=0), pts.max(axis=0)
        center = Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (low[2] + high[2]) / 2))
        cam_pos = center + game_camera_offset(ORTHO * 4)
        variant_info = {"janela_olhos": window_rect(box, EYES_FRAC, raise_frac), "janela_boca": window_rect(box, MOUTH_FRAC), "cabeca": box, "phi_max_olhos_graus": eyes["phi_max_graus"]}
        for name, spec in rosto["expressoes"].items():
            set_cell(mat_e, eyes_cfg["quadros"][spec["olhos"]], eyes_cfg["colunas"], eyes_cfg["linhas"])
            set_cell(mat_m, mouth_cfg["quadros"][spec["boca"]], mouth_cfg["colunas"], mouth_cfg["linhas"])
            shoot(scene, cam_pos, center, ORTHO, out / f"{variant}_{name}.png")
        info["variacoes"][variant] = variant_info
    (out / "prova.json").write_text(json.dumps(info, indent=2) + "\n")


main()

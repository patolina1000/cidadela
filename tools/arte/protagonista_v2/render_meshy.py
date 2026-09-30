"""Passo 2: renders dos corpos brutos da Meshy para a folha de contato (Blender headless). Sem limpeza, rig nem decimação.

Para cada GLB: normaliza a 0,80 m (contrato; pés em z = 0, centro na origem), material toon chapado na pele
#91ADB7, sempre com o aldeão v2 ao lado (só o corpo, 0,40 m, pele #AEBFD3 e retalhos no quadro 0).
Luz: a mesma do diagnóstico da v1 (fraca, fria, quase de cima e um pouco da frente), toon do Toon.gdshaderinc.
- frente, lado (perfil esquerdo, câmera em +X), 3/4: ortográficas 1024², o aldeão sempre à direita da câmera;
- câmera do jogo (CameraRig.cs: 55°, FOV 45°, 16 m ÷ zoom, 3024×1890) nos zooms 0,4 / 1 / 2,5;
- a frente da protagonista sozinha (máscara para medir a cabeça como na folha).
Mede: triângulos brutos, altura em px na câmera do jogo (vértice a vértice, protagonista e aldeão), simetria
(distância de cada vértice ao espelho mais próximo, em mm a 0,80 m).

Saída: <pasta>/<nome>_{frente,lado,tres_quartos,jogo_0.4,jogo_1.0,jogo_2.5,mascara}.png (fundo transparente) e
<nome>_medidas.json. A montagem é do folha_meshy.py.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/render_meshy.py -- <pasta> <glb> [<glb> ...]
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Vector, kdtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import (GAME_H, GAME_W, ROOT, eevee_scene, game_camera, hex_linear, import_glb, load_rest,  # noqa: E402
                      mesh_objects, mesh_points, render, toon_material)

HEIGHT_M = 0.80
PELE = "#91ADB7"
PELE_ALDEAO = "#AEBFD3"
ALDEAO = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
ROSTO = ROOT / "assets/modelos/aldeao_v2/rosto"
ZOOMS = (0.4, 1.0, 2.5)
SIDE_M = 0.45  # centro do aldeão a esta distância da protagonista, para a direita da câmera
ORTHO_RES = 1024

# Luz do diagnostico_v1.py (a folha aprovada da v1): fraca, fria, quase de cima; ambiente roxo-acinzentado.
SUN_EULER = Euler((math.radians(28), 0, math.radians(-20)))
SUN_RGB = tuple(c * 0.75 for c in (0.72, 0.78, 0.95))
AMBIENT_RGB = tuple(c * 0.6 for c in (0.36, 0.33, 0.44))


def light_dir() -> Vector:
    return (SUN_EULER.to_matrix() @ Vector((0, 0, 1))).normalized()


def root_of(objects, name):
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    for obj in objects:
        if obj.parent is None:
            obj.parent = root
    return root


def load_protagonist(glb: Path):
    objects = import_glb(glb)
    mat = toon_material("pele", light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(PELE))
    for obj in mesh_objects(objects):
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    root = root_of(objects, "protagonista")
    bpy.context.view_layer.update()
    pts = mesh_points(objects)
    low, high = pts.min(axis=0), pts.max(axis=0)
    s = HEIGHT_M / (high[2] - low[2])
    root.scale = (s, s, s)
    root.location = (-(low[0] + high[0]) / 2 * s, -(low[1] + high[1]) / 2 * s, -low[2] * s)
    bpy.context.view_layer.update()
    return objects, root


def load_villager():
    rosto = json.loads((ROSTO / "rosto.json").read_text())
    skin = toon_material("pele_aldeao", light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(PELE_ALDEAO))
    patches = {}
    for key, name in (("olhos", "Olhos"), ("boca", "Boca")):
        info = rosto[key]
        img = bpy.data.images.load(str(ROSTO / f"{key}.png"))
        patches[name] = toon_material(f"rosto_{key}", light_dir(), SUN_RGB, AMBIENT_RGB, image=img,
                                      cell=(0, info["colunas"], info["linhas"]))
    objects = load_rest(ALDEAO)
    for obj in mesh_objects(objects):
        mat = patches.get(obj.name, skin)
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return objects, root_of(objects, "aldeao")


def triangles(objects) -> int:
    total = 0
    for obj in mesh_objects(objects):
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
    return total


def symmetry_mm(pts: np.ndarray) -> dict:
    """Espelha em x = 0 (a figura já está centrada) e mede a distância ao vértice mais próximo do original."""
    tree = kdtree.KDTree(len(pts))
    for i, p in enumerate(pts):
        tree.insert(Vector(p), i)
    tree.balance()
    d = np.array([tree.find(Vector((-p[0], p[1], p[2])))[2] for p in pts]) * 1000
    return {"media_mm": round(float(d.mean()), 2), "p95_mm": round(float(np.percentile(d, 95)), 2),
            "max_mm": round(float(d.max()), 2)}


def ortho_camera(scene, direction: Vector, center: Vector, size: float):
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size
    cam.location = center + direction.normalized() * 10
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    bpy.context.view_layer.update()  # matrix_world válida para camera_right()
    return cam


def camera_right(cam) -> Vector:
    r = cam.matrix_world.to_3x3() @ Vector((1, 0, 0))
    r.z = 0
    return r.normalized()


def projected(scene, cam, pts: np.ndarray) -> np.ndarray:
    """Pontos do mundo em pixels da imagem (x para a direita, y para baixo)."""
    w, h = scene.render.resolution_x, scene.render.resolution_y
    out = [world_to_camera_view(scene, cam, Vector(p)) for p in pts]
    return np.array([[v.x * w, (1 - v.y) * h] for v in out])


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    for glb in (Path(a).resolve() for a in args[1:]):
        name = glb.stem
        scene = eevee_scene(transparent=True)
        scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0  # o toon é emissivo
        prot, _ = load_protagonist(glb)
        vill, vroot = load_villager()
        ppts = mesh_points(prot)
        measures = {"glb": str(glb.relative_to(ROOT)), "triangulos": triangles(prot), "altura_m": HEIGHT_M,
                    "largura_m": round(float(ppts[:, 0].max() - ppts[:, 0].min()), 3),
                    "profundidade_m": round(float(ppts[:, 1].max() - ppts[:, 1].min()), 3),
                    "simetria": symmetry_mm(ppts), "jogo": {}}

        # Máscara da frente, só a protagonista (a mesma escala de figura da folha: ~90% do quadro).
        vroot.hide_render = True
        for o in vill:
            o.hide_render = True
        scene.render.resolution_x = scene.render.resolution_y = ORTHO_RES
        center = Vector((0, 0, HEIGHT_M / 2))
        cam = ortho_camera(scene, Vector((0, -1, 0)), center, HEIGHT_M * 1.1)
        render(scene, out / f"{name}_mascara.png")
        bpy.data.objects.remove(cam)
        for o in vill:
            o.hide_render = False
        vroot.hide_render = False

        for view, direction in (("frente", Vector((0, -1, 0))), ("lado", Vector((1, 0, 0))),
                                ("tres_quartos", Vector((1, -1, 0)))):
            scene.render.resolution_x = scene.render.resolution_y = ORTHO_RES
            cam = ortho_camera(scene, direction, Vector((0, 0, 0)), 1.0)
            right = camera_right(cam)
            vroot.location = right * SIDE_M
            bpy.context.view_layer.update()
            c = right * (SIDE_M / 2) + Vector((0, 0, HEIGHT_M / 2))
            cam.location = c + direction.normalized() * 10
            cam.data.ortho_scale = max(HEIGHT_M, SIDE_M + 0.5) * 1.12
            render(scene, out / f"{name}_{view}.png")
            bpy.data.objects.remove(cam)

        vroot.location = (SIDE_M, 0, 0)
        bpy.context.view_layer.update()
        vpts = mesh_points(vill)
        for zoom in ZOOMS:
            cam = game_camera(scene, zoom)
            bpy.context.view_layer.update()  # matrix_world da câmera nova, antes de projetar
            pp, vp = projected(scene, cam, ppts), projected(scene, cam, vpts)
            both = np.vstack([pp, vp])
            measures["jogo"][str(zoom)] = {
                "protagonista_px": round(float(pp[:, 1].max() - pp[:, 1].min()), 1),
                "aldeao_px": round(float(vp[:, 1].max() - vp[:, 1].min()), 1),
                "caixa_px": [float(both[:, 0].min()), float(both[:, 1].min()), float(both[:, 0].max()), float(both[:, 1].max())],
                "tela": [GAME_W, GAME_H]}
            render(scene, out / f"{name}_jogo_{zoom}.png")
            bpy.data.objects.remove(cam)
        (out / f"{name}_medidas.json").write_text(json.dumps(measures, indent=2, ensure_ascii=False) + "\n")
        print("MEDIDAS " + json.dumps(measures, ensure_ascii=False), flush=True)


main()

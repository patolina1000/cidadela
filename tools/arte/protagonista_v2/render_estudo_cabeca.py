"""Estudo de proporção da cabeça (só prévia; nenhum GLB é salvo). Blender headless.

Sobre o bruto B (corpo_b_multi_1.glb) normalizado a 0,80 m: a cabeça é escalada de forma uniforme a partir da base
do pescoço (tudo acima dela, com uma faixa de 1,5 cm abaixo que só alarga em x/y, para a malha não rasgar) até a
cabeça (topo ao queixo) ser a fração pedida da altura; depois a figura inteira vai à altura total pedida.
Fator da cabeça: s = r·base ÷ (h − r·(topo − base)), com h = topo − queixo (marcos do estudo_cabeca.py marcos).

Cada variação: frente ortográfica (mesma escala em todas, 1,15 m de quadro) e câmera do jogo (CameraRig.cs) nos
zooms 0,4 / 1 / 2,5, sempre com o aldeão v2 (só o corpo) ao lado. Mais uma fileira com a v1 texturizada como
estava no jogo. Toon e luz do render_meshy.py. Px por projeção de vértices.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/render_estudo_cabeca.py -- <pasta> <marcos.json>
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import GAME_H, GAME_W, ROOT, V1, eevee_scene, game_camera, hex_linear, import_glb, load_rest, mesh_objects, mesh_points, render, toon_material  # noqa: E402,E501
from render_meshy import (AMBIENT_RGB, PELE, SUN_EULER, SUN_RGB, load_villager, light_dir, ortho_camera,  # noqa: E402
                          projected, root_of)

BRUTO = ROOT / "assets/modelos/protagonista_v2/meshy/corpo_b_multi_1.glb"
BASE_H = 0.80  # altura em que os marcos foram medidos
RAMP = 0.015
ZOOMS = (0.4, 1.0, 2.5)
ORTHO = 1.15
GAP = 0.06  # folga entre a mão da protagonista e o aldeão


def head_factor(r: float, m: dict) -> float:
    base, top, chin = m["base_pescoco_z"], m["topo_z"], m["queixo_z"]
    return r * base / ((top - chin) - r * (top - base))


def baked_protagonist():
    objects = import_glb(BRUTO)
    mat = toon_material("pele", light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(PELE))
    meshes = mesh_objects(objects)
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    bpy.context.view_layer.update()
    pts = mesh_points(objects)
    low, high = pts.min(axis=0), pts.max(axis=0)
    k = BASE_H / (high[2] - low[2])
    norm = Matrix.Translation((-(low[0] + high[0]) / 2 * k, -(low[1] + high[1]) / 2 * k, -low[2] * k)) @ Matrix.Scale(k, 4)
    for obj in meshes:  # tudo em coordenadas do mundo, sem pais: a deformação trabalha direto nos vértices
        mw = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = Matrix.Identity(4)
        obj.data.transform(norm @ mw)
    for obj in objects:
        if obj.type != "MESH":
            bpy.data.objects.remove(obj)
    base = {obj.name: np.array([v.co[:] for v in obj.data.vertices]) for obj in meshes}
    return meshes, base


def apply_variant(meshes, base, marks, ratio, height) -> dict:
    s = 1.0 if ratio is None else head_factor(ratio, marks)
    nb = marks["base_pescoco_z"]
    allp = np.vstack(list(base.values()))
    ring = allp[np.abs(allp[:, 2] - nb) < 0.004]
    pivot = np.array([ring[:, 0].mean(), ring[:, 1].mean(), nb])
    out = {}
    for obj in meshes:
        p = base[obj.name].copy()
        above = p[:, 2] >= nb
        p[above] = pivot + (p[above] - pivot) * s
        band = (p[:, 2] < nb) & (p[:, 2] > nb - RAMP)
        w = (p[band, 2] - (nb - RAMP)) / RAMP
        p[band, :2] = pivot[:2] + (p[band, :2] - pivot[:2]) * (1 + (s - 1) * w)[:, None]
        out[obj.name] = p
    top = max(p[:, 2].max() for p in out.values())
    k = height / top  # pés continuam em z = 0
    for obj in meshes:
        p = out[obj.name] * k
        obj.data.vertices.foreach_set("co", p.ravel())
        obj.data.update()
    head = s * (marks["topo_z"] - marks["queixo_z"]) * k
    return {"fator_cabeca": round(s, 3), "altura_m": round(top * k, 4), "cabeca_m": round(head, 4),
            "cabeca_sobre_altura": round(head / (top * k), 3)}


def pbr_lights(scene) -> None:
    """v1 com o material dela (render_meshy/diagnostico_v1): sol de verdade e ambiente só para o PBR."""
    sun = bpy.data.objects.new("crepusculo", bpy.data.lights.new("crepusculo", "SUN"))
    sun.data.energy = 1.0
    sun.data.color = SUN_RGB
    sun.data.angle = math.radians(20)
    sun.rotation_euler = SUN_EULER
    scene.collection.objects.link(sun)
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*AMBIENT_RGB, 1)
    bg.inputs["Strength"].default_value = 1.0


def shoot_all(scene, name, prot_objects, vroot, vill, out, info) -> None:
    """Frente ortográfica e câmera do jogo, com o aldeão encostado à direita da mão da protagonista."""
    ppts = mesh_points(prot_objects)
    vroot.location = (0, 0, 0)
    bpy.context.view_layer.update()
    vx0 = mesh_points(vill)[:, 0].min()
    vroot.location = (ppts[:, 0].max() + GAP - vx0, 0, 0)
    bpy.context.view_layer.update()
    vpts = mesh_points(vill)
    both = np.vstack([ppts, vpts])
    cx = (both[:, 0].min() + both[:, 0].max()) / 2
    scene.render.resolution_x = scene.render.resolution_y = 1024
    cam = ortho_camera(scene, Vector((0, -1, 0)), Vector((cx, 0, ORTHO / 2 - 0.04)), ORTHO)
    render(scene, out / f"{name}_frente.png")
    bpy.data.objects.remove(cam)
    info["jogo"] = {}
    for zoom in ZOOMS:
        cam = game_camera(scene, zoom)
        bpy.context.view_layer.update()
        pp, vp = projected(scene, cam, ppts), projected(scene, cam, vpts)
        allp = np.vstack([pp, vp])
        info["jogo"][str(zoom)] = {
            "protagonista_px": round(float(pp[:, 1].max() - pp[:, 1].min()), 1),
            "aldeao_px": round(float(vp[:, 1].max() - vp[:, 1].min()), 1),
            "caixa_px": [float(allp[:, 0].min()), float(allp[:, 1].min()), float(allp[:, 0].max()), float(allp[:, 1].max())],
            "tela": [GAME_W, GAME_H]}
        render(scene, out / f"{name}_jogo_{zoom}.png")
        bpy.data.objects.remove(cam)


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    out, marks = Path(args[0]), json.loads(Path(args[1]).read_text())
    out.mkdir(parents=True, exist_ok=True)
    report = {"marcos": marks, "variacoes": {}}

    scene = eevee_scene(transparent=True)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    meshes, base = baked_protagonist()
    vill, vroot = load_villager()
    for ratio in marks["fracoes"]:
        for height in (0.80, 0.67):
            name = f"cabeca_{'atual' if ratio is None else round(ratio * 1000)}_{round(height * 100)}"
            info = apply_variant(meshes, base, marks, ratio, height)
            info.update({"fracao_pedida": ratio, "altura_pedida": height})
            shoot_all(scene, name, meshes, vroot, vill, out, info)
            report["variacoes"][name] = info
            print("VAR " + name + " " + json.dumps(info), flush=True)

    # v1 como estava no jogo (textura e escala do GLB), ao lado do mesmo aldeão.
    scene = eevee_scene(transparent=True)
    pbr_lights(scene)
    v1 = load_rest(V1)
    root_of(v1, "v1")
    vill, vroot = load_villager()
    pts = mesh_points(v1)
    info = {"altura_m": round(float(pts[:, 2].max() - pts[:, 2].min()), 4)}
    shoot_all(scene, "v1", v1, vroot, vill, out, info)
    report["v1"] = info
    print("VAR v1 " + json.dumps(info), flush=True)
    (out / "estudo_render.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()

"""Protagonista v2, parada 1: quadros para os GIFs de comparação de clipes (Blender headless). Versão do
aldeao_v2/gif_clipes.py para a protagonista: 0,80 m (o rig da Meshy já vem nessa altura), pele #91ADB7.

Para cada opção (rótulo, GLB, nome da ação): importa, leva à escala do jogo, tira o avanço de raiz se houver,
mede a passada (raiz ou pés) e renderiza cada quadro do ciclo em duas câmeras: a do jogo (55°, ortográfica,
fundo transparente; a montagem reduz o aldeão a 44 px e amplia 3x sem suavizar) e de lado. O chão é um plano
com grade de 10 cm que desliza para trás na velocidade da passada, para ver se os pés deslizam.
Saída: <pasta>/<rotulo>/<vista>_<quadro>.png e <pasta>/<rotulo>/info.json. A montagem dos GIFs é do gif_montar.py.

Uso:
  Blender -b --factory-startup --python tools/arte/protagonista_v2/gif_clipes.py -- <pasta_saida> <rotulo>=<glb>:<acao> [...]
  (glb relativo à raiz do repositório; acao = nome da ação no arquivo)
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aldeao_v2"))
from corpo_lib import ROOT, flat_material, game_camera_offset, import_glb, set_smooth, setup_scene, shoot, twilight_lights  # noqa: E402
from rig_lib import loop_gap, measure_stride, play, remove_root_motion, rest_points  # noqa: E402

SKIN = (0.283, 0.418, 0.474, 1.0)  # #91ADB7 em linear
HEIGHT = 0.80

RESOLUTION = 384
ORTHO_GAME, ORTHO_SIDE = 1.3, 1.15
GRID_CELL = 0.10  # m


def grid_texture():
    size = 256
    img = bpy.data.images.new("grade", size, size)
    px = np.full((size, size, 4), (0.36, 0.34, 0.42, 1.0), dtype=np.float32)
    px[:, :2] = (0.62, 0.60, 0.70, 1.0)
    px[:2, :] = (0.62, 0.60, 0.70, 1.0)
    img.pixels = px.ravel().tolist()
    return img


def ground(scene, speed):
    plane = bpy.data.meshes.new("chao")
    plane.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    uv = plane.uv_layers.new()
    for i, (u, v) in enumerate(((0, 0), (60, 0), (60, 60), (0, 60))):  # 6 m / 0,1 m = 60 células
        uv.data[i].uv = (u, v)
    obj = bpy.data.objects.new("chao", plane)
    scene.collection.objects.link(obj)
    mat = bpy.data.materials.new("chao")
    mat.use_nodes = True
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = grid_texture()
    tex.interpolation = "Closest"
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 1.0
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    plane.materials.append(mat)
    obj["speed"] = speed
    return obj


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    views = ("jogo", "lado")
    if args[0].startswith("--vistas="):
        views = tuple(args[0][len("--vistas="):].split(","))
        args = args[1:]
    out = Path(args[0])
    for spec in args[1:]:
        label, rest = spec.split("=", 1)
        glb, action_name = rest.rsplit(":", 1)
        folder = out / label
        folder.mkdir(parents=True, exist_ok=True)
        scene = setup_scene(RESOLUTION, transparent=True)
        twilight_lights(scene)
        objs = import_glb(ROOT / glb)
        armature = next(o for o in objs if o.type == "ARMATURE")
        meshes = [o for o in objs if o.type == "MESH"]
        body = max(meshes, key=lambda o: len(o.data.vertices))
        for a in list(bpy.data.actions):
            if a.name != action_name:
                bpy.data.actions.remove(a)
        action = bpy.data.actions[action_name]
        if armature.animation_data:
            for t in armature.animation_data.nla_tracks:
                t.mute = True
        rest_h = float(np.ptp(rest_points(body)[:, 2]))
        if abs(rest_h - HEIGHT) > 0.01:
            raise RuntimeError(f"{glb}: altura de repouso {rest_h:.3f} m, esperado {HEIGHT}")
        for m in meshes:
            if m is body:
                flat_material([m], SKIN, matte=True)
            set_smooth([m], True)
        root_speed = remove_root_motion(armature, action)
        feet_speed = measure_stride(armature, action)
        gap = loop_gap(armature, action)
        speed = root_speed if root_speed > 0.05 else (0.0 if (np.isnan(feet_speed) or feet_speed < 0.05) else feet_speed)
        fps = scene.render.fps / scene.render.fps_base
        start, end = (int(f) for f in action.frame_range)
        info = {"glb": glb, "acao": action_name, "quadros": [start, end], "fps": fps, "duracao_s": (end - start) / fps,
                "velocidade_raiz_m_s": round(root_speed, 3), "passada_pes_m_s": None if np.isnan(feet_speed) else round(feet_speed, 3),
                "velocidade_chao_m_s": round(speed, 3), "laco_m": round(gap, 4)}
        armature.data.pose_position = "REST"
        bpy.context.view_layer.update()
        pts = rest_points(body)
        low, high = pts.min(axis=0), pts.max(axis=0)
        center = Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (low[2] + high[2]) / 2))
        info["altura_repouso_m"] = float(high[2] - low[2])
        armature.data.pose_position = "POSE"
        play(armature, action)
        floor = ground(scene, speed)
        step = 2 if end - start > 100 else 1  # idles longos: metade dos quadros
        info["fps"] = fps / step
        for f in range(start, end, step):  # o último quadro repete o primeiro no laço
            scene.frame_set(f)
            floor.location.y = ((f - start) / fps * speed) % GRID_CELL  # a grade recua (+Y) na velocidade da passada
            if "jogo" in views:
                shoot(scene, center + game_camera_offset(3), center, ORTHO_GAME, folder / f"jogo_{f:03d}.png")
            if "lado" in views:  # de lado, 22° acima do chão: a grade aparece e o deslize dos pés também
                side = Vector((math.cos(math.radians(22)), 0, math.sin(math.radians(22)))) * 2.5
                shoot(scene, center + side, center, ORTHO_SIDE, folder / f"lado_{f:03d}.png")
        (folder / "info.json").write_text(json.dumps(info, indent=2) + "\n")
        print("INFO " + label + " " + json.dumps(info))


main()

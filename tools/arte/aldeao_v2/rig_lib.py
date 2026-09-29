"""Funções de rig compartilhadas (montar_rig.py, colocar_retalhos.py, gif_clipes.py): escala do jogo pelo objeto
armature, transferência de pesos, tocar ação, laço, remoção do avanço de raiz e passada."""

import bpy
import numpy as np
from mathutils import Vector

from corpo_lib import HEIGHT_M

STRIDE_BONES = ("LeftToeBase", "RightToeBase")


def rest_points(mesh_obj):
    return np.array([[p.x, p.y, p.z] for p in (mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices)])


def normalize_rig(armature, raw_mesh):
    """Escala e posiciona pelo objeto armature: a malha crua em pose de repouso fica com 0,40 m, pés em z = 0,
    centro dos pés na origem (mesma regra de limpar_corpo.normalize)."""
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    pts = rest_points(raw_mesh)
    low, high = pts.min(axis=0), pts.max(axis=0)
    s = HEIGHT_M / (high[2] - low[2])
    feet = pts[pts[:, 2] < low[2] + (high[2] - low[2]) * 0.03]
    cx, cy = (feet[:, 0].min() + feet[:, 0].max()) / 2, (feet[:, 1].min() + feet[:, 1].max()) / 2
    armature.scale = armature.scale * s
    armature.location = armature.location * s + Vector((-cx * s, -cy * s, -low[2] * s))
    bpy.context.view_layer.update()
    pts = rest_points(raw_mesh)
    return pts.min(axis=0), pts.max(axis=0)


def transfer_weights(src, dst, armature):
    for g in src.vertex_groups:
        if g.name not in dst.vertex_groups:
            dst.vertex_groups.new(name=g.name)
    mod = dst.modifiers.new("pesos", "DATA_TRANSFER")
    mod.object = src
    mod.use_vert_data = True
    mod.data_types_verts = {"VGROUP_WEIGHTS"}
    mod.vert_mapping = "POLYINTERP_NEAREST"
    mod.layers_vgroup_select_src = "ALL"
    mod.layers_vgroup_select_dst = "NAME"
    bpy.context.view_layer.objects.active = dst
    bpy.ops.object.modifier_apply(modifier=mod.name)
    dst.parent = armature
    dst.matrix_parent_inverse = armature.matrix_world.inverted()
    arm = dst.modifiers.new("Armature", "ARMATURE")
    arm.object = armature
    # Vértice sem peso nenhum (fora do alcance da transferência) recebe o osso mais perto: evita pontos parados.
    unweighted = [v.index for v in dst.data.vertices if not v.groups]
    if unweighted:
        bones = {b.name: armature.matrix_world @ b.head_local for b in armature.data.bones}
        for i in unweighted:
            p = dst.matrix_world @ dst.data.vertices[i].co
            nearest = min(bones, key=lambda n: (bones[n] - p).length)
            dst.vertex_groups[nearest].add([i], 1.0, "REPLACE")
    return len(unweighted)


def play(armature, action):
    armature.animation_data_create()
    armature.animation_data.action = action
    if getattr(action, "slots", None):
        armature.animation_data.action_slot = action.slots[0]


def loop_gap(armature, action) -> float:
    """Diferença (m) entre a pose do último e do primeiro quadro, somada nos dedos dos pés e nas mãos."""
    scene = bpy.context.scene
    armature.data.pose_position = "POSE"
    play(armature, action)
    start, end = (int(f) for f in action.frame_range)
    bones = ("LeftToeBase", "RightToeBase", "LeftHand", "RightHand", "Head")

    def pose(frame):
        scene.frame_set(frame)
        return [(armature.matrix_world @ armature.pose.bones[b].head).copy() for b in bones]
    a, b = pose(start), pose(end)
    return float(sum((p - q).length for p, q in zip(a, b)))


def remove_root_motion(armature, action, root="Hips") -> float:
    """Tira o avanço horizontal do quadril (clipes da biblioteca com deslocamento de raiz, como a investida):
    ajusta uma reta à posição do quadril no mundo ao longo do clipe e subtrai a parte horizontal, quadro a
    quadro, das curvas de posição do osso. O balanço vertical fica. Devolve a velocidade da raiz (m/s)."""
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    armature.data.pose_position = "POSE"
    play(armature, action)
    start, end = (int(f) for f in action.frame_range)
    frames = list(range(start, end + 1))
    world = []
    for frame in frames:
        scene.frame_set(frame)
        world.append(np.array((armature.matrix_world @ armature.pose.bones[root].head)[:]))
    world = np.array(world)
    t = (np.array(frames) - start) / fps
    vel = np.array([np.polyfit(t, world[:, i], 1)[0] for i in range(3)])
    vel[2] = 0.0  # só o avanço horizontal sai
    bone = armature.data.bones[root]
    to_local = (armature.matrix_world @ bone.matrix_local).to_3x3().inverted()
    curves = {c.array_index: c for c in action_fcurves(action) if c.data_path == f'pose.bones["{root}"].location'}
    if not curves:
        raise RuntimeError(f"sem curva de posição do {root}")
    for k in range(len(curves[0].keyframe_points)):
        frame = curves[0].keyframe_points[k].co[0]
        delta_world = Vector((-vel * ((frame - start) / fps)).tolist())
        delta_local = to_local @ delta_world
        for i, c in curves.items():
            c.keyframe_points[k].co[1] += delta_local[i]
    for c in curves.values():
        c.update()
    return float(np.linalg.norm(vel[:2]))


def action_fcurves(action):
    if hasattr(action, "fcurves") and len(action.fcurves):
        return list(action.fcurves)
    out = []
    for layer in action.layers:  # Blender 4.4+: ação em camadas
        for strip in layer.strips:
            for bag in strip.channelbags:
                out += list(bag.fcurves)
    return out


def measure_stride(armature, action) -> float:
    """m/s com que o pé de apoio recua (+Y, a frente é -Y): mediana das velocidades dos dedos quando recuam."""
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    armature.data.pose_position = "POSE"
    play(armature, action)
    start, end = (int(f) for f in action.frame_range)
    track = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        track.append({b: (armature.matrix_world @ armature.pose.bones[b].head).copy() for b in STRIDE_BONES})
    speeds = [(now[b].y - before[b].y) * fps for before, now in zip(track, track[1:]) for b in STRIDE_BONES if now[b].y > before[b].y]
    return float(np.median(speeds))




def close_loop(action, fraction=0.25, min_frames=4) -> int:
    """Fecha o laço sem pulo: nos últimos `fraction` quadros de cada curva, mistura o valor com o do primeiro
    quadro (peso 0 -> 1, suave), de modo que o último quadro fique igual ao primeiro. Quaternions com o sinal
    do primeiro quadro. Devolve o número de quadros misturados."""
    curves = action_fcurves(action)
    start, end = action.frame_range
    n = int(end - start)
    tail = max(min_frames, int(round(n * fraction)))
    quats = {}
    for c in curves:
        if c.data_path.endswith("rotation_quaternion"):
            quats.setdefault(c.data_path, {})[c.array_index] = c
    for path, comps in quats.items():  # q e -q são a mesma rotação: alinha o sinal de cada quadro ao do anterior
        keys = [sorted(comps)[i] for i in range(len(comps))]
        pts = [comps[k].keyframe_points for k in keys]
        count = min(len(pk) for pk in pts)
        prev = [pts[i][0].co[1] for i in range(len(keys))]
        for j in range(1, count):
            cur = [pts[i][j].co[1] for i in range(len(keys))]
            if sum(a * b for a, b in zip(prev, cur)) < 0:
                for i in range(len(keys)):
                    pts[i][j].co[1] = -cur[i]
                cur = [-v for v in cur]
            prev = cur
    for c in curves:
        pts = c.keyframe_points
        if len(pts) < 2:
            continue
        first = pts[0].co[1]
        m = len(pts)
        for j in range(max(0, m - tail), m):
            t = (j - (m - 1 - tail)) / tail  # 0 no início da cauda, 1 no último quadro
            w = t * t * (3 - 2 * t)
            pts[j].co[1] = pts[j].co[1] * (1 - w) + first * w
        c.update()
    return tail

"""Funções de IK da prova de operação (girar_roda.py, medir_ergonomia.py): mãos numa manopla que gira num círculo
vertical na frente do corpo, tronco acompanhando pouco, pés fixos. Servem para qualquer corpo com o rig da Meshy
(nomes Hips, Spine02, Spine01, Spine, LeftArm, LeftForeArm, LeftHand...), em qualquer escala (usa a escala do
mundo do armature, que inclui a de um nó pai). Espaço do Blender: o personagem olha para -Y, a direita dele é -X.
Importado com sys.path apontando para esta pasta."""

import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

CHAIN = ("Arm", "ForeArm", "Hand")
SIDES = ("Left", "Right")
GRIP_HALF = 0.018  # cada mão de um lado da manopla (m, no aldeão; medir_ergonomia escala pela mão)
KNOB_R = 0.012  # raio da manopla
LEAN0, LEAN1, TWIST, BEND = 4.0, 8.0, 8.0, 4.0  # tronco, graus
POLE_OFFSET = Vector((0.06, 0.03, -0.04))  # polo do cotovelo: para fora, para trás, para baixo (aldeão)
TOLERANCE_MM = 5.0  # "fecha": palma a no máximo 5 mm do ponto da manopla


def world_scale(arm) -> float:
    return arm.matrix_world.to_scale()[0]


def body_mesh(objects):
    """A malha do corpo: a com mais vértices entre as que têm grupos de vértices (fora Olhos e Boca)."""
    meshes = [o for o in objects if o.type == "MESH" and o.vertex_groups and o.name.split(".")[0] not in ("Olhos", "Boca")]
    return max(meshes, key=lambda o: len(o.data.vertices))


def dominant(body):
    names = [g.name for g in body.vertex_groups]
    return [names[max(v.groups, key=lambda g: g.weight).group] if v.groups else None for v in body.data.vertices]


def hand_points(body, side) -> np.ndarray:
    dom = dominant(body)
    return np.array([(body.matrix_world @ v.co)[:] for v, d in zip(body.data.vertices, dom) if d == f"{side}Hand"])


def fix_lengths(arm, body) -> dict:
    """Comprimento real nos ossos do braço (o importador do Blender erra quando há escala no nó): muda só `length`,
    direção e rolagem ficam. Braço e antebraço até o filho; mão até o centro da palma (centro dos vértices da mão
    projetado no eixo do osso). Devolve os comprimentos no mundo e a mudança nas matrizes de repouso."""
    s = world_scale(arm)
    palms = {side: Vector(hand_points(body, side).mean(axis=0).tolist()) for side in SIDES}
    before = {b.name: b.matrix_local.copy() for b in arm.data.bones}
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    lengths = {}
    for side in SIDES:
        for bone, child in ((f"{side}Arm", f"{side}ForeArm"), (f"{side}ForeArm", f"{side}Hand")):
            eb[bone].length = (eb[child].head - eb[bone].head).length
            lengths[bone] = eb[bone].length * s
        hand = eb[f"{side}Hand"]
        y = (hand.tail - hand.head).normalized()
        hand.length = (arm.matrix_world.inverted() @ palms[side] - hand.head).dot(y)
        lengths[f"{side}Hand"] = hand.length * s
    for name, child in (("Spine02", "Spine01"), ("Spine01", "Spine")):
        eb[name].length = (eb[child].head - eb[name].head).length
    bpy.ops.object.mode_set(mode="OBJECT")
    rot = max(before[b.name].to_quaternion().rotation_difference(b.matrix_local.to_quaternion()).angle for b in arm.data.bones)
    rot = min(rot, 2 * math.pi - rot)
    pos = max((before[b.name].to_translation() - b.matrix_local.to_translation()).length * s for b in arm.data.bones)
    return {"comprimentos_m": {k: round(v, 4) for k, v in lengths.items()},
            "repouso_dif_rotacao_graus": round(math.degrees(rot), 6), "repouso_dif_posicao_mm": round(pos * 1000, 6)}


def reset_pose(arm) -> None:
    arm.animation_data_clear()
    arm.data.pose_position = "POSE"
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


def setup_ik(arm, pole_scale=1.0) -> tuple:
    """IK nas mãos: cadeia mão-antebraço-braço, ponta no centro da palma, sem esticar, polo no cotovelo."""
    targets, poles = {}, {}
    for side, out in (("Left", 1), ("Right", -1)):
        elbow = arm.matrix_world @ arm.data.bones[f"{side}ForeArm"].head_local
        off = POLE_OFFSET * pole_scale
        targets[side] = empty(f"alvo_{side}")
        poles[side] = empty(f"polo_{side}", elbow + Vector((off.x * out, off.y, off.z)))
        pb = arm.pose.bones[f"{side}Hand"]
        c = pb.constraints.new("IK")
        c.target, c.pole_target = targets[side], poles[side]
        c.chain_count, c.use_tail, c.use_stretch, c.iterations = 3, True, False, 500
        pb.ik_stiffness_x = pb.ik_stiffness_y = pb.ik_stiffness_z = 0.5
        for b in CHAIN:
            arm.pose.bones[f"{side}{b}"].ik_stretch = 0.0
    return targets, poles


def palm(arm, side) -> Vector:
    return arm.matrix_world @ arm.pose.bones[f"{side}Hand"].tail


def front_profile(body) -> list:
    """(z, y mínimo) da frente do corpo sem os braços, numa faixa central de ±12,5% da altura em x, fatias de 1/40
    da altura (no aldeão: |x| < 5 cm, fatias de 1 cm)."""
    dom = dominant(body)
    arms = {f"{s}{b}" for s in SIDES for b in CHAIN}
    pts = np.array([(body.matrix_world @ v.co)[:] for v, d in zip(body.data.vertices, dom) if d not in arms])
    low, high = pts[:, 2].min(), pts[:, 2].max()
    h = high - low
    prof = []
    for z in np.arange(low, high + 1e-9, h / 40):
        sel = pts[(np.abs(pts[:, 2] - z) < h * 0.015) & (np.abs(pts[:, 0]) < h * 0.125)]
        if len(sel):
            prof.append((float(z), float(sel[:, 1].min())))
    return prof


def grip_distance(prof, radius, axis_z, hand_clear) -> float:
    """Distância (m, para -Y, a partir de y = 0) do plano das manoplas: livre do corpo em toda a altura do círculo."""
    lo, hi = axis_z - radius - KNOB_R - 0.01, axis_z + radius + KNOB_R + 0.01
    return max(-y for z, y in prof if lo <= z <= hi) + hand_clear


def handle_center(phase, radius, dist, axis_z) -> Vector:
    """Manopla da alça no espaço do personagem. Fase 0 no topo, depois à direita dele (-X)."""
    a = 2 * math.pi * phase
    return Vector((-radius * math.sin(a), -dist, axis_z + radius * math.cos(a)))


def spine_pose(arm, phase) -> None:
    """Tronco: inclina para a frente (mais com a alça embaixo), gira e flexiona para o lado da alça. Metade em
    Spine02 e metade em Spine01, no espaço do armature (sem rotação: eixos = mundo)."""
    a = 2 * math.pi * phase
    side = -math.sin(a)  # +1 com a alça à esquerda dele (+X), -1 à direita
    lean = math.radians(LEAN0 + LEAN1 * (1 - math.cos(a)) / 2)
    rot = (Matrix.Rotation(math.radians(TWIST) * side, 3, "Z") @ Matrix.Rotation(math.radians(BEND) * side, 3, "Y")
           @ Matrix.Rotation(lean, 3, "X"))
    half = Quaternion((1, 0, 0, 0)).slerp(rot.to_quaternion(), 0.5).to_matrix().to_4x4()
    for name in ("Spine02", "Spine01"):
        arm.pose.bones[name].rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    for name in ("Spine02", "Spine01"):
        pb = arm.pose.bones[name]
        m = pb.matrix.copy()
        head = m.to_translation()
        pb.matrix = Matrix.Translation(head) @ half @ Matrix.Translation(-head) @ m
        bpy.context.view_layer.update()


def set_targets(targets, phase, radius, dist, axis_z, grip_half=GRIP_HALF) -> None:
    c = handle_center(phase, radius, dist, axis_z)
    targets["Left"].location = c + Vector((grip_half, 0, 0))
    targets["Right"].location = c - Vector((grip_half, 0, 0))


def misses(arm, targets) -> dict:
    return {s: (palm(arm, s) - targets[s].matrix_world.to_translation()).length for s in SIDES}


def evaluate(arm, targets, radius, dist, axis_z, phases, grip_half=GRIP_HALF) -> list:
    rows = []
    for p in phases:
        spine_pose(arm, p)
        set_targets(targets, p, radius, dist, axis_z, grip_half)
        bpy.context.view_layer.update()
        m = misses(arm, targets)
        rows.append({"fase": round(p, 4), "falta_esq_mm": round(m["Left"] * 1000, 1), "falta_dir_mm": round(m["Right"] * 1000, 1)})
    return rows


def calibrate_poles(arm, targets, poles, radius, dist, axis_z, grip_half=GRIP_HALF) -> dict:
    """Ângulo do polo por lado (as rolagens dos braços são ±90° e diferentes entre os lados): o que deixa o
    cotovelo mais perto do objeto-polo e a palma mais perto do alvo em quatro fases."""
    chosen = {}
    for side in SIDES:
        c = arm.pose.bones[f"{side}Hand"].constraints[0]
        best = None
        for ang in (-180, -135, -90, -45, 0, 45, 90, 135):
            c.pole_angle = math.radians(ang)
            score = 0.0
            for p in (0, 0.25, 0.5, 0.75):
                spine_pose(arm, p)
                set_targets(targets, p, radius, dist, axis_z, grip_half)
                bpy.context.view_layer.update()
                elbow = arm.matrix_world @ arm.pose.bones[f"{side}ForeArm"].head
                score += (elbow - poles[side].location).length + 3 * misses(arm, targets)[side]
            if best is None or score < best[0]:
                best = (score, ang)
        c.pole_angle = math.radians(best[1])
        chosen[side] = best[1]
    return chosen

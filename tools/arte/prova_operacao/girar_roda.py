"""Passo 3 da prova de operação: clipe-protótipo "girar_roda-loop" por IK no Blender, sem Meshy (headless).
Esqueleto aprovado (aldeao_corpo.glb, escala 0,004, sem normalizar). Roda provisória vertical, eixo horizontal
na altura do peito, uma alça em cada face a 0,10 m do eixo, defasadas 180°. O aldeão fica de um lado, de
frente para a face da roda, pés fixos (Hips parado); as duas mãos seguram a manopla da alça (uma de cada lado
dela) por IK durante uma volta; o tronco acompanha um pouco (inclinação, giro e flexão lateral leves).

Método:
1. Ossos com comprimento de verdade (o importador os faz 250× longos): em modo de edição, só `length` muda
   (direção e rolagem ficam; confere que as matrizes de repouso não mudaram). Braço e antebraço vão até o filho;
   a mão até o centro da palma (centro dos vértices da mão projetado no eixo do osso).
2. IK nas mãos (cadeia de 3: mão, antebraço, braço; ponta = centro da palma; sem esticar), polo no cotovelo
   (para fora, um pouco para trás e para baixo); o ângulo do polo é escolhido por lado (as rolagens são ±90°).
3. Varredura do raio (antes do clipe): para raios de 0,03 a 0,10 m, a maior distância palma-manopla na volta, com
   a distância da roda ao corpo recalculada pelo perfil da barriga. Diz até que raio as mãos fecham.
4. Clipe com o raio pedido: tronco por quadro, alvos por quadro, bake visual (tira as restrições), laço
   conferido (último quadro = primeiro); exporta só o esqueleto e o clipe (NLA, POSE).
5. Roda (roda.glb, pivô no eixo, frente +Z do glTF = face da alça A) e clipes.json.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/prova_operacao/girar_roda.py [-- <raio> <subpasta>]
  Sem argumentos: o raio pedido (0,10 m) nas saídas principais. Com argumentos (variante, ex.: 0.06 variante_r06):
  saídas em assets/modelos/prova_operacao/<subpasta>/ e assets/previews/prova_operacao/<subpasta>/.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aldeao_v2"))
from corpo_lib import ROOT, import_glb  # noqa: E402
from rig_lib import action_fcurves, close_loop, loop_gap  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SRC = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
OUT_DIR = ROOT / "assets/modelos/prova_operacao" / (ARGS[1] if len(ARGS) > 1 else "")
CLIP = OUT_DIR / "clipes/girar_roda.glb"
WHEEL = OUT_DIR / "roda.glb"
CLIPS_JSON = OUT_DIR / "clipes.json"
REPORT = ROOT / "assets/previews/prova_operacao" / (ARGS[1] if len(ARGS) > 1 else "") / "girar_roda.json"
CLIP_NAME = "girar_roda-loop"

# Escolhas técnicas da prova (não são números de design).
FPS, FRAMES = 24, 48  # 1 volta = 2 s
RADIUS = float(ARGS[0]) if ARGS else 0.10  # pedido: 0,10
AXIS_Z = 0.19  # peito: entre Spine01 (0,180) e Spine (0,209)
GRIP_HALF = 0.018  # cada mão de um lado da manopla
KNOB_R, KNOB_LEN, STEM_R, STEM_LEN = 0.012, 0.03, 0.006, 0.05
WHEEL_R, WHEEL_T, AXLE_R, AXLE_LEN = 0.125, 0.02, 0.012, 0.05
HAND_CLEAR = 0.032  # manopla (12 mm) + espessura da mão (~20 mm) na frente do corpo
COUNT_AT = 0.5  # a volta conta quando a alça A passa embaixo (fim da empurrada)
LEAN0, LEAN1, TWIST, BEND = 4.0, 8.0, 8.0, 4.0  # graus
SWEEP = (0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10)
CHAIN = ("Arm", "ForeArm", "Hand")
WOOD, IRON = "#4A3B3A", "#66636B"


def hex_linear(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


# ---------- esqueleto ----------

def fix_lengths(arm, body) -> dict:
    """Comprimento real nos ossos do braço (direção e rolagem intactas). Devolve a diferença das matrizes."""
    s = arm.scale[0]
    names = [g.name for g in body.vertex_groups]
    palms = {}
    for side in ("Left", "Right"):
        pts = [body.matrix_world @ v.co for v in body.data.vertices
               if v.groups and names[max(v.groups, key=lambda g: g.weight).group] == f"{side}Hand"]
        palms[side] = sum(pts, Vector()) / len(pts)
    before = {b.name: b.matrix_local.copy() for b in arm.data.bones}
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    lengths = {}
    for side in ("Left", "Right"):
        for bone, child in ((f"{side}Arm", f"{side}ForeArm"), (f"{side}ForeArm", f"{side}Hand")):
            eb[bone].length = (eb[child].head - eb[bone].head).length
            lengths[bone] = eb[bone].length * s
        hand = eb[f"{side}Hand"]
        y = (hand.tail - hand.head).normalized()
        palm_local = arm.matrix_world.inverted() @ palms[side]
        hand.length = (palm_local - hand.head).dot(y)
        lengths[f"{side}Hand"] = hand.length * s
    for name in ("Spine02", "Spine01"):  # coluna curta, para o giro por matriz não depender da ponta
        eb[name].length = (eb["Spine01" if name == "Spine02" else "Spine"].head - eb[name].head).length
    bpy.ops.object.mode_set(mode="OBJECT")
    diff_rot = max(math.degrees(before[b.name].to_quaternion().rotation_difference(b.matrix_local.to_quaternion()).angle % 360)
                   for b in arm.data.bones)
    diff_rot = min(diff_rot, 360 - diff_rot)
    diff_pos = max((before[b.name].to_translation() - b.matrix_local.to_translation()).length * s for b in arm.data.bones)
    return {"comprimentos_m": {k: round(v, 4) for k, v in lengths.items()},
            "repouso_dif_rotacao_graus": round(diff_rot, 6), "repouso_dif_posicao_mm": round(diff_pos * 1000, 6)}


def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


def setup_ik(arm):
    targets, poles = {}, {}
    mw = arm.matrix_world
    for side, out in (("Left", 1), ("Right", -1)):
        elbow = mw @ arm.data.bones[f"{side}ForeArm"].head_local
        targets[side] = empty(f"alvo_{side}")
        poles[side] = empty(f"polo_{side}", elbow + Vector((0.06 * out, 0.03, -0.04)))
        pb = arm.pose.bones[f"{side}Hand"]
        c = pb.constraints.new("IK")
        c.target = targets[side]
        c.pole_target = poles[side]
        c.chain_count = 3
        c.use_tail = True
        c.use_stretch = False
        c.iterations = 500
        pb.ik_stiffness_x = pb.ik_stiffness_y = pb.ik_stiffness_z = 0.5
        for b in CHAIN:
            arm.pose.bones[f"{side}{b}"].ik_stretch = 0.0
    return targets, poles


def palm(arm, side) -> Vector:
    return arm.matrix_world @ arm.pose.bones[f"{side}Hand"].tail


# ---------- roda e alvos ----------

def front_profile(body, arm) -> list:
    """(z, y mínimo) da frente do corpo sem os braços, |x| < 5 cm, fatias de 1 cm."""
    names = [g.name for g in body.vertex_groups]
    arms = {f"{s}{b}" for s in ("Left", "Right") for b in CHAIN}
    pts = np.array([(body.matrix_world @ v.co)[:] for v in body.data.vertices
                    if v.groups and names[max(v.groups, key=lambda g: g.weight).group] not in arms])
    prof = []
    for z in np.arange(0.0, 0.42, 0.01):
        sel = pts[(np.abs(pts[:, 2] - z) < 0.006) & (np.abs(pts[:, 0]) < 0.05)]
        if len(sel):
            prof.append((float(z), float(sel[:, 1].min())))
    return prof


def grip_distance(prof, radius) -> float:
    """Distância (m, para -Y) do plano das manoplas: livre da barriga e da cabeça em toda a altura do círculo."""
    lo, hi = AXIS_Z - radius - KNOB_R - 0.01, AXIS_Z + radius + KNOB_R + 0.01
    return max(-y for z, y in prof if lo <= z <= hi) + HAND_CLEAR


def handle_center(phase, radius, dist) -> Vector:
    """Manopla da alça A no espaço do aldeão (Blender: frente -Y, direita -X). Fase 0 no topo, depois à direita."""
    a = 2 * math.pi * phase
    return Vector((-radius * math.sin(a), -dist, AXIS_Z + radius * math.cos(a)))


def spine_pose(arm, phase, radius):
    """Tronco: inclina para a frente (mais com a alça embaixo), gira e flexiona para o lado da alça. Metade em
    Spine02 e metade em Spine01, aplicada no espaço do armature (sem rotação: eixos = mundo)."""
    a = 2 * math.pi * phase
    side = -math.sin(a)  # +1 com a alça à esquerda dele (+X), -1 à direita (-X)
    lean = math.radians(LEAN0 + LEAN1 * (1 - math.cos(a)) / 2)  # +X: o alto vai para a frente (-Y)
    twist = math.radians(TWIST) * side  # +Z: a frente vira para +X
    bend = math.radians(BEND) * side  # +Y: o alto vai para +X
    rot = Matrix.Rotation(twist, 3, "Z") @ Matrix.Rotation(bend, 3, "Y") @ Matrix.Rotation(lean, 3, "X")
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


def set_targets(targets, phase, radius, dist):
    c = handle_center(phase, radius, dist)
    targets["Left"].location = c + Vector((GRIP_HALF, 0, 0))
    targets["Right"].location = c - Vector((GRIP_HALF, 0, 0))


def misses(arm, targets) -> dict:
    return {s: (palm(arm, s) - targets[s].matrix_world.to_translation()).length for s in ("Left", "Right")}


def evaluate(arm, targets, radius, dist, phases) -> list:
    rows = []
    for p in phases:
        spine_pose(arm, p, radius)
        set_targets(targets, p, radius, dist)
        bpy.context.view_layer.update()
        m = misses(arm, targets)
        rows.append({"fase": round(p, 4), "falta_esq_mm": round(m["Left"] * 1000, 1), "falta_dir_mm": round(m["Right"] * 1000, 1)})
    return rows


def calibrate_poles(arm, targets, poles, dist) -> dict:
    """Ângulo do polo por lado: o que deixa o cotovelo mais perto do objeto-polo em quatro fases."""
    chosen = {}
    for side in ("Left", "Right"):
        c = arm.pose.bones[f"{side}Hand"].constraints[0]
        best = None
        for ang in (-180, -135, -90, -45, 0, 45, 90, 135):
            c.pole_angle = math.radians(ang)
            score = 0.0
            for p in (0, 0.25, 0.5, 0.75):
                spine_pose(arm, p, RADIUS)
                set_targets(targets, p, RADIUS, dist)
                bpy.context.view_layer.update()
                elbow = arm.matrix_world @ arm.pose.bones[f"{side}ForeArm"].head
                score += (elbow - poles[side].location).length + 3 * misses(arm, targets)[side]
            if best is None or score < best[0]:
                best = (score, ang)
        c.pole_angle = math.radians(best[1])
        chosen[side] = best[1]
    return chosen


# ---------- roda ----------

def build_wheel() -> bpy.types.Object:
    """Roda no seu espaço (Blender): eixo em Y, face da alça A em -Y (+Z do glTF), alça A no topo, B embaixo atrás."""
    bm = bmesh.new()

    def cyl(radius, depth, center, axis_y=True, segs=24):
        m = Matrix.Translation(center) @ (Matrix.Rotation(math.radians(90), 4, "X") if axis_y else Matrix.Identity(4))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=radius, radius2=radius, depth=depth, matrix=m)

    cyl(WHEEL_R, WHEEL_T, Vector((0, 0, 0)), segs=32)
    cyl(AXLE_R, WHEEL_T + 2 * AXLE_LEN, Vector((0, 0, 0)), segs=12)
    stem_y = WHEEL_T / 2 + STEM_LEN / 2
    knob_y = WHEEL_T / 2 + STEM_LEN + KNOB_LEN / 2
    for sign, z in ((-1, RADIUS), (1, -RADIUS)):  # A na frente (-Y) no topo; B atrás (+Y) embaixo
        cyl(STEM_R, STEM_LEN, Vector((0, sign * stem_y, z)), segs=10)
        cyl(KNOB_R, KNOB_LEN, Vector((0, sign * knob_y, z)), segs=12)
    mesh = bpy.data.meshes.new("roda")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("roda", mesh)
    bpy.context.scene.collection.objects.link(obj)
    mat = bpy.data.materials.new("madeira")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = hex_linear(WOOD)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    mesh.materials.append(mat)
    obj["knob_y"] = knob_y
    return obj


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    objects = import_glb(SRC)
    arm = next(o for o in objects if o.type == "ARMATURE")
    body = next(o for o in objects if o.name == "aldeao_corpo")
    arm.animation_data_clear()
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    report = {"esqueleto": fix_lengths(arm, body)}
    prof = front_profile(body, arm)
    arm.data.pose_position = "POSE"
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    mw = arm.matrix_world
    report["ombros_m"] = {s: [round(v, 4) for v in mw @ arm.data.bones[f"{s}Arm"].head_local] for s in ("Left", "Right")}
    report["alcance_ombro_palma_m"] = {s: round(sum(report["esqueleto"]["comprimentos_m"][f"{s}{b}"] for b in CHAIN), 4)
                                       for s in ("Left", "Right")}

    targets, poles = setup_ik(arm)
    dist = grip_distance(prof, RADIUS)
    report["poles_graus"] = calibrate_poles(arm, targets, poles, dist)

    # Varredura do raio.
    phases16 = [i / 16 for i in range(16)]
    sweep = {}
    for r in SWEEP:
        d = grip_distance(prof, r)
        rows = evaluate(arm, targets, r, d, phases16)
        sweep[f"{r:.2f}"] = {"distancia_manopla_m": round(d, 4),
                             "falta_max_mm": max(max(x["falta_esq_mm"], x["falta_dir_mm"]) for x in rows)}
    report["varredura_raio"] = sweep
    closes = [float(r) for r, v in sweep.items() if v["falta_max_mm"] <= 5.0]
    report["maior_raio_que_fecha_m"] = max(closes) if closes else None

    # Clipe com o raio pedido.
    arm.animation_data_create()
    per_frame = []
    for i in range(FRAMES + 1):
        frame = 1 + i
        p = (i % FRAMES) / FRAMES
        scene.frame_set(frame)
        spine_pose(arm, p, RADIUS)
        for name in ("Spine02", "Spine01"):
            arm.pose.bones[name].keyframe_insert("rotation_quaternion", frame=frame)
        set_targets(targets, p, RADIUS, dist)
        for t in targets.values():
            t.keyframe_insert("location", frame=frame)
    scene.frame_start, scene.frame_end = 1, FRAMES + 1
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.nla.bake(frame_start=1, frame_end=FRAMES + 1, only_selected=False, visual_keying=True, clear_constraints=True,
                     use_current_action=True, bake_types={"POSE"})
    bpy.ops.object.mode_set(mode="OBJECT")
    action = arm.animation_data.action
    action.name = CLIP_NAME
    # Faltas no clipe já assado (sem restrições): palma x manopla, quadro a quadro.
    for i in range(FRAMES):
        scene.frame_set(1 + i)
        p = i / FRAMES
        c = handle_center(p, RADIUS, dist)
        tl, tr = c + Vector((GRIP_HALF, 0, 0)), c - Vector((GRIP_HALF, 0, 0))
        per_frame.append({"quadro": 1 + i, "fase": round(p, 4),
                          "falta_esq_mm": round((palm(arm, "Left") - tl).length * 1000, 1),
                          "falta_dir_mm": round((palm(arm, "Right") - tr).length * 1000, 1),
                          "palma_esq_m": [round(v, 4) for v in palm(arm, "Left")]})
    gap_before = loop_gap(arm, action)
    blended = 0
    if gap_before > 0.001:
        blended = close_loop(action)
    gap_after = loop_gap(arm, action)
    hips_moves = max(float(np.ptp([k.co[1] for k in c.keyframe_points])) for c in action_fcurves(action)
                     if c.data_path == 'pose.bones["Hips"].location')
    worst = max(per_frame, key=lambda r: max(r["falta_esq_mm"], r["falta_dir_mm"]))
    report["clipe"] = {"nome": CLIP_NAME, "fps": FPS, "quadros": FRAMES, "duracao_s": FRAMES / FPS, "raio_m": RADIUS,
                       "eixo_altura_m": AXIS_Z, "distancia_manopla_m": round(dist, 4),
                       "falta_max_mm": max(worst["falta_esq_mm"], worst["falta_dir_mm"]), "pior_quadro": worst,
                       "quadros_fechados_5mm": sum(1 for r in per_frame if max(r["falta_esq_mm"], r["falta_dir_mm"]) <= 5),
                       "laco_antes_cm": round(gap_before * 100, 3), "laco_depois_cm": round(gap_after * 100, 3),
                       "quadros_misturados": blended, "hips_posicao_faixa_unidades": round(hips_moves, 5)}
    report["por_quadro"] = per_frame

    # Exporta só o esqueleto e o clipe.
    for a in [a for a in bpy.data.actions if a is not action]:
        bpy.data.actions.remove(a)
    for t in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(t)
    arm.animation_data.action = None
    track = arm.animation_data.nla_tracks.new()
    track.name = CLIP_NAME
    strip = track.strips.new(CLIP_NAME, 1, action)
    if getattr(action, "slots", None) and hasattr(strip, "action_slot"):
        strip.action_slot = action.slots[0]
    arm.data.pose_position = "POSE"
    for o in list(scene.objects):
        if o.type != "ARMATURE":
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    CLIP.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(CLIP), export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
                              export_animations=True, export_animation_mode="NLA_TRACKS", export_skins=True,
                              export_force_sampling=True, export_frame_range=False, export_optimize_animation_size=False)

    # Roda.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    wheel = build_wheel()
    knob_y = wheel["knob_y"]
    bpy.ops.object.select_all(action="DESELECT")
    wheel.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(WHEEL), export_format="GLB", use_selection=True, export_yup=True,
                              export_materials="EXPORT")
    # Conferência do sentido: roda no espaço do aldeão girada 180° em Z e, na fase p, girada 2πp no seu +Y do Blender.
    center = Vector((0, -(dist + knob_y), AXIS_Z))
    check = 0.0
    for p in (0, 0.125, 0.25, 0.6):
        m = Matrix.Translation(center) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Rotation(2 * math.pi * p, 4, "Y")
        check = max(check, (m @ Vector((0, -knob_y, RADIUS)) - handle_center(p, RADIUS, dist)).length)
    assert check < 1e-6, check

    clips = {CLIP_NAME: {
        "duracao_s": FRAMES / FPS, "quadros": FRAMES, "fps": FPS,
        "fase0": "alça A (face +Z da roda) no topo",
        "conta_na_fracao": COUNT_AT,
        "conta_significa": "a alça A passa embaixo (fim da empurrada para baixo)",
        "roda": {
            "arquivo": "roda.glb", "raio_alca_m": RADIUS,
            "angulo": "em volta do +Z local da roda: -360° × fase (fase 0 = alça A no topo)",
            "posicao_no_espaco_do_aldeao_m": [0.0, AXIS_Z, round(dist + knob_y, 4)],
            "giro_em_y_no_espaco_do_aldeao_graus": 180.0,
            "nota": "espaço do aldeão = glTF, aldeão olhando +Z; a roda fica na frente dele com a face +Z virada para ele",
        },
        "lado_oposto": "o segundo aldeão, do outro lado, segura a alça B: toca o mesmo clipe AO CONTRÁRIO com fase 0,5 − t "
                       "(visto do outro lado a roda gira no sentido oposto); com +0,5 para a frente as mãos só coincidem em 2 instantes",
        "falta_max_mm": report["clipe"]["falta_max_mm"],
    }}
    CLIPS_JSON.write_text(json.dumps(clips, indent=2, ensure_ascii=False) + "\n")
    report["roda"] = {"conferencia_sentido_m": check, "knob_y_m": knob_y, "centro_no_espaco_do_aldeao_blender_m": list(center)}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("RELATORIO " + json.dumps({k: v for k, v in report.items() if k != "por_quadro"}, ensure_ascii=False))


main()

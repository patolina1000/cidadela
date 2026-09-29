"""Clipes de operação "girar_roda" por IK no Blender, sem Meshy (headless): um clipe POR POSTO (contrato de
animação, 29/09/2026). Corpo aprovado (aldeao_corpo.glb, em metros). Roda provisória vertical, eixo horizontal na
altura do peito, uma alça em cada face, defasadas 180° (A na face +Z, no topo na fase 0; B na face −Z). Posto A na
frente da face +Z, posto B na frente da face −Z; em cada um o aldeão olha para a roda, pés fixos (Hips parado), e as
duas mãos seguram a manopla da alça do posto (uma de cada lado dela) por IK durante uma volta; o tronco acompanha um
pouco (inclinação, giro e flexão lateral leves).

Método:
1. Ossos com comprimento de verdade (só `length` muda; o repouso fica), IK nas mãos (cadeia de 3, ponta no centro
   da palma, sem esticar), polo no cotovelo com ângulo por lado (operacao_lib).
2. Varredura do raio no posto A (0,03 a 0,10 m): até que raio as mãos fecham.
3. Por posto: a cada quadro i (fase da roda p = i / 48) o alvo é a manopla da alça do posto vista pelo aldeão
   daquele posto (A: fase p; B: a alça B, que vista do outro lado está na fase 0,5 − p do círculo do aldeão),
   tronco e alvos por quadro, bake visual, laço conferido. O quadro do clipe é sempre a fase da RODA × 48.
4. Exporta pelo contrato (operacao_lib.export_clip): só esqueleto, metros, primeira chave em t = 0, 24 fps; um
   GLB por posto: clipes/girar_roda.glb (girar_roda-loop, posto A) e clipes/girar_roda_b.glb (girar_roda_b-loop).
5. Roda (roda.glb, pivô no eixo, frente +Z = face da alça A) e clipes.json com um bloco por posto.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/prova_operacao/girar_roda.py [-- <raio> <subpasta>]
  Sem argumentos: o raio 0,10 m nas saídas principais. Com argumentos (ex.: 0.06 variante_r06): saídas em
  assets/modelos/prova_operacao/<subpasta>/ e assets/previews/prova_operacao/<subpasta>/ (subpasta absoluta = fora
  do repositório, para testes).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aldeao_v2"))
from corpo_lib import ROOT, import_glb  # noqa: E402
from rig_lib import action_fcurves, close_loop, loop_gap  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from operacao_lib import (CHAIN, CLIP_FPS, calibrate_poles, export_clip, evaluate, gltf_clip_times, fix_lengths, front_profile, grip_distance, handle_center,  # noqa: E402
                          palm, setup_ik, spine_pose, set_targets)

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SRC = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
OUT_DIR = ROOT / "assets/modelos/prova_operacao" / (ARGS[1] if len(ARGS) > 1 else "")
WHEEL = OUT_DIR / "roda.glb"
CLIPS_JSON = OUT_DIR / "clipes.json"
REPORT = ROOT / "assets/previews/prova_operacao" / (ARGS[1] if len(ARGS) > 1 else "") / "girar_roda.json"
POSTOS = {  # alça do posto, fase do círculo do aldeão em função da fase da roda, giro do posto em relação à roda
    "A": {"clipe": "girar_roda-loop", "arquivo": "clipes/girar_roda.glb", "fase_do_alvo": lambda p: p, "giro": 180.0, "lado": 1},
    "B": {"clipe": "girar_roda_b-loop", "arquivo": "clipes/girar_roda_b.glb", "fase_do_alvo": lambda p: (0.5 - p) % 1.0, "giro": 0.0, "lado": -1},
}

# Escolhas técnicas da prova (não são números de design).
FPS, FRAMES = CLIP_FPS, 48  # 1 volta = 2 s
RADIUS = float(ARGS[0]) if ARGS else 0.10  # pedido: 0,10
AXIS_Z = 0.19  # peito: entre Spine01 (0,180) e Spine (0,209)
GRIP_HALF = 0.018  # cada mão de um lado da manopla (= operacao_lib.GRIP_HALF)
KNOB_R, KNOB_LEN, STEM_R, STEM_LEN = 0.012, 0.03, 0.006, 0.05
WHEEL_R, WHEEL_T, AXLE_R, AXLE_LEN = 0.125, 0.02, 0.012, 0.05
KNOB_Y = WHEEL_T / 2 + STEM_LEN + KNOB_LEN / 2  # centro da manopla, a partir do plano do meio da roda
HAND_CLEAR = 0.032  # manopla (12 mm) + espessura da mão (~20 mm) na frente do corpo
COUNT_AT = 0.5  # a volta conta quando a alça A passa embaixo (fim da empurrada)
SWEEP = (0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10)
WOOD, IRON = "#4A3B3A", "#66636B"


def hex_linear(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


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


def prepare(scene):
    """Cena nova com o corpo aprovado pronto para o IK."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.0
    objects = import_glb(SRC)
    arm = next(o for o in objects if o.type == "ARMATURE")
    body = next(o for o in objects if o.name == "aldeao_corpo")
    arm.animation_data_clear()
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    skeleton = fix_lengths(arm, body)
    prof = front_profile(body)
    arm.data.pose_position = "POSE"
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    targets, poles = setup_ik(arm)
    return scene, arm, skeleton, prof, targets, poles


def bake_posto(key, sweep_too=False) -> dict:
    posto = POSTOS[key]
    scene, arm, skeleton, prof, targets, poles = prepare(None)
    report = {"esqueleto": skeleton}
    mw = arm.matrix_world
    report["ombros_m"] = {s: [round(v, 4) for v in mw @ arm.data.bones[f"{s}Arm"].head_local] for s in ("Left", "Right")}
    report["alcance_ombro_palma_m"] = {s: round(sum(skeleton["comprimentos_m"][f"{s}{b}"] for b in CHAIN), 4) for s in ("Left", "Right")}
    dist = grip_distance(prof, RADIUS, AXIS_Z, HAND_CLEAR)
    report["poles_graus"] = calibrate_poles(arm, targets, poles, RADIUS, dist, AXIS_Z)

    if sweep_too:
        phases16 = [i / 16 for i in range(16)]
        sweep = {}
        for r in SWEEP:
            d = grip_distance(prof, r, AXIS_Z, HAND_CLEAR)
            rows = evaluate(arm, targets, r, d, AXIS_Z, phases16)
            sweep[f"{r:.2f}"] = {"distancia_manopla_m": round(d, 4),
                                 "falta_max_mm": max(max(x["falta_esq_mm"], x["falta_dir_mm"]) for x in rows)}
        report["varredura_raio"] = sweep
        closes = [float(r) for r, v in sweep.items() if v["falta_max_mm"] <= 5.0]
        report["maior_raio_que_fecha_m"] = max(closes) if closes else None

    # Quadro i = fase da roda i / 48; o alvo é a manopla da alça do posto no círculo visto pelo aldeão do posto.
    arm.animation_data_create()
    for i in range(FRAMES + 1):
        q = posto["fase_do_alvo"]((i % FRAMES) / FRAMES)
        scene.frame_set(i)
        spine_pose(arm, q)
        for name in ("Spine02", "Spine01"):
            arm.pose.bones[name].keyframe_insert("rotation_quaternion", frame=i)
        set_targets(targets, q, RADIUS, dist, AXIS_Z)
        for t in targets.values():
            t.keyframe_insert("location", frame=i)
    scene.frame_start, scene.frame_end = 0, FRAMES
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.nla.bake(frame_start=0, frame_end=FRAMES, only_selected=False, visual_keying=True, clear_constraints=True,
                     use_current_action=True, bake_types={"POSE"})
    bpy.ops.object.mode_set(mode="OBJECT")
    action = arm.animation_data.action
    action.name = posto["clipe"]
    per_frame = []
    for i in range(FRAMES):
        scene.frame_set(i)
        p = i / FRAMES
        c = handle_center(posto["fase_do_alvo"](p), RADIUS, dist, AXIS_Z)
        tl, tr = c + Vector((GRIP_HALF, 0, 0)), c - Vector((GRIP_HALF, 0, 0))
        per_frame.append({"quadro": i, "fase_da_roda": round(p, 4),
                          "falta_esq_mm": round((palm(arm, "Left") - tl).length * 1000, 1),
                          "falta_dir_mm": round((palm(arm, "Right") - tr).length * 1000, 1)})
    gap_before = loop_gap(arm, action)
    blended = close_loop(action) if gap_before > 0.001 else 0
    gap_after = loop_gap(arm, action)
    hips_moves = max(float(np.ptp([k.co[1] for k in c.keyframe_points])) for c in action_fcurves(action)
                     if c.data_path == 'pose.bones["Hips"].location')
    worst = max(per_frame, key=lambda r: max(r["falta_esq_mm"], r["falta_dir_mm"]))
    report["clipe"] = {"nome": posto["clipe"], "arquivo": posto["arquivo"], "fps": FPS, "quadros": FRAMES, "duracao_s": FRAMES / FPS,
                       "raio_m": RADIUS, "eixo_altura_m": AXIS_Z, "distancia_manopla_m": round(dist, 4),
                       "falta_max_mm": max(worst["falta_esq_mm"], worst["falta_dir_mm"]), "pior_quadro": worst,
                       "quadros_fechados_5mm": sum(1 for r in per_frame if max(r["falta_esq_mm"], r["falta_dir_mm"]) <= 5),
                       "laco_antes_cm": round(gap_before * 100, 3), "laco_depois_cm": round(gap_after * 100, 3),
                       "quadros_misturados": blended, "hips_posicao_faixa_m": round(hips_moves, 6)}
    report["por_quadro"] = per_frame
    for a in [a for a in bpy.data.actions if a is not action]:
        bpy.data.actions.remove(a)
    report["exportacao"] = export_clip(arm, [action], OUT_DIR / posto["arquivo"])
    report["gltf"] = gltf_clip_times(OUT_DIR / posto["arquivo"])
    report["distancia"] = dist
    return report


def main() -> None:
    postos = {key: bake_posto(key, sweep_too=(key == "A")) for key in POSTOS}
    dist = postos["A"]["distancia"]

    # Roda.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    wheel = build_wheel()
    assert abs(wheel["knob_y"] - KNOB_Y) < 1e-9
    bpy.ops.object.select_all(action="DESELECT")
    wheel.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(WHEEL), export_format="GLB", use_selection=True, export_yup=True,
                              export_materials="EXPORT")
    # Conferência dos postos: com o aldeão do posto na origem do seu espaço, a manopla física da alça do posto
    # (roda na origem, girada 2πp em volta do +Y do Blender = −360° × fase em volta do +Z do glTF) cai no alvo.
    check = 0.0
    for key, posto in POSTOS.items():
        d = dist + KNOB_Y
        # glTF z = lado × d vira Blender y = −lado × d; pés AXIS_Z abaixo do eixo.
        villager = Matrix.Translation(Vector((0, -posto["lado"] * d, -AXIS_Z))) @ Matrix.Rotation(math.radians(posto["giro"]), 4, "Z")
        knob_local = Vector((0, -KNOB_Y, RADIUS)) if key == "A" else Vector((0, KNOB_Y, -RADIUS))
        for p in (0, 0.125, 0.25, 0.6):
            knob = villager.inverted() @ (Matrix.Rotation(2 * math.pi * p, 4, "Y") @ knob_local)
            check = max(check, (knob - handle_center(posto["fase_do_alvo"](p), RADIUS, dist, AXIS_Z)).length)
    assert check < 1e-6, check

    clips = {}
    for key, posto in POSTOS.items():
        d = round(dist + KNOB_Y, 4)
        clips[posto["clipe"]] = {
            "arquivo": posto["arquivo"], "duracao_s": FRAMES / FPS, "quadros": FRAMES, "fps": FPS,
            "conta_na_fracao": COUNT_AT,
            "conta_significa": "a roda passa pela fase 0,5 (alça A embaixo, alça B no topo): fim da empurrada do posto A",
            "posto": {
                "nome": key, "alca": key,
                "posicao_m": [0.0, -AXIS_Z, posto["lado"] * d],
                "giro_em_y_graus": posto["giro"],
                "fase": f"quadro = fase_da_roda × {FRAMES} (t = fase_da_roda × {FRAMES / FPS:g} s; primeira chave em t = 0); "
                        "fase 0 = alça A no topo; sem inverter nem defasar",
                "referencia": "espaço da roda (glTF): pivô no eixo, eixo em +Z; posição = pés do aldeão; giro 0 = aldeão olhando +Z",
            },
            "peca": {"arquivo": "roda.glb", "raio_alca_m": RADIUS,
                     "giro": "−360° × fase_da_roda em volta do +Z local (fase 0 = alça A no topo)"},
            "falta_max_mm": postos[key]["clipe"]["falta_max_mm"],
        }
    CLIPS_JSON.write_text(json.dumps(clips, indent=2, ensure_ascii=False) + "\n")
    report = {k: v for k, v in postos["A"].items() if k != "distancia"}
    report["postos"] = {k: {x: v[x] for x in ("poles_graus", "clipe", "por_quadro", "gltf")} for k, v in postos.items()}
    report["roda"] = {"conferencia_postos_m": check, "knob_y_m": KNOB_Y,
                      "centro_no_espaco_do_aldeao_blender_m": [0.0, -(dist + KNOB_Y), AXIS_Z]}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("RELATORIO " + json.dumps({k: {x: v["clipe"][x] for x in ("nome", "falta_max_mm", "quadros_fechados_5mm", "laco_depois_cm", "hips_posicao_faixa_m")}
                                     | {"gltf": v["gltf"]} for k, v in postos.items()}, ensure_ascii=False))


main()

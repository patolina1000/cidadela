"""Medidas de ergonomia de um corpo com o rig da Meshy (Blender headless): o que uma máquina operada precisa
respeitar. Serve para o aldeão v2 e para a protagonista v2 (qualquer escala; usa a escala do mundo do armature).
Em pose de repouso, pés no chão (z = 0), personagem olhando -Y do Blender (+Z do glTF):
- alturas do quadril (Hips), do peito (meio entre Spine01 e Spine, onde a prova pôs o eixo) e dos ombros
  (cabeça dos ossos LeftArm/RightArm, a articulação);
- alcance do ombro à palma (braço + antebraço + mão até o centro da palma), por lado;
- quanto a barriga avança: frente do tronco (sem braços, faixa central) entre o quadril e os ombros, à frente da
  linha dos ombros e à frente do pivô;
- manivela na altura do peito (método da prova de operação, operacao_lib): para cada raio, a manopla fica no
  plano mais perto que ainda livra o corpo (perfil da frente + raio da manopla + espessura da mão) e as duas mãos
  a seguem por IK numa volta de 16 fases, com o tronco acompanhando pouco; "fecha" = palma a ≤ 5 mm do alvo.
  Dá a distância mínima da manopla aos ombros por raio e o maior raio em que as mãos fecham.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/prova_operacao/medir_ergonomia.py -- <corpo.glb> <saida.json>
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
sys.path.insert(0, str(HERE))
from corpo_lib import ROOT, import_glb  # noqa: E402
from operacao_lib import (CHAIN, KNOB_R, SIDES, TOLERANCE_MM, body_mesh, calibrate_poles, dominant, evaluate,  # noqa: E402
                          fix_lengths, front_profile, grip_distance, hand_points, reset_pose, setup_ik, world_scale)

SNUG_MM = 1.0  # "encosta": palma a no máximo 1 mm (a mão fica visualmente na manopla)
ALDEAO_REACH = 0.1225  # m: o polo do cotovelo da prova foi posto para este alcance; escala junto
STEP = 0.005


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    glb, out = Path(args[0]), Path(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objects = import_glb(glb)
    arm = next(o for o in objects if o.type == "ARMATURE")
    body = body_mesh(objects)
    arm.animation_data_clear()
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    mw = arm.matrix_world
    head = {b.name: mw @ b.head_local for b in arm.data.bones}
    pts = np.array([(body.matrix_world @ v.co)[:] for v in body.data.vertices])
    height = float(pts[:, 2].max() - pts[:, 2].min())

    skeleton = fix_lengths(arm, body)
    reach = {s: round(sum(skeleton["comprimentos_m"][f"{s}{b}"] for b in CHAIN), 4) for s in SIDES}
    hips_z = head["Hips"].z
    chest_z = (head["Spine01"].z + head["Spine"].z) / 2
    shoulder_z = (head["LeftArm"].z + head["RightArm"].z) / 2
    shoulder_y = (head["LeftArm"].y + head["RightArm"].y) / 2

    # Barriga: frente do tronco sem braços, faixa central, entre o quadril e os ombros.
    dom = dominant(body)
    arms = {f"{s}{b}" for s in SIDES for b in CHAIN}
    torso = np.array([p for p, d in zip(pts, dom) if d not in arms])
    band = torso[(torso[:, 2] >= hips_z) & (torso[:, 2] <= shoulder_z) & (np.abs(torso[:, 0]) < height * 0.125)]
    belly_y = float(band[:, 1].min())
    belly_z = float(band[band[:, 1].argmin(), 2])

    # Mão: espessura (menor lado da caixa) define a folga na frente do corpo e o afastamento das duas mãos.
    hand_min = min(float(np.ptp(hand_points(body, s), axis=0).min()) for s in SIDES)
    hand_clear = KNOB_R + 0.55 * hand_min
    grip_half = 0.48 * hand_min

    reset_pose(arm)
    prof = front_profile(body)
    targets, poles = setup_ik(arm, pole_scale=min(reach.values()) / ALDEAO_REACH)
    dist0 = grip_distance(prof, 0.10, chest_z, hand_clear)
    pole_angles = calibrate_poles(arm, targets, poles, 0.10, dist0, chest_z, grip_half)

    phases = [i / 16 for i in range(16)]
    sweep, max_ok, max_snug, closing, snug = {}, None, None, True, True
    r = 0.02
    while r <= min(reach.values()) + 1e-9:
        d = grip_distance(prof, r, chest_z, hand_clear)
        rows = evaluate(arm, targets, r, d, chest_z, phases, grip_half)
        worst = max(max(x["falta_esq_mm"], x["falta_dir_mm"]) for x in rows)
        sweep[f"{r:.3f}"] = {"distancia_manopla_aos_ombros_m": round(d + shoulder_y, 4), "falta_max_mm": worst}
        if closing and worst <= TOLERANCE_MM:
            max_ok = round(r, 3)
        else:
            closing = False
        if snug and worst <= SNUG_MM:
            max_snug = round(r, 3)
        else:
            snug = False
        r = round(r + STEP, 3)

    def at(radius):
        return sweep.get(f"{radius:.3f}", {}).get("distancia_manopla_aos_ombros_m")

    result = {
        "corpo": str(glb.relative_to(ROOT)) if glb.is_relative_to(ROOT) else str(glb),
        "unidade": "metros; pés em y = 0 (glTF), frente +Z do glTF",
        "altura_m": round(height, 4),
        "altura_quadril_m": round(hips_z, 4),
        "altura_peito_m": round(chest_z, 4),
        "altura_ombros_m": round(shoulder_z, 4),
        "alcance_ombro_palma_m": {"esquerdo": reach["Left"], "direito": reach["Right"], "menor": min(reach.values())},
        "barriga_avanca_m": {"a_frente_dos_ombros": round(shoulder_y - belly_y, 4), "a_frente_do_pivo": round(-belly_y, 4),
                             "na_altura_m": round(belly_z, 4)},
        "distancia_minima_alca_aos_ombros_m": {"no_raio_recomendado": at(max_snug) if max_snug else None, "raio_0_10": at(0.10),
                                               "regra": "manopla na frente dos ombros, livre do corpo em toda a altura do círculo; "
                                                        "cresce com o raio (ver manivela_por_raio)"},
        "raio_max_manivela_no_peito_m": {"recomendado": max_snug, "encosta_ate_1mm": max_snug, "fecha_ate_5mm": max_ok,
                                         "regra": "usar o recomendado: no limite de 5 mm a mão já fica alguns mm fora da manopla"},
        "manivela_por_raio": sweep,
        "nota": ("Medido em pose de repouso no Blender (tools/arte/prova_operacao/medir_ergonomia.py). Peito = meio entre os "
                 "ossos Spine01 e Spine; ombros = articulação dos ossos LeftArm/RightArm; palma = centro dos vértices da mão. "
                 "Manivela: eixo horizontal na altura do peito, círculo vertical na frente do corpo, as duas mãos na manopla "
                 f"(uma de cada lado, ±{grip_half * 1000:.0f} mm), pés fixos, tronco acompanhando pouco (inclinação 4° a 12°, giro ±8°, "
                 f"flexão ±4°); IK de 3 ossos sem esticar; manopla a {hand_clear * 1000:.0f} mm do corpo (raio da manopla + mão); "
                 f"'fecha' = palma a ≤ {TOLERANCE_MM:.0f} mm do alvo nas 16 fases; 'encosta' = ≤ {SNUG_MM:.0f} mm. A prova de operação "
                 "(eixo a 0,19 m, passo de 1 cm) deu 0,06 m."),
        "medicao": {"escala_mundo_armature": round(world_scale(arm), 6), "polo_graus": pole_angles,
                    "folga_mao_m": round(hand_clear, 4), "meia_pegada_m": round(grip_half, 4),
                    "repouso_intacto": {k: skeleton[k] for k in ("repouso_dif_rotacao_graus", "repouso_dif_posicao_mm")}},
    }
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print("ERGONOMIA " + json.dumps({k: v for k, v in result.items() if k not in ("manivela_por_raio", "nota")}, ensure_ascii=False))


main()

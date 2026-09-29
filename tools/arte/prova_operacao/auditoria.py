"""Passo 1 da prova de operação: auditoria do esqueleto do aldeão v2 (Blender headless, só leitura).
Lê assets/modelos/aldeao_v2/aldeao_corpo.glb (sem alterar) e o JSON cru do GLB; grava em
assets/previews/prova_operacao/: auditoria.json (medidas) e mao_esquerda.png, mao_direita.png (512 px, de perto,
material chapado #AEBFD3). O auditoria.md é escrito à mão a partir destes números.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/prova_operacao/auditoria.py
"""

import json
import math
import struct
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aldeao_v2"))
from corpo_lib import ROOT, SKIN, flat_material, import_glb, set_smooth, setup_scene, shoot  # noqa: E402
from rig_lib import action_fcurves  # noqa: E402

GLB = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
OUT = ROOT / "assets/previews/prova_operacao"
PAIRS = [("LeftUpLeg", "RightUpLeg"), ("LeftLeg", "RightLeg"), ("LeftFoot", "RightFoot"), ("LeftShoulder", "RightShoulder"),
         ("LeftArm", "RightArm"), ("LeftForeArm", "RightForeArm")]


def gltf_json(path: Path) -> dict:
    b = path.read_bytes()
    n = struct.unpack("<I", b[12:16])[0]
    return json.loads(b[20:20 + n])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    j = gltf_json(GLB)
    nodes = {n.get("name"): n for n in j["nodes"]}
    report = {"glb": str(GLB.relative_to(ROOT)), "gltf": {
        "no_armature": {k: nodes["Armature"].get(k) for k in ("translation", "rotation", "scale")},
        "juntas_com_escala_diferente_de_1": [n["name"] for n in j["nodes"] if "scale" in n and n.get("name") != "Armature"
                                             and max(abs(s - 1) for s in n["scale"]) > 1e-4],
        "canais_por_animacao": {a["name"]: sorted({c["target"]["path"] for c in a["channels"]}) for a in j["animations"]},
    }}

    setup_scene(512).view_settings.exposure = -1.2  # a luz do setup_scene estoura o branco-azulado de perto
    objects = import_glb(GLB)
    arm = next(o for o in objects if o.type == "ARMATURE")
    body = next(o for o in objects if o.name == "aldeao_corpo")
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    s = arm.scale[0]
    mw = arm.matrix_world
    bones = {}
    for b in arm.data.bones:
        children = [c for c in b.children]
        to_child = min(((c.head_local - b.head_local).length for c in children), default=None)
        y_axis = (b.matrix_local.to_3x3() @ Vector((0, 1, 0))).normalized()
        bones[b.name] = {
            "pai": b.parent.name if b.parent else None,
            "cabeca_mundo_m": [round(v, 4) for v in mw @ b.head_local],
            "comprimento_blender_unidades": round(b.length, 1),
            "comprimento_blender_m": round(b.length * s, 3),
            "distancia_ao_filho_unidades": round(to_child, 3) if to_child else None,
            "distancia_ao_filho_m": round(to_child * s, 4) if to_child else None,
            "eixo_y_no_armature": [round(v, 3) for v in y_axis],
        }
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for eb in arm.data.edit_bones:
        bones[eb.name]["rolagem_graus"] = round(math.degrees(eb.roll), 2)
    bpy.ops.object.mode_set(mode="OBJECT")
    report["escala_armature"] = s
    report["ossos"] = bones
    report["simetria"] = {f"{a}/{b}": {"filho_m": [bones[a]["distancia_ao_filho_m"], bones[b]["distancia_ao_filho_m"]],
                                         "rolagem": [bones[a]["rolagem_graus"], bones[b]["rolagem_graus"]]} for a, b in PAIRS}
    # Braço em repouso: ângulo abaixo da horizontal e para trás.
    for side in ("Left", "Right"):
        a = Vector(bones[f"{side}Arm"]["cabeca_mundo_m"])
        h = Vector(bones[f"{side}Hand"]["cabeca_mundo_m"])
        d = (h - a).normalized()
        report[f"braco_{side.lower()}_repouso"] = {"abaixo_da_horizontal_graus": round(math.degrees(math.asin(-d.z)), 1),
                                                   "para_tras_graus": round(math.degrees(math.atan2(d.y, abs(d.x))), 1),
                                                   "ombro_ao_punho_m": round((h - a).length, 4)}
    # Poses das ações: escala e posição por osso (há curvas de escala e posição em todos?).
    act_info = {}
    for act in bpy.data.actions:
        curves = action_fcurves(act)
        loc = [c for c in curves if c.data_path.endswith(".location")]
        scl = [c for c in curves if c.data_path.endswith(".scale")]
        moving_loc = sorted({c.data_path.split('"')[1] for c in loc if np.ptp([k.co[1] for k in c.keyframe_points]) > 1e-3})
        hips = [c for c in loc if '"Hips"' in c.data_path]
        act_info[act.name] = {"quadros": list(act.frame_range), "ossos_com_posicao_variando": moving_loc,
                              "hips_posicao_faixa_unidades": [round(float(np.ptp([k.co[1] for k in c.keyframe_points])), 2) for c in hips],
                              "escala_varia": any(np.ptp([k.co[1] for k in c.keyframe_points]) > 1e-4 for c in scl)}
    report["acoes"] = act_info

    # Mãos de perto.
    flat_material(objects, SKIN, matte=True)
    set_smooth(objects, True)
    names = [g.name for g in body.vertex_groups]
    for side, label, out_x in (("Left", "esquerda", 1), ("Right", "direita", -1)):
        pts = []
        for v in body.data.vertices:
            if v.groups:
                g = max(v.groups, key=lambda g: g.weight)
                if names[g.group] == f"{side}Hand":
                    pts.append(body.matrix_world @ v.co)
        p = np.array([[q.x, q.y, q.z] for q in pts])
        lo, hi = p.min(axis=0), p.max(axis=0)
        c = Vector(((lo + hi) / 2).tolist())
        size = float(max(hi - lo)) * 1.8
        direction = Vector((0.55 * out_x, -1, 0.15)).normalized()  # de frente e um pouco de fora
        shoot(bpy.context.scene, c + direction * 2, c, size, OUT / f"mao_{label}.png")
        report[f"mao_{label}"] = {"vertices": len(p), "caixa_mm": [round(float(v) * 1000, 1) for v in hi - lo]}
    (OUT / "auditoria.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("OK")


main()

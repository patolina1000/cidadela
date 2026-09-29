"""Passo 2 da prova de operação: normalização da escala do aldeão v2 numa CÓPIA (Blender headless).
1. Importa assets/modelos/aldeao_v2/aldeao_corpo.glb (não é alterado).
2. Aplica a escala 0,004 do Armature: multiplica os ossos (armature.data.transform) e as malhas filhas
   (mesh.transform) pela escala, zera a escala do objeto (1) e multiplica as curvas de posição dos ossos pela
   mesma escala (elas estão no espaço do osso, em unidades de 4 mm). Rotações não mudam.
3. Exporta como montar_rig.py (faixas NLA, esqueleto em POSE, sem otimização) em
   assets/modelos/prova_operacao/aldeao_normalizado.glb.
4. Reimporta os dois arquivos e, em idle-loop e run-loop, nos quadros de 0, 25, 50 e 75% do clipe, mede a maior
   distância entre vértices correspondentes das malhas deformadas (corpo, Olhos, Boca), em mm; também as
   cabeças dos ossos e o GetBoneGlobalRest equivalente (matriz de repouso no mundo) dos ossos de encaixe.
Saída: assets/previews/prova_operacao/normalizacao.json

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/prova_operacao/normalizar.py
"""

import json
import struct
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, kdtree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aldeao_v2"))
from corpo_lib import ROOT, import_glb  # noqa: E402
from rig_lib import action_fcurves, play  # noqa: E402

SRC = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
DST = ROOT / "assets/modelos/prova_operacao/aldeao_normalizado.glb"
REPORT = ROOT / "assets/previews/prova_operacao/normalizacao.json"
FRACTIONS = (0.0, 0.25, 0.5, 0.75)
SOCKET_BONES = ("Head", "Spine02")


def gltf_json(path: Path) -> dict:
    b = path.read_bytes()
    n = struct.unpack("<I", b[12:16])[0]
    return json.loads(b[20:20 + n])


def export_nla(armature, objects, path: Path) -> None:
    armature.data.pose_position = "POSE"  # o exportador amostra a pose ativa
    armature.animation_data_create()
    armature.animation_data.action = None
    for track in list(armature.animation_data.nla_tracks):
        armature.animation_data.nla_tracks.remove(track)
    for action in bpy.data.actions:
        track = armature.animation_data.nla_tracks.new()
        track.name = action.name
        strip = track.strips.new(action.name, int(action.frame_range[0]), action)
        if getattr(action, "slots", None) and hasattr(strip, "action_slot"):
            strip.action_slot = action.slots[0]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
                              export_animations=True, export_animation_mode="NLA_TRACKS", export_skins=True, export_materials="EXPORT",
                              export_force_sampling=True, export_frame_range=False, export_optimize_animation_size=False)


def normalize() -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objects = import_glb(SRC)
    arm = next(o for o in objects if o.type == "ARMATURE")
    meshes = [o for o in objects if o.type == "MESH"]
    s = arm.scale[0]
    assert all(abs(v - s) < 1e-9 for v in arm.scale), arm.scale
    rest_before = {b.name: (arm.matrix_world @ b.matrix_local).copy() for b in arm.data.bones}
    S = Matrix.Scale(s, 4)
    arm.data.transform(S)
    for m in meshes:
        assert m.parent == arm and m.matrix_parent_inverse == Matrix.Identity(4) and m.matrix_basis == Matrix.Identity(4), m.name
        m.data.transform(S)
    arm.scale = (1, 1, 1)
    scaled = 0
    for action in bpy.data.actions:
        for c in action_fcurves(action):
            if c.data_path.startswith("pose.bones") and c.data_path.endswith(".location"):
                for k in c.keyframe_points:
                    k.co[1] *= s
                    k.handle_left[1] *= s
                    k.handle_right[1] *= s
                c.update()
                scaled += 1
    bpy.context.view_layer.update()
    rest_after = {b.name: (arm.matrix_world @ b.matrix_local) for b in arm.data.bones}
    # Matriz de repouso no mundo: posição igual, rotação igual (a escala 0,004 sai da matriz).
    rest_diff = max((rest_before[n].to_translation() - rest_after[n].to_translation()).length for n in rest_before)
    rot_diff = max(2 * np.arccos(min(1.0, min(abs(rest_before[n].to_quaternion().dot(rest_after[n].to_quaternion())) for n in rest_before))), 0.0)
    export_nla(arm, [arm, *meshes], DST)
    return {"escala_aplicada": s, "curvas_de_posicao_escaladas": scaled,
            "repouso_mundo_dif_posicao_mm": round(rest_diff * 1000, 6), "repouso_mundo_dif_rotacao_graus": round(float(np.degrees(rot_diff)), 6)}


def deformed(objs) -> np.ndarray:
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in sorted((o for o in objs if o.type == "MESH"), key=lambda o: o.name.split(".")[0]):
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        out.append(np.array([(o.matrix_world @ v.co)[:] for v in me.vertices]))
        ev.to_mesh_clear()
    return out


def compare() -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    a = import_glb(SRC)
    acts_a = list(bpy.data.actions)
    b = import_glb(DST)
    acts_b = [x for x in bpy.data.actions if x not in acts_a]
    arm_a = next(o for o in a if o.type == "ARMATURE")
    arm_b = next(o for o in b if o.type == "ARMATURE")
    out = {"escala_armature": [arm_a.scale[0], arm_b.scale[0]],
           "gltf_no_armature_normalizado": {k: next(n for n in gltf_json(DST)["nodes"] if n.get("name") == "Armature").get(k) for k in ("scale", "translation")}}
    # Correspondência de vértices pela posição em repouso (o exportador pode reordenar).
    for arm in (arm_a, arm_b):
        arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    rest_a, rest_b = deformed(a), deformed(b)
    maps = []
    for pa, pb in zip(rest_a, rest_b):
        tree = kdtree.KDTree(len(pb))
        for i, p in enumerate(pb):
            tree.insert(p, i)
        tree.balance()
        idx, dist = zip(*[(tree.find(p)[1], tree.find(p)[2]) for p in pa])
        maps.append((np.array(idx), float(max(dist))))
    out["repouso_max_mm"] = round(max(m[1] for m in maps) * 1000, 4)
    out["vertices"] = [[len(x) for x in rest_a], [len(x) for x in rest_b]]
    # GetBoneGlobalRest no mundo (o que o jogo compensa nos encaixes).
    out["repouso_encaixes"] = {n: {"posicao_mm": round((arm_a.matrix_world @ arm_a.data.bones[n].matrix_local).to_translation().__sub__(
        (arm_b.matrix_world @ arm_b.data.bones[n].matrix_local).to_translation()).length * 1000, 5)} for n in SOCKET_BONES}
    for arm in (arm_a, arm_b):
        arm.data.pose_position = "POSE"
    clips = {}
    scene = bpy.context.scene
    for name in ("idle-loop", "run-loop"):
        act_a = next(x for x in acts_a if x.name.startswith(name))
        act_b = next(x for x in acts_b if x.name.startswith(name))
        play(arm_a, act_a)
        play(arm_b, act_b)
        start, end = act_a.frame_range
        rows = {}
        for f in FRACTIONS:
            frame = int(round(start + f * (end - start)))
            scene.frame_set(frame)
            da, db = deformed(a), deformed(b)
            vmax = max(float(np.linalg.norm(x - y[m[0]], axis=1).max()) for x, y, m in zip(da, db, maps))
            bmax = max((arm_a.matrix_world @ arm_a.pose.bones[n].head - arm_b.matrix_world @ arm_b.pose.bones[n].head).length
                       for n in arm_a.pose.bones.keys())
            rows[f"{int(f * 100)}%"] = {"quadro": frame, "vertices_max_mm": round(vmax * 1000, 4), "ossos_max_mm": round(bmax * 1000, 4)}
        clips[name] = rows
    out["clipes"] = clips
    out["maior_diferenca_mm"] = max(r["vertices_max_mm"] for c in clips.values() for r in c.values())
    return out


def main() -> None:
    report = {"normalizacao": normalize()}
    report["comparacao"] = compare()
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("RELATORIO " + json.dumps(report, ensure_ascii=False))


main()

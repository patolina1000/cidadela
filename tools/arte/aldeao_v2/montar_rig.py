"""Passo 6: monta o corpo limpo aprovado com o rig e os clipes da Meshy (Blender headless).

A Meshy não aceitou o GLB limpo ("Pose estimation failed"), então o rig foi feito sobre a tarefa original dela
(corpo_so_frente_1) e os pesos são transferidos para a malha limpa pela superfície mais próxima.
1. Importa animacoes.glb (armature + malha crua com pesos + ações Idle e Male_Head_Down_Charge).
2. Leva o conjunto para a escala do jogo: 0,40 m, pés em z = 0, pivô entre os pés (a mesma conta da limpeza),
   mexendo só no objeto armature (as curvas de posição ficam intactas).
3. Importa aldeao_corpo.glb (limpo), transfere os grupos de vértices da malha crua, prende ao armature.
4. Renomeia as ações: Idle -> idle-loop, Male_Head_Down_Charge -> run-loop (o Godot tira o sufixo e importa
   em loop). Confere se o fim volta ao começo.
5. Mede a passada do run (m/s: velocidade com que o pé de apoio recua, mediana; método do v1).
6. rosto.json: ossoCabeca, ossoPeito, passadaRun. Exporta assets/modelos/aldeao_v2/aldeao_corpo.glb com o rig
   e os dois clipes (sem os retalhos do rosto ainda) e reimporta para conferir.
7. Exporta NORMALIZADO (decisão de 29/09/2026): antes de exportar, a escala do objeto armature vai para os ossos,
   a malha e as curvas de posição (rig_lib.apply_armature_scale); o nó Armature sai com escala 1, em metros.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/montar_rig.py [-- <saida.glb>]
  Com <saida.glb> (prova ou teste): grava lá, com o relatório ao lado, e não mexe no rosto.json.
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpo_lib import ROOT, ROSTO, import_glb, mesh_points, triangle_count  # noqa: E402
from rig_lib import (apply_armature_scale, close_loop, loop_gap, measure_stride, normalize_rig, remove_root_motion,  # noqa: E402
                     rest_points, transfer_weights)

RIG_DIR = ROOT / "assets/conceitos/aldeao_v2/meshy/rig"
CLEAN = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo_limpo.glb"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(ARGS[0]) if ARGS else ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
ANIM_SOURCE = RIG_DIR / "extras_14_243_252.glb"  # escolha de 29/09/2026: Idle_3 e Run_02
CLIPS = {"Idle_3": "idle-loop", "Run_02": "run-loop"}
HEAD_BONE, CHEST_BONE = "Head", "Spine02"


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    objs = import_glb(ANIM_SOURCE)
    armature = next(o for o in objs if o.type == "ARMATURE")
    raw = next(o for o in objs if o.type == "MESH")
    for a in bpy.data.actions:
        a.use_fake_user = True
    low, high = normalize_rig(armature, raw)
    report = {"malha_crua": {"triangulos": triangle_count([raw]), "altura_m": float(high[2] - low[2]), "pes_z": float(low[2])}}

    before = set(bpy.data.actions)
    clean_objs = import_glb(CLEAN)
    clean = next(o for o in clean_objs if o.type == "MESH")
    for o in clean_objs:  # o arquivo limpo não deve trazer rig; se trouxer, sai tudo menos a malha
        if o is not clean:
            bpy.data.objects.remove(o)
    for a in [a for a in bpy.data.actions if a not in before]:
        bpy.data.actions.remove(a)
    clean.modifiers.clear()
    clean.vertex_groups.clear()
    clean.parent = None
    clean.name = clean.data.name = "aldeao_corpo"
    cpts = rest_points(clean)
    report["malha_limpa"] = {"triangulos": triangle_count([clean]), "altura_m": float(cpts[:, 2].max() - cpts[:, 2].min()),
                             "desvio_caixa_mm": [round(float(x) * 1000, 1) for x in (cpts.min(axis=0) - low).tolist() + (cpts.max(axis=0) - high).tolist()]}
    report["vertices_sem_peso_corrigidos"] = transfer_weights(raw, clean, armature)
    bpy.data.objects.remove(raw)

    clips = {}
    root_speed = None
    for action in list(bpy.data.actions):
        if action.name in CLIPS:
            if CLIPS[action.name] == "run-loop":
                root_speed = remove_root_motion(armature, action)
            gap_before = loop_gap(armature, action)
            tail = close_loop(action)
            gap = loop_gap(armature, action)
            action.name = CLIPS[action.name]
            fps = scene.render.fps / scene.render.fps_base
            clips[action.name] = {"quadros": [int(f) for f in action.frame_range], "duracao_s": round((action.frame_range[1] - action.frame_range[0]) / fps, 3),
                                  "laco_antes_m": round(gap_before, 4), "laco_depois_m": round(gap, 4), "quadros_misturados": tail}
        else:
            bpy.data.actions.remove(action)
    stride_feet = measure_stride(armature, bpy.data.actions["run-loop"])
    clips["run-loop"]["velocidade_raiz_m_s"] = round(root_speed or 0.0, 3)
    clips["run-loop"]["passada_pelos_pes_m_s"] = round(stride_feet, 3) if not np.isnan(stride_feet) else None
    # Depois de tirar o avanço da raiz, a velocidade em que os pés não deslizam é a medida pelos pés no clipe
    # no lugar (o avanço original da investida incluía escorregão: 0,785 contra 0,502 m/s).
    stride = stride_feet if not np.isnan(stride_feet) else root_speed
    clips["run-loop"]["passada_m_s"] = round(stride, 3)
    report["clipes"] = clips
    armature.animation_data.action = None
    armature.data.pose_position = "POSE"  # o exportador amostra a pose ativa: em REST sairia tudo parado
    scene.frame_set(0)

    bones = {b.name for b in armature.data.bones}
    assert HEAD_BONE in bones and CHEST_BONE in bones, bones
    rosto = json.loads((ROSTO / "rosto.json").read_text())
    rosto["ossoCabeca"] = HEAD_BONE
    rosto["ossoPeito"] = CHEST_BONE
    rosto["passadaRun"] = round(stride, 3)
    if not ARGS:
        (ROSTO / "rosto.json").write_text(json.dumps(rosto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["normalizacao"] = apply_armature_scale(armature, [clean])  # exporta sempre em metros

    # Cada clipe numa faixa da NLA (o exportador em modo ACTIONS não amostrava as ações com slot no Blender 5.1:
    # saíam só 2 quadros por canal). Sem otimização de tamanho, para manter todos os quadros.
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
    armature.select_set(True)
    clean.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
                              export_animations=True, export_animation_mode="NLA_TRACKS", export_skins=True, export_materials="EXPORT",
                              export_force_sampling=True, export_frame_range=False, export_optimize_animation_size=False)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_glb(OUT)
    check = {"objetos": [(o.type, o.name) for o in objs], "animacoes": [a.name for a in bpy.data.actions],
             "triangulos": triangle_count(objs), "materiais": [m.name for m in bpy.data.materials]}
    pts = mesh_points(objs)
    check["altura_m"] = float(pts[:, 2].max() - pts[:, 2].min())
    check["pes_z"] = float(pts[:, 2].min())
    report["conferencia"] = check
    (OUT.with_name("aldeao_corpo_rig.json")).write_text(json.dumps(report, indent=2) + "\n")
    print("RELATORIO " + json.dumps(report))


main()

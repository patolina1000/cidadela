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

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/montar_rig.py
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpo_lib import HEIGHT_M, ROOT, ROSTO, import_glb, mesh_points, triangle_count  # noqa: E402

RIG_DIR = ROOT / "assets/conceitos/aldeao_v2/meshy/rig"
CLEAN = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo_limpo.glb"
OUT = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
CLIPS = {"Idle": "idle-loop", "Male_Head_Down_Charge": "run-loop"}
HEAD_BONE, CHEST_BONE = "Head", "Spine02"
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


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    objs = import_glb(RIG_DIR / "animacoes.glb")
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
            gap = loop_gap(armature, action)
            action.name = CLIPS[action.name]
            fps = scene.render.fps / scene.render.fps_base
            clips[action.name] = {"quadros": [int(f) for f in action.frame_range], "duracao_s": round((action.frame_range[1] - action.frame_range[0]) / fps, 3), "diferenca_fim_inicio_m": round(gap, 4)}
        else:
            bpy.data.actions.remove(action)
    stride_feet = measure_stride(armature, bpy.data.actions["run-loop"])
    clips["run-loop"]["velocidade_raiz_m_s"] = round(root_speed, 3)
    clips["run-loop"]["passada_pelos_pes_m_s"] = round(stride_feet, 3) if not np.isnan(stride_feet) else None
    stride = root_speed  # a velocidade em que os pés não deslizam é a do avanço original da raiz
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
    (ROSTO / "rosto.json").write_text(json.dumps(rosto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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

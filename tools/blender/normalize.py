"""Padroniza um asset baixado da Meshy para o jogo (Blender em modo headless).

- escala do jogo (tools/assets.json, altura_m; 1 célula = 1 m);
- pivô no centro da base;
- frente virada para +Z do glTF (-Y no Blender), a frente de modelo do Godot;
- personagens: clipes renomeados para idle, walk, attack, work;
- texturas reduzidas para 512 px (GDD, seção 17);
- cristal_emissivo: as faces do cristal ganham o material separado "Cristal", com
  uma textura de emissão que só acende os pixels do cristal.

Uso:
  Blender -b --factory-startup --python tools/blender/normalize.py -- <nome>
"""

import json
import math
import re
import struct
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
TEXTURE_SIZE = 512
FOOTPRINT = 0.9  # base máxima de construções e recursos, para caber em 1 célula com folga
CRYSTAL_MATERIAL = "Cristal"
CRYSTAL_EMISSION_STRENGTH = 3.0
STRIDE_BONES = ("LeftToeBase", "RightToeBase")
BLEED = 3  # px além da borda das ilhas de UV pintados no rosto apagado
BLEED_PX = 8  # px de sangria em volta das ilhas de UV da textura da pele
AO_RAYS, AO_REACH = 48, 0.08  # oclusão: raios por vértice e alcance (fração da altura do modelo)
# Linha do cabelo (fração da altura da cabeça acima da base): na testa, na nuca, e a largura da borda.
HAIRLINE_FRONT, HAIRLINE_BACK, HAIRLINE_SOFT = 0.70, 0.12, 0.08
RIGID_MARGIN, RIGID_FADE = 1.25, 1.6  # pele rígida até 1,25x o meio-tamanho do plano; some até 1,6x
LOCOMOTION_CLIPS = ("run",)  # clipes com passada medida para protagonista.json
LEAN_TOLERANCE = 0.5  # graus
# Laço dos movimentos por texto: ossos comparados, margem ignorada nas pontas e duração do ciclo.
LOOP_BONES = ("LeftFoot", "RightFoot", "LeftHand", "RightHand", "Head")
LOOP_EDGE = 12  # quadros: o começo e o fim do clipe gerado costumam ter arrancada e parada
LOOP_MIN_FRAMES = 20
LOOP_MAX_FRAMES = 60
LEAN_MAX_PASSES = 6  # clipes com passada medida para protagonista.json
IDLE_KEY_STEP = 3  # quadros entre as chaves do idle feito à mão
MATTE_ROUGHNESS = 0.8  # fosco, como textura pintada à mão
# O cristal fica no peito: faixa de altura (fração da altura total) e perto do eixo central.
CHEST_BAND = (0.50, 0.85)
CHEST_HALF_WIDTH = 0.15  # fração da altura
CRYSTAL_FACE_FRACTION = 0.10  # fração mínima de pixels de cristal para a face entrar no material


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path: Path) -> list:
    # Sem a Icosphere que o importador cria para desenhar os ossos: ela entraria nas medidas.
    bpy.ops.import_scene.gltf(filepath=str(path), disable_bone_shape=True)
    return list(bpy.context.selected_objects)


def meshes() -> list:
    return [o for o in bpy.data.objects if o.type == "MESH"]


def world_bounds() -> tuple[Vector, Vector]:
    """Caixa do modelo como é desenhado (malha deformada pelo esqueleto em pose de repouso)."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in meshes():
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        coords = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", coords)
        coords = coords.reshape(-1, 3)
        matrix = np.array(obj.matrix_world)
        points.append(coords @ matrix[:3, :3].T + matrix[:3, 3])
        evaluated.to_mesh_clear()
    allpoints = np.concatenate(points)
    return Vector(allpoints.min(axis=0)), Vector(allpoints.max(axis=0))


def add_root(name: str) -> bpy.types.Object:
    """Um nó raiz com o nome do asset segura escala e pivô sem mexer nas animações."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    for obj in list(bpy.data.objects):
        if obj is not root and obj.parent is None:
            obj.parent = root
    return root


def fit(root: bpy.types.Object, asset: dict) -> None:
    low, high = world_bounds()
    size = high - low
    scale = asset["altura_m"] / size.z
    if asset["tipo"] != "personagem":
        scale = min(scale, FOOTPRINT / max(size.x, size.y))
    root.scale = (scale, scale, scale)
    center = (low + high) / 2
    root.location = (-center.x * scale, -center.y * scale, -low.z * scale)
    bpy.context.view_layer.update()
    low, high = world_bounds()
    print(f"  tamanho final: {high.x - low.x:.2f} x {high.y - low.y:.2f} x {high.z - low.z:.2f} m")


def import_extra_clips(raw: Path) -> None:
    """Traz os clipes de animacoes_extra.glb (mesmo rig) e descarta o resto do arquivo."""
    before_objects, before_actions = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(raw / "animacoes_extra.glb"), disable_bone_shape=True)
    for obj in [o for o in bpy.data.objects if o not in before_objects]:
        bpy.data.objects.remove(obj)
    clips = json.loads((raw / "animacoes_extra.json").read_text())
    for action in [a for a in bpy.data.actions if a not in before_actions]:
        ours = clips.get(action.name)
        if ours is None:
            bpy.data.actions.remove(action)
            continue
        if ours in bpy.data.actions:
            bpy.data.actions.remove(bpy.data.actions[ours])
        print(f"  clipe {action.name} -> {ours} (extra)")
        action.name = ours
        action.use_fake_user = True


def import_motion_clip(raw: Path, clip: str) -> None:
    """Traz um movimento da Text to Motion como <clip> num laço no lugar.

    O movimento gerado anda para a frente e não fecha em laço. Procura dois instantes com a mesma
    pose (pés, mãos e cabeça em relação ao quadril) separados por um a três ciclos, corta esse trecho
    e distribui em linha reta a diferença entre o fim e o começo em cada canal. Isso fecha o laço e
    tira o avanço do quadril (fica no lugar).
    """
    before_objects, before_actions = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(raw / f"movimento_{clip}.glb"), disable_bone_shape=True)
    imported = [o for o in bpy.data.objects if o not in before_objects]
    source_armature = next(o for o in imported if o.type == "ARMATURE")
    source = source_armature.animation_data.action
    start, end = source.frame_range
    scene = bpy.context.scene

    def pose_at(time: float) -> list:
        set_time(scene, time)
        hips = source_armature.pose.bones["Hips"].head
        return [source_armature.pose.bones[b].head - hips for b in LOOP_BONES] + [Vector((0, 0, hips.z))]

    times = [start + LOOP_EDGE + i for i in range(int(end - start - 2 * LOOP_EDGE) + 1)]
    poses = {t: pose_at(t) for t in times}
    best = None
    for t0 in times:
        for t1 in times:
            if not LOOP_MIN_FRAMES <= t1 - t0 <= LOOP_MAX_FRAMES:
                continue
            error = sum((a - b).length for a, b in zip(poses[t0], poses[t1]))
            if best is None or error < best[0]:
                best = (error, t0, t1)
    _, t0, t1 = best
    length = int(round(t1 - t0))

    looped = bpy.data.actions.new(clip)
    looped.use_fake_user = True
    slot = looped.slots.new("OBJECT", source_armature.name)
    layer = looped.layers.new("loop")
    bag = layer.strips.new(type="KEYFRAME").channelbag(slot, ensure=True)
    for curve in channelbags(source)[0].fcurves:
        values = [curve.evaluate(t0 + i) for i in range(length + 1)]
        target = values[0]
        if curve.data_path.endswith("rotation_quaternion"):
            # q e -q são a mesma rotação: fecha no sinal mais próximo do fim.
            quat = [c for c in channelbags(source)[0].fcurves if c.data_path == curve.data_path]
            q0 = [c.evaluate(t0) for c in sorted(quat, key=lambda c: c.array_index)]
            q1 = [c.evaluate(t1) for c in sorted(quat, key=lambda c: c.array_index)]
            if sum(a * b for a, b in zip(q0, q1)) < 0:
                target = -values[0]
        drift = values[-1] - target
        new = bag.fcurves.new(curve.data_path, index=curve.array_index, group_name=curve.group.name if curve.group else "")
        for i, value in enumerate(values):
            new.keyframe_points.insert(i, value - drift * i / length, options={"FAST"})
    for obj in imported:
        bpy.data.objects.remove(obj)
    for action in [a for a in bpy.data.actions if a not in before_actions and a is not looped]:
        bpy.data.actions.remove(action)
    if clip in bpy.data.actions and bpy.data.actions[clip] is not looped:
        bpy.data.actions.remove(bpy.data.actions[clip])
    looped.name = clip
    fps = scene.render.fps / scene.render.fps_base
    print(f"  {clip}: movimento por texto, laço de {length / fps:.2f} s (quadros {t0:.1f}-{t1:.1f}, "
          f"diferença de pose {best[0]:.1f})")


def discard_clips(names: list) -> None:
    for name in names:
        if name in bpy.data.actions:
            bpy.data.actions.remove(bpy.data.actions[name])
            print(f"  clipe {name} descartado")


def rename_clips(raw: Path) -> None:
    clips = {slug(k): v for k, v in json.loads((raw / "animacoes.json").read_text()).items()}
    for action in list(bpy.data.actions):
        match = next((ours for theirs, ours in clips.items() if theirs in slug(action.name)), None)
        if match is None:
            print(f"  aviso: clipe sem nome nosso: {action.name}")
            continue
        print(f"  clipe {action.name} -> {match}")
        action.name = match
        action.use_fake_user = True


def matte_materials() -> None:
    """Corrige os materiais da Meshy para o estilo pintado do jogo.

    - A Meshy liga a textura de cor na emissão: o modelo brilharia inteiro à noite.
    - Ela não informa metalicidade, e no glTF isso vale 1: no jogo, sem reflexos, o modelo fica preto.
    - O reflexo especular vem dobrado (fator 2).
    """
    for material in bpy.data.materials:
        for node in material.node_tree.nodes if material.node_tree else []:
            if node.type == "BSDF_PRINCIPLED":
                for name in ("Emission Color", "Metallic", "Roughness", "Specular Tint"):
                    for link in list(node.inputs[name].links):
                        material.node_tree.links.remove(link)
                node.inputs["Emission Color"].default_value = (0, 0, 0, 1)
                node.inputs["Emission Strength"].default_value = 0.0
                node.inputs["Metallic"].default_value = 0.0
                node.inputs["Roughness"].default_value = MATTE_ROUGHNESS
                node.inputs["Specular Tint"].default_value = (1, 1, 1, 1)


def use_rig_clip(raw: Path, clip: str, file: str) -> None:
    """Usa um clipe grátis que veio com o rig (mesmos ossos) como <clip>, trocando o que houver."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(raw / file), disable_bone_shape=True)
    imported = [o for o in bpy.data.objects if o not in before]
    source = next(o for o in imported if o.type == "ARMATURE")
    action = source.animation_data.action
    for obj in imported:
        bpy.data.objects.remove(obj)
    if clip in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[clip])
    action.name = clip
    action.use_fake_user = True
    print(f"  {clip}: clipe do rig ({file})")


def close_arms(clip: str, degrees: float) -> None:
    """Gira os ombros para baixo, em volta do eixo frente-trás, em todos os quadros do clipe."""
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    armature.data.pose_position = "POSE"
    armature.animation_data_create()
    action = bpy.data.actions[clip]
    armature.animation_data.action = action
    if action.slots:
        armature.animation_data.action_slot = action.slots[0]
    scene = bpy.context.scene
    # Eixo frente-trás do mundo, no espaço do esqueleto (onde vivem as matrizes dos ossos).
    axis = (armature.matrix_world.inverted().to_3x3() @ Vector((0, 1, 0))).normalized()
    for side in ("Left", "Right"):
        bone = armature.pose.bones[f"{side}Arm"]
        bone.rotation_mode = "QUATERNION"
        path = f'pose.bones["{bone.name}"].rotation_quaternion'
        curves = [c for bag in channelbags(action) for c in bag.fcurves if c.data_path == path]
        # As chaves podem estar em tempos fracionados (a caminhada do rig começa em 0,8):
        # regravar nos mesmos tempos, senão a curva alterna entre chave corrigida e original.
        times = sorted({k.co.x for c in curves for k in c.keyframe_points})
        original = {}
        for time in times:
            set_time(scene, time)
            original[time] = bone.matrix.copy()
        # O sinal que abaixa a mão depende do lado: testa na primeira chave.
        set_time(scene, times[0])
        best = None
        for sign in (1, -1):
            turned = rotate_about_head(original[times[0]], axis, sign * math.radians(degrees))
            tail_z = (armature.matrix_world @ (turned @ Vector((0, bone.bone.length, 0)))).z
            if best is None or tail_z < best[1]:
                best = (sign, tail_z)
        angle = best[0] * math.radians(degrees)
        corrected = {}
        for time in times:
            set_time(scene, time)
            bone.matrix = rotate_about_head(original[time], axis, angle)
            bpy.context.view_layer.update()
            corrected[time] = bone.rotation_quaternion.copy()
        for curve in curves:
            index = curve.array_index
            curve.keyframe_points.clear()
            for time in times:
                curve.keyframe_points.insert(time, corrected[time][index], options={"FAST"})
    armature.animation_data.action = None
    armature.data.pose_position = "REST"
    scene.frame_set(0)
    print(f"  braços fechados em {degrees:g}° no {clip}")


def breathing_idle(settings: dict) -> None:
    """Idle feito à mão: ereta, olhando para a frente, só respirando.

    Parte da T-pose de repouso. A malha da Meshy fica inclinada para a frente (tornozelos atrás do
    quadril): endireita coxa e canela, deixa os pés planos e sobe ou desce o quadril para os pés
    ficarem no chão. Baixa os braços ao lado do corpo com o cotovelo um pouco dobrado e levanta um pouco
    a cabeça. Num ciclo lento, o peito sobe (a coluna se abre um pouco para trás) e os ombros acompanham;
    a cabeça não balança. Todos os ossos têm chave, senão o Godot mantém a pose do clipe anterior nos
    ossos sem trilha (as pernas ficariam no walk).
    """
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    armature.data.pose_position = "POSE"
    armature.animation_data_create()
    if "idle" in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions["idle"])
    action = bpy.data.actions.new("idle")
    action.use_fake_user = True
    armature.animation_data.action = action
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    breaths = settings.get("respiracoes", 1)
    frames = round(settings["periodo_s"] * breaths * fps)
    bones = armature.pose.bones
    for bone in bones:
        bone.rotation_mode = "QUATERNION"
    side_axis, front_axis = Vector((1, 0, 0)), Vector((0, 1, 0))  # espaço do esqueleto: Z sobe, frente -Y

    def turn(name: str, axis: Vector, degrees: float) -> None:
        bone = bones[name]
        bone.matrix = rotate_about_head(bone.matrix.copy(), axis, math.radians(degrees))
        bpy.context.view_layer.update()

    def keep_rest_orientation(name: str, extra_degrees: float = 0.0) -> None:
        bone = bones[name]
        rest = bone.bone.matrix_local.to_3x3().to_4x4()
        bone.matrix = Matrix.Translation(bone.matrix.to_translation()) @ rest
        bpy.context.view_layer.update()
        if extra_degrees:
            turn(name, side_axis, extra_degrees)

    def plumb(upper: str, lower: str) -> None:
        """Gira <upper> em volta do eixo lateral até <lower> ficar logo abaixo dele (mesmo Y)."""
        top, bottom = bones[upper].head, bones[lower].head
        turn(upper, side_axis, -math.degrees(math.atan2(bottom.y - top.y, top.z - bottom.z)))

    def stand_up() -> None:
        for side in ("Left", "Right"):
            plumb(f"{side}UpLeg", f"{side}Leg")
            plumb(f"{side}Leg", f"{side}Foot")
            keep_rest_orientation(f"{side}Foot")

    # Quanto o quadril sobe ou desce para os pés voltarem ao chão depois de endireitar as pernas.
    ground = min(bones[f"{s}ToeBase"].head.z for s in ("Left", "Right"))
    stand_up()
    lift = ground - min(bones[f"{s}ToeBase"].head.z for s in ("Left", "Right"))

    for frame in range(0, frames + 1, IDLE_KEY_STEP):
        cycle = frame / frames  # 0..1 no clipe inteiro: o balanço do peso dá uma volta por clipe
        breath = (1 - math.cos(2 * math.pi * cycle * breaths)) / 2  # 0 = expirado, 1 = inspirado
        sway = math.sin(2 * math.pi * cycle)  # -1..1: tronco para um lado e para o outro
        for bone in bones:
            bone.location = (0, 0, 0)
            bone.rotation_quaternion = (1, 0, 0, 0)
        bpy.context.view_layer.update()
        hips = bones["Hips"]
        hips.matrix = Matrix.Translation((0, 0, lift)) @ hips.matrix
        bpy.context.view_layer.update()
        stand_up()
        # A coluna se abre para trás ao inspirar (+Y é trás), dividida pelos três ossos.
        for name in ("Spine02", "Spine01", "Spine"):
            turn(name, side_axis, -settings["peito_graus"] * breath / 3)
        # Peso do corpo: só o tronco balança (o quadril levaria os pés junto).
        turn("Spine02", front_axis, settings.get("balanco_graus", 0.0) * sway)
        # Esquerda fica em +X: girar em volta de +Y abaixa; a direita é o espelho.
        turn("LeftShoulder", front_axis, -settings["ombros_graus"] * breath)
        turn("RightShoulder", front_axis, settings["ombros_graus"] * breath)
        turn("LeftArm", front_axis, settings["bracos_graus"])
        turn("RightArm", front_axis, -settings["bracos_graus"])
        # Ao inspirar, os braços vão um pouco para a frente (-Y) e os pulsos relaxam.
        swing = settings.get("bracos_balanco_graus", 0.0) * breath
        turn("LeftArm", side_axis, -swing)
        turn("RightArm", side_axis, -swing)
        turn("LeftForeArm", side_axis, -settings["cotovelo_graus"])
        turn("RightForeArm", side_axis, -settings["cotovelo_graus"])
        wrist = settings.get("pulso_graus", 0.0) * breath
        turn("LeftHand", side_axis, -wrist)
        turn("RightHand", side_axis, -wrist)
        # Cabeça: levantada, inclina junto com o balanço e acena de leve ao soltar o ar.
        keep_rest_orientation("Head", -settings.get("cabeca_graus", 0.0)
                              + settings.get("cabeca_aceno_graus", 0.0) * (1 - breath))
        turn("Head", front_axis, settings.get("cabeca_inclina_graus", 0.0) * sway)
        for bone in bones:
            bone.keyframe_insert("rotation_quaternion", frame=frame)
            bone.keyframe_insert("location", frame=frame)
    armature.animation_data.action = None
    armature.data.pose_position = "REST"
    scene.frame_set(0)
    print(f"  idle: {breaths} respirações de {settings['periodo_s']:g} s feitas no Blender")


def trunk_lean(armature: bpy.types.Object) -> float:
    """Inclinação do tronco para a frente, em graus (quadril → pescoço contra a vertical; frente é -Y)."""
    up = (armature.matrix_world @ armature.pose.bones["neck"].head) - (armature.matrix_world @ armature.pose.bones["Hips"].head)
    return math.degrees(math.atan2(-up.y, up.z))


def set_trunk_lean(clip: str, target: float) -> None:
    """Desloca a inclinação média do tronco até <target>, preservando o balanço de cada passada.

    O trecho quadril → primeiro osso da coluna não gira, então uma passada não chega ao alvo:
    repete até ficar a menos de LEAN_TOLERANCE graus.
    """
    first = None
    for _ in range(LEAN_MAX_PASSES):
        before, after = trunk_lean_pass(clip, target)
        first = before if first is None else first
        if abs(after - target) < LEAN_TOLERANCE:
            break
    print(f"  tronco do {clip}: {first:.0f}° -> {after:.1f}° de inclinação média")


def trunk_lean_pass(clip: str, target: float) -> tuple[float, float]:
    """Uma passada da correção. A rotação é dividida pelos três ossos da coluna. Pescoço e ombros voltam
    à orientação original no mundo: a cabeça continua olhando para onde olhava, e os braços balançam na
    mesma altura (sem isso, ao endireitar o tronco, as mãos subiam até o rosto)."""
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    armature.data.pose_position = "POSE"
    armature.animation_data_create()
    action = bpy.data.actions[clip]
    armature.animation_data.action = action
    if action.slots:
        armature.animation_data.action_slot = action.slots[0]
    scene = bpy.context.scene
    spine = ("Spine02", "Spine01", "Spine")
    kept = ("neck", "LeftShoulder", "RightShoulder")
    names = spine + kept
    bones = armature.pose.bones
    paths = {f'pose.bones["{n}"].rotation_quaternion' for n in names}
    curves = [c for bag in channelbags(action) for c in bag.fcurves if c.data_path in paths]
    times = sorted({k.co.x for c in curves for k in c.keyframe_points})
    leans = []
    for time in times:
        set_time(scene, time)
        leans.append(trunk_lean(armature))
    before = sum(leans) / len(leans)
    # +X é o eixo lateral no espaço do esqueleto: girar em volta dele leva o topo para a frente (-Y).
    step = math.radians(target - before) / 3
    corrected = {name: {} for name in names}
    for time in times:
        set_time(scene, time)
        # Orientação no espaço do esqueleto (o objeto só tem escala, então equivale ao mundo).
        orientation = {name: bones[name].matrix.to_3x3().normalized() for name in kept}
        for name in spine:
            bones[name].rotation_mode = "QUATERNION"
            bones[name].matrix = rotate_about_head(bones[name].matrix.copy(), Vector((1, 0, 0)), step)
            bpy.context.view_layer.update()
        for name in kept:
            bone = bones[name]
            bone.rotation_mode = "QUATERNION"
            size = bone.matrix.to_scale()
            bone.matrix = (Matrix.Translation(bone.matrix.to_translation()) @ orientation[name].to_4x4()
                           @ Matrix.Diagonal((*size, 1)))
            bpy.context.view_layer.update()
        for name in names:
            corrected[name][time] = bones[name].rotation_quaternion.copy()
    for name in names:
        path = f'pose.bones["{name}"].rotation_quaternion'
        bag = channelbags(action)[0]
        for index in range(4):
            curve = next((c for c in bag.fcurves if c.data_path == path and c.array_index == index), None)
            if curve is None:
                curve = bag.fcurves.new(path, index=index, group_name=name)
            curve.keyframe_points.clear()
            for time in times:
                curve.keyframe_points.insert(time, corrected[name][time][index], options={"FAST"})
    after = []
    for time in times:
        set_time(scene, time)
        after.append(trunk_lean(armature))
    armature.animation_data.action = None
    armature.data.pose_position = "REST"
    scene.frame_set(0)
    return before, sum(after) / len(after)


def armature_object() -> bpy.types.Object:
    return next(o for o in bpy.data.objects if o.type == "ARMATURE")


def use_action(armature: bpy.types.Object, action: bpy.types.Action) -> None:
    armature.data.pose_position = "POSE"
    armature.animation_data_create()
    armature.animation_data.action = action
    if action.slots:
        armature.animation_data.action_slot = action.slots[0]


def copy_action(source: str, name: str) -> bpy.types.Action:
    if name in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[name])
    action = bpy.data.actions[source].copy()
    action.name = name
    action.use_fake_user = True
    return action


def key_times(action: bpy.types.Action, bones: tuple) -> list:
    """Tempos das chaves de rotação desses ossos (as ações podem ter chaves em tempos fracionados)."""
    paths = {f'pose.bones["{b}"].rotation_quaternion' for b in bones}
    return sorted({k.co.x for bag in channelbags(action) for c in bag.fcurves if c.data_path in paths
                   for k in c.keyframe_points})


def rewrite_curves(action: bpy.types.Action, values: dict, prop: str, size: int) -> None:
    """Regrava as curvas <prop> dos ossos com os valores {osso: {tempo: vetor}} (cria as que faltam)."""
    bag = channelbags(action)[0]
    for bone, per_time in values.items():
        path = f'pose.bones["{bone}"].{prop}'
        for index in range(size):
            curve = next((c for c in bag.fcurves if c.data_path == path and c.array_index == index), None)
            if curve is None:
                curve = bag.fcurves.new(path, index=index, group_name=bone)
            curve.keyframe_points.clear()
            for time, value in sorted(per_time.items()):
                curve.keyframe_points.insert(time, value[index], options={"FAST"})


def bone_tip(armature: bpy.types.Object, name: str) -> Vector:
    """Ponta útil do osso: a cabeça do filho (as caudas dos ossos da Meshy apontam para longe)."""
    bone = armature.pose.bones[name]
    return bone.children[0].head if bone.children else bone.tail


def aim(armature: bpy.types.Object, name: str, direction: Vector) -> None:
    """Gira o osso em volta da cabeça dele até apontar para <direction> (espaço do esqueleto)."""
    bone = armature.pose.bones[name]
    current = (bone_tip(armature, name) - bone.head).normalized()
    turn_by = current.rotation_difference(direction.normalized())
    head = bone.head.copy()
    bone.matrix = Matrix.Translation(head) @ turn_by.to_matrix().to_4x4() @ Matrix.Translation(-head) @ bone.matrix
    bpy.context.view_layer.update()


def reach(armature: bpy.types.Object, side: str, hand: Vector, pole: Vector) -> None:
    """IK de dois ossos: põe a mão em <hand>, com o cotovelo para o lado de <pole>."""
    arm, fore = f"{side}Arm", f"{side}ForeArm"
    shoulder = armature.pose.bones[arm].head.copy()
    upper = (bone_tip(armature, arm) - shoulder).length
    lower = (bone_tip(armature, fore) - armature.pose.bones[fore].head).length
    to_hand = hand - shoulder
    distance = min(to_hand.length, (upper + lower) * 0.999)
    axis = to_hand.normalized()
    # Lei dos cossenos: quanto o cotovelo sai da reta ombro-mão.
    along = (upper ** 2 - lower ** 2 + distance ** 2) / (2 * distance)
    out = math.sqrt(max(upper ** 2 - along ** 2, 0.0))
    bend = (pole - axis * pole.dot(axis)).normalized()
    elbow = shoulder + axis * along + bend * out
    aim(armature, arm, elbow - shoulder)
    aim(armature, fore, shoulder + axis * distance - armature.pose.bones[fore].head)


def carry_from_walk(settings: dict) -> None:
    """carry: a caminhada com os braços travados à frente da barriga, segurando a carga.

    As direções do braço e do antebraço (no espaço do tronco) vêm da configuração; elas seguem o
    giro do tronco em cada quadro, para os braços acompanharem o balanço da caminhada.
    """
    armature = armature_object()
    action = copy_action(settings.get("de", "walk"), "carry")
    use_action(armature, action)
    scene = bpy.context.scene
    bones = armature.pose.bones
    arm_bones = ("LeftArm", "LeftForeArm", "RightArm", "RightForeArm")
    rest_spine = bones["Spine"].bone.matrix_local.to_3x3()
    values = {b: {} for b in arm_bones}
    for time in key_times(action, arm_bones):
        set_time(scene, time)
        torso = bones["Spine"].matrix.to_3x3() @ rest_spine.inverted()
        for side, sign in (("Left", 1), ("Right", -1)):
            ux, uy, uz = settings["braco"]
            fx, fy, fz = settings["antebraco"]
            aim(armature, f"{side}Arm", torso @ Vector((sign * ux, uy, uz)))
            aim(armature, f"{side}ForeArm", torso @ Vector((sign * fx, fy, fz)))
        for b in arm_bones:
            values[b][time] = bones[b].rotation_quaternion.copy()
    rewrite_curves(action, values, "rotation_quaternion", 4)
    armature.animation_data.action = None
    print("  carry: caminhada com os braços segurando a carga")


def crank_work(settings: dict) -> None:
    """work: parado (a partir do idle), girando uma manivela com as duas mãos.

    As mãos seguem um círculo num plano vertical à frente do corpo (eixo da manivela na direção
    lateral); o tronco balança um pouco junto com a volta. O clipe tem o tamanho do idle, com um
    número inteiro de voltas, para fechar o laço.
    """
    armature = armature_object()
    action = copy_action("idle", "work")
    use_action(armature, action)
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    bones = armature.pose.bones
    start, end = action.frame_range
    turns = max(1, round((end - start) / fps / settings["volta_s"]))

    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    shoulders = (bones["LeftArm"].head + bones["RightArm"].head) / 2
    span = (bones["LeftArm"].head - bones["RightArm"].head).length
    front_y = world_to_armature(armature, Vector((0, world_bounds()[0].y, 0))).y
    armature.data.pose_position = "POSE"
    center = Vector((0, front_y, shoulders.z)) + Vector((0, -settings["frente"], -settings["abaixo"])) * span
    radius = settings["raio"] * span
    grip = settings["pegada"] * span / 2
    moved = ("LeftArm", "LeftForeArm", "RightArm", "RightForeArm", "Spine01")
    values = {b: {} for b in moved}
    for time in key_times(action, ("Hips",)):
        set_time(scene, time)
        angle = 2 * math.pi * turns * (time - start) / (end - start)
        lean = math.radians(settings["tronco_graus"]) * math.sin(angle)
        bones["Spine01"].matrix = rotate_about_head(bones["Spine01"].matrix.copy(), Vector((1, 0, 0)), -lean)
        bpy.context.view_layer.update()
        hand = center + Vector((0, math.cos(angle), math.sin(angle))) * radius
        for side, sign in (("Left", 1), ("Right", -1)):
            reach(armature, side, hand + Vector((sign * grip, 0, 0)), Vector((sign, 0.2, -1)))
        for b in moved:
            values[b][time] = bones[b].rotation_quaternion.copy()
    rewrite_curves(action, values, "rotation_quaternion", 4)
    armature.animation_data.action = None
    print(f"  work: manivela, {turns} voltas em {(end - start) / fps:.1f} s")


def world_to_armature(armature: bpy.types.Object, point: Vector) -> Vector:
    return armature.matrix_world.inverted() @ point


def ground_clip(clip: str) -> None:
    """Desce (ou sobe) o clipe inteiro até a malha encostar no chão da pose de repouso.

    O sono da biblioteca deita a uns centímetros do chão (como numa cama).
    """
    armature = armature_object()
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    ground = world_bounds()[0].z
    action = bpy.data.actions[clip]
    use_action(armature, action)
    scene = bpy.context.scene
    start, end = action.frame_range
    lowest = min(_min_z_at(scene, f) for f in range(int(start), int(end) + 1, 4))
    drop = (lowest - ground) / armature.matrix_world.to_scale().z
    hips = armature.pose.bones["Hips"]
    paths = {'pose.bones["Hips"].location'}
    times = sorted({k.co.x for bag in channelbags(action) for c in bag.fcurves if c.data_path in paths
                    for k in c.keyframe_points}) or [start]
    values = {"Hips": {}}
    for time in times:
        set_time(scene, time)
        hips.matrix = Matrix.Translation((0, 0, -drop)) @ hips.matrix
        bpy.context.view_layer.update()
        values["Hips"][time] = hips.location.copy()
    rewrite_curves(action, values, "location", 3)
    armature.animation_data.action = None
    armature.data.pose_position = "REST"
    print(f"  {clip}: apoiado no chão ({(lowest - ground) * 100:+.1f} cm na escala bruta)")


def _min_z_at(scene: bpy.types.Scene, frame: int) -> float:
    scene.frame_set(frame)
    return world_bounds()[0].z


FACE: dict = {}  # medida do rosto antes do fit (posição no mundo e largura), usada na exportação


def measure_face(settings: dict) -> None:
    """Onde fica a frente do rosto: na superfície da malha, entre a base da cabeça (osso "Head", na
    altura do pescoço) e o topo ("head_end"), na fração "altura_fracao" (o meio de olhos e boca).

    O marcador em si é gravado direto no glTF depois de exportar (add_face_node): preso a um osso no
    Blender, um objeto fica relativo à ponta do osso, e as pontas dos ossos da Meshy apontam para longe.
    """
    armature = armature_object()
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    base = armature.matrix_world @ armature.pose.bones["Head"].head
    top = armature.matrix_world @ armature.pose.bones["head_end"].head
    anchor = base.lerp(top, settings.get("altura_fracao", 0.35))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in meshes():
        mesh = obj.evaluated_get(depsgraph).to_mesh()
        points += [obj.matrix_world @ v.co for v in mesh.vertices]
        obj.evaluated_get(depsgraph).to_mesh_clear()
    low, high = world_bounds()
    band = (high.z - low.z) * settings.get("faixa", 0.04)
    near = [p for p in points if abs(p.z - anchor.z) < band]
    front = [p for p in near if abs(p.x - anchor.x) < band * 2]
    FACE["posicao"] = Vector((anchor.x, min(p.y for p in front) - band * 0.25, anchor.z))
    FACE["largura"] = (max(p.x for p in near) - min(p.x for p in near)) * settings.get("largura_fracao", 0.6)
    print(f"  Rosto: frente da cabeça a {settings.get('altura_fracao', 0.35):.0%} da altura da cabeça")


def erase_face(settings: dict) -> None:
    """Apaga o rosto pintado na textura (olhos, sobrancelhas, nariz, boca): o jogo projeta a expressão.

    A textura é picotada em ilhas de UV, então a pintura é feita pela posição 3D de cada pixel: dentro
    de um elipsoide em volta do rosto (centro atrás do marcador "Rosto"), o pixel recebe a cor média da
    pele da cabeça em volta do rosto; entre o elipsoide de dentro e o de fora a mistura é suave. Depois
    a geometria do rosto (olhos em órbitas, nariz, boca) é trocada por uma calota lisa (flatten_face).
    """
    armature = armature_object()
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    obj = max(meshes(), key=lambda o: len(o.data.polygons))
    image = base_color_image(obj.data.materials[0])
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, 4)

    base = armature.matrix_world @ armature.pose.bones["Head"].head
    top = armature.matrix_world @ armature.pose.bones["head_end"].head
    head_height = top.z - base.z
    head_width = FACE["largura"] / settings.get("largura_fracao", 0.6)
    center = FACE["posicao"] + Vector((0, 1, 0)) * head_width * settings.get("recuo", 0.3)
    center.z = base.z + head_height * settings.get("centro_altura", 0.38)
    radii = np.array([head_width * settings.get("raio_largura", 0.45),
                      head_width * settings.get("raio_profundidade", 0.45),
                      head_height * settings.get("raio_altura", 0.3)])
    inner = settings.get("miolo", 0.7)

    # Posição 3D (pose de repouso, mundo) de cada vértice, e os triângulos com as UVs.
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph).to_mesh()
    positions = np.array([(obj.matrix_world @ v.co)[:] for v in evaluated.vertices])
    obj.evaluated_get(depsgraph).to_mesh_clear()
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    ring_colors, targets = [], []
    c = np.array(center[:])
    covered = np.zeros((height, width), dtype=bool)
    for tri in mesh.loop_triangles:
        pix = (np.array([uv[l].uv[:] for l in tri.loops]) % 1.0) * [width, height]
        x0, y0 = np.floor(pix.min(axis=0)).astype(int)
        x1, y1 = np.ceil(pix.max(axis=0)).astype(int)
        covered[max(y0, 0):min(y1, height - 1) + 1, max(x0, 0):min(x1, width - 1) + 1] = True
    for tri in mesh.loop_triangles:
        corners3d = positions[list(tri.vertices)]
        distance = np.linalg.norm((corners3d.mean(axis=0) - c) / radii)
        if distance > 1.6:
            continue
        corners_uv = np.array([uv[l].uv[:] for l in tri.loops]) % 1.0
        pix = corners_uv * [width, height]
        x0, y0 = np.floor(pix.min(axis=0)).astype(int)
        x1, y1 = np.ceil(pix.max(axis=0)).astype(int)
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        points = np.stack([xs.ravel() + 0.5, ys.ravel() + 0.5], axis=1)
        # Coordenadas baricêntricas de cada pixel no triângulo de UV.
        a, b, cc = pix
        m = np.array([b - a, cc - a]).T
        if abs(np.linalg.det(m)) < 1e-9:
            continue
        lam = np.linalg.solve(m, (points - a).T).T
        inside = (lam[:, 0] >= -0.01) & (lam[:, 1] >= -0.01) & (lam.sum(axis=1) <= 1.01)
        if not inside.any():
            continue
        lam, points = lam[inside], points[inside].astype(int)
        points = np.clip(points, 0, [width - 1, height - 1])
        world = corners3d[0] + lam[:, :1] * (corners3d[1] - corners3d[0]) + lam[:, 1:] * (corners3d[2] - corners3d[0])
        d = np.linalg.norm((world - c) / radii, axis=1)
        ring = (d > 1.05) & (d < 1.5)
        if ring.any():
            ring_colors.append(pixels[points[ring, 1], points[ring, 0], :3])
        near = d < 1.0
        if near.any():
            targets.append((points[near], d[near]))
    skin = np.median(np.concatenate(ring_colors), axis=0)
    painted = 0
    for points, d in targets:
        weight = 1 - np.clip((d - inner) / (1 - inner), 0, 1)
        weight = weight * weight * (3 - 2 * weight)
        old = pixels[points[:, 1], points[:, 0], :3]
        pixels[points[:, 1], points[:, 0], :3] = old * (1 - weight[:, None]) + skin * weight[:, None]
        painted += len(points)
        if "uv_pele" not in FACE and (weight > 0.99).any():
            px = points[weight > 0.99][0]
            FACE["uv_pele"] = ((px[0] + 0.5) / width, (px[1] + 0.5) / height)
        # Borda da ilha: pixels vizinhos que nenhum triângulo usa também viram pele (a textura é
        # filtrada e esses pixels sangram para dentro das faces).
        full = points[weight > 0.99]
        for dx in range(-BLEED, BLEED + 1):
            for dy in range(-BLEED, BLEED + 1):
                xs = np.clip(full[:, 0] + dx, 0, width - 1)
                ys = np.clip(full[:, 1] + dy, 0, height - 1)
                free = ~covered[ys, xs]
                pixels[ys[free], xs[free], :3] = skin
    image.pixels.foreach_set(pixels.ravel())
    image.pack()
    print(f"  rosto apagado da textura: {painted} pixels pintados com a pele {np.round(skin * 255).astype(int)}")
    flatten_face(obj, positions, c, radii, inner, base, top)


def flatten_face(obj: bpy.types.Object, positions: np.ndarray, center: np.ndarray, radii: np.ndarray,
                 inner: float, base: Vector, top: Vector) -> None:
    """Troca a geometria do rosto (olhos em órbitas, nariz e boca em relevo) por uma calota lisa.

    As faces dentro do elipsoide do rosto saem. O buraco é triangulado de novo no plano da frente (borda
    como restrição e pontos em grade dentro); a profundidade de cada ponto novo é uma membrana presa na
    borda, estufada até a esfera ajustada à cabeça no meio, para continuar a curvatura. As faces novas
    usam a UV de um pixel de pele e ficam 100% no osso Head.
    """
    import bmesh
    mesh = obj.data
    to_world = np.array(obj.matrix_world)
    to_local = np.linalg.inv(to_world)
    d = np.linalg.norm((positions - center) / radii, axis=1)
    head = (positions[:, 2] > base.z + (top.z - base.z) * 0.15) & (d > 1.1)
    pts = positions[head]
    a = np.hstack([2 * pts, np.ones((len(pts), 1))])
    solution = np.linalg.lstsq(a, (pts ** 2).sum(axis=1), rcond=None)[0]
    sphere_center, radius = solution[:3], np.sqrt(solution[3] + (solution[:3] ** 2).sum())

    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    deform = bm.verts.layers.deform.active
    head_group = obj.vertex_groups["Head"].index
    old = bm.verts.layers.int.new("antigo")  # 1 nos vértices que já existiam
    for v in bm.verts:
        v[old] = 1
    doomed = [f for f in bm.faces if np.mean([d[v.index] for v in f.verts]) < 1.0]
    material = doomed[0].material_index if doomed else 0
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # Costuras de UV duplicam vértices: solda os da borda que estão na mesma posição.
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if any(e.is_boundary for e in v.link_edges)], dist=1e-6)

    # Maior laço de borda = o buraco do rosto (buracos pequenos que já existiam ficam).
    loops, seen = [], set()
    for edge in bm.edges:
        if not edge.is_boundary or edge in seen:
            continue
        loop, stack = [], [edge]
        while stack:
            e = stack.pop()
            if e in seen:
                continue
            seen.add(e)
            loop.append(e)
            for v in e.verts:
                stack.extend(x for x in v.link_edges if x.is_boundary and x not in seen)
        loops.append(loop)
    rim = max(loops, key=len)
    # Laço ordenado de vértices da borda.
    rim_set = set(rim)
    ordered = [rim[0].verts[0]]
    visited = {ordered[0]}
    came = None
    for _ in range(len(rim) + 1):  # borda que se toca num vértice não pode virar laço infinito
        v = ordered[-1]
        step = next((e for e in v.link_edges if e in rim_set and e is not came and e.other_vert(v) not in visited),
                    None)
        if step is None:
            break
        ordered.append(step.other_vert(v))
        visited.add(ordered[-1])
        came = step
    world_rim = np.array([(to_world @ np.append(v.co[:], 1.0))[:3] for v in ordered])
    # Triangulação no plano da frente (x, z do mundo): borda como restrição + pontos em grade dentro.
    from mathutils.geometry import delaunay_2d_cdt
    from mathutils import Vector as V
    xz = world_rim[:, [0, 2]]
    spacing = np.linalg.norm(np.diff(np.vstack([xz, xz[:1]]), axis=0), axis=1).mean()

    def inside(point: np.ndarray) -> bool:
        x, y = point
        crossings = 0
        for (x1, y1), (x2, y2) in zip(xz, np.roll(xz, -1, axis=0)):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                crossings += 1
        return crossings % 2 == 1

    low, high = xz.min(axis=0), xz.max(axis=0)
    grid = [np.array([x, z]) for x in np.arange(low[0], high[0], spacing) for z in np.arange(low[1], high[1], spacing)]
    grid = [g for g in grid if inside(g) and np.min(np.linalg.norm(xz - g, axis=1)) > spacing * 0.6]
    n_rim = len(xz)
    coords = [V((p[0], p[1])) for p in xz] + [V((g[0], g[1])) for g in grid]
    edges = [(i, (i + 1) % n_rim) for i in range(n_rim)]
    out_verts, _, out_faces, orig_verts, _, _ = delaunay_2d_cdt(coords, edges, [list(range(n_rim))], 1, 1e-9)
    # Profundidade (y do mundo): membrana com a borda presa, depois estufada até a esfera no meio.
    count = len(out_verts)
    source = [ov[0] if ov else -1 for ov in orig_verts]
    ys = np.zeros(count)
    is_rim = np.array([0 <= source[i] < n_rim for i in range(count)])
    for i in range(count):
        ys[i] = world_rim[source[i], 1] if is_rim[i] else world_rim[:, 1].mean()
    neighbors = [set() for _ in range(count)]
    for face in out_faces:
        for a_, b_ in zip(face, face[1:] + face[:1]):
            neighbors[a_].add(b_)
            neighbors[b_].add(a_)
    free = np.array([i for i in range(count) if not is_rim[i] and neighbors[i]])
    lists = [np.array(sorted(neighbors[i])) for i in free]
    for _ in range(400):
        ys[free] = [ys[n].mean() for n in lists]
    points2d = np.array([[p[0], p[1]] for p in out_verts])
    far = max((np.min(np.linalg.norm(xz - points2d[i], axis=1)) for i in range(count) if not is_rim[i]), default=1.0)
    new_positions = {}
    for i in range(count):
        if is_rim[i]:
            continue
        x, z = points2d[i]
        t = np.min(np.linalg.norm(xz - points2d[i], axis=1)) / far
        t = t * t * (3 - 2 * t)
        under = radius ** 2 - (x - sphere_center[0]) ** 2 - (z - sphere_center[2]) ** 2
        sphere_y = sphere_center[1] - np.sqrt(max(under, 0.0))  # frente é -Y
        new_positions[i] = np.array([x, ys[i] + (sphere_y - ys[i]) * t, z])
    verts_out = {}
    for i in range(count):
        if is_rim[i]:
            verts_out[i] = ordered[source[i]]
        else:
            vert = bm.verts.new(Vector((to_local @ np.append(new_positions[i], 1.0))[:3]))
            vert[deform][head_group] = 1.0
            verts_out[i] = vert
    interior = [verts_out[i] for i in range(count) if not is_rim[i]]
    patch = []
    for face in out_faces:
        try:
            f = bm.faces.new([verts_out[i] for i in face])
        except ValueError:
            continue
        patch.append(f)
    bm.normal_update()
    # Normais para fora (a frente é -Y no mundo).
    if patch and sum((to_world[:3, :3] @ np.array(f.normal[:]))[1] for f in patch) > 0:
        bmesh.ops.reverse_faces(bm, faces=patch)
    skin_uv = FACE.get("uv_pele")
    for f in patch:
        f.material_index = material
        f.smooth = True  # facetada, a grade da calota aparece em xadrez
        if skin_uv is not None:
            for loop in f.loops:
                loop[uv_layer].uv = skin_uv
    bm.verts.layers.int.remove(old)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    doomed = range(len(doomed))
    print(f"  rosto trocado por calota lisa: {len(doomed)} faces removidas, {len(interior)} vértices novos, "
          f"borda de {len(rim)} arestas")


def srgb_to_linear(hex_color: str) -> np.ndarray:
    c = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float64) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def finish_skin(settings: dict) -> None:
    """Acabamento do corpo-base: pele de cor única, sombreado liso, cabeça mais densa, couro cabeludo.

    - Solda os vértices duplicados nas costuras de UV (sem isso o sombreado liso quebra nas costuras).
    - Subdivide só a cabeça (uma vez, com arredondamento) e alisa o queixo e o rosto (Taubin), o que
      também tira a ponta que sobrava embaixo da boca.
    - Sombreado liso em tudo.
    - Pele: cor única com um degradê suave de altura, uma oclusão leve (raios) e o couro cabeludo na cor
      escura do cabelo, com borda suave na linha do cabelo; calculada por vértice e gravada numa textura
      nova com UV nova (bake_colors_to_texture).
    """
    import bmesh
    from mathutils.bvhtree import BVHTree
    armature = armature_object()
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    body = max(meshes(), key=lambda o: len(o.data.polygons))
    mesh = body.data
    to_world = body.matrix_world
    base = armature.matrix_world @ armature.pose.bones["Head"].head
    top = armature.matrix_world @ armature.pose.bones["head_end"].head
    head_h = top.z - base.z

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    head_edges = [e for e in bm.edges if all((to_world @ v.co).z > base.z for v in e.verts)]
    bmesh.ops.subdivide_edges(bm, edges=head_edges, cuts=1, use_grid_fill=True, smooth=1.0)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    # Rosto e queixo: Taubin (alisa sem encolher), mais forte no miolo.
    face_center = FACE["posicao"]
    radius = head_h * settings.get("alisar_raio", 0.45)
    region = [v for v in bm.verts if (to_world @ v.co - face_center).length < radius and (to_world @ v.co).z > base.z - head_h * 0.1]
    for step in range(settings.get("alisar_passos", 12) * 2):
        factor = 0.5 if step % 2 == 0 else -0.53
        moves = {}
        for v in region:
            ring = [e.other_vert(v).co for e in v.link_edges]
            if ring:
                w = 1 - (to_world @ v.co - face_center).length / radius
                moves[v] = v.co + (sum(ring, Vector()) / len(ring) - v.co) * factor * w
        for v, co in moves.items():
            v.co = co
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    if "sharp_edge" in mesh.attributes:
        mesh.attributes.remove(mesh.attributes["sharp_edge"])
    if "sharp_face" in mesh.attributes:
        mesh.attributes.remove(mesh.attributes["sharp_face"])

    # Cores dos vértices: degradê de altura, oclusão e couro cabeludo.
    skin = srgb_to_linear(settings["pele"])
    hair = srgb_to_linear(settings["cabelo"])
    world = np.array([(to_world @ v.co)[:] for v in mesh.vertices])
    normals = np.array([(to_world.to_3x3() @ v.normal).normalized()[:] for v in mesh.vertices])
    tree = BVHTree.FromPolygons([Vector(p) for p in world], [p.vertices[:] for p in mesh.polygons])
    low_z, high_z = world[:, 2].min(), world[:, 2].max()
    rng = np.random.default_rng(1)
    dirs = rng.normal(size=(AO_RAYS, 3))
    dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    reach = (high_z - low_z) * AO_REACH
    head_center = np.array([(base.x + top.x) / 2, FACE["posicao"].y + head_h * 0.5, base.z + head_h * 0.5])
    colors = np.zeros((len(world), 4))
    for i, (p, n) in enumerate(zip(world, normals)):
        hits = 0
        for d in dirs:
            if d @ n < 0:
                d = -d
            origin = Vector(p + n * 1e-4)
            if tree.ray_cast(origin, Vector(d), reach)[0] is not None:
                hits += 1
        ao = 1 - settings.get("oclusao", 0.35) * hits / AO_RAYS
        height = (p[2] - low_z) / (high_z - low_z)
        shade = 1 - settings.get("degrade", 0.12) * (1 - height)
        color = skin * shade * ao
        # Couro cabeludo: acima da linha do cabelo (alta na frente, baixa na nuca), fora das orelhas.
        rel = p - head_center
        front = -rel[1] / max(np.hypot(rel[0], rel[1]), 1e-9)  # 1 na frente, -1 atrás
        line = base.z + head_h * (HAIRLINE_BACK + (HAIRLINE_FRONT - HAIRLINE_BACK) * (front + 1) / 2)
        ear = abs(rel[0]) > head_h * 0.38 and p[2] < base.z + head_h * 0.62 and front > -0.6
        t = np.clip((p[2] - line) / (head_h * HAIRLINE_SOFT) + 0.5, 0, 1) if p[2] > base.z else 0.0
        t = 0.0 if ear else t * t * (3 - 2 * t)
        color = color * (1 - t) + hair * ao * t
        colors[i, :3] = color / skin  # o glTF multiplica COLOR_0 pela cor base (a pele)
        colors[i, 3] = 1

    # Suaviza as cores pelos vizinhos: tira o ruído da oclusão e o serrilhado da linha do cabelo.
    neighbors = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbors[a].append(b)
        neighbors[b].append(a)
    rgb = colors[:, :3].copy()
    for _ in range(settings.get("suavizar_cor", 6)):
        rgb = np.array([(rgb[i] + rgb[n].sum(axis=0)) / (1 + len(n)) if n else rgb[i]
                        for i, n in enumerate(neighbors)])
    bake_colors_to_texture(body, rgb * skin, settings.get("textura_px", 1024))
    print(f"  acabamento da pele: {len(mesh.polygons)} faces (cabeça subdividida), pele {settings['pele']}, "
          f"couro cabeludo {settings['cabelo']}, oclusão por {AO_RAYS} raios")


def bake_colors_to_texture(body: bpy.types.Object, colors: np.ndarray, size: int) -> None:
    """Grava as cores por vértice numa textura nova, com UV nova (projeção automática), e troca o
    material para usá-la. O Godot importa o glTF com a cor dos vértices desligada no material; a
    textura funciona em qualquer lugar."""
    mesh = body.data
    for layer in list(mesh.uv_layers):
        mesh.uv_layers.remove(layer)
    mesh.uv_layers.new(name="UVMap")
    bpy.ops.object.select_all(action="DESELECT")
    body.hide_set(False)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.01)
    bpy.ops.object.mode_set(mode="OBJECT")
    uv = mesh.uv_layers.active.data
    image = np.zeros((size, size, 3), dtype=np.float32)
    filled = np.zeros((size, size), dtype=bool)
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        pix = np.array([uv[l].uv[:] for l in tri.loops]) * size
        cols = colors[list(tri.vertices)]
        x0, y0 = np.floor(pix.min(axis=0)).astype(int)
        x1, y1 = np.ceil(pix.max(axis=0)).astype(int)
        xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1, size - 1) + 1), np.arange(max(y0, 0), min(y1, size - 1) + 1))
        points = np.stack([xs.ravel() + 0.5, ys.ravel() + 0.5], axis=1)
        a, b, c = pix
        m = np.array([b - a, c - a]).T
        if abs(np.linalg.det(m)) < 1e-12:
            continue
        lam = np.linalg.solve(m, (points - a).T).T
        inside = (lam[:, 0] >= -0.02) & (lam[:, 1] >= -0.02) & (lam.sum(axis=1) <= 1.02)
        if not inside.any():
            continue
        lam = np.clip(lam[inside], 0, 1)
        weights = np.stack([1 - lam.sum(axis=1), lam[:, 0], lam[:, 1]], axis=1).clip(0, 1)
        px = points[inside].astype(int)
        image[px[:, 1], px[:, 0]] = weights @ cols
        filled[px[:, 1], px[:, 0]] = True
    # Sangria: pixels vazios em volta das ilhas pegam a média dos vizinhos pintados, BLEED_PX vezes.
    for _ in range(BLEED_PX):
        acc = np.zeros_like(image)
        count = np.zeros(filled.shape, dtype=np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            shifted_fill = np.roll(filled, (dy, dx), axis=(0, 1))
            acc += np.roll(image, (dy, dx), axis=(0, 1)) * shifted_fill[..., None]
            count += shifted_fill
        grow = ~filled & (count > 0)
        image[grow] = acc[grow] / count[grow][:, None]
        filled |= grow
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[..., :3] = image
    texture = bpy.data.images.new(f"{body.name}_pele", size, size, float_buffer=False)
    texture.colorspace_settings.name = "Non-Color"
    texture.pixels.foreach_set(rgba.ravel())
    texture.colorspace_settings.name = "sRGB"
    # Os valores estão em linear: converte para sRGB antes de gravar (a imagem é 8 bits sRGB).
    srgb = np.where(image <= 0.0031308, image * 12.92, 1.055 * np.power(np.clip(image, 0, None), 1 / 2.4) - 0.055)
    rgba[..., :3] = np.clip(srgb, 0, 1)
    texture.pixels.foreach_set(rgba.ravel())
    texture.pack()
    material = mesh.materials[0]
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    for link in list(bsdf.inputs["Base Color"].links):
        links.remove(link)
    for node in [n for n in nodes if n.type in ("TEX_IMAGE", "VERTEX_COLOR", "MIX")]:
        nodes.remove(node)
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = texture
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
    for attribute in list(mesh.color_attributes):
        mesh.color_attributes.remove(attribute)


def rigid_skin(body: bpy.types.Object, center: tuple, half: tuple, neck_z: float) -> None:
    """A pele debaixo de um plano do rosto passa a seguir 100% o osso Head (o plano segue só ele; o
    queixo e as bochechas tinham peso do pescoço e entravam no plano na caminhada). Borda suave."""
    head = body.vertex_groups["Head"].index
    others = [g for g in body.vertex_groups if g.index != head]
    for v in body.data.vertices:
        world = body.matrix_world @ v.co
        d = max(abs(world.x - center[0]) / (half[0] * RIGID_MARGIN), abs(world.z - center[1]) / (half[1] * RIGID_MARGIN))
        if d >= RIGID_FADE or world.z < neck_z:
            continue  # longe do plano ou abaixo da base da cabeça (o pescoço continua dobrando)
        w = 1.0 if d <= 1 else 1 - (d - 1) / (RIGID_FADE - 1)
        for g in others:
            try:
                old = g.weight(v.index)
            except RuntimeError:
                continue
            g.add([v.index], old * (1 - w), "REPLACE")
        try:
            current = body.vertex_groups["Head"].weight(v.index)
        except RuntimeError:
            current = 0.0
        body.vertex_groups["Head"].add([v.index], current + (1 - current) * w, "REPLACE")


def add_face_planes(settings: dict, asset: dict) -> None:
    """Rosto em planos 2D presos à cabeça (olhos e boca), como em jogos estilizados.

    Para cada plano de "planos": uma grade no plano da frente, centrada na altura "centro_altura" da
    cabeça (fração entre a base, no osso Head, e o topo), com largura "largura_fracao" da cabeça e altura
    largura x "proporcao"; cada ponto é projetado na superfície do rosto (raio de frente para trás) e
    afastado "afastamento_m" pela normal. UV: exatamente a célula 1 (coluna 0, linha 0) da folha, que tem
    "colunas" x "linhas" células; o jogo troca a célula pelo deslocamento de UV. Material com a folha,
    transparente. Presos ao esqueleto com peso 1 no osso Head.
    """
    import bmesh
    from mathutils.bvhtree import BVHTree
    armature = armature_object()
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    body = max(meshes(), key=lambda o: len(o.data.polygons))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph).to_mesh()
    verts = [body.matrix_world @ v.co for v in evaluated.vertices]
    polys = [p.vertices[:] for p in evaluated.polygons]
    body.evaluated_get(depsgraph).to_mesh_clear()
    tree = BVHTree.FromPolygons(verts, polys)
    low, high = world_bounds()
    raw_to_m = asset["altura_m"] / (high.z - low.z)  # escala final (o fit vem depois)
    base = armature.matrix_world @ armature.pose.bones["Head"].head
    top = armature.matrix_world @ armature.pose.bones["head_end"].head
    head_height = top.z - base.z
    head_width = FACE["largura"] / 0.6
    center_x = FACE["posicao"].x
    offset = settings.get("afastamento_m", 0.001) / raw_to_m
    for plane in settings["planos"]:
        width = head_width * plane["largura_fracao"]
        height = width * plane["proporcao"]
        center_z = base.z + head_height * plane["centro_altura"]
        front_y = min(v.y for v in verts if abs(v.z - center_z) < height) - head_width
        nx = plane.get("grade", 12)
        ny = max(2, round(nx * plane["proporcao"]))
        cols, rows = plane["colunas"], plane["linhas"]
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")
        grid = []
        for j in range(ny + 1):
            row = []
            for i in range(nx + 1):
                u, v = i / nx, j / ny
                origin = Vector((center_x + (u - 0.5) * width, front_y, center_z + (v - 0.5) * height))
                hit, normal, _, _ = tree.ray_cast(origin, Vector((0, 1, 0)), head_width * 4)
                if hit is None:
                    hit, normal, _, _ = tree.find_nearest(origin)
                point = hit + normal.normalized() * offset
                # Em concavidades (canto do olho) outra face pode ficar mais perto que a do raio.
                near, near_normal, _, dist = tree.find_nearest(point)
                if dist < offset * 0.8:
                    point = near + near_normal.normalized() * offset
                row.append(bm.verts.new(point))
            grid.append(row)
        for j in range(ny):
            for i in range(nx):
                face = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
                for loop, (di, dj) in zip(face.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    # Célula 1: primeira coluna, linha de cima (V do Blender cresce para cima).
                    loop[uv_layer].uv = ((i + di) / nx / cols, 1 - 1 / rows + (j + dj) / ny / rows)
        bm.normal_update()
        if sum(f.normal.y for f in bm.faces) > 0:  # normais para a frente (-Y)
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(plane["nome"])
        bm.to_mesh(mesh)
        bm.free()
        for poly in mesh.polygons:
            poly.use_smooth = True
        obj = bpy.data.objects.new(plane["nome"], mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = armature
        obj.matrix_parent_inverse = armature.matrix_world.inverted()
        obj.vertex_groups.new(name="Head").add(range(len(mesh.vertices)), 1.0, "REPLACE")
        obj.modifiers.new("Armature", "ARMATURE").object = armature
        material = bpy.data.materials.new(plane["nome"].lower())
        nodes, links = material.node_tree.nodes, material.node_tree.links
        bsdf = nodes["Principled BSDF"]
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(ROOT / plane["imagem"]))
        tex.image.pack()
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        bsdf.inputs["Roughness"].default_value = MATTE_ROUGHNESS
        material.surface_render_method = "BLENDED"
        mesh.materials.append(material)
        rigid_skin(body, (center_x, center_z), (width / 2, height / 2), base.z)
        print(f"  plano {plane['nome']}: {width * raw_to_m * 100:.1f} x {height * raw_to_m * 100:.1f} cm, "
              f"a {plane['centro_altura']:.0%} da cabeça, {settings.get('afastamento_m', 0.001) * 1000:.0f} mm fora")
    FACE["mascara"] = True


def measure_head_top(settings: dict) -> None:
    """Topo da cabeça (ponto mais alto da malha perto do eixo), para os nós de encaixe do cabelo e do
    chapéu. Cada nó sobe "acima_fracao" da altura da cabeça a partir do topo."""
    armature = armature_object()
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    base = armature.matrix_world @ armature.pose.bones["Head"].head
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in meshes():
        mesh = obj.evaluated_get(depsgraph).to_mesh()
        points += [obj.matrix_world @ v.co for v in mesh.vertices]
        obj.evaluated_get(depsgraph).to_mesh_clear()
    top_z = max(p.z for p in points)
    near_axis = [p for p in points if abs(p.x - base.x) < (top_z - base.z) * 0.15 and p.z > top_z - (top_z - base.z) * 0.1]
    top = Vector((base.x, sum(p.y for p in near_axis) / len(near_axis), top_z))
    head_height = top_z - base.z
    for name, node in settings.items():
        HEAD_NODES[name] = top + Vector((0, 0, node.get("acima_fracao", 0.0) * head_height))
    print(f"  encaixes no topo da cabeça: {', '.join(settings)}")


HEAD_NODES: dict = {}  # nome -> posição no mundo antes do fit (encaixes presos à cabeça)


def add_head_node(glb: Path, name: str, position: Vector, extras: dict | None = None) -> None:
    """Acrescenta ao glTF um nó filho da articulação da cabeça (acompanha as animações).

    <position> está no espaço do modelo do glTF (Y para cima, frente +Z). O nó fica sem giro e sem
    escala no espaço do modelo: +Y para cima, +Z para a frente do personagem.
    """
    data = glb.read_bytes()
    json_length = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20:20 + json_length])
    binary = data[20 + json_length:]
    nodes = gltf["nodes"]

    def local(node: dict) -> Matrix:
        t = Matrix.Translation(node.get("translation", (0, 0, 0)))
        x, y, z, w = node.get("rotation", (0, 0, 0, 1))
        r = Quaternion((w, x, y, z)).to_matrix().to_4x4()
        sx, sy, sz = node.get("scale", (1, 1, 1))
        return t @ r @ Matrix.Diagonal((sx, sy, sz, 1))

    parent_of = {child: i for i, n in enumerate(nodes) for child in n.get("children", [])}
    head = next(i for i, n in enumerate(nodes) if n.get("name") == "Head")
    chain, node = [], head
    while node is not None:
        chain.append(node)
        node = parent_of.get(node)
    head_global = Matrix.Identity(4)
    for index in reversed(chain):
        head_global = head_global @ local(nodes[index])
    marker = head_global.inverted() @ Matrix.Translation(position)
    t, r, sc = marker.decompose()
    node = {"name": name, "translation": list(t), "rotation": [r.x, r.y, r.z, r.w], "scale": list(sc)}
    if extras:
        node["extras"] = extras
    nodes.append(node)
    nodes[head].setdefault("children", []).append(len(nodes) - 1)

    text = json.dumps(gltf, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    body = struct.pack("<II", len(text), 0x4E4F534A) + text + binary
    glb.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
    print(f"  nó {name} na cabeça" + (f" {extras}" if extras else ""))


def channelbags(action: bpy.types.Action) -> list:
    return [bag for layer in action.layers for strip in layer.strips for bag in strip.channelbags]


def set_time(scene: bpy.types.Scene, time: float) -> None:
    scene.frame_set(int(math.floor(time)), subframe=time - math.floor(time))


def rotate_about_head(matrix: Matrix, axis: Vector, angle: float) -> Matrix:
    head = matrix.to_translation()
    return (Matrix.Translation(head) @ Matrix.Rotation(angle, 4, axis)
            @ Matrix.Translation(-head) @ matrix)


def remove_bone_scale_tracks() -> None:
    """Ossos não mudam de tamanho. O idle 0 da Meshy escala o quadril em 1,176, e a personagem
    parecia encolher ao sair do idle para o walk."""
    for action in bpy.data.actions:
        for bag in channelbags(action):
            for curve in [c for c in bag.fcurves if c.data_path.endswith(".scale")]:
                bag.fcurves.remove(curve)


def measure_stride(clip: str) -> float:
    """Velocidade (m/s, já na escala do jogo) com que o pé de apoio recua no clipe feito no lugar.

    É a velocidade de chão em que a animação não desliza.
    """
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    armature.data.pose_position = "POSE"
    armature.animation_data_create()
    action = bpy.data.actions[clip]
    armature.animation_data.action = action
    if action.slots:
        armature.animation_data.action_slot = action.slots[0]
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    start, end = (int(f) for f in action.frame_range)
    track = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        track.append({b: (armature.matrix_world @ armature.pose.bones[b].head).copy() for b in STRIDE_BONES})
    # A frente é -Y: no apoio o pé recua devagar (+Y); no ar ele avança rápido (-Y).
    # Altura não serve para achar o apoio, porque o dedo sobe quando o calcanhar levanta.
    speeds = [
        (now[b].y - before[b].y) * fps
        for before, now in zip(track, track[1:])
        for b in STRIDE_BONES
        if now[b].y > before[b].y
    ]
    armature.animation_data.action = None
    armature.data.pose_position = "REST"
    scene.frame_set(0)
    return float(np.median(speeds))  # mediana: ignora os picos na virada do passo


def shrink_textures() -> None:
    for image in bpy.data.images:
        if image.size[0] > TEXTURE_SIZE:
            image.scale(TEXTURE_SIZE, TEXTURE_SIZE)


def base_color_image(material: bpy.types.Material) -> bpy.types.Image | None:
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            links = node.inputs["Base Color"].links
            if links and links[0].from_node.type == "TEX_IMAGE":
                return links[0].from_node.image
    return None


def triangle_texels(corners: list, width: int, height: int) -> np.ndarray:
    """Texels (x, y) cobertos por um triângulo de UV, por amostragem baricêntrica densa."""
    a, b, c = (np.array([u % 1 * width, v % 1 * height]) for u, v in corners)
    (ux, uy), (vx, vy) = b - a, c - a
    area = abs(ux * vy - uy * vx) / 2
    steps = int(max(8, np.sqrt(area) * 2))
    i, j = np.meshgrid(np.arange(steps + 1), np.arange(steps + 1))
    keep = i + j <= steps
    wa, wb = i[keep] / steps, j[keep] / steps
    points = np.outer(wa, a) + np.outer(wb, b) + np.outer(1 - wa - wb, c)
    texels = np.unique(points.astype(int), axis=0)
    return np.clip(texels, 0, [width - 1, height - 1])


def crystal_pixels(pixels: np.ndarray) -> np.ndarray:
    """Pixels azul-saturados e claros: o cristal. A pele e o cabelo são azuis, mas pálidos."""
    r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    return (b > 0.70) & (b - r > 0.40) & (g > 0.45)


def make_crystal_material(asset_name: str) -> None:
    obj = max(meshes(), key=lambda o: len(o.data.polygons))
    mesh = obj.data
    source = mesh.materials[0]
    image = base_color_image(source)
    if image is None:
        print("  aviso: sem textura de cor; cristal não separado")
        return
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, 4)
    is_crystal = crystal_pixels(pixels)

    # Posição de cada face na pose de repouso (coordenadas do mundo). As faces são grandes
    # perto do cristal, então amostramos o interior de cada triângulo no UV, não só os vértices.
    low, high = world_bounds()
    tall = high.z - low.z
    matrix = obj.matrix_world
    uv = mesh.uv_layers.active.data
    front_y = (low.y + high.y) / 2
    mid_x = (low.x + high.x) / 2
    mesh.calc_loop_triangles()
    picked = set()
    lit = np.zeros((height, width), dtype=bool)
    for tri in mesh.loop_triangles:
        center = matrix @ tri.center
        if not (CHEST_BAND[0] <= (center.z - low.z) / tall <= CHEST_BAND[1]):
            continue
        if abs(center.x - mid_x) > CHEST_HALF_WIDTH * tall or center.y > front_y:
            continue
        texels = triangle_texels([uv[l].uv for l in tri.loops], width, height)
        hits = is_crystal[texels[:, 1], texels[:, 0]]
        if hits.mean() >= CRYSTAL_FACE_FRACTION:
            picked.add(tri.polygon_index)
            lit[texels[hits, 1], texels[hits, 0]] = True
    if not picked:
        print("  aviso: nenhuma face do cristal encontrada no peito")
        return

    # Emissão: só os pixels do cristal dentro das faces escolhidas.
    emission = np.zeros_like(pixels)
    emission[..., 3] = 1.0
    emission[lit, :3] = pixels[lit, :3]
    glow = bpy.data.images.new(f"{asset_name}_cristal_emissao", width, height)
    glow.pixels.foreach_set(emission.ravel())
    glow.pack()

    crystal = source.copy()
    crystal.name = CRYSTAL_MATERIAL
    nodes, links = crystal.node_tree.nodes, crystal.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = glow
    links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = CRYSTAL_EMISSION_STRENGTH
    mesh.materials.append(crystal)
    slot = len(mesh.materials) - 1
    for index in picked:
        mesh.polygons[index].material_index = slot
    print(f"  cristal: {len(picked)} faces, {int(lit.sum())} pixels emissivos")


def export(root: bpy.types.Object, path: Path, animated: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        export_yup=True,
        export_animations=animated,
        export_animation_mode="ACTIONS",
        export_extras=True,  # dados extras dos nós (ex.: largura do "Rosto")
    )
    print(f"  exportado {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


def main() -> None:
    name = sys.argv[sys.argv.index("--") + 1]
    config = json.loads((ROOT / "tools/assets.json").read_text())
    asset = next(a for a in config["assets"] if a["nome"] == name)
    folder = ROOT / "assets/modelos" / name
    raw = folder / "bruto"
    character = asset["tipo"] == "personagem"
    print(f"== {name}")

    reset_scene()
    import_glb(raw / ("animacoes.glb" if character else "modelo.glb"))
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"  # medidas e cristal na pose de repouso
    bpy.context.view_layer.update()

    matte_materials()
    if character:
        rename_clips(raw)
        discard_clips(asset.get("descartar_clipes", []))
        if asset.get("animacoes_extra"):
            import_extra_clips(raw)
        for clip in asset.get("movimentos_texto", {}):
            import_motion_clip(raw, clip)
        for clip, file in asset.get("clipes_do_rig", {}).items():
            use_rig_clip(raw, clip, file)
        if asset.get("idle_respirando"):
            breathing_idle(asset["idle_respirando"])
        remove_bone_scale_tracks()
        for clip, degrees in asset.get("fechar_bracos_graus", {}).items():
            close_arms(clip, degrees)
        for clip, degrees in asset.get("inclinacao_tronco_graus", {}).items():
            set_trunk_lean(clip, degrees)
        if asset.get("carregar"):
            carry_from_walk(asset["carregar"])
        if asset.get("manivela"):
            crank_work(asset["manivela"])
        for clip in asset.get("apoiar_no_chao", []):
            ground_clip(clip)
        if "rosto" in asset:
            measure_face(asset["rosto"])
        if "nos_cabeca" in asset:
            measure_head_top(asset["nos_cabeca"])
    if asset.get("cristal_emissivo"):
        make_crystal_material(name)
    shrink_textures()
    if "apagar_rosto" in asset:
        erase_face(asset["apagar_rosto"])
    if "acabamento_pele" in asset:
        finish_skin(asset["acabamento_pele"])
    if "planos_rosto" in asset:
        add_face_planes(asset["planos_rosto"], asset)
    root = add_root(name)
    fit(root, asset)
    def to_gltf(point: Vector) -> Vector:
        # Mundo do Blender depois do fit (Z para cima, frente -Y) para o espaço do modelo glTF.
        world = root.matrix_world @ point
        return Vector((world.x, world.z, -world.y))
    head_nodes = []
    if FACE and not FACE.get("mascara"):  # com a máscara, "Rosto" é a malha, não um nó vazio
        head_nodes.append(("Rosto", to_gltf(FACE["posicao"]), {"largura_m": round(FACE["largura"] * root.scale.x, 4)}))
    for node_name, point in HEAD_NODES.items():
        head_nodes.append((node_name, to_gltf(point), None))
    if character:
        # O jogo lê isto para tocar as corridas no ritmo da velocidade real, sem deslizar.
        info = {}
        for clip in asset.get("clipes_passada", LOCOMOTION_CLIPS):
            if clip in bpy.data.actions:
                stride = measure_stride(clip)
                info[f"passada_{clip}_m_s"] = round(stride, 3)
                print(f"  passada do {clip}: {stride:.3f} m/s")
        (folder / f"{name}.json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n")
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "POSE"
    export(root, folder / f"{name}.glb", animated=character)
    for node_name, position, extras in head_nodes:
        add_head_node(folder / f"{name}.glb", node_name, position, extras)
    if head_nodes:
        # O jogo e as ferramentas de cabelo leem as posições dos encaixes (espaço do modelo glTF).
        info_path = folder / f"{name}.json"
        info = json.loads(info_path.read_text()) if info_path.exists() else {}
        info["encaixes"] = {n: [round(v, 4) for v in p] for n, p, _ in head_nodes}
        info_path.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n")


main()

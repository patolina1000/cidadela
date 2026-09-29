"""Passo 8: retalhos "Olhos" e "Boca" no corpo com rig (Blender headless).

Janela dos olhos até ±45° em volta do eixo da cabeça, na altura da variação b (10% mais alta); boca na janela
padrão. Retalhos curvos a 1,5 mm da pele, UV 0..1, materiais "rosto_olhos" e "rosto_boca" (atlas embutido, alfa
misturado), peso 100% no osso "Head". Depois confere nos quadros do idle-loop e do run-loop a distância de cada
vértice dos retalhos à pele (nunca negativa = nunca atravessa) e renderiza dois quadros.

Exporta NORMALIZADO (decisão de 29/09/2026): Armature com escala 1, em metros (rig_lib.apply_armature_scale;
sem efeito se a entrada já vier normalizada do montar_rig.py).

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/colocar_retalhos.py -- <pasta_previa> [<entrada.glb> <saida.glb>]
  Sem entrada e saída: lê e grava assets/modelos/aldeao_v2/aldeao_corpo.glb.
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpo_lib import (EYES_FRAC, MOUTH_FRAC, ROOT, ROSTO, SKIN, face_patch, flat_material, game_camera_offset,  # noqa: E402
                       head_box, import_glb, load_rosto, set_cell, set_smooth, setup_scene, shoot, twilight_lights, window_rect)
from rig_lib import apply_armature_scale, clearance, evaluated_points, play  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
BODY_IN = Path(ARGS[1]) if len(ARGS) > 2 else ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
BODY = Path(ARGS[2]) if len(ARGS) > 2 else BODY_IN
PHI_MAX, RAISE_B, OFFSET = 45, 0.10, 0.002  # 2 mm: o máximo do contrato, para nunca atravessar
RIGID_MARGIN = 0.015  # m: a pele até isso em volta das janelas passa a seguir só o osso Head
HEAD_BONE = "Head"
CHECK_POINTS = 6  # quadros conferidos por clipe, distribuídos pelo ciclo


def lit_material(name, image_path, cols, rows):
    """Material do jogo: cor do atlas com alfa, fosco (o jogo troca pelo shader toon)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(image_path))
    tex.image.pack()
    tex.extension = "CLIP"
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1 / cols, 1 / rows, 1)
    coord = nodes.new("ShaderNodeTexCoord")
    links.new(coord.outputs["UV"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    else:
        mat.blend_method = "BLEND"
    mat["mapping"] = mapping.name
    return mat


def rigid_face(body, armature, windows):
    """A pele da frente da cabeça sob as janelas (e uma margem em volta) passa a seguir 100% o osso Head, com
    transição suave: assim os retalhos, presos ao Head, nunca cruzam a pele quando o pescoço dobra."""
    head_group = body.vertex_groups[HEAD_BONE]
    others = [g for g in body.vertex_groups if g.name != HEAD_BONE]
    ymid = float(np.mean([(body.matrix_world @ v.co).y for v in body.data.vertices]))
    changed = 0
    for v in body.data.vertices:
        w = body.matrix_world @ v.co
        if w.y > ymid:
            continue  # só a frente
        d = min(max(x0 - w.x, w.x - x1, w.z - zt, zb - w.z, 0.0) for x0, zt, x1, zb in windows)
        if d > RIGID_MARGIN:
            continue
        t = 1.0 - d / RIGID_MARGIN  # 1 dentro da janela, 0 na borda da margem
        current = {g.group: g.weight for g in v.groups}
        head_w = current.get(head_group.index, 0.0)
        new_head = head_w + (1.0 - head_w) * t
        head_group.add([v.index], new_head, "REPLACE")
        for g in others:
            if g.index in current:
                g.add([v.index], current[g.index] * (1.0 - t), "REPLACE")
        changed += 1
    return changed


def main() -> None:
    out = Path(ARGS[0])
    out.mkdir(parents=True, exist_ok=True)
    scene = setup_scene(512, transparent=False)
    twilight_lights(scene)
    objs = import_glb(BODY_IN)
    armature = next(o for o in objs if o.type == "ARMATURE")
    body = next(o for o in objs if o.type == "MESH")
    for o in objs:
        if o.type == "MESH" and o.name in ("Olhos", "Boca"):
            bpy.data.objects.remove(o)
    armature.data.pose_position = "REST"
    ad = armature.animation_data
    ad.action = None
    for t in ad.nla_tracks:
        t.mute = True
    bpy.context.view_layer.update()
    rosto = load_rosto()
    ec, mc = rosto["olhos"], rosto["boca"]
    box = head_box(evaluated_points(body))
    eyes = face_patch(body, "Olhos", window_rect(box, EYES_FRAC, RAISE_B), ec["colunas"], ec["linhas"], OFFSET, grid=(32, 20), phi_max_deg=PHI_MAX)
    mouth = face_patch(body, "Boca", window_rect(box, MOUTH_FRAC), mc["colunas"], mc["linhas"], OFFSET, grid=(16, 8))
    mat_e = lit_material("rosto_olhos", ROSTO / "olhos.png", ec["colunas"], ec["linhas"])
    mat_m = lit_material("rosto_boca", ROSTO / "boca.png", mc["colunas"], mc["linhas"])
    eyes.data.materials.append(mat_e)
    mouth.data.materials.append(mat_m)
    rigid_face(body, armature, [eyes["janela"], mouth["janela"]])
    for patch in (eyes, mouth):  # peso 100% no osso da cabeça
        group = patch.vertex_groups.new(name=HEAD_BONE)
        group.add(list(range(len(patch.data.vertices))), 1.0, "REPLACE")
        patch.parent = armature
        patch.matrix_parent_inverse = armature.matrix_world.inverted()
        patch.modifiers.new("Armature", "ARMATURE").object = armature
    report = {"janela_olhos_m": list(eyes["janela"]), "phi_max_graus": eyes["phi_max_graus"], "janela_boca_m": list(mouth["janela"]), "folga_mm": {}, "offset_mm": OFFSET * 1000}

    # Conferência nos clipes: a folga fica entre 0 e ~offset em todos os quadros.
    armature.data.pose_position = "POSE"
    for t in ad.nla_tracks:
        t.mute = True
    for clip in ("idle-loop", "run-loop"):
        play(armature, bpy.data.actions[clip])
        a, b = (int(x) for x in bpy.data.actions[clip].frame_range)
        for f in [a + (b - a) * i // (CHECK_POINTS - 1) for i in range(CHECK_POINTS)]:
            scene.frame_set(f)
            report["folga_mm"][f"{clip}@{f}"] = {p.name: [round(v, 2) for v in clearance(body, p)] for p in (eyes, mouth)}
    worst = min(v[0] for frame in report["folga_mm"].values() for v in frame.values())
    report["folga_minima_mm"] = round(worst, 2)

    # Dois quadros de prévia com o rosto (distraído).
    set_cell(mat_e, ec["quadros"]["aberto"], ec["colunas"], ec["linhas"])
    set_cell(mat_m, mc["quadros"]["entreaberta"], mc["colunas"], mc["linhas"])
    set_smooth([body], True)  # o material "pele" do arquivo fica (criar outro renomearia para pele.001)
    pts = evaluated_points(body)
    low, high = pts.min(axis=0), pts.max(axis=0)
    center = Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (low[2] + high[2]) / 2))
    for clip in ("idle-loop", "run-loop"):
        play(armature, bpy.data.actions[clip])
        f = int(sum(bpy.data.actions[clip].frame_range) / 2)
        scene.frame_set(f)
        shoot(scene, center + game_camera_offset(3), center, 0.6, out / f"retalhos_{clip}_{f}_jogo.png")
        shoot(scene, center + Vector((2.1, -2.1, 0.6)), center, 0.6, out / f"retalhos_{clip}_{f}_tres_quartos.png")

    # Exporta com o rig: faixas NLA de novo ativas, pose ativa.
    ad.action = None
    for t in ad.nla_tracks:
        t.mute = False
    scene.frame_set(0)
    report["normalizacao"] = apply_armature_scale(armature, [body, eyes, mouth])  # exporta sempre em metros
    bpy.ops.object.select_all(action="DESELECT")
    for o in (armature, body, eyes, mouth):
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(BODY), export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
                              export_animations=True, export_animation_mode="NLA_TRACKS", export_skins=True, export_materials="EXPORT",
                              export_force_sampling=True, export_frame_range=False, export_optimize_animation_size=False, export_image_format="AUTO")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_glb(BODY)
    report["conferencia"] = {"objetos": [(o.type, o.name) for o in objs], "animacoes": [a.name for a in bpy.data.actions], "materiais": [m.name for m in bpy.data.materials],
                             "grupos_olhos": [g.name for g in next(o for o in objs if o.name == "Olhos").vertex_groups]}
    (BODY.with_name("aldeao_corpo_retalhos.json")).write_text(json.dumps(report, indent=2) + "\n")
    print("RELATORIO " + json.dumps(report))


main()

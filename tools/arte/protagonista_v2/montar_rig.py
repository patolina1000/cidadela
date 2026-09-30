"""Protagonista v2, parada 1: corpo limpo com o rig da Meshy, retalhos do rosto e conferência nos clipes (Blender headless).

1. rig.glb da Meshy (feito direto no corpo limpo, 0,80 m, 24 ossos): o armature fica; os pesos da malha da Meshy vão
   para as 9 malhas do corpo limpo por transferência (rig_lib.transfer_weights, face mais próxima, grupos por nome);
   as bordas entre as regiões coincidem, então as peças deformam juntas.
2. Retalhos "Olhos" e "Boca" nas janelas da b3 aprovada (olhos ±45° e +10% da cabeça, boca +12%, 2 mm da pele), atlas
   do rosto (rosto.json), peso 100% no Head; a pele da frente da cabeça sob as janelas (+1,5 cm) passa a seguir 100%
   o Head (como no aldeão: o retalho nunca cruza a pele quando o pescoço dobra).
3. Conferência da folga dos retalhos em 6 quadros de cada clipe; prévias da pose de repouso e de quadros dos clipes.
4. Exporta pelo contrato (rig_lib.export_contract_glb: metros, Armature escala 1, t = 0, 24 fps).

Clipes PROVISÓRIOS, só para a conferência desta parada (a escolha sai dos GIFs): idle-loop = Idle (0) e run-loop = a
corrida básica que veio grátis com o rig.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/montar_rig.py -- <pasta_previa>
Saída: assets/modelos/protagonista_v2/protagonista_corpo_prova.glb e protagonista_corpo_prova.json
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "aldeao_v2"))
from corpo_lib import EYES_FRAC, MOUTH_FRAC, face_patch, game_camera_offset, head_box, import_glb, set_cell, setup_scene, shoot, twilight_lights, window_rect  # noqa: E402,E501
from rig_lib import clearance, evaluated_points, export_contract_glb, play, transfer_weights  # noqa: E402

ROOT = HERE.parents[2]
RIG_DIR = ROOT / "assets/modelos/protagonista_v2/meshy/rig"
CLEAN = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
ROSTO = ROOT / "assets/modelos/protagonista_v2/rosto"
OUT = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_prova.glb"
PROVISIONAL = {"idles.glb": ("Idle", "idle-loop"), "corrida_basica.glb": ("Armature|running|baselayer", "run-loop")}
PHI_MAX, EYES_RAISE, MOUTH_RAISE, OFFSET = 45, 0.10, 0.12, 0.002  # b3
RIGID_MARGIN = 0.015
HEAD_BONE = "Head"
CHECK_POINTS = 6
COLORS = {"pele": (0.283, 0.418, 0.474, 1.0), "tecido": (0.05, 0.033, 0.054, 1.0)}


def lit_material(name, image_path, cols, rows):
    """Cor do atlas com alfa, fosco (o jogo troca pelo shader do rosto e escolhe a célula)."""
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
    mat["mapping"] = mapping.name
    return mat


def rigid_face(head, windows):
    """Pele da frente da cabeça sob as janelas (+ margem, com transição) 100% no osso Head."""
    head_group = head.vertex_groups[HEAD_BONE]
    others = [g for g in head.vertex_groups if g.name != HEAD_BONE]
    ymid = float(np.mean([(head.matrix_world @ v.co).y for v in head.data.vertices]))
    changed = 0
    for v in head.data.vertices:
        w = head.matrix_world @ v.co
        if w.y > ymid:
            continue
        d = min(max(x0 - w.x, w.x - x1, w.z - zt, zb - w.z, 0.0) for x0, zt, x1, zb in windows)
        if d > RIGID_MARGIN:
            continue
        t = 1.0 - d / RIGID_MARGIN
        current = {g.group: g.weight for g in v.groups}
        hw = current.get(head_group.index, 0.0)
        head_group.add([v.index], hw + (1.0 - hw) * t, "REPLACE")
        for g in others:
            if g.index in current:
                g.add([v.index], current[g.index] * (1.0 - t), "REPLACE")
        changed += 1
    return changed


def main() -> None:
    preview = Path(sys.argv[sys.argv.index("--") + 1:][0])
    preview.mkdir(parents=True, exist_ok=True)
    scene = setup_scene(768, transparent=False)
    twilight_lights(scene)
    report = {"clipes_provisorios": {v[1]: f"{k}:{v[0]}" for k, v in PROVISIONAL.items()}}

    objs = import_glb(RIG_DIR / "rig.glb")
    armature = next(o for o in objs if o.type == "ARMATURE")
    raw = next(o for o in objs if o.type == "MESH")
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()

    clean = [o for o in import_glb(CLEAN) if o.type == "MESH"]
    report["pesos"] = {}
    for m in clean:
        m.parent = None
        m.vertex_groups.clear()
        m.modifiers.clear()
        report["pesos"][m.name] = {"sem_peso_corrigidos": transfer_weights(raw, m, armature)}
    bpy.data.objects.remove(raw)

    # clipes provisórios: só as ações (os ossos batem pelo nome)
    for fname, (src, dst) in PROVISIONAL.items():
        before = set(bpy.data.actions)
        tmp = import_glb(RIG_DIR / fname)
        for a in [a for a in bpy.data.actions if a not in before]:
            if a.name == src:
                a.name = dst
                a.use_fake_user = True
            else:
                bpy.data.actions.remove(a)
        for o in tmp:
            bpy.data.objects.remove(o)
    armature.animation_data_create()

    head = next(o for o in clean if o.name.split(".")[0] == "cabeca")
    rosto = json.loads((ROSTO / "rosto.json").read_text())
    ec, mc = rosto["olhos"], rosto["boca"]
    box = head_box(np.vstack([evaluated_points(m) for m in clean]))
    eyes = face_patch(head, "Olhos", window_rect(box, EYES_FRAC, EYES_RAISE), ec["colunas"], ec["linhas"], OFFSET, grid=(32, 20), phi_max_deg=PHI_MAX)
    mouth = face_patch(head, "Boca", window_rect(box, MOUTH_FRAC, MOUTH_RAISE), mc["colunas"], mc["linhas"], OFFSET, grid=(16, 8))
    mat_e = lit_material("rosto_olhos", ROSTO / "olhos.png", ec["colunas"], ec["linhas"])
    mat_m = lit_material("rosto_boca", ROSTO / "boca.png", mc["colunas"], mc["linhas"])
    eyes.data.materials.append(mat_e)
    mouth.data.materials.append(mat_m)
    report["pele_do_rosto_no_head_vertices"] = rigid_face(head, [eyes["janela"], mouth["janela"]])
    for patch in (eyes, mouth):
        g = patch.vertex_groups.new(name=HEAD_BONE)
        g.add(list(range(len(patch.data.vertices))), 1.0, "REPLACE")
        patch.parent = armature
        patch.matrix_parent_inverse = armature.matrix_world.inverted()
        patch.modifiers.new("Armature", "ARMATURE").object = armature
    report.update({"janela_olhos_m": list(eyes["janela"]), "janela_boca_m": list(mouth["janela"]), "offset_mm": OFFSET * 1000})

    # prévias: repouso e quadros dos clipes (pele fosca, rosto no quadro padrão)
    set_cell(mat_e, 0, ec["colunas"], ec["linhas"])
    set_cell(mat_m, 0, mc["colunas"], mc["linhas"])
    for m in clean:
        for mat in m.data.materials:
            key = mat.name.split(".")[0]
            if key in COLORS:
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                bsdf.inputs["Base Color"].default_value = COLORS[key]
                bsdf.inputs["Roughness"].default_value = 1.0
    center = Vector((0, 0, 0.42))
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    shoot(scene, center + Vector((0, -3, 0)), center, 1.0, preview / "repouso_frente.png")
    shoot(scene, center + Vector((2.1, -2.1, 0.6)), center, 1.0, preview / "repouso_tres_quartos.png")
    armature.data.pose_position = "POSE"
    report["folga_mm"] = {}
    for clip in ("idle-loop", "run-loop"):
        action = bpy.data.actions[clip]
        play(armature, action)
        a, b = (int(x) for x in action.frame_range)
        frames = [a + (b - a) * i // (CHECK_POINTS - 1) for i in range(CHECK_POINTS)]
        for f in frames:
            scene.frame_set(f)
            report["folga_mm"][f"{clip}@{f}"] = {p.name: [round(v, 2) for v in clearance(head, p)] for p in (eyes, mouth)}
        f = frames[2]
        scene.frame_set(f)
        shoot(scene, center + game_camera_offset(3), center, 1.0, preview / f"{clip}_jogo.png")
        head_c = Vector((0, 0, 0.70))
        shoot(scene, head_c + Vector((1.6, -2.2, 0.5)), head_c, 0.3, preview / f"{clip}_cabeca_tres_quartos.png")
        shoot(scene, center + Vector((2.1, -2.1, 0.6)), center, 1.0, preview / f"{clip}_tres_quartos.png")
    report["folga_minima_mm"] = round(min(v[0] for fr in report["folga_mm"].values() for v in fr.values()), 2)
    report["folga_maxima_mm"] = round(max(v[1] for fr in report["folga_mm"].values() for v in fr.values()), 2)

    armature.animation_data.action = None
    scene.frame_set(0)
    report["exportacao"] = export_contract_glb(armature, [armature, *clean, eyes, mouth], OUT)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_glb(OUT)
    tris = 0
    for o in objs:
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles) if o.name not in ("Olhos", "Boca") else 0
    report["conferencia"] = {"objetos": sorted(o.name for o in objs), "animacoes": [a.name for a in bpy.data.actions],
                             "materiais": sorted(m.name for m in bpy.data.materials), "triangulos_corpo": tris,
                             "escala_armature": [round(x, 4) for x in next(o for o in objs if o.type == "ARMATURE").scale]}
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("RELATORIO " + json.dumps({k: v for k, v in report.items() if k != "folga_mm"}, ensure_ascii=False))


main()

"""Prova do cristal da protagonista v2 ao lado da v1 (Blender headless).

v2 = corpo limpo (toon chapado, pele #91ADB7, tecido #3F3342) + cristal.glb (toon da cor da gema + emissão × 3, o
reforço que o jogo aplica ao material "Cristal"). v1 = protagonista.glb como estava no jogo (textura e luz de verdade,
emissão do Cristal × 3). Duas luzes: dia (a luz fraca e fria das prévias) e crepúsculo (a luz × #6A5B7C; a emissão não
muda, como no jogo). Vistas: frente e 3/4 das duas, close do peito (frente e 3/4) e câmera do jogo nos zooms 0,4 / 1 /
2,5. Mede o cristal em px na câmera do jogo (v2 e v1). A luz OmniLight da v1 (que clareia o chão e os vizinhos) é do
jogo e não entra aqui.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/prova_cristal.py -- <pasta>
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import GAME_H, GAME_W, ROOT, V1, eevee_scene, game_camera, hex_linear, import_glb, load_rest, mesh_objects, mesh_points, render, toon_material  # noqa: E402,E501
from render_meshy import AMBIENT_RGB, SUN_EULER, SUN_RGB, light_dir, ortho_camera, projected, root_of  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
GEM = ROOT / "assets/modelos/protagonista_v2/cristal.glb"
INFO = ROOT / "assets/modelos/protagonista_v2/cristal.json"
COLORS = {"pele": "#91ADB7", "tecido": "#3F3342"}
TWILIGHT = hex_linear("#6A5B7C")[:3]
BOOST = 3.0  # CastellanVisual.CrystalEmissionBoost
V1_X = 0.55
ZOOMS = (0.4, 1.0, 2.5)


def glow_material(info, sun_rgb, amb_rgb):
    """A gema: a cor dela na luz toon (o sol e o ambiente da cena) + a emissão × força × 3 (reforço do jogo). A parte
    emissiva não depende da luz, como no jogo."""
    base = hex_linear(info["cor_base"])[:3]
    emit = [c * info["forca_emissao"] * BOOST for c in hex_linear(info["emissao"])[:3]]
    lit = [b * (a + s * 0.7) for b, a, s in zip(base, amb_rgb, sun_rgb)]
    mat = bpy.data.materials.new("Cristal")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*[l + e for l, e in zip(lit, emit)], 1)
    em.inputs["Strength"].default_value = 1.0
    mat.node_tree.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def build(scene, light):
    sun_rgb = tuple(c * t for c, t in zip(SUN_RGB, light))
    amb_rgb = tuple(c * t for c, t in zip(AMBIENT_RGB, light))
    info = json.loads(INFO.read_text())
    prot = import_glb(BODY)
    mats = {k: toon_material(k, light_dir(), sun_rgb, amb_rgb, color=hex_linear(c)) for k, c in COLORS.items()}
    for o in mesh_objects(prot):
        m = o.data.materials[0].name.split(".")[0] if o.data.materials else "pele"
        o.data.materials.clear()
        o.data.materials.append(mats.get(m, mats["pele"]))
    gem = [o for o in import_glb(GEM) if o.type == "MESH"]
    gem_mat = glow_material(info, sun_rgb, amb_rgb)
    for o in gem:
        o.data.materials.clear()
        o.data.materials.append(gem_mat)
    # v1 como no jogo: material do GLB, sol e ambiente de verdade (as mesmas cores), Cristal × 3
    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sun.data.energy = 1.0
    sun.data.color = sun_rgb
    sun.data.angle = math.radians(20)
    sun.rotation_euler = SUN_EULER
    scene.collection.objects.link(sun)
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*amb_rgb, 1)
    bg.inputs["Strength"].default_value = 1.0
    v1 = load_rest(V1)
    v1_gem = []
    for o in mesh_objects(v1):
        for m in o.data.materials:
            b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if m.name.startswith("Cristal") and b is not None:
                b.inputs["Emission Strength"].default_value *= BOOST
                v1_gem.append(o)
    root = root_of(v1, "v1")
    root.location = (V1_X, 0, 0)
    bpy.context.view_layer.update()
    return prot, gem, v1


def v1_crystal_points(v1):
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in mesh_objects(v1):
        idx = [i for i, m in enumerate(o.data.materials) if m.name.startswith("Cristal")]
        if not idx:
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        vids = {v for t in me.loop_triangles if t.material_index in idx for v in t.vertices}
        pts += [(o.matrix_world @ me.vertices[i].co)[:] for i in vids]
        ev.to_mesh_clear()
    return np.array(pts)


def main() -> None:
    out = Path(sys.argv[sys.argv.index("--") + 1:][0])
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for tag, light in (("dia", (1.0, 1.0, 1.0)), ("crepusculo", TWILIGHT)):
        scene = eevee_scene(transparent=True)
        prot, gem, v1 = build(scene, light)
        chest_z = float(np.mean([v[:] for o in gem for v in [o.matrix_world @ vv.co for vv in o.data.vertices]], axis=0)[2])
        for view, d in (("frente", Vector((0, -1, 0))), ("tres_quartos", Vector((1, -1, 0)))):
            scene.render.resolution_x = scene.render.resolution_y = 1024
            cam = ortho_camera(scene, d, Vector((V1_X / 2, 0, 0.45)), 1.25)
            render(scene, out / f"{tag}_{view}.png")
            bpy.data.objects.remove(cam)
            for who, x in (("v2", 0.0), ("v1", V1_X)):
                cam = ortho_camera(scene, d, Vector((x, 0, chest_z + 0.02)), 0.22)
                render(scene, out / f"{tag}_peito_{who}_{view}.png")
                bpy.data.objects.remove(cam)
        gem_pts = mesh_points(gem)
        v1_pts = v1_crystal_points(v1)
        both = np.vstack([mesh_points(prot), mesh_points(v1)])
        for zoom in ZOOMS:
            cam = game_camera(scene, zoom, Vector((V1_X / 2, 0, 0)))
            bpy.context.view_layer.update()
            gp, vp, bp = projected(scene, cam, gem_pts), projected(scene, cam, v1_pts), projected(scene, cam, both)
            if tag == "dia":
                report[str(zoom)] = {
                    "cristal_v2_px": [round(float(np.ptp(gp[:, 0])), 1), round(float(np.ptp(gp[:, 1])), 1)],
                    "cristal_v1_px": [round(float(np.ptp(vp[:, 0])), 1), round(float(np.ptp(vp[:, 1])), 1)],
                    "cristal_v2_centro_px": [float(gp[:, 0].mean()), float(gp[:, 1].mean())],
                    "cristal_v1_centro_px": [float(vp[:, 0].mean()), float(vp[:, 1].mean())],
                    "caixa_px": [float(bp[:, 0].min()), float(bp[:, 1].min()), float(bp[:, 0].max()), float(bp[:, 1].max())],
                    "tela": [GAME_W, GAME_H]}
            render(scene, out / f"{tag}_jogo_{zoom}.png")
            bpy.data.objects.remove(cam)
    (out / "prova_cristal.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PX " + json.dumps({z: (r["cristal_v2_px"], r["cristal_v1_px"]) for z, r in report.items()}))


main()

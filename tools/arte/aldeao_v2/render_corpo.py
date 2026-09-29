"""Renderiza um GLB bruto da Meshy (corpo do aldeão v2) em Blender headless, com material chapado cor de pele:
frente, lado, 3/4, câmera do jogo (55°) e a frente com a protagonista ao lado em escala (aldeão a 0,40 m,
protagonista como está, ~0,75 m). Sem limpeza, rig ou animação. Também mede a cabeça e a lisura da área do rosto.

Saída: <pasta>/<nome>_{frente,lado,tres_quartos,jogo,escala}.png e <nome>_medidas.json com a caixa da cabeça
na imagem de frente (para marcar os retalhos) e o desvio da área do rosto em relação a uma esfera ajustada.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/render_corpo.py -- <glb> <pasta_saida>
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
PROTAGONIST = ROOT / "assets/modelos/protagonista/protagonista.glb"
RESOLUTION = 1024
HEIGHT_M = 0.40  # contrato
SKIN = (0.682, 0.749, 0.827, 1.0)  # #AEBFD3
GAME_TILT = 55
# Janelas dos retalhos, em fração da caixa da cabeça (de desenhar_rosto.py: cabeça 18..238 x 12..248, olhos
# 24..232 x 78..208, boca 110..174 x 170..202, no rosto de referência de 256 px).
EYES_FRAC = ((24 - 18) / 220, (78 - 12) / 236, (232 - 18) / 220, (208 - 12) / 236)
MOUTH_FRAC = ((110 - 18) / 220, (170 - 12) / 236, (174 - 18) / 220, (202 - 12) / 236)


def import_glb(path: Path) -> list:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), disable_bone_shape=True)
    return [o for o in bpy.data.objects if o not in before]


def mesh_points(objects) -> np.ndarray:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in objects:
        if obj.type == "MESH":
            ev = obj.evaluated_get(depsgraph)
            m = ev.to_mesh()
            pts += [obj.matrix_world @ v.co for v in m.vertices]
            ev.to_mesh_clear()
    return np.array([[p.x, p.y, p.z] for p in pts])


def flat_material(objects, color):
    mat = bpy.data.materials.new("pele_previa")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.9
    for obj in objects:
        if obj.type == "MESH":
            obj.data.materials.clear()
            obj.data.materials.append(mat)


def normalize(objects, height: float) -> tuple:
    """Escala para a altura pedida, pés em z = 0, centro x/y na origem (Blender: z para cima)."""
    pts = mesh_points(objects)
    low, high = pts.min(axis=0), pts.max(axis=0)
    scale = height / (high[2] - low[2])
    root = bpy.data.objects.new("raiz", None)
    bpy.context.scene.collection.objects.link(root)
    for obj in objects:
        if obj.parent is None:
            obj.parent = root
    root.scale = (scale,) * 3
    root.location = (-(low[0] + high[0]) / 2 * scale, -(low[1] + high[1]) / 2 * scale, -low[2] * scale)
    bpy.context.view_layer.update()
    pts = mesh_points(objects)
    return pts, pts.min(axis=0), pts.max(axis=0)


def head_box(pts: np.ndarray, low, high) -> dict:
    """Cabeça = tudo acima do pescoço; pescoço = fatia mais estreita (em x) entre 55% e 88% da altura."""
    h = high[2] - low[2]
    zs = pts[:, 2]
    best = None
    for f in np.linspace(0.55, 0.88, 67):
        z = low[2] + f * h
        band = pts[np.abs(zs - z) < h * 0.01]
        if len(band) < 5:
            continue
        w = band[:, 0].max() - band[:, 0].min()
        if best is None or w < best[0]:
            best = (w, z)
    neck_z = best[1]
    head = pts[zs >= neck_z]
    return {"pescoco_z": float(neck_z), "x": [float(head[:, 0].min()), float(head[:, 0].max())],
            "y": [float(head[:, 1].min()), float(head[:, 1].max())], "z": [float(neck_z), float(head[:, 2].max())]}


def face_flatness(pts: np.ndarray, box: dict) -> dict:
    """Pontos da frente da cabeça (-y no Blender = +z do glTF, a frente) dentro da janela dos olhos e da boca:
    ajusta uma esfera por mínimos quadrados e devolve o desvio RMS e máximo, em mm."""
    x0, x1 = box["x"]
    z0, z1 = box["z"]
    w, hh = x1 - x0, z1 - z0
    out = {}
    for name, (fx0, fy0, fx1, fy1) in (("olhos", EYES_FRAC), ("boca", MOUTH_FRAC)):
        sel = pts[(pts[:, 0] >= x0 + fx0 * w) & (pts[:, 0] <= x0 + fx1 * w)
                  & (pts[:, 2] <= z1 - fy0 * hh) & (pts[:, 2] >= z1 - fy1 * hh)]
        ymid = (box["y"][0] + box["y"][1]) / 2
        sel = sel[sel[:, 1] < ymid]  # frente da cabeça
        if len(sel) < 12:
            out[name] = {"pontos": int(len(sel))}
            continue
        A = np.c_[2 * sel, np.ones(len(sel))]
        b = (sel ** 2).sum(axis=1)
        c, *_ = np.linalg.lstsq(A, b, rcond=None)
        center, r = c[:3], math.sqrt(c[3] + (c[:3] ** 2).sum())
        dev = np.linalg.norm(sel - center, axis=1) - r
        out[name] = {"pontos": int(len(sel)), "raio_mm": round(r * 1000, 1), "rms_mm": round(float(np.sqrt((dev ** 2).mean()) * 1000), 2),
                     "max_mm": round(float(np.abs(dev).max() * 1000), 2)}
    return out


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.types, "SceneEEVEE") and "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = RESOLUTION
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("fundo")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.92, 0.91, 0.94, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = world
    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(45), 0, math.radians(-35))
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("contra", bpy.data.lights.new("contra", "SUN"))
    fill.data.energy = 0.8
    fill.rotation_euler = (math.radians(60), 0, math.radians(150))
    scene.collection.objects.link(fill)
    return scene


def shoot(scene, location: Vector, target: Vector, ortho: float, path: Path) -> dict:
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"  {path.name}")
    info = {"ortho": ortho, "alvo": list(target), "posicao": list(location)}
    bpy.data.objects.remove(cam)
    return info


def main() -> None:
    glb, out = (Path(a) for a in sys.argv[sys.argv.index("--") + 1:][:2])
    out.mkdir(parents=True, exist_ok=True)
    name = glb.stem
    scene = setup_scene()
    objects = import_glb(glb)
    for obj in objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"
    flat_material(objects, SKIN)
    pts, low, high = normalize(objects, HEIGHT_M)
    box = head_box(pts, low, high)
    flat = face_flatness(pts, box)
    tris = sum(len(o.data.loop_triangles) if (o.type == "MESH" and (o.data.calc_loop_triangles() or True)) else 0 for o in objects)

    center = Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (low[2] + high[2]) / 2))
    size = float(max(high - low)) * 1.15
    dist = size * 4
    views = {}
    views["frente"] = shoot(scene, center + Vector((0, -dist, 0)), center, size, out / f"{name}_frente.png")
    views["lado"] = shoot(scene, center + Vector((dist, 0, 0)), center, size, out / f"{name}_lado.png")
    d = dist / math.sqrt(2)
    views["tres_quartos"] = shoot(scene, center + Vector((d, -d, 0)), center, size, out / f"{name}_tres_quartos.png")
    tilt = math.radians(GAME_TILT)
    views["jogo"] = shoot(scene, center + Vector((0, -math.cos(tilt), math.sin(tilt))) * dist, center, size, out / f"{name}_jogo.png")

    # Escala: protagonista ao lado, como está (o normalize dela já é o do jogo).
    prot = import_glb(PROTAGONIST) if PROTAGONIST.exists() else []
    for obj in prot:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"
    if prot:
        flat_material(prot, (0.55, 0.62, 0.72, 1))
        proot = bpy.data.objects.new("raiz_prot", None)
        scene.collection.objects.link(proot)
        for obj in prot:
            if obj.parent is None:
                obj.parent = proot
        proot.location = (0.55, 0, 0)
        bpy.context.view_layer.update()
        ppts = mesh_points(prot)
        allp = np.vstack([pts, ppts])
        lo, hi = allp.min(axis=0), allp.max(axis=0)
        c = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))
        s = float(max(hi - lo)) * 1.15
        views["escala"] = shoot(scene, c + Vector((0, -s * 4, 0)), c, s, out / f"{name}_escala.png")
        views["escala"]["altura_protagonista_m"] = float(ppts[:, 2].max() - ppts[:, 2].min())

    measures = {"glb": str(glb), "triangulos": int(tris), "altura_m": HEIGHT_M, "caixa_total": [low.tolist(), high.tolist()],
                "cabeca": box, "rosto": flat, "vistas": views}
    (out / f"{name}_medidas.json").write_text(json.dumps(measures, indent=2) + "\n")
    print(json.dumps({"triangulos": int(tris), "cabeca": box, "rosto": flat}, indent=1))


main()

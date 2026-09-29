"""Altura em pixels da protagonista e do aldeão na câmera do jogo (perspectiva, FOV vertical 45°, pitch 55°,
distância 16 m / zoom), em 3024x1890, nos zooms 0,4, 1 e 2,5 (CameraRig.cs)."""
import math, sys, json
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0, "/Users/arthurlopesdefranca/Projetos/cidadela-arte/tools/arte/aldeao_v2")
from corpo_lib import import_glb, mesh_points, flat_material, set_smooth, SKIN
import numpy as np
ROOT = Path("/Users/arthurlopesdefranca/Projetos/cidadela-arte")
S = Path(__file__).resolve().parent / "_zoom"  # renders de medição, fora do git
W, H, FOV, PITCH, DIST = 3024, 1890, 45.0, 55.0, 16.0
out = {}
for name, glb in (("protagonista", ROOT / "assets/modelos/protagonista/protagonista.glb"), ("aldeao", ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = W, H
    scene.render.film_transparent = True
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    objs = import_glb(glb)
    for o in objs:
        if o.type == "ARMATURE": o.data.pose_position = "REST"
    flat_material(objs, SKIN); set_smooth(objs, True)
    pts = mesh_points(objs); low, high = pts.min(axis=0), pts.max(axis=0)
    height = float(high[2] - low[2])
    out[name] = {"altura_m": round(height, 3), "zoom": {}}
    for zoom in (0.4, 1.0, 2.5):
        d = DIST / zoom
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam)
        cam.data.type = "PERSP"; cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(FOV)
        cam.data.clip_end = 200
        tilt = math.radians(PITCH)
        target = Vector((0, 0, 0))  # a câmera mira o chão onde o personagem está
        cam.location = target + Vector((0, -math.cos(tilt), math.sin(tilt))) * d
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
        path = S / f"zoom_{name}_{zoom}.png"
        scene.render.filepath = str(path); bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(str(path))
        px = np.array(img.pixels[:]).reshape(H, W, 4)[:, :, 3]
        rows = np.nonzero(px.max(axis=1) > 0.05)[0]
        out[name]["zoom"][str(zoom)] = int(rows.max() - rows.min() + 1) if len(rows) else 0
        bpy.data.images.remove(img); bpy.data.objects.remove(cam)
print("MEDIDAS " + json.dumps(out))

"""Tira de quadros dos clipes do corpo com rig (Blender headless): pose de repouso e quadros do idle-loop e do
run-loop na câmera do jogo (55°) e de lado, material fosco e luz do crepúsculo. Saída: <pasta>/<clipe>_<quadro>_<vista>.png.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/previa_clipes.py -- <pasta_saida>
"""

import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpo_lib import ROOT, SKIN, flat_material, game_camera_offset, import_glb, mesh_points, set_smooth, setup_scene, shoot, twilight_lights  # noqa: E402

BODY = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
FRAMES = {"idle-loop": (0, 24, 48, 72), "run-loop": (0, 3, 6, 9)}


def main() -> None:
    out = Path(sys.argv[sys.argv.index("--") + 1])
    out.mkdir(parents=True, exist_ok=True)
    scene = setup_scene(512, transparent=False)
    twilight_lights(scene)
    objs = import_glb(BODY)
    armature = next(o for o in objs if o.type == "ARMATURE")
    flat_material(objs, SKIN, matte=True)
    set_smooth(objs, True)
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    pts = mesh_points(objs)
    low, high = pts.min(axis=0), pts.max(axis=0)
    center = Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (low[2] + high[2]) / 2))
    ortho = 0.6
    shoot(scene, center + game_camera_offset(3), center, ortho, out / "repouso_jogo.png")
    shoot(scene, center + Vector((3, 0, 0)), center, ortho, out / "repouso_lado.png")
    armature.data.pose_position = "POSE"
    armature.animation_data_create()
    for clip, frames in FRAMES.items():
        action = bpy.data.actions[clip]
        armature.animation_data.action = action
        if getattr(action, "slots", None):
            armature.animation_data.action_slot = action.slots[0]
        for f in frames:
            scene.frame_set(f)
            shoot(scene, center + game_camera_offset(3), center, ortho, out / f"{clip}_{f:02d}_jogo.png")
            shoot(scene, center + Vector((3, 0, 0)), center, ortho, out / f"{clip}_{f:02d}_lado.png")


main()

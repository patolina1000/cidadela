"""Entrada do rig da Meshy: o corpo limpo (protagonista_corpo_limpo.glb) juntado numa malha só, sem o cristal, 0,80 m,
frente +Z do glTF, material "pele" (a Meshy só precisa da forma). Vértices das bordas entre regiões fundidos.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/preparar_rig.py
Saída: assets/modelos/protagonista_v2/meshy/corpo_para_rig.glb
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prot_lib import ROOT, import_glb, mesh_objects  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
OUT = ROOT / "assets/modelos/protagonista_v2/meshy/corpo_para_rig.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)
meshes = mesh_objects(import_glb(BODY))
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
bm = bmesh.new()
bm.from_mesh(obj.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(obj.data)
bm.free()
obj.name = obj.data.name = "corpo"
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True, export_yup=True,
                          export_apply=True, export_materials="EXPORT")
obj.data.calc_loop_triangles()
print("PREPARADO", OUT.relative_to(ROOT), len(obj.data.loop_triangles), "triângulos", len(obj.data.vertices), "vértices")

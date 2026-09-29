"""Reexporta os clipes da prova de operação pelo contrato de animação (29/09/2026), sem refazer o IK: importa
clipes/girar_roda.glb (exportado em escala 0,004, primeira chave no quadro 1), normaliza o esqueleto para metros,
desloca as chaves para t = 0 e exporta a 24 fps (operacao_lib.export_clip), no mesmo lugar. Raiz e variante_r06.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/prova_operacao/reexportar_clipes.py
"""

import json
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
sys.path.insert(0, str(HERE))
from corpo_lib import ROOT, import_glb  # noqa: E402
from operacao_lib import export_clip, gltf_clip_times  # noqa: E402

FOLDERS = ("", "variante_r06")


def main() -> None:
    report = {}
    for sub in FOLDERS:
        path = ROOT / "assets/modelos/prova_operacao" / sub / "clipes/girar_roda.glb"
        before = gltf_clip_times(path)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = import_glb(path)
        arm = next(o for o in objs if o.type == "ARMATURE")
        actions = [a for a in bpy.data.actions]
        info = export_clip(arm, actions, path)
        report[sub or "raiz"] = {"antes": before, "depois": gltf_clip_times(path), **info}
    print("REEXPORTACAO " + json.dumps(report, ensure_ascii=False))


main()

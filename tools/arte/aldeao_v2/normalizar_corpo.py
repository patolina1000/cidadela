"""Normalização oficial do aldeão v2 aprovado (29/09/2026): Armature com escala 1, em metros (Blender headless).
Método da prova (tools/arte/prova_operacao/normalizar.py), hoje em rig_lib.apply_armature_scale. Nomes de
ossos, clipes, materiais e malhas ficam. Exporta num arquivo temporário, confere contra o aprovado com o
conferir_corpo.compare e só substitui assets/modelos/aldeao_v2/aldeao_corpo.glb se tudo passar:
- vértices: diferença máxima < 0,01 mm nos quadros 0/25/50/75% dos dois clipes;
- folga dos retalhos entre 1,4 e 3,2 mm nos quadros que o colocar_retalhos.py confere;
- cabelos 1 a 5 presos como no jogo: diferença < 0,01 mm;
- mesmos nomes; nó Armature do glTF sem escala.
Relatório: assets/modelos/aldeao_v2/aldeao_corpo_normalizacao.json.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/aldeao_v2/normalizar_corpo.py -- <temporario.glb>
"""

import json
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conferir_corpo import compare  # noqa: E402
from corpo_lib import ROOT, import_glb  # noqa: E402
from rig_lib import apply_armature_scale, export_rig_glb  # noqa: E402

BODY = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
REPORT = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo_normalizacao.json"
MAX_MM = 0.01
GAP_RANGE = (1.4, 3.2)


def main() -> None:
    tmp = Path(sys.argv[sys.argv.index("--") + 1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_glb(BODY)
    arm = next(o for o in objs if o.type == "ARMATURE")
    meshes = [o for o in objs if o.type == "MESH"]
    info = apply_armature_scale(arm, meshes)
    export_rig_glb(arm, [arm, *meshes], tmp)

    report = {"normalizacao": info, "conferencia": compare(BODY, tmp)}
    c = report["conferencia"]
    fb = c["folga_retalhos"]["b"]
    checks = {
        "vertices_menor_que_0_01_mm": c["vertices_max_mm"] < MAX_MM,
        "folga_retalhos_entre_1_4_e_3_2_mm": GAP_RANGE[0] <= fb["min_mm"] and fb["max_mm"] <= GAP_RANGE[1],
        "cabelos_menor_que_0_01_mm": c["cabelos_max_mm"] < MAX_MM,
        "nomes_iguais": all(c["nomes_iguais"].values()),
        "armature_sem_escala": c["gltf_armature"]["b"]["scale"] in (None, [1, 1, 1], [1.0, 1.0, 1.0]),
    }
    report["metas"] = checks
    report["substituiu_o_aprovado"] = all(checks.values())
    if report["substituiu_o_aprovado"]:
        shutil.copyfile(tmp, BODY)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("METAS " + json.dumps(checks) + " SUBSTITUIU " + str(report["substituiu_o_aprovado"]))
    print("RESUMO " + json.dumps({"vertices_max_mm": c["vertices_max_mm"], "cabelos_max_mm": c["cabelos_max_mm"],
                                  "folga_a": [c["folga_retalhos"]["a"]["min_mm"], c["folga_retalhos"]["a"]["max_mm"]],
                                  "folga_b": [fb["min_mm"], fb["max_mm"]], "nomes": c["nomes"], "cabelos_corpo": c["cabelos_repouso_min_ate_corpo_mm"],
                                  "gltf": c["gltf_armature"]}, ensure_ascii=False))


main()

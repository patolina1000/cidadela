"""Confere os clipes de operação de uma pasta da prova contra o corpo aprovado (Blender headless), como o jogo os usa.
Para cada clipe do clipes.json:
1. arquivo: escala do nó Armature, malhas, tempos das chaves (t0, t1, contagem, fps) lidos do GLB;
2. esqueleto: mesmos nomes e repouso igual ao de assets/modelos/aldeao_v2/aldeao_corpo.glb (posição em mm e
   rotação em graus, no mundo);
3. palma-manopla nos quadros do ciclo: o corpo aprovado é posto no posto (posição e giro em relação à roda, do
   clipes.json), a roda (roda.glb, pivô no eixo) gira −360° × fase em volta do seu +Z, o clipe é posicionado pela
   fórmula da fase (quadro = fase × quadros, primeira chave em t = 0) e a palma de cada mão é comparada com o seu
   lado da manopla física da alça do posto. Compara com os valores anteriores, se houver.
clipes.json antigo (um posto só, bloco "roda"): o posto A é tirado de "posicao_no_espaco_do_aldeao_m".

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/prova_operacao/conferir_clipes.py -- <subpasta ou ""> <saida.json>
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
sys.path.insert(0, str(HERE))
from corpo_lib import ROOT, import_glb  # noqa: E402
from operacao_lib import GRIP_HALF, gltf_clip_times  # noqa: E402
from rig_lib import play  # noqa: E402

BODY = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"


def gltf_to_blender(v) -> Vector:
    return Vector((v[0], -v[2], v[1]))


def postos(clips: dict) -> dict:
    """{nome_do_clipe: (arquivo, posto)} no formato novo; o antigo vira o posto A."""
    out = {}
    for name, c in clips.items():
        if "posto" in c:
            out[name] = (c["arquivo"], c["posto"], c)
        else:
            cx, cy, cz = c["roda"]["posicao_no_espaco_do_aldeao_m"]
            posto = {"alca": "A", "posicao_m": [-cx, -cy, cz], "giro_em_y_graus": 180.0}  # inverso de: roda em (c) girada 180°
            out[name] = ("clipes/girar_roda.glb", posto, c)
    return out


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    sub, out_path = args[0], Path(args[1])
    base = ROOT / "assets/modelos/prova_operacao" / sub
    prev_dir = ROOT / "assets/previews/prova_operacao" / sub
    clips = json.loads((base / "clipes.json").read_text())
    rep = json.loads((prev_dir / "girar_roda.json").read_text())
    knob_y = rep["roda"]["knob_y_m"]
    palm_len = {s: rep["esqueleto"]["comprimentos_m"][f"{s}Hand"] for s in ("Left", "Right")}
    previous = {}
    gif = prev_dir / "roda_gif_medidas.json"
    if gif.exists():
        rows = json.loads(gif.read_text())["por_quadro"]
        previous["A"] = [(r["A_esq"], r["A_dir"]) for r in rows]
        previous["B"] = [(r["B_esq"], r["B_dir"]) for r in rows]

    report = {}
    for name, (file, posto, c) in postos(clips).items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.fps = c["fps"]
        body = import_glb(BODY)
        arm = next(o for o in body if o.type == "ARMATURE")
        arm.animation_data_clear()
        before = set(bpy.data.actions)
        clip_objs = import_glb(base / file)
        carm = next(o for o in clip_objs if o.type == "ARMATURE")
        action = next(a for a in bpy.data.actions if a not in before and a.name.startswith(name))
        bpy.context.view_layer.update()
        rest_pos = max((arm.matrix_world @ b.matrix_local).to_translation().__sub__(
            (carm.matrix_world @ carm.data.bones[b.name].matrix_local).to_translation()).length for b in arm.data.bones)
        rest_rot = max((arm.matrix_world @ b.matrix_local).to_quaternion().rotation_difference(
            (carm.matrix_world @ carm.data.bones[b.name].matrix_local).to_quaternion()).angle for b in arm.data.bones)
        rest_rot = min(rest_rot, 2 * math.pi - rest_rot)
        info = {"arquivo": file, "gltf": gltf_clip_times(base / file)["animacoes"].get(name) or gltf_clip_times(base / file),
                "gltf_armature": gltf_clip_times(base / file)["armature"], "malhas_no_clipe": gltf_clip_times(base / file)["malhas"],
                "ossos_iguais": [b.name for b in arm.data.bones] == [b.name for b in carm.data.bones],
                "repouso_dif_mm": round(rest_pos * 1000, 5), "repouso_dif_graus": round(math.degrees(rest_rot), 5),
                "quadros_da_acao": list(action.frame_range), "posto": posto}
        for o in clip_objs:
            bpy.data.objects.remove(o)

        # Corpo no posto; roda na origem.
        root = bpy.data.objects.new("posto", None)
        scene.collection.objects.link(root)
        arm.parent = root
        root.matrix_world = Matrix.Translation(gltf_to_blender(posto["posicao_m"])) @ Matrix.Rotation(math.radians(posto["giro_em_y_graus"]), 4, "Z")
        arm.data.pose_position = "POSE"
        play(arm, action)
        radius = c.get("peca", {}).get("raio_alca_m") or c.get("roda", {}).get("raio_alca_m")
        knob_local = Vector((0, -knob_y, radius)) if posto["alca"] == "A" else Vector((0, knob_y, -radius))
        frames = c["quadros"]
        lateral = (root.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
        rows = []
        for i in range(frames):
            p = i / frames
            scene.frame_set(int(action.frame_range[0]) + i)  # quadro = fase × quadros, a partir da primeira chave
            knob = Matrix.Rotation(2 * math.pi * p, 4, "Y") @ knob_local  # −360° × fase em volta do +Z do glTF
            miss = {}
            for side, sign in (("Left", 1), ("Right", -1)):
                pb = arm.pose.bones[f"{side}Hand"]
                palm = arm.matrix_world @ pb.matrix @ Vector((0, palm_len[side] / arm.matrix_world.to_scale()[0], 0))
                miss[side] = (palm - (knob + lateral * GRIP_HALF * sign)).length * 1000
            rows.append((round(miss["Left"], 1), round(miss["Right"], 1)))
        info["palma_manopla_max_mm"] = max(max(r) for r in rows)
        info["palma_manopla_por_quadro_mm"] = rows
        prev = previous.get(posto["alca"])
        if prev:
            info["dif_contra_antes_mm"] = round(max(abs(a - b) for r, q in zip(rows, prev) for a, b in zip(r, q)), 2)
            info["antes_max_mm"] = max(max(q) for q in prev)
        report[name] = info
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("CONFERENCIA " + json.dumps({k: {x: v[x] for x in v if x != "palma_manopla_por_quadro_mm"} for k, v in report.items()}, ensure_ascii=False))


main()

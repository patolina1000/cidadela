"""Passo 4 da prova de operação: quadros dos GIFs da roda com dois aldeões (Blender headless).
Cena: roda no centro, eixo em X do mundo; aldeão A de um lado (cabelo 1), aldeão B do outro (cabelo 3). Os dois
são o aldeao_corpo.glb aprovado. Como o jogo (contrato de animação): um clipe POR POSTO, do clipes.json —
A toca girar_roda-loop (clipes/girar_roda.glb), B toca girar_roda_b-loop (clipes/girar_roda_b.glb), cada GLB só
esqueleto + clipe, o que também prova que os clipes exportados servem no arquivo aprovado. Cada aldeão fica na
posição e no giro do seu posto, no espaço da roda; os dois são posicionados pela fase da roda (quadro = fase × 48),
sem inverter nem defasar. A roda gira −360° × fase em volta do seu +Z (glTF). A cena inteira é girada para o eixo
da roda ficar em X do mundo, como nos GIFs anteriores.
Mede em cada quadro a distância palma-manopla dos dois aldeões nesta cena (confere a transferência do clipe).
Material toon do prot_lib (Toon.gdshaderinc), luz do diagnóstico. Duas câmeras, fundo transparente:
  jogo: CameraRig no zoom 2,5 (aldeão ~112 px), 3024x1890 (recortado na montagem);
  lado: ortográfica de frente para a cena, 22° acima do chão, 640 px por metro (aldeão de 0,40 m = 256 px).
Saída: <pasta>/{jogo,lado}_NNN.png e <pasta>/medidas.json.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/prova_operacao/gif_roda.py -- <pasta> [subpasta_da_variante]
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "protagonista_v2"))
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
from prot_lib import ROOT, eevee_scene, game_camera, hex_linear, import_glb, render, toon_material  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SUB = ARGS[1] if len(ARGS) > 1 else ""
BASE = ROOT / "assets/modelos/prova_operacao" / SUB
REPORT = ROOT / "assets/previews/prova_operacao" / SUB / "girar_roda.json"
ALDEAO = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
CABELOS = ROOT / "assets/modelos/aldeao_v2/cabelos"
ROSTO = ROOT / "assets/modelos/aldeao_v2/rosto"
PELE, CABELO, MADEIRA = "#AEBFD3", "#6F7F96", "#4A3B3A"
SUN_EULER = Euler((math.radians(28), 0, math.radians(-20)))
SUN_RGB = tuple(c * 0.75 for c in (0.72, 0.78, 0.95))
AMBIENT_RGB = tuple(c * 0.6 for c in (0.36, 0.33, 0.44))
SIDE_PX_PER_M, SIDE_W, SIDE_H = 640, 640, 400
GAME_ZOOM = 2.5


def light_dir() -> Vector:
    return (SUN_EULER.to_matrix() @ Vector((0, 0, 1))).normalized()


def mat(name, color):
    return toon_material(name, light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(color))


def villager(root_matrix: Matrix, hair_n: int, skin, hair_mat, patches) -> tuple:
    objs = import_glb(ALDEAO)
    arm = next(o for o in objs if o.type == "ARMATURE")
    arm.animation_data_clear()
    arm.data.pose_position = "REST"
    for o in objs:
        if o.type == "MESH":
            o.data.materials.clear()
            o.data.materials.append(patches.get(o.name.split(".")[0], skin))
    root = bpy.data.objects.new("raiz", None)
    bpy.context.scene.collection.objects.link(root)
    arm.parent = root
    root.matrix_world = root_matrix
    bpy.context.view_layer.update()
    hair = [o for o in import_glb(CABELOS / f"cabelo_{hair_n}.glb") if o.type == "MESH"][0]
    hair.data.materials.clear()
    hair.data.materials.append(hair_mat)
    hair.matrix_world = root_matrix @ hair.matrix_world
    bpy.context.view_layer.update()
    world = hair.matrix_world.copy()
    hair.parent = arm
    hair.parent_type = "BONE"
    hair.parent_bone = "Head"
    bpy.context.view_layer.update()
    hair.matrix_world = world  # rígido no Head, na posição de repouso
    arm.data.pose_position = "POSE"
    return arm, root


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rep = json.loads(REPORT.read_text())
    clips = json.loads((BASE / "clipes.json").read_text())["girar_roda-loop"]
    frames, radius = clips["quadros"], clips["peca"]["raio_alca_m"]
    knob_y = rep["roda"]["knob_y_m"]
    grip_half = 0.018
    palm_len = {s: rep["esqueleto"]["comprimentos_m"][f"{s}Hand"] for s in ("Left", "Right")}

    scene = eevee_scene(transparent=True)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.render.fps = clips["fps"]
    skin, hair_mat, wood = mat("pele", PELE), mat("cabelo", CABELO), mat("madeira", MADEIRA)
    rosto = json.loads((ROSTO / "rosto.json").read_text())
    patches = {}
    for key, name in (("olhos", "Olhos"), ("boca", "Boca")):
        info = rosto[key]
        patches[name] = toon_material(f"rosto_{key}", light_dir(), SUN_RGB, AMBIENT_RGB,
                                      image=bpy.data.images.load(str(ROSTO / f"{key}.png")), cell=(0, info["colunas"], info["linhas"]))

    # Espaço da roda (glTF → Blender: x, −z, y): pivô no eixo, a h acima do chão (os postos ficam com os pés em y = −h).
    # Girado −90° em Z para o posto A olhar para +X, como antes.
    all_clips = json.loads((BASE / "clipes.json").read_text())
    h = -all_clips["girar_roda-loop"]["posto"]["posicao_m"][1]
    wheel_space = Matrix.Rotation(math.radians(-90), 4, "Z") @ Matrix.Translation((0, 0, h))

    def post_matrix(post: dict) -> Matrix:
        x, y, z = post["posicao_m"]
        # giro em torno do +Y do glTF = +Z do Blender; giro 0 = olhando +Z do glTF (−Y do Blender, a frente do GLB).
        return wheel_space @ Matrix.Translation((x, -z, y)) @ Matrix.Rotation(math.radians(post["giro_em_y_graus"]), 4, "Z")

    clip_info = {}
    arms = {}
    for key, hair_n in (("girar_roda-loop", 1), ("girar_roda_b-loop", 3)):
        spec = all_clips[key]
        arm, _ = villager(post_matrix(spec["posto"]), hair_n, skin, hair_mat, patches)
        before = set(bpy.data.actions)
        clip_objs = import_glb(BASE / spec["arquivo"])
        action = next(a for a in bpy.data.actions if a not in before and a.name.startswith(key))
        clip_info[key] = {"objetos": sorted({o.type for o in clip_objs}), "acao": action.name,
                          "posto": spec["posto"]["nome"], "quadros": spec["quadros"]}
        for o in clip_objs:
            bpy.data.objects.remove(o)
        arm.animation_data_create()
        arm.animation_data.action = action
        if getattr(action, "slots", None):
            arm.animation_data.action_slot = action.slots[0]
        arms[spec["posto"]["nome"]] = arm
    arm_a, arm_b = arms["A"], arms["B"]
    m_a, m_b = arm_a.parent.matrix_world, arm_b.parent.matrix_world

    wheel = [o for o in import_glb(BASE / "roda.glb") if o.type == "MESH"][0]
    wheel.data.materials.clear()
    wheel.data.materials.append(wood)
    wheel_base = wheel_space

    lat_a = (m_a.to_3x3() @ Vector((1, 0, 0))).normalized()
    lat_b = (m_b.to_3x3() @ Vector((1, 0, 0))).normalized()

    def palm(arm, side):
        pb = arm.pose.bones[f"{side}Hand"]
        s = arm.matrix_world.to_scale()[0]
        return arm.matrix_world @ pb.matrix @ Vector((0, palm_len[side] / s, 0))

    cam_game = game_camera(scene, GAME_ZOOM, Vector((0, 0, 0)))
    cam_side = bpy.data.objects.new("lado", bpy.data.cameras.new("lado"))
    scene.collection.objects.link(cam_side)
    cam_side.data.type = "ORTHO"
    cam_side.data.ortho_scale = SIDE_W / SIDE_PX_PER_M
    tilt = math.radians(22)
    tgt = Vector((0, 0, 0.2))
    cam_side.location = tgt + Vector((0, -math.cos(tilt), math.sin(tilt))) * 5
    cam_side.rotation_euler = (tgt - cam_side.location).to_track_quat("-Z", "Y").to_euler()

    rows = []
    for t in range(frames):
        p = t / frames
        scene.frame_set(t)  # os dois postos pela mesma fase: quadro = fase × 48 (a primeira chave, t = 0, é o quadro 0)
        wheel.matrix_world = wheel_base @ Matrix.Rotation(2 * math.pi * p, 4, "Y")  # −360° × fase em volta do +Z glTF
        bpy.context.view_layer.update()
        knob_a = wheel.matrix_world @ Vector((0, -knob_y, radius))
        knob_b = wheel.matrix_world @ Vector((0, knob_y, -radius))
        miss = {"A_esq": (palm(arm_a, "Left") - (knob_a + lat_a * grip_half)).length,
                "A_dir": (palm(arm_a, "Right") - (knob_a - lat_a * grip_half)).length,
                "B_esq": (palm(arm_b, "Left") - (knob_b + lat_b * grip_half)).length,
                "B_dir": (palm(arm_b, "Right") - (knob_b - lat_b * grip_half)).length}
        rows.append({k: round(v * 1000, 1) for k, v in miss.items()})
        scene.camera = cam_game
        scene.render.resolution_x, scene.render.resolution_y = 3024, 1890
        render(scene, OUT / f"jogo_{t:03d}.png")
        scene.camera = cam_side
        scene.render.resolution_x, scene.render.resolution_y = SIDE_W, SIDE_H
        render(scene, OUT / f"lado_{t:03d}.png")
    out = {"clipe_importado": clip_info, "falta_max_mm": {k: max(r[k] for r in rows) for k in rows[0]}, "por_quadro": rows,
           "zoom_jogo": GAME_ZOOM, "lado_px_por_m": SIDE_PX_PER_M}
    (OUT / "medidas.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print("MEDIDAS " + json.dumps({k: v for k, v in out.items() if k != "por_quadro"}, ensure_ascii=False))


main()

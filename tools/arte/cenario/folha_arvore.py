"""Renders da folha de contato da árvore piloto (a montagem é montar_folha.py).

Importa os GLBs exportados por arvore.py (como o jogo faria) e renderiza, com material fosco e a luz de crepúsculo
da ARTE (fria, de cima; corpo_lib.twilight_lights), no chão terra arroxeada:
  - cada variação sozinha, de frente e em 3/4 (ortográfica), com o aldeão v2 e a protagonista ao lado;
  - a fila das 4 com aldeão v2 (só corpo) e protagonista (bruto v2, 0,80 m) na câmera do jogo (CameraRig.cs: 55°, FOV 45°,
    16 m ÷ zoom, 3024×1890) nos zooms 0,4 / 1 / 2,5;
  - um bosque de 8 árvores misturadas (giro e escala sorteados, uma por célula) nos zooms 0,4 / 1 / 2,5;
  - personagem atrás da árvore (0,5, 1 e 2 m) no zoom 1, com a fração visível medida.
A copa leva a borda de luz fria (b), aprovada pelo Arthur em 29/09/2026 (aproximação; o Toon do jogo ainda não tem).
Recortes (caixa em pixels) e medidas vão em medidas.json na pasta de saída.

Uso: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/folha_arvore.py -- <saida>
"""

import json
import math
import random
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/arte/aldeao_v2"))
from corpo_lib import import_glb, setup_scene, twilight_lights  # noqa: E402  (ferramenta da ARTE, só uso)

OUT = Path(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else Path("/tmp/folha_arvore")
ARVORES = [ROOT / f"assets/cenario/arvore/arvore_{i}.glb" for i in range(1, 5)]
ALDEAO = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
# O repouso da v1 é torto (T deitado); o bruto v2 da Meshy (sem rig) vai escalado para os 0,80 m do contrato.
PROTAGONISTA = ROOT / "assets/modelos/protagonista_v2/meshy/corpo_b_multi_1.glb"
ALTURA_PROTAGONISTA = 0.80
W, H, FOV, PITCH, DIST = 3024, 1890, 45.0, 55.0, 16.0
CHAO = "#3F3342"  # terra arroxeada (GDD, seção 17)
PELE_ALDEAO = "#AEBFD3"
RIM_COR = tuple(c * 0.10 for c in (0.72, 0.78, 0.9))  # a cor do sol frio do Main.tscn, fraca
RIM_LARGURA = 0.25
PELE_PROTAGONISTA = "#91ADB7"  # cor provisória do visor


def linear(hex_color):
    out = []
    for i in (1, 3, 5):
        c = int(hex_color[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def fosco(nome, hex_color):
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = linear(hex_color)
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    return mat


def add_rim(mat):
    """Borda de luz fria em faixa dura (aproximação: nem o Toon do jogo nem o visor têm borda ainda)."""
    nt = mat.node_tree
    out = nt.nodes["Material Output"]
    surface = out.inputs["Surface"].links[0].from_node
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = RIM_LARGURA
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[1].position = 0.62
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*RIM_COR, 1.0)
    mix = nt.nodes.new("ShaderNodeMixShader")
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(lw.outputs["Facing"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emit.inputs["Strength"])
    nt.links.new(surface.outputs[0], add.inputs[0])
    nt.links.new(emit.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])


def place(path, location, yaw_deg=0.0, scale=1.0, color=None):
    """Importa um GLB e põe a raiz no lugar. Personagem fica em repouso e com a cor chapada da pele."""
    objs = import_glb(path)
    for o in objs:
        if o.type == "ARMATURE":
            o.data.pose_position = "REST"
            o.animation_data_clear()  # sem isso o primeiro clipe entra e o corpo deita
    bpy.context.view_layer.update()
    if color:
        mat = fosco(f"pele_{path.stem}", color)
        for o in objs:
            if o.type == "MESH":
                o.data.materials.clear()
                o.data.materials.append(mat)
    for o in objs:
        if o.type == "MESH":
            for p in o.data.polygons:
                if color:
                    p.use_smooth = True
    if path in ARVORES:  # borda fria (b), aprovada pelo Arthur: só na copa
        for m in {sl.material for o in objs if o.type == "MESH" for sl in o.material_slots}:
            if m and m.name.startswith("copa") and "rim" not in m:
                add_rim(m)
                m["rim"] = True
    for o in [o for o in objs if o.parent is None]:
        o.location = Vector(location)
        o.rotation_mode = "XYZ"
        o.rotation_euler.z += math.radians(yaw_deg)
        o.scale = o.scale * scale  # a raiz do GLB pode vir com escala própria
    if path == PROTAGONISTA:
        bpy.context.view_layer.update()
        pts = world_points(objs)
        k = ALTURA_PROTAGONISTA / (max(p.z for p in pts) - min(p.z for p in pts))
        for o in [o for o in objs if o.parent is None]:
            o.scale = o.scale * k
        bpy.context.view_layer.update()
        pts = world_points(objs)
        cx = (max(p.x for p in pts) + min(p.x for p in pts)) / 2
        cy = (max(p.y for p in pts) + min(p.y for p in pts)) / 2
        for o in [o for o in objs if o.parent is None]:
            o.location += Vector((location[0] - cx, location[1] - cy, -min(p.z for p in pts)))
        bpy.context.view_layer.update()
    return objs


def meshes(objs):
    return [o for o in objs if o.type == "MESH"]


def world_points(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes(objs):
        ev = o.evaluated_get(dg)
        m = ev.to_mesh()
        pts += [ev.matrix_world @ v.co for v in m.vertices]
        ev.to_mesh_clear()
    return pts


def height(objs):
    return max(p.z for p in world_points(objs)) - min(p.z for p in world_points(objs))


def game_camera(scene, target, zoom):
    cam = bpy.data.objects.new("cam_jogo", bpy.data.cameras.new("cam_jogo"))
    scene.collection.objects.link(cam)
    cam.data.type = "PERSP"
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle_y = math.radians(FOV)
    cam.data.clip_end = 300
    tilt = math.radians(PITCH)
    cam.location = Vector(target) + Vector((0, -math.cos(tilt), math.sin(tilt))) * (DIST / zoom)
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def ortho_camera(scene, target, azimuth_deg, elevation_deg, ortho):
    cam = bpy.data.objects.new("cam_orto", bpy.data.cameras.new("cam_orto"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    cam.data.clip_end = 100
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    # azimute 0 = de frente (Blender -Y, que é a frente +Z do glTF)
    offset = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * 20
    cam.location = Vector(target) + offset
    cam.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def pixel_box(scene, cam, objs, margin=24):
    xs, ys = [], []
    for p in world_points(objs):
        v = world_to_camera_view(scene, cam, p)
        xs.append(v.x * scene.render.resolution_x)
        ys.append((1 - v.y) * scene.render.resolution_y)
    return [max(int(min(xs)) - margin, 0), max(int(min(ys)) - margin, 0),
            min(int(max(xs)) + margin, scene.render.resolution_x),
            min(int(max(ys)) + margin, scene.render.resolution_y)]


def render(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"  {path.name}", flush=True)


def new_scene(resolution=(W, H), transparent=False):
    scene = setup_scene(1024, transparent)
    twilight_lights(scene)
    scene.render.resolution_x, scene.render.resolution_y = resolution
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "chao"
    ground.data.materials.append(fosco("chao", CHAO))
    return scene


def alpha_count(path):
    img = bpy.data.images.load(str(path))
    import numpy as np
    px = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(px)
    n = int((px[3::4] > 0.5).sum())
    bpy.data.images.remove(img)
    return n


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    medidas = {"recortes": {}, "atras": {}}

    # 1. Cada variação sozinha, frente e 3/4, aldeão ao lado.
    for i, glb in enumerate(ARVORES, start=1):
        for vista, az, el in (("frente", 0, 8), ("tres_quartos", 45, 25)):
            scene = new_scene((720, 720))
            place(glb, (0, 0, 0))
            place(ALDEAO, (0.85, -0.1, 0), color=PELE_ALDEAO)
            place(PROTAGONISTA, (1.3, -0.1, 0), color=PELE_PROTAGONISTA)
            ortho_camera(scene, (0.35, 0, 1.35), az, el, 3.2)
            render(scene, OUT / f"arvore_{i}_{vista}.png")

    # 2. Fila na câmera do jogo.
    scene = new_scene()
    fila = []
    for i, glb in enumerate(ARVORES):
        fila += place(glb, (-2.6 + 1.2 * i, 0, 0))
    aldeao = place(ALDEAO, (2.1, 0, 0), color=PELE_ALDEAO)
    prot = place(PROTAGONISTA, (2.75, 0, 0), color=PELE_PROTAGONISTA)
    medidas["altura_aldeao_m"] = round(height(aldeao), 3)
    medidas["altura_protagonista_m"] = round(height(prot), 3)
    for zoom in (0.4, 1.0, 2.5):
        cam = game_camera(scene, (0.1, 0, 0), zoom)
        box = pixel_box(scene, cam, fila + aldeao + prot, margin=int(30 * zoom))
        medidas["recortes"][f"fila_{zoom}"] = box
        medidas.setdefault("altura_px_aldeao", {})[str(zoom)] = pixel_box(scene, cam, aldeao, 0)
        render(scene, OUT / f"fila_zoom_{zoom}.png")
        bpy.data.objects.remove(cam)

    # 3. Bosque de 8, uma árvore por célula, variação/giro/escala sorteados (semente fixa).
    scene = new_scene()
    rng = random.Random(7)
    celulas = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (3, 1), (1, 2), (2, 2)]
    bosque = []
    ordem = [0, 0, 0, 1, 1, 3, 3, 2]  # líquen (3) só uma vez: destaque raro
    rng.shuffle(ordem)
    for (cx, cy), v in zip(celulas, ordem):
        bosque += place(ARVORES[v], (cx - 1.5, cy - 1.0, 0), rng.uniform(0, 360), rng.uniform(0.9, 1.1))
    bosque += place(ALDEAO, (1.6, -1.35, 0), color=PELE_ALDEAO)
    bosque += place(PROTAGONISTA, (-2.2, -1.1, 0), color=PELE_PROTAGONISTA)
    for zoom in (0.4, 1.0, 2.5):
        cam = game_camera(scene, (0.0, 0.3, 0), zoom)
        medidas["recortes"][f"bosque_{zoom}"] = pixel_box(scene, cam, bosque, margin=int(40 * zoom))
        render(scene, OUT / f"bosque_zoom_{zoom}.png")
        bpy.data.objects.remove(cam)

    # 4. Personagem atrás da árvore (mais longe da câmera = +Y no Blender): 0,5, 1 e 2 m.
    casos = [(n, g, c, arv, d) for n, g, c, arv in (("aldeao", ALDEAO, PELE_ALDEAO, 0),
                                                    ("protagonista", PROTAGONISTA, PELE_PROTAGONISTA, 3))
             for d in (0.5, 1.0, 2.0)]
    for nome, glb, cor, arv, dist in casos:
        chave = f"{nome}_atras_arvore_{arv + 1}_{dist}m"
        scene = new_scene()
        tree = place(ARVORES[arv], (0, 0, 0))
        char = place(glb, (0.05, dist, 0), color=cor)
        cam = game_camera(scene, (0, 0.6, 0), 1.0)
        medidas["recortes"][chave] = pixel_box(scene, cam, tree + char, margin=40)
        render(scene, OUT / f"{chave}.png")
        # Fração visível: só o personagem com alfa, chão e árvore recortando (holdout).
        scene.render.film_transparent = True
        hold = bpy.data.materials.new("holdout")
        hold.use_nodes = True
        nt = hold.node_tree
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        h = nt.nodes.new("ShaderNodeHoldout")
        nt.links.new(h.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
        others = [o for o in scene.objects if o.type == "MESH" and o not in char]
        for o in others:
            o.data.materials.clear()
            o.data.materials.append(hold)
        render(scene, OUT / f"_{chave}_visivel.png")
        for o in tree:
            o.hide_render = True
        render(scene, OUT / f"_{chave}_inteiro.png")
        vis, full = alpha_count(OUT / f"_{chave}_visivel.png"), alpha_count(OUT / f"_{chave}_inteiro.png")
        medidas["atras"][chave] = round(vis / full, 3) if full else None

    (OUT / "medidas.json").write_text(json.dumps(medidas, ensure_ascii=False, indent=2) + "\n")
    print("MEDIDAS " + json.dumps(medidas["atras"]))


main()

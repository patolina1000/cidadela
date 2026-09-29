"""Funções comuns dos scripts de Blender da protagonista v2: importar a v1 em repouso, regiões por osso, câmera
do jogo (CameraRig.cs) e material toon (Toon.gdshaderinc) feito com nós. Reaproveita o corpo_lib do aldeão v2.
Importado com sys.path apontando para esta pasta."""

import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
from corpo_lib import ROOT, import_glb, mesh_objects, mesh_points  # noqa: E402,F401

V1 = ROOT / "assets/modelos/protagonista/protagonista.glb"

# Regiões pelo osso de maior peso (nomes do rig da Meshy).
REGIONS = {
    "cabeca_cabelo": ("Head", "neck", "head_end", "headfront"),
    "tronco": ("Hips", "Spine", "Spine01", "Spine02"),
    "bracos_maos": ("LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
                    "RightShoulder", "RightArm", "RightForeArm", "RightHand"),
    "pernas_pes": ("LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
                   "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase"),
}
BONE_REGION = {b: r for r, bones in REGIONS.items() for b in bones}

# CameraRig.cs: pitch 55°, FOV vertical 45° (padrão da Camera3D), distância 16 m no zoom 1; tela 3024x1890.
GAME_W, GAME_H, GAME_FOV, GAME_PITCH, GAME_DIST = 3024, 1890, 45.0, 55.0, 16.0

# Toon.gdshaderinc
TOON_STEPS, TOON_FLOOR = 3, 0.35


def load_rest(path: Path) -> list:
    """Importa um GLB com o esqueleto em pose de repouso."""
    objects = import_glb(path)
    for obj in objects:
        if obj.type == "ARMATURE":
            obj.data.pose_position = "REST"
            obj.animation_data_clear()
    bpy.context.view_layer.update()
    return objects


def triangle_bones(obj) -> tuple:
    """Por triângulo: índice do material e osso de maior peso (soma dos pesos dos 3 vértices)."""
    names = [g.name for g in obj.vertex_groups]
    vw = np.zeros((len(obj.data.vertices), len(names)))
    for v in obj.data.vertices:
        for g in v.groups:
            vw[v.index, g.group] = g.weight
    obj.data.calc_loop_triangles()
    mats, bones = [], []
    for t in obj.data.loop_triangles:
        mats.append(t.material_index)
        bones.append(names[int(vw[list(t.vertices)].sum(axis=0).argmax())])
    return mats, bones


def region_vertices(obj, region: str) -> np.ndarray:
    """Vértices (mundo) cujo osso de maior peso está na região."""
    names = [g.name for g in obj.vertex_groups]
    out = []
    for v in obj.data.vertices:
        if not v.groups:
            continue
        g = max(v.groups, key=lambda g: g.weight)
        if BONE_REGION.get(names[g.group]) == region:
            out.append(obj.matrix_world @ v.co)
    return np.array([[p.x, p.y, p.z] for p in out])


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_linear(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)


def game_camera(scene, zoom: float, target=Vector((0, 0, 0))):
    """Câmera do jogo olhando o ponto no chão (onde o personagem está), de frente para ele (-Y do Blender)."""
    scene.render.resolution_x, scene.render.resolution_y = GAME_W, GAME_H
    cam = bpy.data.objects.new("camera_jogo", bpy.data.cameras.new("camera_jogo"))
    scene.collection.objects.link(cam)
    cam.data.type = "PERSP"
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle_y = math.radians(GAME_FOV)
    cam.data.clip_end = 200
    tilt = math.radians(GAME_PITCH)
    cam.location = target + Vector((0, -math.cos(tilt), math.sin(tilt))) * (GAME_DIST / zoom)
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def toon_material(name: str, light_dir: Vector, light_rgb, ambient_rgb, color=None, image=None, cell=None,
                  emission=None) -> bpy.types.Material:
    """Material emissivo que calcula a luz do Toon.gdshaderinc: meio-Lambert em 3 faixas com piso 0,35,
    vezes a cor da luz, mais o ambiente (a parte que o Godot soma fora da função light()).
    color: cor chapada (linear); image: textura (UV); cell=(índice, colunas, linhas) escolhe a célula de um
    atlas com alfa (retalhos do rosto); emission=(imagem, força) soma a emissão do cristal."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")

    geo = nodes.new("ShaderNodeNewGeometry")
    ldir = nodes.new("ShaderNodeCombineXYZ")
    ld = light_dir.normalized()
    ldir.inputs[0].default_value, ldir.inputs[1].default_value, ldir.inputs[2].default_value = ld.x, ld.y, ld.z
    dot = nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    links.new(geo.outputs["Normal"], dot.inputs[0])
    links.new(ldir.outputs[0], dot.inputs[1])

    def math_node(op, a, b=None, clamp=False):
        n = nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                links.new(v, n.inputs[i])
        return n.outputs[0]

    ndl = math_node("MULTIPLY_ADD", dot.outputs["Value"], 0.5)
    ndl.node.inputs[2].default_value = 0.5
    ndl = math_node("MINIMUM", math_node("MAXIMUM", ndl, 0.0), 1.0)
    band = math_node("DIVIDE", math_node("FLOOR", math_node("MULTIPLY", ndl, float(TOON_STEPS))), float(TOON_STEPS - 1))
    band = math_node("MINIMUM", band, 1.0)
    band = math_node("MULTIPLY_ADD", band, 1.0 - TOON_FLOOR)
    band.node.inputs[2].default_value = TOON_FLOOR

    # luz = cor_da_luz × faixa + ambiente
    lcol = nodes.new("ShaderNodeRGB")
    lcol.outputs[0].default_value = (*light_rgb, 1)
    acol = nodes.new("ShaderNodeRGB")
    acol.outputs[0].default_value = (*ambient_rgb, 1)
    scale = nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    links.new(lcol.outputs[0], scale.inputs[0])
    links.new(band, scale.inputs["Scale"])
    light = nodes.new("ShaderNodeVectorMath")
    light.operation = "ADD"
    links.new(scale.outputs[0], light.inputs[0])
    links.new(acol.outputs[0], light.inputs[1])

    alpha = None
    if image is not None:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Linear"
        if cell is not None:
            idx, cols, rows = cell
            tex.extension = "CLIP"
            mapping = nodes.new("ShaderNodeMapping")
            mapping.inputs["Scale"].default_value = (1 / cols, 1 / rows, 1)
            mapping.inputs["Location"].default_value = ((idx % cols) / cols, 1 - (idx // cols + 1) / rows, 0)
            coord = nodes.new("ShaderNodeTexCoord")
            links.new(coord.outputs["UV"], mapping.inputs["Vector"])
            links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
            alpha = tex.outputs["Alpha"]
        albedo = tex.outputs["Color"]
    else:
        rgb = nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = color
        albedo = rgb.outputs[0]

    lit = nodes.new("ShaderNodeVectorMath")
    lit.operation = "MULTIPLY"
    links.new(albedo, lit.inputs[0])
    links.new(light.outputs[0], lit.inputs[1])
    final = lit.outputs[0]
    if emission is not None:
        eimg, strength = emission
        etex = nodes.new("ShaderNodeTexImage")
        etex.image = eimg
        escale = nodes.new("ShaderNodeVectorMath")
        escale.operation = "SCALE"
        escale.inputs["Scale"].default_value = strength
        links.new(etex.outputs["Color"], escale.inputs[0])
        add = nodes.new("ShaderNodeVectorMath")
        add.operation = "ADD"
        links.new(final, add.inputs[0])
        links.new(escale.outputs[0], add.inputs[1])
        final = add.outputs[0]

    emit = nodes.new("ShaderNodeEmission")
    links.new(final, emit.inputs["Color"])
    if alpha is None:
        links.new(emit.outputs[0], out.inputs["Surface"])
    else:
        mix = nodes.new("ShaderNodeMixShader")
        transp = nodes.new("ShaderNodeBsdfTransparent")
        links.new(alpha, mix.inputs["Fac"])
        links.new(transp.outputs[0], mix.inputs[1])
        links.new(emit.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs["Surface"])
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
        else:
            mat.blend_method = "BLEND"
    return mat


def eevee_scene(transparent=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    scene.render.film_transparent = transparent
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("mundo")
    world.use_nodes = True
    scene.world = world
    return scene


def render(scene, path: Path) -> None:
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"  {path.name}", flush=True)

"""Funções comuns dos scripts de Blender do corpo do aldeão v2 (importar, medir a cabeça, lisura do rosto,
retalhos do rosto, cena de render). Importado com sys.path apontando para esta pasta."""

import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
HEIGHT_M = 0.40  # contrato
SKIN = (0.682, 0.749, 0.827, 1.0)  # #AEBFD3
GAME_TILT = 55
# Janelas dos retalhos, em fração da caixa da cabeça (de desenhar_rosto.py: cabeça 18..238 x 12..248, olhos
# 24..232 x 78..208, boca 110..174 x 170..202, no rosto de referência de 256 px). (x0, y0, x1, y1), y do topo.
EYES_FRAC = ((24 - 18) / 220, (78 - 12) / 236, (232 - 18) / 220, (208 - 12) / 236)
MOUTH_FRAC = ((110 - 18) / 220, (170 - 12) / 236, (174 - 18) / 220, (202 - 12) / 236)
ROSTO = ROOT / "assets/modelos/aldeao_v2/rosto"


def import_glb(path: Path) -> list:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), disable_bone_shape=True)
    return [o for o in bpy.data.objects if o not in before]


def mesh_objects(objects):
    return [o for o in objects if o.type == "MESH"]


def mesh_points(objects) -> np.ndarray:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in mesh_objects(objects):
        ev = obj.evaluated_get(depsgraph)
        m = ev.to_mesh()
        pts += [obj.matrix_world @ v.co for v in m.vertices]
        ev.to_mesh_clear()
    return np.array([[p.x, p.y, p.z] for p in pts])


def triangle_count(objects) -> int:
    total = 0
    for obj in mesh_objects(objects):
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
    return total


def head_box(pts: np.ndarray) -> dict:
    """Cabeça = tudo acima do pescoço; pescoço = fatia mais estreita (em x) entre 55% e 88% da altura."""
    low, high = pts.min(axis=0), pts.max(axis=0)
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


def window_rect(box: dict, frac, raise_frac=0.0) -> tuple:
    """Janela de um retalho no mundo: (x0, z_top, x1, z_bottom); raise_frac sobe a janela em fração da cabeça."""
    x0, x1 = box["x"]
    z0, z1 = box["z"]
    w, hh = x1 - x0, z1 - z0
    fx0, fy0, fx1, fy1 = frac
    return (x0 + fx0 * w, z1 - (fy0 - raise_frac) * hh, x0 + fx1 * w, z1 - (fy1 - raise_frac) * hh)


def ellipsoid_deviation(sel: np.ndarray) -> np.ndarray:
    """Distância (m, com sinal) de cada ponto a um elipsoide alinhado aos eixos ajustado por mínimos quadrados
    (A x² + B y² + C z² + D x + E y + F z = 1); distância aproximada por |f| / |grad f|."""
    x, y, z = sel[:, 0], sel[:, 1], sel[:, 2]
    M = np.c_[x * x, y * y, z * z, x, y, z]
    coef, *_ = np.linalg.lstsq(M, np.ones(len(sel)), rcond=None)
    A, B, C, D, E, F = coef
    f = M @ coef - 1
    grad = np.c_[2 * A * x + D, 2 * B * y + E, 2 * C * z + F]
    return f / np.maximum(np.linalg.norm(grad, axis=1), 1e-9)


def face_flatness(pts: np.ndarray, box: dict, raise_frac=0.0) -> dict:
    """Rugosidade da frente da cabeça (-y no Blender = +z do glTF) dentro das janelas: desvio, em mm, de um
    elipsoide ajustado (segue o ovo da cabeça e a curva dos lados; o que sobra é o amassado). Também o desvio
    de uma esfera ajustada, para comparar com medidas antigas."""
    ymid = (box["y"][0] + box["y"][1]) / 2
    out = {}
    for name, frac in (("olhos", EYES_FRAC), ("boca", MOUTH_FRAC)):
        x0, zt, x1, zb = window_rect(box, frac, raise_frac)
        sel = pts[(pts[:, 0] >= x0) & (pts[:, 0] <= x1) & (pts[:, 2] <= zt) & (pts[:, 2] >= zb) & (pts[:, 1] < ymid)]
        if len(sel) < 12:
            out[name] = {"pontos": int(len(sel))}
            continue
        dev = ellipsoid_deviation(sel)
        A = np.c_[2 * sel, np.ones(len(sel))]
        c, *_ = np.linalg.lstsq(A, (sel ** 2).sum(axis=1), rcond=None)
        center, r = c[:3], math.sqrt(c[3] + (c[:3] ** 2).sum())
        sdev = np.linalg.norm(sel - center, axis=1) - r
        out[name] = {"pontos": int(len(sel)), "rms_mm": round(float(np.sqrt((dev ** 2).mean()) * 1000), 2),
                     "max_mm": round(float(np.abs(dev).max() * 1000), 2), "esfera_raio_mm": round(r * 1000, 1),
                     "esfera_rms_mm": round(float(np.sqrt((sdev ** 2).mean()) * 1000), 2), "esfera_max_mm": round(float(np.abs(sdev).max() * 1000), 2)}
    return out


def flat_material(objects, color, name="pele", matte=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 1.0 if matte else 0.9
    if matte and "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    for obj in mesh_objects(objects):
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return mat


def set_smooth(objects, smooth=True):
    for obj in mesh_objects(objects):
        for p in obj.data.polygons:
            p.use_smooth = smooth


def twilight_lights(scene):
    """Luz do jogo (GDD, seção 17): crepúsculo frio vindo de cima, fraco, ambiente roxo-acinzentado."""
    for obj in [o for o in scene.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(obj)
    sun = bpy.data.objects.new("crepusculo", bpy.data.lights.new("crepusculo", "SUN"))
    sun.data.energy = 1.6
    sun.data.color = (0.72, 0.78, 0.95)
    sun.data.angle = math.radians(20)
    sun.rotation_euler = (math.radians(28), 0, math.radians(-20))  # quase de cima, um pouco da frente
    scene.collection.objects.link(sun)
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.36, 0.33, 0.44, 1)
    bg.inputs["Strength"].default_value = 0.55


def setup_scene(resolution=1024, transparent=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = resolution
    scene.render.film_transparent = transparent
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
    print(f"  {path.name}", flush=True)
    info = {"ortho": ortho, "alvo": list(target), "posicao": list(location)}
    bpy.data.objects.remove(cam)
    return info


def game_camera_offset(distance: float) -> Vector:
    tilt = math.radians(GAME_TILT)
    return Vector((0, -math.cos(tilt), math.sin(tilt))) * distance


# ---------- retalhos do rosto ----------

def face_patch(body_obj, name: str, rect, cols: int, rows: int, offset_m=0.0015, grid=(24, 12), phi_max_deg=None) -> bpy.types.Object:
    """Retalho curvo na frente da cabeça, afastado offset_m da pele, UV de 0 a 1 (o material escolhe a célula).
    Projeção cilíndrica em volta do eixo vertical da cabeça: cada linha da grade fica na altura z da janela e
    cada coluna num ângulo, de -phi_max a +phi_max, escolhido para que a corda corresponda à largura da janela.
    Assim toda coluna acha pele mesmo onde o ovo é mais estreito, e o retalho acompanha os lados da cabeça."""
    import bmesh
    x0, zt, x1, zb = rect
    depsgraph = bpy.context.evaluated_depsgraph_get()
    inv = body_obj.matrix_world.inverted()
    coords = np.array([v.co[:] for v in body_obj.data.vertices])
    head = coords[coords[:, 2] >= zb - 0.02]
    yc = float((head[:, 1].min() + head[:, 1].max()) / 2)
    band = head[np.abs(head[:, 2] - (zt + zb) / 2) < 0.01]
    r_mid = float(band[:, 0].max() - band[:, 0].min()) / 2 if len(band) else float(head[:, 0].max() - head[:, 0].min()) / 2
    if phi_max_deg is not None:
        # Janela pela corda do ângulo pedido; a altura segue a proporção da célula, centrada na janela dada.
        phi_max = math.radians(phi_max_deg)
        aspect = (x1 - x0) / (zt - zb)
        half_w = r_mid * math.sin(phi_max)
        zc = (zt + zb) / 2
        x0, x1 = (x0 + x1) / 2 - half_w, (x0 + x1) / 2 + half_w
        zt, zb = zc + half_w / aspect, zc - half_w / aspect
    else:
        phi_max = math.asin(min(0.995, (x1 - x0) / 2 / r_mid))
    nx, nz = grid
    bm = bmesh.new()
    verts = []
    for j in range(nz + 1):
        z = zt - (zt - zb) * j / nz
        row = []
        for i in range(nx + 1):
            phi = phi_max * (2 * i / nx - 1)
            origin = Vector(((x0 + x1) / 2, yc, z))
            direction = Vector((math.sin(phi), -math.cos(phi), 0))
            hit, loc, normal, _ = body_obj.ray_cast(inv @ origin, (inv.to_3x3() @ direction).normalized(), depsgraph=depsgraph)
            if not hit:
                raise RuntimeError(f"{name}: o raio na linha z={z:.3f}, ângulo {math.degrees(phi):.0f}°, não achou a pele")
            world = body_obj.matrix_world @ loc
            n = (body_obj.matrix_world.to_3x3() @ normal).normalized()
            if n.dot(direction) < 0:
                n = -n
            row.append(bm.verts.new(world + n * offset_m))
        verts.append(row)
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for j in range(nz):
        for i in range(nx):
            f = bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
            for loop, (di, dj) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                loop[uv_layer].uv = ((i + di) / nx, 1 - (j + dj) / nz)
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:  # normais para a frente (-Y)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for p in mesh.polygons:
        p.use_smooth = True
    obj["phi_max_graus"] = math.degrees(phi_max)
    obj["janela"] = [x0, zt, x1, zb]
    return obj


def patch_material(name: str, image_path: Path, cols: int, rows: int, lit=False):
    """Material com o atlas: célula escolhida pelo nó Mapping (set_cell). lit=False: emissão (sem luz);
    lit=True: difuso fosco, recebe a mesma luz do corpo."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    mix = nodes.new("ShaderNodeMixShader")
    transp = nodes.new("ShaderNodeBsdfTransparent")
    if lit:
        emit = nodes.new("ShaderNodeBsdfDiffuse")
        emit.inputs["Roughness"].default_value = 1.0
        emit.outputs["BSDF"].name = "BSDF"
    else:
        emit = nodes.new("ShaderNodeEmission")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(image_path))
    tex.interpolation = "Linear"
    tex.extension = "CLIP"
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1 / cols, 1 / rows, 1)
    coord = nodes.new("ShaderNodeTexCoord")
    links.new(coord.outputs["UV"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], emit.inputs["Color"])
    links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    links.new(transp.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs[0], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    else:
        mat.blend_method = "BLEND"
    mat.use_backface_culling = True
    mat["mapping"] = mapping.name
    return mat


def set_cell(mat, index: int, cols: int, rows: int):
    mapping = mat.node_tree.nodes[mat["mapping"]]
    col, row = index % cols, index // cols
    mapping.inputs["Location"].default_value = (col / cols, 1 - (row + 1) / rows, 0)


def load_rosto() -> dict:
    return json.loads((ROSTO / "rosto.json").read_text())

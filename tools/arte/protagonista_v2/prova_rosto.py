"""Protagonista v2, passo 4: prova do rosto no corpo limpo, ANTES do rig (Blender headless).

Para cada variação do estudo_rosto.py: retalhos "Olhos" e "Boca" como no aldeão (corpo_lib.face_patch): curvos, a
2 mm da pele, cilíndricos em volta do eixo da cabeça; olhos até ±45° e na janela 10% mais alta, boca na janela padrão;
UV 0..1 na célula única do estudo. Material toon com alfa misturado (o mesmo Toon.gdshaderinc da pele, como o
VillagerFace.gdshader); pele #91ADB7, tecido #3F3342, luz do render_meshy.py. O peso 100% no Head fica para o rig.
Vistas: frente e 3/4 ortográficas com o aldeão v2 ao lado, close da cabeça (frente e 3/4) e câmera do jogo
(CameraRig.cs) nos zooms 0,4 / 1 / 2,5 em 3024×1890.

Rodada 2: variações podem trazer "boca_sobe" (a janela da boca sobe essa fração da cabeça) e "queixo" (< 1: a parte
de baixo da cabeça, do queixo até o meio do rosto, encolhe nesse fator e a cabeça volta a 18% da altura, escalada a
partir da base do pescoço, e a figura a 0,80 m; só na memória, nenhum GLB é salvo). Com --v1, renderiza também a v1
texturizada (como no jogo) nas mesmas vistas, como referência de rosto.

Uso:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/arte/protagonista_v2/prova_rosto.py -- <pasta> [<pasta_do_estudo>] [--v1]
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "aldeao_v2"))
from corpo_lib import EYES_FRAC, MOUTH_FRAC, face_patch, head_box, window_rect  # noqa: E402
from prot_lib import GAME_H, GAME_W, ROOT, V1, eevee_scene, game_camera, hex_linear, import_glb, load_rest, mesh_objects, mesh_points, render, toon_material  # noqa: E402,E501
from render_estudo_cabeca import pbr_lights  # noqa: E402
from render_meshy import AMBIENT_RGB, SUN_RGB, camera_right, light_dir, load_villager, ortho_camera, projected, root_of  # noqa: E402

BODY = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpo.glb"
CLEAN = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpeza.json"
STUDY_MARKS = ROOT / "assets/previews/protagonista_v2/estudo_cabeca.json"
HEIGHT, HEAD_RATIO = 0.80, 0.18
STUDY = ROOT / "assets/previews/protagonista_v2/rosto_estudo"
COLORS = {"pele": "#91ADB7", "tecido": "#3F3342"}
OFFSET = 0.002
RAISE = 0.10
PHI_MAX = 45
ZOOMS = (0.4, 1.0, 2.5)
SIDE_M = 0.45


def shorten_chin(objects, factor):
    """Encolhe a parte de baixo da cabeça (do queixo até o meio do rosto) no fator e devolve a cabeça a 18% da altura,
    escalando a partir da base do pescoço, e a figura a 0,80 m. Mexe nos vértices de todas as peças (continuidade)."""
    clean = json.loads(CLEAN.read_text())
    marks = json.loads(STUDY_MARKS.read_text())["marcos_bruto_b"]
    chin = clean["cabeca"]["queixo_z"]
    base = marks["base_pescoco_z"] * clean["cabeca"]["escala_do_corpo_k"]
    top = max(float(mesh_points(objects)[:, 2].max()), 1e-6)
    mid = chin + 0.45 * (top - chin)
    meshes = mesh_objects(objects)
    coords = {o.name: np.array([v.co[:] for v in o.data.vertices]) for o in meshes}
    new_chin = mid - (mid - chin) * factor
    s = HEAD_RATIO * base / ((top - new_chin) - HEAD_RATIO * (top - base))
    for o in meshes:
        p = coords[o.name].copy()
        w = np.clip((p[:, 2] - (chin - 0.015)) / 0.015, 0, 1) * (p[:, 2] < mid)
        p[:, 2] = np.where(w > 0, p[:, 2] + w * ((mid - (mid - p[:, 2]) * factor) - p[:, 2]), p[:, 2])
        above = p[:, 2] >= base
        pivot = np.array([0.0, float(p[above, 1].mean()) if above.any() else 0.0, base])
        p[above] = pivot + (p[above] - pivot) * s
        coords[o.name] = p
    k = HEIGHT / max(c[:, 2].max() for c in coords.values())
    for o in meshes:
        o.data.vertices.foreach_set("co", (coords[o.name] * k).ravel())
        o.data.update()
    chin_final = (base + s * (new_chin - base)) * k
    return {"queixo_antes_z": round(chin, 4), "queixo_depois_z": round(chin_final, 4), "fator_queixo": factor,
            "fator_cabeca": round(s, 4), "escala_figura": round(k, 4),
            "cabeca_sobre_altura": round((HEIGHT - chin_final) / HEIGHT, 4)}


def shoot_set(scene, prefix, prot_objects, vroot, box, out, v):
    """Frente e 3/4 com o aldeão, close da cabeça, e a câmera do jogo nos três zooms (medidas em v)."""
    for view, d in (("frente", Vector((0, -1, 0))), ("tres_quartos", Vector((1, -1, 0)))):
        scene.render.resolution_x = scene.render.resolution_y = 1024
        cam = ortho_camera(scene, d, Vector((0, 0, 0)), 1.0)
        right = camera_right(cam)
        vroot.location = right * SIDE_M
        bpy.context.view_layer.update()
        cam.location = right * (SIDE_M / 2) + Vector((0, 0, 0.46)) + d.normalized() * 10
        bpy.context.view_layer.update()
        render(scene, out / f"{prefix}_{view}.png")
        bpy.data.objects.remove(cam)
        cz = (box["z"][0] + box["z"][1]) / 2
        cam = ortho_camera(scene, d, Vector((0, 0, cz)), max(0.2, 1.25 * (box["z"][1] - box["z"][0])))
        render(scene, out / f"{prefix}_cabeca_{view}.png")
        bpy.data.objects.remove(cam)
    vroot.location = (SIDE_M, 0, 0)
    bpy.context.view_layer.update()
    pts = mesh_points(prot_objects)
    vpts = mesh_points([o for o in vroot.children_recursive if o.type == "MESH"])
    for zoom in ZOOMS:
        cam = game_camera(scene, zoom)
        bpy.context.view_layer.update()
        pp, vp = projected(scene, cam, pts), projected(scene, cam, vpts)
        both = np.vstack([pp, vp])
        hp = projected(scene, cam, pts[(pts[:, 2] >= box["z"][0]) & (np.abs(pts[:, 0]) < 0.12)])  # sem os braços (v1 em pose T)
        v["jogo"][str(zoom)] = {
            "protagonista_px": round(float(pp[:, 1].max() - pp[:, 1].min()), 1),
            "cabeca_px": [round(float(hp[:, 0].max() - hp[:, 0].min()), 1), round(float(hp[:, 1].max() - hp[:, 1].min()), 1)],
            "caixa_px": [float(both[:, 0].min()), float(both[:, 1].min()), float(both[:, 0].max()), float(both[:, 1].max())],
            "cabeca_caixa_px": [float(hp[:, 0].min()), float(hp[:, 1].min()), float(hp[:, 0].max()), float(hp[:, 1].max())],
            "tela": [GAME_W, GAME_H]}
        render(scene, out / f"{prefix}_jogo_{zoom}.png")
        bpy.data.objects.remove(cam)


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:]
    with_v1 = "--v1" in args
    args = [a for a in args if a != "--v1"]
    out = Path(args[0])
    study = Path(args[1]).resolve() if len(args) > 1 else STUDY
    out.mkdir(parents=True, exist_ok=True)
    variants = json.loads((study / "variacoes.json").read_text())
    info = {"estudo": str(study.relative_to(ROOT)), "variacoes": {}}

    for name, spec in variants.items():
        scene = eevee_scene(transparent=True)
        scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
        prot = import_glb(BODY)
        mats = {k: toon_material(k, light_dir(), SUN_RGB, AMBIENT_RGB, color=hex_linear(c)) for k, c in COLORS.items()}
        for obj in mesh_objects(prot):
            m = obj.data.materials[0].name.split(".")[0] if obj.data.materials else "pele"
            obj.data.materials.clear()
            obj.data.materials.append(mats.get(m, mats["pele"]))
        root_of(prot, "protagonista")
        vill, vroot = load_villager()
        v = {"jogo": {}}
        if spec.get("queixo", 1.0) < 1.0:
            v["queixo"] = shorten_chin(prot, spec["queixo"])
        bpy.context.view_layer.update()
        head_obj = next(o for o in mesh_objects(prot) if o.name.split(".")[0] == "cabeca")
        box = head_box(mesh_points(prot))
        eyes = face_patch(head_obj, "Olhos", window_rect(box, EYES_FRAC, RAISE), 1, 1, OFFSET, grid=(32, 20), phi_max_deg=PHI_MAX)
        mouth = face_patch(head_obj, "Boca", window_rect(box, MOUTH_FRAC, spec.get("boca_sobe", 0.0)), 1, 1, OFFSET, grid=(16, 8))
        for patch, key in ((eyes, "olhos"), (mouth, "boca")):
            img = bpy.data.images.load(str(study / f"{name}_{key}.png"))
            patch.data.materials.append(toon_material(f"rosto_{key}_{name}", light_dir(), SUN_RGB, AMBIENT_RGB, image=img,
                                                      cell=(0, 1, 1)))
        chin = v.get("queixo", {}).get("queixo_depois_z") or json.loads(CLEAN.read_text())["cabeca"]["queixo_z"]
        v.update({"janela_olhos": list(eyes["janela"]), "janela_boca": list(mouth["janela"]), "cabeca": box,
                  "cabeca_largura_sobre_altura": round((box["x"][1] - box["x"][0]) / (box["z"][1] - chin), 3)})
        shoot_set(scene, name, prot, vroot, box, out, v)
        info["variacoes"][name] = v
        print("VAR " + name + " " + json.dumps({z: j["cabeca_px"] for z, j in v["jogo"].items()}), flush=True)

    if with_v1:  # a v1 como estava no jogo: textura e luz de verdade (diagnostico_v1 / render_estudo_cabeca)
        scene = eevee_scene(transparent=True)
        pbr_lights(scene)
        v1 = load_rest(V1)
        root_of(v1, "v1")
        vill, vroot = load_villager()
        bpy.context.view_layer.update()
        box = head_box(mesh_points(v1))
        v = {"jogo": {}, "cabeca": box}
        shoot_set(scene, "v1", v1, vroot, box, out, v)
        info["v1"] = v
    (out / "prova.json").write_text(json.dumps(info, indent=2) + "\n")


main()

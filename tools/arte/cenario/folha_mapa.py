"""Pedaço de mapa antes e depois de um ajuste de pedra e veio, com o brilho medido de cada grupo.

Renderiza o mesmo mapa de folha_cenario.build_mapa duas vezes (GLBs de pedra e veio "antes", guardados numa pasta,
e os atuais de assets/cenario) nos zooms 0,4 / 1 / 2,5. Depois, no zoom 1, mede o brilho médio do que aparece de
cada grupo (pedra, veio, árvore, aldeão, protagonista): o resto do mapa vira holdout e conta só o pixel visível.
Brilho = luma Rec. 709 do sRGB da tela (0–255), média e percentil 95 (o topo mais claro), com a borda fria
incluída, como o jogador vê.

Uso: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/folha_mapa.py -- <saida> <pasta_antes>
A montagem é montar_folha_mapa.py.
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_cenario import MAPA_ALVO, PEDRAS, VEIOS, build_mapa  # noqa: E402
from folha_arvore import game_camera, new_scene, pixel_box, render  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT, ANTES = Path(ARGS[0]), Path(ARGS[1])
CONJUNTOS = {
    "antes": ([ANTES / f"pedra_{i}.glb" for i in range(1, 5)], [ANTES / f"veio_{i}.glb" for i in range(1, 5)]),
    "depois": (PEDRAS, VEIOS),
}


def holdout_material():
    mat = bpy.data.materials.new("holdout")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    h = nt.nodes.new("ShaderNodeHoldout")
    nt.links.new(h.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return mat


def luma(path):
    img = bpy.data.images.load(str(path))
    px = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    px = px.reshape(-1, 4)
    vis = px[px[:, 3] > 0.9]
    if not len(vis):
        return None
    # PNG de 8 bits: o Blender devolve os valores já em sRGB, como estão no arquivo
    y = vis[:, :3] @ np.array([0.2126, 0.7152, 0.0722]) * 255
    return {"media": round(float(y.mean()), 1), "p95": round(float(np.percentile(y, 95)), 1)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    medidas = {"recortes": {}, "brilho": {}}
    for nome, (pedras, veios) in CONJUNTOS.items():
        scene = new_scene()
        grupos = build_mapa(pedras, veios)
        todos = sum(grupos.values(), [])
        for zoom in (0.4, 1.0, 2.5):
            cam = game_camera(scene, MAPA_ALVO, zoom)
            medidas["recortes"][f"mapa_{zoom}"] = pixel_box(scene, cam, todos, margin=int(40 * zoom))
            render(scene, OUT / f"mapa_{nome}_zoom_{zoom}.png")
            bpy.data.objects.remove(cam)
        medidas["brilho"][nome] = {}
        for grupo in grupos:
            scene = new_scene()
            g = build_mapa(pedras, veios)
            scene.render.film_transparent = True
            hold = holdout_material()
            keep = set(g[grupo])
            for o in scene.objects:
                if o.type == "MESH" and o not in keep:
                    o.data.materials.clear()
                    o.data.materials.append(hold)
            cam = game_camera(scene, MAPA_ALVO, 1.0)
            path = OUT / f"_brilho_{nome}_{grupo}.png"
            render(scene, path)
            medidas["brilho"][nome][grupo] = luma(path)
    (OUT / "medidas.json").write_text(json.dumps(medidas, ensure_ascii=False, indent=2) + "\n")
    print("BRILHO " + json.dumps(medidas["brilho"]))


main()

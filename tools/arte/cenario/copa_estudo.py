"""Estudo (tarefa 9): alternativas sem borda fria para a copa não sumir no crepúsculo. Só renders: os GLBs não mudam.

O mesmo pedaço de mapa de folha_cenario.build_mapa, com a copa SEM borda (pedra e veio mantêm a deles), em 4 versões
aplicadas só na hora do render:
  0  atual sem borda;
  A  tronco terra #4A3B3A em todas as árvores (hoje duas usam lama #2E2931 e uma terra arroxeada #3F3342);
  B  A + duas cores por árvore: a massa de cima da copa em grama morta #5A5847 (a de baixo segue musgo #4E5544);
     na alta, que tem uma massa só, a parte de cima (a ponta dobrada); os tufos (líquen) ficam como estão;
  C  B + contorno fino escuro (#1B1620, traço do GDD) nas árvores, por casca invertida de 1,2 cm: APROXIMAÇÃO do
     contorno que o toon do jogo ainda não tem.
Zooms 1 e 2,5 da câmera do jogo; a montagem (com o crepúsculo) é montar_copa_estudo.py.

Uso: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/copa_estudo.py -- <saida>
"""

import json
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import folha_arvore  # noqa: E402
from folha_arvore import fosco, game_camera, linear, new_scene, pixel_box, render  # noqa: E402
from folha_cenario import MAPA_ALVO, PEDRAS, VEIOS, build_mapa  # noqa: E402

OUT = Path(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else Path("/tmp/copa_estudo")
TRONCO = "#4A3B3A"
COPA_CIMA = "#5A5847"
MUSGO = "#4E5544"
TRACO = "#1B1620"
CONTORNO_M = 0.012
VERSOES = ("0", "A", "B", "C")


def is_musgo(mat):
    c = mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
    return abs(c[1] - linear(MUSGO)[1]) < 0.01 and abs(c[0] - linear(MUSGO)[0]) < 0.01


def islands(bm, faces):
    """Massas da copa: grupos de faces ligadas por vértices na mesma posição (o GLB separa vértices por normal)."""
    parent = {}

    def find(k):
        while parent.setdefault(k, k) != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    key = lambda v: (round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4))
    for f in faces:
        ks = [key(v) for v in f.verts]
        for k in ks[1:]:
            parent[find(k)] = find(ks[0])
    groups = {}
    for f in faces:
        groups.setdefault(find(key(f.verts[0])), []).append(f)
    return list(groups.values())


def two_tone(obj, cima):
    """Pinta a massa de cima da copa (musgo) com a cor clara; numa copa de massa só, a metade de cima."""
    slots = [i for i, s in enumerate(obj.material_slots) if s.material and s.material.name.startswith("copa")
             and is_musgo(s.material)]
    if not slots:
        return
    obj.data.materials.append(cima)
    idx = len(obj.data.materials) - 1
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    faces = [f for f in bm.faces if f.material_index in slots]
    groups = islands(bm, faces)
    if len(groups) > 1:
        top = max(groups, key=lambda g: max(v.co.z for f in g for v in f.verts))
    else:
        zs = [v.co.z for f in faces for v in f.verts]
        cut = min(zs) + 0.55 * (max(zs) - min(zs))
        top = [f for f in faces if f.calc_center_median().z > cut]
    for f in top:
        f.material_index = idx
    bm.to_mesh(obj.data)
    bm.free()


def outline(obj, traco):
    """Casca invertida: cópia inflada com as normais viradas e só a face de trás visível (contorno aproximado)."""
    obj.data.materials.append(traco)
    mod = obj.modifiers.new("contorno", "SOLIDIFY")
    mod.thickness = CONTORNO_M
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.material_offset = len(obj.data.materials) - 1


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    folha_arvore.COPA_RIM = False  # a copa sem borda é o ponto de partida (tarefa 8)
    medidas = {"recortes": {}}
    for versao in VERSOES:
        scene = new_scene()
        grupos = build_mapa(PEDRAS, VEIOS)
        arvores = [o for o in grupos["arvore"] if o.type == "MESH"]
        if versao in "ABC":
            for o in arvores:
                for s in o.material_slots:
                    if s.material and s.material.name.startswith("tronco"):
                        s.material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = \
                            linear(TRONCO)
        if versao in "BC":
            cima = fosco("copa_cima", COPA_CIMA)
            for o in arvores:
                two_tone(o, cima)
        if versao == "C":
            traco = fosco("traco", TRACO)
            traco.use_backface_culling = True
            for o in arvores:
                outline(o, traco)
        todos = sum(grupos.values(), [])
        for zoom in (1.0, 2.5):
            cam = game_camera(scene, MAPA_ALVO, zoom)
            if versao == "0":
                medidas["recortes"][f"mapa_{zoom}"] = pixel_box(scene, cam, todos, margin=int(40 * zoom))
            render(scene, OUT / f"copa_{versao}_zoom_{zoom}.png")
            bpy.data.objects.remove(cam)
    (OUT / "medidas.json").write_text(json.dumps(medidas, ensure_ascii=False, indent=2) + "\n")


main()

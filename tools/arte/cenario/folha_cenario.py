"""Renders da folha de contato conjunta do cenário: pedra e veio de ferro, e as três famílias juntas.

Mesma luz, chão, câmera e personagens da folha da árvore (as peças vêm de folha_arvore.py). A borda de luz fria
(b), aprovada pelo Arthur, vai na copa das árvores e em todos os materiais de pedra e veio.
  - cada pedra e cada veio sozinhos, de frente e em 3/4 (ortográfica), com o aldeão ao lado;
  - as três famílias lado a lado em 3/4 (árvore, pedra, veio, aldeão, protagonista);
  - a fila de pedras e veios na câmera do jogo nos zooms 0,4 / 1 / 2,5;
  - um pedaço de mapa misturado (bosque com pedras e uma mancha de veios) nos zooms 0,4 / 1 / 2,5.
A montagem é montar_folha_cenario.py.

Uso: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/folha_cenario.py -- <saida>
"""

import json
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_arvore import (ALDEAO, ARVORES, PELE_ALDEAO, PELE_PROTAGONISTA, PROTAGONISTA, ROOT,  # noqa: E402
                          add_rim, game_camera, ortho_camera, pixel_box, place, render, new_scene)

OUT = Path(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else Path("/tmp/folha_cenario")
PEDRAS = [ROOT / f"assets/cenario/pedra/pedra_{i}.glb" for i in range(1, 5)]
VEIOS = [ROOT / f"assets/cenario/veio/veio_{i}.glb" for i in range(1, 5)]
PESO_ARVORE = [0.3, 0.3, 0.1, 0.3]  # gota, dupla, tufos (líquen), alta


def put(path, location, yaw=0.0, scale=1.0):
    """Objeto do cenário; pedra e veio levam a borda fria em todos os materiais (a árvore, só na copa)."""
    objs = place(path, location, yaw, scale)
    if path not in ARVORES:
        for m in {s.material for o in objs if o.type == "MESH" for s in o.material_slots}:
            if m and "rim" not in m:
                add_rim(m)
                m["rim"] = True
    return objs


MAPA_ALVO = (0.3, 0.3, 0)


def build_mapa(pedras_glb, veios_glb):
    """Pedaço de mapa de 7×5 células na cena atual; devolve os objetos por grupo (para medir o brilho de cada um)."""
    rng = random.Random(17)
    g = {"arvore": [], "pedra": [], "veio": [], "aldeao": [], "protagonista": []}
    arvores = [(0, 0), (1, 0), (3, 0), (0, 1), (2, 1), (4, 1), (1, 2), (3, 3), (5, 0), (6, 2)]
    pedras = [(2, 0), (4, 0), (5, 2), (0, 3)]
    veios = [(4, 3), (5, 3), (5, 4), (6, 4)]
    for cx, cy in arvores:
        v = rng.choices(range(4), PESO_ARVORE)[0]
        g["arvore"] += put(ARVORES[v], (cx - 3, cy - 1.5, 0), rng.uniform(0, 360), rng.uniform(0.9, 1.1))
    for k, (cx, cy) in enumerate(pedras):
        g["pedra"] += put(pedras_glb[k % 4], (cx - 3, cy - 1.5, 0), rng.uniform(0, 360), rng.uniform(0.9, 1.1))
    for k, (cx, cy) in enumerate(veios):
        g["veio"] += put(veios_glb[k % 4], (cx - 3, cy - 1.5, 0), rng.uniform(0, 360), rng.uniform(0.9, 1.1))
    # personagens na frente (lado da câmera), para não sumirem atrás das copas
    g["aldeao"] += place(ALDEAO, (-1.4, -2.1, 0), color=PELE_ALDEAO)
    g["protagonista"] += place(PROTAGONISTA, (1.8, -2.0, 0), color=PELE_PROTAGONISTA)
    return g


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    medidas = {"recortes": {}}

    # 1. Cada pedra e veio sozinhos.
    for familia, lista in (("pedra", PEDRAS), ("veio", VEIOS)):
        for i, glb in enumerate(lista, start=1):
            for vista, az, el in (("frente", 0, 12), ("tres_quartos", 45, 35)):
                scene = new_scene((600, 600))
                put(glb, (0, 0, 0))
                place(ALDEAO, (0.55, -0.05, 0), color=PELE_ALDEAO)
                ortho_camera(scene, (0.17, 0, 0.26), az, el, 1.35)
                render(scene, OUT / f"{familia}_{i}_{vista}.png")

    # 2. As três famílias juntas, em 3/4.
    scene = new_scene((1800, 1100))
    put(ARVORES[0], (-1.0, 0, 0))
    put(PEDRAS[0], (0.1, 0, 0))
    put(VEIOS[0], (0.85, 0, 0))
    place(ALDEAO, (1.5, 0, 0), color=PELE_ALDEAO)
    place(PROTAGONISTA, (2.0, 0, 0), color=PELE_PROTAGONISTA)
    ortho_camera(scene, (0.45, 0, 1.35), 30, 20, 5.2)
    render(scene, OUT / "familias.png")

    # 3. Fila de pedras e veios na câmera do jogo, uma por célula.
    scene = new_scene()
    fila = []
    for i, glb in enumerate(PEDRAS + VEIOS):
        fila += put(glb, (-3.5 + i, 0, 0))
    fila += place(ALDEAO, (4.6, 0, 0), color=PELE_ALDEAO)
    fila += place(PROTAGONISTA, (5.2, 0, 0), color=PELE_PROTAGONISTA)
    for zoom in (0.4, 1.0, 2.5):
        cam = game_camera(scene, (0.85, 0, 0), zoom)
        medidas["recortes"][f"fila_{zoom}"] = pixel_box(scene, cam, fila, margin=int(30 * zoom))
        render(scene, OUT / f"fila_zoom_{zoom}.png")
        bpy.data.objects.remove(cam)

    # 4. Pedaço de mapa: bosque (sorteio 30/30/10/30), pedras soltas e uma mancha de 4 veios juntos.
    scene = new_scene()
    mapa = sum(build_mapa(PEDRAS, VEIOS).values(), [])
    for zoom in (0.4, 1.0, 2.5):
        cam = game_camera(scene, MAPA_ALVO, zoom)
        medidas["recortes"][f"mapa_{zoom}"] = pixel_box(scene, cam, mapa, margin=int(40 * zoom))
        render(scene, OUT / f"mapa_zoom_{zoom}.png")
        bpy.data.objects.remove(cam)

    (OUT / "medidas.json").write_text(json.dumps(medidas, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":  # folha_mapa.py importa build_mapa daqui
    main()

"""Renders da folha "quando o recurso esgota" (opções para o Arthur decidir, tarefa 5).

  - cada toco (toco.py) e cada mancha (mancha.py) sozinhos, de frente e em 3/4, com o aldeão ao lado;
  - o mesmo pedaço de mapa de folha_cenario.build_mapa em três estados: tudo vivo, "depois da coleta: some tudo" e
    "depois da coleta: tocos e manchas", nos zooms 0,4 / 1 / 2,5.
A montagem é montar_folha_esgotado.py.

Uso: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/arte/cenario/folha_esgotado.py -- <saida>
"""

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_cenario import MANCHAS, MAPA_ALVO, PEDRAS, TOCOS, VEIOS, build_mapa, put  # noqa: E402
from folha_arvore import ALDEAO, PELE_ALDEAO, game_camera, new_scene, ortho_camera, pixel_box, place, render  # noqa: E402

OUT = Path(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else Path("/tmp/folha_esgotado")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    medidas = {"recortes": {}}
    for familia, lista in (("toco", TOCOS), ("mancha", MANCHAS)):
        for i, glb in enumerate(lista, start=1):
            for vista, az, el in (("frente", 0, 15), ("tres_quartos", 45, 40)):
                scene = new_scene((500, 500))
                put(glb, (0, 0, 0))
                place(ALDEAO, (0.42, -0.05, 0), color=PELE_ALDEAO)
                ortho_camera(scene, (0.15, 0, 0.2), az, el, 1.0)
                render(scene, OUT / f"{familia}_{i}_{vista}.png")
    for estado in (None, "some", "restos"):
        nome = estado or "vivo"
        scene = new_scene()
        todos = sum(build_mapa(PEDRAS, VEIOS, estado).values(), [])
        for zoom in (0.4, 1.0, 2.5):
            cam = game_camera(scene, MAPA_ALVO, zoom)
            if estado is None:  # o mesmo recorte para os três estados
                medidas["recortes"][f"mapa_{zoom}"] = pixel_box(scene, cam, todos, margin=int(40 * zoom))
            render(scene, OUT / f"mapa_{nome}_zoom_{zoom}.png")
            bpy.data.objects.remove(cam)
    (OUT / "medidas.json").write_text(json.dumps(medidas, ensure_ascii=False, indent=2) + "\n")


main()

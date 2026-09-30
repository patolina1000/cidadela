"""Monta o estudo da copa sem borda (tarefa 9) com os renders de copa_estudo.py.

Uso: uv run --project tools/arte tools/arte/cenario/montar_copa_estudo.py <pasta_dos_renders>
Saída: assets/previews/cenario/copa_sem_borda.png (ESTUDO: não muda os arquivos que o jogo usa)
"""

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from montar_folha import ROOT, Sheet, twilight  # noqa: E402

OUT = ROOT / "assets/previews/cenario/copa_sem_borda.png"
VERSOES = (("0", "0 — atual, sem borda"), ("A", "A — tronco terra #4A3B3A em todas"),
           ("B", "B — A + massa de cima #5A5847"), ("C", "C — B + contorno escuro (APROXIMAÇÃO no Blender)"))
ZOOM25 = (600, 100, 2000, 1300)


def main():
    src = Path(sys.argv[1])
    m = json.loads((src / "medidas.json").read_text())
    s = Sheet()
    s.text("ESTUDO — copa sem borda fria no crepúsculo (tarefa 9): alternativas, nada aplicado aos arquivos do jogo", 42)
    s.text("Mesmo pedaço de mapa na câmera do jogo; copa sem borda em todas; pedra e veio com a borda deles. B: na alta "
           "(massa só) a metade de cima; os tufos (líquen) ficam como estão.", 26, (70, 70, 70))
    s.text("C: contorno #1B1620 por casca invertida de 1,2 cm — aproximação do contorno fino escuro que o GDD pede e o "
           "toon do jogo ainda não tem.", 26, (70, 70, 70))
    s.text("Zoom 1 (pixels reais) — luz do jogo e crepúsculo (× #6A5B7C)", 38)
    for v, label in VERSOES:
        im = Image.open(src / f"copa_{v}_zoom_1.0.png").convert("RGB").crop(m["recortes"]["mapa_1.0"])
        s.images([(im, label), (twilight(im), f"{label} — crepúsculo")])
    s.text("Zoom 2,5 (pixels reais, recorte do meio do bosque)", 38)
    for v, label in VERSOES:
        im = Image.open(src / f"copa_{v}_zoom_2.5.png").convert("RGB").crop(ZOOM25)
        s.images([(im, label), (twilight(im), f"{label} — crepúsculo")])
    s.save(OUT)


if __name__ == "__main__":
    main()

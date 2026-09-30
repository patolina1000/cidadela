"""Monta a folha do pedaço de mapa antes e depois (tarefa 4: pedra mais escura, lascas do veio mais gordas).

Uso: uv run --project tools/arte tools/arte/cenario/montar_folha_mapa.py <pasta_dos_renders>
Saída: assets/previews/cenario/mapa_antes_depois.png
"""

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from montar_folha import ROOT, Sheet, twilight  # noqa: E402

OUT = ROOT / "assets/previews/cenario/mapa_antes_depois.png"
NOMES = {"pedra": "pedra", "veio": "veio", "arvore": "copa/tronco", "aldeao": "aldeão", "protagonista": "protagonista"}


def main():
    src = Path(sys.argv[1])
    m = json.loads((src / "medidas.json").read_text())
    crop = lambda nome, z: Image.open(src / f"mapa_{nome}_zoom_{z}.png").convert("RGB").crop(m["recortes"][f"mapa_{z}"])

    s = Sheet()
    s.text("Pedaço de mapa — antes × depois (tarefa 4): pedra #66636B → #57535F; lascas do veio 40 % mais largas; "
           "veio 3 com 0,34 m", 40)
    b = m["brilho"]
    s.text("Brilho medido no zoom 1 (luma do sRGB da tela, 0–255, média / 5 % mais claros, com a borda fria): "
           + " | ".join(f"{NOMES[g]} {b['antes'][g]['media']:.0f}/{b['antes'][g]['p95']:.0f} → "
                        f"{b['depois'][g]['media']:.0f}/{b['depois'][g]['p95']:.0f}" for g in ("pedra", "veio")),
           28, (40, 40, 40))
    s.text("Referência: " + " | ".join(f"{NOMES[g]} {b['depois'][g]['media']:.0f}/{b['depois'][g]['p95']:.0f}"
                                     for g in ("aldeao", "protagonista", "arvore")), 28, (40, 40, 40))

    s.text("Zoom 0,4 (pixels reais e ampliado ×2)", 36)
    row, row_t = [], []
    for nome in ("antes", "depois"):
        z = crop(nome, 0.4)
        big = z.resize((z.width * 2, z.height * 2), Image.NEAREST)
        row += [(z, nome), (big, f"{nome} ×2")]
        row_t += [(twilight(z), f"{nome} — crepúsculo"), (twilight(big), f"{nome} ×2 — crepúsculo")]
    s.images(row)
    s.images(row_t)

    s.text("Zoom 1 (pixels reais)", 36)
    z = {n: crop(n, 1.0) for n in ("antes", "depois")}
    s.images([(z["antes"], "antes"), (z["depois"], "depois")])
    s.images([(twilight(z["antes"]), "antes — crepúsculo"), (twilight(z["depois"]), "depois — crepúsculo")])

    s.text("Zoom 2,5 (pixels reais, recorte da mancha de veios e das pedras, lado direito da tela)", 36)
    z = {n: Image.open(src / f"mapa_{n}_zoom_2.5.png").convert("RGB").crop((1500, 0, 2960, 1400))
         for n in ("antes", "depois")}
    s.images([(z["antes"], "antes"), (z["depois"], "depois")])
    s.images([(twilight(z["antes"]), "antes — crepúsculo"), (twilight(z["depois"]), "depois — crepúsculo")])
    s.save(OUT)


if __name__ == "__main__":
    main()

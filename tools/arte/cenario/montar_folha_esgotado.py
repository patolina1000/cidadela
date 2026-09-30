"""Monta a folha "quando o recurso esgota" (opções para o Arthur decidir) com os renders de folha_esgotado.py.

Uso: uv run --project tools/arte tools/arte/cenario/montar_folha_esgotado.py <pasta_dos_renders>
Saída: assets/previews/cenario/esgotado_contato.png
"""

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from montar_folha import ROOT, Sheet, twilight  # noqa: E402

OUT = ROOT / "assets/previews/cenario/esgotado_contato.png"
ESTADOS = (("some", "some tudo"), ("restos", "tocos e manchas"))
ZOOM25 = (1100, 300, 2700, 1890)  # recorte do zoom 2,5: tocos da frente, pedras e veios


def main():
    src = Path(sys.argv[1])
    m = json.loads((src / "medidas.json").read_text())
    crop = lambda n, z: Image.open(src / f"mapa_{n}_zoom_{z}.png").convert("RGB").crop(m["recortes"][f"mapa_{z}"])

    s = Sheet()
    s.text("Quando o recurso esgota — opções para o Arthur decidir (nada decidido)", 44)
    s.text("(a) toco da própria árvore: a base dela cortada, mesma torção, inclinação e giro, 3 raízes, corte na cor "
           "da madeira #6B5B4B.", 26, (70, 70, 70))
    s.text("(b) mancha do veio: placa baixa com 2 lascas quebradas, ou só 3 lascas. A pedra esgotada some nas duas "
           "versões. Borda fria na mancha; o toco é tronco e fica sem borda.", 26, (70, 70, 70))
    for familia, n, titulo in (("toco", 4, "(a) Tocos — um por árvore: 1 gota, 2 dupla, 3 tufos, 4 alta"),
                               ("mancha", 2, "(b) Manchas do veio — 1 placa, 2 lascas")):
        rep = json.loads((ROOT / f"assets/cenario/{'arvore' if familia == 'toco' else 'veio'}/"
                          f"{familia}_relatorio.json").read_text())
        items = []
        for vista in ("frente", "tres_quartos"):
            for i, v in enumerate(rep["variacoes"], start=1):
                im = Image.open(src / f"{familia}_{i}_{vista}.png").convert("RGB").resize((360, 360), Image.LANCZOS)
                label = (f"{i} {v['nome']}: {v['triangulos']} tri, {v['altura_m']:.2f} m".replace(".", ",")
                         if vista == "frente" else f"{i} {v['nome']} — 3/4")
                items.append((im, label))
        s.text(titulo, 34)
        s.images(items)

    s.text("Pedaço de mapa depois da coleta (4 árvores, 2 veios e 1 pedra esgotados) — câmera do jogo, pixels reais",
           38)
    row, row_t = [], []
    for n, label in ESTADOS:
        z = crop(n, 0.4)
        big = z.resize((z.width * 2, z.height * 2), Image.NEAREST)
        row += [(z, f"0,4 {label}"), (big, f"0,4 ×2 {label}")]
        row_t += [(twilight(z), "crepúsculo"), (twilight(big), f"crepúsculo ×2 {label}")]
    s.images(row)
    s.images(row_t)
    z = {n: crop(n, 1.0) for n, _ in ESTADOS}
    s.images([(z[n], f"zoom 1 — {label}") for n, label in ESTADOS])
    s.images([(twilight(z[n]), f"zoom 1 — {label} — crepúsculo") for n, label in ESTADOS])
    z = {n: Image.open(src / f"mapa_{n}_zoom_2.5.png").convert("RGB").crop(ZOOM25) for n, _ in ESTADOS}
    s.images([(z[n], f"zoom 2,5 (recorte) — {label}") for n, label in ESTADOS])
    s.images([(twilight(z[n]), f"zoom 2,5 — {label} — crepúsculo") for n, label in ESTADOS])
    s.save(OUT)


if __name__ == "__main__":
    main()

"""Recorta as vistas de frente e de costas (T-pose) das 5 variações de cabelo do aldeão.

Mesmo método da protagonista (crop_concept.py): o personagem é frio (azul) e o papel é quente;
em cada região fica a maior região conectada. Cada par sai num quadrado de 1024 px, fundo branco,
frente e costas na mesma escala.

Uso: uv run villager_views.py
"""

from pathlib import Path

import numpy as np
from PIL import Image

from crop_concept import figure_mask

ROOT = Path(__file__).resolve().parents[2]
CONCEPTS = ROOT / "assets/conceitos/aldeao"
OUT_DIR = CONCEPTS / "vistas"
CANVAS = 1024
MARGIN = 0.06
PAD = 20  # px em volta da região detectada, para não cortar fios de cabelo
WARM = 10  # vermelho - azul acima disso é papel (o aldeão não tem cor quente nenhuma)

# Regiões (x0, y0, x1, y1) de frente e costas. As variações de cabelo estão em "aldeao_expressoes.png"
# (os nomes dos conceitos vieram trocados); o cabelo longo liso está na folha principal.
VARIANTS = {
    "curto_baguncado": ("aldeao_expressoes.png", (35, 96, 351, 493), (360, 96, 671, 492)),
    "medio_franja": ("aldeao_expressoes.png", (745, 89, 1062, 493), (1072, 88, 1387, 493)),
    "ondulado": ("aldeao_expressoes.png", (36, 595, 352, 1004), (361, 595, 672, 1000)),
    "longo_liso": ("aldeao_folha.png", (254, 350, 666, 802), (677, 351, 1089, 801)),
    "rabo_cavalo": ("aldeao_expressoes.png", (747, 602, 1062, 1005), (1072, 599, 1384, 1004)),
    # Corpo-base careca (estrutura modular, 27/09/2026): os cabelos viram peças separadas.
    "careca": ("aldeao_careca.png", (90, 193, 690, 903), (732, 193, 1333, 902)),
}


def cut(sheet: Image.Image, box: tuple) -> Image.Image:
    x0, y0, x1, y1 = box
    region = (max(x0 - PAD, 0), max(y0 - PAD, 0), min(x1 + PAD, sheet.width), min(y1 + PAD, sheet.height))
    rgb = np.asarray(sheet.crop(region))
    mask = figure_mask(rgb)
    # O preenchimento de buracos prende pedaços do papel entre o cabelo e o pescoço: eles viram fundo.
    mask &= (rgb[..., 0].astype(int) - rgb[..., 2].astype(int)) <= WARM
    ys, xs = np.nonzero(mask)
    rgba = np.dstack([rgb, (mask * 255).astype(np.uint8)])[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return Image.fromarray(rgba, "RGBA")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, (file, front, back) in VARIANTS.items():
        sheet = Image.open(CONCEPTS / file).convert("RGB")
        views = {"frente": cut(sheet, front), "costas": cut(sheet, back)}
        biggest = max(max(v.size) for v in views.values())
        scale = CANVAS * (1 - 2 * MARGIN) / biggest
        for side, view in views.items():
            size = (round(view.width * scale), round(view.height * scale))
            view = view.resize(size, Image.LANCZOS)
            canvas = Image.new("RGB", (CANVAS, CANVAS), "white")
            canvas.paste(view, ((CANVAS - size[0]) // 2, (CANVAS - size[1]) // 2), view)
            path = OUT_DIR / f"{name}_{side}.png"
            canvas.save(path)
            print(f"{path.relative_to(ROOT)}  figura {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()

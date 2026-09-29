"""Monta a folha da prova do rosto: por variação (a, b, c), as 9 expressões com o aldeão a 96 px e a 48 px de
altura, mais a linha de 48 px multiplicada por #6A5B7C (crepúsculo).

Uso: uv run prova_rosto_folha.py <pasta_dos_renders> <saida.png>
Tamanhos reais do jogo (3024x1890): aldeão com 19, 44 e 112 px nos zooms 0,4, 1 e 2,5.
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
EXPRESSIONS = ["distraido", "esforco", "feliz", "sonolento", "dormindo", "espantado", "preocupado", "chorando", "bravo"]
VARIANTS = [("p35", "janela dos olhos até ±35°"), ("p45", "janela dos olhos até ±45°")]
# Altura do aldeão em pixels na câmera do jogo em 3024x1890 (medido em medir_zoom.py): zoom 0,4 / 1 / 2,5.
SIZES = [("zoom mínimo (19 px)", 19, 40, False), ("zoom padrão (44 px)", 44, 64, False), ("zoom máximo (112 px)", 112, 132, False),
         ("zoom padrão × crepúsculo", 44, 64, True)]
GROUND = (78, 74, 88)  # chão escuro do jogo
TWILIGHT = (106, 91, 124)


def villager(path: Path, height_px: int) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    crop = image.crop(bbox)
    scale = height_px / crop.height
    return crop.resize((max(1, round(crop.width * scale)), height_px), Image.LANCZOS)


def tile(sprite: Image.Image, size: int, twilight=False) -> Image.Image:
    bg = tuple(round(g * t / 255) for g, t in zip(GROUND, TWILIGHT)) if twilight else GROUND
    out = Image.new("RGBA", (size, size), (*bg, 255))
    if twilight:
        rgb = ImageChops.multiply(sprite.convert("RGB"), Image.new("RGB", sprite.size, TWILIGHT))
        sprite = Image.merge("RGBA", (*rgb.split(), sprite.getchannel("A")))
    out.alpha_composite(sprite, ((size - sprite.width) // 2, (size - sprite.height) // 2))
    return out


def main() -> None:
    renders, out = Path(sys.argv[1]), Path(sys.argv[2])
    font, small = ImageFont.truetype(FONT, 20), ImageFont.truetype(FONT, 14)
    rows = SIZES
    cell = 130
    block_h = 34 + sum(r[2] + 6 for r in rows) + 12
    sheet = Image.new("RGBA", (150 + cell * 9, 28 + block_h * len(VARIANTS)), (236, 233, 240, 255))
    d = ImageDraw.Draw(sheet)
    for c, name in enumerate(EXPRESSIONS):
        d.text((150 + c * cell + 4, 6), name, fill=(40, 36, 48), font=small)
    for b, (key, label) in enumerate(VARIANTS):
        y = 28 + b * block_h
        d.text((8, y + 6), label, fill=(30, 26, 40), font=font)
        y += 34
        for rname, height, size, twilight in rows:
            d.text((8, y + size // 2 - 8), rname, fill=(90, 86, 100), font=small)
            for c, name in enumerate(EXPRESSIONS):
                sprite = villager(renders / f"{key}_{name}.png", height)
                sheet.alpha_composite(tile(sprite, size, twilight), (150 + c * cell + (cell - size) // 2, y))
            y += size + 6
    sheet.convert("RGB").save(out)
    print(out)


if __name__ == "__main__":
    main()

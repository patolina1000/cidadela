"""Monta a prévia de um cabelo a partir dos renders do extrair_peruca.py: frente, lado, 3/4 e câmera do jogo,
com o aldeão a 44 px e a 112 px de altura (zoom padrão e máximo em 3024x1890), e a linha de 44 px multiplicada
por #6A5B7C (crepúsculo).

Uso: uv run previa_cabelo.py <pasta_dos_renders> <saida.png>
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
VIEWS = ["frente", "lado", "tres_quartos", "jogo"]
ROWS = [("112 px", 112, 136, False), ("44 px", 44, 64, False), ("44 px × crepúsculo", 44, 64, True)]
GROUND = (78, 74, 88)
TWILIGHT = (106, 91, 124)


def sprite(path: Path, height: int) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    crop = im.crop(bbox)
    scale = height / crop.height
    return crop.resize((max(1, round(crop.width * scale)), height), Image.LANCZOS)


def tile(sp: Image.Image, size: int, twilight: bool) -> Image.Image:
    bg = tuple(round(g * t / 255) for g, t in zip(GROUND, TWILIGHT)) if twilight else GROUND
    out = Image.new("RGBA", (size, size), (*bg, 255))
    if twilight:
        rgb = ImageChops.multiply(sp.convert("RGB"), Image.new("RGB", sp.size, TWILIGHT))
        sp = Image.merge("RGBA", (*rgb.split(), sp.getchannel("A")))
    out.alpha_composite(sp, ((size - sp.width) // 2, (size - sp.height) // 2))
    return out


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    font, small = ImageFont.truetype(FONT, 18), ImageFont.truetype(FONT, 14)
    cell = 150
    height = 30 + sum(r[2] + 8 for r in ROWS)
    sheet = Image.new("RGBA", (140 + cell * len(VIEWS), height), (236, 233, 240, 255))
    d = ImageDraw.Draw(sheet)
    for c, v in enumerate(VIEWS):
        d.text((140 + c * cell + 4, 6), v.replace("_", " "), fill=(40, 36, 48), font=font)
    y = 30
    for label, h, size, twilight in ROWS:
        d.text((8, y + size // 2 - 8), label, fill=(90, 86, 100), font=small)
        for c, v in enumerate(VIEWS):
            sheet.alpha_composite(tile(sprite(src / f"{v}.png", h), size, twilight), (140 + c * cell + (cell - size) // 2, y))
        y += size + 8
    sheet.convert("RGB").save(out)
    print(out)


if __name__ == "__main__":
    main()

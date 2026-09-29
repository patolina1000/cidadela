"""Monta a folha de diagnóstico da protagonista v1 a partir dos renders do diagnostico_v1.py.
Três colunas (v1 com textura, v1 chapada toon, aldeão v2 toon) × linhas dos zooms 0,4, 1 e 2,5, em pixels reais
da tela 3024x1890 (sem ampliar), com o mesmo recorte nas três colunas de cada zoom (o aldeão fica no tamanho real
ao lado dela); mais uma linha com o zoom 1 multiplicado por #6A5B7C (crepúsculo). A altura em px de cada
personagem vai embaixo de cada quadro.

Uso: uv run montar_diagnostico.py <pasta_dos_renders> <saida.png>
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
COLUMNS = [("a_v1_textura", "a) v1 com textura"), ("b_v1_chapada", "b) v1 chapada, toon"), ("c_aldeao_v2", "c) aldeão v2, toon")]
ZOOMS = ["0.4", "1.0", "2.5"]
GROUND = (78, 74, 88)
TWILIGHT = (106, 91, 124)
MARGIN = 0.18


def union_box(images) -> tuple:
    boxes = [im.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox() for im in images]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    pad = max(6, round(MARGIN * (y1 - y0)))
    return x0 - pad, y0 - pad, x1 + pad, y1 + pad


def height_px(im: Image.Image) -> int:
    b = im.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox()
    return b[3] - b[1]


def tile(im: Image.Image, box, twilight: bool) -> Image.Image:
    crop = im.crop(box)
    out = Image.new("RGBA", crop.size, (*GROUND, 255))
    out.alpha_composite(crop)
    if twilight:
        rgb = ImageChops.multiply(out.convert("RGB"), Image.new("RGB", out.size, TWILIGHT))
        out = rgb.convert("RGBA")
    return out


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    font, small = ImageFont.truetype(FONT, 20), ImageFont.truetype(FONT, 15)
    rows = []
    for zoom in ZOOMS + ["1.0x"]:
        z = zoom.rstrip("x")
        ims = [Image.open(src / f"{c}_{z}.png").convert("RGBA") for c, _ in COLUMNS]
        box = union_box(ims)
        tiles = [tile(im, box, zoom.endswith("x")) for im in ims]
        label = f"zoom {z.replace('.', ',').replace(',0', '')}" + (" × crepúsculo" if zoom.endswith("x") else "")
        rows.append((label, tiles, [height_px(im) for im in ims]))

    cell_w = max(t.width for _, tiles, _ in rows for t in tiles) + 24
    left, top, gap, caption = 170, 44, 16, 22
    height = top + sum(max(t.height for t in tiles) + caption + gap for _, tiles, _ in rows)
    sheet = Image.new("RGBA", (left + cell_w * len(COLUMNS), height), (236, 233, 240, 255))
    d = ImageDraw.Draw(sheet)
    for c, (_, title) in enumerate(COLUMNS):
        d.text((left + c * cell_w + 8, 12), title, fill=(40, 36, 48), font=font)
    y = top
    for label, tiles, heights in rows:
        rh = max(t.height for t in tiles)
        d.text((10, y + rh // 2 - 10), label, fill=(70, 66, 80), font=small)
        for c, (t, h) in enumerate(zip(tiles, heights)):
            x = left + c * cell_w + (cell_w - t.width) // 2
            sheet.alpha_composite(t, (x, y))
            d.text((x, y + rh + 3), f"{h} px de altura", fill=(90, 86, 100), font=small)
        y += rh + caption + gap
    dst.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(dst)
    print(dst, {label: heights for label, _, heights in rows})


if __name__ == "__main__":
    main()

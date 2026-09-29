"""Prévia conjunta dos 5 cabelos: para cada vista (frente, lado, 3/4, jogo), os cabelos lado a lado, nas linhas
112 px, 44 px e 44 px × crepúsculo (as mesmas da prévia do cabelo 4).

Uso: uv run previa_cabelos_conjunta.py <saida.png> <pasta_1> <pasta_2> ... (pastas de renders do extrair_peruca.py, na ordem)
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from previa_cabelo import FONT, ROWS, VIEWS, sprite, tile


def main() -> None:
    out, folders = Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]
    font, small = ImageFont.truetype(FONT, 18), ImageFont.truetype(FONT, 14)
    cell = 140
    block_w = cell * len(folders) + 20
    block_h = 30 + sum(r[2] + 8 for r in ROWS)
    sheet = Image.new("RGBA", (150 + block_w * len(VIEWS), block_h), (236, 233, 240, 255))
    d = ImageDraw.Draw(sheet)
    for v_i, view in enumerate(VIEWS):
        x0 = 150 + v_i * block_w
        d.text((x0 + 4, 6), view.replace("_", " "), fill=(40, 36, 48), font=font)
        for c, folder in enumerate(folders):
            d.text((x0 + c * cell + 4, 26), folder.name, fill=(90, 86, 100), font=small)
    y = 46
    for label, h, size, twilight in ROWS:
        d.text((8, y + size // 2 - 8), label, fill=(90, 86, 100), font=small)
        for v_i, view in enumerate(VIEWS):
            x0 = 150 + v_i * block_w
            for c, folder in enumerate(folders):
                sheet.alpha_composite(tile(sprite(folder / f"{view}.png", h), size, twilight), (x0 + c * cell + (cell - size) // 2, y))
        y += size + 8
    sheet = sheet.crop((0, 0, sheet.width, y + 8))
    sheet.convert("RGB").save(out)
    print(out)


if __name__ == "__main__":
    main()

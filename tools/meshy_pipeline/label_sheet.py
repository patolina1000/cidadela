"""Escreve os números/nomes embaixo de cada modelo na folha de prévia (lê o .json ao lado do .png).

Uso: uv run label_sheet.py <folha.png>
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"


def main() -> None:
    path = Path(sys.argv[1])
    labels = json.loads(path.with_suffix(".json").read_text())
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT, 26)
    for label in labels:
        width = draw.textlength(label["texto"], font=font)
        draw.text((label["x"] - width / 2, image.height - 60), label["texto"], fill=(237, 230, 214), font=font)
    image.save(path)
    path.with_suffix(".json").unlink()
    print(path)


if __name__ == "__main__":
    main()

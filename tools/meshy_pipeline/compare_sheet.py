"""Monta a folha de comparação conceito x modelo a partir dos renders do Blender.

Linha 1: recortes do conceito (frente, costas) e renders do modelo (frente, costas, noite).
Linha 2: câmera do jogo (55°) em pose de repouso e um quadro de cada animação.

Uso: uv run compare_sheet.py <nome> <pasta_dos_renders>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TILE = 400
LABEL_HEIGHT = 36
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"  # a fonte padrão do Pillow não tem acentos


def tile(path: Path, label: str) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail((TILE, TILE))
    out = Image.new("RGB", (TILE, TILE + LABEL_HEIGHT), "white")
    out.paste(image, ((TILE - image.width) // 2, LABEL_HEIGHT + (TILE - image.height) // 2))
    font = ImageFont.truetype(FONT, 22)
    ImageDraw.Draw(out).text((10, 6), label, fill="black", font=font)
    return out


def main() -> None:
    name, renders = sys.argv[1], Path(sys.argv[2])
    concept = ROOT / "assets/conceitos"
    rows = [
        [
            tile(concept / f"{name}_frente.png", "conceito: frente"),
            tile(concept / f"{name}_costas.png", "conceito: costas"),
            tile(renders / f"{name}_frente.png", "modelo: frente"),
            tile(renders / f"{name}_costas.png", "modelo: costas"),
            tile(renders / f"{name}_noite.png", "modelo: noite (cristal)"),
        ],
        [tile(renders / f"{name}_jogo.png", "câmera do jogo, 55°")]
        + [tile(renders / f"{name}_clipe_{clip}.png", f"clipe: {clip}") for clip in ("idle", "walk", "attack", "work")],
    ]
    width = max(len(r) for r in rows) * TILE
    sheet = Image.new("RGB", (width, len(rows) * (TILE + LABEL_HEIGHT)), "white")
    for y, row in enumerate(rows):
        for x, image in enumerate(row):
            sheet.paste(image, (x * TILE, y * (TILE + LABEL_HEIGHT)))
    path = ROOT / "assets/previews" / f"{name}_comparacao.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()

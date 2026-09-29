"""Folha de contato da Parte C: para cada GLB renderizado por render_corpo.py, uma linha com frente (com a área
dos retalhos do rosto marcada), lado, 3/4, câmera do jogo e a frente com a protagonista ao lado em escala, mais
as medidas (triângulos, lisura da área do rosto).

Uso: uv run folha_contato.py <pasta_dos_renders> <saida.png> [nome ...]
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
TILE = 300
LABEL = 30
EYES_FRAC = ((24 - 18) / 220, (78 - 12) / 236, (232 - 18) / 220, (208 - 12) / 236)
MOUTH_FRAC = ((110 - 18) / 220, (170 - 12) / 236, (174 - 18) / 220, (202 - 12) / 236)


def to_pixels(view: dict, x: float, z: float, res: int) -> tuple:
    """Coordenadas do mundo (x, z) para pixels na imagem de frente (câmera ortográfica olhando em +y)."""
    ortho = view["ortho"]
    cx, cz = view["alvo"][0], view["alvo"][2]
    px = (x - cx) / ortho * res + res / 2
    py = res / 2 - (z - cz) / ortho * res
    return px, py


def mark_face(image: Image.Image, measures: dict) -> Image.Image:
    view, box = measures["vistas"]["frente"], measures["cabeca"]
    res = image.width
    x0, x1 = box["x"]
    z0, z1 = box["z"]
    w, h = x1 - x0, z1 - z0
    d = ImageDraw.Draw(image)
    for (fx0, fy0, fx1, fy1), color in ((EYES_FRAC, (200, 60, 60)), (MOUTH_FRAC, (60, 90, 200))):
        ax, ay = to_pixels(view, x0 + fx0 * w, z1 - fy0 * h, res)
        bx, by = to_pixels(view, x0 + fx1 * w, z1 - fy1 * h, res)
        d.rectangle([ax, ay, bx, by], outline=color, width=3)
    ax, ay = to_pixels(view, x0, z1, res)
    bx, by = to_pixels(view, x1, z0, res)
    d.rectangle([ax, ay, bx, by], outline=(120, 120, 120), width=1)
    return image


def tile(path: Path, label: str, measures=None) -> Image.Image:
    image = Image.open(path).convert("RGB")
    if measures:
        image = mark_face(image, measures)
    image.thumbnail((TILE, TILE))
    out = Image.new("RGB", (TILE, TILE + LABEL), "white")
    out.paste(image, ((TILE - image.width) // 2, LABEL + (TILE - image.height) // 2))
    ImageDraw.Draw(out).text((8, 6), label, fill="black", font=ImageFont.truetype(FONT, 18))
    return out


def main() -> None:
    renders, out = Path(sys.argv[1]), Path(sys.argv[2])
    names = sys.argv[3:] or sorted(p.stem[:-len("_medidas")] for p in renders.glob("*_medidas.json"))
    font = ImageFont.truetype(FONT, 16)
    rows = []
    for name in names:
        m = json.loads((renders / f"{name}_medidas.json").read_text())
        row = [tile(renders / f"{name}_frente.png", f"{name}: frente + retalhos", m),
               tile(renders / f"{name}_lado.png", "lado"),
               tile(renders / f"{name}_tres_quartos.png", "3/4"),
               tile(renders / f"{name}_jogo.png", "câmera do jogo 55°")]
        if (renders / f"{name}_escala.png").exists():
            row.append(tile(renders / f"{name}_escala.png", "escala: protagonista"))
        r = m["rosto"]
        text = (f"{m['triangulos']} triângulos | cabeça {1000 * (m['cabeca']['x'][1] - m['cabeca']['x'][0]):.0f} x "
                f"{1000 * (m['cabeca']['z'][1] - m['cabeca']['z'][0]):.0f} mm | área dos olhos: rugosidade RMS "
                f"{r.get('olhos', {}).get('rms_mm', '?')} mm, máx {r.get('olhos', {}).get('max_mm', '?')} mm | boca: RMS "
                f"{r.get('boca', {}).get('rms_mm', '?')} mm, máx {r.get('boca', {}).get('max_mm', '?')} mm")
        rows.append((row, text))
    width = max(len(r) for r, _ in rows) * TILE
    sheet = Image.new("RGB", (width, len(rows) * (TILE + LABEL + 24)), "white")
    for i, (row, text) in enumerate(rows):
        y = i * (TILE + LABEL + 24)
        for j, image in enumerate(row):
            sheet.paste(image, (j * TILE, y))
        ImageDraw.Draw(sheet).text((8, y + TILE + LABEL + 4), text, fill=(40, 40, 40), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()

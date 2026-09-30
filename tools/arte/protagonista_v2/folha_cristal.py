"""Folha da prova do cristal (renders do prova_cristal.py): duas fileiras, dia e crepúsculo (a luz × #6A5B7C, a emissão
igual). Em cada uma: v2 e v1 de frente e 3/4, closes do peito, câmera do jogo em recorte 1:1 nos zooms 0,4 / 1 / 2,5 e
o zoom 0,4 ampliado 6×.

Uso (em tools/arte): uv run protagonista_v2/folha_cristal.py <pasta_dos_renders>
Saída: assets/previews/protagonista_v2/cristal_prova.png
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_meshy import FONT, INK, PAPER, br, labeled, on_bg  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2/cristal_prova.png"
INFO = ROOT / "assets/modelos/protagonista_v2/cristal.json"
TILE = 300
ZOOMS = ("0.4", "1.0", "2.5")


def crop(path, center, size):
    img = on_bg(Image.open(path))
    x0, y0 = int(round(center[0] - size / 2)), int(round(center[1] - size / 2))
    return img.crop((x0, y0, x0 + size, y0 + size))


def main() -> None:
    renders = Path(sys.argv[1])
    px = json.loads((renders / "prova_cristal.json").read_text())
    info = json.loads(INFO.read_text())
    font = ImageFont.truetype(FONT, 15)
    rows = []
    for tag, name in (("dia", "dia"), ("crepusculo", "crepúsculo (luz × #6A5B7C; a emissão não muda, como no jogo)")):
        tiles = [labeled(on_bg(Image.open(renders / f"{tag}_{v}.png")).resize((TILE, TILE), Image.LANCZOS), t, font)
                 for v, t in (("frente", "frente: v2 e v1"), ("tres_quartos", "3/4: v2 e v1"))]
        tiles += [labeled(on_bg(Image.open(renders / f"{tag}_peito_{w}_{v}.png")).resize((TILE, TILE), Image.LANCZOS), t, font)
                  for w, v, t in (("v2", "frente", "peito v2, frente"), ("v2", "tres_quartos", "peito v2, 3/4"), ("v1", "frente", "peito v1, frente"))]
        for z in ZOOMS:
            b = px[z]["caixa_px"]
            c = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            tiles.append(labeled(crop(renders / f"{tag}_jogo_{z}.png", c, TILE),
                                 br(f"zoom {z.rstrip('0').rstrip('.')} 1:1: cristal {px[z]['cristal_v2_px'][0]:.1f}×{px[z]['cristal_v2_px'][1]:.1f} px (v1 {px[z]['cristal_v1_px'][0]:.1f}×{px[z]['cristal_v1_px'][1]:.1f})"), font))
        c2, c1 = px["0.4"]["cristal_v2_centro_px"], px["0.4"]["cristal_v1_centro_px"]
        tiles.append(labeled(crop(renders / f"{tag}_jogo_0.4.png", ((c2[0] + c1[0]) / 2, c2[1] - 4), 50).resize((TILE, TILE), Image.NEAREST),
                             "zoom 0,4 ampliado 6×: v2 (esq.) e v1", font))
        rows.append((name, tiles))
    width = TILE * len(rows[0][1])
    header = 76
    row_h = rows[0][1][0].height + 30
    sheet = Image.new("RGB", (width, header + row_h * len(rows)), PAPER)
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), "Protagonista v2 — cristal do peito (por código) ao lado da v1", fill=INK, font=ImageFont.truetype(FONT, 24))
    d.text((10, 44), br(f"{info['triangulos']} triângulos (limite 60), material Cristal, {info['tamanho_mm']['largura']:.0f}×{info['tamanho_mm']['altura']:.0f}×"
                        f"{info['tamanho_mm']['fundo']:.0f} mm, avança {info['avanca_da_pele_mm']} mm do esterno, inclinado {info['inclinacao_graus']}° para cima; "
                        f"emissão {info['emissao']} força {info['forca_emissao']} (× 3 no jogo). A v1: losango de 4 triângulos, 27×52 mm."),
           fill=INK, font=font)
    y = header
    for name, tiles in rows:
        d.text((10, y + 4), name, fill=INK, font=ImageFont.truetype(FONT, 18))
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * TILE, y + 30))
        y += row_h
    sheet.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()

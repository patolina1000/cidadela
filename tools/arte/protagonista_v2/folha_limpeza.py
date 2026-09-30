"""Folha da limpeza do cabelo e do teste dos chifres com a base recuada (renders do prova_cabelo.py).

Fileira 1 e 2: antes (c4a7337) e depois da limpeza, close de frente, perfil, costas, 3/4 e corpo de costas.
Fileira 3 e 4: chifres a 20° (atuais) e com a base recuada 18 mm pelo crânio, de frente, 3/4, perfil, de cima e a cabeça no
zoom 2,5 da câmera do jogo ampliada 4×. Versão crepúsculo.

Uso (em tools/arte): uv run protagonista_v2/folha_limpeza.py <antes> <depois> <recuados>
Saída: assets/previews/protagonista_v2/cabelo_limpeza.png e _crepusculo.png
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_meshy import FONT, INK, PAPER, TWILIGHT, labeled, on_bg  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2/cabelo_limpeza.png"
TILE = 300


def tile(path, text, font):
    return labeled(on_bg(Image.open(path)).resize((TILE, TILE), Image.LANCZOS), text, font)


def game_head(d, font, text):
    hc = json.loads((d / "prova_cabelo.json").read_text())["jogo"]["2.5"]["cabeca_centro_px"]
    img = on_bg(Image.open(d / "jogo_2.5.png"))
    x0, y0 = int(hc[0] - 37), int(hc[1] - 37)
    return labeled(img.crop((x0, y0, x0 + 75, y0 + 75)).resize((TILE, TILE), Image.NEAREST), text, font)


def main() -> None:
    before, after, slid = (Path(a) for a in sys.argv[1:4])
    font = ImageFont.truetype(FONT, 15)
    views = (("cabeca_frente", "frente"), ("cabeca_lado", "perfil"), ("cabeca_costas", "costas"), ("cabeca_tres_quartos", "3/4"),
             ("corpo_costas", "corpo, costas"))
    rows = [(f"{name} da limpeza", [tile(d / f"{v}.png", t, font) for v, t in views]) for name, d in (("antes", before), ("depois", after))]
    horn_views = (("cabeca_frente", "frente"), ("cabeca_tres_quartos", "3/4"), ("cabeca_lado", "perfil"), ("cabeca_topo", "de cima"))
    for name, d in (("chifres a 20° (atuais)", after), ("chifres com a base recuada 18 mm", slid)):
        rows.append((name, [tile(d / f"{v}.png", t, font) for v, t in horn_views] + [game_head(d, font, "zoom 2,5, cabeça 4×")]))
    lines = [
        "Protagonista v2 — limpeza do cabelo (0 crédito) e teste dos chifres com a base recuada",
        "Cabelo: furos pequenos fechados, sem UV (o exportador abria ~480 bordas nas costuras), borda da linha do cabelo suavizada,",
        "   borda lateral puxada para as costas: nenhum vértice dentro do corpo em nenhum quadro da corrida e do idle (folga mínima 3,5 mm; antes −28 mm).",
        "Chifres recuados: a base desliza 18 mm (13,7°) para trás pelo crânio; de frente eles saem de dentro do cabelo, não dos cantos da cabeça.",
    ]
    width = TILE * 5
    header = 20 + 24 * len(lines)
    row_h = rows[0][1][0].height + 30
    sheet = Image.new("RGB", (width, header + row_h * len(rows)), PAPER)
    d = ImageDraw.Draw(sheet)
    for i, line in enumerate(lines):
        d.text((10, 8 + 24 * i), line, fill=INK, font=ImageFont.truetype(FONT, 20 if i == 0 else 15))
    y = header
    for label, tiles in rows:
        d.text((10, y + 4), label, fill=INK, font=ImageFont.truetype(FONT, 17))
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * TILE, y + 30))
        y += row_h
    sheet.save(OUT)
    ImageChops.multiply(sheet, Image.new("RGB", sheet.size, TWILIGHT)).save(OUT.with_name("cabelo_limpeza_crepusculo.png"))
    print(OUT)


if __name__ == "__main__":
    main()

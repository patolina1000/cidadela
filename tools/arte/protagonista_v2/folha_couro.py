"""Folha do couro cabeludo coberto (antes/depois) a partir do prova_cabelo.py e do teste_couro.py (--guardar).

Fileiras: closes em volta dos chifres (3/4 dos dois lados e de cima) e duas imagens do teste (pele do couro cabeludo em
vermelho, o resto em preto), antes (variante recuada, sem a calota) e depois; câmera do jogo nos 3 zooms, depois.
Versão crepúsculo.

Uso (em tools/arte): uv run protagonista_v2/folha_couro.py <prova_antes> <prova_depois> <teste_antes> <teste_depois>
Saída: assets/previews/protagonista_v2/cabelo_couro.png e _crepusculo.png
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_meshy import FONT, INK, PAPER, TWILIGHT, br, labeled, on_bg  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2/cabelo_couro.png"
TILE = 300
GRAY = (128, 128, 128)


def tile(path, text, font, bg=None):
    im = Image.open(path).convert("RGBA")
    base = Image.new("RGBA", im.size, (*(bg or (78, 74, 88)), 255))
    base.alpha_composite(im)
    return labeled(base.convert("RGB").resize((TILE, TILE), Image.LANCZOS), text, font)


def crop(path, center, size):
    img = on_bg(Image.open(path))
    x0, y0 = int(round(center[0] - size / 2)), int(round(center[1] - size / 2))
    return img.crop((x0, y0, x0 + size, y0 + size))


def main() -> None:
    pa, pd, ta, td = (Path(a) for a in sys.argv[1:5])
    font = ImageFont.truetype(FONT, 15)
    ja, jd = json.loads((ta / "teste_couro.json").read_text()), json.loads((td / "teste_couro.json").read_text())
    rows = []
    for name, p, t, j in (("antes (base recuada, sem a calota)", pa, ta, ja), ("depois (calota + anel em volta dos chifres + volume)", pd, td, jd)):
        tiles = [tile(p / f"close_{v}.png", lab, font) for v, lab in
                 (("chifre_esq_tq", "chifre esquerdo, 3/4"), ("chifre_dir_tq", "chifre direito, 3/4"), ("chifres_cima", "de cima"))]
        for k in ("repouso_frente", "repouso_tq_frente_dir"):
            tiles.append(tile(t / f"{k}.png", f"teste: {j['imagens'][k]} px de pele", font, GRAY))
        rows.append((br(f"{name} — teste: {j['total_pixels_de_pele']} px de pele em {len(j['imagens'])} imagens"), tiles))
    proof = json.loads((pd / "prova_cabelo.json").read_text())
    game = []
    for z in ("0.4", "1.0", "2.5"):
        b, hc = proof["jogo"][z]["caixa_px"], proof["jogo"][z]["cabeca_centro_px"]
        c = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) if z != "2.5" else (hc[0], hc[1] + 110)
        game.append(labeled(crop(pd / f"jogo_{z}.png", c, TILE), br(f"zoom {z.rstrip('0').rstrip('.')} 1:1"), font))
    game.append(labeled(crop(pd / "jogo_2.5.png", proof["jogo"]["2.5"]["cabeca_centro_px"], 75).resize((TILE, TILE), Image.NEAREST),
                        "zoom 2,5, cabeça ampliada 4×", font))
    rows.append(("depois, na câmera do jogo (v1 à esquerda, aldeão à direita)", game))
    lines = [
        "Protagonista v2 — couro cabeludo coberto: calota de cabelo por código sob as mechas, anel em volta da base dos chifres",
        "Teste automático: a pele do couro cabeludo (da linha do cabelo para trás) pintada de vermelho, o resto de preto; 10 vistas e a câmera do",
        "   jogo nos 3 zooms (13 imagens), em repouso e em 4 quadros da corrida e 3 do idle: 104 imagens. Meta: zero pixels vermelhos.",
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
    ImageChops.multiply(sheet, Image.new("RGB", sheet.size, TWILIGHT)).save(OUT.with_name("cabelo_couro_crepusculo.png"))
    print(OUT)


if __name__ == "__main__":
    main()

"""Passo 4: folha da prova do rosto (3 variações), a partir dos renders do prova_rosto.py.

Uma fileira por variação: cabeça de frente e 3/4 (close), frente e 3/4 com o aldeão v2 ao lado, câmera do jogo em
recorte 1:1 nos zooms 0,4 / 1 / 2,5 e a cabeça no zoom 2,5 ampliada 6× (pixels do jogo, sem suavizar). Versão
crepúsculo (× #6A5B7C) e as notas de leitura de cada traço por zoom.

Uso (em tools/arte): uv run protagonista_v2/folha_rosto.py <pasta_dos_renders> <notas.json> [<pasta_do_estudo> <nome_saida>]
Saída: assets/previews/protagonista_v2/<nome_saida>.png (padrão rosto_prova), _crepusculo.png e .json. Se a prova tiver
a v1 (prova_rosto.py --v1), ela entra como última fileira, de referência.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_meshy import FONT, INK, PAPER, TWILIGHT, br, labeled, on_bg  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2"
STUDY = OUT / "rosto_estudo"
TILE = 300
ZOOMS = ("0.4", "1.0", "2.5")


def crop_1to1(path: Path, center, size=TILE) -> Image.Image:
    img = on_bg(Image.open(path))
    x0, y0 = int(round(center[0] - size / 2)), int(round(center[1] - size / 2))
    return img.crop((x0, y0, x0 + size, y0 + size))


def main() -> None:
    renders, notes = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
    study = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else STUDY
    out_name = sys.argv[4] if len(sys.argv) > 4 else "rosto_prova"
    proof = json.loads((renders / "prova.json").read_text())
    variants = json.loads((study / "variacoes.json").read_text())
    title = notes.get("titulo", "Protagonista v2 — prova do rosto (neutra_cansada) no corpo limpo, antes do rig: 3 variações")
    font = ImageFont.truetype(FONT, 15)
    title_font = ImageFont.truetype(FONT, 24)
    rows = []
    entries = list(proof["variacoes"].items()) + ([("v1", proof["v1"])] if "v1" in proof else [])
    for name, v in entries:
        tiles = [labeled(on_bg(Image.open(renders / f"{name}_cabeca_{view}.png")).resize((TILE, TILE), Image.LANCZOS), t, font)
                 for view, t in (("frente", "cabeça, frente"), ("tres_quartos", "cabeça, 3/4"))]
        tiles += [labeled(on_bg(Image.open(renders / f"{name}_{view}.png")).resize((TILE, TILE), Image.LANCZOS), t, font)
                  for view, t in (("frente", "frente, com o aldeão"), ("tres_quartos", "3/4, com o aldeão"))]
        for z in ZOOMS:
            j = v["jogo"][z]
            b = j["caixa_px"]
            tiles.append(labeled(crop_1to1(renders / f"{name}_jogo_{z}.png", ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)),
                                 br(f"jogo zoom {z.rstrip('0').rstrip('.')} (1:1): cabeça {j['cabeca_px'][0]:.0f} px"), font))
        hb = v["jogo"]["2.5"]["cabeca_caixa_px"]
        head = crop_1to1(renders / f"{name}_jogo_2.5.png", ((hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2 + 6), 50)
        tiles.append(labeled(head.resize((TILE, TILE), Image.NEAREST), "zoom 2,5, cabeça ampliada 6×", font))
        label = variants[name]["nome"] if name in variants else "v1 (referência de rosto, como estava no jogo)"
        rows.append((label, tiles, notes["variacoes"].get(name, "")))

    width = TILE * len(rows[0][1])
    row_h = rows[0][1][0].height + 52
    lines = notes["leitura"]
    header = 48 + 22 * len(lines) + 10
    sheet = Image.new("RGB", (width, header + row_h * len(rows)), PAPER)
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), title, fill=INK, font=title_font)
    for i, line in enumerate(lines):
        d.text((10, 48 + 22 * i), line, fill=INK, font=font)
    y = header
    big = ImageFont.truetype(FONT, 18)
    for label, tiles, note in rows:
        d.text((10, y + 4), f"{label} — {note}", fill=INK, font=big)
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * TILE, y + 30))
        y += row_h
    sheet.save(OUT / f"{out_name}.png")
    ImageChops.multiply(sheet, Image.new("RGB", sheet.size, TWILIGHT)).save(OUT / f"{out_name}_crepusculo.png")
    (OUT / f"{out_name}.json").write_text(json.dumps({"prova": proof, "variacoes": variants, "notas": notes},
                                                     indent=2, ensure_ascii=False) + "\n")
    print(OUT / f"{out_name}.png")


if __name__ == "__main__":
    main()

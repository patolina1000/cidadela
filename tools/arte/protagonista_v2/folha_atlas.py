"""Passo 6: folha da prova do atlas do rosto e GIFs do piscar, a partir dos renders do prova_atlas.py.

Folha: uma coluna por expressão (rosto.json); fileiras: close de frente, close 3/4, câmera do jogo no zoom 2,5 em
recorte 1:1 com o aldeão ao lado, e a cabeça no zoom 2,5 ampliada 6× (pixels do jogo). Versão crepúsculo.
GIFs do piscar (aberto → meio_fechado → fechado → meio_fechado → aberto, a 24 quadros/s com o olho aberto parado ~1,2 s):
close de frente e a cabeça no zoom 2,5 ampliada 6×.

Uso (em tools/arte): uv run protagonista_v2/folha_atlas.py <pasta_dos_renders>
Saída: assets/previews/protagonista_v2/rosto_atlas_prova.png, _crepusculo.png, piscar_close.gif e piscar_jogo.gif
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_meshy import FONT, INK, PAPER, TWILIGHT, labeled, on_bg  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2"
ROSTO = ROOT / "assets/modelos/protagonista_v2/rosto/rosto.json"
TILE = 300
MS = 42  # 24 quadros/s


def crop(path: Path, center, size):
    img = on_bg(Image.open(path))
    x0, y0 = int(round(center[0] - size / 2)), int(round(center[1] - size / 2))
    return img.crop((x0, y0, x0 + size, y0 + size))


def main() -> None:
    renders = Path(sys.argv[1])
    info = json.loads((renders / "prova_atlas.json").read_text())
    rosto = json.loads(ROSTO.read_text())
    font = ImageFont.truetype(FONT, 15)
    big = ImageFont.truetype(FONT, 18)
    b, hb = info["jogo"]["caixa_px"], info["jogo"]["cabeca_caixa_px"]
    pair_c = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    head_c = ((hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2 + 6)
    names = list(rosto["expressoes"])
    cols = []
    for n in names:
        e, m = rosto["expressoes"][n]["olhos"], rosto["expressoes"][n]["boca"]
        col = [labeled(on_bg(Image.open(renders / f"{n}_cabeca_{v}.png")).resize((TILE, TILE), Image.LANCZOS), t, font)
               for v, t in (("frente", f"{n}: frente"), ("tres_quartos", f"{n}: 3/4"))]
        col.append(labeled(crop(renders / f"{n}_jogo.png", pair_c, TILE), "jogo zoom 2,5 (1:1), com o aldeão", font))
        col.append(labeled(crop(renders / f"{n}_jogo.png", head_c, 50).resize((TILE, TILE), Image.NEAREST),
                           "zoom 2,5, cabeça ampliada 6×", font))
        cols.append((n, col))
    header = 44
    col_h = sum(t.height for t in cols[0][1]) + 30
    sheet = Image.new("RGB", (TILE * len(cols), header + col_h), PAPER)
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), "Protagonista v2 — atlas do rosto (b3 aprovada): as 5 expressões do contrato no corpo limpo, antes do rig",
           fill=INK, font=ImageFont.truetype(FONT, 22))
    for i, (label, col) in enumerate(cols):
        x = i * TILE
        d.text((x + 6, header + 4), label, fill=INK, font=big)
        y = header + 30
        for t in col:
            sheet.paste(t, (x, y))
            y += t.height
    sheet.save(OUT / "rosto_atlas_prova.png")
    ImageChops.multiply(sheet, Image.new("RGB", sheet.size, TWILIGHT)).save(OUT / "rosto_atlas_prova_crepusculo.png")

    # piscar: aberto parado, 2 quadros meio, 3 fechado, 2 meio
    seq = [("neutra_cansada", 29), ("piscar_meio_fechado", 2), ("piscar", 3), ("piscar_meio_fechado", 2)]
    for kind, tag in (("close", "piscar_close.gif"), ("jogo", "piscar_jogo.gif")):
        frames, durations = [], []
        for name, n in seq:
            if kind == "close":
                img = on_bg(Image.open(renders / f"{name}_cabeca_frente.png")).resize((400, 400), Image.LANCZOS)
            else:
                img = crop(renders / f"{name}_jogo.png", head_c, 60).resize((360, 360), Image.NEAREST)
            frames.append(img.convert("P", palette=Image.Palette.ADAPTIVE, colors=255))
            durations.append(n * MS)
        frames[0].save(OUT / tag, save_all=True, append_images=frames[1:], duration=durations, loop=0, disposal=1)
    print(OUT / "rosto_atlas_prova.png")


if __name__ == "__main__":
    main()

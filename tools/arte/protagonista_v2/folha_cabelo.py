"""Folha de contato do cabelo (renders do prova_cabelo.py) e GIFs da corrida e do idle com cabelo.

Folha: close da cabeça (frente, perfil, costas, 3/4, topo); corpo inteiro (frente, perfil, costas, 3/4); câmera do jogo
1:1 nos zooms 0,4 / 1 / 2,5 com o aldeão e a v1 ao lado, e a cabeça no 2,5 ampliada 4×. Versão crepúsculo.
GIFs: run-loop (19 quadros, 24 q/s) e idle-loop (30 quadros ao longo dos 11,25 s), de lado, de costas e na câmera do jogo.

Uso (em tools/arte): uv run protagonista_v2/folha_cabelo.py <pasta_prova> <pasta_quadros>
Saída: assets/previews/protagonista_v2/cabelo_prova.png, _crepusculo.png e cabelo_gifs/*.gif
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_meshy import FONT, INK, PAPER, TWILIGHT, br, labeled, on_bg  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2/cabelo_prova.png"
GIFS = ROOT / "assets/previews/protagonista_v2/cabelo_gifs"
INFO = ROOT / "assets/modelos/protagonista_v2/cabelo.json"
TILE = 300
GROUND = (78, 74, 88)


def tile(path, text, font):
    return labeled(on_bg(Image.open(path)).resize((TILE, TILE), Image.LANCZOS), text, font)


def crop(path, center, size):
    img = on_bg(Image.open(path))
    x0, y0 = int(round(center[0] - size / 2)), int(round(center[1] - size / 2))
    return img.crop((x0, y0, x0 + size, y0 + size))


def gifs(frames_dir: Path) -> None:
    GIFS.mkdir(parents=True, exist_ok=True)
    for clip, ms in (("run-loop", 42), ("idle-loop", 375)):
        for view in ("lado", "costas", "jogo"):
            paths = sorted(frames_dir.glob(f"{clip}_{view}_*.png"))
            if not paths:
                continue
            ims = [on_bg(Image.open(p)).resize((360, 360), Image.LANCZOS) for p in paths]
            if view == "jogo":  # o tamanho da câmera do jogo no zoom 1 (80 px de altura), ampliado 2×
                ims = [im.resize((96, 96), Image.LANCZOS).resize((288, 288), Image.NEAREST) for im in ims]
            pal = ims[0].quantize(colors=200, method=Image.Quantize.MEDIANCUT)
            q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in ims]
            q[0].save(GIFS / f"{clip}_{view}.gif", save_all=True, append_images=q[1:], duration=ms, loop=0, disposal=1)


def main() -> None:
    prova, frames = Path(sys.argv[1]), Path(sys.argv[2])
    info = json.loads(INFO.read_text())
    proof = json.loads((prova / "prova_cabelo.json").read_text())
    font = ImageFont.truetype(FONT, 15)
    rows = [("close da cabeça", [tile(prova / f"cabeca_{v}.png", t, font) for v, t in
                                 (("frente", "frente"), ("lado", "perfil"), ("costas", "costas"), ("tres_quartos", "3/4"), ("topo", "de cima"))]),
            ("corpo inteiro", [tile(prova / f"corpo_{v}.png", t, font) for v, t in
                               (("frente", "frente"), ("lado", "perfil"), ("costas", "costas"), ("tres_quartos", "3/4"))])]
    game = []
    for z in ("0.4", "1.0", "2.5"):
        b, hc = proof["jogo"][z]["caixa_px"], proof["jogo"][z]["cabeca_centro_px"]
        center = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) if z != "2.5" else (hc[0], hc[1] + 110)  # no 2,5 o trio não cabe
        game.append(labeled(crop(prova / f"jogo_{z}.png", center, TILE),
                            br(f"zoom {z.rstrip('0').rstrip('.')} 1:1" + (" — v1, protagonista, aldeão" if z != "2.5" else " — ela")), font))
    hc = proof["jogo"]["2.5"]["cabeca_centro_px"]
    game.append(labeled(crop(prova / "jogo_2.5.png", hc, 75).resize((TILE, TILE), Image.NEAREST), "zoom 2,5, cabeça ampliada 4×", font))
    rows.append(("câmera do jogo, com a v1 (esq.) e o aldeão (dir.)", game))
    worst = info["pior_quadro"]
    lines = [
        "Protagonista v2 — cabelo longo com pesos (piloto), com chifres (20°, 1,3×) e cristal, no corpo final",
        br(f"{info['triangulos']} triângulos (limite 1,000), material cabelo #4B5A69; pesos: calota 100% Head, depois neck, Spine e Spine01 pela altura."),
        "Janela dos olhos aberta; folga de 2 mm do corpo e dos retalhos (3 mm na calota, conferida também no meio das faces), medida depois da decimação.",
        br(f"Nos clipes: idle sem nada dentro do corpo; na corrida o braço passa pela borda lateral do cabelo (pior {info['pior_mm']} mm em {worst}, "
           f"até {info['vertices_dentro_max']} vértices)."),
    ]
    width = TILE * max(len(r[1]) for r in rows)
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
    ImageChops.multiply(sheet, Image.new("RGB", sheet.size, TWILIGHT)).save(OUT.with_name("cabelo_prova_crepusculo.png"))
    gifs(frames)
    print(OUT)


if __name__ == "__main__":
    main()

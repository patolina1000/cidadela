"""Folha de contato dos chifres (piloto), a partir dos renders do prova_chifres.py (0°, e as variações de inclinação).

Fileiras: (1) o bruto da Meshy com as ilhas (roxo: o par escolhido; vermelho: a duplicata de trás), frente, perfil e topo;
(2) a peça extraída sobre a cabeça do corpo final, frente, perfil, 3/4 e costas; (3) corpo de frente e 3/4 com o aldeão,
câmera do jogo 1:1 nos zooms 0,4 / 1 / 2,5 e a cabeça no 2,5 ampliada 4×; (4) "orelha de gato": frente e 3/4 com os
chifres a 0° (a folha), 20° e 35° para trás. Versão crepúsculo (× #6A5B7C).

Uso (em tools/arte): uv run protagonista_v2/folha_chifres.py <pasta_0> <pasta_20> <pasta_35>
Saída: assets/previews/protagonista_v2/chifres_prova.png e chifres_prova_crepusculo.png
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_meshy import FONT, INK, PAPER, TWILIGHT, br, labeled, on_bg  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2/chifres_prova.png"
INFO = ROOT / "assets/modelos/protagonista_v2/chifres.json"
TILE = 300


def tile(path, text, font):
    return labeled(on_bg(Image.open(path)).resize((TILE, TILE), Image.LANCZOS), text, font)


def crop(path, center, size):
    img = on_bg(Image.open(path))
    x0, y0 = int(round(center[0] - size / 2)), int(round(center[1] - size / 2))
    return img.crop((x0, y0, x0 + size, y0 + size))


def main() -> None:
    d0, d20, d35 = (Path(a) for a in sys.argv[1:4])
    info = json.loads(INFO.read_text())
    proof = json.loads((d0 / "prova_chifres.json").read_text())
    font = ImageFont.truetype(FONT, 15)
    rows = [
        ("bruto da Meshy (geração 1): quatro chifres — roxo, o par escolhido; vermelho, a duplicata de trás",
         [tile(d0 / f"bruto_{v}.png", t, font) for v, t in (("frente", "bruto, frente"), ("lado", "bruto, perfil"), ("topo", "bruto, topo"))]),
        ("peça extraída sobre a cabeça do corpo final (0°, como na folha)",
         [tile(d0 / f"cabeca_{v}.png", t, font) for v, t in (("frente", "frente"), ("lado", "perfil"), ("tres_quartos", "3/4"), ("costas", "costas"))]),
    ]
    game = [tile(d0 / "corpo_frente.png", "corpo e aldeão, frente", font), tile(d0 / "corpo_tres_quartos.png", "3/4", font)]
    for z in ("0.4", "1.0", "2.5"):
        b = proof["jogo"][z]["caixa_px"]
        game.append(labeled(crop(d0 / f"jogo_{z}.png", ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), TILE),
                            br(f"jogo zoom {z.rstrip('0').rstrip('.')} 1:1: chifres {proof['jogo'][z]['chifres_px'][0]:.0f} px de largura"), font))
    hc = proof["jogo"]["2.5"]["cabeca_centro_px"]
    game.append(labeled(crop(d0 / "jogo_2.5.png", hc, 75).resize((TILE, TILE), Image.NEAREST), "zoom 2,5, cabeça ampliada 4×", font))
    rows.append(("na câmera do jogo, com o aldeão", game))
    tilt = []
    for d, t in ((d0, "0° (folha)"), (d20, "20° para trás"), (d35, "35° para trás")):
        tilt.append(tile(d / "cabeca_frente.png", f"{t}, frente", font))
        tilt.append(tile(d / "cabeca_tres_quartos.png", f"{t}, 3/4", font))
    rows.append(("orelha de gato: a mesma peça inclinada para trás pela base", tilt))

    ce = proof["orelha_de_gato"]
    lines = [
        "Protagonista v2 — chifres (piloto): gerados na Meshy, extraídos e encaixados na cabeça do corpo final",
        br(f"{info['triangulos']} triângulos o par (limite 300), material chifre #2B2140, facetados, rígidos, no espaço do corpo em repouso; escala por eixo "
           f"{' / '.join(f'{x:.3f}' for x in info['escala_por_eixo'])}; base afundada no crânio."),
        br(f"Direito {info['por_lado']['direito']['altura_mm']:.0f} mm (ponta a {ce['direito']['ponta_z_m']:.3f} m; topo da cabeça a 0,80 m), esquerdo "
           f"{info['por_lado']['esquerdo']['altura_mm']:.0f} mm; de frente, {ce['direito']['inclinacao_de_frente_graus']}° e {ce['esquerdo']['inclinacao_de_frente_graus']}° "
           f"da vertical; de lado, {ce['direito']['inclinacao_de_lado_graus_para_tras']}° e {ce['esquerdo']['inclinacao_de_lado_graus_para_tras']}° para trás."),
        "Orelha de gato: de frente, a 0° os dois sobem quase na vertical dos cantos de cima da cabeça — o risco é real no close de frente;",
        "   20° para trás tira boa parte da leitura sem perder o chifre; 35° vira toco. Na câmera do jogo (de cima) eles correm ao longo do crânio.",
    ]
    width = TILE * max(len(r[1]) for r in rows)
    header = 20 + 24 * len(lines)
    row_h = rows[0][1][0].height + 30
    sheet = Image.new("RGB", (width, header + row_h * len(rows)), PAPER)
    dr = ImageDraw.Draw(sheet)
    for i, line in enumerate(lines):
        dr.text((10, 8 + 24 * i), line, fill=INK, font=ImageFont.truetype(FONT, 20 if i == 0 else 15))
    y = header
    for label, tiles in rows:
        dr.text((10, y + 4), label, fill=INK, font=ImageFont.truetype(FONT, 17))
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * TILE, y + 30))
        y += row_h
    sheet.save(OUT)
    ImageChops.multiply(sheet, Image.new("RGB", sheet.size, TWILIGHT)).save(OUT.with_name("chifres_prova_crepusculo.png"))
    print(OUT)


if __name__ == "__main__":
    main()

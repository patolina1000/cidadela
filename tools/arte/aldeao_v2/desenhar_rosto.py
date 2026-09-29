"""Atlas de expressões do aldeão v2: olhos.png, boca.png e rosto.json (formato do contrato), mais uma prévia.

Estilo dark-fofo (GDD, seção 17): olhos enormes e redondos, levemente desalinhados e com ar de quem demora a
focar; boca pequena, entreaberta no quadro padrão; traço escuro compatível com o contorno toon; pupilas escuras
com um brilho pequeno em branco osso (#EDE6D6). Tudo é desenhado em 4x e reduzido no fim (antialiasing); fundo
transparente e margem transparente em volta de cada célula.

Olhos: grade 3x3 de células 512x256 (2:1). Boca: grade 4x2 de células 256x128 (2:1), a última célula vazia.
O índice 0 é o quadro padrão. A prévia monta as 9 expressões do GDD sobre um círculo cor de pele.

Uso: uv run desenhar_rosto.py
"""

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/modelos/aldeao_v2/rosto"
PREVIEW = ROOT / "assets/previews/aldeao_v2/expressoes.png"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"

S = 4  # desenha em 4x e reduz
MARGIN = 16  # px transparentes em volta de cada célula (contrato: pelo menos 8)
EYE_CELL, EYE_GRID = (512, 256), (3, 3)
MOUTH_CELL, MOUTH_GRID = (256, 128), (4, 2)

INK = (27, 30, 38)  # traço, na cor do contorno toon
WHITE = (227, 231, 235)  # branco do olho, levemente acinzentado
PUPIL = (21, 23, 28)
BONE = (237, 230, 214)  # brilho da pupila (branco osso da paleta)
TEAR = (207, 227, 241)
MOUTH_IN = (42, 30, 39)
TEETH = (238, 240, 242)
SKIN = (159, 183, 203)  # só na prévia
LINE = 6

# Olhos desalinhados de propósito: o direito (na tela) um pouco menor e mais alto.
LEFT, RL = (150, 138), 72
RIGHT, RR = (352, 130), 66
MOUTH_C = (128, 62)

EYES = ["aberto", "fechado", "meio_fechado", "arregalado", "feliz", "apertado", "preocupado", "bravo", "lagrima"]
MOUTHS = ["entreaberta", "sorriso", "o", "tensa", "triste", "brava", "dormindo"]
# Proposta do mapa expressão (GDD) -> quadros.
EXPRESSIONS = {
    "distraido": ("aberto", "entreaberta"),
    "esforco": ("apertado", "tensa"),
    "feliz": ("feliz", "sorriso"),
    "sonolento": ("meio_fechado", "entreaberta"),
    "dormindo": ("fechado", "dormindo"),
    "espantado": ("arregalado", "o"),
    "preocupado": ("preocupado", "triste"),
    "chorando": ("lagrima", "triste"),
    "bravo": ("bravo", "brava"),
}


def sp(points):
    return [(x * S, y * S) for x, y in points]


def bezier(p0, p1, p2, n=48):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def stroke(draw, points, width=LINE, color=INK):
    draw.line(sp(points), fill=(*color, 255), width=round(width * S), joint="curve")
    for x, y in (points[0], points[-1]):  # pontas redondas
        disc(draw, (x, y), width / 2, color)


def disc(draw, center, r, fill, outline=None, width=0):
    x, y = center
    draw.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(*fill, 255),
                 outline=(*outline, 255) if outline else None, width=round(width * S))


def rotated(point, center, degrees):
    dx, dy = point[0] - center[0], point[1] - center[1]
    a = math.radians(degrees)
    return (center[0] + dx * math.cos(a) - dy * math.sin(a), center[1] + dx * math.sin(a) + dy * math.cos(a))


def eye(cell, center, r, *, look=(0, 0), pupil=20, lid_top=None, lid_bottom=None, tilt=0, side=1):
    """Olho redondo. lid_top / lid_bottom: quanto do olho (px a partir do centro) fica visível acima / abaixo;
    tilt: inclinação das pálpebras em graus (positivo abaixa o lado de dentro); side: +1 olho esquerdo na tela."""
    cx, cy = center
    layer = Image.new("RGBA", cell.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    disc(d, center, r, WHITE)
    px, py = cx + look[0], cy + look[1]
    disc(d, (px, py), pupil, PUPIL)
    disc(d, (px - pupil * 0.35, py - pupil * 0.38), max(3.5, pupil * 0.3), BONE)
    disc(d, center, r, WHITE, outline=INK, width=LINE) if False else d.ellipse(
        [(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], outline=(*INK, 255), width=round(LINE * S))
    if lid_top is not None or lid_bottom is not None:
        angle = tilt * side
        top = cy - (lid_top if lid_top is not None else r + 20)
        bottom = cy + (lid_bottom if lid_bottom is not None else r + 20)
        corners = [rotated(p, center, angle) for p in
                   ((cx - r - 20, top), (cx + r + 20, top), (cx + r + 20, bottom), (cx - r - 20, bottom))]
        mask = Image.new("L", cell.size, 0)
        ImageDraw.Draw(mask).polygon(sp(corners), fill=255)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
        d = ImageDraw.Draw(layer)
        for edge, cut in ((top, lid_top), (bottom, lid_bottom)):
            if cut is None:
                continue
            half = math.sqrt(max(r * r - min(cut, r - 1) ** 2, 0)) + 2
            stroke(d, [rotated((cx - half, edge), center, angle), rotated((cx + half, edge), center, angle)], LINE + 1)
    cell.alpha_composite(layer)


def brow(cell, center, *, width=64, arch=8, tilt=0, dy=0, side=1):
    """Sobrancelha fina: arco. tilt positivo abaixa a ponta de dentro (bravo); negativo levanta (preocupado)."""
    cx, cy = center[0], center[1] + dy
    inner, outer = cx + side * width / 2, cx - side * width / 2
    pts = bezier((inner, cy + tilt), (cx, cy - arch), (outer, cy - tilt))
    stroke(ImageDraw.Draw(cell), pts, LINE - 1)


def closed_eye(cell, center, r, *, up=False):
    cx, cy = center
    d = ImageDraw.Draw(cell)
    if up:  # feliz: arco para cima
        stroke(d, bezier((cx - r + 2, cy + 14), (cx, cy - 50), (cx + r - 2, cy + 14)), LINE + 2)
    else:  # fechado: arco para baixo
        stroke(d, bezier((cx - r + 8, cy + 4), (cx, cy + 40), (cx + r - 8, cy + 4)), LINE + 2)


def tear(cell, tip):
    tx, ty = tip
    d = ImageDraw.Draw(cell)
    for color, grow in ((INK, 2.5), (TEAR, 0)):
        d.polygon(sp([(tx, ty - grow * 1.5), (tx + 9 + grow, ty + 20), (tx - 9 - grow, ty + 20)]), fill=(*color, 255))
        disc(d, (tx, ty + 22), 10 + grow, color)


def draw_eyes(kind: str, cell: Image.Image) -> None:
    (lx, ly), (rx, ry) = LEFT, RIGHT
    bl, br = (lx, ly - RL - 20), (rx, ry - RR - 20)  # sobrancelhas
    if kind == "aberto":
        eye(cell, LEFT, RL, look=(6, 2)), eye(cell, RIGHT, RR, look=(-2, 5), pupil=18)
        brow(cell, bl, side=1), brow(cell, br, side=-1)
    elif kind == "fechado":
        closed_eye(cell, LEFT, RL), closed_eye(cell, RIGHT, RR)
        brow(cell, bl, arch=5, dy=16, side=1), brow(cell, br, arch=5, dy=16, side=-1)
    elif kind == "meio_fechado":
        eye(cell, LEFT, RL, look=(2, 16), pupil=18, lid_top=6), eye(cell, RIGHT, RR, look=(-1, 15), pupil=17, lid_top=5)
        brow(cell, bl, arch=4, dy=14, side=1), brow(cell, br, arch=4, dy=14, side=-1)
    elif kind == "arregalado":
        eye(cell, LEFT, RL + 8, pupil=11), eye(cell, RIGHT, RR + 8, pupil=10)
        brow(cell, bl, arch=12, dy=-10, side=1), brow(cell, br, arch=12, dy=-10, side=-1)
    elif kind == "feliz":
        closed_eye(cell, LEFT, RL, up=True), closed_eye(cell, RIGHT, RR, up=True)
        brow(cell, bl, arch=12, dy=-6, side=1), brow(cell, br, arch=12, dy=-6, side=-1)
    elif kind == "apertado":
        eye(cell, LEFT, RL, pupil=16, lid_top=12, lid_bottom=12, tilt=6, side=1)
        eye(cell, RIGHT, RR, pupil=15, lid_top=11, lid_bottom=11, tilt=6, side=-1)
        brow(cell, bl, arch=2, dy=22, tilt=10, side=1), brow(cell, br, arch=2, dy=22, tilt=10, side=-1)
    elif kind == "preocupado":
        eye(cell, LEFT, RL, look=(5, -8), lid_bottom=RL - 16), eye(cell, RIGHT, RR, look=(-5, -8), pupil=18, lid_bottom=RR - 14)
        brow(cell, bl, arch=4, dy=4, tilt=-9, side=1), brow(cell, br, arch=4, dy=4, tilt=-9, side=-1)
    elif kind == "bravo":
        eye(cell, LEFT, RL, look=(2, 2), pupil=16, lid_top=22, tilt=14, side=1)
        eye(cell, RIGHT, RR, look=(-2, 2), pupil=15, lid_top=20, tilt=14, side=-1)
        brow(cell, bl, arch=2, dy=20, tilt=14, side=1), brow(cell, br, arch=2, dy=20, tilt=14, side=-1)
    elif kind == "lagrima":
        eye(cell, LEFT, RL, look=(0, -4), lid_bottom=RL - 10), eye(cell, RIGHT, RR, look=(-1, -3), pupil=18, lid_bottom=RR - 8)
        brow(cell, bl, arch=4, dy=6, tilt=-6, side=1), brow(cell, br, arch=4, dy=6, tilt=-6, side=-1)
        tear(cell, (lx - 34, ly + RL - 8))
    else:
        raise ValueError(kind)


def draw_mouth(kind: str, cell: Image.Image) -> None:
    cx, cy = MOUTH_C
    d = ImageDraw.Draw(cell)
    if kind == "entreaberta":
        d.ellipse(sp([(cx - 14, cy - 11), (cx + 20, cy + 11)]), fill=(*MOUTH_IN, 255), outline=(*INK, 255), width=round((LINE - 1) * S))
    elif kind == "sorriso":
        stroke(d, bezier((cx - 36, cy - 6), (cx, cy + 34), (cx + 36, cy - 6)))
    elif kind == "o":
        disc(d, (cx + 2, cy), 15, MOUTH_IN, outline=INK, width=LINE - 1)
    elif kind == "tensa":
        stroke(d, [(cx - 32, cy), (cx - 16, cy + 4), (cx, cy - 2), (cx + 16, cy + 4), (cx + 32, cy)])
    elif kind == "triste":
        stroke(d, bezier((cx - 28, cy + 8), (cx, cy - 22), (cx + 28, cy + 8)))
    elif kind == "brava":
        top = bezier((cx - 34, cy + 6), (cx, cy - 26), (cx + 34, cy + 6))
        bottom = bezier((cx + 34, cy + 6), (cx, cy + 16), (cx - 34, cy + 6))
        d.polygon(sp(top + bottom), fill=(*MOUTH_IN, 255))
        teeth = [(x, y) for x, y in top] + [(x, y + 8) for x, y in reversed(top)]
        d.polygon(sp(teeth), fill=(*TEETH, 255))
        stroke(d, top + bottom + [top[0]], LINE - 1)
        for i in (12, 24, 36):  # separação dos dentes
            x, y = top[i]
            stroke(d, [(x, y), (x, y + 8)], 2)
    elif kind == "dormindo":
        disc(d, (cx + 8, cy + 4), 8, MOUTH_IN, outline=INK, width=LINE - 2)
    else:
        raise ValueError(kind)


def atlas(names, cell_size, grid, painter) -> Image.Image:
    w, h = cell_size
    cols, rows = grid
    assert len(names) <= cols * rows
    sheet = Image.new("RGBA", (w * cols, h * rows), (0, 0, 0, 0))
    for i, name in enumerate(names):
        big = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        painter(name, big)
        cell = big.resize((w, h), Image.LANCZOS)
        alpha = np.asarray(cell.getchannel("A"))
        border = np.concatenate([alpha[:MARGIN].ravel(), alpha[-MARGIN:].ravel(), alpha[:, :MARGIN].ravel(), alpha[:, -MARGIN:].ravel()])
        if border.any():
            raise RuntimeError(f"quadro {name!r} invade a margem de {MARGIN} px")
        sheet.paste(cell, ((i % cols) * w, (i // cols) * h))
    return sheet


def preview(eyes: Image.Image, mouths: Image.Image) -> None:
    tile, label_h = 300, 52
    font = ImageFont.truetype(FONT, 22)
    small = ImageFont.truetype(FONT, 17)
    sheet = Image.new("RGB", (tile * 3, (tile + label_h) * 3), (58, 52, 68))
    ew, eh = EYE_CELL
    mw, mh = MOUTH_CELL
    for i, (expression, (eye_name, mouth_name)) in enumerate(EXPRESSIONS.items()):
        x0, y0 = (i % 3) * tile, (i // 3) * (tile + label_h)
        d = ImageDraw.Draw(sheet)
        cx, cy, r = x0 + tile // 2, y0 + tile // 2, 118
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SKIN, outline=INK, width=4)
        e = EYES.index(eye_name)
        eye_cell = eyes.crop(((e % 3) * ew, (e // 3) * eh, (e % 3 + 1) * ew, (e // 3 + 1) * eh)).resize((190, 95), Image.LANCZOS)
        sheet.paste(eye_cell, (cx - 95, cy - 66), eye_cell)
        m = MOUTHS.index(mouth_name)
        mouth_cell = mouths.crop(((m % 4) * mw, (m // 4) * mh, (m % 4 + 1) * mw, (m // 4 + 1) * mh)).resize((96, 48), Image.LANCZOS)
        sheet.paste(mouth_cell, (cx - 48, cy + 34), mouth_cell)
        d.text((x0 + 10, y0 + tile + 2), expression, fill=(235, 230, 220), font=font)
        d.text((x0 + 10, y0 + tile + 28), f"{eye_name} + {mouth_name}", fill=(180, 175, 190), font=small)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(PREVIEW)
    print(PREVIEW.relative_to(ROOT))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    eyes = atlas(EYES, EYE_CELL, EYE_GRID, draw_eyes)
    mouths = atlas(MOUTHS, MOUTH_CELL, MOUTH_GRID, draw_mouth)
    eyes.save(OUT / "olhos.png")
    mouths.save(OUT / "boca.png")
    info = {
        "olhos": {"colunas": EYE_GRID[0], "linhas": EYE_GRID[1], "celulaPx": list(EYE_CELL), "margemPx": MARGIN,
                  "quadros": {name: i for i, name in enumerate(EYES)}},
        "boca": {"colunas": MOUTH_GRID[0], "linhas": MOUTH_GRID[1], "celulaPx": list(MOUTH_CELL), "margemPx": MARGIN,
                 "quadros": {name: i for i, name in enumerate(MOUTHS)}},
        "ossoCabeca": "",
        "passadaWalk": 0.0,
        "expressoes": {name: {"olhos": e, "boca": m} for name, (e, m) in EXPRESSIONS.items()},
    }
    (OUT / "rosto.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for path in ("olhos.png", "boca.png", "rosto.json"):
        print((OUT / path).relative_to(ROOT))
    preview(eyes, mouths)


if __name__ == "__main__":
    main()

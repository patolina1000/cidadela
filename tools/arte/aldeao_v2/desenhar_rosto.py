"""Atlas de expressões do aldeão v2 na direção A1 "Fundos" (aprovada em 29/09/2026): olhos.png, boca.png e
rosto.json no formato do contrato, mais três prévias.

Estilo: olho afundado, sem sobrancelhas; linha de tinta #1B1620 só na pálpebra de cima (grossa no meio, afinando
nas pontas, mais pesada por fora); pálpebra de baixo quase sem linha; esclera branco osso #EDE6D6 com a sombra
da pálpebra no alto; olheira #2B2140 com borda definida por dentro e desfoque só por fora, cobrindo a bolsa;
assimetria (olho direito menor e mais alto, pupilas sem focar no mesmo ponto); tristeza como padrão. Sombreado
sem direção de luz (a luz é do jogo). Cada expressão lê pela silhueta do olho (pálpebras + olheira) a 48 px.

Desenho em 6x, em coordenadas de um rosto de 256 px, e recorto duas janelas: a dos olhos (com a olheira inteira,
desfoque incluído) vira a célula 512x320 (8:5), a da boca vira 256x128 (2:1). Margem transparente de 16 px por
célula, conferida. Olhos 3x3, boca 4x2 (última célula vazia). Índice 0 = padrão.

Uso: uv run desenhar_rosto.py
"""

import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/modelos/aldeao_v2/rosto"
PREVIEWS = ROOT / "assets/previews/aldeao_v2"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"

S = 6  # desenha em 6x
FACE = 256  # o rosto de referência em que tudo é desenhado
MARGIN = 16  # px transparentes por célula (contrato: pelo menos 8)
EYE_CELL, EYE_GRID = (512, 320), (3, 3)
MOUTH_CELL, MOUTH_GRID = (256, 128), (4, 2)
# Janelas no rosto de 256 px que viram as células (mesma proporção das células).
EYE_WINDOW = (24, 78, 232, 208)  # 208 x 130 = 8:5
MOUTH_WINDOW = (110, 170, 174, 202)  # 64 x 32 = 2:1

INK = (27, 22, 32)  # #1B1620
BONE = (237, 230, 214)  # #EDE6D6
SHADOW = (43, 33, 64)  # #2B2140
SKIN = (174, 191, 211)  # só nas prévias
MOUTH_IN = (42, 30, 39)
MOIST = (246, 243, 236)
TWILIGHT = (106, 91, 124)  # #6A5B7C
CAVITY = tuple(round(b * 0.62 + s * 0.38) for b, s in zip(BONE, SHADOW))

L, R = (82, 124), (174, 118)  # centros dos olhos (o direito menor e mais alto)

EYES = ["aberto", "fechado", "meio_fechado", "arregalado", "feliz", "apertado", "preocupado", "bravo", "lagrima"]
MOUTHS = ["entreaberta", "sorriso", "o", "tensa", "triste", "brava", "dormindo"]
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


# ---------- traço de tinta ----------

class Noise:
    def __init__(self, seed: int):
        rng = random.Random(seed)
        self.parts = [(rng.uniform(1.5, 5), rng.uniform(0, math.tau), rng.uniform(0.4, 1)) for _ in range(4)]
        self.total = sum(a for _, _, a in self.parts)

    def __call__(self, t: float) -> float:
        return sum(a * math.sin(math.tau * f * t + p) for f, p, a in self.parts) / self.total


def sp(points):
    return [(x * S, y * S) for x, y in points]


def disc(draw, center, r, color):
    x, y = center
    draw.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=color)


def bezier(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def arc(p0, p2, apex_y, n=40):
    yc = 2 * apex_y - 0.5 * (p0[1] + p2[1])
    return bezier(p0, ((p0[0] + p2[0]) / 2, yc), p2, n)


def stroke(layer, points, width_at, seed, *, jitter=0.5, color=INK, alpha=255):
    """Traço de tinta: discos ao longo do caminho, espessura width_at(t) com ruído leve e desvio lateral."""
    d = ImageDraw.Draw(layer)
    nw, nj = Noise(seed), Noise(seed + 7)
    lengths = [0.0]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
    total = lengths[-1] or 1
    dist, i = 0.0, 0
    while dist <= total:
        while i < len(points) - 2 and lengths[i + 1] < dist:
            i += 1
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        seg = (lengths[i + 1] - lengths[i]) or 1
        u = (dist - lengths[i]) / seg
        x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        nx, ny = -(y1 - y0) / seg, (x1 - x0) / seg
        t = dist / total
        r = width_at(t) / 2 * (1 + 0.25 * nw(t))
        off = jitter * nj(t)
        if r > 0.15:
            disc(d, (x + nx * off, y + ny * off), r, (*color, alpha))
        dist += 0.3


def taper(width, outer_weight=0.3):
    return lambda t: width * math.sin(math.pi * t) ** 0.55 * (1 + outer_weight / 2 - outer_weight * t)


# ---------- olho ----------

class Eye:
    """Forma do olho: canto de dentro, canto de fora (caído), arco de cima e de baixo.
    side=+1: olho esquerdo na tela (o canto de dentro fica à direita)."""

    def __init__(self, center, side, rx, ry_top, ry_bot, droop):
        self.cx, self.cy, self.side = center[0], center[1], side
        self.inner = (self.cx + side * rx, self.cy + 1)
        self.outer = (self.cx - side * rx, self.cy + droop)
        self.upper = arc(self.inner, self.outer, self.cy - ry_top)
        self.lower = arc(self.inner, self.outer, self.cy + ry_bot)
        self.h = ry_top + ry_bot
        self.half_w = rx

    def lid(self, cover_in, cover_out, curve=0.0, straight=False):
        """Pálpebra de cima: cobre cover_in do olho no canto de dentro e cover_out no de fora.
        straight: reta entre as pontas (dura); curve > 0 abaúla para baixo no meio."""
        n = len(self.upper) - 1
        pts = []
        for i, ((ux, uy), (_, ly)) in enumerate(zip(self.upper, self.lower)):
            t = i / n
            cover = cover_in + (cover_out - cover_in) * t + curve * math.sin(math.pi * t)
            pts.append((ux, uy + (ly - uy) * cover))
        if straight:
            (x0, y0), (x1, y1) = pts[0], pts[-1]
            pts = [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n + curve * self.h * math.sin(math.pi * i / n)) for i in range(n + 1)]
        return pts

    def floor(self, raise_amount, flat=False):
        n = len(self.lower) - 1
        pts = []
        for i, ((ux, uy), (lx, ly)) in enumerate(zip(self.upper, self.lower)):
            t = i / n
            k = math.sin(math.pi * t) ** (0.35 if flat else 0.7)
            pts.append((lx, ly - (ly - uy) * raise_amount * k))
        return pts


def olheira(face, eye: Eye, alpha=110, bag=55):
    """Mancha roxa sem direção de luz: borda definida por dentro, desfoque só por fora, bolsa em crescente."""
    cx, cy = eye.cx, eye.cy + eye.h * 0.14
    rx, ry = eye.half_w * 1.16, eye.h * 0.72
    sharp = Image.new("L", face.size, 0)
    ImageDraw.Draw(sharp).ellipse(sp([(cx - rx, cy - ry * 0.8), (cx + rx, cy + ry * 1.0)]), fill=alpha)
    crescent = Image.new("L", face.size, 0)
    cd = ImageDraw.Draw(crescent)
    top = eye.cy + eye.h * 0.22
    cd.ellipse(sp([(cx - rx * 0.86, top), (cx + rx * 0.86, top + ry * 0.62)]), fill=255)
    cd.ellipse(sp([(cx - rx * 0.86, top - ry * 0.55), (cx + rx * 0.86, top + ry * 0.22)]), fill=0)
    crescent = crescent.filter(ImageFilter.GaussianBlur(1.2 * S))
    sharp = ImageChops.add(sharp, crescent.point(lambda v: v * bag // 255))
    soft = sharp.filter(ImageFilter.GaussianBlur(5.0 * S))
    layer = Image.new("RGBA", face.size, (*SHADOW, 0))
    layer.putalpha(ImageChops.lighter(sharp, soft))
    face.alpha_composite(layer)


def draw_eye(face, eye: Eye, *, cover_in, cover_out, pupil, look, raise_lower=0.0, lash=4.2, cavity=0.42,
             moist=False, seed=0, curve=0.0, straight=False, flat_floor=False, closed=False, floor_alpha=95):
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    if closed:  # só a linha dos cílios, grossa e curvada para baixo
        line = eye.lid(0.80, 0.86, curve=0.16)
        stroke(layer, line, taper(5.2, 0.2), seed)
        face.alpha_composite(layer)
        return
    d = ImageDraw.Draw(layer)
    shape = eye.upper + eye.lower[::-1]
    d.polygon(sp(shape), fill=(*BONE, 255))
    band = Image.new("RGBA", face.size, (0, 0, 0, 0))  # sombra da pálpebra na cavidade, sem direção de luz
    ImageDraw.Draw(band).polygon(sp(eye.upper + eye.lid(cavity, cavity + 0.08)[::-1]), fill=(*CAVITY, 255))
    band = band.filter(ImageFilter.GaussianBlur(2.2 * S))
    sclera = Image.new("L", face.size, 0)
    ImageDraw.Draw(sclera).polygon(sp(shape), fill=255)
    band.putalpha(ImageChops.multiply(band.getchannel("A"), sclera))
    layer.alpha_composite(band)
    px, py = eye.cx + look[0], eye.cy + look[1]
    d = ImageDraw.Draw(layer)
    disc(d, (px, py), pupil * 1.35, (*CAVITY, 70))
    disc(d, (px, py), pupil, (*INK, 255))
    lid, floor = eye.lid(cover_in, cover_out, curve, straight), eye.floor(raise_lower, flat_floor)
    mask = Image.new("L", face.size, 0)
    ImageDraw.Draw(mask).polygon(sp(lid + floor[::-1]), fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    stroke(layer, lid, taper(lash), seed)
    stroke(layer, floor[3:-3], lambda t: 1.1 * math.sin(math.pi * t) ** 0.4, seed + 3, alpha=floor_alpha)
    if moist:
        stroke(layer, [(x, y - 1.6) for x, y in floor[5:-5]], lambda t: 1.4 * math.sin(math.pi * t) ** 0.5, seed + 5, color=MOIST, alpha=210)
    face.alpha_composite(layer)


def tear_streak(face, start, length, seed, lean=0.0, width=6.0):
    """Lágrima como risco escuro e grosso escorrendo da olheira até a bochecha (lê a 48 px)."""
    n = Noise(seed)
    pts = [(start[0] + lean * length * i / 30 + 0.6 * n(i / 30), start[1] + length * i / 30) for i in range(31)]
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    stroke(layer, pts, lambda t: width * (1 - 0.5 * t), seed, jitter=0.15, color=SHADOW, alpha=230)
    stroke(layer, pts, lambda t: width * 0.45 * (1 - 0.5 * t), seed + 1, jitter=0.1, color=INK, alpha=140)
    face.alpha_composite(layer)


def eyes_pair(kind: str):
    if kind == "arregalado":  # redondo, totalmente aberto
        return Eye(L, +1, 30, 28, 26, 2), Eye(R, -1, 26, 25, 23, 2)
    return Eye(L, +1, 31, 25, 24, 7), Eye(R, -1, 27, 22, 21, 6)


def draw_eyes(kind: str, face: Image.Image) -> None:
    left, right = eyes_pair(kind)
    under = Image.new("RGBA", face.size, (0, 0, 0, 0))
    olheira(under, left)
    olheira(under, right)
    face.alpha_composite(under)
    seed = 100 + EYES.index(kind) * 10
    for i, eye in enumerate((left, right)):
        s = seed + i * 3
        p = 8 if i == 0 else 7
        if kind == "aberto":  # distraído: pálpebra cobre 1/3, mais pesada por fora, olhar baixo e para o lado
            draw_eye(face, eye, cover_in=0.24, cover_out=0.40, pupil=p, look=(5, 4) if i == 0 else (-1, 5), seed=s)
        elif kind == "meio_fechado":  # sonolento: 2/3 coberto, pupila meio escondida
            draw_eye(face, eye, cover_in=0.62, cover_out=0.72, pupil=p, look=(2, 1) if i == 0 else (-1, 2), lash=4.6, seed=s)
        elif kind == "fechado":  # dormindo e piscar
            draw_eye(face, eye, cover_in=1, cover_out=1, pupil=p, look=(0, 0), closed=True, seed=s)
        elif kind == "feliz":  # alívio cansado: a pálpebra de baixo sobe 1/3, meia-lua deitada
            draw_eye(face, eye, cover_in=0.16, cover_out=0.26, pupil=p, look=(3, -1) if i == 0 else (-2, 0),
                     raise_lower=0.44, flat_floor=True, floor_alpha=200, lash=3.8, seed=s)
        elif kind == "bravo":  # pálpebra reta e dura cobrindo metade, inclinada para o nariz
            draw_eye(face, eye, cover_in=0.64, cover_out=0.36, pupil=p * 0.7, look=(3, 2) if i == 0 else (-3, 2),
                     straight=True, lash=5.0, seed=s)
        elif kind == "arregalado":  # espantado: tudo aberto, pupilas em pontinhos
            draw_eye(face, eye, cover_in=0.02, cover_out=0.05, pupil=3.2, look=(1, 0) if i == 0 else (-2, 1), cavity=0.30, lash=3.6, seed=s)
        elif kind == "preocupado":  # canto interno mais alto (contrário do bravo)
            draw_eye(face, eye, cover_in=0.26, cover_out=0.58, pupil=p, look=(3, -2) if i == 0 else (-2, -1),
                     straight=True, raise_lower=0.12, seed=s)
        elif kind == "apertado":  # esforço: as duas pálpebras apertam até virar uma fenda
            draw_eye(face, eye, cover_in=0.44, cover_out=0.50, pupil=p * 0.8, look=(2, 0) if i == 0 else (-2, 0),
                     raise_lower=0.36, flat_floor=True, floor_alpha=160, lash=4.8, seed=s)
        elif kind == "lagrima":  # chorando: silhueta do preocupado + risco grosso
            draw_eye(face, eye, cover_in=0.28, cover_out=0.60, pupil=p, look=(2, 4) if i == 0 else (-1, 5),
                     straight=True, raise_lower=0.14, moist=True, seed=s)
        else:
            raise ValueError(kind)
    if kind == "lagrima":
        tear_streak(face, (left.outer[0] + 6, left.cy + left.h * 0.64), 40, seed + 7, lean=-0.08, width=6.5)
        tear_streak(face, (right.cx + 4, right.cy + right.h * 0.70), 24, seed + 8, lean=0.05, width=5.0)


# ---------- boca: variações da dobra ----------

def teeth(layer, top_pts, spots):
    """Dentinhos tortos desenhados dentro da dobra, com traço fino e fundo osso."""
    d = ImageDraw.Draw(layer)
    for x0, x1, h in spots:
        ys = {x: y for x, y in top_pts}
        xs = sorted(ys)
        y0 = ys[min(xs, key=lambda x: abs(x - x0))]
        y1 = ys[min(xs, key=lambda x: abs(x - x1))]
        quad = [(x0, y0), (x1, y1), (x1 - 0.8, y1 + h), (x0 + 0.8, y0 + h + 0.6)]
        d.polygon(sp(quad), fill=(*BONE, 255))
        stroke(layer, quad + [quad[0]], lambda t: 0.7, 500 + int(x0), jitter=0.1, alpha=200)


def draw_mouth(kind: str, face: Image.Image) -> None:
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    seed = 300 + MOUTHS.index(kind) * 10
    if kind == "entreaberta":  # padrão: dobra fina, fraca e torta, quase sumindo
        stroke(layer, bezier((131, 184), (141, 188), (152, 185)), taper(1.5, 0), seed, alpha=120)
    elif kind == "sorriso":  # feliz: a dobra alonga e um canto sobe de leve
        stroke(layer, bezier((128, 186), (142, 189), (157, 181)), taper(1.6, 0), seed, alpha=150)
        stroke(layer, [(157, 181), (159, 178)], lambda t: 1.0, seed + 1, alpha=110)
    elif kind == "o":  # espantado: a dobra abre num oval pequeno e torto, escuro por dentro
        oval = [(142 + 8 * math.cos(a) * math.cos(0.2) - 5.5 * math.sin(a) * math.sin(0.2),
                 186 + 8 * math.cos(a) * math.sin(0.2) + 5.5 * math.sin(a) * math.cos(0.2)) for a in (math.tau * i / 40 for i in range(41))]
        d.polygon(sp(oval), fill=(*MOUTH_IN, 255))
        stroke(layer, oval, lambda t: 1.3, seed, jitter=0.2, alpha=200)
        stroke(layer, [(150, 186), (156, 185)], lambda t: 1.0, seed + 1, alpha=110)
        stroke(layer, [(134, 187), (128, 186)], lambda t: 1.0, seed + 2, alpha=110)
    elif kind == "tensa":  # esforço: dobra apertada e mais funda, dentinhos cerrados
        top = bezier((129, 185), (142, 183), (156, 186))
        stroke(layer, top, taper(2.2, 0), seed, alpha=230)
        teeth(layer, top, ((136, 140, 2.6), (143, 148, 3.0), (150, 153, 2.3)))
    elif kind == "triste":  # preocupado, chorando: dobra mais funda, cantos para baixo, torta
        stroke(layer, bezier((130, 188), (142, 182), (155, 189)), taper(1.9, 0), seed, alpha=190)
    elif kind == "brava":  # dobra entreaberta com o interior escuro e dentinhos tortos
        top = bezier((128, 184), (142, 181), (157, 183))
        bottom = bezier((157, 183), (143, 190), (128, 184))
        d.polygon(sp(top + bottom), fill=(*MOUTH_IN, 255))
        stroke(layer, top, taper(2.0, 0), seed, alpha=230)
        stroke(layer, bottom, lambda t: 1.0, seed + 1, alpha=140)
        teeth(layer, top, ((135, 139, 2.8), (143, 148, 3.3), (151, 154, 2.5)))
    elif kind == "dormindo":  # dobra frouxa, um respiro escuro no canto
        stroke(layer, bezier((133, 186), (142, 189), (151, 187)), taper(1.3, 0), seed, alpha=110)
        sliver = bezier((145, 187.2), (149, 186.4), (152, 187)) + bezier((152, 187), (149, 189.2), (145, 187.2))
        d.polygon(sp(sliver), fill=(*MOUTH_IN, 230))
    else:
        raise ValueError(kind)
    face.alpha_composite(layer)


# ---------- atlas ----------

def render_face(painter, name) -> Image.Image:
    face = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
    painter(name, face)
    return face


def cell_from(face: Image.Image, window, cell_size) -> Image.Image:
    x0, y0, x1, y1 = window
    return face.crop((x0 * S, y0 * S, x1 * S, y1 * S)).resize(cell_size, Image.LANCZOS)


def atlas(names, cell_size, grid, painter, window):
    w, h = cell_size
    cols, rows = grid
    sheet = Image.new("RGBA", (w * cols, h * rows), (0, 0, 0, 0))
    faces = {}
    for i, name in enumerate(names):
        face = render_face(painter, name)
        faces[name] = face
        cell = cell_from(face, window, cell_size)
        alpha = np.asarray(cell.getchannel("A"))
        border = np.concatenate([alpha[:MARGIN].ravel(), alpha[-MARGIN:].ravel(), alpha[:, :MARGIN].ravel(), alpha[:, -MARGIN:].ravel()])
        if border.any():
            raise RuntimeError(f"quadro {name!r} invade a margem de {MARGIN} px (alfa máximo {border.max()})")
        sheet.paste(cell, ((i % cols) * w, (i // cols) * h))
    return sheet, faces


# ---------- prévias ----------

def head() -> Image.Image:
    """Esfera sombreada sem direção de luz: pele com vinheta nas bordas."""
    big = FACE * S
    base = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(base).ellipse(sp([(18, 12), (238, 248)]), fill=(*SKIN, 255))
    shade = Image.new("L", (big, big), 0)
    sd = ImageDraw.Draw(shade)
    for i in range(10):
        k = i / 10
        sd.ellipse(sp([(18 + 110 * k, 12 + 118 * k), (238 - 110 * k, 248 - 118 * k)]), fill=int(70 * (1 - k)))
    shade = shade.filter(ImageFilter.GaussianBlur(8 * S))
    dark = Image.new("RGBA", (big, big), (*SHADOW, 0))
    dark.putalpha(ImageChops.multiply(shade, base.getchannel("A")))
    base.alpha_composite(dark)
    return base


def face_from_atlas(eyes, mouths, eye_name, mouth_name) -> Image.Image:
    """Monta o rosto a partir das CÉLULAS do atlas (confere o recorte), sobre a esfera, em 256 px."""
    tile = head().resize((FACE, FACE), Image.LANCZOS)
    ew, eh = EYE_CELL
    mw, mh = MOUTH_CELL
    e = EYES.index(eye_name)
    cell = eyes.crop(((e % 3) * ew, (e // 3) * eh, (e % 3 + 1) * ew, (e // 3 + 1) * eh))
    x0, y0, x1, y1 = EYE_WINDOW
    tile.alpha_composite(cell.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
    m = MOUTHS.index(mouth_name)
    cell = mouths.crop(((m % 4) * mw, (m // 4) * mh, (m % 4 + 1) * mw, (m // 4 + 1) * mh))
    x0, y0, x1, y1 = MOUTH_WINDOW
    tile.alpha_composite(cell.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
    return tile


def twilight(tile: Image.Image) -> Image.Image:
    rgb = ImageChops.multiply(tile.convert("RGB"), Image.new("RGB", tile.size, TWILIGHT))
    return Image.merge("RGBA", (*rgb.split(), tile.getchannel("A")))


def previews(eyes, mouths) -> None:
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    font, small = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 15)
    big, tiny, gap = 256, 48, 20
    # Prévia 1: as 9 expressões sobre a esfera, em 256 e 48 px.
    col_w = big + tiny + gap * 2
    sheet = Image.new("RGBA", (col_w * 3, (big + 60) * 3), (236, 233, 240, 255))
    d = ImageDraw.Draw(sheet)
    faces = {}
    for i, (name, (e, m)) in enumerate(EXPRESSIONS.items()):
        x, y = (i % 3) * col_w, (i // 3) * (big + 60)
        tile = face_from_atlas(eyes, mouths, e, m)
        faces[name] = tile
        sheet.alpha_composite(tile, (x, y))
        sheet.alpha_composite(tile.resize((tiny, tiny), Image.LANCZOS), (x + big + gap, y + big - tiny))
        d.text((x + 8, y + big + 6), name, fill=INK, font=font)
        d.text((x + 8, y + big + 34), f"{e} + {m}", fill=(100, 95, 110), font=small)
    sheet.convert("RGB").save(PREVIEWS / "expressoes.png")
    # Prévia 2: as 9 a 48 px lado a lado, no crepúsculo, sem legenda.
    strip = Image.new("RGBA", ((tiny + 8) * 9 + 8, tiny + 16), (58, 50, 70, 255))
    for i, name in enumerate(EXPRESSIONS):
        strip.alpha_composite(twilight(faces[name].resize((tiny, tiny), Image.LANCZOS)), (8 + i * (tiny + 8), 8))
    strip.convert("RGB").save(PREVIEWS / "expressoes_48px_crepusculo.png")
    # Prévia 3: tira do piscar (aberto -> fechado -> aberto).
    frames = ["aberto", "meio_fechado", "fechado", "meio_fechado", "aberto"]
    size = 160
    blink = Image.new("RGBA", ((size + 12) * len(frames) + 12, size + 24), (236, 233, 240, 255))
    for i, e in enumerate(frames):
        tile = face_from_atlas(eyes, mouths, e, "entreaberta").resize((size, size), Image.LANCZOS)
        blink.alpha_composite(tile, (12 + i * (size + 12), 12))
    blink.convert("RGB").save(PREVIEWS / "piscar.png")
    for name in ("expressoes.png", "expressoes_48px_crepusculo.png", "piscar.png"):
        print((PREVIEWS / name).relative_to(ROOT))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    eyes, _ = atlas(EYES, EYE_CELL, EYE_GRID, draw_eyes, EYE_WINDOW)
    mouths, _ = atlas(MOUTHS, MOUTH_CELL, MOUTH_GRID, draw_mouth, MOUTH_WINDOW)
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
    previews(eyes, mouths)


if __name__ == "__main__":
    main()

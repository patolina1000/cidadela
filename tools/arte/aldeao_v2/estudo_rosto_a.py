"""Estudo 2 do rosto do aldeão v2: quatro variações da direção A ("Olheiras"), mais adultas e mais tristes.

Não toca no atlas nem no rosto.json. Regras: olho afundado (linha forte só na pálpebra de cima, grossa no meio e
afinando nas pontas; pálpebra de baixo quase sem linha); esclera branco osso #EDE6D6 com a sombra da pálpebra
escurecendo a parte de cima; tristeza como padrão (cantos externos caídos, pálpebra mais pesada por fora, pupilas
um pouco para baixo e para o lado); olheiras #2B2140 com borda definida por dentro e desfoque só por fora,
cobrindo também a bolsa embaixo do olho; olhos mais afastados e mais baixos; boca só uma dobra fina e torta no
padrão; sem sobrancelhas; assimetria; tinta #1B1620.

A1 Fundos: olhos grandes, cavidade marcada, pupila média. A2 Caídos: amendoados, canto externo bem caído, pálpebra
cobrindo metade. A3 Sem boca: A1 sem boca no padrão e no feliz. A4 Vidrados: A2 com linha de umidade na pálpebra de
baixo e pupila pequena. Expressões: distraído, feliz (alívio cansado), bravo, chorando (risco escuro, não gota).
Prévia: cabeça oval com volume (sem fundo chapado atrás do rosto), 256 px e 48 px, e a linha de crepúsculo.

Uso: uv run estudo_rosto_a.py
"""

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from estudo_rosto import BONE, FONT, INK, MOUTH_IN, ROOT, S, SHADOW, SKIN, TWILIGHT, Noise, bezier, disc, ink, sp

OUT = ROOT / "assets/previews/aldeao_v2/estudo_rosto_a.png"
FACE = 256
CAVITY = tuple(round(b * 0.62 + s * 0.38) for b, s in zip(BONE, SHADOW))  # esclera na sombra da pálpebra
MOIST = (246, 243, 236)

# Olhos mais afastados e mais baixos que no estudo 1; o da direita menor e um pouco mais alto.
L, R = (82, 124), (174, 118)


def stroke(layer, points, width_at, seed, *, jitter=0.5, color=INK, alpha=255):
    """Traço de tinta com espessura dada por width_at(t), t de 0 a 1 ao longo do caminho."""
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
        dist += 0.35


def arc(p0, p2, apex_y, n=40):
    """Bezier quadrático de p0 a p2 cujo ponto do meio passa pela altura apex_y."""
    yc = 2 * apex_y - 0.5 * (p0[1] + p2[1])
    return bezier(p0, ((p0[0] + p2[0]) / 2, yc), p2, n)


class Eye:
    """Forma do olho: canto de dentro, canto de fora (caído), arco de cima e de baixo. side=+1: olho esquerdo
    na tela (o canto de dentro fica à direita)."""

    def __init__(self, center, side, rx, ry_top, ry_bot, droop):
        self.cx, self.cy, self.side = center[0], center[1], side
        self.inner = (self.cx + side * rx, self.cy + 1)
        self.outer = (self.cx - side * rx, self.cy + droop)
        self.upper = arc(self.inner, self.outer, self.cy - ry_top)
        self.lower = arc(self.inner, self.outer, self.cy + ry_bot)
        self.h = ry_top + ry_bot

    def lid(self, cover_in, cover_out, curve=0.0):
        """Curva da pálpebra de cima: cobre cover_in do olho no canto de dentro e cover_out no de fora."""
        pts = []
        n = len(self.upper) - 1
        for i, ((ux, uy), (_, ly)) in enumerate(zip(self.upper, self.lower)):
            t = i / n
            cover = cover_in + (cover_out - cover_in) * t + curve * math.sin(math.pi * t)
            pts.append((ux, uy + (ly - uy) * cover))
        return pts

    def floor(self, raise_amount):
        pts = []
        n = len(self.lower) - 1
        for i, ((ux, uy), (lx, ly)) in enumerate(zip(self.upper, self.lower)):
            t = i / n
            pts.append((lx, ly - (ly - uy) * raise_amount * math.sin(math.pi * t) ** 0.7))
        return pts


def olheira(face, eye: Eye, alpha=105, bag=55):
    """Mancha roxa com borda definida por dentro e desfoque só por fora, com a bolsa de cansaço embaixo do olho.
    A pele aparece através (alfa parcial); a bolsa é um crescente, não um bloco."""
    cx, cy = eye.cx, eye.cy + eye.h * 0.14
    rx, ry = abs(eye.inner[0] - eye.outer[0]) / 2 * 1.16, eye.h * 0.72
    sharp = Image.new("L", face.size, 0)
    d = ImageDraw.Draw(sharp)
    d.ellipse(sp([(cx - rx, cy - ry * 0.8), (cx + rx, cy + ry * 1.0)]), fill=alpha)
    # Bolsa: crescente colado à pálpebra de baixo (uma elipse menos a elipse do olho deslocada para cima).
    crescent = Image.new("L", face.size, 0)
    cd = ImageDraw.Draw(crescent)
    top = eye.cy + eye.h * 0.22
    cd.ellipse(sp([(cx - rx * 0.86, top), (cx + rx * 0.86, top + ry * 0.62)]), fill=255)
    cd.ellipse(sp([(cx - rx * 0.86, top - ry * 0.55), (cx + rx * 0.86, top + ry * 0.22)]), fill=0)
    crescent = crescent.filter(ImageFilter.GaussianBlur(1.2 * S))
    sharp = ImageChops.add(sharp, crescent.point(lambda v: v * bag // 255))
    soft = sharp.filter(ImageFilter.GaussianBlur(5.5 * S))
    combined = ImageChops.lighter(sharp, soft)  # dentro: a borda nítida; fora: só o desfoque
    layer = Image.new("RGBA", face.size, (*SHADOW, 0))
    layer.putalpha(combined)
    face.alpha_composite(layer)


def draw_eye(face, eye: Eye, *, cover_in, cover_out, pupil, look, raise_lower=0.0, lash=4.2, cavity=0.42,
             moist=False, seed=0, curve=0.0):
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    shape = eye.upper + eye.lower[::-1]
    d.polygon(sp(shape), fill=(*BONE, 255))
    # Sombra da pálpebra dentro da cavidade: faixa escura no alto do olho, desfocada e presa à esclera.
    band = Image.new("RGBA", face.size, (0, 0, 0, 0))
    ImageDraw.Draw(band).polygon(sp(eye.upper + eye.lid(cavity, cavity + 0.12)[::-1]), fill=(*CAVITY, 255))
    band = band.filter(ImageFilter.GaussianBlur(2.2 * S))
    sclera = Image.new("L", face.size, 0)
    ImageDraw.Draw(sclera).polygon(sp(shape), fill=255)
    band.putalpha(ImageChops.multiply(band.getchannel("A"), sclera))
    layer.alpha_composite(band)
    px, py = eye.cx + look[0], eye.cy + look[1]
    disc(d, (px, py), pupil, (*INK, 255))
    disc(d, (px, py), pupil * 1.35, (*CAVITY, 70))  # íris fraca em volta da pupila
    disc(d, (px, py), pupil, (*INK, 255))
    # Recorte pelas pálpebras.
    lid, floor = eye.lid(cover_in, cover_out, curve), eye.floor(raise_lower)
    mask = Image.new("L", face.size, 0)
    ImageDraw.Draw(mask).polygon(sp(lid + floor[::-1]), fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    # Linha dos cílios: grossa no meio, afinando nas pontas; mais pesada do lado de fora.
    stroke(layer, lid, lambda t: lash * math.sin(math.pi * t) ** 0.55 * (1.15 - 0.3 * t), seed)
    # Pálpebra de baixo: só um traço fino e fraco.
    stroke(layer, floor[3:-3], lambda t: 1.1 * math.sin(math.pi * t) ** 0.4, seed + 3, alpha=95)
    if moist:  # linha de umidade clara por dentro da pálpebra de baixo
        wet = [(x, y - 1.6) for x, y in floor[5:-5]]
        stroke(layer, wet, lambda t: 1.4 * math.sin(math.pi * t) ** 0.5, seed + 5, color=MOIST, alpha=210)
    face.alpha_composite(layer)


def tear_streak(face, start, length, seed, lean=0.12):
    """Lágrima como risco escuro escorrendo da olheira: quase reto, com leve ondulação, afinando."""
    n = Noise(seed)
    pts = [(start[0] + lean * length * i / 30 + 0.7 * n(i / 30), start[1] + length * i / 30) for i in range(31)]
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    stroke(layer, pts, lambda t: 1.9 * (1 - 0.65 * t), seed, jitter=0.15, color=SHADOW, alpha=210)
    stroke(layer, pts[:10], lambda t: 1.1, seed + 1, jitter=0.1, color=INK, alpha=110)
    face.alpha_composite(layer)


def mouth(face, kind, seed, *, fold=True):
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if kind == "distraido":
        if fold:  # dobra fina, fraca e torta, quase sumindo
            stroke(layer, bezier((131, 184), (141, 188), (152, 185)), lambda t: 1.5 * math.sin(math.pi * t) ** 0.5, seed, alpha=120)
    elif kind == "feliz":
        if fold:  # alívio cansado: a dobra alonga e um canto sobe de leve
            stroke(layer, bezier((128, 186), (142, 189), (157, 181)), lambda t: 1.6 * math.sin(math.pi * t) ** 0.5, seed, alpha=150)
            stroke(layer, [(157, 181), (159, 178)], lambda t: 1.0, seed + 1, alpha=110)
    elif kind == "bravo":  # pequena, torta, escura por dentro, dentinhos tortos
        pts = [(126, 182), (140, 178), (155, 176), (157, 186), (143, 190), (130, 190), (126, 182)]
        d.polygon(sp(pts), fill=(*MOUTH_IN, 255))
        for x0, x1, h in ((133, 138, 5), (141, 147, 7), (149, 153, 4)):
            y0 = 178 + (x0 - 126) * (176 - 182) / 29 + 0.5
            y1 = 178 + (x1 - 126) * (176 - 182) / 29 + 0.5
            d.polygon(sp([(x0, y0), (x1, y1), (x1 - 1, y1 + h), (x0 + 1, y0 + h + 1)]), fill=(*BONE, 255))
        stroke(layer, pts, lambda t: 2.2 * (0.7 + 0.3 * math.sin(math.pi * t)), seed, jitter=0.4)
    elif kind == "chorando":  # pequena, torta, puxada para baixo, escura por dentro
        pts = [(130, 186), (141, 183), (152, 185), (151, 190), (140, 192), (132, 190), (130, 186)]
        d.polygon(sp(pts), fill=(*MOUTH_IN, 255))
        stroke(layer, pts, lambda t: 1.8 * (0.7 + 0.3 * math.sin(math.pi * t)), seed, jitter=0.4)
    face.alpha_composite(layer)


# ---------- variações ----------

def eyes_for(variant: str):
    if variant in ("A1", "A3"):  # fundos: grandes, cavidade marcada
        return Eye(L, +1, 31, 25, 24, 7), Eye(R, -1, 27, 22, 21, 6)
    return Eye(L, +1, 33, 19, 16, 13), Eye(R, -1, 29, 17, 14, 11)  # caídos: amendoados, canto bem caído


def face_of(variant: str, kind: str) -> Image.Image:
    face = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
    left, right = eyes_for(variant)
    deep = variant in ("A1", "A3")
    pupil = (8, 7) if deep else (7, 6)
    if variant == "A4":
        pupil = (5, 4.5)
    cover = 0.30 if deep else 0.50
    cavity = 0.42 if deep else 0.30
    base = dict(pupil=pupil, cover=cover, cavity=cavity, moist=variant == "A4")
    seed = {"A1": 100, "A2": 200, "A3": 300, "A4": 400}[variant]

    for i, (eye, side) in enumerate(((left, +1), (right, -1))):
        p = base["pupil"][i]
        k = dict(pupil=p, cavity=cavity, moist=base["moist"], seed=seed + i * 10)
        if kind == "distraido":
            look = (3 * side + 2, 4) if i == 0 else (-1, 5)  # para baixo e para o lado, sem focar no mesmo ponto
            draw_eye(face, eye, cover_in=cover - 0.06, cover_out=cover + 0.10, look=look, **k)
        elif kind == "feliz":
            look = (2, 1) if i == 0 else (-2, 2)
            draw_eye(face, eye, cover_in=cover - 0.08, cover_out=cover + 0.04, look=look, raise_lower=0.30, lash=3.8, **k)
        elif kind == "bravo":
            look = (3, 1) if i == 0 else (-3, 1)
            k["pupil"] = p * 0.7
            draw_eye(face, eye, cover_in=cover + 0.22, cover_out=cover + 0.02, look=look, lash=5.0, curve=-0.04, **k)
        elif kind == "chorando":
            look = (2, 6) if i == 0 else (-1, 7)
            draw_eye(face, eye, cover_in=cover + 0.02, cover_out=cover + 0.16, look=look, raise_lower=0.16, moist=True, **{kk: v for kk, v in k.items() if kk != "moist"})
    # olheiras entram por baixo dos olhos: desenhadas antes, numa camada própria
    under = Image.new("RGBA", face.size, (0, 0, 0, 0))
    olheira(under, left, alpha=110 if deep else 100)
    olheira(under, right, alpha=110 if deep else 100)
    under.alpha_composite(face)
    face = under
    if kind == "chorando":
        tear_streak(face, (left.outer[0] + 5, left.cy + left.h * 0.72), 44, seed + 7, lean=-0.10)
        tear_streak(face, (right.cx + 3, right.cy + right.h * 0.78), 24, seed + 8, lean=0.06)
    mouth(face, kind, seed + 30, fold=variant != "A3")
    return face


# ---------- prévia ----------

def head(size: int) -> Image.Image:
    """Cabeça oval com volume suave (sem fundo chapado): cor de pele com sombra nas bordas e nas órbitas."""
    big = FACE * S
    base = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.ellipse(sp([(18, 12), (238, 248)]), fill=(*SKIN, 255))
    shade = Image.new("L", (big, big), 0)
    sd = ImageDraw.Draw(shade)
    for i in range(10):  # vinheta radial: mais escuro na borda
        k = 1 - i / 10
        sd.ellipse(sp([(18 + 110 * (1 - k), 12 + 118 * (1 - k)), (238 - 110 * (1 - k), 248 - 118 * (1 - k))]), fill=int(70 * (1 - k)))
    shade = shade.filter(ImageFilter.GaussianBlur(8 * S))
    dark = Image.new("RGBA", (big, big), (*SHADOW, 0))
    dark.putalpha(ImageChops.multiply(shade, base.getchannel("A")))
    base.alpha_composite(dark)
    return base


def compose(face: Image.Image, size: int, twilight=False) -> Image.Image:
    tile = head(size)
    tile.alpha_composite(face)
    tile = tile.resize((size, size), Image.LANCZOS)
    if twilight:
        rgb = ImageChops.multiply(tile.convert("RGB"), Image.new("RGB", tile.size, TWILIGHT))
        tile = Image.merge("RGBA", (*rgb.split(), tile.getchannel("A")))
    return tile


def main() -> None:
    variants = [("A1  Fundos", "A1"), ("A2  Caídos", "A2"), ("A3  Sem boca", "A3"), ("A4  Vidrados", "A4")]
    kinds = ["distraido", "feliz", "bravo", "chorando"]
    big, small, gap, label_w, header = 256, 48, 20, 150, 44
    col_w = big + small + gap * 2
    width = label_w + col_w * len(kinds)
    height = header + (big + gap) * 5
    sheet = Image.new("RGBA", (width, height), (236, 233, 240, 255))
    d = ImageDraw.Draw(sheet)
    font, small_font = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 15)
    for c, kind in enumerate(kinds):
        d.text((label_w + c * col_w, 12), kind, fill=INK, font=font)
    faces = {}
    for row, (name, variant) in enumerate(variants):
        y = header + row * (big + gap)
        d.text((10, y + 8), name, fill=INK, font=font)
        d.text((10, y + 36), "256 px e 48 px", fill=(100, 95, 110), font=small_font)
        for c, kind in enumerate(kinds):
            x = label_w + c * col_w
            face = face_of(variant, kind)
            faces[(variant, kind)] = face
            sheet.alpha_composite(compose(face, big), (x, y))
            sheet.alpha_composite(compose(face, small), (x + big + gap, y + big - small))
    y = header + 4 * (big + gap)
    d.text((10, y + 8), "crepúsculo", fill=INK, font=font)
    d.text((10, y + 36), "x #6A5B7C, distraído", fill=(100, 95, 110), font=small_font)
    for c, (name, variant) in enumerate(variants):
        x = label_w + c * col_w
        face = faces[(variant, "distraido")]
        sheet.alpha_composite(compose(face, big, twilight=True), (x, y))
        sheet.alpha_composite(compose(face, small, twilight=True), (x + big + gap, y + big - small))
        d.text((x, y + big + 2), name, fill=INK, font=small_font)
    sheet.convert("RGB").save(OUT)
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

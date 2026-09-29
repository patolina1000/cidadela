"""Estudo de direção do rosto do aldeão v2 (não toca no atlas nem no rosto.json).

Três direções (A "Olheiras", B "Vazio", C "Tinta") x três expressões (distraído, feliz, bravo), sobre a cor de
pele #AEBFD3, em 256 px e 48 px (tamanho aproximado na câmera do jogo), e uma linha com as três direções
escurecidas pelo roxo do crepúsculo (multiplicação por #6A5B7C). Regras comuns: sem sobrancelhas; a emoção vem
das pálpebras e das pupilas; assimetria sempre; traço de tinta à mão (espessura variável, levemente irregular)
em #1B1620; boca pequena, torta, fora de centro, com o interior escuro.

Uso: uv run estudo_rosto.py
"""

import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/aldeao_v2/estudo_rosto.png"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"

S = 4  # desenha em 4x e reduz
FACE = 256
SKIN = (174, 191, 211)  # #AEBFD3
INK = (27, 22, 32)  # #1B1620
BONE = (237, 230, 214)  # #EDE6D6
SHADOW = (43, 33, 64)  # #2B2140, olheira
MOUTH_IN = (42, 30, 39)
TWILIGHT = (106, 91, 124)  # #6A5B7C

# Olhos assimétricos: o da direita (na tela) menor e mais alto.
L, R = (92, 112), (166, 105)


class Noise:
    """Ruído 1D suave (soma de senos com fases aleatórias), em [-1, 1]."""

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


def ellipse_path(center, rx, ry, n=90):
    cx, cy = center
    return [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in (math.tau * i / n for i in range(n + 1))]


def ink(layer, points, width, seed, *, wobble=0.35, jitter=0.7, color=INK, alpha=255):
    """Traço de tinta à mão: discos ao longo do caminho, com raio e desvio lateral variando por ruído."""
    d = ImageDraw.Draw(layer)
    nw, nj = Noise(seed), Noise(seed + 7)
    lengths = [0.0]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
    total = lengths[-1] or 1
    step, dist, i = 0.35, 0.0, 0
    while dist <= total:
        while i < len(points) - 2 and lengths[i + 1] < dist:
            i += 1
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        seg = (lengths[i + 1] - lengths[i]) or 1
        u = (dist - lengths[i]) / seg
        x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        nx, ny = -(y1 - y0) / seg, (x1 - x0) / seg
        t = dist / total
        off = jitter * nj(t)
        r = width / 2 * (1 + wobble * nw(t))
        disc(d, (x + nx * off, y + ny * off), max(r, 0.4), (*color, alpha))
        dist += step


def lid(layer, center, rx, ry, *, top=True, cover=0.33, tilt=0.0, arch=0.12, seed=0, line=3.2):
    """Pálpebra: recorta o olho (máscara de alfa) numa curva e desenha a borda em tinta, de borda a borda do
    olho (sem sobrar ponta). cover: fração do olho coberta; tilt: px que o lado de dentro (a direita, para o
    olho esquerdo na tela) desce; arch: curvatura (positivo = pálpebra pesada no meio)."""
    cx, cy = center
    y0 = cy - ry + 2 * ry * cover if top else cy + ry - 2 * ry * cover

    def half(y):
        return rx * math.sqrt(max(1 - ((y - cy) / ry) ** 2, 0.02))

    ya, yb = y0 - tilt, y0 + tilt
    curve = bezier((cx - half(ya), ya), (cx, y0 + arch * ry * (1 if top else -1)), (cx + half(yb), yb))
    far = cy + ry + 30 if top else cy - ry - 30
    keep = curve + [(cx + rx + 40, curve[-1][1]), (cx + rx + 40, far), (cx - rx - 40, far), (cx - rx - 40, curve[0][1])]
    mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(mask).polygon(sp(keep), fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    ink(layer, curve[1:-1], line, seed, wobble=0.45, jitter=0.4)


def shadow(face, center, r, alpha):
    """Olheira roxa semitransparente em volta e embaixo do olho."""
    cx, cy = center
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse(sp([(cx - r * 1.12, cy - r * 0.75), (cx + r * 1.12, cy + r * 1.35)]), fill=(*SHADOW, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(3.0 * S))
    face.alpha_composite(layer)


# ---------- direções ----------

def eye_a(face, center, r, *, pupil, look, cover, tilt=0.0, bottom=None, seed=0, olheira=90, arch=0.12):
    """A "Olheiras": esclera branco osso, pupila pequena, pálpebra superior pesada, olheira roxa."""
    shadow(face, center, r, olheira)
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse(sp([(cx - r, cy - r * 0.96), (cx + r, cy + r * 0.96)]), fill=(*BONE, 255))
    disc(d, (cx + look[0], cy + look[1]), pupil, (*INK, 255))
    ink(layer, ellipse_path(center, r, r * 0.96), 2.8, seed, wobble=0.4)
    lid(layer, center, r, r * 0.96, top=True, cover=cover, tilt=tilt, arch=arch, seed=seed + 3, line=3.6)
    if bottom:
        lid(layer, center, r, r * 0.96, top=False, cover=bottom, arch=0.45, seed=seed + 5, line=2.4)
    face.alpha_composite(layer)


def eye_b(face, center, rx, ry, *, glint, glint_r, cover, tilt=0.0, bottom=None, seed=0, arch=0.12):
    """B "Vazio": oval escuro sem esclera, um brilho pequeno fora de centro; as pálpebras recortam o oval."""
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse(sp([(cx - rx, cy - ry), (cx + rx, cy + ry)]), fill=(*INK, 255))
    ink(layer, ellipse_path(center, rx, ry), 2.2, seed, wobble=0.5, jitter=0.9)
    disc(d, (cx + glint[0], cy + glint[1]), glint_r, (*BONE, 255))
    lid(layer, center, rx, ry, top=True, cover=cover, tilt=tilt, arch=arch, seed=seed + 3, line=3.4)
    if bottom:
        lid(layer, center, rx, ry, top=False, cover=bottom, arch=0.45, seed=seed + 5, line=2.4)
    face.alpha_composite(layer)


def eye_c(face, center, r, *, pupil, look, cover=None, tilt=0.0, bottom=None, seed=0):
    """C "Tinta": olho médio só de contorno rabiscado (a pele aparece dentro), pupila de tamanho variável."""
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse(sp([(cx - r, cy - r * 0.92), (cx + r, cy + r * 0.92)]), fill=(*SKIN, 255))  # base para o recorte
    disc(d, (cx + look[0], cy + look[1]), pupil, (*INK, 255))
    ink(layer, ellipse_path(center, r, r * 0.92), 2.4, seed, wobble=0.6, jitter=1.3)
    ink(layer, ellipse_path(center, r * 1.02, r * 0.9), 1.4, seed + 11, wobble=0.8, jitter=1.8, alpha=170)
    if cover:
        lid(layer, center, r, r * 0.92, top=True, cover=cover, tilt=tilt, seed=seed + 3, line=3.0)
        y0 = cy - r * 0.92 + 2 * r * 0.92 * cover
        ink(layer, bezier((cx - r * 0.7, y0 - tilt * 0.7 + 3), (cx, y0 + 5), (cx + r * 0.7, y0 + tilt * 0.7 + 3)), 1.3, seed + 4, jitter=1.5, alpha=150)
    if bottom:
        lid(layer, center, r, r * 0.92, top=False, cover=bottom, arch=0.45, seed=seed + 5, line=2.2)
    face.alpha_composite(layer)


# ---------- bocas ----------

def mouth(face, kind: str, seed: int):
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if kind == "distraido":  # oval pequeno e torto, fora de centro
        pts = [(138 + 9 * math.cos(a) * math.cos(0.25) - 5.5 * math.sin(a) * math.sin(0.25),
                178 + 9 * math.cos(a) * math.sin(0.25) + 5.5 * math.sin(a) * math.cos(0.25)) for a in
               (math.tau * i / 40 for i in range(41))]
    elif kind == "feliz":  # um canto sobe; abertura fina e inclinada
        pts = [(124, 181), (136, 178), (149, 168), (154, 172), (140, 181), (127, 185), (124, 181)]
    elif kind == "bravo":  # abertura torta com dentinhos tortos
        pts = [(122, 176), (137, 172), (152, 169), (154, 180), (140, 185), (128, 186), (122, 176)]
    else:
        raise ValueError(kind)
    d.polygon(sp(pts), fill=(*MOUTH_IN, 255))
    if kind == "bravo":
        for x0, x1, h in ((130, 136, 6), (139, 146, 8), (148, 152, 5)):
            top0 = 172 + (x0 - 122) * (169 - 176) / 30 + 1
            top1 = 172 + (x1 - 122) * (169 - 176) / 30 + 1
            d.polygon(sp([(x0, top0), (x1, top1), (x1 - 1, top1 + h), (x0 + 1, top0 + h + 1)]), fill=(*BONE, 255))
    ink(layer, pts, 2.6, seed, wobble=0.5, jitter=0.6)
    face.alpha_composite(layer)


# ---------- rostos ----------

def face_a(kind: str) -> Image.Image:
    face = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
    if kind == "distraido":
        eye_a(face, L, 30, pupil=7, look=(5, 3), cover=0.34, seed=1)
        eye_a(face, R, 26, pupil=6.5, look=(-6, 5), cover=0.30, seed=2)
    elif kind == "feliz":
        eye_a(face, L, 30, pupil=8, look=(3, -1), cover=0.22, bottom=0.34, seed=3, olheira=70, arch=-0.04)
        eye_a(face, R, 26, pupil=7.5, look=(4, -3), cover=0.18, bottom=0.38, seed=4, olheira=70, arch=-0.04)
    else:
        eye_a(face, L, 30, pupil=5, look=(4, 2), cover=0.50, tilt=7, seed=5, olheira=110)
        eye_a(face, R, 26, pupil=4.5, look=(-2, 3), cover=0.46, tilt=-6, seed=6, olheira=110)
    mouth(face, kind, 30)
    return face


def face_b(kind: str) -> Image.Image:
    face = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
    if kind == "distraido":
        eye_b(face, L, 22, 30, glint=(-7, -10), glint_r=4.5, cover=0.16, seed=11)
        eye_b(face, R, 19, 26, glint=(-3, -14), glint_r=3.8, cover=0.12, seed=12)
    elif kind == "feliz":
        eye_b(face, L, 22, 30, glint=(-6, -5), glint_r=5.2, cover=0.14, bottom=0.34, seed=13, arch=-0.03)
        eye_b(face, R, 19, 26, glint=(-2, -8), glint_r=4.6, cover=0.10, bottom=0.38, seed=14, arch=-0.03)
    else:
        eye_b(face, L, 22, 30, glint=(-6, -2), glint_r=3, cover=0.50, tilt=8, seed=15)
        eye_b(face, R, 19, 26, glint=(-2, -4), glint_r=2.6, cover=0.46, tilt=-7, seed=16)
    mouth(face, kind, 40)
    return face


def face_c(kind: str) -> Image.Image:
    face = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
    lc, rc = (94, 112), (164, 107)
    if kind == "distraido":
        eye_c(face, lc, 20, pupil=9, look=(3, 3), seed=21)
        eye_c(face, rc, 18, pupil=5, look=(-5, -1), seed=22)
    elif kind == "feliz":
        eye_c(face, lc, 20, pupil=7, look=(2, -2), bottom=0.40, seed=23)
        eye_c(face, rc, 18, pupil=6, look=(3, -3), bottom=0.44, seed=24)
    else:
        eye_c(face, lc, 20, pupil=4, look=(3, 2), cover=0.45, tilt=6, seed=25)
        eye_c(face, rc, 18, pupil=3.5, look=(-2, 3), cover=0.42, tilt=-5, seed=26)
    mouth(face, kind, 50)
    return face


# ---------- prévia ----------

def on_skin(face: Image.Image, size: int) -> Image.Image:
    tile = Image.new("RGBA", face.size, (*SKIN, 255))
    tile.alpha_composite(face)
    return tile.resize((size, size), Image.LANCZOS).convert("RGB")


def twilight(image: Image.Image) -> Image.Image:
    return ImageChops.multiply(image, Image.new("RGB", image.size, TWILIGHT))


def main() -> None:
    directions = [("A  Olheiras", face_a), ("B  Vazio", face_b), ("C  Tinta", face_c)]
    kinds = ["distraido", "feliz", "bravo"]
    big, small, gap, label_w, header = 256, 48, 24, 150, 44
    col_w = big + small + gap * 2
    width = label_w + col_w * 3
    height = header + (big + gap) * 4
    sheet = Image.new("RGB", (width, height), (232, 228, 236))
    d = ImageDraw.Draw(sheet)
    font, small_font = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 15)
    for c, kind in enumerate(kinds):
        d.text((label_w + c * col_w, 12), kind, fill=INK, font=font)
    faces = {}
    for row, (name, painter) in enumerate(directions):
        y = header + row * (big + gap)
        d.text((10, y + 8), name, fill=INK, font=font)
        d.text((10, y + 36), "256 px e 48 px", fill=(100, 95, 110), font=small_font)
        for c, kind in enumerate(kinds):
            x = label_w + c * col_w
            face = painter(kind)
            faces[(row, kind)] = face
            sheet.paste(on_skin(face, big), (x, y))
            sheet.paste(on_skin(face, small), (x + big + gap, y + big - small))
    y = header + 3 * (big + gap)
    d.text((10, y + 8), "crepúsculo", fill=INK, font=font)
    d.text((10, y + 36), "x #6A5B7C, distraído", fill=(100, 95, 110), font=small_font)
    for c, (name, _) in enumerate(directions):
        x = label_w + c * col_w
        face = faces[(c, "distraido")]
        sheet.paste(twilight(on_skin(face, big)), (x, y))
        sheet.paste(twilight(on_skin(face, small)), (x + big + gap, y + big - small))
        d.text((x, y + big + 2), name, fill=INK, font=small_font)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

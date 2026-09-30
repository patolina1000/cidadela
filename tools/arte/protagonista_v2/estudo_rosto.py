"""Protagonista v2, passo 4: estudo do rosto, 3 variações da expressão neutra_cansada (contrato, seção ROSTO).

Traços do contrato: olhos amendoados sem pupila; 3 cílios longos no canto externo; olheira mais funda que a do aldeão;
fissura fina sob o olho esquerdo (o esquerdo DELA: à direita na tela); boca reta e curta. Entre as variações mudam
o tamanho dos olhos, a inclinação dos cantos e a força da olheira. Neutra cansada: pálpebra de cima pesada (cobre
~40% do olho), olhar vazio.

Mesmo sistema do aldeão (aldeao_v2/desenhar_rosto.py): desenho em 6x num rosto de referência de 256 px, janela dos
olhos (24, 78, 232, 208) vira a célula 512×320 e a da boca (110, 170, 174, 202) a célula 256×128, com 16 px de
margem transparente; assim os retalhos usam as mesmas janelas (EYES_FRAC, MOUTH_FRAC). Tinta #1B1620, esclera osso
#EDE6D6, olheira roxo #2B2140.

Saída: assets/previews/protagonista_v2/rosto_estudo/<variação>_{olhos,boca}.png (uma célula cada: é estudo, não o
atlas) e estudo_rosto_2d.png (as três num rosto chapado da cor da pele, 256 e 64 px).

Uso (em tools/arte): uv run protagonista_v2/estudo_rosto.py
"""

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aldeao_v2"))
from desenhar_rosto import (BONE, EYE_CELL, EYE_WINDOW, FACE, INK, MARGIN, MOUTH_CELL, MOUTH_WINDOW, S, SHADOW,  # noqa: E402
                            Noise, arc, bezier, sp, stroke, taper)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2/rosto_estudo"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
SKIN = (145, 173, 183)  # #91ADB7, só nas prévias
TWILIGHT = (106, 91, 124)
CAVITY = tuple(round(b * 0.62 + s * 0.38) for b, s in zip(BONE, SHADOW))

# Centros dos olhos no rosto de 256 px (esquerdo DELA à direita na tela). Mais afastados que no aldeão: amendoados
# são mais largos que altos.
LEFT_SCREEN, RIGHT_SCREEN = (84, 128), (172, 128)

VARIANTS = {
    # tamanho (meia-largura, altura de cima, de baixo), queda do canto externo em px (+ = caído), olheira (força, largura)
    "a": {"nome": "a: médios, canto caído", "rx": 30, "top": 19, "bot": 13, "queda": 6, "olheira": (125, 0.92)},
    "b": {"nome": "b: grandes, cantos retos", "rx": 35, "top": 22, "bot": 15, "queda": -1, "olheira": (150, 0.95)},
    "c": {"nome": "c: menores, bem caído", "rx": 26, "top": 16, "bot": 11, "queda": 12, "olheira": (180, 1.02)},
}


class Almond:
    """Olho amendoado: cantos em ponta, arco de cima mais alto que o de baixo. side=+1: o canto de dentro fica à
    direita (olho à esquerda na tela)."""

    def __init__(self, center, side, rx, top, bot, droop):
        self.cx, self.cy, self.side = center[0], center[1], side
        self.inner = (self.cx + side * rx, self.cy - 1)
        self.outer = (self.cx - side * rx, self.cy + droop)
        self.upper = self._curve(self.inner, self.outer, -top)
        self.lower = self._curve(self.inner, self.outer, bot)
        self.h, self.top, self.half_w, self.droop = top + bot, top, rx, droop

    @staticmethod
    def _curve(p0, p2, bulge, n=48):
        # arco mais cheio perto do canto de dentro (amêndoa): controle deslocado para dentro
        c = (p0[0] * 0.58 + p2[0] * 0.42, (p0[1] + p2[1]) / 2 + 2 * bulge)
        return bezier(p0, c, p2, n)

    def lid(self, cover_in, cover_out):
        n = len(self.upper) - 1
        return [(ux, uy + (ly - uy) * (cover_in + (cover_out - cover_in) * i / n))
                for i, ((ux, uy), (_, ly)) in enumerate(zip(self.upper, self.lower))]


def deep_olheira(face, eye: Almond, strength, spread):
    """Olheira mais funda que a do aldeão: mancha maior e mais opaca, borda nítida por dentro, bolsa em crescente
    escura embaixo, desfoque só por fora."""
    cx, cy = eye.cx - eye.side * eye.half_w * 0.06, eye.cy + eye.h * 0.22
    rx, ry = eye.half_w * 1.12 * spread, eye.h * 0.78 * spread
    sharp = Image.new("L", face.size, 0)
    ImageDraw.Draw(sharp).ellipse(sp([(cx - rx, cy - ry * 0.85), (cx + rx, cy + ry * 1.05)]), fill=strength)
    bag = Image.new("L", face.size, 0)
    bd = ImageDraw.Draw(bag)
    top = eye.cy + eye.h * 0.35
    bd.ellipse(sp([(cx - rx * 0.9, top), (cx + rx * 0.9, top + ry * 0.95)]), fill=255)
    bd.ellipse(sp([(cx - rx * 0.9, top - ry * 0.6), (cx + rx * 0.9, top + ry * 0.35)]), fill=0)
    bag = bag.filter(ImageFilter.GaussianBlur(1.0 * S))
    sharp = ImageChops.lighter(sharp, bag.point(lambda v: min(255, v * (strength + 40) // 255)))
    soft = sharp.filter(ImageFilter.GaussianBlur(4.5 * S))
    layer = Image.new("RGBA", face.size, (*SHADOW, 0))
    layer.putalpha(ImageChops.lighter(sharp, soft).point(lambda v: 0 if v < 12 else v))
    face.alpha_composite(layer)


def draw_almond(face, eye: Almond, seed):
    """Esclera sem pupila, sombra da pálpebra por cima, pálpebra pesada (neutra cansada), linha fraca embaixo e três
    cílios longos no canto externo."""
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    shape = eye.upper + eye.lower[::-1]
    d.polygon(sp(shape), fill=(*BONE, 255))
    lid = eye.lid(0.28, 0.40)
    band = Image.new("RGBA", face.size, (0, 0, 0, 0))
    ImageDraw.Draw(band).polygon(sp(eye.upper + eye.lid(0.44, 0.54)[::-1]), fill=(*CAVITY, 170))
    band = band.filter(ImageFilter.GaussianBlur(2.0 * S))
    sclera = Image.new("L", face.size, 0)
    ImageDraw.Draw(sclera).polygon(sp(shape), fill=255)
    band.putalpha(ImageChops.multiply(band.getchannel("A"), sclera))
    layer.alpha_composite(band)
    mask = Image.new("L", face.size, 0)
    ImageDraw.Draw(mask).polygon(sp(lid + eye.lower[::-1]), fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    stroke(layer, lid, taper(5.0, 0.45), seed)
    stroke(layer, eye.lower[4:-4], lambda t: 1.1 * math.sin(math.pi * t) ** 0.4, seed + 3, alpha=110)
    # três cílios longos saindo do canto externo, abrindo em leque para fora e para cima, curvos
    ox, oy = lid[-1]
    for i, (ang, length) in enumerate(((-8, 17), (-32, 19), (-56, 15))):
        a = math.radians(ang)
        dx, dy = -eye.side * math.cos(a), math.sin(a)
        p0 = (ox + dx * 1.5, oy + dy * 1.5)
        p2 = (ox + dx * length, oy + dy * length - 3)
        p1 = ((p0[0] + p2[0]) / 2 - eye.side * 2, (p0[1] + p2[1]) / 2 + 3)
        stroke(layer, bezier(p0, p1, p2, 24), lambda t: 3.2 * (1 - t) ** 0.8 + 0.4, seed + 10 + i, jitter=0.2)
    face.alpha_composite(layer)


def fissure(face, eye: Almond, seed):
    """Fissura fina sob o olho esquerdo dela: rachadura de porcelana em três trechos, saindo da borda da olheira para
    baixo, com um galho curto."""
    n = Noise(seed)
    x0, y0 = eye.cx - eye.side * eye.half_w * 0.15, eye.cy + eye.h * 1.35
    main = [(x0, y0)]
    for i in range(1, 4):
        main.append((main[-1][0] + (2.5 if i % 2 else -2.0) + n(i / 4), main[-1][1] + 6.5))
    branch = [main[2], (main[2][0] - eye.side * 5, main[2][1] + 4)]
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    stroke(layer, main, lambda t: 1.9 * (1 - 0.6 * t), seed, jitter=0.1)
    stroke(layer, branch, lambda t: 1.2 * (1 - 0.7 * t), seed + 1, jitter=0.1)
    face.alpha_composite(layer)


def mouth(face, seed, width=15):
    """Boca reta e curta: um traço só, levemente mais grosso no meio."""
    y = 186
    pts = [(142 - width, y + 0.5), (142, y), (142 + width, y + 0.8)]
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    stroke(layer, bezier(*pts, 30), lambda t: 2.6 * math.sin(math.pi * t) ** 0.35, seed, jitter=0.15)
    face.alpha_composite(layer)


def draw_face(spec) -> Image.Image:
    face = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
    left = Almond(LEFT_SCREEN, +1, spec["rx"], spec["top"], spec["bot"], spec["queda"])
    right = Almond(RIGHT_SCREEN, -1, spec["rx"] * 0.96, spec["top"] * 0.96, spec["bot"], spec["queda"] + 1)
    strength, spread = spec["olheira"]
    under = Image.new("RGBA", face.size, (0, 0, 0, 0))
    deep_olheira(under, left, strength, spread)
    deep_olheira(under, right, strength, spread)
    face.alpha_composite(under)
    draw_almond(face, left, 11)
    draw_almond(face, right, 23)
    fissure(face, right, 41)  # o olho esquerdo DELA fica à direita na tela
    lips = Image.new("RGBA", face.size, (0, 0, 0, 0))
    mouth(lips, 61)
    return face, lips  # camadas separadas: a janela dos olhos também cobre a altura da boca


def cell(face, window, size) -> Image.Image:
    x0, y0, x1, y1 = window
    crop = face.crop((x0 * S, y0 * S, x1 * S, y1 * S))
    inner = (size[0] - 2 * MARGIN, size[1] - 2 * MARGIN)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.alpha_composite(crop.resize(inner, Image.LANCZOS), (MARGIN, MARGIN))
    return out


def preview(faces) -> Image.Image:
    font = ImageFont.truetype(FONT, 18)
    tile = 300
    sheet = Image.new("RGB", (tile * len(faces), 2 * tile + 60), (237, 230, 214))
    d = ImageDraw.Draw(sheet)
    for i, (name, face) in enumerate(faces.items()):
        head = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
        ImageDraw.Draw(head).ellipse([20 * S, -20 * S, 236 * S, 250 * S], fill=(*SKIN, 255))
        head.alpha_composite(face)
        big = head.resize((256, 256), Image.LANCZOS)
        small = head.resize((64, 64), Image.LANCZOS)
        for row, twilight in enumerate((False, True)):
            bg = Image.new("RGB", (tile, tile), (78, 74, 88))
            bg.paste(big, (22, 30), big)
            bg.paste(small, (tile - 70, tile - 70), small)
            if twilight:
                bg = ImageChops.multiply(bg, Image.new("RGB", bg.size, TWILIGHT))
            sheet.paste(bg, (i * tile, 30 + row * (tile + 30)))
        d.text((i * tile + 6, 6), VARIANTS[name]["nome"], fill=INK, font=font)
    d.text((6, tile + 36), "crepúsculo (× #6A5B7C); canto: 64 px", fill=INK, font=font)
    return sheet


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    faces = {}
    for name, spec in VARIANTS.items():
        eyes, lips = draw_face(spec)
        cell(eyes, EYE_WINDOW, EYE_CELL).save(OUT / f"{name}_olhos.png")
        cell(lips, MOUTH_WINDOW, MOUTH_CELL).save(OUT / f"{name}_boca.png")
        both = eyes.copy()
        both.alpha_composite(lips)
        faces[name] = both
    preview(faces).save(OUT / "estudo_rosto_2d.png")
    (OUT / "variacoes.json").write_text(json.dumps({k: {kk: vv for kk, vv in v.items()} for k, v in VARIANTS.items()},
                                                   indent=2, ensure_ascii=False) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()

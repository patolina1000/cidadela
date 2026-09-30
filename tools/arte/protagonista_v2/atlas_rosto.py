"""Protagonista v2, passo 6: atlas do rosto (olhos.png, boca.png, rosto.json), na direção b3 aprovada pelo Arthur
em 29/09/2026 (olhos amendoados abertos, sem pupila, pálpebra pesada no terço de cima; boca reta e curta).

Contrato (seção ROSTO): 3 cílios longos no canto externo, olheira funda, fissura fina sob o olho esquerdo dela (à
direita na tela; agora subida para junto do canto externo — na b3 ela ficava na altura da boca e as duas pareciam um
bigode torto), boca reta e curta; expressões neutra_cansada (padrão), esforco, dor, piscar e olhar_cristal. As emoções
vêm das pálpebras e da olheira, como no aldeão; sem sobrancelha.

Mesmo sistema do aldeão: desenho em 6x num rosto de 256 px; a janela dos olhos (24, 78, 232, 208) vira a célula
512×320 e a da boca (110, 170, 174, 202) a célula 256×128, margem transparente de 16 px por célula (celulaPx inclui a
margem). Olhos 3×2, boca 2×2 (última vazia). Índice 0 = padrão (neutra_cansada).
Retalhos (para o passo do rig, como na prova b3): olhos até ±45° e janela 10% da cabeça mais alta; boca 12% mais alta;
2 mm da pele; 100% Head.

Saída: assets/modelos/protagonista_v2/rosto/{olhos.png, boca.png, rosto.json} e a prévia
assets/previews/protagonista_v2/rosto_atlas.png (as 5 expressões a 256 e 64 px, e o crepúsculo).

Uso (em tools/arte): uv run protagonista_v2/atlas_rosto.py
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent


def _load(name, path):
    """Carrega um módulo pelo caminho: o aldeão tem arquivos com os mesmos nomes (estudo_rosto, desenhar_rosto)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_ald = _load("aldeao_desenhar_rosto", HERE.parent / "aldeao_v2/desenhar_rosto.py")
_est = _load("protagonista_estudo_rosto", HERE / "estudo_rosto.py")
BONE, EYE_CELL, EYE_WINDOW, FACE, INK, MARGIN = _ald.BONE, _ald.EYE_CELL, _ald.EYE_WINDOW, _ald.FACE, _ald.INK, _ald.MARGIN
MOUTH_CELL, MOUTH_WINDOW, S, Noise, bezier, sp, stroke, taper = (_ald.MOUTH_CELL, _ald.MOUTH_WINDOW, _ald.S, _ald.Noise,
                                                                 _ald.bezier, _ald.sp, _ald.stroke, _ald.taper)
CAVITY, LEFT_SCREEN, OPEN, RIGHT_SCREEN = _est.CAVITY, _est.LEFT_SCREEN, _est.OPEN, _est.RIGHT_SCREEN
SKIN, TWILIGHT, Almond, deep_olheira = _est.SKIN, _est.TWILIGHT, _est.Almond, _est.deep_olheira

ROOT = HERE.parents[2]
OUT = ROOT / "assets/modelos/protagonista_v2/rosto"
PREVIEW = ROOT / "assets/previews/protagonista_v2/rosto_atlas.png"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
EYE_GRID, MOUTH_GRID = (3, 2), (2, 2)

# Quadros dos olhos: pálpebra de cima (cobre no canto de dentro, no de fora), pálpebra de baixo sobe, olheira.
EYES = {
    "aberto_cansado": {"cobre": OPEN["cobre"], "baixo_sobe": 0.0, "olheira": 150},
    "meio_fechado": {"cobre": (0.62, 0.70), "baixo_sobe": 0.0, "olheira": 150},
    "fechado": {"fechado": True, "olheira": 150},
    "apertado": {"cobre": (0.40, 0.46), "baixo_sobe": 0.38, "olheira": 175},
    "dor": {"cobre": (0.02, 0.66), "baixo_sobe": 0.30, "olheira": 195},
    "olhar_baixo": {"cobre": (0.50, 0.56), "baixo_sobe": 0.0, "olheira": 150, "sombra": (0.54, 0.62, 140)},
}
MOUTHS = ["reta", "tensa", "dor"]
EXPRESSIONS = {
    "neutra_cansada": ("aberto_cansado", "reta"),
    "esforco": ("apertado", "tensa"),
    "dor": ("dor", "dor"),
    "piscar": ("fechado", "reta"),
    "olhar_cristal": ("olhar_baixo", "reta"),
}


def raised_floor(eye: Almond, amount):
    """Pálpebra de baixo subindo `amount` da altura do olho no meio (achatada, como no aperto)."""
    n = len(eye.lower) - 1
    return [(lx, ly - (ly - uy) * amount * math.sin(math.pi * i / n) ** 0.35)
            for i, ((ux, uy), (lx, ly)) in enumerate(zip(eye.upper, eye.lower))]


def lashes(layer, eye: Almond, corner, seed):
    """Três cílios longos saindo do canto externo, em leque para fora e para cima."""
    ox, oy = corner
    for i, (ang, length) in enumerate(((-8, 17), (-32, 19), (-56, 15))):
        a = math.radians(ang)
        dx, dy = -eye.side * math.cos(a), math.sin(a)
        p0 = (ox + dx * 1.5, oy + dy * 1.5)
        p2 = (ox + dx * length, oy + dy * length - 3)
        p1 = ((p0[0] + p2[0]) / 2 - eye.side * 2, (p0[1] + p2[1]) / 2 + 3)
        stroke(layer, bezier(p0, p1, p2, 24), lambda t: 3.2 * (1 - t) ** 0.8 + 0.4, seed + 10 + i, jitter=0.2)


def draw_eye(face, eye: Almond, spec, seed):
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    if spec.get("fechado"):
        # piscar: só a linha da pálpebra fechada, curvada para baixo, com os cílios
        line = eye.lid(0.86, 0.90)
        n = len(line) - 1
        line = [(x, y + 2.5 * math.sin(math.pi * i / n)) for i, (x, y) in enumerate(line)]
        stroke(layer, line, taper(5.4, 0.3), seed)
        lashes(layer, eye, line[-1], seed)
        face.alpha_composite(layer)
        return
    d = ImageDraw.Draw(layer)
    shape = eye.upper + eye.lower[::-1]
    d.polygon(sp(shape), fill=(*BONE, 255))
    shade = spec.get("sombra", OPEN["sombra"])
    band = Image.new("RGBA", face.size, (0, 0, 0, 0))
    ImageDraw.Draw(band).polygon(sp(eye.upper + eye.lid(shade[0], shade[1])[::-1]), fill=(*CAVITY, shade[2]))
    band = band.filter(ImageFilter.GaussianBlur(2.0 * S))
    sclera = Image.new("L", face.size, 0)
    ImageDraw.Draw(sclera).polygon(sp(shape), fill=255)
    band.putalpha(ImageChops.multiply(band.getchannel("A"), sclera))
    layer.alpha_composite(band)
    lid = eye.lid(*spec["cobre"])
    floor = raised_floor(eye, spec["baixo_sobe"]) if spec["baixo_sobe"] else eye.lower
    mask = Image.new("L", face.size, 0)
    ImageDraw.Draw(mask).polygon(sp(lid + floor[::-1]), fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    stroke(layer, lid, taper(5.0, 0.45), seed)
    rim_w, rim_a = OPEN["contorno"]
    if spec["baixo_sobe"]:
        rim_w, rim_a = rim_w * 1.2, 235
    stroke(layer, floor[4:-4], lambda t: rim_w * math.sin(math.pi * t) ** 0.4, seed + 3, alpha=rim_a)
    lashes(layer, eye, lid[-1], seed)
    face.alpha_composite(layer)


def fissure(face, eye: Almond, seed):
    """Fissura fina junto do canto externo do olho esquerdo dela: sai logo abaixo do canto, desce e abre para fora,
    com um galho curto. Longe da boca (na b3 as duas pareciam um bigode torto)."""
    n = Noise(seed)
    ox = eye.outer[0] + eye.side * 5  # um pouco para dentro do canto externo
    y0 = eye.cy + eye.h * 0.62
    main = [(ox, y0)]
    for i in range(1, 4):
        main.append((main[-1][0] - eye.side * (1.8 + 0.6 * n(i / 4)), main[-1][1] + 4.6))
    branch = [main[1], (main[1][0] - eye.side * 4.5, main[1][1] + 2.2)]
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    stroke(layer, main, lambda t: 1.8 * (1 - 0.6 * t), seed, jitter=0.1)
    stroke(layer, branch, lambda t: 1.1 * (1 - 0.7 * t), seed + 1, jitter=0.1)
    face.alpha_composite(layer)


def draw_eyes(kind) -> Image.Image:
    spec = EYES[kind]
    face = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
    left = Almond(LEFT_SCREEN, +1, OPEN["rx"], OPEN["top"], OPEN["bot"], OPEN["queda"])
    right = Almond(RIGHT_SCREEN, -1, OPEN["rx"] * 0.96, OPEN["top"] * 0.96, OPEN["bot"], OPEN["queda"] + 1)
    under = Image.new("RGBA", face.size, (0, 0, 0, 0))
    deep_olheira(under, left, spec["olheira"], OPEN["olheira"][1])
    deep_olheira(under, right, spec["olheira"], OPEN["olheira"][1])
    face.alpha_composite(under)
    draw_eye(face, left, spec, 11)
    draw_eye(face, right, spec, 23)
    fissure(face, right, 41)  # o olho esquerdo DELA fica à direita na tela
    return face


def draw_mouth(kind) -> Image.Image:
    face = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
    layer = Image.new("RGBA", face.size, (0, 0, 0, 0))
    cx, y = 142, 186
    if kind == "reta":  # a da b3: um traço só, mais grosso no meio
        stroke(layer, bezier((cx - 15, y + 0.5), (cx, y), (cx + 15, y + 0.8), 30),
               lambda t: 2.6 * math.sin(math.pi * t) ** 0.35, 61, jitter=0.15)
    elif kind == "tensa":  # esforço: mais larga, apertada, cantos puxados para baixo, leve ondulação
        pts = [(cx - 19 + 38 * i / 30, y + 1.6 * math.sin(math.pi * i / 30 * 3) * 0.5 + 2.2 * abs(i / 15 - 1) ** 3)
               for i in range(31)]
        stroke(layer, pts, lambda t: 3.2 * math.sin(math.pi * t) ** 0.25, 62, jitter=0.2)
    elif kind == "dor":  # entreaberta e caída: lente escura estreita, cantos para baixo
        d = ImageDraw.Draw(layer)
        top = bezier((cx - 12, y + 2.5), (cx, y - 2.5), (cx + 12, y + 3.0), 24)
        bot = bezier((cx - 12, y + 2.5), (cx, y + 4.5), (cx + 12, y + 3.0), 24)
        d.polygon(sp(top + bot[::-1]), fill=(42, 30, 39, 255))
        stroke(layer, top, lambda t: 2.4 * math.sin(math.pi * t) ** 0.3 + 0.6, 63, jitter=0.15)
        stroke(layer, bot[3:-3], lambda t: 1.0 * math.sin(math.pi * t) ** 0.4, 64, jitter=0.1, alpha=150)
    else:
        raise ValueError(kind)
    face.alpha_composite(layer)
    return face


def cell(face, window, size) -> Image.Image:
    x0, y0, x1, y1 = window
    crop = face.crop((x0 * S, y0 * S, x1 * S, y1 * S))
    inner = (size[0] - 2 * MARGIN, size[1] - 2 * MARGIN)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.alpha_composite(crop.resize(inner, Image.LANCZOS), (MARGIN, MARGIN))
    return out


def atlas(cells, grid, size) -> Image.Image:
    img = Image.new("RGBA", (grid[0] * size[0], grid[1] * size[1]), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        img.alpha_composite(c, ((i % grid[0]) * size[0], (i // grid[0]) * size[1]))
    return img


def check_margins(img, grid, size):
    """Nenhum pixel desenhado na margem de 16 px de cada célula (contrato do atlas)."""
    a = img.getchannel("A")
    for r in range(grid[1]):
        for c in range(grid[0]):
            x0, y0 = c * size[0], r * size[1]
            inner = (x0 + MARGIN, y0 + MARGIN, x0 + size[0] - MARGIN, y0 + size[1] - MARGIN)
            full = a.crop((x0, y0, x0 + size[0], y0 + size[1])).getbbox()
            if full and not (full[0] >= MARGIN and full[1] >= MARGIN and full[2] <= size[0] - MARGIN and full[3] <= size[1] - MARGIN):
                raise RuntimeError(f"célula ({c},{r}) desenha na margem: {full} fora de {inner}")


def preview(eye_faces, mouth_faces) -> Image.Image:
    font = ImageFont.truetype(FONT, 18)
    tile = 280
    names = list(EXPRESSIONS)
    sheet = Image.new("RGB", (tile * len(names), 2 * tile + 70), (237, 230, 214))
    d = ImageDraw.Draw(sheet)
    for i, name in enumerate(names):
        e, m = EXPRESSIONS[name]
        head = Image.new("RGBA", (FACE * S, FACE * S), (0, 0, 0, 0))
        ImageDraw.Draw(head).ellipse([20 * S, -20 * S, 236 * S, 250 * S], fill=(*SKIN, 255))
        head.alpha_composite(eye_faces[e])
        # a boca sobe no retalho (b3); na prévia 2D, só uma aproximação (a prova em 3D é a medida)
        mouth = Image.new("RGBA", head.size, (0, 0, 0, 0))
        mouth.alpha_composite(mouth_faces[m], (0, -12 * S))
        head.alpha_composite(mouth)
        big = head.resize((240, 240), Image.LANCZOS)
        small = head.resize((64, 64), Image.LANCZOS)
        for row, twilight in enumerate((False, True)):
            bg = Image.new("RGB", (tile, tile), (78, 74, 88))
            bg.paste(big, (20, 30), big)
            bg.paste(small, (tile - 68, tile - 68), small)
            if twilight:
                bg = ImageChops.multiply(bg, Image.new("RGB", bg.size, TWILIGHT))
            sheet.paste(bg, (i * tile, 34 + row * (tile + 36)))
        d.text((i * tile + 8, 8), name, fill=INK, font=font)
    d.text((8, tile + 44), "crepúsculo (× #6A5B7C); canto: 64 px", fill=INK, font=font)
    return sheet


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    eye_faces = {k: draw_eyes(k) for k in EYES}
    mouth_faces = {k: draw_mouth(k) for k in MOUTHS}
    eyes = atlas([cell(eye_faces[k], EYE_WINDOW, EYE_CELL) for k in EYES], EYE_GRID, EYE_CELL)
    mouths = atlas([cell(mouth_faces[k], MOUTH_WINDOW, MOUTH_CELL) for k in MOUTHS], MOUTH_GRID, MOUTH_CELL)
    check_margins(eyes, EYE_GRID, EYE_CELL)
    check_margins(mouths, MOUTH_GRID, MOUTH_CELL)
    eyes.save(OUT / "olhos.png")
    mouths.save(OUT / "boca.png")
    rosto = {
        "olhos": {"colunas": EYE_GRID[0], "linhas": EYE_GRID[1], "celulaPx": list(EYE_CELL), "margemPx": MARGIN,
                  "quadros": {k: i for i, k in enumerate(EYES)}},
        "boca": {"colunas": MOUTH_GRID[0], "linhas": MOUTH_GRID[1], "celulaPx": list(MOUTH_CELL), "margemPx": MARGIN,
                 "quadros": {k: i for i, k in enumerate(MOUTHS)}},
        "expressoes": {k: {"olhos": e, "boca": m} for k, (e, m) in EXPRESSIONS.items()},
        "ossoCabeca": "Head",
        "ossoPeito": "Spine",
    }
    (OUT / "rosto.json").write_text(json.dumps(rosto, indent=2, ensure_ascii=False) + "\n")
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    preview(eye_faces, mouth_faces).save(PREVIEW)
    print(OUT, eyes.size, mouths.size)


if __name__ == "__main__":
    main()

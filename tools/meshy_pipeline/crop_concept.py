"""Recorta as vistas de frente e de costas do conceito da protagonista.

A personagem é fria (azul) e o fundo de pergaminho é quente, então a máscara vem da
diferença azul - vermelho. Em cada vista fica só a maior região conectada, o que
descarta as cabeças isoladas, os textos, as setas e os ícones.

Correções aprovadas em 25/09/2026, porque o conceito tem dois defeitos:
- a mão esquerda não existe em nenhuma vista: espelhamos a mão direita (com a faixa
  do pulso) e encaixamos na ponta do braço esquerdo;
- o cristal aparece também nas costas: cobrimos com o cabelo ao lado dele.

Uso: uv run crop_concept.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets/conceitos/protagonista.jpg"
OUT_DIR = ROOT / "assets/conceitos"

PARCHMENT = (243, 228, 199)
COOL_THRESHOLD = 6  # azul - vermelho acima disso conta como personagem
GLOW_RED = 210  # o brilho do cristal no papel é frio mas quase branco; a pele nunca passa disso
CANVAS = 1024  # saída quadrada, mesma escala nas duas vistas
MARGIN = 0.06
HAND_OVERLAP = 6  # px que a mão espelhada entra no braço, para não sobrar fresta

# Coordenadas na folha de 1280x709. box: região da vista. hand: mão direita + faixa do pulso.
# attach: lado da vista onde fica a ponta do braço esquerdo. arm_rows: faixa de linhas do braço.
VIEWS = {
    "protagonista_frente": {
        "box": (150, 90, 620, 660),
        "hand": (170, 270, 266, 314),
        "attach": "right",
        "arm_rows": (262, 295),
        "erase": [(503, 248, 534, 294)],  # ícone "Nascido do Cristal Único" colado no braço
    },
    "protagonista_costas": {
        "box": (660, 90, 1180, 660),
        "hand": (1055, 268, 1164, 311),
        "attach": "left",
        "arm_rows": (280, 305),
        "erase": [],
    },
}
BACK_CRYSTAL = (898, 266, 934, 334)  # cristal das costas, com o brilho em volta
HAIR_OFFSET = (-34, 0)  # de onde vem o cabelo que cobre o cristal: do lado, mesma altura e sombra


def figure_mask(rgb: np.ndarray) -> np.ndarray:
    r, b = rgb[..., 0].astype(int), rgb[..., 2].astype(int)
    mask = ((b - r) > COOL_THRESHOLD) & (r < GLOW_RED)
    mask = ndimage.binary_opening(mask, iterations=1)
    labels, count = ndimage.label(mask)
    if count == 0:
        raise RuntimeError("nenhuma região fria encontrada")
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    mask = labels == (int(np.argmax(sizes)) + 1)
    # Contornos escuros e pontas finas ficam de fora da máscara de cor: fecha e engorda 1 px.
    mask = ndimage.binary_closing(mask, iterations=3)
    mask = ndimage.binary_fill_holes(mask)
    return ndimage.binary_dilation(mask, iterations=1)


def cover_back_crystal(sheet: Image.Image) -> None:
    x0, y0, x1, y1 = BACK_CRYSTAL
    dx, dy = HAIR_OFFSET
    hair = sheet.crop((x0 + dx, y0 + dy, x1 + dx, y1 + dy))
    feather = Image.new("L", hair.size, 0)
    ImageDraw.Draw(feather).ellipse((3, 3, hair.width - 4, hair.height - 4), fill=255)
    sheet.paste(hair, (x0, y0), feather.filter(ImageFilter.GaussianBlur(3)))


def attach_mirrored_hand(rgb: np.ndarray, mask: np.ndarray, view: dict) -> None:
    """Espelha a mão direita e cola na ponta do braço esquerdo (coordenadas da vista)."""
    bx, by = view["box"][:2]
    hx0, hy0, hx1, hy1 = (v - o for v, o in zip(view["hand"], (bx, by, bx, by)))
    patch = rgb[hy0:hy1, hx0:hx1][:, ::-1].copy()
    patch_mask = mask[hy0:hy1, hx0:hx1][:, ::-1].copy()

    r0, r1 = (v - by for v in view["arm_rows"])
    cols = np.nonzero(mask[r0:r1].any(axis=0))[0]
    tip_x = cols.max() if view["attach"] == "right" else cols.min()
    tip_rows = np.nonzero(mask[r0:r1, tip_x])[0] + r0
    tip_y = int(tip_rows.mean())

    h, w = patch_mask.shape
    x = tip_x - HAND_OVERLAP if view["attach"] == "right" else tip_x + HAND_OVERLAP - w
    y = tip_y - int(np.nonzero(patch_mask[:, 0 if view["attach"] == "right" else -1])[0].mean())
    if x < 0 or y < 0 or x + w > mask.shape[1] or y + h > mask.shape[0]:
        raise RuntimeError("a mão espelhada sai da região da vista; aumente o box")
    region = (slice(y, y + h), slice(x, x + w))
    rgb[region][patch_mask] = patch[patch_mask]
    mask[region] |= patch_mask


def main() -> None:
    sheet = Image.open(SOURCE).convert("RGB")
    cover_back_crystal(sheet)
    draw = ImageDraw.Draw(sheet)
    for view in VIEWS.values():
        for box in view["erase"]:
            draw.rectangle(box, fill=PARCHMENT)

    crops = {}
    for name, view in VIEWS.items():
        rgb = np.asarray(sheet.crop(view["box"])).copy()
        mask = figure_mask(rgb)
        attach_mirrored_hand(rgb, mask, view)
        ys, xs = np.nonzero(mask)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        rgba = np.dstack([rgb, (mask * 255).astype(np.uint8)])[y0:y1, x0:x1]
        crops[name] = Image.fromarray(rgba, "RGBA")

    # Mesma escala nas duas vistas: o maior lado entre as duas ocupa a tela menos a margem.
    biggest = max(max(c.size) for c in crops.values())
    scale = CANVAS * (1 - 2 * MARGIN) / biggest
    for name, crop in crops.items():
        size = (round(crop.width * scale), round(crop.height * scale))
        crop = crop.resize(size, Image.LANCZOS)
        canvas = Image.new("RGB", (CANVAS, CANVAS), "white")
        canvas.paste(crop, ((CANVAS - size[0]) // 2, (CANVAS - size[1]) // 2), crop)
        path = OUT_DIR / f"{name}.png"
        canvas.save(path)
        print(f"{path.relative_to(ROOT)}  figura {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()

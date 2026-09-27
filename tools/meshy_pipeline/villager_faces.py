"""Atlas de expressões do aldeão: recorta o rosto de cada uma das 9 cabeças do conceito.

Só os TRAÇOS ficam (sobrancelhas, olhos com o branco e as pupilas, nariz, boca, lágrimas); todo o resto é
100% transparente, sem nenhuma pele do desenho (a pele do conceito tem outro tom que a do modelo e fazia
uma borda). Traço = escuro (contornos, pupilas, boca) ou claro e pouco saturado (branco do olho,
lágrimas); cavidades pequenas cercadas de traço (interior do olho, boca aberta) também. Contra halo, os
pixels transparentes levam a cor do traço mais próximo (a filtragem da textura mistura vizinhos).
Ordem das células (da esquerda para a direita, de cima para baixo): 1 distraído, 2 esforço,
3 feliz, 4 sonolento, 5 dormindo, 6 espantado, 7 preocupado, 8 chorando, 9 bravo.

Uso: uv run villager_faces.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
# O arquivo com as 9 cabeças se chama "aldeao_cabelos.png" (os nomes dos conceitos vieram trocados).
SOURCE = ROOT / "assets/conceitos/aldeao/aldeao_cabelos.png"
ATLAS = ROOT / "assets/texturas/aldeao/expressoes.png"
PREVIEW = ROOT / "assets/previews/aldeao_expressoes.png"
STROKES_PREVIEW = ROOT / "assets/previews/expressoes_tracos.png"

CELL = 256  # px de cada célula no atlas
CROP = 220  # px do quadrado recortado no conceito (as cabeças têm o mesmo tamanho)
# Oval do rosto em fração da célula (raio x, raio y) e onde o degradê começa (fração do raio).
FACE_RADIUS = (0.47, 0.36)  # oval justa em volta dos traços (fração da célula)
FACE_CENTER_Y = 0.50
FEATHER_START = 0.70
# Traço escuro: brilho (0..1) abaixo de DARK[0] é traço inteiro, acima de DARK[1] é nada.
DARK = (0.26, 0.37)
# Traço claro (branco do olho, lágrimas): brilho acima de LIGHT e saturação abaixo de LIGHT_SAT.
LIGHT = (0.73, 0.80)
LIGHT_SAT = (0.11, 0.16)
REGION_FEATHER = 0.8  # fração do raio da elipse onde a borda começa a cair
MIN_SPECK = 6  # px: traço escuro menor que isso é sujeira
NEAR_LINE = 3  # px: claro a até isso de um traço escuro conta (lágrimas contornadas)
ENCLOSE_GROW = 1.3  # elipses maiores para achar o miolo fechado dos olhos

# Elipses dos traços de cada célula, na ordem de FACES: (centro x, centro y, raio x, raio y) em fração
# da célula, marcadas vendo as 9 cabeças com uma grade (27/09/2026). Olhos, sobrancelhas visíveis,
# nariz, boca e lágrimas; o resto (cabelo, contorno do rosto, orelhas, olheiras, pescoço) fica de fora.
FEATURES = [
    [(0.34, 0.47, 0.13, 0.13), (0.70, 0.40, 0.13, 0.13), (0.49, 0.54, 0.04, 0.03), (0.49, 0.65, 0.06, 0.05)],
    [(0.34, 0.43, 0.12, 0.12), (0.72, 0.39, 0.12, 0.12), (0.28, 0.25, 0.12, 0.05), (0.72, 0.20, 0.12, 0.05),
     (0.53, 0.52, 0.04, 0.03), (0.52, 0.63, 0.08, 0.04)],
    [(0.35, 0.47, 0.13, 0.13), (0.70, 0.40, 0.12, 0.12), (0.51, 0.54, 0.03, 0.03), (0.50, 0.64, 0.08, 0.05)],
    [(0.32, 0.48, 0.13, 0.09), (0.70, 0.42, 0.12, 0.08), (0.30, 0.30, 0.10, 0.04), (0.73, 0.28, 0.10, 0.04),
     (0.51, 0.53, 0.03, 0.03), (0.52, 0.64, 0.06, 0.03)],
    [(0.30, 0.47, 0.12, 0.06), (0.70, 0.36, 0.12, 0.07), (0.49, 0.44, 0.03, 0.03), (0.49, 0.61, 0.06, 0.08)],
    [(0.30, 0.44, 0.14, 0.14), (0.74, 0.38, 0.14, 0.14), (0.78, 0.18, 0.12, 0.05),
     (0.49, 0.53, 0.03, 0.03), (0.49, 0.64, 0.04, 0.06)],
    [(0.32, 0.52, 0.14, 0.13), (0.66, 0.36, 0.13, 0.14), (0.25, 0.31, 0.12, 0.07),
     (0.47, 0.56, 0.03, 0.03), (0.56, 0.64, 0.06, 0.05)],
    [(0.33, 0.43, 0.13, 0.13), (0.27, 0.57, 0.10, 0.07), (0.74, 0.39, 0.12, 0.12), (0.72, 0.55, 0.08, 0.06),
     (0.28, 0.25, 0.12, 0.05), (0.72, 0.22, 0.12, 0.05), (0.49, 0.52, 0.03, 0.03), (0.50, 0.63, 0.05, 0.03)],
    [(0.30, 0.45, 0.15, 0.14), (0.72, 0.42, 0.14, 0.15), (0.48, 0.56, 0.03, 0.03), (0.49, 0.64, 0.06, 0.04)],
]
SKIN = (160, 184, 206)  # pele azul-pálida do conceito, só para a prévia

# Centro do rosto (meio caminho entre a linha dos olhos e a boca) de cada cabeça no conceito,
# na ordem das células do atlas. Posição na folha: (linha, coluna).
FACES = [
    ("distraído", (712, 545)),   # 2,2: olhar parado para a frente, boca em "o" pequeno
    ("esforço", (715, 905)),     # 3,2: sobrancelhas tensas, dentes cerrados, ombros erguidos
    ("feliz", (712, 205)),       # 1,2: sorriso aberto
    ("sonolento", (272, 550)),   # 2,1: pálpebras caídas
    ("dormindo", (1165, 910)),   # 3,3: olhos fechados, boca aberta
    ("espantado", (270, 890)),   # 3,1: olhos arregalados, boca em "O" grande
    ("preocupado", (1175, 545)), # 2,3: sobrancelhas erguidas, olhar desviado para cima
    ("chorando", (272, 205)),    # 1,1: lágrimas
    ("bravo", (1160, 215)),      # 1,3: sobrancelhas franzidas
]


def face_mask() -> np.ndarray:
    """Oval opaco no meio e degradê até transparente na borda."""
    coords = (np.arange(CELL) + 0.5) / CELL - 0.5
    x, y = np.meshgrid(coords, coords)
    y = y + 0.5 - FACE_CENTER_Y
    r = np.sqrt((x / FACE_RADIUS[0]) ** 2 + (y / FACE_RADIUS[1]) ** 2)
    t = np.clip((r - FEATHER_START) / (1 - FEATHER_START), 0, 1)
    return 1 - t * t * (3 - 2 * t)


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0, 1)
    return t * t * (3 - 2 * t)


def oval_radius(radii: tuple = None) -> np.ndarray:
    """Raio normalizado de uma oval em cada pixel (1 = borda); padrão: a oval dos traços."""
    rx, ry = radii or FACE_RADIUS
    coords = (np.arange(CELL) + 0.5) / CELL - 0.5
    x, y = np.meshgrid(coords, coords)
    return np.sqrt((x / rx) ** 2 + ((y + 0.5 - FACE_CENTER_Y) / ry) ** 2)


def region_mask(ellipses: list, grow: float = 1.0) -> np.ndarray:
    """1 dentro das elipses dos traços da célula (raios × grow), caindo a 0 numa borda curta."""
    coords = (np.arange(CELL) + 0.5) / CELL
    x, y = np.meshgrid(coords, coords)
    mask = np.zeros((CELL, CELL), dtype=np.float32)
    for cx, cy, rx, ry in ellipses:
        r = np.sqrt(((x - cx) / (rx * grow)) ** 2 + ((y - cy) / (ry * grow)) ** 2)
        mask = np.maximum(mask, smoothstep(1.0, REGION_FEATHER, r))
    return mask


def strokes_alpha(rgb: np.ndarray, ellipses: list) -> np.ndarray:
    """Alfa dos traços: dentro das elipses marcadas para a célula (olhos, sobrancelhas, nariz, boca,
    lágrimas), traço escuro ou claro e pouco saturado (branco do olho, lágrimas); as cavidades cercadas
    de traço dentro delas (miolo do olho, boca aberta) também. Fora das elipses, nada."""
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    sat = (rgb.max(axis=-1) - rgb.min(axis=-1)) / np.maximum(rgb.max(axis=-1), 1e-6)
    region = region_mask(ellipses)
    dark = smoothstep(DARK[1], DARK[0], lum) * region
    light = smoothstep(LIGHT[0], LIGHT[1], lum) * smoothstep(LIGHT_SAT[1], LIGHT_SAT[0], sat) * region
    dark_solid = dark > 0.5
    labels, count = ndimage.label(dark_solid)
    sizes = ndimage.sum(np.ones_like(labels), labels, range(1, count + 1))
    dark_solid = np.isin(labels, 1 + np.nonzero(sizes >= MIN_SPECK)[0])  # só tira sujeira de poucos px
    # Claro (branco do olho, lágrimas): só dentro do contorno escuro fechado ou colado a ele; brilhos da
    # pele em volta dos olhos ficam de fora.
    # O contorno do olho pode passar da elipse: o "fechado" usa as elipses um pouco maiores.
    wide = (smoothstep(DARK[1], DARK[0], lum) > 0.5) & (region_mask(ellipses, ENCLOSE_GROW) > 0.5)
    enclosed = ndimage.binary_fill_holes(wide) & (region > 0.5)
    near = ndimage.distance_transform_edt(~dark_solid) <= NEAR_LINE
    light = light * (enclosed | near)
    alpha = np.maximum(dark * ndimage.binary_dilation(dark_solid, iterations=1), light)
    alpha = np.maximum(alpha, (enclosed & ~dark_solid).astype(np.float32) * region)
    return np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)),
                      dtype=np.float32) / 255


def bleed(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Pixels transparentes recebem a cor do traço opaco mais próximo (sem halo de pele na filtragem)."""
    _, (iy, ix) = ndimage.distance_transform_edt(alpha < 0.5, return_indices=True)
    return rgb[iy, ix]


def main() -> None:
    sheet = Image.open(SOURCE).convert("RGB")
    oval = face_mask()
    atlas = Image.new("RGBA", (CELL * 3, CELL * 3), (0, 0, 0, 0))
    for index, (_, (cx, cy)) in enumerate(FACES):
        half = CROP // 2
        face = sheet.crop((cx - half, cy - half, cx + half, cy + half)).resize((CELL, CELL), Image.LANCZOS)
        rgb = np.asarray(face, dtype=np.float32) / 255
        alpha_f = strokes_alpha(rgb, FEATURES[index])
        rgb = bleed(rgb, alpha_f)
        face = Image.fromarray((rgb * 255).round().astype(np.uint8), "RGB")
        cell = np.dstack([np.asarray(face), (alpha_f * 255).round().astype(np.uint8)])
        atlas.paste(Image.fromarray(cell, "RGBA"), ((index % 3) * CELL, (index // 3) * CELL))
    ATLAS.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(ATLAS)
    print(ATLAS.relative_to(ROOT))

    # Prévia: o atlas sobre a cor da pele, numerado, para conferir a mistura das bordas.
    preview = Image.new("RGB", atlas.size, SKIN)
    preview.paste(atlas, (0, 0), atlas)
    draw = ImageDraw.Draw(preview)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
    for index, (name, _) in enumerate(FACES):
        x, y = (index % 3) * CELL, (index // 3) * CELL
        draw.text((x + 8, y + 6), f"{index + 1} {name}", fill=(20, 20, 30), font=font)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    preview.save(PREVIEW)
    print(PREVIEW.relative_to(ROOT))

    # Os traços sobre três fundos (pele clara, pele escura, cinza): nenhuma borda pode aparecer.
    font_big = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 26)
    backgrounds = [("pele clara", (150, 177, 195)), ("pele escura", (70, 88, 108)), ("cinza", (128, 128, 128))]
    sheet = Image.new("RGB", (atlas.width * 3 + 40, atlas.height + 50), (30, 28, 34))
    draw = ImageDraw.Draw(sheet)
    for k, (label, color) in enumerate(backgrounds):
        tile = Image.new("RGB", atlas.size, color)
        tile.paste(atlas, (0, 0), atlas)
        sheet.paste(tile, (k * (atlas.width + 20), 50))
        draw.text((k * (atlas.width + 20) + 8, 10), label, fill=(237, 230, 214), font=font_big)
    sheet.save(STROKES_PREVIEW)
    print(STROKES_PREVIEW.relative_to(ROOT))


if __name__ == "__main__":
    main()

"""Atlas de expressões do aldeão: recorta o rosto de cada uma das 9 cabeças do conceito.

Só os traços do rosto ficam opacos (sobrancelhas, olhos, nariz, boca, lágrimas): o que se afasta da cor
da pele, dentro de uma oval justa em volta deles. Onde é só pele a célula fica transparente, e a pele do
próprio modelo aparece; fios de cabelo, contorno do rosto, orelhas, pescoço e papel ficam de fora.
Ordem das células (da esquerda para a direita, de cima para baixo): 1 distraído, 2 esforço,
3 feliz, 4 sonolento, 5 dormindo, 6 espantado, 7 preocupado, 8 chorando, 9 bravo.

Uso: uv run villager_faces.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
# O arquivo com as 9 cabeças se chama "aldeao_cabelos.png" (os nomes dos conceitos vieram trocados).
SOURCE = ROOT / "assets/conceitos/aldeao/aldeao_cabelos.png"
ATLAS = ROOT / "assets/texturas/aldeao/expressoes.png"
PREVIEW = ROOT / "assets/previews/aldeao_expressoes.png"

CELL = 256  # px de cada célula no atlas
CROP = 220  # px do quadrado recortado no conceito (as cabeças têm o mesmo tamanho)
# Oval do rosto em fração da célula (raio x, raio y) e onde o degradê começa (fração do raio).
FACE_RADIUS = (0.40, 0.31)  # oval justa em volta dos traços (fração da célula)
FACE_CENTER_Y = 0.50
FEATHER_START = 0.70
# Traço = distância de cor até a pele (0..1): abaixo de DEV_LOW é pele, acima de DEV_HIGH é traço.
DEV_LOW, DEV_HIGH = 0.07, 0.20
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


def main() -> None:
    sheet = Image.open(SOURCE).convert("RGB")
    oval = face_mask()
    atlas = Image.new("RGBA", (CELL * 3, CELL * 3), (0, 0, 0, 0))
    for index, (_, (cx, cy)) in enumerate(FACES):
        half = CROP // 2
        face = sheet.crop((cx - half, cy - half, cx + half, cy + half)).resize((CELL, CELL), Image.LANCZOS)
        rgb = np.asarray(face, dtype=np.float32) / 255
        # Pele: a cor mais comum dentro da oval (mediana dos pixels claros e pouco saturados).
        inside = oval > 0.9
        lum = rgb @ np.array([0.299, 0.587, 0.114])
        candidates = rgb[inside & (lum > np.percentile(lum[inside], 40))]
        skin = np.median(candidates, axis=0)
        deviation = np.linalg.norm(rgb - skin, axis=-1) / np.sqrt(3)
        t = np.clip((deviation - DEV_LOW) / (DEV_HIGH - DEV_LOW), 0, 1)
        feature = t * t * (3 - 2 * t)
        warm = rgb[..., 0] > rgb[..., 2]  # papel do conceito (o aldeão é todo frio)
        alpha_f = feature * oval * ~warm
        alpha_f = np.asarray(Image.fromarray((alpha_f * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)),
                             dtype=np.float32) / 255
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


if __name__ == "__main__":
    main()

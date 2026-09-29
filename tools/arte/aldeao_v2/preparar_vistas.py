"""Prepara as vistas das folhas de modelagem do aldeão v2 para a Meshy.

Lê cada folha em assets/conceitos/aldeao_v2/folhas/ e, para cada figura encontrada nela:
1. recorta a figura (regiões que diferem do fundo; textos, setas e ícones pequenos são descartados);
2. centraliza num quadrado com margem, na MESMA escala para todas as vistas da mesma folha;
3. uniformiza o fundo numa cor lisa;
4. salva em assets/conceitos/aldeao_v2/vistas/<folha>_<vista>.png e uma prévia _previa_<folha>.png.

Os nomes das vistas vêm de --vistas, na ordem de leitura (linhas de cima para baixo, da esquerda para a
direita). Se a folha tiver outro número de figuras, todas saem como vista_1, vista_2... e o script avisa; aí
escolha por índice: --vistas frente:2,costas:3. Figuras que encostam na borda da folha (molduras, vinhetas)
são ignoradas.

Uso:
  uv run preparar_vistas.py                                  # todas as folhas, vistas frente,lado,costas
  uv run preparar_vistas.py --folha corpo.png --vistas frente,lado,costas
  uv run preparar_vistas.py --folha cabelo_1.png --vistas frente,costas --limiar 24
  uv run preparar_vistas.py --saida /tmp/teste               # gravar em outra pasta (teste)
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
SHEETS = ROOT / "assets/conceitos/aldeao_v2/folhas"
OUT = ROOT / "assets/conceitos/aldeao_v2/vistas"

CANVAS = 1024  # lado do quadrado de saída
MARGIN = 0.08  # fração do lado, em volta da figura
BACKGROUND = (235, 235, 235)  # fundo liso, claro e neutro (a Meshy separa bem do boneco)
MIN_AREA = 0.05  # fração da maior figura: menor que isso é texto, seta ou ícone
FRAME = 0.85  # região maior que isso da folha (nas duas direções) é moldura, não figura
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"


def background_color(rgb: np.ndarray) -> np.ndarray:
    """Cor mais comum da folha (quantizada em 32 níveis): o fundo liso ocupa a maior parte da imagem."""
    bins = (rgb // 8).reshape(-1, 3).astype(np.int64)
    keys = bins[:, 0] * 1024 + bins[:, 1] * 32 + bins[:, 2]
    common = np.bincount(keys).argmax()
    return rgb.reshape(-1, 3)[keys == common].mean(axis=0)


def figures(rgb: np.ndarray, threshold: int) -> list[tuple[np.ndarray, tuple[int, int, int, int]]]:
    """Máscaras das figuras da folha (uma por região grande), com a caixa (x0, y0, x1, y1) de cada uma."""
    bg = background_color(rgb)
    diff = np.abs(rgb.astype(int) - bg.astype(int)).max(axis=2)
    mask = diff > threshold
    mask = ndimage.binary_opening(mask, iterations=3)  # some com linhas finas (molduras, setas)
    # Junta partes da mesma figura separadas por traços finos (cabelo, mãos) antes de rotular.
    joined = ndimage.binary_closing(mask, iterations=4)
    labels, count = ndimage.label(joined)
    if count == 0:
        raise RuntimeError("nenhuma figura encontrada: o fundo é liso? tente --limiar menor")
    edge = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    touching = set(np.unique(edge)) - {0}
    sizes = ndimage.sum(joined, labels, range(1, count + 1))
    boxes = ndimage.find_objects(labels)
    h, w = labels.shape
    frames = {i + 1 for i, (ys, xs) in enumerate(boxes)  # molduras e vinhetas: uma região do tamanho da folha
              if (ys.stop - ys.start) > FRAME * h and (xs.stop - xs.start) > FRAME * w}
    inside = [(i + 1, s) for i, s in enumerate(sizes) if i + 1 not in touching | frames]
    if not inside:
        raise RuntimeError("todas as figuras encostam na borda da folha")
    largest = max(s for _, s in inside)
    keep = [label for label, s in inside if s >= MIN_AREA * largest]
    found = []
    for label in keep:
        region = labels == label
        ys, xs = np.nonzero(region)
        box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        fig = ndimage.binary_fill_holes(region & ndimage.binary_dilation(mask, iterations=2))
        found.append((fig, box))
    # Ordem de leitura: linhas (caixas que se sobrepõem na vertical) e, dentro delas, da esquerda para a direita.
    found.sort(key=lambda f: f[1][1])
    rows: list[list] = []
    for fig in found:
        y0, y1 = fig[1][1], fig[1][3]
        for row in rows:
            ry0, ry1 = row[0][1][1], row[0][1][3]
            if min(y1, ry1) - max(y0, ry0) > 0.5 * min(y1 - y0, ry1 - ry0):
                row.append(fig)
                break
        else:
            rows.append([fig])
    return [fig for row in rows for fig in sorted(row, key=lambda f: f[1][0])]


def prepare(sheet_path: Path, names: list[str], threshold: int, out_dir: Path, crop=None) -> list[Path]:
    sheet = Image.open(sheet_path).convert("RGB")
    if crop:
        sheet = sheet.crop(crop)
    rgb = np.asarray(sheet)
    found = figures(rgb, threshold)
    picked = [(name, int(index) - 1) for name, index in (n.split(":") for n in names if ":" in n)]
    if picked:
        if any(i < 0 or i >= len(found) for _, i in picked):
            raise RuntimeError(f"{sheet_path.name} tem {len(found)} figura(s); índice fora da faixa em --vistas")
        names, found = [n for n, _ in picked], [found[i] for _, i in picked]
    elif len(found) != len(names):
        print(f"  aviso: {sheet_path.name} tem {len(found)} figura(s), esperava {len(names)} ({', '.join(names)}); "
              f"saindo como vista_N; escolha com --vistas nome:índice")
        for i, (_, box) in enumerate(found):
            print(f"    {i + 1}: caixa x {box[0]}-{box[2]}, y {box[1]}-{box[3]}")
        names = [f"vista_{i + 1}" for i in range(len(found))]
    crops = []
    for mask, (x0, y0, x1, y1) in found:
        alpha = (mask[y0:y1, x0:x1] * 255).astype(np.uint8)
        crops.append(Image.fromarray(np.dstack([rgb[y0:y1, x0:x1], alpha]), "RGBA"))

    biggest = max(max(c.size) for c in crops)  # mesma escala em todas as vistas da folha
    scale = CANVAS * (1 - 2 * MARGIN) / biggest
    stem = sheet_path.stem
    paths = []
    for name, crop in zip(names, crops):
        size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
        crop = crop.resize(size, Image.LANCZOS)
        canvas = Image.new("RGB", (CANVAS, CANVAS), BACKGROUND)
        canvas.paste(crop, ((CANVAS - size[0]) // 2, (CANVAS - size[1]) // 2), crop)
        path = out_dir / f"{stem}_{name}.png"
        canvas.save(path)
        paths.append(path)
        print(f"  {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}  figura {size[0]}x{size[1]}")

    preview(paths, out_dir / f"_previa_{stem}.png")
    return paths


def preview(paths: list[Path], out: Path, tile: int = 360) -> None:
    font = ImageFont.truetype(FONT, 20)
    sheet = Image.new("RGB", (tile * len(paths), tile + 32), "white")
    for i, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((tile, tile))
        sheet.paste(image, (i * tile, 32))
        ImageDraw.Draw(sheet).text((i * tile + 8, 6), path.stem, fill="black", font=font)
    sheet.save(out)
    print(f"  prévia: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--folha", help="uma folha (nome em folhas/ ou caminho); padrão: todas as de folhas/")
    parser.add_argument("--vistas", default="frente,lado,costas", help="nomes das vistas, da esquerda para a direita")
    parser.add_argument("--limiar", type=int, default=28, help="diferença de cor mínima para ser figura (0-255)")
    parser.add_argument("--saida", help="pasta de saída (padrão: assets/conceitos/aldeao_v2/vistas)")
    parser.add_argument("--recorte", help="x0,y0,x1,y1: usar só essa região da folha (folhas com fundo desenhado)")
    args = parser.parse_args()

    out_dir = Path(args.saida) if args.saida else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.folha:
        candidate = Path(args.folha)
        sheets = [candidate if candidate.exists() else SHEETS / args.folha]
    else:
        sheets = sorted(p for p in SHEETS.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
    if not sheets:
        print(f"nenhuma folha em {SHEETS.relative_to(ROOT)}")
        return
    names = [n.strip() for n in args.vistas.split(",") if n.strip()]
    for sheet in sheets:
        print(sheet.name)
        crop = tuple(int(v) for v in args.recorte.split(",")) if args.recorte else None
        prepare(sheet, names, args.limiar, out_dir, crop)


if __name__ == "__main__":
    main()

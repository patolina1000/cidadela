"""Monta os GIFs da roda a partir dos quadros do gif_roda.py: câmera do jogo (zoom 2,5, aldeão ~112 px, em
pixels reais, recortada em volta) e lado (aldeão de 0,40 m = 256 px), cada um também multiplicado por #6A5B7C
(crepúsculo). Fundo do chão #4E4A58, uma paleta por GIF, 24 quadros/s, em laço.

Uso: uv run gif_roda_montar.py <pasta_dos_quadros> <pasta_saida>
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops

GROUND = (78, 74, 88)
TWILIGHT = (106, 91, 124)
MS = 42  # 24 quadros/s


def frames(src: Path, view: str) -> list:
    return [Image.open(p).convert("RGBA") for p in sorted(src.glob(f"{view}_*.png"))]


def crop_box(ims, pad) -> tuple:
    boxes = [im.getchannel("A").getbbox() for im in ims]
    x0, y0 = min(b[0] for b in boxes) - pad, min(b[1] for b in boxes) - pad
    x1, y1 = max(b[2] for b in boxes) + pad, max(b[3] for b in boxes) + pad
    w, h = ims[0].size
    return max(0, x0), max(0, y0), min(w, x1), min(h, y1)


def compose(im, box, twilight) -> Image.Image:
    crop = im.crop(box)
    out = Image.new("RGBA", crop.size, (*GROUND, 255))
    out.alpha_composite(crop)
    rgb = out.convert("RGB")
    if twilight:
        rgb = ImageChops.multiply(rgb, Image.new("RGB", rgb.size, TWILIGHT))
    return rgb


def save_gif(rgbs, path: Path) -> None:
    mosaic = Image.new("RGB", (rgbs[0].width, rgbs[0].height * len(rgbs)))
    for i, im in enumerate(rgbs):
        mosaic.paste(im, (0, i * im.height))
    pal = mosaic.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in rgbs]
    q[0].save(path, save_all=True, append_images=q[1:], duration=MS, loop=0, disposal=1, optimize=False)
    print(path, f"{rgbs[0].width}x{rgbs[0].height}", len(q))


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    for view, pad in (("jogo", 24), ("lado", 16)):
        ims = frames(src, view)
        box = crop_box(ims, pad)
        for twilight in (False, True):
            save_gif([compose(im, box, twilight) for im in ims], dst / f"roda_{view}{'_crepusculo' if twilight else ''}.gif")


if __name__ == "__main__":
    main()

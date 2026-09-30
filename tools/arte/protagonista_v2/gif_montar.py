"""Protagonista v2: monta os GIFs de comparação dos clipes a partir dos quadros do protagonista_v2/gif_clipes.py
(versão do aldeao_v2/gif_montar.py).

Por opção: <rotulo>_jogo.gif (protagonista a 80 px de altura, como no zoom 1 em 3024x1890, ampliada 2x sem
suavizar) e <rotulo>_lado.gif (maior). Também uma folha de contato com um quadro de cada opção e as medidas.

Uso (em tools/arte): uv run protagonista_v2/gif_montar.py <pasta_dos_quadros> <pasta_saida> [rotulo ...]
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
GAME_PX, GAME_ZOOM, SIDE_PX = 80, 2, 320
HEIGHT, ORTHO_GAME = 0.80, 1.3  # protagonista_v2/gif_clipes.py
GROUND = (78, 74, 88)


def frames_of(folder: Path, view: str):
    return sorted(folder.glob(f"{view}_*.png"))


def to_palette(frames):
    """Todos os quadros com a mesma paleta (a do primeiro), sem alfa: evita cores embaralhadas e cintilação."""
    base = frames[0].convert("RGB").quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    return [f.convert("RGB").quantize(palette=base, dither=Image.Dither.NONE) for f in frames]


def save_gif(frames, out: Path, fps: float) -> None:
    tiles = to_palette(frames)
    tiles[0].save(out, save_all=True, append_images=tiles[1:], duration=int(round(1000 / fps)), loop=0, disposal=1)


def game_gif(folder: Path, out: Path, info: dict) -> None:
    frames = frames_of(folder, "jogo")
    first = Image.open(frames[0]).convert("RGBA")
    # Escala fixa pela altura de repouso: 80 px = 0,80 m; o quadro cobre ORTHO_GAME m em RESOLUTION px.
    scale = GAME_PX / (HEIGHT / ORTHO_GAME * first.height)
    win = int(130 / scale)  # janela de 130 px finais em volta do centro
    cx, cy = first.width // 2, first.height // 2
    tiles = []
    for f in frames:
        im = Image.open(f).convert("RGBA").crop((cx - win // 2, cy - win // 2, cx + win // 2, cy + win // 2))
        small = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        bg = Image.new("RGBA", small.size, (*GROUND, 255))
        bg.alpha_composite(small)
        tiles.append(bg.resize((bg.width * GAME_ZOOM, bg.height * GAME_ZOOM), Image.NEAREST))
    save_gif(tiles, out, info["fps"])


def side_gif(folder: Path, out: Path, info: dict) -> None:
    tiles = []
    for f in frames_of(folder, "lado"):
        im = Image.open(f).convert("RGBA").resize((SIDE_PX, SIDE_PX), Image.LANCZOS)
        bg = Image.new("RGBA", im.size, (*GROUND, 255))
        bg.alpha_composite(im)
        tiles.append(bg)
    save_gif(tiles, out, info["fps"])


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    labels = sys.argv[3:] or sorted(p.name for p in src.iterdir() if (p / "info.json").exists())
    out.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(FONT, 15)
    rows = []
    for label in labels:
        folder = src / label
        info = json.loads((folder / "info.json").read_text())
        game_gif(folder, out / f"{label}_jogo.gif", info)
        side_gif(folder, out / f"{label}_lado.gif", info)
        mid = frames_of(folder, "lado")[len(frames_of(folder, "lado")) // 2]
        im = Image.open(mid).convert("RGBA").resize((200, 200), Image.LANCZOS)
        bg = Image.new("RGBA", (200, 200), (*GROUND, 255))
        bg.alpha_composite(im)
        row = Image.new("RGB", (620, 200), "white")
        row.paste(bg.convert("RGB"), (0, 0))
        text = (f"{label}\n{info['acao']} ({info['glb'].split('/')[-1]})\n{info['quadros'][1] - info['quadros'][0]} quadros, {info['duracao_s']:.2f} s\n"
                f"raiz {info['velocidade_raiz_m_s']} m/s | pés {info['passada_pes_m_s']} m/s\nchão a {info['velocidade_chao_m_s']} m/s | laço {info['laco_m'] * 100:.1f} cm")
        ImageDraw.Draw(row).text((210, 10), text, fill="black", font=font)
        rows.append(row)
        print(f"{label}: {out / (label + '_jogo.gif')} e _lado.gif")
    sheet = Image.new("RGB", (620, 204 * len(rows)), "white")
    for i, r in enumerate(rows):
        sheet.paste(r, (0, i * 204))
    sheet.save(out / "_opcoes.png")


if __name__ == "__main__":
    main()

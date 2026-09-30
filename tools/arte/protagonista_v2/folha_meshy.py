"""Passo 2: folha de contato dos corpos brutos da Meshy, a partir dos renders do render_meshy.py.

Uma fileira por geração: frente, lado, 3/4 (ortográficas, com o aldeão v2 ao lado) e a câmera do jogo nos zooms
0,4 / 1 / 2,5 em recorte 1:1 dos 3024×1890 (sem reduzir: é o tamanho real na tela). Fundo #4E4A58.
Mede a cabeça na máscara de frente com o mesmo head_profile do conferir_recortes.py (largura máxima ÷ topo ao
queixo), para comparar com a folha (corpo 0,935). Grava também a versão crepúsculo (tudo × #6A5B7C).

Uso (em tools/arte): uv run protagonista_v2/folha_meshy.py <pasta_dos_renders> <notas.json> <nome> [<nome> ...]
  notas.json: {"<nome>": {"rotulo": "...", "notas": ["...", ...]}} (observações de mãos, pés, anatomia)
Saída: assets/previews/protagonista_v2/meshy_corpo.png, meshy_corpo_crepusculo.png e meshy_corpo.json
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conferir_recortes import head_profile  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BG = (78, 74, 88)  # #4E4A58
PAPER = (237, 230, 214)  # osso #EDE6D6
INK = (27, 22, 32)  # traço #1B1620
TWILIGHT = (0x6A, 0x5B, 0x7C)
TILE = 400
ZOOMS = ("0.4", "1.0", "2.5")
TARGET_PX = {"0.4": 28, "1.0": 68, "2.5": 179}  # nota 01
SHEET_HEAD = 0.935  # conferir_recortes: corpo, vista de frente
SHEET_HEAD_FIG = 0.144  # altura da cabeça (topo ao queixo) ÷ altura da figura na mesma folha


def br(text: str) -> str:
    """Números no jeito brasileiro: 0.915 -> 0,915 e 2,602 (milhar) -> 2.602."""
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "\x00", text)  # só entre dígitos: a vírgula do texto fica
    text = re.sub(r"(?<=\d)\.(?=\d)", ",", text)
    return text.replace("\x00", ".")


def on_bg(img: Image.Image) -> Image.Image:
    base = Image.new("RGBA", img.size, BG + (255,))
    base.alpha_composite(img.convert("RGBA"))
    return base.convert("RGB")


def ortho_tile(path: Path) -> Image.Image:
    img = on_bg(Image.open(path))
    img.thumbnail((TILE, TILE), Image.LANCZOS)
    return img


def game_tile(path: Path, box) -> Image.Image:
    """Recorte 1:1 de TILE×TILE centrado no par (protagonista + aldeão)."""
    img = on_bg(Image.open(path))
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    x0, y0 = int(round(cx - TILE / 2)), int(round(cy - TILE / 2))
    return img.crop((x0, y0, x0 + TILE, y0 + TILE))


def head_ratio(mask_path: Path) -> dict:
    alpha = np.array(Image.open(mask_path).convert("RGBA"))[:, :, 3] > 127
    p = head_profile(alpha, None, head_frac=0.18)
    h = p["queixo_y"] - p["topo"]
    fig = np.nonzero(alpha.any(axis=1))[0]
    return {"largura_sobre_altura": round(p["largura_max"] / h, 3), "largura_px": int(p["largura_max"]),
            "altura_px": int(h), "cabeca_sobre_figura": round(float(h / (fig.max() - fig.min() + 1)), 3)}


def labeled(img: Image.Image, text: str, font) -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + 28), PAPER)
    out.paste(img, (0, 28))
    ImageDraw.Draw(out).text((6, 4), text, fill=INK, font=font)
    return out


def main() -> None:
    renders, notes_path, names = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
    notes = json.loads(notes_path.read_text())
    font = ImageFont.truetype(FONT, 17)
    small = ImageFont.truetype(FONT, 16)
    title_font = ImageFont.truetype(FONT, 24)
    rows, report = [], {}
    for name in names:
        m = json.loads((renders / f"{name}_medidas.json").read_text())
        head = head_ratio(renders / f"{name}_mascara.png")
        tiles = [labeled(ortho_tile(renders / f"{name}_{v}.png"), t, font)
                 for v, t in (("frente", "frente"), ("lado", "lado (perfil esquerdo)"), ("tres_quartos", "3/4"))]
        for z in ZOOMS:
            j = m["jogo"][z]
            tiles.append(labeled(game_tile(renders / f"{name}_jogo_{z}.png", j["caixa_px"]),
                                 br(f"jogo zoom {z.rstrip('0').rstrip('.')} (1:1): "
                                    f"{j['protagonista_px']:.0f} px (alvo {TARGET_PX[z]})"), font))
        px = " / ".join(f"{m['jogo'][z]['protagonista_px']:.0f}" for z in ZOOMS)
        vpx = " / ".join(f"{m['jogo'][z]['aldeao_px']:.0f}" for z in ZOOMS)
        s = m["simetria"]
        lines = [
            f"{notes[name]['rotulo']}  —  {m['triangulos']:,} triângulos brutos; 0,80 m; largura {m['largura_m']:.3f} m "
            f"(pose A), profundidade {m['profundidade_m']:.3f} m",
            f"câmera do jogo: {px} px (alvo 28 / 68 / 179); aldeão ao lado {vpx} px (nota 01: 19 / 44 / 112)",
            f"cabeça L÷A {head['largura_sobre_altura']:.3f} (folha {SHEET_HEAD}); cabeça = {100 * head['cabeca_sobre_figura']:.1f}% "
            f"da altura (folha {100 * SHEET_HEAD_FIG:.1f}%); simetria: espelho a {s['media_mm']} mm em média, "
            f"p95 {s['p95_mm']} mm, máx {s['max_mm']} mm",
        ]
        lines = [br(line) for line in lines] + notes[name]["notas"]
        rows.append((tiles, lines))
        report[name] = {"medidas": m, "cabeca": head, "notas": notes[name]}

    width = sum(t.width for t in rows[0][0])
    line_h = 22
    heights = [rows_tiles[0].height + 12 + line_h * len(lines) + 24 for rows_tiles, lines in rows]
    title_h = 48
    sheet = Image.new("RGB", (width, title_h + sum(heights)), PAPER)
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), "Protagonista v2 — corpo bruto da Meshy (sem limpeza), com o aldeão v2 ao lado; "
                     "toon chapado, luz fraca e fria de cima; câmera do jogo 55°, FOV 45°, 16 m ÷ zoom, recortes 1:1 de 3024×1890",
           fill=INK, font=title_font)
    y = title_h
    for (tiles, lines), h in zip(rows, heights):
        x = 0
        for t in tiles:
            sheet.paste(t, (x, y))
            x += t.width
        ty = y + tiles[0].height + 8
        for k, line in enumerate(lines):
            d.text((10, ty + k * line_h), line, fill=INK, font=font if k == 0 else small)
        y += h
    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT / "meshy_corpo.png")
    ImageChops.multiply(sheet, Image.new("RGB", sheet.size, TWILIGHT)).save(OUT / "meshy_corpo_crepusculo.png")
    (OUT / "meshy_corpo.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    for name, r in report.items():
        print(name, r["cabeca"], {z: r["medidas"]["jogo"][z]["protagonista_px"] for z in ZOOMS})


if __name__ == "__main__":
    main()

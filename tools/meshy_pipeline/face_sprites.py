"""Traços do rosto do aldeão desenhados por código (SVG -> PNG com fundo 100% transparente).

Estilo do conceito: olhos grandes e redondos, branco levemente acinzentado, pupila pequena e escura,
olheira suave, contorno escuro fino; sobrancelhas finas; bocas pequenas e simples. Nada de pele nem de
sombreado pintado.

Duas folhas, cada uma com células do mesmo tamanho e o desenho centralizado no mesmo ponto:
- olhos (com sobrancelhas), 3 x 3 células de 512 x 256: EYES, na ordem abaixo;
- boca, 3 x 2 células de 256 x 128 (baixas: o plano da boca não chega ao queixo): MOUTHS, na ordem abaixo.
Célula i: coluna i % 3, linha i // 3 (de cima para baixo). Os SVGs ficam ao lado dos PNGs.

Uso: uv run face_sprites.py
"""

import os
import sys
from pathlib import Path

if "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ:  # o cairo do Homebrew, para o cairosvg
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib"
    os.execv(sys.executable, [sys.executable, *sys.argv])

import cairosvg  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets/texturas/aldeao"

INK = "#1b1e26"  # contorno
WHITE = "#e3e7eb"  # branco do olho, levemente acinzentado
PUPIL = "#15171c"
SHADOW = "#2c3142"  # olheira (com transparência e desfoque)
TEAR = "#cfe3f1"
MOUTH_IN = "#2a1e27"  # interior da boca
TEETH = "#eef0f2"
LINE = 5  # espessura do contorno, px na célula

EYE_W, EYE_H = 512, 256
MOUTH_W, MOUTH_H = 256, 128
LEFT, RIGHT = (150, 136), (362, 136)  # centro de cada olho na célula
R = 74  # raio do olho

EYES = ["distraído", "esforço", "feliz", "sonolento", "fechado", "espantado", "preocupado", "chorando", "bravo"]
MOUTHS = ["neutra", "entreaberta", "sorriso", "esforço", "o", "triste"]

DEFS = f"""<defs>
  <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="7"/></filter>
</defs>"""


def eye(cx: float, cy: float, *, r: float = R, look=(0, 0), pupil: float = 15, lid_top: float | None = None,
        lid_angle: float = 0, bottom_lid: float | None = None, side: int = 1) -> str:
    """Olho redondo. lid_top: altura (a partir do centro, px) onde a pálpebra de cima corta o olho;
    lid_angle: inclinação da pálpebra (graus, positivo desce para o nariz); bottom_lid: corte de baixo."""
    clip_id = f"clip{int(cx)}{int(cy)}{int(r)}{lid_top}{lid_angle}{bottom_lid}".replace(".", "").replace("-", "m")
    parts = [f'<ellipse cx="{cx}" cy="{cy + r * 0.62}" rx="{r * 0.95}" ry="{r * 0.42}" fill="{SHADOW}" '
             f'opacity="0.28" filter="url(#blur)"/>']
    lines, lid_clip = [], None
    if lid_top is not None or bottom_lid is not None:
        top = cy - (lid_top if lid_top is not None else r + 10)
        bottom = cy + (bottom_lid if bottom_lid is not None else r + 10)
        tilt = lid_angle * side
        lid_clip = (f'<g transform="rotate({tilt} {cx} {cy})"><rect x="{cx - r - 12}" y="{top}" '
                    f'width="{2 * r + 24}" height="{bottom - top}"/></g>')
        for edge, cut in ((top, lid_top), (bottom, bottom_lid)):
            if cut is None:
                continue
            half = (r ** 2 - min(cut, r - 1) ** 2) ** 0.5
            lines.append(f'<g transform="rotate({tilt} {cx} {cy})"><line x1="{cx - half}" y1="{edge}" '
                         f'x2="{cx + half}" y2="{edge}" stroke="{INK}" stroke-width="{LINE + 1}" '
                         f'stroke-linecap="round"/></g>')
    parts.append(f'<clipPath id="{clip_id}c"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>')
    if lid_clip:
        parts.append(f'<clipPath id="{clip_id}l">{lid_clip}</clipPath>')
    px, py = cx + look[0], cy + look[1]
    inner = (f'<g clip-path="url(#{clip_id}c)"><circle cx="{cx}" cy="{cy}" r="{r}" fill="{WHITE}"/>'
             f'<circle cx="{px}" cy="{py}" r="{pupil}" fill="{PUPIL}"/>'
             f'<circle cx="{px - pupil * 0.35}" cy="{py - pupil * 0.4}" r="{pupil * 0.28}" fill="#ffffff"/></g>'
             f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="{LINE}"/>')
    parts.append(f'<g clip-path="url(#{clip_id}l)">{inner}</g>' if lid_clip else inner)
    return "".join(parts + lines)


def brow(cx: float, cy: float, *, tilt: float = 0, arch: float = 8, width: float = 70, side: int = 1) -> str:
    """Sobrancelha fina: arco com as pontas afinadas. tilt positivo abaixa a ponta de dentro (bravo)."""
    inner = cx - side * width / 2
    outer = cx + side * width / 2
    y_in, y_out = cy + tilt, cy - tilt
    return (f'<path d="M {inner} {y_in} Q {cx} {cy - arch - abs(tilt) * 0.3} {outer} {y_out}" fill="none" '
            f'stroke="{INK}" stroke-width="{LINE}" stroke-linecap="round"/>')


def tear(cx: float, cy: float) -> str:
    return (f'<path d="M {cx} {cy} C {cx - 10} {cy + 16} {cx - 11} {cy + 30} {cx} {cy + 32} '
            f'C {cx + 11} {cy + 30} {cx + 10} {cy + 16} {cx} {cy} Z" fill="{TEAR}" stroke="{INK}" '
            f'stroke-width="3"/>')


def eyes_svg(kind: str) -> str:
    (lx, ly), (rx, ry) = LEFT, RIGHT
    by = ly - R - 22  # altura das sobrancelhas
    body = []
    if kind == "distraído":
        body += [eye(lx, ly, look=(18, -10)), eye(rx, ry, look=(18, -10)),
                 brow(lx, by, arch=10, side=-1), brow(rx, by, arch=10)]
    elif kind == "esforço":
        body += [eye(lx, ly, lid_top=34, lid_angle=10, side=1), eye(rx, ry, lid_top=34, lid_angle=10, side=-1),
                 brow(lx, by + 22, tilt=10, arch=2, side=-1), brow(rx, by + 22, tilt=10, arch=2)]
    elif kind == "feliz":
        body += [eye(lx, ly, bottom_lid=46), eye(rx, ry, bottom_lid=46),
                 brow(lx, by - 6, arch=14, side=-1), brow(rx, by - 6, arch=14)]
    elif kind == "sonolento":
        body += [eye(lx, ly, lid_top=8, look=(0, 22)), eye(rx, ry, lid_top=8, look=(0, 22)),
                 brow(lx, by + 10, arch=4, side=-1), brow(rx, by + 10, arch=4)]
    elif kind == "fechado":
        for cx, cy in (LEFT, RIGHT):
            body.append(f'<ellipse cx="{cx}" cy="{cy + R * 0.6}" rx="{R * 0.95}" ry="{R * 0.42}" fill="{SHADOW}" '
                        f'opacity="0.28" filter="url(#blur)"/>')
            body.append(f'<path d="M {cx - R + 6} {cy + 10} Q {cx} {cy + 44} {cx + R - 6} {cy + 10}" fill="none" '
                        f'stroke="{INK}" stroke-width="{LINE + 2}" stroke-linecap="round"/>')
        body += [brow(lx, by + 14, arch=6, side=-1), brow(rx, by + 14, arch=6)]
    elif kind == "espantado":
        body += [eye(lx, ly, r=R + 8, pupil=10), eye(rx, ry, r=R + 8, pupil=10),
                 brow(lx, by - 16, arch=16, side=-1), brow(rx, by - 16, arch=16)]
    elif kind == "preocupado":
        body += [eye(lx, ly, look=(6, -16)), eye(rx, ry, look=(-6, -16)),
                 brow(lx, by, tilt=-12, arch=4, side=-1), brow(rx, by, tilt=-12, arch=4)]
    elif kind == "chorando":
        body += [eye(lx, ly, look=(0, 10), bottom_lid=52), eye(rx, ry, look=(0, 10), bottom_lid=52),
                 brow(lx, by + 4, tilt=-12, arch=4, side=-1), brow(rx, by + 4, tilt=-12, arch=4),
                 tear(lx - 30, ly + 52), tear(rx + 30, ry + 52)]
    elif kind == "bravo":
        body += [eye(lx, ly, lid_top=30, lid_angle=16, side=1), eye(rx, ry, lid_top=30, lid_angle=16, side=-1),
                 brow(lx, by + 26, tilt=14, arch=0, side=-1), brow(rx, by + 26, tilt=14, arch=0)]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{EYE_W}" height="{EYE_H}" '
            f'viewBox="0 0 {EYE_W} {EYE_H}">{DEFS}{"".join(body)}</svg>')


def mouth_svg(kind: str) -> str:
    c = MOUTH_W / 2  # centro x; o y usa o mesmo número deslocado (célula 2:1)
    shift = MOUTH_H / 2 - c
    stroke = f'stroke="{INK}" stroke-width="{LINE}" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "neutra":
        body = f'<path d="M {c - 22} {c} Q {c} {c + 4} {c + 22} {c}" fill="none" {stroke}/>'
    elif kind == "entreaberta":
        body = f'<ellipse cx="{c}" cy="{c}" rx="15" ry="10" fill="{MOUTH_IN}" {stroke}/>'
    elif kind == "sorriso":
        body = (f'<path d="M {c - 34} {c - 8} Q {c} {c - 4} {c + 34} {c - 8} Q {c + 22} {c + 26} {c} {c + 26} '
                f'Q {c - 22} {c + 26} {c - 34} {c - 8} Z" fill="{MOUTH_IN}" {stroke}/>')
    elif kind == "esforço":
        body = (f'<rect x="{c - 30}" y="{c - 12}" width="60" height="24" rx="9" fill="{TEETH}" {stroke}/>'
                f'<line x1="{c - 28}" y1="{c}" x2="{c + 28}" y2="{c}" stroke="{INK}" stroke-width="3"/>'
                + "".join(f'<line x1="{c + x}" y1="{c - 11}" x2="{c + x}" y2="{c + 11}" stroke="{INK}" '
                          f'stroke-width="2.5"/>' for x in (-15, 0, 15)))
    elif kind == "o":
        body = f'<ellipse cx="{c}" cy="{c}" rx="14" ry="19" fill="{MOUTH_IN}" {stroke}/>'
    elif kind == "triste":
        body = f'<path d="M {c - 24} {c + 8} Q {c} {c - 12} {c + 24} {c + 8}" fill="none" {stroke}/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{MOUTH_W}" height="{MOUTH_H}" '
            f'viewBox="0 0 {MOUTH_W} {MOUTH_H}"><g transform="translate(0 {shift})">{body}</g></svg>')


def sheet(name: str, cells: list[str], render, cell_w: int, cell_h: int, rows: int) -> None:
    """Monta a folha num SVG só (cada célula num grupo deslocado) e exporta o PNG."""
    groups = []
    for i, kind in enumerate(cells):
        inner = render(kind)
        body = inner[inner.index(">") + 1:inner.rindex("</svg>")]
        groups.append(f'<g transform="translate({i % 3 * cell_w} {i // 3 * cell_h})">{body}</g>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{cell_w * 3}" height="{cell_h * rows}">'
           f'{"".join(groups)}</svg>')
    (OUT / f"{name}.svg").write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(OUT / f"{name}.png"))
    print(f"{(OUT / name).relative_to(ROOT)}.png: {len(cells)} células de {cell_w}x{cell_h}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sheet("olhos", EYES, eyes_svg, EYE_W, EYE_H, 3)
    sheet("bocas", MOUTHS, mouth_svg, MOUTH_W, MOUTH_H, 2)


if __name__ == "__main__":
    main()

"""Compara o atlas de antes e o de depois do ajuste de feliz, preocupado e bravo (29/09/2026): cada expressão em
96 px sobre a esfera, multiplicada pelo roxo do crepúsculo (#6A5B7C), antes em cima e depois embaixo.

Uso: uv run comparar_ajuste.py <pasta_com_olhos_e_boca_de_antes>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from desenhar_rosto import EXPRESSIONS, FONT, INK, OUT, PREVIEWS, ROOT, face_from_atlas, twilight

SIZE = 96
KINDS = ["feliz", "preocupado", "bravo"]


def main() -> None:
    before_dir = Path(sys.argv[1])
    sets = [("antes", Image.open(before_dir / "olhos.png"), Image.open(before_dir / "boca.png")),
            ("depois", Image.open(OUT / "olhos.png"), Image.open(OUT / "boca.png"))]
    font = ImageFont.truetype(FONT, 15)
    gap, label_w = 12, 70
    sheet = Image.new("RGBA", (label_w + (SIZE + gap) * len(KINDS) + gap, (SIZE + gap) * 2 + gap + 22), (58, 50, 70, 255))
    d = ImageDraw.Draw(sheet)
    for c, kind in enumerate(KINDS):
        d.text((label_w + gap + c * (SIZE + gap), 4), kind, fill=(220, 214, 226), font=font)
    for r, (label, eyes, mouths) in enumerate(sets):
        y = 22 + gap + r * (SIZE + gap)
        d.text((8, y + SIZE // 2 - 8), label, fill=(220, 214, 226), font=font)
        for c, kind in enumerate(KINDS):
            e, m = EXPRESSIONS[kind]
            tile = face_from_atlas(eyes, mouths, e, m).resize((SIZE, SIZE), Image.LANCZOS)
            sheet.alpha_composite(twilight(tile), (label_w + gap + c * (SIZE + gap), y))
    out = PREVIEWS / "comparacao_ajuste.png"
    sheet.convert("RGB").save(out)
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()

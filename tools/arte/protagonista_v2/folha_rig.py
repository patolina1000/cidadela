"""Parada 1: folha do corpo com rig (repouso e quadros dos clipes provisórios, retalhos acompanhando a cabeça), a partir
das prévias do montar_rig.py e do protagonista_corpo_prova.json.

Uso (em tools/arte): uv run protagonista_v2/folha_rig.py <pasta_previas>
Saída: assets/previews/protagonista_v2/rig_parada1.png
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folha_meshy import FONT, INK, PAPER, br, labeled  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_prova.json"
OUT = ROOT / "assets/previews/protagonista_v2/rig_parada1.png"
TILE = 360


def main() -> None:
    src = Path(sys.argv[1])
    rep = json.loads(REPORT.read_text())
    font = ImageFont.truetype(FONT, 16)
    names = [("repouso_frente", "repouso, frente (pesos transferidos)"), ("repouso_tres_quartos", "repouso, 3/4"),
             ("idle-loop_tres_quartos", "idle provisório (Idle), 3/4"), ("idle-loop_cabeca_tres_quartos", "idle: retalhos com a cabeça"),
             ("run-loop_tres_quartos", "corrida provisória (básica), 3/4"), ("run-loop_cabeca_tres_quartos", "corrida: retalhos com a cabeça"),
             ("run-loop_jogo", "corrida, câmera do jogo (ortográfica)")]
    tiles = [labeled(Image.open(src / f"{n}.png").convert("RGB").resize((TILE, TILE), Image.LANCZOS), t, font) for n, t in names]
    lines = [
        "Protagonista v2 — parada 1: rig da Meshy no corpo limpo (24 ossos), pesos nas 9 malhas, retalhos do rosto (b3) no Head",
        br(f"Pesos: transferidos da malha da Meshy para as 9 regiões, 0 vértices sem peso; pele da frente da cabeça 100% Head em "
           f"{rep['pele_do_rosto_no_head_vertices']} vértices."),
        br(f"Retalhos a {rep['offset_mm']:.0f} mm: folga entre {rep['folga_minima_mm']} e {rep['folga_maxima_mm']} mm em 6 quadros de cada clipe "
           "(nunca atravessa). Defeito a corrigir: na corrida, uma ponta do short sai atrás da coxa (peso da bainha)."),
        br(f"GLB pelo contrato: Armature escala 1, metros, 24 fps, t = 0; {rep['conferencia']['triangulos_corpo']:,} triângulos no corpo; "
           f"materiais {', '.join(rep['conferencia']['materiais'])}. Clipes deste GLB são PROVISÓRIOS (Idle e corrida básica), só para a conferência."),
    ]
    width = TILE * 4
    rows = [tiles[:4], tiles[4:]]
    header = 30 + 24 * len(lines)
    sheet = Image.new("RGB", (width, header + sum(r[0].height for r in rows)), PAPER)
    d = ImageDraw.Draw(sheet)
    for i, line in enumerate(lines):
        d.text((10, 8 + 24 * i), line, fill=INK, font=ImageFont.truetype(FONT, 20 if i == 0 else 15))
    y = header
    for row in rows:
        for i, t in enumerate(row):
            sheet.paste(t, (i * TILE, y))
        y += row[0].height
    sheet.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()

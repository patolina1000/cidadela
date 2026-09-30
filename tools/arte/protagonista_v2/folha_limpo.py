"""Passo 3: folha de contato do corpo limpo, a partir dos renders do render_limpo.py e do protagonista_corpo_limpeza.json.

Fileira 1: frente, lado, costas, 3/4 (com o aldeão v2 ao lado). Fileira 2: câmera do jogo 1:1 nos zooms 0,4 / 1 / 2,5 e
as regiões de frente. Fileira 3: regiões de lado e de costas e as medidas. Grava também a versão crepúsculo.
A cabeça é medida de novo na máscara de frente, pelo head_profile das folhas (conferência da conta do limpar_corpo.py).

Uso (em tools/arte): uv run protagonista_v2/folha_limpo.py <pasta_dos_renders>
Saída: assets/previews/protagonista_v2/corpo_limpo.png, corpo_limpo_crepusculo.png e corpo_limpo.json
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conferir_recortes import head_profile  # noqa: E402
from folha_meshy import FONT, INK, PAPER, TARGET_PX, TWILIGHT, br, game_tile, labeled, on_bg  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2"
REPORT = ROOT / "assets/modelos/protagonista_v2/protagonista_corpo_limpeza.json"
TILE = 400
ZOOMS = ("0.4", "1.0", "2.5")
MASK_ORTHO, MASK_RES = 0.88, 1024  # render_limpo.py


def main() -> None:
    renders = Path(sys.argv[1])
    info = json.loads((renders / "render.json").read_text())
    clean = json.loads(REPORT.read_text())
    font = ImageFont.truetype(FONT, 17)
    title_font = ImageFont.truetype(FONT, 24)

    alpha = np.array(Image.open(renders / "mascara.png").convert("RGBA"))[:, :, 3] > 127
    prof = head_profile(alpha, None, head_frac=0.25)
    fig = np.nonzero(alpha.any(axis=1))[0]
    head_sil = (prof["queixo_y"] - prof["topo"]) / (fig.max() - fig.min() + 1)

    def ortho(name, text):
        img = on_bg(Image.open(renders / f"{name}.png")).resize((TILE, TILE), Image.LANCZOS)
        return labeled(img, text, font)

    row1 = [ortho(v, t) for v, t in (("frente", "frente"), ("lado", "lado (perfil esquerdo)"), ("costas", "costas"),
                                        ("tres_quartos", "3/4"))]
    row2 = [labeled(game_tile(renders / f"jogo_{z}.png", info["jogo"][z]["caixa_px"]),
                    br(f"jogo zoom {z.rstrip('0').rstrip('.')} (1:1): {info['jogo'][z]['protagonista_px']:.0f} px "
                       f"(alvo {TARGET_PX[z]}) · aldeão {info['jogo'][z]['aldeao_px']:.0f}"), font) for z in ZOOMS]
    row2.append(ortho("regioes_frente", "regiões, frente"))
    row3 = [ortho("regioes_lado", "regiões, lado"), ortho("regioes_costas", "regiões, costas")]

    tri = info["triangulos"]
    order = ["cabeca", "tronco", "bracos", "maos", "quadril", "roupa_intima", "coxas", "canelas", "pes"]
    rough = clean["rosto_calombos"]
    lines = [
        br(f"altura {info['altura_m']:.3f} m · {info['triangulos_total']:,} triângulos (limite 2,500)"),
        br(f"cabeça ÷ altura {100 * clean['cabeca_sobre_altura']:.2f}% (conta) · {100 * head_sil:.1f}% (silhueta)"),
        br(f"cabeça × {clean['cabeca']['fator']:.3f} a partir da base do pescoço; corpo × {clean['cabeca']['escala_do_corpo_k']:.3f}"),
        br(f"frente da cabeça (janela ±45°): calombos RMS {rough['rms_mm']} mm, máx {rough['max_mm']} mm"),
        "triângulos por região:",
    ] + [f"   {r}: {tri.get(r, 0)}" + ("  (tecido)" if r == "roupa_intima" else "") for r in order] + [
        "sem rig e sem rosto; ergonomia.json sai depois do rig",
    ]
    legend = Image.new("RGB", (2 * TILE, TILE + 28), PAPER)
    d = ImageDraw.Draw(legend)
    for i, line in enumerate(lines):
        d.text((12, 8 + i * 25), line, fill=INK, font=font)
    colors = info["cores_regioes"]
    for i, r in enumerate(order):
        y = 8 + (5 + i) * 25
        d.rectangle([2 * TILE - 170, y + 2, 2 * TILE - 150, y + 20], fill=colors[r])
        d.text((2 * TILE - 142, y), r, fill=INK, font=font)
    row3.append(legend)

    rows = [row1, row2, row3]
    header = 76
    height = header + sum(r[0].height for r in rows)
    sheet = Image.new("RGB", (4 * TILE, height), PAPER)
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), "Protagonista v2 — corpo limpo (B, cabeça 18%, 0,80 m), sem rig e sem rosto", fill=INK, font=title_font)
    d.text((10, 44), "toon chapado (pele #91ADB7, tecido #3F3342), luz fraca e fria de cima; aldeão v2 (0,40 m) ao lado; "
                     "câmera do jogo 55°, FOV 45°, 16 m ÷ zoom, recortes 1:1 de 3024×1890", fill=INK, font=font)
    y = header
    for row in rows:
        x = 0
        for t in row:
            sheet.paste(t, (x, y))
            x += t.width
        y += row[0].height
    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT / "corpo_limpo.png")
    ImageChops.multiply(sheet, Image.new("RGB", sheet.size, TWILIGHT)).save(OUT / "corpo_limpo_crepusculo.png")
    report = {"render": info, "cabeca_silhueta_sobre_altura": round(float(head_sil), 4), "limpeza": clean}
    (OUT / "corpo_limpo.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"cabeca_silhueta": round(float(head_sil), 4), "px": {z: info["jogo"][z]["protagonista_px"] for z in ZOOMS}}))


if __name__ == "__main__":
    main()

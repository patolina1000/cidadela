"""Estudo de proporção da cabeça da protagonista (só prévia, 0 crédito). Duas etapas, em volta do Blender:

  marcos: mede no bruto B (máscara de frente do render_meshy.py, 0,80 m, quadro de 0,88 m em 1024 px centrado em
          z = 0,40) topo, queixo (head_profile do conferir_recortes.py), pescoço mais fino e base do pescoço (1ª linha
          abaixo do mais fino com largura ≥ 1,25× a dele), e monta a lista de frações a estudar: atual, 18%, a da v1
          (medir_cabeca_v1.py) e 22%.
  folha:  monta assets/previews/protagonista_v2/estudo_cabeca.png (+ _crepusculo e .json) dos renders do
          render_estudo_cabeca.py: uma fileira por variação, frente e câmera do jogo 1:1 nos três zooms, e a v1.

Uso (em tools/arte):
  uv run protagonista_v2/estudo_cabeca.py marcos <mascara_b.png> <cabeca_v1.json> <marcos.json>
  uv run protagonista_v2/estudo_cabeca.py folha <pasta_renders> <cabeca_v1.json>
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conferir_recortes import central_run, head_profile  # noqa: E402
from folha_meshy import BG, FONT, INK, PAPER, TARGET_PX, TWILIGHT, br, game_tile, labeled, on_bg  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/protagonista_v2"
MASK_ORTHO, MASK_CENTER_Z, MASK_RES = 0.88, 0.40, 1024  # render_meshy.py
ZOOMS = ("0.4", "1.0", "2.5")
TILE = 400


def marcos(mask_path: Path, v1_path: Path, out: Path) -> None:
    a = np.array(Image.open(mask_path).convert("RGBA"))[:, :, 3] > 127
    p = head_profile(a, None, head_frac=0.18)
    neck_w = p["pescoco_largura"]
    y = p["pescoco_y"]
    while True:
        r = central_run(a[y], p["cx"])
        if r[1] - r[0] >= 1.25 * neck_w:
            break
        y += 1
    z = lambda row: MASK_CENTER_Z + (MASK_RES / 2 - (row + 0.5)) * MASK_ORTHO / MASK_RES  # noqa: E731
    v1 = json.loads(v1_path.read_text())["v1"]["cabeca_sobre_altura"]
    top, chin = z(p["topo"] - 0.5), z(p["queixo_y"])
    marks = {"topo_z": round(top, 4), "queixo_z": round(chin, 4), "pescoco_z": round(z(p["pescoco_y"]), 4),
             "base_pescoco_z": round(z(y), 4), "cabeca_sobre_altura": round((top - chin) / 0.80, 3),
             "fracoes": [None, 0.18, v1, 0.22], "fracao_v1": v1}
    out.write_text(json.dumps(marks, indent=2) + "\n")
    print(json.dumps(marks))


def folha(renders: Path, v1_path: Path) -> None:
    data = json.loads((renders / "estudo_render.json").read_text())
    heads = json.loads(v1_path.read_text())
    font = ImageFont.truetype(FONT, 17)
    title_font = ImageFont.truetype(FONT, 24)
    v1_ratio = data["marcos"]["fracao_v1"]

    def row_for(name: str, info: dict, label: str):
        tiles = [labeled(on_bg(Image.open(renders / f"{name}_frente.png")).resize((TILE, TILE), Image.LANCZOS),
                         "frente (mesma escala em todas)", font)]
        for z in ZOOMS:
            j = info["jogo"][z]
            tiles.append(labeled(game_tile(renders / f"{name}_jogo_{z}.png", j["caixa_px"]),
                                 br(f"zoom {z.rstrip('0').rstrip('.')} (1:1): {j['protagonista_px']:.0f} px "
                                    f"(alvo {TARGET_PX[z]}) · aldeão {j['aldeao_px']:.0f}"), font))
        return tiles, label

    rows = []
    for name, info in data["variacoes"].items():
        r = info["fracao_pedida"]
        what = ("atual (bruto B)" if r is None else
                "v1" if r == v1_ratio else f"{round(100 * r)}%")
        label = br(f"cabeça {what}: {100 * info['cabeca_sobre_altura']:.1f}% da altura · altura {info['altura_m']:.2f} m"
                   f"{' (contrato)' if info['altura_pedida'] == 0.8 else ' (alvo 179 px)'} · fator da cabeça "
                   f"{info['fator_cabeca']:.2f}× · cabeça {100 * info['cabeca_m']:.1f} cm")
        rows.append(row_for(name, info, label))
    v1 = data["v1"]
    rows.append(row_for("v1", v1, br(f"REFERÊNCIA v1 como estava no jogo (textura, pose T): {v1['altura_m']:.2f} m, "
                                     f"cabeça {100 * heads['v1']['cabeca_sobre_altura']:.1f}% da altura "
                                     f"(topo do cabelo ao queixo)")))

    width = TILE * 4
    row_h = TILE + 28 + 30
    title = [
        "Protagonista v2 — estudo de proporção da cabeça sobre o bruto B (só prévia; nenhum GLB salvo)",
        br(f"cabeça = topo ao queixo ÷ altura. v1 {100 * heads['v1']['cabeca_sobre_altura']:.1f}% · aldeão v2 "
           f"{100 * heads['aldeao']['cabeca_sobre_altura']:.1f}% · bruto B {100 * data['marcos']['cabeca_sobre_altura']:.1f}%. "
           "Cabeça escalada a partir da base do pescoço; aldeão v2 (0,40 m) sempre ao lado."),
        br(f"v1 e bruto B têm os dois 0,80 m, mas na câmera do jogo a v1 dá {v1['jogo']['2.5']['protagonista_px']:.0f} px "
           f"e o B {data['variacoes']['cabeca_atual_80']['jogo']['2.5']['protagonista_px']:.0f} px no zoom 2,5: a câmera a 55° "
           "soma profundidade;"),
        "a cabeça da v1 pende para a frente e os pés do B avançam. O alvo de 179 px é a pose da v1 a 0,80 m, não outra altura.",
    ]
    sheet = Image.new("RGB", (width, 128 + row_h * len(rows)), PAPER)
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), title[0], fill=INK, font=title_font)
    for i, line in enumerate(title[1:]):
        d.text((10, 46 + 24 * i), line, fill=INK, font=font)
    y = 128
    for tiles, label in rows:
        d.text((10, y + 6), label, fill=INK, font=font)
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * TILE, y + 30))
        y += row_h
    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT / "estudo_cabeca.png")
    ImageChops.multiply(sheet, Image.new("RGB", sheet.size, TWILIGHT)).save(OUT / "estudo_cabeca_crepusculo.png")
    report = {"medidas_cabeca": heads, "marcos_bruto_b": data["marcos"], "variacoes": data["variacoes"], "v1": v1}
    (OUT / "estudo_cabeca.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    for name, info in list(data["variacoes"].items()) + [("v1", v1)]:
        print(name, info.get("cabeca_sobre_altura"), {z: info["jogo"][z]["protagonista_px"] for z in ZOOMS})


if __name__ == "__main__":
    if sys.argv[1] == "marcos":
        marcos(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        folha(Path(sys.argv[2]), Path(sys.argv[3]))

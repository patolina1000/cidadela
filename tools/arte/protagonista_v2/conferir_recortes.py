"""Folha de conferência dos recortes da protagonista v2 (vistas do preparar_vistas.py, mesma escala por folha).
Mede e desenha:
- corpo (frente, perfil esquerdo, costas): altura; pescoço (linha mais estreita entre 10% e 35% da altura);
  largura dos ombros na frente e nas costas (maior largura da faixa central entre 3% e 8% da altura abaixo do
  pescoço); pés (faixa de baixo, 4% da altura): na frente e nas costas, a distância entre os centros dos dois pés e
  a largura de cada um; no perfil, o comprimento do pé e o calcanhar em relação ao eixo da cabeça;
- rosto (frente do corpo e frente do busto dos chifres): variação de tom na área do rosto (elipse no meio da
  cabeça): desvio do tom em relação a um ajuste quadrático (o sombreado suave sai) e o máximo de um passa-alta
  (tom − desfoque gaussiano de 5 px), em níveis de 0 a 255;
- chifres (frente, perfil, costas, topo): caixa de cada chifre (pixels escuros), altura e posição em relação à
  cabeça, e as medidas que precisam bater entre vistas (altura do chifre esquerdo dela na frente, nas costas e no
  perfil; distância entre os chifres na frente, nas costas e no topo; comprimento de frente para trás no perfil e no
  topo).
Diferenças em % da média das duas medidas.

Uso: uv run protagonista_v2/conferir_recortes.py   (a partir de tools/arte)
Saída: assets/previews/protagonista_v2/recortes.png e recortes.json
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
VIEWS = ROOT / "assets/conceitos/protagonista_v2/vistas"
OUT = ROOT / "assets/previews/protagonista_v2"
BG = np.array([235, 235, 235])  # fundo do preparar_vistas.py
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
HORN_LUM = 115  # chifre: pixels bem mais escuros que a pele (a pele na sombra fica acima de ~140)


def load(name):
    rgb = np.asarray(Image.open(VIEWS / f"{name}.png").convert("RGB")).astype(float)
    mask = np.abs(rgb - BG).max(axis=2) > 6
    mask = ndimage.binary_opening(mask, iterations=1)
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    return rgb, mask, lum


def bbox(mask):
    ys, xs = np.nonzero(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def central_run(row: np.ndarray, x: int):
    """(início, fim) do trecho contínuo da linha que contém x (ou o mais perto dele)."""
    xs = np.nonzero(row)[0]
    if not len(xs):
        return None
    if not row[x]:
        x = int(xs[np.abs(xs - x).argmin()])
    a = x
    while a > 0 and row[a - 1]:
        a -= 1
    b = x
    while b < len(row) - 1 and row[b + 1]:
        b += 1
    return a, b + 1


def pct(a, b):
    return round(abs(a - b) / ((a + b) / 2) * 100, 1)


def body(name):
    rgb, mask, lum = load(name)
    x0, y0, x1, y1 = bbox(mask)
    h = y1 - y0
    top = mask[y0:y0 + int(0.08 * h)]
    head_cx = int(np.nonzero(top)[1].mean())
    widths = {}
    for y in range(y0 + int(0.10 * h), y0 + int(0.35 * h)):
        r = central_run(mask[y], head_cx)
        if r:
            widths[y] = r[1] - r[0]
    neck = min(widths, key=widths.get)
    sh = None
    for y in range(neck + int(0.03 * h), neck + int(0.08 * h)):
        r = central_run(mask[y], head_cx)
        if r and (sh is None or r[1] - r[0] > sh[2] - sh[1]):
            sh = (y, r[0], r[1])
    band = mask[y1 - int(0.04 * h):y1]
    labels, n = ndimage.label(band)
    feet = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(labels == i)
        if len(xs) > 30:
            feet.append((int(xs.min()), int(xs.max()) + 1, float(xs.mean())))
    feet.sort()
    return {"altura_px": h, "largura_px": x1 - x0, "caixa": [x0, y0, x1, y1], "eixo_cabeca_x": head_cx,
            "pescoco_y": neck, "pescoco_largura_px": widths[neck], "cabeca_altura_px": neck - y0,
            "ombros": {"y": sh[0], "x0": sh[1], "x1": sh[2], "largura_px": sh[2] - sh[1]}, "pes": feet}


def face(name, head_top, neck, head_cx):
    rgb, mask, lum = load(name)
    hh = neck - head_top
    row = mask[head_top + hh // 2]
    run = central_run(row, head_cx)
    hw = run[1] - run[0]
    cy, cx = head_top + 0.55 * hh, (run[0] + run[1]) / 2
    yy, xx = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]
    zone = (((xx - cx) / (0.30 * hw)) ** 2 + ((yy - cy) / (0.28 * hh)) ** 2 <= 1) & ndimage.binary_erosion(mask, iterations=4)
    ys, xs = np.nonzero(zone)
    v = lum[ys, xs]
    A = np.c_[np.ones(len(xs)), xs, ys, xs * xs, xs * ys, ys * ys]
    coef, *_ = np.linalg.lstsq(A, v, rcond=None)
    resid = v - A @ coef
    hp = lum - ndimage.gaussian_filter(lum, 5)
    head = mask[head_top:neck]
    hys, hxs = np.nonzero(head)
    return {"cabeca_largura_px": int(hxs.max() - hxs.min() + 1), "cabeca_altura_px": int(hh),
            "cabeca_largura_sobre_altura": round(float((hxs.max() - hxs.min() + 1) / hh), 3), "pixels": int(zone.sum()), "tom_medio": round(float(v.mean()), 1), "tom_p5_p95": [round(float(np.percentile(v, 5)), 1), round(float(np.percentile(v, 95)), 1)],
            "residuo_quadratico_dp": round(float(resid.std()), 2), "residuo_quadratico_max": round(float(np.abs(resid).max()), 1),
            "passa_alta_dp": round(float(hp[zone].std()), 2), "passa_alta_max": round(float(np.abs(hp[zone]).max()), 1),
            "_zona": (cx, cy, 0.30 * hw, 0.28 * hh), "_hp": hp, "_mask": zone}


def horns(name, count):
    rgb, mask, lum = load(name)
    dark = mask & (lum < HORN_LUM)
    dark = ndimage.binary_opening(dark, iterations=1)
    labels, n = ndimage.label(dark)
    sizes = ndimage.sum(dark, labels, range(1, n + 1))
    keep = sorted(range(1, n + 1), key=lambda i: -sizes[i - 1])[:count]
    out = []
    for i in keep:
        ys, xs = np.nonzero(labels == i)
        out.append({"caixa": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], "centro": [round(float(xs.mean()), 1), round(float(ys.mean()), 1)],
                    "altura_px": int(ys.max() - ys.min() + 1), "largura_px": int(xs.max() - xs.min() + 1), "pixels": int(len(xs))})
    out.sort(key=lambda hbox: hbox["centro"][0])
    skin = mask & ~dark
    return out, bbox(skin), skin


HAIR_LUM = 125  # cabelo azul-acinzentado escuro (~80 de tom); a pele na sombra fica acima de ~140


def dark_and_skin(name, lum_max, strict=False):
    """Máscara da figura, do escuro (cabelo ou chifre) e da pele. strict: pele = clara e azulada (B − R > 12 e
    tom > 140), para a borda da silhueta do cabelo, onde o escuro se mistura com o fundo cinza, não contar como pele
    (só no cabelo; nas cabeças carecas isso cortaria o sombreado da borda)."""
    rgb, mask, lum = load(name)
    dark = ndimage.binary_opening(mask & (lum < lum_max), iterations=1)
    skin = mask & ~dark
    if strict:
        skin = ndimage.binary_opening(skin & (rgb[:, :, 2] - rgb[:, :, 0] > 12) & (lum > 140), iterations=1)
    return mask, dark, skin


def neck_row(skin, cx, y0, y1):
    """Linha mais estreita do trecho central da pele entre y0 e y1 (o pescoço)."""
    wid = {}
    for y in range(y0, y1):
        r = central_run(skin[y], cx)
        if r:
            wid[y] = r[1] - r[0]
    return min(wid, key=wid.get)


def head_profile(skin, dark, head_frac=0.6, top=None):
    """Perfil da cabeça na vista de frente: meia-largura do trecho central da pele por linha, do topo da pele até o
    busto; linha mais larga; pescoço (menor largura abaixo dela, até 1,5 largura máxima para baixo); queixo = primeira
    linha abaixo da mais larga em que a largura cai abaixo de pescoço + 30% da diferença (a curva do queixo encontra o
    pescoço). Marca, por linha, se as duas bordas encostam em cabelo (até 3 px para fora)."""
    sx0, sy0, sx1, sy1 = bbox(skin)
    if top is not None:  # topo da pele estrita: a borda misturada do escuro com o fundo não é pele
        sy0 = top
    cx = int(np.nonzero(skin[sy0:sy0 + max(3, (sy1 - sy0) // 30)])[1].mean())
    rows = {}
    for y in range(sy0, sy1):
        r = central_run(skin[y], cx)
        if r:
            hair_l = dark is not None and dark[y, max(0, r[0] - 3):r[0]].any()
            hair_r = dark is not None and dark[y, r[1]:r[1] + 3].any()
            rows[y] = (r[0], r[1], hair_l and hair_r)
    widths = {y: r[1] - r[0] for y, r in rows.items()}
    upper = [y for y in widths if y < sy0 + (sy1 - sy0) * head_frac]  # a cabeça fica nesse alto da figura
    widest = max(upper, key=widths.get)
    wmax = widths[widest]
    below = [y for y in widths if widest < y <= widest + 1.5 * wmax]
    neck = min(below, key=widths.get)
    cut = widths[neck] + 0.3 * (wmax - widths[neck])
    chin = next(y for y in sorted(below) if widths[y] < cut)
    return {"topo": sy0, "mais_larga_y": widest, "largura_max": wmax, "pescoco_y": neck, "pescoco_largura": widths[neck],
            "queixo_y": chin, "cx": cx, "_rows": rows}


def sheet_boxes(sheet: str) -> list:
    """Caixas das figuras na folha original (mesmo método e limiar do preparar_vistas), em ordem de leitura."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aldeao_v2"))
    from preparar_vistas import figures
    rgb = np.asarray(Image.open(ROOT / f"assets/conceitos/protagonista_v2/folhas/{sheet}.png").convert("RGB"))
    return [box for _, box in figures(rgb, 8)]


def to_sheet_y(view_mask, sheet_box, y):
    """Linha do quadro de 1024 → linha da folha original (o preparador centraliza cada vista no seu quadro)."""
    x0, y0, x1, y1 = bbox(view_mask)
    scale = (y1 - y0) / (sheet_box[3] - sheet_box[1])
    return sheet_box[1] + (y - y0) / scale


def hair_view(name):
    mask, dark, skin = dark_and_skin(name, HAIR_LUM)
    hx0, hy0, hx1, hy1 = bbox(dark)
    out = {"cabelo_caixa": [hx0, hy0, hx1, hy1], "cabelo_largura_px": hx1 - hx0, "cabelo_altura_px": hy1 - hy0}
    if skin.any():
        out["pele_caixa"] = list(bbox(skin))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {"corpo": {v: body(f"corpo_{v}") for v in ("frente", "lado", "costas")}}
    c = rep["corpo"]
    hs = [c[v]["altura_px"] for v in c]
    fr, bk, sd = c["frente"], c["costas"], c["lado"]
    fsep = abs(fr["pes"][1][2] - fr["pes"][0][2]) if len(fr["pes"]) == 2 else None
    bsep = abs(bk["pes"][1][2] - bk["pes"][0][2]) if len(bk["pes"]) == 2 else None
    side_foot = sd["pes"][0] if sd["pes"] else None
    rep["corpo_comparacao"] = {
        "altura_px": dict(zip(c, hs)), "altura_dif_max_pct": pct(max(hs), min(hs)),
        "cabeca_altura_px": {v: c[v]["cabeca_altura_px"] for v in c},
        "ombros_frente_costas_px": [fr["ombros"]["largura_px"], bk["ombros"]["largura_px"]],
        "ombros_dif_pct": pct(fr["ombros"]["largura_px"], bk["ombros"]["largura_px"]),
        "pes_distancia_centros_px": [round(fsep, 1), round(bsep, 1)], "pes_distancia_dif_pct": pct(fsep, bsep),
        "pes_distancia_pct_altura": [round(fsep / fr["altura_px"] * 100, 1), round(bsep / bk["altura_px"] * 100, 1)],
        "pes_largura_px": {"frente": [f[1] - f[0] for f in fr["pes"]], "costas": [f[1] - f[0] for f in bk["pes"]]},
        "pe_perfil": {"comprimento_px": side_foot[1] - side_foot[0], "comprimento_pct_altura": round((side_foot[1] - side_foot[0]) / sd["altura_px"] * 100, 1),
                      "calcanhar_atras_do_eixo_da_cabeca_pct_altura": round((side_foot[1] - sd["eixo_cabeca_x"]) / sd["altura_px"] * 100, 1),
                      "ponta_a_frente_do_eixo_da_cabeca_pct_altura": round((sd["eixo_cabeca_x"] - side_foot[0]) / sd["altura_px"] * 100, 1)},
    }
    faces = {"corpo_frente": face("corpo_frente", fr["caixa"][1], fr["pescoco_y"], fr["eixo_cabeca_x"])}
    hb = {}
    for v, n in (("frente", 2), ("lado", 1), ("costas", 2), ("topo", 2)):
        hb[v] = horns(f"chifres_{v}", n)
    # rosto do busto: cabeça = pele acima do pescoço (linha mais estreita da metade de baixo da pele)
    _, (sx0, sy0, sx1, sy1), skin = hb["frente"]
    cx = (sx0 + sx1) // 2
    wid = {y: (lambda r: r[1] - r[0] if r else 9999)(central_run(skin[y], cx)) for y in range(sy0 + (sy1 - sy0) // 3, sy1 - (sy1 - sy0) // 6)}
    bneck = min(wid, key=wid.get)
    faces["chifres_frente"] = face("chifres_frente", sy0, bneck, cx)
    rep["rosto"] = {k: {a: b for a, b in v.items() if not a.startswith("_")} for k, v in faces.items()}

    f, s, b, t = (hb[v][0] for v in ("frente", "lado", "costas", "topo"))
    # Frente: a esquerda dela fica à direita da imagem; costas: à esquerda; perfil esquerdo: o chifre visível é o esquerdo.
    left_front, right_front = f[1], f[0]
    left_back, right_back = b[0], b[1]
    side = s[0]
    rep["chifres"] = {v: hb[v][0] for v in hb}
    rep["chifres_comparacao"] = {
        "altura_esquerdo_frente_costas_perfil_px": [left_front["altura_px"], left_back["altura_px"], side["altura_px"]],
        "altura_direito_frente_costas_px": [right_front["altura_px"], right_back["altura_px"]],
        "altura_esquerdo_frente_x_costas_dif_pct": pct(left_front["altura_px"], left_back["altura_px"]),
        "altura_direito_frente_x_costas_dif_pct": pct(right_front["altura_px"], right_back["altura_px"]),
        "altura_esquerdo_frente_x_perfil_dif_pct": pct(left_front["altura_px"], side["altura_px"]),
        "esquerdo_x_direito_na_frente_altura_dif_pct": pct(left_front["altura_px"], right_front["altura_px"]),
        "distancia_entre_centros_px": {"frente": round(abs(f[1]["centro"][0] - f[0]["centro"][0]), 1), "costas": round(abs(b[1]["centro"][0] - b[0]["centro"][0]), 1),
                                       "topo": round(abs(t[1]["centro"][0] - t[0]["centro"][0]), 1)},
        "frente_para_tras_px": {"perfil": side["largura_px"], "topo": [t[0]["altura_px"], t[1]["altura_px"]]},
    }
    cc = rep["chifres_comparacao"]
    cc["distancia_frente_x_topo_dif_pct"] = pct(cc["distancia_entre_centros_px"]["frente"], cc["distancia_entre_centros_px"]["topo"])
    cc["frente_para_tras_perfil_x_topo_dif_pct"] = pct(side["largura_px"], max(t[0]["altura_px"], t[1]["altura_px"]))
    # Cabelo
    rep["cabelo"] = {v: hair_view(f"cabelo_{v}") for v in ("frente", "lado", "costas", "topo")}
    hv = rep["cabelo"]
    # Posições na folha original (as vistas dividem escala e chão lá); tamanhos no quadro de 1024.
    boxes = dict(zip(("frente", "lado", "costas", "topo"), sheet_boxes("cabelo")))
    fig = {v: load(f"cabelo_{v}")[1] for v in boxes}
    sheet_y = {v: (lambda yy, v=v: round(float(to_sheet_y(fig[v], boxes[v], yy)), 1)) for v in boxes}
    scale_1024 = (bbox(fig["frente"])[3] - bbox(fig["frente"])[1]) / (boxes["frente"][3] - boxes["frente"][1])
    rep["cabelo_comparacao"] = {
        "nota": "posições (y) em px da folha original; tamanhos em px do quadro de 1024 (escala folha→quadro "
                f"{round(scale_1024, 3)})",
        "topo_do_cabelo_y_folha": {v: sheet_y[v](hv[v]["cabelo_caixa"][1]) for v in ("frente", "lado", "costas")},
        "fundo_do_cabelo_y_folha": {"lado": sheet_y["lado"](hv["lado"]["cabelo_caixa"][3]), "costas": sheet_y["costas"](hv["costas"]["cabelo_caixa"][3]),
                                    "frente_visivel": sheet_y["frente"](hv["frente"]["cabelo_caixa"][3])},
        "comprimento_lado_x_costas_dif_pct": pct(hv["lado"]["cabelo_caixa"][3] - hv["lado"]["cabelo_caixa"][1],
                                                 hv["costas"]["cabelo_caixa"][3] - hv["costas"]["cabelo_caixa"][1]),
        "largura_px": {"frente": hv["frente"]["cabelo_largura_px"], "costas": hv["costas"]["cabelo_largura_px"], "topo": hv["topo"]["cabelo_largura_px"]},
        "largura_frente_x_costas_dif_pct": pct(hv["frente"]["cabelo_largura_px"], hv["costas"]["cabelo_largura_px"]),
        "largura_costas_x_topo_dif_pct": pct(hv["costas"]["cabelo_largura_px"], hv["topo"]["cabelo_largura_px"]),
        "frente_para_tras_px": {"lado": hv["lado"]["cabelo_largura_px"], "topo": hv["topo"]["cabelo_altura_px"]},
        "frente_para_tras_lado_x_topo_dif_pct": pct(hv["lado"]["cabelo_largura_px"], hv["topo"]["cabelo_altura_px"]),
    }
    # Proporção da cabeça nas três folhas (vista de frente): largura máxima ÷ (topo ao queixo). Nas carecas é direta;
    # no cabelo o alto está coberto: o perfil da cabeça do corpo é ajustado às bordas visíveis (queixo fixo, só a
    # altura livre). O mesmo ajuste nos chifres (careca) mostra o erro do método.
    profs = {"corpo": head_profile(load("corpo_frente")[1], None, head_frac=0.18)}
    for sheet_name, lum_max in (("chifres", HORN_LUM), ("cabelo", HAIR_LUM)):
        mask, dark, skin = dark_and_skin(f"{sheet_name}_frente", lum_max)
        strict = dark_and_skin(f"{sheet_name}_frente", lum_max, strict=True)[2]
        profs[sheet_name] = head_profile(skin, dark, top=bbox(strict)[1])
        profs[sheet_name]["_skin"] = skin
    heads = {}
    for k, pr in profs.items():
        h = pr["queixo_y"] - pr["topo"]
        entry = {x: pr[x] for x in ("topo", "mais_larga_y", "largura_max", "pescoco_y", "queixo_y")}
        entry["_cx"] = pr["cx"]
        if k == "cabelo":
            hair_top = rep["cabelo"]["frente"]["cabelo_caixa"][1]
            entry["topo_e_a_linha_do_cabelo"] = True
            entry["topo_do_cabelo_y"] = hair_top
            entry["rosto_visivel_largura_sobre_altura"] = round(pr["largura_max"] / h, 3)
            entry["ate_o_topo_do_cabelo_largura_sobre_altura"] = round(pr["largura_max"] / (pr["queixo_y"] - hair_top), 3)
        else:
            entry["largura_sobre_altura"] = round(pr["largura_max"] / h, 3)
        heads[k] = entry
    rep["cabeca_proporcao"] = heads
    cc2 = rep["cabelo_comparacao"]
    cc2["queixo_frente_y_folha"] = sheet_y["frente"](heads["cabelo"]["queixo_y"])
    tops = cc2["topo_do_cabelo_y_folha"]
    cc2["topo_do_cabelo_dif_max_px_folha"] = round(max(tops.values()) - min(tops.values()), 1)
    head_h_sheet = cc2["queixo_frente_y_folha"] - tops["frente"]
    cc2["topo_do_cabelo_dif_max_pct_da_cabeca"] = round(cc2["topo_do_cabelo_dif_max_px_folha"] / head_h_sheet * 100, 1)
    fb = cc2["fundo_do_cabelo_y_folha"]
    cc2["fundo_lado_x_costas_px_folha"] = round(abs(fb["lado"] - fb["costas"]), 1)
    clean = json.loads(json.dumps({k: v for k, v in rep.items()}, default=lambda o: None))
    for v in clean["cabeca_proporcao"].values():
        v.pop("_cx", None)
    (OUT / "recortes.json").write_text(json.dumps(clean, indent=2, ensure_ascii=False) + "\n")
    sheet(rep, faces)
    print(json.dumps({k: rep[k] for k in ("cabelo_comparacao", "cabeca_proporcao")}, indent=1, ensure_ascii=False))


def tile(name, draw_fn, scale):
    im = Image.open(VIEWS / f"{name}.png").convert("RGB")
    d = ImageDraw.Draw(im)
    draw_fn(d)
    return im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)


def sheet(rep, faces):
    font, small, big = ImageFont.truetype(FONT, 17), ImageFont.truetype(FONT, 14), ImageFont.truetype(FONT, 22)
    S = 0.5
    c = rep["corpo"]
    body_tiles = []
    for v in ("frente", "lado", "costas"):
        m = c[v]

        def draw(d, m=m):
            x0, y0, x1, y1 = m["caixa"]
            for y, col in ((y0, (200, 60, 60)), (m["pescoco_y"], (60, 120, 200)), (m["ombros"]["y"], (60, 160, 60)), (y1, (200, 60, 60))):
                d.line([(0, y), (1024, y)], fill=col, width=2)
            if v != "lado":
                d.line([(m["ombros"]["x0"], m["ombros"]["y"] - 12), (m["ombros"]["x0"], m["ombros"]["y"] + 12)], fill=(60, 160, 60), width=4)
                d.line([(m["ombros"]["x1"], m["ombros"]["y"] - 12), (m["ombros"]["x1"], m["ombros"]["y"] + 12)], fill=(60, 160, 60), width=4)
            for fx0, fx1, fc in m["pes"]:
                d.rectangle([fx0, y1 - int(0.04 * (y1 - y0)), fx1, y1], outline=(200, 120, 40), width=3)
            d.line([(m["eixo_cabeca_x"], y0), (m["eixo_cabeca_x"], y1)], fill=(150, 150, 150), width=1)
            if v == "frente":
                hc_ = rep["cabeca_proporcao"]["corpo"]
                d.line([(m["eixo_cabeca_x"] - 90, hc_["queixo_y"]), (m["eixo_cabeca_x"] + 90, hc_["queixo_y"])], fill=(200, 60, 200), width=3)
        body_tiles.append((v, m, tile(f"corpo_{v}", draw, S)))
    horn_tiles = []
    for v in ("frente", "lado", "costas", "topo"):
        def draw(d, v=v):
            for hbx in rep["chifres"][v]:
                d.rectangle(hbx["caixa"], outline=(220, 60, 60), width=3)
            if v == "frente":
                hc_ = rep["cabeca_proporcao"]["chifres"]
                for yy, col in ((hc_["topo"], (60, 160, 60)), (hc_["queixo_y"], (60, 120, 200))):
                    d.line([(250, yy), (774, yy)], fill=col, width=3)
                d.line([(hc_["_cx"] - hc_["largura_max"] // 2, hc_["mais_larga_y"]), (hc_["_cx"] + hc_["largura_max"] // 2, hc_["mais_larga_y"])], fill=(60, 160, 60), width=3)
        horn_tiles.append((v, tile(f"chifres_{v}", draw, 0.36)))
    hair_tiles = []
    for v in ("frente", "lado", "costas", "topo"):
        def draw(d, v=v):
            d.rectangle(rep["cabelo"][v]["cabelo_caixa"], outline=(220, 60, 60), width=3)
            if v == "frente":
                hc_ = rep["cabeca_proporcao"]["cabelo"]
                for yy, col in ((hc_["topo_do_cabelo_y"], (200, 60, 200)), (hc_["topo"], (60, 160, 60)), (hc_["queixo_y"], (60, 120, 200))):
                    d.line([(300, yy), (724, yy)], fill=col, width=3)
                d.line([(512 - hc_["largura_max"] // 2, hc_["mais_larga_y"]), (512 + hc_["largura_max"] // 2, hc_["mais_larga_y"])], fill=(60, 160, 60), width=3)
        hair_tiles.append((v, tile(f"cabelo_{v}", draw, 0.36)))
    face_tiles = []
    for k, fz in faces.items():
        name = k
        im = Image.open(VIEWS / f"{name}.png").convert("RGB")
        cx, cy, rx, ry = fz["_zona"]
        half = int(max(rx, ry) * 2.3)  # quadrado em volta da cabeça inteira
        box = (int(cx - half), int(cy - half * 1.1), int(cx + half), int(cy + half * 0.9))
        crop = im.crop(box)
        hp = np.clip(np.abs(fz["_hp"]) * 40, 0, 255).astype(np.uint8)  # 1 nível de tom = 40 no mapa
        heat = Image.fromarray(np.dstack([hp, hp // 3, 255 - hp]), "RGB").crop(box)
        zm = Image.fromarray((fz["_mask"] * 255).astype(np.uint8)).crop(box)
        heat = Image.composite(heat, Image.new("RGB", heat.size, (40, 40, 40)), zm)
        size = (280, round(280 * crop.height / crop.width))
        face_tiles.append((k, crop.resize(size, Image.LANCZOS), heat.resize(size, Image.NEAREST)))

    W = 1560
    Hs = 60 + max(t.height for _, _, t in body_tiles) + 40 + max(t.height for _, t in horn_tiles) + 40 + max(t.height for _, t in hair_tiles) + 40 + max(ft[1].height for ft in face_tiles) + 60
    out = Image.new("RGB", (W, Hs + 330), (248, 247, 250))
    d = ImageDraw.Draw(out)
    d.text((16, 12), "Protagonista v2 — conferência dos recortes (corpo: 0,5×; chifres: 0,36×; px medidos no quadro de 1024)", fill=(30, 30, 40), font=big)
    x, y = 16, 50
    for v, m, t in body_tiles:
        out.paste(t, (x, y))
        d.text((x + 6, y + 4), f"{v}: {m['altura_px']} px de altura", fill=(30, 30, 40), font=font)
        if v != "lado":
            d.text((x + 6, y + 24), f"ombros {m['ombros']['largura_px']} px", fill=(60, 140, 60), font=small)
        x += t.width + 10
    cc = rep["corpo_comparacao"]
    lines = [
        "CORPO",
        f"altura: {cc['altura_px']['frente']} / {cc['altura_px']['lado']} / {cc['altura_px']['costas']} px (frente/lado/costas), dif. máx {cc['altura_dif_max_pct']}%",
        f"cabeça (topo ao pescoço): {cc['cabeca_altura_px']['frente']} / {cc['cabeca_altura_px']['lado']} / {cc['cabeca_altura_px']['costas']} px",
        f"ombros: {cc['ombros_frente_costas_px'][0]} / {cc['ombros_frente_costas_px'][1]} px (frente/costas), dif. {cc['ombros_dif_pct']}%",
        f"pés, distância entre centros: {cc['pes_distancia_centros_px'][0]} / {cc['pes_distancia_centros_px'][1]} px, dif. {cc['pes_distancia_dif_pct']}%",
        f"pés, largura: frente {cc['pes_largura_px']['frente']}, costas {cc['pes_largura_px']['costas']} px",
        f"pé no perfil: {cc['pe_perfil']['comprimento_px']} px ({cc['pe_perfil']['comprimento_pct_altura']}% da altura); "
        f"calcanhar {cc['pe_perfil']['calcanhar_atras_do_eixo_da_cabeca_pct_altura']}% atrás do eixo da cabeça",
        "linhas: vermelho topo/pés, azul pescoço, verde ombros; laranja: pés",
    ]
    tx = x + 10
    for i, line in enumerate(lines):
        d.text((tx, y + 6 + i * 22), line, fill=(30, 30, 40) if i else (120, 40, 40), font=small if i else font)
    y += max(t.height for _, _, t in body_tiles) + 40
    x = 16
    for v, t in horn_tiles:
        out.paste(t, (x, y))
        d.text((x + 6, y + 4), f"chifres {v}", fill=(30, 30, 40), font=font)
        x += t.width + 10
    y += max(t.height for _, t in horn_tiles) + 40
    x = 16
    for v, t in hair_tiles:
        out.paste(t, (x, y))
        d.text((x + 6, y + 4), f"cabelo {v}", fill=(30, 30, 40), font=font)
        x += t.width + 10
    y += max(t.height for _, t in hair_tiles) + 40
    x = 16
    for k, crop, heat in face_tiles:
        out.paste(crop, (x, y))
        out.paste(heat, (x + crop.width + 6, y))
        r = rep["rosto"][k]
        d.text((x, y - 20), f"rosto ({k}): resíduo dp {r['residuo_quadratico_dp']}, passa-alta máx {r['passa_alta_max']}", fill=(30, 30, 40), font=small)
        x += crop.width * 2 + 40
    ch = rep["chifres_comparacao"]
    lines = [
        "CHIFRES (esquerdo = o esquerdo dela)",
        f"altura do esquerdo: frente {ch['altura_esquerdo_frente_costas_perfil_px'][0]}, costas {ch['altura_esquerdo_frente_costas_perfil_px'][1]}, "
        f"perfil {ch['altura_esquerdo_frente_costas_perfil_px'][2]} px (frente×costas {ch['altura_esquerdo_frente_x_costas_dif_pct']}%, frente×perfil {ch['altura_esquerdo_frente_x_perfil_dif_pct']}%)",
        f"altura do direito: frente {ch['altura_direito_frente_costas_px'][0]}, costas {ch['altura_direito_frente_costas_px'][1]} px ({ch['altura_direito_frente_x_costas_dif_pct']}%)",
        f"esquerdo × direito na frente: {ch['esquerdo_x_direito_na_frente_altura_dif_pct']}%",
        f"distância entre os centros: frente {ch['distancia_entre_centros_px']['frente']}, costas {ch['distancia_entre_centros_px']['costas']}, "
        f"topo {ch['distancia_entre_centros_px']['topo']} px (frente×topo {ch['distancia_frente_x_topo_dif_pct']}%)",
        f"frente para trás: perfil {ch['frente_para_tras_px']['perfil']} px, topo {ch['frente_para_tras_px']['topo']} px ({ch['frente_para_tras_perfil_x_topo_dif_pct']}%)",
        "mapa do rosto: passa-alta (tom − desfoque de 5 px), 1 nível = 40; azul = liso",
    ]
    for i, line in enumerate(lines):
        d.text((16, y + max(ft[1].height for ft in face_tiles) + 20 + i * 22), line, fill=(30, 30, 40) if i else (120, 40, 40), font=small if i else font)
    hc, hp_ = rep["cabelo_comparacao"], rep["cabeca_proporcao"]
    hl = [
        "CABELO",
        f"topo do cabelo na folha: {hc['topo_do_cabelo_y_folha']['frente']} / {hc['topo_do_cabelo_y_folha']['lado']} / {hc['topo_do_cabelo_y_folha']['costas']} px (frente/lado/costas; dif. máx {hc['topo_do_cabelo_dif_max_pct_da_cabeca']}% da cabeça)",
        f"fundo na folha: lado {hc['fundo_do_cabelo_y_folha']['lado']}, costas {hc['fundo_do_cabelo_y_folha']['costas']} px (dif. {hc['fundo_lado_x_costas_px_folha']} px; comprimento {hc['comprimento_lado_x_costas_dif_pct']}%); na frente some atrás do busto em {hc['fundo_do_cabelo_y_folha']['frente_visivel']}",
        f"largura: frente {hc['largura_px']['frente']}, costas {hc['largura_px']['costas']}, topo {hc['largura_px']['topo']} px (frente×costas {hc['largura_frente_x_costas_dif_pct']}%, costas×topo {hc['largura_costas_x_topo_dif_pct']}%)",
        f"frente para trás: lado {hc['frente_para_tras_px']['lado']}, topo {hc['frente_para_tras_px']['topo']} px ({hc['frente_para_tras_lado_x_topo_dif_pct']}%)",
        "frente, perfil e costas coerentes; o topo, como nos chifres, não bate (mais estreito e mais longo para trás: parece vista oblíqua de cima e de trás)",
        "CABEÇA, largura ÷ altura (largura máxima ÷ topo ao queixo, vista de frente)",
        f"corpo {hp_['corpo']['largura_sobre_altura']} · chifres {hp_['chifres']['largura_sobre_altura']} · cabelo: alto coberto, entre "
        f"{hp_['cabelo']['ate_o_topo_do_cabelo_largura_sobre_altura']} (topo no topo do cabelo) e {hp_['cabelo']['rosto_visivel_largura_sobre_altura']} (topo na linha do cabelo)",
        "linhas: verde topo e largura máxima, azul/magenta queixo; no cabelo, magenta = topo do cabelo",
    ]
    ty = y + max(ft[1].height for ft in face_tiles) + 20 + 7 * 22 + 16
    for i, line in enumerate(hl):
        d.text((16, ty + i * 22), line, fill=(120, 40, 40) if line.isupper() or line.startswith("CABEÇA") else (30, 30, 40), font=small if not (line.isupper() or line.startswith("CABEÇA")) else font)
    out.save(OUT / "recortes.png")


if __name__ == "__main__":
    main()

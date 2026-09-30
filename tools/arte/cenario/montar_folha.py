"""Monta a folha de contato da árvore piloto com os renders de folha_arvore.py.

Uso: uv run --project tools/arte tools/arte/cenario/montar_folha.py <pasta_dos_renders>
Saída: assets/previews/cenario/arvore_contato.png
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/previews/cenario/arvore_contato.png"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
W = 3024
BG = (238, 236, 240)
TWILIGHT = (106, 91, 124)  # #6A5B7C
NOMES = {"aldeao": "aldeão", "protagonista": "protagonista"}


def font(size):
    return ImageFont.truetype(FONT, size)


def twilight(im):
    return ImageChops.multiply(im.convert("RGB"), Image.new("RGB", im.size, TWILIGHT))


class Sheet:
    def __init__(self):
        self.rows = []  # (altura, função de desenho)

    def text(self, s, size=34, color=(30, 30, 30), pad=10):
        h = size + 2 * pad
        self.rows.append((h, lambda img, y: ImageDraw.Draw(img).text((20, y + pad), s, fill=color, font=font(size))))

    def images(self, items, gap=16):
        """items: (imagem, legenda). Lado a lado, legenda em cima."""
        h = max(im.height for im, _ in items) + 44

        def draw(img, y):
            x = 20
            d = ImageDraw.Draw(img)
            for im, label in items:
                d.text((x, y + 4), label, fill=(40, 40, 40), font=font(28))
                img.paste(im.convert("RGB"), (x, y + 40))
                x += im.width + gap
        self.rows.append((h + gap, draw))

    def save(self, path):
        total = sum(h for h, _ in self.rows) + 20
        img = Image.new("RGB", (W, total), BG)
        y = 10
        for h, draw in self.rows:
            draw(img, y)
            y += h
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, optimize=True)
        print(path, img.size)


def main():
    src = Path(sys.argv[1])
    m = json.loads((src / "medidas.json").read_text())
    rep = json.loads((ROOT / "assets/cenario/arvore/arvore_relatorio.json").read_text())
    crop = lambda name, key=None: Image.open(src / f"{name}.png").convert("RGB").crop(m["recortes"][key or name])

    s = Sheet()
    s.text("Árvore piloto, revisão 2 — mais torta (tronco inclinado 5–12°, pontas dobradas, massas assimétricas); "
           "4 alta vira chapéu de bruxa dobrado", 40)
    s.text("Material fosco, luz de crepúsculo fria de cima (corpo_lib.twilight_lights), chão chapado terra arroxeada "
           "#3F3342. Aldeão v2 (0,40 m, só corpo) e protagonista (bruto v2 da Meshy escalado a 0,80 m) para escala.",
           26, (70, 70, 70))
    tile = 700
    for vista, titulo in (("frente", "frente"), ("tres_quartos", "3/4")):
        items = []
        for v in rep["variacoes"]:
            i = v["arquivo"].split("_")[1].split(".")[0]
            im = Image.open(src / f"arvore_{i}_{vista}.png").convert("RGB").resize((tile, tile), Image.LANCZOS)
            label = (f"{i} {v['nome']}: {v['triangulos']} tri, {v['altura_m']:.2f} m, {v['inclinacao_graus']}°"
                     if vista == "frente"
                     else f"{i} {v['nome']} — {titulo}")
            items.append((im, label))
        s.images(items, gap=34)
    s.text("Cores: " + " | ".join(f"{v['nome']}: tronco {v['cores']['tronco']}, copa {v['cores']['copa']}"
                                  for v in rep["variacoes"]), 26, (70, 70, 70))

    s.text("Câmera do jogo (55°, FOV 45°, 16 m ÷ zoom, 3024×1890) — recortes em pixels reais", 38)
    z04 = crop("fila_zoom_0.4", "fila_0.4")
    z1 = crop("fila_zoom_1.0", "fila_1.0")
    z25 = crop("fila_zoom_2.5", "fila_2.5")
    big04 = z04.resize((z04.width * 3, z04.height * 3), Image.NEAREST)
    s.images([(z04, "zoom 0,4 (1:1)"), (big04, "zoom 0,4 ampliado ×3 (mesmos pixels)"), (z1, "zoom 1 (1:1)")])
    s.images([(z25, "zoom 2,5 (1:1)")])
    s.text("Crepúsculo (× #6A5B7C)", 38)
    s.images([(twilight(z04), "zoom 0,4"), (twilight(big04), "zoom 0,4 ×3"), (twilight(z1), "zoom 1")])
    s.images([(twilight(z25), "zoom 2,5")])

    s.text("Bosque: 8 árvores, uma por célula, giro e escala (0,9–1,1) sorteados, líquen 1 em 8 — zoom 1, "
           "ampliado ×1,2", 38)
    s.text("Saídas para a copa musgo no crepúsculo: (a) copa #5A5847, o extremo claro da faixa pedida; "
           "(b) musgo #4E5544 com borda de luz fria (aproximação: o Toon do jogo e o visor ainda não têm borda)",
           26, (70, 70, 70))
    cols = []
    for suf, label in (("", "atual: musgo #4E5544"), ("_a", "(a) copa #5A5847"), ("_b", "(b) musgo + borda fria")):
        b = crop(f"bosque{suf}_zoom_1.0", "bosque_1.0")
        cols.append((b.resize((int(b.width * 1.2), int(b.height * 1.2)), Image.LANCZOS), label))
    s.images(cols)
    s.images([(twilight(im), label + " — crepúsculo") for im, label in cols])
    s.text("Sorteio proposto por célula de árvore: 1 gota 30 %, 2 dupla 30 %, 4 alta 30 %, 3 tufos (líquen) 10 %.",
           30, (40, 40, 40))

    s.text("Personagem atrás da árvore (mais longe da câmera) — zoom 1, ampliado ×2; % = quanto do corpo aparece", 38)
    items, items_t = [], []
    for key, frac in m["atras"].items():
        nome, dist = key.split("_atras_")[0], key.rsplit("_", 1)[1]
        im = crop(key)
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
        label = f"{NOMES[nome]} {dist.replace('m', ' m').replace('.', ',')} atrás: {round(100 * frac)} %"
        items.append((im, label))
        items_t.append((twilight(im), label))
    s.images(items)
    s.images(items_t)
    s.save(OUT)


if __name__ == "__main__":
    main()

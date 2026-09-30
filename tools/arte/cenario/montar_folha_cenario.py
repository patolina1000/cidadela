"""Monta a folha de contato conjunta do cenário (pedra, veio e as três famílias) com os renders de folha_cenario.py.

Uso: uv run --project tools/arte tools/arte/cenario/montar_folha_cenario.py <pasta_dos_renders>
Saída: assets/previews/cenario/cenario_contato.png
"""

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from montar_folha import ROOT, Sheet, twilight  # noqa: E402

OUT = ROOT / "assets/previews/cenario/cenario_contato.png"


def main():
    src = Path(sys.argv[1])
    m = json.loads((src / "medidas.json").read_text())
    crop = lambda name, key: Image.open(src / f"{name}.png").convert("RGB").crop(m["recortes"][key])

    s = Sheet()
    s.text("Cenário — as três famílias para aprovação: árvore (revisão 3), pedra (escurecida) e veio de ferro", 44)
    s.text("Material fosco, luz de crepúsculo fria de cima, chão chapado #3F3342, borda de luz fria (b) na copa, na "
           "pedra e no veio. Aldeão v2 (0,40 m) e protagonista (bruto v2, 0,80 m) para escala.", 26, (70, 70, 70))
    tile = 360
    for familia, cores in (("pedra", "pedra escurecida #57535F (tarefa 4), tampa de musgo #4E5544 na 1"),
                           ("veio", "rocha lama #2E2931, lascas azul meia-noite #1E2A3A (a cor do ferro), engordadas na tarefa 4")):
        rep = json.loads((ROOT / f"assets/cenario/{familia}/{familia}_relatorio.json").read_text())
        items = []
        for vista in ("frente", "tres_quartos"):
            for i, v in enumerate(rep["variacoes"], start=1):
                im = Image.open(src / f"{familia}_{i}_{vista}.png").convert("RGB").resize((tile, tile), Image.LANCZOS)
                label = (f"{i} {v['nome']}: {v['triangulos']} tri, {v['altura_m']:.2f} m".replace(".", ",")
                         if vista == "frente" else f"{i} {v['nome']} — 3/4")
                items.append((im, label))
        s.text(f"{familia.capitalize()} — {cores}", 34)
        s.images(items, gap=16)

    s.text("As três famílias juntas (3/4): árvore 1, pedra 1, veio 1, aldeão, protagonista", 38)
    fam = Image.open(src / "familias.png").convert("RGB")
    s.images([(fam, "luz do jogo"), (twilight(fam).resize((fam.width // 2, fam.height // 2), Image.LANCZOS),
                                     "crepúsculo (½)")])

    for nome, titulo in (("fila", "Fila de pedras 1–4 e veios 1–4, uma por célula"),
                         ("mapa", "Pedaço de mapa: bosque (sorteio 30/30/10/30 %), pedras soltas, mancha de 4 veios")):
        s.text(f"{titulo} — câmera do jogo (55°, FOV 45°, 16 m ÷ zoom, 3024×1890), pixels reais", 38)
        z = {k: crop(f"{nome}_zoom_{k}", f"{nome}_{k}") for k in (0.4, 1.0, 2.5)}
        big = z[0.4].resize((z[0.4].width * 3, z[0.4].height * 3), Image.NEAREST)
        s.images([(z[0.4], "zoom 0,4"), (big, "zoom 0,4 ×3"), (z[1.0], "zoom 1")])
        s.images([(twilight(z[0.4]), "crepúsculo 0,4"), (twilight(big), "crepúsculo 0,4 ×3"),
                  (twilight(z[1.0]), "crepúsculo 1")])
        s.images([(z[2.5], "zoom 2,5")])
        s.images([(twilight(z[2.5]), "zoom 2,5 — crepúsculo")])
    s.save(OUT)


if __name__ == "__main__":
    main()

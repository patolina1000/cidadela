"""Acrescenta uma prévia ao visor (assets/previews/visor.json). O visor mostra a mais nova em até 2 s.

Uso, na raiz da worktree da arte:
  python3 tools/arte/visor/publicar.py <caminho> <imagem|gif|glb> "<título>" "<nota>" [--junto a.glb b.glb]

O caminho (e os do --junto) precisa estar dentro de assets/, que é o que o servidor do visor entrega.
"""

import argparse
import datetime
import json
import os
import sys
import tempfile

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
VISOR = os.path.join(ROOT, "assets", "previews", "visor.json")
EXTENSOES = {"imagem": (".png", ".jpg", ".jpeg", ".webp"), "gif": (".gif",), "glb": (".glb",)}


def relativo(caminho, extensoes):
    """Caminho relativo à raiz, validado: existe, fica em assets/, sem pasta oculta, extensão certa."""
    real = os.path.realpath(caminho if os.path.isabs(caminho) else os.path.join(os.getcwd(), caminho))
    if not os.path.isfile(real):
        # Aceita também relativo à raiz da worktree, rodando de outra pasta.
        real = os.path.realpath(os.path.join(ROOT, caminho))
    if not os.path.isfile(real):
        sys.exit(f"não existe: {caminho}")
    rel = os.path.relpath(real, ROOT).replace(os.sep, "/")
    if not rel.startswith("assets/") or any(p.startswith(".") for p in rel.split("/")):
        sys.exit(f"fora de assets/ (o visor não entrega): {rel}")
    if not rel.lower().endswith(extensoes):
        sys.exit(f"extensão não bate com o tipo ({', '.join(extensoes)}): {rel}")
    return rel


def main():
    ap = argparse.ArgumentParser(description="Acrescenta uma prévia ao visor.")
    ap.add_argument("caminho")
    ap.add_argument("tipo", choices=sorted(EXTENSOES))
    ap.add_argument("titulo")
    ap.add_argument("nota")
    ap.add_argument("--junto", nargs="+", default=[], metavar="GLB",
                    help="outros GLBs na mesma cena (peça no osso do encaixe, corpo ao lado, GLB de clipes)")
    a = ap.parse_args()
    if a.junto and a.tipo != "glb":
        sys.exit("--junto só vale para tipo glb")

    item = {
        "quando": datetime.datetime.now().isoformat(timespec="seconds"),
        "titulo": a.titulo,
        "tipo": a.tipo,
        "caminho": relativo(a.caminho, EXTENSOES[a.tipo]),
        "nota": a.nota,
    }
    if a.junto:
        item["junto"] = [relativo(j, EXTENSOES["glb"]) for j in a.junto]

    itens = []
    if os.path.exists(VISOR):
        with open(VISOR, encoding="utf-8") as f:
            itens = json.load(f)
    if itens and itens[-1]["quando"] >= item["quando"]:
        # Dois no mesmo segundo: o visor ordena por "quando", então o novo não pode empatar.
        ultimo = datetime.datetime.fromisoformat(itens[-1]["quando"])
        item["quando"] = (ultimo + datetime.timedelta(seconds=1)).isoformat(timespec="seconds")
    itens.append(item)

    # Grava inteiro e troca de uma vez: o visor nunca lê um JSON pela metade.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(VISOR), prefix=".visor", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(itens, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, VISOR)
    print(f"publicado ({len(itens)} no visor): {item['titulo']}  →  http://127.0.0.1:8765/")


if __name__ == "__main__":
    main()

"""Cabelos do aldeão como peças próprias ("perucas") na Meshy.

Para cada variação:
1. Image to Image (referências: vistas de frente e de costas do conceito) gera a peruca sozinha, de frente
   e de costas: sem cabeça, sem rosto, franja acima das sobrancelhas.
2. Multi-Image to 3D com as duas imagens (a primeira é a frente) gera a peça fechada e texturizada.
Brutos em assets/modelos/aldeao_cabelos/bruto/ (fora do git). O encaixe na cabeça é feito no Blender
(tools/blender/fit_hair.py). Estado em hair_state.json; trava de créditos.

Uso:
  uv run hair_pieces.py                        # saldo e estimativa
  uv run hair_pieces.py --run curto_baguncado  # gera as variações pedidas
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from pipeline import ROOT, Meshy, fetch

VIEWS = ROOT / "assets/conceitos/aldeao/vistas"
RAW = ROOT / "assets/modelos/aldeao_cabelos/bruto"
STATE_FILE = Path(__file__).with_name("hair_state.json")
LIMIT = 250  # créditos (aprovados: 210 para os 5 cabelos)
IMAGE_MODEL = "nano-banana-2"
COST = {"frente": 6, "costas": 6, "modelo": 30}
VARIANTS = ("curto_baguncado", "medio_franja", "ondulado", "longo_liso", "rabo_cavalo")
ATTEMPTS = 2

PROMPT = (
    "Using the hairstyle shown in the reference images, draw ONLY that hairstyle as a standalone wig, "
    "seen from the {side}, centered, on a plain white background. No head, no face, no skin, no neck, no body: "
    "only the hair, as a single closed, full and tidy hair volume with the same hand-painted style, "
    "blue-grey colors and strand shapes as the reference. {extra}"
)
EXTRA = {
    "frente": "The fringe must end above the eyebrow line: the whole face area stays empty, with no strands "
              "hanging in front of the face or the eyes.",
    "costas": "The back must be fully covered with hair, with no gaps, holes or bald spots.",
}


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def spent(state: dict) -> int:
    return sum(a.get("credits", a.get("estimate", 0)) for v in state.values() for s in v.values()
               for a in s.get("attempts", []))


def step(meshy: Meshy, state: dict, variant: str, name: str, path: str, body: dict) -> dict | None:
    record = state.setdefault(variant, {}).setdefault(name, {"attempts": []})
    if record.get("status") == "SUCCEEDED":
        return record["task"]
    while len(record["attempts"]) < ATTEMPTS:
        if spent(state) + COST[name] > LIMIT:
            raise RuntimeError(f"limite de {LIMIT} créditos: parei antes de {variant}/{name}")
        task_id = meshy.post(path, body)
        attempt = {"task_id": task_id, "estimate": COST[name]}
        record["attempts"].append(attempt)
        save_state(state)
        task = meshy.wait(path, task_id)
        attempt["credits"] = task.get("consumed_credits", 0)
        attempt["status"] = task["status"]
        save_state(state)
        print(f"  {variant}/{name}: {task['status']} ({attempt['credits']} créditos)")
        if task["status"] == "SUCCEEDED":
            record.update(status="SUCCEEDED", task=task)
            save_state(state)
            return task
    return None


def generate(meshy: Meshy, state: dict, variant: str) -> None:
    refs = [data_uri(VIEWS / f"{variant}_frente.png"), data_uri(VIEWS / f"{variant}_costas.png")]
    images = {}
    for side, word in (("frente", "front"), ("costas", "back")):
        task = step(meshy, state, variant, side, "/v1/image-to-image", {
            "ai_model": IMAGE_MODEL,
            "prompt": PROMPT.format(side=word, extra=EXTRA[side]),
            "reference_image_urls": refs,
        })
        if task is None:
            print(f"  {variant}: imagem de {side} falhou duas vezes")
            return
        images[side] = RAW / f"{variant}_{side}.png"
        fetch(task["image_urls"][0], images[side])
    task = step(meshy, state, variant, "modelo", "/v1/multi-image-to-3d", {
        "image_urls": [data_uri(images["frente"]), data_uri(images["costas"])],
        "ai_model": "latest",
        "should_texture": True,
        "texture_resolution": "2k",
        "image_enhancement": False,
        "should_remesh": True,
        "topology": "triangle",
        "target_polycount": 3000,
        "target_formats": ["glb"],
    })
    if task is None:
        print(f"  {variant}: modelo falhou duas vezes")
        return
    fetch(task["model_urls"]["glb"], RAW / f"{variant}.glb")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("variants", nargs="*", default=list(VARIANTS))
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    if not os.environ.get("MESHY_API_KEY"):
        sys.exit("MESHY_API_KEY não encontrada no .env")
    meshy = Meshy(os.environ["MESHY_API_KEY"])
    state = load_state()
    todo = sum(COST[s] for v in args.variants for s in COST if state.get(v, {}).get(s, {}).get("status") != "SUCCEEDED")
    print(f"Saldo: {meshy.balance()}. Estimativa para {', '.join(args.variants)}: {todo} créditos. "
          f"Já gastos: {spent(state)}. Limite: {LIMIT}.")
    if not args.run:
        return
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / ".gdignore").touch()
    for variant in args.variants:
        print(f"== {variant}")
        generate(meshy, state, variant)
    print(f"Gastos nos cabelos: {spent(state)}. Saldo: {meshy.balance()}.")


if __name__ == "__main__":
    main()

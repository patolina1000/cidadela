"""Passo 11: peruca na Meshy (cabeça + cabelo da folha), só malha, para extrair a peruca no Blender.

Multi-Image to 3D com frente, lado, costas e topo da folha do cabelo (a primeira é a frente), should_texture
falso (20 créditos), should_remesh + target_polycount 3000 (a cabeça leva ~40% e some; o cabelo é decimado
depois para ≤ 800), symmetry_mode auto. Brutos em assets/conceitos/aldeao_v2/meshy/cabelos/cabelo_N_<tentativa>.glb.
Trava: MAX_GENERATIONS por cabelo. Estado em estado_meshy_cabelos.json (fora do git).

Uso:
  uv run meshy_cabelo.py 4            # saldo e estado (não gasta)
  uv run meshy_cabelo.py 4 --run      # gera (ou repete) o cabelo 4
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
VIEWS = ROOT / "assets/conceitos/aldeao_v2/vistas"
OUT = ROOT / "assets/conceitos/aldeao_v2/meshy/cabelos"
STATE_FILE = Path(__file__).with_name("estado_meshy_cabelos.json")
API = "https://api.meshy.ai/openapi"
MAX_GENERATIONS = 2
COST = 20
NAMES = {1: "1_curto_baguncado", 2: "2_medio_franja_lado", 3: "3_ondulado", 4: "4_longo_liso", 5: "5_rabo_de_cavalo"}
PAYLOAD = {"ai_model": "latest", "should_texture": False, "should_remesh": True, "topology": "triangle", "target_polycount": 3000, "symmetry_mode": "auto"}


def data_uri(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cabelo", type=int, choices=list(NAMES))
    p.add_argument("--run", action="store_true")
    args = p.parse_args()
    for env in (Path(__file__).resolve().parents[1] / ".env", ROOT / ".env"):
        if env.exists():
            load_dotenv(env)
            break
    key = os.environ.get("MESHY_API_KEY") or sys.exit("MESHY_API_KEY não encontrada")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {key}"
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    tasks = state.setdefault(str(args.cabelo), [])
    print(f"saldo: {s.get(f'{API}/v1/balance', timeout=30).json()['balance']}; cabelo {args.cabelo}: {len(tasks)}/{MAX_GENERATIONS} gerações")
    if not args.run:
        return
    if len(tasks) >= MAX_GENERATIONS:
        sys.exit("trava: gerações esgotadas para este cabelo; pare e pergunte")
    stem = f"cabelo_{NAMES[args.cabelo]}_folha"
    images = [VIEWS / f"{stem}_{v}.png" for v in ("frente", "lado", "costas", "topo")]
    for i in images:
        if not i.exists():
            sys.exit(f"falta {i}")
    payload = dict(PAYLOAD, image_urls=[data_uri(i) for i in images])
    r = s.post(f"{API}/v1/multi-image-to-3d", json=payload, timeout=120)
    if r.status_code >= 400:
        sys.exit(f"erro {r.status_code}: {r.text[:300]}")
    task_id = r.json()["result"]
    record = {"task_id": task_id, "tentativa": len(tasks) + 1, "status": "PENDING"}
    tasks.append(record)
    STATE_FILE.write_text(json.dumps(state, indent=2))
    start = time.time()
    while time.time() - start < 1800:
        task = s.get(f"{API}/v1/multi-image-to-3d/{task_id}", timeout=30).json()
        print(f"    {task['status']} {task.get('progress', 0)}%", flush=True)
        if task["status"] in ("SUCCEEDED", "FAILED", "CANCELED", "EXPIRED"):
            break
        time.sleep(10)
    record.update(status=task["status"], creditos=task.get("consumed_credits"), erro=(task.get("task_error") or {}).get("message"))
    STATE_FILE.write_text(json.dumps(state, indent=2))
    if task["status"] != "SUCCEEDED":
        sys.exit(f"falhou: {record['erro']}")
    OUT.mkdir(parents=True, exist_ok=True)
    glb = OUT / f"cabelo_{args.cabelo}_{record['tentativa']}.glb"
    glb.write_bytes(requests.get(task["model_urls"]["glb"], timeout=300).content)
    record["glb"] = str(glb.relative_to(ROOT))
    STATE_FILE.write_text(json.dumps(state, indent=2))
    print(f"baixado: {record['glb']}; saldo final: {s.get(f'{API}/v1/balance', timeout=30).json()['balance']}")


if __name__ == "__main__":
    main()

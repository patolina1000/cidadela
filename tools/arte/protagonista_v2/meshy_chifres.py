"""Protagonista v2: chifres na Meshy (piloto, rígidos). Busto careca + chifres da folha aprovada, Multi-Image to 3D
com frente, perfil e costas (sem o topo: a conferência dos recortes mostrou o topo incoerente), só malha (20 créditos),
remesh a 6.000 triângulos (a cabeça do busto sai na extração; os chifres precisam de detalhe para as facetas),
simetria desligada (os chifres são assimétricos: o direito é ~32% maior de frente).

Teto (manda do Arthur, 29/09/2026): 300 créditos para a protagonista inteira, somando corpo (meshy/corpo_meshy.json),
rig e clipes (meshy/rig_meshy.json) e estas gerações (meshy/chifres_meshy.json, público, sem chave). Saldo e custo
conferidos antes de cada pedido. Brutos em assets/modelos/protagonista_v2/meshy/chifres/chifres_<n>.glb.

Uso (em tools/arte):
  uv run protagonista_v2/meshy_chifres.py          # saldo e gasto (não gasta)
  uv run protagonista_v2/meshy_chifres.py --run    # uma geração
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
VIEWS = ROOT / "assets/conceitos/protagonista_v2/vistas"
MESHY_DIR = ROOT / "assets/modelos/protagonista_v2/meshy"
OUT = MESHY_DIR / "chifres"
RECORD = MESHY_DIR / "chifres_meshy.json"
API = "https://api.meshy.ai/openapi"
COST, CAP, MAX_GENERATIONS = 20, 300, 3
IMAGES = ["chifres_frente.png", "chifres_lado.png", "chifres_costas.png"]
PAYLOAD = {"ai_model": "latest", "should_texture": False, "should_remesh": True, "topology": "triangle",
           "target_polycount": 6000, "symmetry_mode": "off"}


def spent_total() -> int:
    total = 0
    for name, key in (("corpo_meshy.json", "tarefas"), ("rig_meshy.json", "pedidos"), ("chifres_meshy.json", "tarefas")):
        path = MESHY_DIR / name
        if path.exists():
            total += sum(t.get("creditos") or 0 for t in json.loads(path.read_text())[key])
    return total


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", action="store_true")
    args = p.parse_args()
    for env in (ROOT / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if env.exists():
            load_dotenv(env)
            break
    s = requests.Session()
    s.headers["Authorization"] = "Bearer " + os.environ["MESHY_API_KEY"]
    balance = lambda: s.get(f"{API}/v1/balance", timeout=30).json()["balance"]  # noqa: E731
    record = json.loads(RECORD.read_text()) if RECORD.exists() else {"teto_protagonista": CAP, "tarefas": []}
    before = balance()
    print(f"saldo {before}; gasto na protagonista {spent_total()}/{CAP}; gerações de chifres {len(record['tarefas'])}/{MAX_GENERATIONS}; "
          f"este pedido ~{COST}")
    if not args.run:
        return
    if spent_total() + COST > CAP or len(record["tarefas"]) >= MAX_GENERATIONS or before < COST:
        sys.exit("passaria do teto (ou das gerações, ou do saldo): pare e avise o Diretor")
    payload = dict(PAYLOAD)
    payload["image_urls"] = ["data:image/png;base64," + base64.b64encode((VIEWS / n).read_bytes()).decode() for n in IMAGES]
    r = s.post(f"{API}/v1/multi-image-to-3d", json=payload, timeout=180)
    if r.status_code >= 400:
        sys.exit(f"recusado: {r.status_code} {r.text[:300]}")
    task_id = r.json()["result"]
    n = len(record["tarefas"]) + 1
    rec = {"tentativa": n, "task_id": task_id, "status": "PENDING", "saldo_antes": before, "imagens": IMAGES, "parametros": PAYLOAD}
    record["tarefas"].append(rec)
    MESHY_DIR.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    last = None
    while True:
        task = s.get(f"{API}/v1/multi-image-to-3d/{task_id}", timeout=30).json()
        if (task["status"], task.get("progress")) != last:
            print(f"    {task['status']} {task.get('progress', 0)}%", flush=True)
            last = (task["status"], task.get("progress"))
        if task["status"] in ("SUCCEEDED", "FAILED", "CANCELED", "EXPIRED"):
            break
        time.sleep(10)
    rec["saldo_depois"] = balance()
    rec["status"] = task["status"]
    rec["creditos"] = task.get("consumed_credits") if isinstance(task.get("consumed_credits"), int) else before - rec["saldo_depois"]
    rec["erro"] = (task.get("task_error") or {}).get("message") or None
    if task["status"] == "SUCCEEDED":
        OUT.mkdir(parents=True, exist_ok=True)
        glb = OUT / f"chifres_{n}.glb"
        glb.write_bytes(requests.get(task["model_urls"]["glb"], timeout=300).content)
        rec["glb"] = str(glb.relative_to(ROOT))
        print(f"  baixado: {rec['glb']}, créditos {rec['creditos']}, id {task_id}")
    RECORD.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(f"saldo final {rec['saldo_depois']}; gasto na protagonista {spent_total()}/{CAP}")


if __name__ == "__main__":
    main()

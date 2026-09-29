"""Parte C: corpo do aldeão v2 na Meshy, em duas entradas de teste, sem textura.

- so_frente: Image to 3D com a vista de frente;
- multi: Multi-Image to 3D com frente, lado e costas (a primeira é a frente).
Parâmetros (docs.meshy.ai, 29/09/2026): should_texture false (20 créditos), pose_mode "a-pose", should_remesh
true, topology "triangle", target_polycount 2500 (contrato: até 2.500 triângulos), symmetry_mode "auto",
ai_model "latest". Os GLB vão para assets/conceitos/aldeao_v2/meshy/<nome>.glb (brutos, sem limpeza).

Trava: no máximo MAX_GENERATIONS tarefas criadas (contadas no estado); passou, o script para e pede.
A chave vem de tools/arte/.env (MESHY_API_KEY) ou do ambiente; nunca é impressa.
Estado em tools/arte/aldeao_v2/estado_meshy_corpo.json (fora do git).

Uso:
  uv run meshy_corpo.py                 # saldo, estimativa e estado (não gasta)
  uv run meshy_corpo.py --run           # cria o que falta e baixa
  uv run meshy_corpo.py --run --only multi
  uv run meshy_corpo.py --run --repetir so_frente   # nova tentativa (conta na trava)
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
OUT = ROOT / "assets/conceitos/aldeao_v2/meshy"
STATE_FILE = Path(__file__).with_name("estado_meshy_corpo.json")
API = "https://api.meshy.ai/openapi"
POLL_SECONDS = 10
TIMEOUT_SECONDS = 30 * 60
MAX_GENERATIONS = 6
COST_MESH_ONLY = 20

COMMON = {
    "ai_model": "latest",
    "should_texture": False,
    "pose_mode": "a-pose",
    "should_remesh": True,
    "topology": "triangle",
    "target_polycount": 2500,
    "symmetry_mode": "auto",
}
INPUTS = {
    "so_frente": {"endpoint": "image-to-3d", "images": ["aldeao_corpo_folha_frente.png"]},
    "multi": {"endpoint": "multi-image-to-3d",
              "images": ["aldeao_corpo_folha_frente.png", "aldeao_corpo_folha_lado.png", "aldeao_corpo_folha_costas.png"]},
}


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


class Meshy:
    def __init__(self, key: str):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {key}"

    def balance(self) -> int:
        r = self.s.get(f"{API}/v1/balance", timeout=30)
        r.raise_for_status()
        return r.json()["balance"]

    def create(self, endpoint: str, payload: dict) -> str:
        r = self.s.post(f"{API}/v1/{endpoint}", json=payload, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"{endpoint}: {r.status_code} {r.text[:300]}")
        return r.json()["result"]

    def wait(self, endpoint: str, task_id: str) -> dict:
        start = time.time()
        while time.time() - start < TIMEOUT_SECONDS:
            r = self.s.get(f"{API}/v1/{endpoint}/{task_id}", timeout=30)
            r.raise_for_status()
            task = r.json()
            status = task["status"]
            print(f"    {status} {task.get('progress', 0)}%", flush=True)
            if status in ("SUCCEEDED", "FAILED", "CANCELED", "EXPIRED"):
                return task
            time.sleep(POLL_SECONDS)
        raise TimeoutError(task_id)


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"tarefas": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--only", choices=list(INPUTS))
    parser.add_argument("--repetir", choices=list(INPUTS), help="cria uma nova tentativa dessa entrada")
    args = parser.parse_args()

    for env in (Path(__file__).resolve().parents[1] / ".env", ROOT / ".env"):  # tools/arte/.env ou a raiz do repositório
        if env.exists():
            load_dotenv(env)
            break
    key = os.environ.get("MESHY_API_KEY")
    if not key:
        print("MESHY_API_KEY não encontrada: crie tools/arte/.env (ou .env na raiz) com MESHY_API_KEY=...; o git ignora .env")
        sys.exit(2)
    meshy = Meshy(key)
    state = load_state()
    done = {t["entrada"] for t in state["tarefas"] if t.get("status") == "SUCCEEDED"}
    created = len(state["tarefas"])
    print(f"saldo: {meshy.balance()} créditos; gerações criadas: {created}/{MAX_GENERATIONS}; concluídas: {sorted(done) or '-'}")

    todo = []
    if args.repetir:
        todo.append(args.repetir)
    for name in INPUTS:
        if name not in done and (not args.only or args.only == name) and name not in todo:
            todo.append(name)
    print(f"a fazer: {todo or '-'}  (~{COST_MESH_ONLY * len(todo)} créditos)")
    if not args.run or not todo:
        return
    for name in todo:
        if len(state["tarefas"]) >= MAX_GENERATIONS:
            print(f"trava: {MAX_GENERATIONS} gerações já criadas nesta parte; pare e pergunte.")
            sys.exit(3)
        spec = INPUTS[name]
        paths = [VIEWS / img for img in spec["images"]]
        for p in paths:
            if not p.exists():
                sys.exit(f"falta {p.relative_to(ROOT)}: rode o preparador")
        payload = dict(COMMON)
        if spec["endpoint"] == "image-to-3d":
            payload["image_url"] = data_uri(paths[0])
        else:
            payload["image_urls"] = [data_uri(p) for p in paths]
        attempt = sum(1 for t in state["tarefas"] if t["entrada"] == name) + 1
        print(f"{name} (tentativa {attempt}): criando na Meshy ({spec['endpoint']})")
        task_id = meshy.create(spec["endpoint"], payload)
        record = {"entrada": name, "tentativa": attempt, "task_id": task_id, "endpoint": spec["endpoint"], "status": "PENDING"}
        state["tarefas"].append(record)
        save_state(state)
        task = meshy.wait(spec["endpoint"], task_id)
        record["status"] = task["status"]
        record["creditos"] = task.get("consumed_credits")
        record["erro"] = (task.get("task_error") or {}).get("message")
        if task["status"] == "SUCCEEDED":
            OUT.mkdir(parents=True, exist_ok=True)
            glb = OUT / f"corpo_{name}_{attempt}.glb"
            data = requests.get(task["model_urls"]["glb"], timeout=300)
            data.raise_for_status()
            glb.write_bytes(data.content)
            record["glb"] = str(glb.relative_to(ROOT))
            print(f"  baixado: {record['glb']} ({len(data.content) // 1024} KB), créditos {record['creditos']}")
        else:
            print(f"  falhou: {record['erro']}")
        save_state(state)
    print(f"saldo final: {meshy.balance()} créditos")


if __name__ == "__main__":
    main()

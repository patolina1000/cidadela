"""Protagonista v2, passo 2: corpo na Meshy, sem textura, pose A. Brutos, sem limpeza, rig ou decimação.

- a_frente: Image to 3D só com corpo_frente.png;
- b_multi: Multi-Image to 3D com frente, perfil e costas (sem o topo; a primeira é a frente).
Parâmetros iguais aos do corpo aprovado do aldeão (aldeao_v2/meshy_corpo.py): ai_model "latest",
should_texture false (mesh only, 20 créditos), pose_mode "a-pose", should_remesh true, topology "triangle",
target_polycount 2500 (contrato: corpo até 2.500 triângulos), symmetry_mode "auto".

Travas (aval do Arthur em 29/09/2026): no máximo MAX_GENERATIONS tarefas criadas e CREDIT_CAP créditos no total,
contados no estado. Antes de cada geração confere o saldo e o custo previsto; se passar do teto, para.
A 3ª geração é reserva, só para falha técnica: sai com --reserva <entrada>.

A chave vem do .env da raiz da worktree (ou tools/arte/.env), nunca é impressa.
Estado em tools/arte/protagonista_v2/estado_meshy_corpo.json (fora do git); o registro público (ids, créditos)
vai em assets/modelos/protagonista_v2/meshy/corpo_meshy.json.

Uso (em tools/arte):
  uv run protagonista_v2/meshy_corpo.py                      # saldo, previsão e estado (não gasta)
  uv run protagonista_v2/meshy_corpo.py --run --only a_frente
  uv run protagonista_v2/meshy_corpo.py --run --only b_multi
  uv run protagonista_v2/meshy_corpo.py --run --reserva a_frente   # só com falha técnica
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
OUT = ROOT / "assets/modelos/protagonista_v2/meshy"
RECORD = OUT / "corpo_meshy.json"
STATE_FILE = Path(__file__).with_name("estado_meshy_corpo.json")
API = "https://api.meshy.ai/openapi"
POLL_SECONDS = 10
TIMEOUT_SECONDS = 30 * 60
MAX_GENERATIONS = 3
CREDIT_CAP = 60
COST_MESH_ONLY = 20  # previsão por geração sem textura (tabela da Meshy; o real vem em consumed_credits)

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
    "a_frente": {"endpoint": "image-to-3d", "images": ["corpo_frente.png"]},
    "b_multi": {"endpoint": "multi-image-to-3d", "images": ["corpo_frente.png", "corpo_lado.png", "corpo_costas.png"]},
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
        last = None
        while time.time() - start < TIMEOUT_SECONDS:
            r = self.s.get(f"{API}/v1/{endpoint}/{task_id}", timeout=30)
            r.raise_for_status()
            task = r.json()
            status = task["status"]
            if (status, task.get("progress")) != last:
                print(f"    {status} {task.get('progress', 0)}%", flush=True)
                last = (status, task.get("progress"))
            if status in ("SUCCEEDED", "FAILED", "CANCELED", "EXPIRED"):
                return task
            time.sleep(POLL_SECONDS)
        raise TimeoutError(task_id)


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"tarefas": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    public = [{k: t.get(k) for k in ("entrada", "tentativa", "task_id", "endpoint", "status", "creditos",
                                      "saldo_antes", "saldo_depois", "glb", "erro", "imagens", "parametros")}
              for t in state["tarefas"]]
    OUT.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps({"teto_creditos": CREDIT_CAP, "teto_geracoes": MAX_GENERATIONS,
                                  "tarefas": public}, indent=2, ensure_ascii=False) + "\n")


def spent(state: dict) -> int:
    # Tarefa sem consumo conhecido conta pela previsão, para a trava nunca subestimar.
    return sum(t["creditos"] if isinstance(t.get("creditos"), int) else COST_MESH_ONLY for t in state["tarefas"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--only", choices=list(INPUTS))
    parser.add_argument("--reserva", choices=list(INPUTS), help="3ª geração: repete uma entrada que falhou tecnicamente")
    args = parser.parse_args()

    for env in (ROOT / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if env.exists():
            load_dotenv(env)
            break
    key = os.environ.get("MESHY_API_KEY")
    if not key:
        sys.exit("MESHY_API_KEY não encontrada no .env da raiz da worktree (ignorado pelo git)")
    meshy = Meshy(key)
    state = load_state()
    done = {t["entrada"] for t in state["tarefas"] if t.get("status") == "SUCCEEDED"}
    print(f"saldo: {meshy.balance()} créditos; gerações criadas: {len(state['tarefas'])}/{MAX_GENERATIONS}; "
          f"gastos: {spent(state)}/{CREDIT_CAP}; concluídas: {sorted(done) or '-'}")

    if args.reserva:
        todo = [args.reserva]
    else:
        todo = [n for n in INPUTS if n not in done and (not args.only or args.only == n)]
        attempted = {t["entrada"] for t in state["tarefas"]}
        if any(n in attempted for n in todo):
            sys.exit(f"{[n for n in todo if n in attempted]} já foi tentada; repetir só com --reserva (falha técnica)")
    print(f"a fazer: {todo or '-'}  (previsão ~{COST_MESH_ONLY * len(todo)} créditos)")
    if not args.run or not todo:
        return
    for name in todo:
        if len(state["tarefas"]) >= MAX_GENERATIONS:
            sys.exit(f"trava: {MAX_GENERATIONS} gerações já criadas; pare e avise o Diretor.")
        balance = meshy.balance()
        if spent(state) + COST_MESH_ONLY > CREDIT_CAP:
            sys.exit(f"trava: {spent(state)} gastos + ~{COST_MESH_ONLY} passaria do teto de {CREDIT_CAP}; pare e avise.")
        if balance < COST_MESH_ONLY:
            sys.exit(f"saldo {balance} menor que o custo previsto {COST_MESH_ONLY}; pare e avise.")
        spec = INPUTS[name]
        paths = [VIEWS / img for img in spec["images"]]
        for p in paths:
            if not p.exists():
                sys.exit(f"falta {p.relative_to(ROOT)}")
        payload = dict(COMMON)
        if spec["endpoint"] == "image-to-3d":
            payload["image_url"] = data_uri(paths[0])
        else:
            payload["image_urls"] = [data_uri(p) for p in paths]
        attempt = sum(1 for t in state["tarefas"] if t["entrada"] == name) + 1
        print(f"{name} (tentativa {attempt}): saldo {balance}, previsão {COST_MESH_ONLY}; criando ({spec['endpoint']})")
        task_id = meshy.create(spec["endpoint"], payload)
        record = {"entrada": name, "tentativa": attempt, "task_id": task_id, "endpoint": spec["endpoint"],
                  "status": "PENDING", "saldo_antes": balance, "imagens": spec["images"], "parametros": COMMON}
        state["tarefas"].append(record)
        save_state(state)
        task = meshy.wait(spec["endpoint"], task_id)
        record["status"] = task["status"]
        record["erro"] = (task.get("task_error") or {}).get("message") or None
        record["saldo_depois"] = meshy.balance()
        consumed = task.get("consumed_credits")
        record["creditos"] = consumed if isinstance(consumed, int) else balance - record["saldo_depois"]
        if task["status"] == "SUCCEEDED":
            glb = OUT / f"corpo_{name}_{attempt}.glb"
            data = requests.get(task["model_urls"]["glb"], timeout=300)
            data.raise_for_status()
            glb.write_bytes(data.content)
            record["glb"] = str(glb.relative_to(ROOT))
            print(f"  baixado: {record['glb']} ({len(data.content) // 1024} KB), créditos {record['creditos']}, id {task_id}")
        else:
            print(f"  falhou: {record['erro']}")
        save_state(state)
    print(f"saldo final: {meshy.balance()} créditos; gastos nesta parte: {spent(state)}/{CREDIT_CAP}")


if __name__ == "__main__":
    main()

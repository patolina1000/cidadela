"""Protagonista v2: rig da Meshy e clipes da biblioteca (manda do Arthur em 29/09/2026: teto de 300 créditos para a
protagonista inteira — corpo, rig, clipes, chifres, cabelo — qualidade antes de economia).

Preços (docs.meshy.ai, 29/09/2026): rig 5 por pedido (recusa não cobra); animação 3 por ação, até 10 por pedido.
- rig: POST /openapi/v1/rigging com model_url = data URI do corpo limpo juntado numa malha (meshy/corpo_para_rig.glb,
  preparar_rig.py), height_meters 0,80; se recusar, --task-id com a tarefa original do bruto B (expira ~02/10). O
  resultado traz o GLB com rig e a caminhada e a corrida básicas, grátis.
- clipes: POST /openapi/v1/animations com rig_task_id e action_ids (até 10 por pedido).
Antes de cada pedido: saldo e custo previsto; se o total da protagonista passar do teto, para. O gasto conta os
40 créditos do corpo (meshy/corpo_meshy.json) e tudo o que este script pediu (estado fora do git; registro público
sem chave em assets/modelos/protagonista_v2/meshy/rig_meshy.json). Brutos em assets/modelos/protagonista_v2/meshy/rig/.

Uso (em tools/arte):
  uv run protagonista_v2/meshy_rig.py                        # saldo e gasto (não gasta)
  uv run protagonista_v2/meshy_rig.py --rig [--task-id ID]   # rig
  uv run protagonista_v2/meshy_rig.py --acoes 14,15,16 --nome corridas   # clipes sobre o rig feito
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
MESHY_DIR = ROOT / "assets/modelos/protagonista_v2/meshy"
MODEL = MESHY_DIR / "corpo_para_rig.glb"
OUT = MESHY_DIR / "rig"
RECORD = MESHY_DIR / "rig_meshy.json"
BODY_RECORD = MESHY_DIR / "corpo_meshy.json"
STATE_FILE = Path(__file__).with_name("estado_meshy_rig.json")
API = "https://api.meshy.ai/openapi"
COST_RIG, COST_ACTION, CAP = 5, 3, 300
HEIGHT_M = 0.80
POLL, TIMEOUT = 10, 30 * 60


class Meshy:
    def __init__(self, key):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {key}"

    def get(self, path):
        r = self.s.get(f"{API}{path}", timeout=60)
        r.raise_for_status()
        return r.json()

    def post(self, path, payload):
        r = self.s.post(f"{API}{path}", json=payload, timeout=180)
        if r.status_code >= 400:
            raise RuntimeError(f"{path}: {r.status_code} {r.text[:300]}")
        return r.json()["result"]

    def wait(self, path, task_id):
        start, last = time.time(), None
        while time.time() - start < TIMEOUT:
            task = self.get(f"{path}/{task_id}")
            if (task["status"], task.get("progress")) != last:
                print(f"    {task['status']} {task.get('progress', 0)}%", flush=True)
                last = (task["status"], task.get("progress"))
            if task["status"] in ("SUCCEEDED", "FAILED", "CANCELED", "EXPIRED"):
                return task
            time.sleep(POLL)
        raise TimeoutError(task_id)


def load_key():
    for env in (ROOT / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if env.exists():
            load_dotenv(env)
            break
    key = os.environ.get("MESHY_API_KEY")
    if not key:
        sys.exit("MESHY_API_KEY não encontrada no .env da raiz da worktree")
    return key


def fetch(url, path):
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    print(f"  baixado: {path.relative_to(ROOT)} ({len(r.content) // 1024} KB)")


def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"pedidos": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    MESHY_DIR.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps({"teto_protagonista": CAP, "pedidos": state["pedidos"]}, indent=2, ensure_ascii=False) + "\n")


def spent_total(state):
    body = json.loads(BODY_RECORD.read_text())["tarefas"] if BODY_RECORD.exists() else []
    return sum(t.get("creditos") or 0 for t in body) + sum(p.get("creditos") or 0 for p in state["pedidos"])


def guard(meshy, state, cost):
    balance = meshy.get("/v1/balance")["balance"]
    total = spent_total(state)
    print(f"saldo {balance}; gasto na protagonista {total}/{CAP}; este pedido ~{cost}")
    if total + cost > CAP:
        sys.exit(f"passaria do teto de {CAP} da protagonista: pare e avise o Diretor")
    if balance < cost:
        sys.exit("saldo menor que o custo previsto: pare e avise")
    return balance


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rig", action="store_true")
    p.add_argument("--task-id", help="rig sobre a tarefa da Meshy (input_task_id) em vez do corpo limpo")
    p.add_argument("--acoes", help="action_ids separados por vírgula (até 10)")
    p.add_argument("--nome", help="nome do arquivo dos clipes (ex.: corridas)")
    args = p.parse_args()
    meshy = Meshy(load_key())
    state = load_state()
    rig = next((x for x in state["pedidos"] if x["tipo"] == "rig" and x["status"] == "SUCCEEDED"), None)
    if not args.rig and not args.acoes:
        print(f"saldo {meshy.get('/v1/balance')['balance']}; gasto na protagonista {spent_total(state)}/{CAP}; "
              f"rig: {rig['task_id'] if rig else '-'}")
        return

    if args.rig:
        before = guard(meshy, state, COST_RIG)
        if args.task_id:
            payload = {"input_task_id": args.task_id, "height_meters": HEIGHT_M}
            desc = f"tarefa {args.task_id}"
        else:
            payload = {"model_url": "data:model/gltf-binary;base64," + base64.b64encode(MODEL.read_bytes()).decode(),
                       "height_meters": HEIGHT_M}
            desc = str(MODEL.relative_to(ROOT))
        print(f"rig: {desc}, height_meters {HEIGHT_M}")
        try:
            task_id = meshy.post("/v1/rigging", payload)
        except RuntimeError as e:  # recusa na criação: não cobra
            state["pedidos"].append({"tipo": "rig", "entrada": desc, "status": "RECUSADO", "creditos": 0, "erro": str(e)[:300]})
            save_state(state)
            sys.exit(f"rig recusado: {e}")
        rec = {"tipo": "rig", "entrada": desc, "task_id": task_id, "status": "PENDING", "saldo_antes": before}
        state["pedidos"].append(rec)
        save_state(state)
        task = meshy.wait("/v1/rigging", task_id)
        rec["saldo_depois"] = meshy.get("/v1/balance")["balance"]
        rec.update(status=task["status"], creditos=task.get("consumed_credits") if isinstance(task.get("consumed_credits"), int)
                   else before - rec["saldo_depois"], erro=(task.get("task_error") or {}).get("message") or None)
        save_state(state)
        if task["status"] != "SUCCEEDED":
            sys.exit(f"rig falhou: {rec['erro']} (créditos {rec['creditos']})")
        res = task["result"]
        fetch(res["rigged_character_glb_url"], OUT / "rig.glb")
        for key, name in (("walking_glb_url", "caminhada_basica.glb"), ("running_glb_url", "corrida_basica.glb")):
            if res.get("basic_animations", {}).get(key):
                fetch(res["basic_animations"][key], OUT / name)
        rig = rec

    if args.acoes:
        if not rig:
            sys.exit("sem rig pronto")
        ids = [int(x) for x in args.acoes.split(",")]
        if len(ids) > 10:
            sys.exit("no máximo 10 ações por pedido")
        before = guard(meshy, state, COST_ACTION * len(ids))
        name = args.nome or "clipes_" + "_".join(map(str, ids))
        task_id = meshy.post("/v1/animations", {"rig_task_id": rig["task_id"], "action_ids": ids})
        rec = {"tipo": "clipes", "nome": name, "action_ids": ids, "task_id": task_id, "status": "PENDING", "saldo_antes": before}
        state["pedidos"].append(rec)
        save_state(state)
        task = meshy.wait("/v1/animations", task_id)
        rec["saldo_depois"] = meshy.get("/v1/balance")["balance"]
        rec.update(status=task["status"], creditos=task.get("consumed_credits") if isinstance(task.get("consumed_credits"), int)
                   else before - rec["saldo_depois"], erro=(task.get("task_error") or {}).get("message") or None)
        save_state(state)
        if task["status"] != "SUCCEEDED":
            sys.exit(f"clipes falharam: {rec['erro']}")
        fetch(task["result"]["animation_glb_url"], OUT / f"{name}.glb")
        (OUT / f"{name}.json").write_text(json.dumps({"action_ids": ids, "result": task["result"]}, indent=2) + "\n")
    print(f"saldo final {meshy.get('/v1/balance')['balance']}; gasto na protagonista {spent_total(state)}/{CAP}")


if __name__ == "__main__":
    main()

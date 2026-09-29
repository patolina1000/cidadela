"""Passo 6: rig do Meshy no corpo limpo aprovado e dois clipes da biblioteca (idle e run).

Preços (docs.meshy.ai, 29/09/2026): rig 5 créditos; animação 3 por ação. Total previsto: 11 créditos.
- rig: POST /openapi/v1/rigging com model_url = data URI do GLB limpo (o personagem olha para +Z do glTF) e
  height_meters = 0,4. O resultado traz o GLB com rig e as animações básicas (walking, running) de graça.
- animações: POST /openapi/v1/animations com rig_task_id e action_ids [idle, run].
Brutos em assets/conceitos/aldeao_v2/meshy/rig/. Estado em estado_meshy_rig.json (fora do git). Nunca imprime a chave.

Uso:
  uv run meshy_rig.py --biblioteca run,jog,walk,idle     # lista ações da biblioteca (GET grátis) que batem
  uv run meshy_rig.py                                     # saldo e o que falta (não gasta)
  uv run meshy_rig.py --run --idle 0 --corrida 123        # rig (se faltar) + animações + download
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
BODY = ROOT / "assets/modelos/aldeao_v2/aldeao_corpo.glb"
OUT = ROOT / "assets/conceitos/aldeao_v2/meshy/rig"
STATE_FILE = Path(__file__).with_name("estado_meshy_rig.json")
API = "https://api.meshy.ai/openapi"
COST_RIG, COST_ACTION, LIMIT = 5, 3, 50
HEIGHT_M = 0.4
POLL, TIMEOUT = 10, 30 * 60


class Meshy:
    def __init__(self, key):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {key}"

    def get(self, path, **params):
        r = self.s.get(f"{API}{path}", params=params, timeout=60)
        r.raise_for_status()
        return r.json()

    def post(self, path, payload):
        r = self.s.post(f"{API}{path}", json=payload, timeout=120)
        if r.status_code >= 400:
            raise RuntimeError(f"{path}: {r.status_code} {r.text[:300]}")
        return r.json()["result"]

    def wait(self, path, task_id):
        start = time.time()
        while time.time() - start < TIMEOUT:
            task = self.get(f"{path}/{task_id}")
            print(f"    {task['status']} {task.get('progress', 0)}%", flush=True)
            if task["status"] in ("SUCCEEDED", "FAILED", "CANCELED", "EXPIRED"):
                return task
            time.sleep(POLL)
        raise TimeoutError(task_id)


def load_key():
    for env in (Path(__file__).resolve().parents[1] / ".env", ROOT / ".env"):
        if env.exists():
            load_dotenv(env)
            break
    key = os.environ.get("MESHY_API_KEY")
    if not key:
        sys.exit("MESHY_API_KEY não encontrada (tools/arte/.env ou .env na raiz)")
    return key


def fetch(url, path):
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    print(f"  baixado: {path.relative_to(ROOT)} ({len(r.content) // 1024} KB)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--biblioteca", help="palavras (separadas por vírgula) para filtrar a biblioteca de animações")
    p.add_argument("--run", action="store_true")
    p.add_argument("--idle", type=int, help="action_id do idle")
    p.add_argument("--corrida", type=int, help="action_id da corridinha")
    p.add_argument("--modelo", help="GLB a enviar no lugar do aldeao_corpo.glb (ex.: cópia a 1,0 m para a estimativa de pose)")
    p.add_argument("--altura", type=float, default=HEIGHT_M, help="height_meters enviado ao rig")
    p.add_argument("--task-id", help="rig sobre uma tarefa da própria Meshy (input_task_id), em vez de enviar o GLB limpo")
    args = p.parse_args()
    meshy = Meshy(load_key())

    if args.biblioteca:
        words = [w.strip().lower() for w in args.biblioteca.split(",")]
        library = meshy.get("/v1/animations/library")
        items = library if isinstance(library, list) else library.get("result", library)
        print(f"{len(items)} ações na biblioteca")
        for a in items:
            text = json.dumps(a, ensure_ascii=False).lower()
            if any(w in text for w in words):
                print(f"  {a.get('action_id'):>4}  {a.get('key') or a.get('name')}  | {a.get('category', '')} | {a.get('description', '')[:90]}")
        return

    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    print(f"saldo: {meshy.balance() if hasattr(meshy, 'balance') else meshy.get('/v1/balance')['balance']} créditos")
    spent = sum(t.get("creditos") or 0 for t in state.values())
    todo = [s for s in ("rig", "animacoes") if state.get(s, {}).get("status") != "SUCCEEDED"]
    print(f"gasto até agora nesta etapa: {spent}; a fazer: {todo or '-'}; previsão {COST_RIG * ('rig' in todo) + 2 * COST_ACTION * ('animacoes' in todo)} créditos (trava {LIMIT})")
    if not args.run or not todo:
        return
    if spent + COST_RIG + 2 * COST_ACTION > LIMIT:
        sys.exit("passaria da trava de créditos: pare e pergunte")

    if "rig" in todo:
        if args.task_id:
            print(f"rig: criando sobre a tarefa {args.task_id} (height_meters {args.altura})")
            task_id = meshy.post("/v1/rigging", {"input_task_id": args.task_id, "height_meters": args.altura})
            state["rig"] = {"task_id": task_id, "status": "PENDING", "input_task_id": args.task_id, "altura": args.altura}
        else:
            model = Path(args.modelo) if args.modelo else BODY
            uri = "data:model/gltf-binary;base64," + base64.b64encode(model.read_bytes()).decode()
            print(f"rig: criando ({model.name}, height_meters {args.altura})")
            task_id = meshy.post("/v1/rigging", {"model_url": uri, "height_meters": args.altura})
            state["rig"] = {"task_id": task_id, "status": "PENDING", "modelo": str(model), "altura": args.altura}
        STATE_FILE.write_text(json.dumps(state, indent=2))
        task = meshy.wait("/v1/rigging", task_id)
        state["rig"].update(status=task["status"], creditos=task.get("consumed_credits"), erro=(task.get("task_error") or {}).get("message"))
        if task["status"] != "SUCCEEDED":
            STATE_FILE.write_text(json.dumps(state, indent=2))
            sys.exit(f"rig falhou: {state['rig']['erro']}")
        res = task["result"]
        fetch(res["rigged_character_glb_url"], OUT / "rig.glb")
        for key, name in (("walking_glb_url", "walking_basico.glb"), ("running_glb_url", "running_basico.glb")):
            if res.get("basic_animations", {}).get(key):
                fetch(res["basic_animations"][key], OUT / name)
        STATE_FILE.write_text(json.dumps(state, indent=2))

    if "animacoes" in todo:
        if args.idle is None or args.corrida is None:
            sys.exit("passe --idle e --corrida (action_id da biblioteca)")
        print(f"animações: idle {args.idle}, corrida {args.corrida}")
        task_id = meshy.post("/v1/animations", {"rig_task_id": state["rig"]["task_id"], "action_ids": [args.idle, args.corrida]})
        state["animacoes"] = {"task_id": task_id, "status": "PENDING", "idle": args.idle, "corrida": args.corrida}
        STATE_FILE.write_text(json.dumps(state, indent=2))
        task = meshy.wait("/v1/animations", task_id)
        state["animacoes"].update(status=task["status"], creditos=task.get("consumed_credits"), erro=(task.get("task_error") or {}).get("message"))
        STATE_FILE.write_text(json.dumps(state, indent=2))
        if task["status"] != "SUCCEEDED":
            sys.exit(f"animações falharam: {state['animacoes']['erro']}")
        fetch(task["result"]["animation_glb_url"], OUT / "animacoes.glb")
        (OUT / "animacoes.json").write_text(json.dumps({"idle": args.idle, "run": args.corrida, "result": task["result"]}, indent=2))
    print(f"saldo final: {meshy.get('/v1/balance')['balance']} créditos")


if __name__ == "__main__":
    main()

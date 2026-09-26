"""Pipeline de assets da Meshy: gera, texturiza, faz rig e anima, e baixa os GLB.

Lê tools/assets.json. Para cada asset:
- personagem com imagens: Multi-Image to 3D (malha + textura) -> rig -> animações;
- personagem por texto: Text to 3D preview (Smart Topology) -> refine -> rig -> animações;
- construção e recurso: Text to 3D preview (Smart Topology) -> refine.
Os arquivos brutos vão para assets/modelos/<nome>/bruto/; a padronização é do Blender.

O estado (IDs das tarefas e créditos) fica em state.json, então rodar de novo continua
de onde parou sem pagar de novo. A chave vem do .env e nunca é impressa.

Uso:
  uv run pipeline.py                      # só mostra saldo e estimativa (não gasta)
  uv run pipeline.py --run                # gera tudo o que falta
  uv run pipeline.py --run --only protagonista
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

ROOT = Path(__file__).resolve().parents[2]
ASSETS_FILE = ROOT / "tools/assets.json"
STATE_FILE = Path(__file__).with_name("state.json")
MODELS_DIR = ROOT / "assets/modelos"

API = "https://api.meshy.ai/openapi"
POLL_SECONDS = 10
TIMEOUT_SECONDS = 30 * 60
MAX_ATTEMPTS = 2  # a tentativa original + uma nova

# Preços da API em créditos (docs.meshy.ai/api/pricing, setembro de 2026).
COST_MULTI_IMAGE_TEXTURED = 30
COST_SMART_TOPOLOGY_PREVIEW = 5
COST_REFINE = 10
COST_RIG = 5
COST_PER_ACTION = 3

# Altura aproximada informada ao rig: o rig acerta melhor com a proporção de uma pessoa;
# a escala do jogo é aplicada depois, no Blender.
RIG_HEIGHT_METERS = 1.4


class BudgetExceeded(Exception):
    pass


class Meshy:
    def __init__(self, api_key: str):
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {api_key}"

    def _check(self, response: requests.Response) -> dict:
        if not response.ok:
            # Só a mensagem da API; nunca os cabeçalhos da requisição.
            raise RuntimeError(f"HTTP {response.status_code} em {response.url}: {response.text[:500]}")
        return response.json()

    def get(self, path: str, **params) -> dict:
        return self._check(self._session.get(f"{API}{path}", params=params, timeout=60))

    def post(self, path: str, payload: dict) -> str:
        return self._check(self._session.post(f"{API}{path}", json=payload, timeout=120))["result"]

    def balance(self) -> int:
        return self.get("/v1/balance")["balance"]

    def wait(self, path: str, task_id: str) -> dict:
        start = time.monotonic()
        last_progress = None
        while True:
            task = self.get(f"{path}/{task_id}")
            status = task["status"]
            if status in ("SUCCEEDED", "FAILED", "CANCELED"):
                return task
            if task.get("progress") != last_progress:
                last_progress = task.get("progress")
                print(f"      {status} {last_progress}%", flush=True)
            if time.monotonic() - start > TIMEOUT_SECONDS:
                raise TimeoutError(f"tarefa {task_id} passou de {TIMEOUT_SECONDS // 60} min")
            time.sleep(POLL_SECONDS)


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def charged_credits(state: dict) -> int:
    """Créditos já cobrados; tarefas ainda rodando contam pelo preço estimado."""
    total = 0
    for steps in state.values():
        for step in steps.values():
            for attempt in step.get("attempts", []):
                total += attempt.get("credits", attempt.get("estimate", 0))
    return total


def data_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def is_character(asset: dict) -> bool:
    return asset["tipo"] == "personagem"


def plan_steps(asset: dict) -> list[tuple[str, int]]:
    """Etapas de um asset e o custo estimado de cada uma."""
    if asset.get("fonte") == "multi_imagem":
        steps = [("modelo", COST_MULTI_IMAGE_TEXTURED)]
    else:
        steps = [("malha", COST_SMART_TOPOLOGY_PREVIEW), ("modelo", COST_REFINE)]
    if is_character(asset):
        steps += [("rig", COST_RIG), ("animacoes", COST_PER_ACTION * len(asset["animacoes"]))]
    return steps


class Runner:
    def __init__(self, meshy: Meshy, config: dict, state: dict):
        self._meshy = meshy
        self._config = config
        self._state = state
        self._limit = config["limite_creditos"]

    def prompt(self, asset: dict) -> str:
        return self._config["estilo"].replace("[OBJETO]", asset["objeto"])

    def payload(self, asset: dict, step: str) -> tuple[str, dict]:
        done = self._state[asset["nome"]]
        if step == "modelo" and asset.get("fonte") == "multi_imagem":
            return "/v1/multi-image-to-3d", {
                "image_urls": [data_uri(ROOT / p) for p in asset["imagens"]],
                "ai_model": "latest",
                "should_texture": True,
                "texture_resolution": "2k",
                "image_enhancement": False,  # preservar o conceito, sem reinterpretar o estilo
                "remove_lighting": True,
                "should_remesh": True,
                "topology": "triangle",
                "target_polycount": asset["polycount"],
                "pose_mode": "t-pose",
                "target_formats": ["glb"],
            }
        if step == "malha":
            body = {
                "mode": "preview",
                "prompt": self.prompt(asset),
                "model_type": "smart-topology",
                "ai_model": "meshy-t2",
                "target_polycount": asset["polycount"],
                "target_formats": ["glb"],
            }
            if is_character(asset):
                body["pose_mode"] = "t-pose"
            return "/v2/text-to-3d", body
        if step == "modelo":
            return "/v2/text-to-3d", {
                "mode": "refine",
                "preview_task_id": done["malha"]["task_id"],
                "texture_resolution": "2k",
                "target_formats": ["glb"],
            }
        if step == "rig":
            return "/v1/rigging", {
                "input_task_id": done["modelo"]["task_id"],
                "height_meters": RIG_HEIGHT_METERS,
            }
        if step == "animacoes":
            return "/v1/animations", {
                "rig_task_id": done["rig"]["task_id"],
                "action_ids": list(asset["animacoes"].values()),
            }
        raise ValueError(step)

    def run_step(self, asset: dict, step: str, cost: int) -> dict | None:
        """Roda (ou retoma) uma etapa. Devolve a tarefa concluída, ou None se falhou de vez."""
        record = self._state.setdefault(asset["nome"], {}).setdefault(step, {"attempts": []})
        if record.get("status") == "SUCCEEDED":
            return record["task"]
        path, _ = self.payload(asset, step)

        while True:
            pending = record["attempts"] and "credits" not in record["attempts"][-1]
            if not pending:
                if len(record["attempts"]) >= MAX_ATTEMPTS:
                    record["status"] = "FAILED"
                    save_state(self._state)
                    return None
                spent = charged_credits(self._state)
                if spent + cost > self._limit:
                    raise BudgetExceeded(
                        f"{asset['nome']}/{step} custaria {cost}; já gastos {spent} de {self._limit}")
                _, body = self.payload(asset, step)
                task_id = self._meshy.post(path, body)
                record["attempts"].append({"task_id": task_id, "estimate": cost})
                save_state(self._state)
                print(f"    {step}: tarefa criada ({cost} créditos estimados)", flush=True)
            attempt = record["attempts"][-1]
            task = self._meshy.wait(path, attempt["task_id"])
            attempt["credits"] = task.get("consumed_credits", 0)
            attempt["status"] = task["status"]
            if task["status"] == "SUCCEEDED":
                record.update(status="SUCCEEDED", task_id=attempt["task_id"], task=task)
                save_state(self._state)
                print(f"    {step}: ok ({attempt['credits']} créditos)", flush=True)
                return task
            error = (task.get("task_error") or {}).get("message", "sem mensagem")
            attempt["error"] = error
            save_state(self._state)
            print(f"    {step}: {task['status']} ({error})", flush=True)

    def run_asset(self, asset: dict) -> bool:
        print(f"\n== {asset['nome']}", flush=True)
        results = {}
        for step, cost in plan_steps(asset):
            try:
                task = self.run_step(asset, step, cost)
            except BudgetExceeded:
                raise
            except Exception as error:  # rede, HTTP 4xx: registra e segue para o próximo asset
                print(f"    {step}: erro: {error}", flush=True)
                return False
            if task is None:
                print(f"    {step}: falhou duas vezes, seguindo para o próximo asset", flush=True)
                return False
            results[step] = task
        download(self._meshy, asset, results)
        return True


def fetch(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with path.open("wb") as file:
            for chunk in response.iter_content(1 << 16):
                file.write(chunk)
    print(f"    baixado {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)", flush=True)


def download(meshy: Meshy, asset: dict, results: dict) -> None:
    raw = MODELS_DIR / asset["nome"] / "bruto"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / ".gdignore").touch()  # o Godot importa só o GLB padronizado, não os brutos
    fetch(results["modelo"]["model_urls"]["glb"], raw / "modelo.glb")
    if not is_character(asset):
        return
    fetch(results["rig"]["result"]["rigged_character_glb_url"], raw / "rig.glb")
    fetch(results["animacoes"]["result"]["animation_glb_url"], raw / "animacoes.glb")
    # Os clipes vêm com o nome da biblioteca; o Blender troca pelos nossos (idle, walk...).
    ids = ",".join(str(i) for i in asset["animacoes"].values())
    library = {a["action_id"]: a["name"] for a in meshy.get("/v1/animations/library", action_ids=ids)}
    clips = {library[action_id]: ours for ours, action_id in asset["animacoes"].items()}
    (raw / "animacoes.json").write_text(json.dumps(clips, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="gera de verdade (gasta créditos)")
    parser.add_argument("--only", nargs="*", help="nomes dos assets a processar")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("MESHY_API_KEY")
    if not api_key:
        sys.exit("MESHY_API_KEY não encontrada no .env")
    meshy = Meshy(api_key)
    config = json.loads(ASSETS_FILE.read_text())
    state = load_state()
    assets = [a for a in config["assets"] if not args.only or a["nome"] in args.only]
    if args.only and len(assets) != len(args.only):
        sys.exit(f"asset desconhecido em {args.only}")

    spent = charged_credits(state)
    todo = 0
    print(f"Saldo na Meshy: {meshy.balance()} créditos")
    for asset in assets:
        done = state.get(asset["nome"], {})
        missing = [(s, c) for s, c in plan_steps(asset) if done.get(s, {}).get("status") != "SUCCEEDED"]
        cost = sum(c for _, c in missing)
        todo += cost
        print(f"  {asset['nome']:<16} {cost:>4} créditos  ({', '.join(s for s, _ in missing) or 'pronto'})")
    print(f"Estimativa: {todo} créditos. Já gastos neste lote: {spent}. Limite: {config['limite_creditos']}.")
    if not args.run:
        print("Nada foi gerado. Use --run para gerar.")
        return

    runner = Runner(meshy, config, state)
    failed = []
    try:
        for asset in assets:
            if not runner.run_asset(asset):
                failed.append(asset["nome"])
    except BudgetExceeded as error:
        print(f"\nPARADO pelo limite de créditos: {error}")
    print(f"\nGastos neste lote: {charged_credits(state)} créditos. Saldo: {meshy.balance()}.")
    if failed:
        print(f"Falharam: {', '.join(failed)}")


if __name__ == "__main__":
    main()

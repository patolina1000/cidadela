"""Confere e corrige o .import de GLBs com animação pelo contrato de animação (docs/animacao_contrato.md):
- animation/fps = 24 (o Godot não reamostra os clipes feitos a 24 fps);
- animation/remove_immutable_tracks = false (todo clipe define a pose inteira: sem isso o importador apaga as trilhas
  que não mudam e o osso congela na pose do clipe anterior);
- otimizador de animação desligado: _subresources → "nodes" → "PATH:AnimationPlayer" → "optimizer/enabled": false
  (o otimizador tira chaves).
O resto do .import fica como está. O .import precisa existir (gerado pelo Godot: godot --headless --import); depois
de corrigir, reimporte o GLB (apague o cache dele em .godot/imported e rode o import de novo).

Uso (Python 3, sem dependências):
  python3 tools/arte/godot_import.py conferir <arquivo.glb> [...]   só lista o que está fora do contrato (sai com 1 se houver)
  python3 tools/arte/godot_import.py corrigir <arquivo.glb> [...]   escreve o que falta e confere de novo
  Opção --no <caminho>: caminho do AnimationPlayer na cena importada (padrão: AnimationPlayer, filho da raiz).
"""

import json
import re
import sys
from pathlib import Path

FPS = 24
PARAMS = {"animation/fps": str(FPS), "animation/remove_immutable_tracks": "false"}
OPTIMIZER_KEY = "optimizer/enabled"


def split_subresources(text: str) -> tuple:
    """(início, valor, fim) do parâmetro _subresources, que pode ocupar várias linhas (chaves balanceadas)."""
    m = re.search(r"^_subresources=", text, re.M)
    if not m:
        raise ValueError("sem _subresources no .import")
    i = m.end()
    depth, j, in_str = 0, i, False
    while j < len(text):
        ch = text[j]
        if in_str:
            if ch == "\\":
                j += 1
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[:i], text[i:j + 1], text[j + 1:]
        j += 1
    raise ValueError("_subresources sem fechar")


def to_godot(value, level=0) -> str:
    """Dicionário no formato em que o Godot grava o _subresources (uma chave por linha, sem recuo)."""
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{json.dumps(k)}: {to_godot(v, level + 1)}" for k, v in value.items()]
        return "{\n" + ",\n".join(items) + "\n}"
    return json.dumps(value)


def parse_subresources(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:  # tipos do Godot (Vector3(...), Transform3D(...)) não são JSON
        raise ValueError(f"_subresources com valores que este script não sabe ler ({e}); corrija à mão") from e


def param(text: str, key: str):
    m = re.search(rf"^{re.escape(key)}=(.*)$", text, re.M)
    return m.group(1) if m else None


def problems(text: str, node: str) -> list:
    out = []
    for key, want in PARAMS.items():
        have = param(text, key)
        if have != want:
            out.append(f"{key} = {have} (contrato: {want})")
    subs = parse_subresources(split_subresources(text)[1])
    opt = subs.get("nodes", {}).get(f"PATH:{node}", {}).get(OPTIMIZER_KEY)
    if opt is not False:
        out.append(f'_subresources → nodes → "PATH:{node}" → "{OPTIMIZER_KEY}" = {opt} (contrato: false)')
    return out


def fix(text: str, node: str) -> str:
    for key, want in PARAMS.items():
        if param(text, key) is None:
            raise ValueError(f"sem {key} no .import (gerado por outra versão do Godot?)")
        text = re.sub(rf"^{re.escape(key)}=.*$", f"{key}={want}", text, count=1, flags=re.M)
    head, raw, tail = split_subresources(text)
    subs = parse_subresources(raw)
    subs.setdefault("nodes", {}).setdefault(f"PATH:{node}", {})[OPTIMIZER_KEY] = False
    return head + to_godot(subs) + tail


def main() -> int:
    args = sys.argv[1:]
    node = "AnimationPlayer"
    if "--no" in args:
        k = args.index("--no")
        node = args[k + 1]
        del args[k:k + 2]
    if len(args) < 2 or args[0] not in ("conferir", "corrigir"):
        print(__doc__)
        return 2
    mode, files = args[0], [Path(a) for a in args[1:]]
    bad = 0
    for glb in files:
        imp = glb.with_name(glb.name + ".import")
        if not imp.exists():
            print(f"{glb}: sem .import (rode o Godot sem janela: godot --headless --import --path <projeto>)")
            bad += 1
            continue
        text = imp.read_text()
        try:
            found = problems(text, node)
            if mode == "corrigir" and found:
                new = fix(text, node)
                imp.write_text(new)
                fixed = found
                found = problems(new, node)
                print(f"{glb}: corrigido ({'; '.join(fixed)})")
        except ValueError as e:
            print(f"{glb}: ERRO {e}")
            bad += 1
            continue
        if found:
            bad += 1
            print(f"{glb}: fora do contrato: " + "; ".join(found))
        elif mode == "conferir":
            print(f"{glb}: ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

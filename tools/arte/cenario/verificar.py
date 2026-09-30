"""Confere os GLBs do cenário contra as regras do rascunho de contrato e mede se um LOD próprio faria diferença.

Lê o GLB direto (JSON + binário do glTF, sem Blender), como o importador do Godot lê. Para cada arquivo:
  - uma malha, um nó, sem esqueleto, animação nem textura; transformação do nó identidade (metros, sem escala);
  - materiais só com nomes de papel (tronco, copa, pedra, minerio, madeira, musgo) e cor no baseColorFactor;
  - pivô no centro da base: nada abaixo de y = -0,06 (a árvore inclinada enterra o pé do lado para onde tomba), e o
    centro da caixa dos vértices da base (y < 5 cm) a menos de 12 cm da origem;
  - pegada (x, z) e altura, triângulos;
  - tamanho dos triângulos na tela no zoom 0,4 (o mais longe), para decidir o LOD.
Frente +Z: o exportador grava com Y para cima e +Z à frente (export_yup); o objeto aceita qualquer giro em Y, então
não há "lado de frente" a conferir além da transformação identidade.

Uso: uv run --project tools/arte tools/arte/cenario/verificar.py
Saída: assets/cenario/verificacao.json e um resumo na tela; sai com erro se alguma regra falhar.
"""

import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PAPEIS = {"tronco", "copa", "pedra", "minerio", "madeira", "musgo"}
PX_POR_M_ZOOM_04 = 47.0  # 3024×1890, FOV 45°, 40 m de distância: ~47 px por metro no chão perto do centro
COMPONENTES = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
TAMANHO = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path):
    data = path.read_bytes()
    assert data[:4] == b"glTF", "não é GLB"
    n = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + n])
    off = 20 + n
    blen = struct.unpack_from("<I", data, off)[0]
    return gltf, data[off + 8:off + 8 + blen]


def accessor(gltf, binary, idx):
    a = gltf["accessors"][idx]
    v = gltf["bufferViews"][a["bufferView"]]
    dtype = COMPONENTES[a["componentType"]]
    k = TAMANHO[a["type"]]
    start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    arr = np.frombuffer(binary, dtype=dtype, count=a["count"] * k, offset=start)
    return arr.reshape(a["count"], k) if k > 1 else arr


def check(path):
    gltf, binary = read_glb(path)
    erros = []
    if len(gltf.get("meshes", [])) != 1:
        erros.append(f"{len(gltf.get('meshes', []))} malhas")
    if len(gltf.get("nodes", [])) != 1:
        erros.append(f"{len(gltf.get('nodes', []))} nós")
    for chave in ("skins", "animations", "textures", "images"):
        if gltf.get(chave):
            erros.append(f"tem {chave}")
    node = gltf["nodes"][0]
    for chave, ident in (("translation", [0, 0, 0]), ("rotation", [0, 0, 0, 1]), ("scale", [1, 1, 1])):
        if chave in node and not np.allclose(node[chave], ident, atol=1e-6):
            erros.append(f"nó com {chave} {node[chave]}")
    mats = [m.get("name", "") for m in gltf.get("materials", [])]
    fora = [m for m in mats if m not in PAPEIS]
    if fora:
        erros.append(f"materiais fora do contrato: {fora}")
    cores = {m.get("name"): m.get("pbrMetallicRoughness", {}).get("baseColorFactor") for m in gltf["materials"]}
    pos, tris = [], []
    base = 0
    for prim in gltf["meshes"][0]["primitives"]:
        p = accessor(gltf, binary, prim["attributes"]["POSITION"]).astype(np.float64)
        i = accessor(gltf, binary, prim["indices"]).astype(np.int64).reshape(-1, 3)
        pos.append(p)
        tris.append(i + base)
        base += len(p)
    pos, tris = np.vstack(pos), np.vstack(tris)
    lo, hi = pos.min(axis=0), pos.max(axis=0)
    if lo[1] < -0.06:
        erros.append(f"desce a y = {lo[1]:.3f}")
    pe = pos[pos[:, 1] < 0.05]
    centro_base = ((pe[:, [0, 2]].min(axis=0) + pe[:, [0, 2]].max(axis=0)) / 2 if len(pe)
                   else np.array([np.nan, np.nan]))
    if np.hypot(*centro_base) > 0.12:
        erros.append(f"centro da base a {np.hypot(*centro_base):.2f} m da origem")
    a, b, c = pos[tris[:, 0]], pos[tris[:, 1]], pos[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    px2 = area * PX_POR_M_ZOOM_04 ** 2  # área real em px² no zoom 0,4, sem o encurtamento da inclinação
    return {
        "arquivo": str(path.relative_to(ROOT)),
        "triangulos": int(len(tris)),
        "altura_m": round(float(hi[1]), 3),
        "enterrado_m": round(float(-lo[1]), 3),
        "raio_m": round(float(np.hypot(pos[:, 0], pos[:, 2]).max()), 3),  # maior alcance no chão, em qualquer giro
        "pegada_x_m": [round(float(lo[0]), 3), round(float(hi[0]), 3)],
        "pegada_z_m": [round(float(lo[2]), 3), round(float(hi[2]), 3)],
        "centro_base_m": [round(float(x), 3) for x in centro_base],
        "materiais": {m: [round(x, 4) for x in (cores[m] or [])] for m in mats},
        "tri_px2_zoom_04": {"mediana": round(float(np.median(px2)), 1), "p10": round(float(np.percentile(px2, 10)), 1)},
        "erros": erros,
    }


def main():
    glbs = sorted((ROOT / "assets/cenario").rglob("*.glb"))
    out = [check(p) for p in glbs]
    (ROOT / "assets/cenario/verificacao.json").write_text(json.dumps(
        {"fonte": "tools/arte/cenario/verificar.py", "arquivos": out}, ensure_ascii=False, indent=2) + "\n")
    falhas = 0
    for r in out:
        ok = "ok" if not r["erros"] else "ERRO " + "; ".join(r["erros"])
        falhas += bool(r["erros"])
        print(f"{Path(r['arquivo']).name:14} {r['triangulos']:4} tri  {r['altura_m']:.2f} m  "
              f"x {r['pegada_x_m']}  z {r['pegada_z_m']}  base {r['centro_base_m']}  "
              f"tri no zoom 0,4: mediana {r['tri_px2_zoom_04']['mediana']} px², p10 {r['tri_px2_zoom_04']['p10']}  {ok}")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()

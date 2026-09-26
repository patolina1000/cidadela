"""Texturas do chão: gera na Text to Image da Meshy, deixa repetível sem emenda e confere.

Lê tools/texturas.json. Para cada textura:
1. gera a imagem (bruta em assets/texturas/chao/bruto/, fora do git);
2. nivela manchas grandes de cor (senão a repetição forma listras) e deixa repetível: mistura a imagem com três cópias deslocadas em meia imagem (na horizontal, na
   vertical e nas duas), cada uma com peso zero onde ela tem emenda; cores misturam suave e o
   detalhe fino vem da cópia dominante, com fronteira orgânica; a original fica no centro;
3. reduz para 512 px e mede a emenda; reprova sozinha e gera de novo até "tentativas" vezes;
4. salva assets/texturas/chao/<nome>.png, a prévia 4x4 em assets/previews/piso/ e, se pedido,
   a máscara de emissão (<nome>_emissao.png).

Uso:
  uv run textures.py                 # saldo e estimativa (não gasta)
  uv run textures.py --run           # gera o que falta
  uv run textures.py --reprocess     # refaz só o passo 2 em diante com as imagens já baixadas
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from PIL import Image, ImageFilter

from pipeline import ROOT, Meshy, fetch

CONFIG_FILE = ROOT / "tools/texturas.json"
STATE_DIR = Path(__file__).parent
# Cada versão das texturas tem seu estado e seu orçamento (os créditos das versões antigas não contam).
STATE_FILE = STATE_DIR / "textures_state_v1.json"
TEXTURE_DIR = ROOT / "assets/texturas/chao"
RAW_DIR = TEXTURE_DIR / "bruto"
PREVIEW_DIR = ROOT / "assets/previews/piso"

COST_PER_IMAGE = {"nano-banana": 3, "nano-banana-2": 6, "nano-banana-pro": 9}
WORK_SIZE = 1024
BLEND_FRACTION = 0.14  # meia largura da faixa mesclada, em fração do lado
NOISE_CELLS = 6  # granulação do ruído que entorta a fronteira da mescla
DETAIL_BLUR = 6  # px: abaixo disso é "detalhe", acima é "cor"
PREVIEW_TILE = 384  # px de cada repetição na prévia 4x4
# Reprovação: junta mais forte que quase todas as linhas da própria textura, ou faixa misturada borrada.
MAX_SEAM_PERCENTILE = 95
FRAME_FLATNESS = 0.3  # borda com menos que isso da variação do interior = moldura lisa
FRAME_STEP = 0.12  # ou borda com brilho bem diferente do interior (moldura clara ou escura)
RAW_TILEABLE_PERCENTILE = 60  # a IA às vezes já entrega repetível: aí não mistura (misturar tábuas desalinha as linhas)
MIN_BAND_CONTRAST = 0.80
FLATTEN_FRACTION = 0.25  # manchas maiores que isso (em fração do lado) contam como "iluminação"
FLATTEN_STRENGTH = 0.75  # quanto dessas manchas sai, para a repetição 4x4 não formar listras
MASK_SOFTNESS = 0.08  # distância de cor (0..1) em que a máscara de emissão vai de 1 a 0


def use_version(version: str) -> None:
    global STATE_FILE
    STATE_FILE = STATE_DIR / f"textures_state_{version}.json"


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def spent(state: dict) -> int:
    return sum(a.get("credits", a.get("estimate", 0)) for t in state.values() for a in t.get("attempts", []))


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def tileable_noise(size: int, seed: int) -> np.ndarray:
    """Ruído suave em -1..1 que também se repete sem emenda (grade aleatória ampliada com borda em volta)."""
    rng = np.random.default_rng(seed)
    cells = rng.uniform(0, 255, (NOISE_CELLS, NOISE_CELLS)).astype(np.uint8)
    wrapped = np.pad(cells, 1, mode="wrap")
    scale = size / NOISE_CELLS
    big = Image.fromarray(wrapped, "L").resize((round(scale * (NOISE_CELLS + 2)),) * 2, Image.BICUBIC)
    offset = round(scale)
    return np.asarray(big, dtype=np.float32)[offset:offset + size, offset:offset + size] / 127.5 - 1.0


def blur(image: np.ndarray, radius: float) -> np.ndarray:
    """Desfoque gaussiano com borda em volta (a textura é periódica)."""
    pad = int(radius * 3)
    wrapped = np.pad(image, ((pad, pad), (pad, pad), (0, 0)), mode="wrap")
    pil = Image.fromarray(np.clip(wrapped * 255, 0, 255).astype(np.uint8), "RGB")
    out = np.asarray(pil.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255
    return out[pad:-pad, pad:-pad]


def flatten(image: np.ndarray) -> np.ndarray:
    """Tira boa parte da variação de cor em grande escala, mantendo detalhe e cor média.

    Uma mancha clara de um lado e escura do outro, repetida, vira listra mesmo sem emenda.
    """
    size = image.shape[0]
    large = blur(image, size * FLATTEN_FRACTION / 3)
    return np.clip(image - FLATTEN_STRENGTH * (large - image.mean(axis=(0, 1))), 0, 1)


def make_seamless(image: np.ndarray, seed: int) -> np.ndarray:
    """Mistura a imagem com três cópias deslocadas em meia imagem, sem emenda em lugar nenhum.

    Cada cópia tem emenda em duas linhas (a original nas bordas; a deslocada na horizontal na coluna
    do meio e na borda de cima; etc.). O peso de cada cópia é o produto de a() ou b() em x e em y,
    que valem zero exatamente nessas linhas; o ruído só entorta a fronteira longe delas. A cor é
    misturada; o detalhe fino vem inteiro da cópia de maior peso, para não virar borrão.
    """
    size = image.shape[0]
    half = size // 2
    band = size * BLEND_FRACTION
    coords = np.arange(size, dtype=np.float32)
    from_edge = np.minimum(coords, size - coords)  # distância até a borda (a emenda da original)
    noise_x, noise_y = tileable_noise(size, seed), tileable_noise(size, seed + 1)
    # a = peso de "longe da borda" (vale 0 na borda); b = 1 - a vale 0 no meio (onde a cópia deslocada tem emenda).
    a_x = smoothstep(0, band, from_edge[None, :] * (1 + 0.5 * noise_x))
    a_y = smoothstep(0, band, from_edge[:, None] * (1 + 0.5 * noise_y))
    copies = [
        (image, a_x * a_y),
        (np.roll(image, half, axis=1), (1 - a_x) * a_y),
        (np.roll(image, half, axis=0), a_x * (1 - a_y)),
        (np.roll(image, (half, half), axis=(0, 1)), (1 - a_x) * (1 - a_y)),
    ]
    color = sum(blur(c, DETAIL_BLUR) * w[..., None] for c, w in copies)
    dominant = np.argmax(np.stack([w for _, w in copies]), axis=0)
    details = np.stack([c - blur(c, DETAIL_BLUR) for c, _ in copies])
    detail = np.take_along_axis(details, dominant[None, ..., None], axis=0)[0]
    return np.clip(color + detail, 0, 1)


def luminance(image: np.ndarray) -> np.ndarray:
    return image[..., 0] * 0.299 + image[..., 1] * 0.587 + image[..., 2] * 0.114


def seam_metrics(texture: np.ndarray) -> dict:
    """Percentil do degrau na junta entre repetições, entre todos os degraus de coluna (e de linha)
    vizinha da própria imagem; e contraste de detalhe na faixa misturada (bordas) contra o centro.

    Tábuas, rachaduras e juntas também fazem linhas fortes: por isso a junta é comparada com as
    outras linhas da mesma textura, e só reprova se for mais forte que quase todas.
    """
    lum = luminance(texture)
    size = lum.shape[0]
    percentiles = []
    for axis in (1, 0):
        wrapped = np.concatenate([lum, np.take(lum, [0], axis=axis)], axis=axis)
        steps = np.abs(np.diff(wrapped, axis=axis)).mean(axis=1 - axis)
        junction = steps[-1]  # última coluna (ou linha) com a primeira: a junta entre repetições
        percentiles.append(float((steps < junction).mean() * 100))
    detail = luminance(texture - blur(texture, 2))
    edge = int(size * BLEND_FRACTION * 0.6)
    band = np.zeros_like(lum, dtype=bool)
    band[:edge, :] = band[-edge:, :] = band[:, :edge] = band[:, -edge:] = True
    core = np.zeros_like(band)
    core[size // 4:-size // 4, size // 4:-size // 4] = True
    outer, inner = ring(size, 0, 0.03), ring(size, 0.06, 0.15)
    framed = (lum[outer].std() < FRAME_FLATNESS * lum[inner].std()
              or abs(lum[outer].mean() - lum[inner].mean()) > FRAME_STEP)
    return {
        "moldura": bool(framed),
        "percentil_junta": round(max(percentiles), 1),
        "contraste_faixa": round(float(detail[band].std() / detail[core].std()), 3),
    }


def ring(size: int, start: float, end: float) -> np.ndarray:
    """Máscara do anel entre <start> e <end> (fração do lado) a partir da borda."""
    def square(fraction: float) -> np.ndarray:
        mask = np.zeros((size, size), dtype=bool)
        cut = int(fraction * size)
        mask[cut:size - cut, cut:size - cut] = True
        return mask
    return square(start) & ~square(end)


def passes(metrics: dict) -> bool:
    if metrics.get("placa"):
        return True
    return (not metrics["moldura"] and metrics["percentil_junta"] <= MAX_SEAM_PERCENTILE
            and metrics["contraste_faixa"] >= MIN_BAND_CONTRAST)


def emission_mask(texture: np.ndarray, hex_color: str) -> np.ndarray:
    """Máscara das runas: pixels perto da cor delas e claros (as runas brilham; a pedra é escura)."""
    target = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255
    distance = np.linalg.norm(texture - target, axis=-1) / np.sqrt(3)
    near = 1 - smoothstep(MASK_SOFTNESS, MASK_SOFTNESS * 2.5, distance)
    bright = smoothstep(0.25, 0.45, luminance(texture))
    mask = blur(np.repeat((near * bright)[..., None], 3, axis=-1), 1)[..., 0]
    lit = mask[mask > 0.05]
    # As runas acesas chegam a 1: o brilho final é trabalho do jogo (força da emissão), não da máscara.
    return np.clip(mask / np.percentile(lit, 90), 0, 1) if lit.size else mask


def recolor(texture: np.ndarray, dark_hex: str, light_hex: str) -> np.ndarray:
    """Repinta a textura com um degradê entre duas cores, mantendo as pinceladas (o claro e escuro).

    O brilho de cada pixel (normalizado entre os percentis 2 e 98) escolhe a cor no degradê.
    """
    def rgb(hex_color: str) -> np.ndarray:
        return np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255
    lum = luminance(texture)
    low, high = np.percentile(lum, (2, 98))
    t = np.clip((lum - low) / max(high - low, 1e-6), 0, 1)[..., None]
    return rgb(dark_hex) * (1 - t) + rgb(light_hex) * t


def save_png(array: np.ndarray, path: Path, mode: str = "RGB") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(array * 255, 0, 255).round().astype(np.uint8), mode).save(path)


def preview(texture: Image.Image, name: str) -> Path:
    tile = texture.resize((PREVIEW_TILE, PREVIEW_TILE), Image.LANCZOS)
    sheet = Image.new("RGB", (PREVIEW_TILE * 4, PREVIEW_TILE * 4))
    for x in range(4):
        for y in range(4):
            sheet.paste(tile, (x * PREVIEW_TILE, y * PREVIEW_TILE))
    path = PREVIEW_DIR / f"{name}_4x4.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=90)
    return path


def process(entry: dict, raw_path: Path, size: int) -> tuple[Image.Image, dict]:
    raw = Image.open(raw_path).convert("RGB")
    side = min(raw.size)  # recorta ao centro se não vier quadrada
    left, top = (raw.width - side) // 2, (raw.height - side) // 2
    raw = raw.crop((left, top, left + side, top + side)).resize((WORK_SIZE, WORK_SIZE), Image.LANCZOS)
    seed = sum(map(ord, entry["nome"]))
    image = np.asarray(raw, dtype=np.float32) / 255
    raw_metrics = seam_metrics(image)
    keep = entry.get("modo") == "placa" or (not raw_metrics["moldura"] and raw_metrics["percentil_junta"] <= RAW_TILEABLE_PERCENTILE)
    if entry.get("nivelar", True):
        image = flatten(image)
    seamless = image if keep else make_seamless(image, seed)
    small = Image.fromarray(np.clip(seamless * 255, 0, 255).round().astype(np.uint8), "RGB")
    small = small.resize((size, size), Image.LANCZOS)
    if "recolorir" in entry:
        colors = entry["recolorir"]
        array = recolor(np.asarray(small, dtype=np.float32) / 255, colors["escuro"], colors["claro"])
        small = Image.fromarray(np.clip(array * 255, 0, 255).round().astype(np.uint8), "RGB")
    metrics = seam_metrics(np.asarray(small, dtype=np.float32) / 255)
    if entry.get("modo") == "placa":
        metrics["placa"] = True  # laje com borda própria: a borda é desenho, não emenda
    return small, metrics


def finish(entry: dict, texture: Image.Image) -> None:
    """Grava a textura final, a prévia e, se pedido, a máscara de emissão."""
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    texture.save(TEXTURE_DIR / f"{entry['nome']}.png")
    print(f"    prévia {preview(texture, entry['nome']).relative_to(ROOT)}")
    if "emissao" in entry:
        mask = emission_mask(np.asarray(texture, dtype=np.float32) / 255, entry["emissao"]["cor"])
        save_png(mask, TEXTURE_DIR / f"{entry['nome']}_emissao.png", "L")
        print(f"    máscara de emissão: {mask.mean():.1%} da área acesa")


def generate(meshy: Meshy, config: dict, state: dict, entry: dict) -> None:
    name = entry["nome"]
    record = state.setdefault(name, {"attempts": []})
    if record.get("status") in ("aprovada", "reprovada"):
        return
    cost = COST_PER_IMAGE[config["modelo_ia"]]
    prompt = config["estilo"].replace("[TIPO]", entry["tipo"])
    while len(record["attempts"]) < config["tentativas"]:
        if spent(state) + cost > config["limite_creditos"]:
            raise RuntimeError(f"limite de {config['limite_creditos']} créditos: parei antes de {name}")
        number = len(record["attempts"]) + 1
        task_id = meshy.post("/v1/text-to-image", {"ai_model": config["modelo_ia"], "prompt": prompt})
        attempt = {"task_id": task_id, "estimate": cost}
        record["attempts"].append(attempt)
        save_state(state)
        task = meshy.wait("/v1/text-to-image", task_id)
        attempt["credits"] = task.get("consumed_credits", 0)
        if task["status"] != "SUCCEEDED":
            attempt["status"] = task["status"]
            save_state(state)
            print(f"  {name} #{number}: {task['status']}")
            continue
        raw = RAW_DIR / f"{name}_{config['versao']}_{number}.png"
        fetch(task["image_urls"][0], raw)
        texture, metrics = process(entry, raw, config["tamanho_px"])
        attempt.update(status="SUCCEEDED", raw=str(raw.relative_to(ROOT)), metricas=metrics)
        ok = passes(metrics)
        print(f"  {name} #{number}: {metrics} -> {'aprovada' if ok else 'reprovada'}")
        if ok or len(record["attempts"]) >= config["tentativas"]:
            record["status"] = "aprovada" if ok else "reprovada"
            record["escolhida"] = number
            finish(entry, texture)
        save_state(state)
        if ok:
            return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="gera de verdade (gasta créditos)")
    parser.add_argument("--reprocess", action="store_true", help="refaz o processamento das imagens já baixadas")
    parser.add_argument("--only", nargs="*", help="nomes das texturas")
    args = parser.parse_args()

    config = json.loads(CONFIG_FILE.read_text())
    use_version(config["versao"])
    state = load_state()
    # Texturas presas a uma versão antiga ("versao" na entrada) ficam como estão.
    entries = [e for e in config["texturas"]
               if e.get("versao", config["versao"]) == config["versao"] and (not args.only or e["nome"] in args.only)]

    if args.reprocess:
        for entry in entries:
            record = state.get(entry["nome"], {})
            chosen = entry.get("tentativa_escolhida", record.get("escolhida"))
            if chosen is None:
                continue
            raw = ROOT / record["attempts"][chosen - 1]["raw"]
            texture, metrics = process(entry, raw, config["tamanho_px"])
            ok = passes(metrics)
            record.update(escolhida=chosen, status="aprovada" if ok else "reprovada", metricas_finais=metrics)
            print(f"  {entry['nome']} #{chosen}: {metrics} -> {'aprovada' if ok else 'reprovada'}")
            finish(entry, texture)
        save_state(state)
        return

    load_dotenv(ROOT / ".env")
    if not os.environ.get("MESHY_API_KEY"):
        sys.exit("MESHY_API_KEY não encontrada no .env")
    meshy = Meshy(os.environ["MESHY_API_KEY"])
    cost = COST_PER_IMAGE[config["modelo_ia"]]
    todo = [e for e in entries if state.get(e["nome"], {}).get("status") not in ("aprovada", "reprovada")]
    print(f"Saldo na Meshy: {meshy.balance()} créditos")
    print(f"{len(todo)} texturas a gerar com {config['modelo_ia']} ({cost} créditos cada): "
          f"{len(todo) * cost} créditos esperados, até {len(todo) * cost * config['tentativas']} se todas "
          f"precisarem de nova tentativa. Já gastos: {spent(state)}. Limite: {config['limite_creditos']}.")
    if not args.run:
        print("Nada foi gerado. Use --run para gerar.")
        return
    for entry in todo:
        generate(meshy, config, state, entry)
    print(f"\nGastos nas texturas: {spent(state)} créditos. Saldo: {meshy.balance()}.")


if __name__ == "__main__":
    main()

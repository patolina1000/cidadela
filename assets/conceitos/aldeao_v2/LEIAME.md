# Aldeão v2 — folhas técnicas de modelagem

Pasta de entrada do aldeão novo. O pipeline (`tools/`) lê daqui; nada é gerado até as folhas
estarem aqui e o custo ser aprovado (ver `docs/DIARIO.md`, 29/09/2026). O que sai do pipeline segue o
contrato em `assets/modelos/aldeao_v2/CONTRATO.md`.

## O que colocar aqui

| Arquivo | Conteúdo | Uso na Meshy |
| --- | --- | --- |
| `corpo_frente.png` | Corpo careca e sem rosto, T-pose, de frente, fundo liso | Multi-Image to 3D (1ª imagem) |
| `corpo_costas.png` | O mesmo, de costas | Multi-Image to 3D (2ª imagem) |
| `corpo_lado.png` | Opcional: de perfil | Multi-Image to 3D (3ª imagem) |
| `cabelo_1_frente.png` … `cabelo_5_frente.png` | Só a peruca, de frente, fechada, sem cabeça | Multi-Image to 3D (1ª imagem) |
| `cabelo_1_costas.png` … `cabelo_5_costas.png` | A mesma peruca, de costas | Multi-Image to 3D (2ª imagem) |
| `folha_*.png` | As folhas originais inteiras (várias vistas na mesma página), para referência | Não vão para a Meshy |

Regras que evitam retrabalho (aprendidas no v1):
- frente e costas de cada peça na **mesma escala** e centradas, fundo branco ou liso, sem texto, setas ou cabeças soltas;
- corpo com a cabeça **lisa** (sem olhos, nariz ou boca): o rosto entra depois, pelos planos "Olhos" e "Boca";
- perucas como **volume fechado** (com a parte de dentro), franja acima da linha da sobrancelha;
- a cor não importa para a Meshy: corpo e cabelos saem só malha ("mesh only") e o jogo pinta a cor chapada
  definida em `data/` (contrato); nas folhas, cores chapadas e contrastadas ajudam a leitura das formas.

Se as folhas vierem com várias vistas na mesma imagem, o recorte é feito por script (como o
`crop_concept.py` fez para a protagonista) e os recortes ficam em `vistas/`.

## Nomes das 5 perucas

Pelo contrato as perucas se chamam `cabelo_1` a `cabelo_5` (`assets/modelos/aldeao_v2/cabelos/cabelo_N.glb`).
O número segue a ordem das folhas; o nome legível de cada penteado vai em `data/villager_looks.json`
(agente de código), não no pipeline.

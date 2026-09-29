# Aldeão v2 — folhas técnicas de modelagem

Pasta de entrada do aldeão novo. O pipeline (`tools/`) lê daqui; nada é gerado até as folhas
estarem aqui e o custo ser aprovado (ver `docs/DIARIO.md`, 29/09/2026).

## O que colocar aqui

| Arquivo | Conteúdo | Uso na Meshy |
| --- | --- | --- |
| `corpo_frente.png` | Corpo careca e sem rosto, T-pose, de frente, fundo liso | Multi-Image to 3D (1ª imagem) |
| `corpo_costas.png` | O mesmo, de costas | Multi-Image to 3D (2ª imagem) |
| `corpo_lado.png` | Opcional: de perfil | Multi-Image to 3D (3ª imagem) |
| `cabelo_<nome>_frente.png` | Só a peruca, de frente, fechada, sem cabeça (5 arquivos) | Multi-Image to 3D (1ª imagem) |
| `cabelo_<nome>_costas.png` | A mesma peruca, de costas | Multi-Image to 3D (2ª imagem) |
| `folha_*.png` | As folhas originais inteiras (várias vistas na mesma página), para referência | Não vão para a Meshy |

Regras que evitam retrabalho (aprendidas no v1):
- frente e costas de cada peça na **mesma escala** e centradas, fundo branco ou liso, sem texto, setas ou cabeças soltas;
- corpo com a cabeça **lisa** (sem olhos, nariz ou boca): o rosto entra depois, pelos planos "Olhos" e "Boca";
- perucas como **volume fechado** (com a parte de dentro), franja acima da linha da sobrancelha;
- as cores já na paleta: pele #9FB7CB, cabelo #4B5A69 (GDD, seção 17 e "Aldeão: implementação v1").

Se as folhas vierem com várias vistas na mesma imagem, o recorte é feito por script (como o
`crop_concept.py` fez para a protagonista) e os recortes ficam em `vistas/`.

## Nomes das 5 perucas

Manter os nomes do v1 (`curto_baguncado`, `medio_franja`, `ondulado`, `longo_liso`, `rabo_cavalo`) faz o
jogo continuar funcionando sem mudar código nem `data/villager_looks.json`. Se os penteados forem outros,
os nomes novos entram no `villager_looks.json` (agente de código).

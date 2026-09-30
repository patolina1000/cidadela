# Protagonista v2 — plano de créditos para o "manda" (29/09/2026)

Nada foi gasto para este plano. **Saldo da Meshy hoje: 2.258 créditos** (consulta grátis em `/v1/balance`).

Preços da Meshy (docs.meshy.ai, tabela da API consultada hoje, iguais aos que o diário do aldeão registrou):

- modelo 3D por imagem ou multi-imagem, **só malha: 20** (com textura 30);
- **rig: 5 por pedido** (um pedido recusado, como o "Pose estimation failed" do aldeão, **não cobra**);
- **animação: 3 por ação**, até 10 ações num pedido; a biblioteca e os GIFs de prévia são grátis;
- o rig já vem com uma caminhada e uma corrida básicas, **grátis**;
- remesh 5; retexture 10 (nada disto é necessário aqui).

O que o aldeão gastou no mesmo caminho: rig 5 + 2 clipes 6 + 3 clipes extras para comparar 9 = **20**; cabelos 5 × 20 = 100.

## 1. Rig e clipes

**Rig (5 créditos, no máximo 10).**

- Primeiro, o rig direto no corpo limpo (`protagonista_corpo_limpo.glb`, 0,80 m). No aldeão esse pedido foi recusado sem custo; a protagonista tem proporção humana e deve passar.
- Se for recusado: rig sobre a tarefa original do bruto B (`01a0efaa-2e6e-72fb-a1a6-8d343e404f45`) e transferência de pesos para a malha limpa no Blender, como no aldeão (`montar_rig.py`).
  - Os ossos da cabeça precisam acompanhar a limpeza: a cabeça cresceu 1,355× a partir da base do pescoço e o corpo foi a 0,94×.
  - **Prazo:** os brutos da Meshy expiram em cerca de 3 dias; a tarefa é de 29/09, então esse caminho vale até mais ou menos 02/10.
- Reserva de mais 5 se o primeiro rig vier torto (mãos, dedos, cabeça).
- Depois do rig, sem crédito:
  - retalhos "Olhos" e "Boca" no GLB (b3: olhos ±45° e janela +10%, boca +12%, 2 mm, 100% Head), com a conferência de folga nos clipes;
  - pele da frente da cabeça 100% Head;
  - `ergonomia.json` (o `medir_ergonomia.py` lê os ossos);
  - `passada_m_s` no `clipes/clipes.json`.

**Corrida (ela só corre).** Candidatos da biblioteca, escolhidos primeiro pelos GIFs de prévia (grátis) e depois gerados para comparar em GIFs na câmera do jogo e de lado, com a grade do chão na passada:

- Run 2 (14), a do aldeão;
- Run 3 (15);
- Run Fast (16);
- Lean Forward Sprint (509);
- mais a corrida básica que vem grátis com o rig.

Custo: **4 candidatos × 3 = 12**. No mínimo, 1 × 3 = 3, se a básica grátis já servir e só uma for gerada para comparar.

**Idle ("mais trabalhado que o do aldeão").** Candidatos calmos, de pés juntos:

- Idle 3 (243), o do aldeão;
- Idle 12 (252);
- Catching Breath (31): cansada, combina com a neutra_cansada;
- Long Breathe and Look Around (336).

Custo: **4 × 3 = 12**; no mínimo, 1 × 3 = 3.

**Rodada de reserva:** se nenhum servir, mais 2 de cada, **12**.

**Uthana (idle).** Não há conta nem chave de API. O GDD dá o Uthana como "preço a confirmar" (orçamento de US$ 30/mês) e ele é cobrado em **dinheiro, não em créditos da Meshy**. Proposta: só abrir a conta se nenhum idle da Meshy servir; aí o Arthur decide a assinatura.

## 2. Chifres (piloto, rígidos)

- Meshy multi-imagem com a folha dos chifres (busto careca + chifres): frente, perfil e costas, sem o topo (a conferência mostrou que o topo é incoerente). Só malha, 20 por geração.
- Depois, sem crédito: extração da peça, âncora em 3 medidas, escala por eixo (o busto é ~5% mais estreito que o corpo), decimação a ≤ 300 triângulos o par, material "chifre", no espaço do corpo em repouso.
- **Teto sugerido: 3 gerações = 60** (1 piloto + 2 se vier técnica ou visualmente errado). Mínimo 20.

## 3. Cabelo com pesos

- Precisa da Meshy para a forma (cabelo longo, mechas; por script não sai bom). Multi-imagem com a folha do cabelo: frente, perfil e costas, sem o topo, só malha, 20 por geração.
- Os pesos (calota 100% Head, trás em gradiente por neck, Spine, Spine01), a janela dos olhos, a folga de 2 mm e a decimação a ≤ 1.000 triângulos são no Blender, sem crédito.
- **Teto sugerido: 2 gerações = 40.** Mínimo 20.
- O cristal (≤ 60 triângulos) sai por código, sem crédito.

## 4. Resumo

| Passo | Mín. | Máx. | Para para o Arthur ver |
|---|--:|--:|---|
| Rig (direto ou pela tarefa original + transferência) | 5 | 10 | A pose de repouso com os pesos e a corrida básica grátis em GIF (câmera do jogo e lado); retalhos acompanhando a cabeça |
| Corridas para comparar | 3 | 12 | GIFs das corridas (jogo 68 px ampliado e lado, grade do chão na passada) |
| Idles para comparar | 3 | 12 | GIFs dos idles, com a neutra_cansada e o piscar |
| Reserva de clipes (2 + 2) | 0 | 12 | Só se nenhum candidato servir; nova folha de GIFs |
| Chifres (piloto) | 20 | 60 | Folha de contato: bruto e peça extraída sobre a cabeça, frente, perfil, 3/4 e câmera do jogo, com crepúsculo |
| Cabelo com pesos | 20 | 40 | Folha de contato e GIF da corrida com o cabelo (não atravessa os braços) |
| Ergonomia, retalhos no GLB, cristal, `clipes.json` | 0 | 0 | Junto da entrega do rig e dos clipes |
| **Total** | **51** | **146** | |

Depois de tudo o saldo fica entre **2.112 e 2.207**. Sugestão de "manda": **teto de 150 créditos para a protagonista inteira**, com as paradas acima. Em cada parada eu confiro o saldo e o custo previsto e, se o próximo passo passar do teto, paro e aviso.

Nota para a próxima volta do atlas (sem crédito): no zoom 2,5, dor e esforço ficaram quase iguais. A dor vai ganhar assimetria (um olho mais fechado).

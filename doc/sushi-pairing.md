# Pairing Analysis — Sushi Vegetariano com Shoyu e Wasabi

## Pratos

**Futomaki** — arroz japonês temperado com limão e açúcar (pouco), nori, cenoura, omeleta, feijão verde, shiitake e kampyo (gourd seco estufado em dashi, soja e mirin)

**Hosomaki** — rolo fino de nori com arroz temperado, pepino, cenoura e nabo em pickle (tsukemono)

Ambos servidos com molho shoyu e wasabi.

---

## Drivers de Harmonização

O ingrediente principal não determina a harmonização — o método e os complementos têm peso igual ou superior. Os drivers dominantes do conjunto são:

| Driver | Implicação |
|---|---|
| Shoyu (umami + salgado intenso) | Exige acidez alta para contrabalançar; evitar taninos |
| Arroz temperado com limão | Acidez no prato — o vinho deve espelhar, não colidir |
| Wasabi (calor picante) | Evitar álcool elevado — amplifica a sensação de calor |
| Kampyo em dashi + soja + mirin (umami + doce leve) | Perfil suave doce-umami; mineralidade delicada e fruta discreta complementam |
| Shiitake + nori (umami + iodo marinho) | Brancos minerais e salobros complementam; iodo do nori ressoa com salinidade |
| Omeleta (textura suave, ovo) | Brancos com acidez equilibrada; evitar vinhos demasiado austeros |
| Nabo em pickle — tsukemono (fermentado + ácido) | Acidez láctica reforça necessidade de acidez alta no vinho; semi-secos podem conflituar com o tang do pickle |
| Pepino + cenoura (vegetal fresco, crocante) | Frescura e leveza — vinhos leves preferíveis |

**Filtros aplicados:** type: white; body_exclude: full, medium-full; tannins_max: 3; alcohol_max: 13.5%

---

## Seleção — 10 Vinhos

*Scores são resultados exactos do engine de harmonização (produção, 30 regras) sobre os 443 vinhos da base de dados.*
*Scores variam por prato: futomaki e hosomaki agora produzem rankings diferentes.*

---

### 1 — Aphros Ten · Aphros Wine
Loureiro · Vinho Verde – Lima · acidity 10 · off-dry · body: light · **score 35 (futomaki) / 28 (hosomaki)**

Vencedor claro para o futomaki: acidez máxima na base de dados (10 g/L) activa a regra `high-acidity-soy-condiment` (+10) com PRIMARY_BONUS (+3 por acertar no primary_tag do prato). O toque off-dry complementa o kampyo doce-umami. Para o hosomaki, o resíduo de açúcar é penalizado pelo conflito com o tsukemono (−7), descendo para score 28 — ainda o melhor do hosomaki, mas a diferença é clara.

---

### 2 — Lezíria Meio Seco Branco · Adega Cooperativa de Almeirim
Fernão Pires · Tejo – Almeirim · acidity 6 · off-dry · body: light · **score 28 (futomaki) / ausente do top-20 hosomaki**

O engine confirma este vinho como segunda escolha para o futomaki — o perfil off-dry acumula score bem com kampyo e umami suave. Para o hosomaki, a regra `conflict-sweetness-pickled` (−7) aplicada ao tsukemono elimina-o completamente do top-20: a doçura residual conflitua com a acidez láctica do nabo em pickle.

---

### 3 — Quinta dos Currais Síria Branco · Quinta dos Currais
Síria · Beira Interior – Cova da Beira · acidity 10 · dry · body: light · **score 26 (ambos)**

Melhor valor da seleção (€5.49). Acidez igual à do Aphros Ten mas seco — sem conflito com tsukemono, funciona bem nos dois rolos. Síria (syn. Roupeiro) de alta acidez natural na Beira Interior.

---

### 4 — Soalheiro Granit Alvarinho · Quinta de Soalheiro
Alvarinho · Vinho Verde – Monção e Melgaço · acidity 9 · dry · **score 26 (ambos)**

Alvarinho clássico de Monção. Acidez alta e salinidade mineral complementam o shoyu e o nori; secura total sem conflito com o tsukemono. Referência da região.

---

### 5 — Aphros Loureiro · Aphros Wine
Loureiro · Vinho Verde – Lima · acidity 9 · dry · **score 26 (ambos)**

Versão seca da mesma casta e produtor do #1. Sem o off-dry que vantagem o futomaki, mas também sem a penalização no hosomaki. Escolha mais segura para servir os dois rolos ao mesmo tempo.

---

### 6 — Contacto Loureiro · Anselmo Mendes
Loureiro (skin contact) · Vinho Verde · acidity 8 · dry · **score 26 (ambos)**

Loureiro com maceração em casca: textura acrescida, complexidade discreta, taninos vestigiais. Dry — sem conflito com tsukemono. A textura do skin contact cria ressonância com a fermentação do nori e do shiitake.

---

### 7 — Muros Antigos Alvarinho · Anselmo Mendes
Alvarinho · Vinho Verde – Monção e Melgaço · acidity 8 · dry · **score 26 (ambos)**

Produtor de referência para Alvarinho. Mineralidade, frescura e fruta cítrica discreta. Funcional nos dois rolos, escolha segura para uma carta.

---

### 8 — Mono C · Luis Seabra
Branco blend · Douro · acidity 9 · dry · **score 26 (ambos)**

Surpresa geográfica: vinho do Douro com acidez suficiente para funcionar neste contexto. Luis Seabra faz vinhos de baixa intervenção com carácter mineral. Menos óbvio mas bem fundamentado estruturalmente.

---

### 9 — Magnum Ribeiro Santo Rabo-de-Ovelha · Carlos Lucas Vinhos
Rabo-de-Ovelha · Dão – Carregal do Sal · acidity 9 · dry · **score 26 (ambos)**

Casta do Dão de acidez alta (9 g/L) e acabamento longo, raramente vista. Motor encontrou-a — não constava da seleção manual. Representa bem o tipo de descoberta que o scoring estrutural proporciona.

---

### 10 — Prova Régia Branco · Quinta da Romeira
Arinto · Lisboa – Bucelas · acidity 7 · dry · **score 21 (ambos)**

Passo abaixo do grupo anterior (acidez 7 vs 8–10). Arinto de Bucelas é clássico e faz sentido qualitativo com sushi, mas o engine coloca-o na segunda prateleira estrutural. Boa opção de carta pela notoriedade da denominação.

---

## Comparação: Engine (Produção) vs Análise Manual Anterior

| Vinho | Score Manual | Score Produção | Avaliação |
|---|---|---|---|
| Aphros Ten | ~33 | **35 / 28** | Motor confirma liderança — diferença por prato agora modelada |
| Soalheiro Granit Alvarinho | ~31 | **26 / 26** | Sobreestimativa manual — salinidade mineral é qualitativa |
| Lezíria Meio Seco | baixado da lista | **28 futomaki / fora hosomaki** | Conflito com tsukemono agora modelado — comportamento correcto |
| Rola Pipa (Açores) | ~30 | **fora do top 20** | Iodo/algas é raciocínio qualitativo — sem regra equivalente |
| Contacto Loureiro skin contact | ~29 | **26 / 26** | Agora aparece no top-20 — acidez ≥ 8 activa nova regra |
| Muros Antigos Alvarinho | ~28 | **26 / 26** | Confirmado na seleção |
| Filipa Pato Bical | ~26 | **fora do top 20** | Bairrada sem regra específica para este perfil |
| Soalheiro 9% | ~25 | **fora do top 20** | Álcool baixo não é vantagem estrutural no engine |
| Prova Régia Arinto | ~25 | **21 / 21** | Desceu — acidez 7 coloca-o abaixo do grupo ac≥8 |
| Quinta dos Currais Síria | não constava | **26 / 26** | Descoberta do engine — melhor valor da seleção |

**Diferença por prato (objectivo atingido):** Aphros Ten 35 vs 28; Lezíria 28 vs ausente. A introdução de `soy_condiment` como primary_tag e `pickled`/`fermented` para hosomaki produz rankings estruturalmente diferentes entre os dois pratos — que era o problema a resolver.

---

## Notas de Método

- Engine: `generate-pairings.py --menu sushi-test` sobre 443 vinhos, **30 regras** (produção)
- Tags futomaki: `soy_condiment` (primary), `soy_based`, `umami`, `egg`, `mushroom`, `dashi_based`, `sweet_sour`, `raw`, `lemon_based`, `delicate`, `light`
- Tags hosomaki: `soy_condiment` (primary), `soy_based`, `umami`, `raw`, `pickled`, `lemon_based`, `fermented`, `delicate`, `light`
- Novas regras que distinguem os pratos: `high-acidity-soy-condiment` (+10, ac≥8 branco + PRIMARY_BONUS +3); `conflict-sweetness-pickled` (−7, sweetness≠dry + pickled/fermented)
- Filtros: type: white; body ∉ {full, medium-full}; tannins ≤ 3; alcohol ≤ 13.5%
- Preços não incluídos — validar via scripts/price-lookup/csv_matcher.py
- Data: Março 2026

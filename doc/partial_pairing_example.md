# Pairing Analysis — Menu Nanban (10 courses)
*Manual simulation of pairing-rules.json applied against the wine DB producers files*
*Status: pairing-engine.js not yet implemented — this is a manual dry run*

---

## Meta-observation

This menu is almost entirely tofu-based with miso and dashi as recurring sauce elements. **No red meat, no fish as main protein.** That has a major consequence: red wine is only marginally justified for one course (Gratin). The DB is weighted heavily toward Portuguese whites — which turns out to be correct for this menu.

---

## Quick Reference Table

| # | Prato | Tags aplicados | Wine | Score |
|---|-------|---------------|------|-------|
| 1 | Goma Doufu + uni | shellfish, umami, silky | **Alvarinho** (Soalheiro / Anselmo Mendes) | 9 |
| 2 | Aperitivos Variados | fried, variety, fat | **Espumante** (Raposeira / Terras do Demo) | 9 |
| 3 | Ceviche de Tofu + yuzu | citrus, acidic, raw | **Síria** (Quinta da Biaia Fonte da Vila) | 9+2 |
| 4 | Tofu Agedashi Frito | miso_based, fried, umami | **Uva-cão** (Passarela O Fugitivo) | 9 |
| 5 | Cataplana Tofu + Ameijoas | shellfish, braised, portuguese | **Encruzado** (Quinta dos Roques) | 9+2 |
| 6 | Nanban-zuke de Tofu | sweet_sour, fried, marinade | **Rosé** (Julia Kemper) | 8 |
| 7 | Gratin de Tofu | rich, creamy, miso, cheese | **Encruzado barrica** (Julia Kemper Reserva) | 9 |
| 8 | Arroz Misto | dashi, light, neutral | Continuar Gratin wine — ou Loureiro | — |
| 9 | Sopa Clara + Yuba + yuzu | dashi, delicate, citrus | **Cerceal Branco** (Quinta dos Roques) | 9+4 |
| 10 | Parfait + Castella | sweet, dessert, nutty | **Colheita Tardia** (Ribeiro Santo) ou Tawny | 10 |

---

## Por prato

### 1 — Goma Doufu (先付 Sakizuke)
*Tofu de gergelim, purê de ouriço, wasabi*

**Fator dominante:** O **uni** (ouriço do mar) — não o tofu. Uni é gordo, intensamente umami, marinho. O wasabi adiciona picante.

**Regras ativadas:**
- `high-acidity-shellfish` → uni = marisco, acidity ≥ 7 → **score 9**
- `light-body-delicate-dishes` → tofu = delicado, silky → score 9
- Tensão: uni pede estrutura, tofu pede leveza → wine precisa de equilibrar ambos

**Vinho:** Alvarinho de Monção e Melgaço (Soalheiro ou Anselmo Mendes). Alta acidez + mineralidade + afinidade natural com marisco. O carácter salino e cítrico espelha o sabor marinho do uni sem dominar o tofu.

> ⚠️ Encruzado sem barrica (Magnum VSM) seria alternativa aceitável pela acidez 6.8 g/L, mas Alvarinho está estruturalmente mais próximo do perfil marisco.

---

### 2 — Aperitivos Variados (八寸 Hassun)
*Yuba roll, abura-age, bacon + queijo, tempura de tofu*

**Fator dominante:** **Variedade** — texturas e sabores díspares num único prato. Bacon + queijo adicionam gordura e sal. Tempura adiciona fritura.

**Regras ativadas:**
- `sparkling-aperitif-variety` → type: sparkling, variety + fried → **score 9**
- `medium-body-fried-light` → acidity ≥ 6, fried → score 8

**Vinho:** Espumante método tradicional — **Raposeira Super Reserva** (Távora-Varosa, Malvasia Fina + Verdelho) ou **Terras do Demo Pata de Lebre** (Malvasia Fina + Gouveio, 2018). A borbulha e a acidez alta são a única categoria capaz de lidar com a heterogeneidade do Hassun.

---

### 3 — Ceviche de Tofu Firme (向付 Mukozuke)
*Tofu firme, yuzu, azeite português, chips de batata doce*

**Fator dominante:** **Yuzu** — o definidor total do prato. Ácido, aromático, cítrico.

**Regras ativadas:**
- `bonus-citrus-citrus-mirror` → acidity ≥ 7 → **+2 bónus** (harmonização por semelhança)
- `light-body-delicate-dishes` → tofu raw/marinated → score 9

**Vinho:** **Quinta da Biaia Single Vineyard "Fonte da Vila" Síria 2019** (Beira Interior — Síria 100%, 13%, acidez 7.35 g/L, pH 3.12). O produtor descreve: *"toranja e lima"* — toranja é o espelhamento direto do yuzu. 30 meses em borras dão textura sem perder frescura. O melhor match de todo o menu por semelhança aromática.

> Alternativa: Magnum VSM Branco 2024 (Encruzado inox, 6.8 g/L) — o mais ácido do DB do Dão, mas sem as notas de toranja da Biaia.

---

### 4 — Tofu Agedashi Frito (焼物 Yakimono)
*Tofu frito em batter leve, molho de missô*

**Fator dominante:** **Molho de miso** — umami doce-salgado. O princípio fundamental diz explicitamente: *miso_based → brancos aromáticos ou ligeiramente adocicados.*

**Regras ativadas:**
- `off-dry-miso-sweet` → sweetness off-dry, miso_based → **score 9** ← regra determinante
- `aromatic-white-umami` → acidity 5-7 → score 8
- `medium-body-fried-light` → fried → score 8

**Vinho:** **Casa da Passarela O Fugitivo Uva-cão 2020** (Dão — Uva-cão, 13%, residual 2.3 g/L = off-dry). Casta rarísima, ligeiramente adocicada, "de enorme frescura, elegante e grande complexidade". A pequena doçura residual espelha a doçura natural do miso sem amplificar o sal — exatamente o que a regra `off-dry-miso-sweet` captura.

> Esta é a única wine do DB com esse perfil off-dry dentro do Dão. É também a escolha mais inesperada e a que o engine produziria sem intervenção humana.

---

### 5 — Cataplana de Tofu e Ameijoas (煮物 Nimono)
*Tofu + amêijoas, estilo cataplana portuguesa, especiarias nanban*

**Fator dominante:** **Amêijoas** (briny, umami, shellfish) + **cataplana** (prato rico, estufado com peso).

**Regras ativadas:**
- `high-acidity-shellfish` → amêijoas, acidity ≥ 7 → score 9
- `bonus-regional-affinity` → cataplana = prato português → **+2 bónus**
- `full-body-white-rich-dishes` → stewed, rich → score 9

**Vinho:** **Quinta dos Roques Encruzado 2023** (Dão — 50% barrica 500L, body medium, affinities explicitamente incluem *"marisco, lagosta, vieiras"*). A combinação de barrica (estrutura para o estufado) + marisco (afinidade declarada) + origem portuguesa (bónus regional) converge perfeitamente.

> Este é o prato onde a afinidade regional (vinho português + prato português) tem mais peso.

---

### 6 — Nanban-zuke de Tofu (酢肴 Suzakana)
*Tofu frito e marinado em molho agridoce*

**Fator dominante:** **Marinada agridoce** — vinagre + doçura. A nomenclatura *Nanban-zuke* remete ao escabeche português (vinagre + gordura + picante).

**Regras ativadas:**
- `medium-body-fried-light` → fried, acidic → score 8
- `madeira-acidic-fortified-acidic-dishes` → sweet_sour, marinade → score 9 (mas Madeira é muito específico para este contexto)
- `sparkling-aperitif-variety` → fried + acidic → score 9 (bubbles cut marinade)

**Vinho:** **Julia Kemper Rosé 2022** (Dão — 50% Jaen + 30% Tinta Roriz + 20% TN, 12.2%, acidez 4.86 g/L, residual 1.2 g/L, *"fresco, seco, persistente e muito envolvente"*). O rosé é a categoria mais versátil para molhos agridoces — suficientemente ácido para cortar a marinada, suficientemente neutro para não conflituar com o vinagre.

---

### 7 — Gratin de Tofu (強肴 Shiizakana)
*Tofu gratinado, molho cremoso de miso e queijo*

**Fator dominante:** **Riqueza** — molho cremoso + queijo derretido + miso = máxima densidade de sabor e gordura do menu.

**Regras ativadas:**
- `full-body-white-rich-dishes` → rich, creamy, fatty → **score 9**
- `off-dry-miso-sweet` → miso_based → score 9
- `conflict-light-body-rich-stew` → vinho leve seria eliminado aqui → score 2 (confirma que precisamos de corpo)

**Vinho:** **Julia Kemper Reserva Branco 2021** (Dão — 100% Encruzado, 15 meses em barricas CF, 13.8%, acidez 6.03 g/L, *"fresco, encorpado, mineral e com acidez crocante, terminando com grande elegância"*). O Encruzado barrica com 15 meses é o wine mais estruturado dos brancos secos no DB — acidez 6.03 corta a gordura do molho, corpo pleno suporta o peso do prato.

> Alternativa mais rica ainda: **Magnum Ribeiro Santo Branco 2019** (borras cruzadas, *"volume impressionante e amanteigado no palato"* — a textura amanteigada espelha o molho cremoso).

---

### 8 — Arroz Misto (御飯 Gohan)
*Arroz com ingredientes sazonais*

Este é um prato de transição em kaiseki. O arroz absorve o dashi — é neutro, limpa o palato.

**Recomendação:** Continuar com o vinho do Gratin (Julia Kemper Reserva) — não há justificação para mudar wine num prato que existe para fazer pausa. Em kaiseki tradicional, o Gohan frequentemente não tem vinho.

---

### 9 — Sopa Clara com Yuba (留椀 Tomewan)
*Suimono, yuba, yuzu*

**Fator dominante:** **Delicadeza máxima** — suimono é o caldo mais refinado da cozinha japonesa. A sopa existe para limpar.

**Regras ativadas:**
- `light-body-delicate-dishes` → dashi_based, delicate → **score 9**
- `bonus-floral-delicate-steam` → body light, steamed → **+2**
- `bonus-citrus-citrus-mirror` → yuzu, acidity ≥ 7 → **+2**
- Score total potencial: **13/10** → é o match mais alto do menu em termos de regras acumuladas

**Vinho:** **Quinta dos Roques Cerceal Branco 2023** (Dão — 12.2%, acidez 6.02 g/L, **body: light**, *"fruta ácida"*). O wine mais leve de todo o DB — demasiado delicado para qualquer outro prato do menu, mas aqui é exatamente o que se precisa. As suas limitações tornam-se virtudes.

> Nota: Em kaiseki formal, o Tomewan é servido com o Gohan sem wine. Mas numa adaptação moderna, este é o momento certo para este wine específico.

---

### 10 — Parfait de Tofu e Castella com Biscoito de Okara (水物 Mizumono)
*Mousse de tofu sedoso, bolo castella, biscoito de okara*

**Fator dominante:** **Sobremesa doce** — regra absoluta: o vinho nunca deve ser menos doce que o prato.

**Regras ativadas:**
- `sweet-fortified-rich-desserts` → sweetness sweet → **score 10**
- `tawny-port-nut-desserts` → okara cookies têm carácter tostado/noz → **score 10**

**Opção 1 — Coerência com o DB do Dão:** **Magnum Ribeiro Santo Colheita Tardia 2021** (Encruzado, 15% alc, colheita tardia, *"mineralidade e final fresco, conjugado com bela acidez"* — o único wine doce do DB do Dão, mais restraint, mais elegante).

**Opção 2 — Score máximo:** Porto Tawny 10 anos. As notas de noz e caramelo do Tawny espelham perfeitamente o biscoito de okara tostado e o castella. Seria a sugestão clássica e de maior impacto.

---

## Conclusões do exercício

**O que funciona bem no DB:**
- Para pratos com miso → `off-dry-miso-sweet` identificou corretamente o Uva-cão (único off-dry do Dão DB)
- Para o Ceviche + yuzu → `bonus-citrus-citrus-mirror` identificou corretamente a Síria da Biaia pelas notas de toranja
- Para o Gratin → `conflict-light-body-rich-stew` elimina automaticamente os wines leves (Cerceal, VSM)
- Para Cataplana → `bonus-regional-affinity` dá peso correto ao contexto português

**Gaps do DB que a implementação teria de resolver:**
1. **Nenhum Alvarinho de produtor** no DB (Dish 1) — os perfis do Soalheiro e Anselmo Mendes existem nos ficheiros mas não têm `acidity_gl` preenchido em todos os wines
2. **Dishes 8 e 9** (Gohan + Tomewan) são cursos de transição — o engine precisaria de um conceito de "no pairing" ou "continue previous"
3. **Sobremesa** — ~~o DB não tem Porto nem Moscatel nos producer files~~ *(corrigido: Porto e Madeira estão agora no DB — 5 produtores de Porto: Graham's, Sogevinus, Dow's, Porto Ferreira, Dalva; 3 de Madeira: Blandy's, Barbeito, Henriques & Henriques)*

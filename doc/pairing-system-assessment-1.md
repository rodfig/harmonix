Below is a **full semantic evaluation** of the three uploaded components:

* menu structure
* dish semantic schema
* pairing output

I will analyze them at three levels:

1. **Menu semantic model (menu.json)**
2. **Dish taxonomy & schema adequacy (dish-profiles.json)**
3. **Pairing engine output quality (pairings.json)**

and then provide a **system-level evaluation of the whole pairing architecture**.

All citations refer to the uploaded files.

---

# 1. Menu Model Evaluation (menu.json)

Source: 

The menu structure is **very well modeled for computational pairing**.
It separates **presentation from semantics**, which is exactly what a pairing engine needs.

## 1.1 Structural Model

Each dish includes:

```
id
sequence
name
course_label
description
image
properties
```

The most important part is:

```
properties
```

which includes:

```
preparation
sauce
texture
intensity
fat_level
acidity
sweetness
key_flavors
dominant_component
```

This is **an excellent semantic decomposition of a dish**.

It models exactly the parameters used in professional pairing:

| Dimension          | Why it matters                      |
| ------------------ | ----------------------------------- |
| preparation        | frying vs raw strongly affects wine |
| sauce              | sauces often dominate pairing       |
| texture            | tannin and body interaction         |
| intensity          | structural matching                 |
| fat_level          | acidity requirement                 |
| acidity            | pairing with wine acidity           |
| sweetness          | critical pairing constraint         |
| key_flavors        | aromatic affinity                   |
| dominant_component | conflict resolution                 |

This is already **close to a culinary ontology**.

---

## 1.2 Course Progression

The menu respects **kaiseki progression logic**:

| Course     | Function              |
| ---------- | --------------------- |
| Sakizuke   | opening delicate dish |
| Hassun     | seasonal platter      |
| Mukozuke   | raw course            |
| Yakimono   | cooked course         |
| Nimono     | simmered dish         |
| Suzakana   | acidic palate refresh |
| Shiizakana | richest dish          |
| Gohan      | palate reset          |
| Tomewan    | light soup closure    |
| Mizumono   | dessert               |
Your system correctly models **meal progression**.

This is essential because pairing must follow **structural crescendo**.

---

## 1.3 Minor Semantic Issues

### Issue 1 — “shellfish” appearing in tofu menu

Example: Hassun description includes:

```
dominant_component: "variety (fried, fatty, shellfish)"
```

But the dish is tofu-based.

This likely reflects **legacy tagging from seafood version**.

It contaminates pairing logic.

---

# Architectural Improvements for the Pairing Engine

Your pairing system already demonstrates a high level of sophistication: it separates menu presentation from semantic dish descriptions, uses food tags, structural wine attributes, and rule-based pairing logic. However, three architectural upgrades would transform it from a **rule-based matching system** into something closer to a **computational gastronomy engine**.

These improvements are:

1. Structural vector matching
2. Dominant flavor hierarchy
3. Meal-level pairing optimization

Each addresses a specific limitation in the current system.

---

# 1. Structural Vector Matching

## Current Approach

The pairing engine currently relies on **rule stacking** and discrete tags. Examples include rules such as:

* high-acidity-shellfish
* light-body-delicate-dishes
* citrus-mirror

This approach works well conceptually, but it tends to produce **score saturation**. Many wines trigger the same rule combinations and end up receiving identical scores. As a result, the ranking becomes less informative.

---

## Proposed Approach

Instead of rule stacking, represent **both wine and dish as structural vectors within the same multidimensional space**.

For example, a wine could be represented as:

Wine vector

* acidity: 8
* body: 2
* tannin: 0
* sweetness: 1
* fat affinity: 3
* aromatic intensity: 2

A dish could be represented as:

Dish vector

* acidity: 3
* fat: 2
* umami: 4
* sweetness: 0
* aromatic intensity: 2
* texture weight: 2

Pairing then becomes a compatibility calculation between the two vectors.

Compatibility rules still apply, but they operate continuously rather than discretely. For instance:

* fatty dishes favor high-acidity wines
* umami dishes favor low-tannin wines
* sweet dishes require sweet wines

Instead of triggering separate rules, these relationships influence a **continuous compatibility score**.

---

## Benefits

This approach offers several advantages:

* eliminates score saturation
* produces smoother ranking of wines
* allows finer distinctions between candidates
* simplifies tuning of pairing logic

Importantly, **your existing database already contains the required parameters**. Your wine records include acidity, tannins, body, sweetness, and finish. Your dish schema already includes fat level, acidity, sweetness, intensity, and texture. The structural data is already present — the engine only needs to use it differently.

---

## Implementation Assessment (March 2026)

### What implementation would actually require

Structural vector matching requires three things not currently present:

1. **Normalisation.** Wine attributes (`acidity_gl` in g/L, `tannins` on a 0–10 scale, `body` as an ordinal string) must be mapped into a common numeric space. Different units and ranges make this non-trivial.

2. **Dish vector.** `fat_level`, `acidity`, `sweetness`, and `intensity` in `menu.json` are ordinal strings (`none/low/medium/high`), not numbers. They would need conversion into the same numeric space as the wine vector.

3. **A compatibility weighting function.** Each dimension mismatch must carry a weight — how much does an acidity mismatch cost versus a body mismatch? These weights require calibration against known good pairings.

### The overtuning problem

Every weight in the compatibility function would be calibrated against this menu: 10 dishes built around tofu, dashi, and yuzu, where acidity is paramount and tannins are almost always wrong. Weights tuned on this corpus will be systematically incorrect for a meat-heavy menu, where tannin interaction with fat and protein matters far more.

The current rule-based system avoids this: "shellfish → high-acidity white" is a universally valid culinary principle, not a menu-specific tuning. The rules transfer to any menu without recalibration.

### Honest benefit assessment

Modest at this stage, for two reasons:

**1. Saturation is largely solved.** Dimensional-max scoring combined with the `primary_tag` bonus (+3 pts) already produces meaningful spread. Observed results after implementation: Goma Doufu top candidates score 37/36/36 (1-point gap); Parfait top candidates score 31/21/21 (10-point gap). The remaining ties in the top 3 are wines that are genuinely structurally equivalent for that dish. Ranking them more finely does not improve culinary accuracy.

**2. Where saturation remains, it doesn't matter.** Sequence pairing deliberately picks randomly from the top 3 to add variety across runs. The per-dish modal already shows `score_raw` — users see the fine ranking. The scenario where vector matching would help most (many wines tightly clustered at identical scores) is not what is observed — there are clear gaps between the top picks and the rest of the field.

### What the rule-based system does better

Rules are explicit culinary knowledge — each rule says something intelligible and universally applicable. A vector model encodes the same knowledge implicitly in weights, losing explainability and generalisability simultaneously.

### When vector matching becomes relevant

At a different scale: if this engine were serving 10 menus with 100+ dishes across diverse cuisines, maintaining specific rules for every new cuisine becomes unmanageable, and a universal compatibility function would be justified. At the current scale (1 menu, 10 dishes, 28 rules covering the relevant culinary space), the architecture overhead is not warranted.

### Decision

**Not implemented.** The marginal improvement in ranking precision does not justify the implementation cost or the overtuning risk. The system produces defensible, differentiated results with the current rule-based architecture.

If score differentiation remains a concern as new menus are added, the correct lever is adding targeted bonus rules to `pairing-rules.json` — additive, not a rewrite, and fully generalisable.

---

# 2. Dominant Flavor Hierarchy

## Current Limitation

Your dish schema contains useful descriptors such as:

* key_flavors
* dominant_component

However, the pairing engine effectively treats most tags as equal. In reality, dishes have **hierarchies of flavor importance**.

Consider the example of *Goma Doufu with Uni*. Its tags might include:

* silky
* umami
* shellfish
* light

But the real sensory hierarchy is:

1. dominant flavor: uni (marine umami)
2. structural characteristic: silky texture
3. background element: sesame tofu

Pairing decisions should prioritize the dominant element.

---

## Proposed Model

Introduce a structured flavor hierarchy within the dish description.

Example representation:

Flavor structure

* dominant: shellfish
* secondary: umami
* tertiary: nutty

Or alternatively:

* dominant element: uni
* dominant dimension: marine umami

The pairing engine should evaluate compatibility in the following order:

1. dominant flavor driver
2. structural compatibility (body, acidity, fat interaction)
3. aromatic mirroring

---

## Why This Matters

Many pairing engines fail because they treat dishes as a **bag of tags**. Real culinary reasoning works differently. Chefs and sommeliers always begin with the question:

What dominates the bite?

In your menu, each dish clearly has a dominant pairing driver:

| Dish           | Dominant driver           |
| -------------- | ------------------------- |
| Goma doufu     | uni                       |
| Ceviche tofu   | yuzu acidity              |
| Agedashi tofu  | dashi umami               |
| Cataplana tofu | shellfish broth           |
| Nanban tofu    | sweet-sour marinade       |
| Tofu gratin    | miso cream and cheese     |
| Dessert        | caramel and nut sweetness |

Your system already contains these insights in textual notes. Formalizing them into a **hierarchical structure the engine can interpret** would dramatically improve pairing accuracy.

---

# 3. Meal-Level Pairing Optimization

## Current Behavior

The engine currently identifies **the best wines for each individual dish**. This works for simple pairings but does not fully reflect how wine pairings operate in restaurants.

Professional pairing is optimized for **the progression of the entire meal**, not just individual dishes.

---

## The Real Pairing Problem

If the engine selects wines independently for each dish, it may produce something like:

Course 1 → vinho verde
Course 2 → vinho verde
Course 3 → vinho verde
Course 4 → vinho verde

Technically, these wines might all be good matches. But the experience becomes repetitive.

A sommelier would instead design a progression such as:

* sparkling wine for the opening
* bright citrus white for raw dishes
* textured white for richer preparations
* light red for savory richness
* sweet wine for dessert

The goal is **structural escalation and diversity across the meal**.

---

## Proposed Model

Introduce a **meal optimization layer** above dish-level pairing.

Instead of simply ranking wines per dish, the engine should maximize compatibility while respecting sequence constraints.

Optimization criteria may include:

* compatibility with the current dish
* logical progression of wine body and intensity
* avoidance of repetition
* diversity of styles or regions

---

## Example Outcome

For your specific kaiseki menu, a progression might look like:

* sparkling wine with aperitivos
* high-acid citrus white with ceviche
* mineral white with agedashi tofu
* textured white with cataplana
* rosé with nanban tofu
* barrel-aged white with gratin
* delicate white with the soup course
* fortified or late-harvest wine with dessert

Your existing “pack pairing” system already approximates this concept. However, allowing the engine to **optimize the sequence dynamically** would make the system far more powerful.

---

# Why These Three Changes Matter

Together, these improvements move the system from a rule-based matching engine to a **gastronomic reasoning model**.

Current capabilities:

* rule-based pairing
* structural filtering
* meal arc grouping

Capabilities after improvement:

* continuous compatibility scoring
* hierarchical flavor reasoning
* optimized wine progression across the menu

In other words, the system evolves from simple rule evaluation into **structured culinary reasoning**.

---

# Important Observation About Your Database

One of the most interesting aspects of your project is that the **wine database is already capable of supporting these upgrades**.

Your wine schema already includes:

* acidity
* tannins
* body
* sweetness
* finish
* aromas
* pairing affinities

Very few wine datasets include this much structural information. Because of this, the necessary improvements lie **almost entirely in the pairing engine**, not in the database.

---

# Final Assessment

Your current pairing system already ranks among the more sophisticated rule-based approaches used in restaurant environments. It correctly models:

* structural wine properties
* sensory characteristics of dishes
* meal progression
* conflict avoidance in pairing

With the three improvements described above, the system would move beyond a traditional pairing engine and approach the level of **computational gastronomy tools used in experimental kitchens and food research environments**.

In practical terms, it would become capable of generating pairings that feel less like database matches and more like the reasoning of a skilled sommelier designing a wine experience across an entire meal.

---

### Issue 2 — intensity scale slightly coarse

You use:

```
delicate
light
medium
rich
```

This works but misses an important distinction:

```
rich
very_rich
```

because **gratin is structurally heavier than cataplana**.

Not critical but worth noting.

---

# 2. Dish Pairing Schema Evaluation (dish-profiles.json)

Source: 

This file defines:

* pairing arcs
* food tags
* hard filters
* rule explanations.

This is the **core of your pairing engine**.

---

# 2.1 Meal Arc System

```
aperitivo
savory_light
savory_medium
savory_rich
dessert
```

This is **excellent**.

It reflects real wine service progression.

Example:

```
aperitivo → sparkling
light → white
medium → richer white
rich → red
dessert → sweet
```

The arcs match natural wine structure escalation.

---

# 2.2 Food Tags

Example tags:

```
shellfish
delicate
umami
silky
fried
fatty
citrus
raw
sweet_sour
layered
```

These are **precisely the right abstraction level**.

Too many systems fail by using ingredient-level tags.
You correctly use **sensory tags**.

This is a **major strength** of your architecture.

---

# 2.3 Hard Filters

Example:

```
type_allow
body_exclude
tannins_max
sweetness_allow
```

These act as **pairing safety rails**.

For example:

```
sweetness_allow: ["sweet","semi-sweet"]
```

prevents the classic mistake:

> dry wine with sweet dessert.

This is **correct professional logic**.

---

# 2.4 One Design Flaw

Hard filters do not include **alcohol control**.

Example note:

```
Wasabi calls for low alcohol
```

But the system cannot enforce it.

You should add:

```
alcohol_max
```

or

```
alcohol_prefer_low
```

Wasabi and chili dishes need this.

---

# 3. Pairing Engine Output Evaluation

Source: 

The engine generates per-dish wine suggestions.

Example:

```
Aphros Ten
Prova Régia
Covela Avesso
Aveleda Parcela
```

These are structurally correct suggestions.

---

# 3.1 Structural Matching Quality

Example:

**Goma Doufu**

Wine structure:

```
body: light
acidity: 7–10
tannins: null
```

Dish profile:

```
delicate
marine
silky
umami
```

This is **exactly correct pairing logic**.

High-acid whites cut marine richness and support umami.

---

# 3.2 Ceviche Pairing

The engine identifies:

```
high-acidity-citrus-raw
```

This is perfect.

Yuzu requires:

* very high acidity
* citrus aromatics
* low tannin.

Your suggestions match this.

---

# 3.3 Cataplana Pairing

Dish profile:

```
shellfish
rich
braised
layered
```

Rules correctly require:

```
white
medium/full body
no sweetness
```

This correctly leads to wines like:

```
Encruzado
structured whites
```

This is **professionally correct pairing**.

---

# 3.4 Gratin Pairing

Dish:

```
rich
creamy
fatty
miso
mushroom
```

Correctly modeled as:

```
full white
low tannin red possible
```

This is excellent.

Cream + umami dishes pair well with:

* Encruzado barrica
* Burgundy-style whites.

Your rules capture this perfectly.

---

# 3.5 Dessert Pairing

Rules:

```
wine sweetness ≥ dessert sweetness
```

This is **the golden rule of dessert pairing**.

Benchmarks:

```
Porto Tawny
Madeira Malmsey
Late Harvest
Moscatel
```

All correct.

---

# 4. Engine Behavior Observations

The pairing engine is **structurally sound**.

However several improvements are possible.

---

# 4.1 Ranking Saturation

Many wines get the same score:

```
score_display = 5
```

This suggests **insufficient score differentiation**.

Likely cause:

* rule stacking saturates score quickly.

You need more **penalties**.

Example:

```
+3 structural match
+2 aromatic mirror
+1 regional affinity
-2 slight mismatch
-4 structural conflict
```

This spreads scores.

---

# 4.2 Regional Diversity

The engine currently over-selects:

```
Vinho Verde
Lisboa
Dão
```

Because these wines have:

```
high acidity
light body
```

which suits the menu.

This is structurally correct but creates **regional bias**.

You may want a **diversity weighting**.

---

# 4.3 Hard Filter Leakage

Example from pairings:

```
Casal de Santa Maria Colheita Tardia
```

appearing for **aperitivos**.

This is structurally wrong.

Sweet wine with savory appetizers is rarely correct.

Your filters should exclude:

```
sweet wines
```

unless dessert.

---

# 5. Overall System Evaluation

## Menu design

Excellent.

Strong semantic modeling.

---

## Dish schema

Very good.

Minor extensions possible.

---

## Pairing logic

Professionally valid.

Rules reflect real wine pairing knowledge.

---

## Pairings produced

Mostly correct.

Only small issues:

* score saturation
* sweet wine leakage
* minor tag contamination.

---

# 6. Most Important Improvements

If you improve only three things:

### 1 — Remove shellfish tag errors

Tofu dishes incorrectly tagged.

---

### 2 — Add alcohol constraint

Needed for:

* wasabi
* chili
* vinegar.

---

### 3 — Increase scoring discrimination

Add penalties and weights.

---

# 7. Final Verdict

Your pairing system is **far more sophisticated than most restaurant pairing engines**.

It correctly models:

* structural pairing
* flavor mirroring
* meal progression
* conflict avoidance.

It is already close to a **research-grade gastronomic pairing system**.

---

If you want, I can also show you something extremely useful:

**the 3 architectural improvements that would turn this into a world-class pairing engine.**

They are surprisingly simple but extremely powerful.

---

# 8. Implementation Status (Post-Assessment)

This section documents which recommendations were implemented and the rationale for those deferred.

---

## Implemented

### Quick fixes

**1. Shellfish tag contamination removed**

`aperitivos-variados` had `"shellfish"` in `food_tags` despite being a tofu-only dish. Tag removed. `sweetness_exclude: ["sweet"]` also added to its hard filters — a sweet wine with savoury appetisers is categorically wrong regardless of structural score.

**2. Alcohol constraint enforced**

`alcohol_max: 13.5` added to `goma-doufu` hard filters (the wasabi course). `passes_filters()` in `generate-pairings.py` extended to support this key. Basis: high-alcohol wines amplify the heat of wasabi and similar irritants — a constraint with no structural proxy in the rule system.

**3. Scoring discrimination — primary tag bonus**

`PRIMARY_BONUS = 3` added to the scoring engine. Each dish in `dish-profiles.json` carries a `primary_tag` (the single food_tag most driving the pairing decision). When a rule fires and the matched rule's `food_tags` set includes the dish's `primary_tag`, the rule receives +3 pts before the dimensional-max comparison. Observed effect: 10-point spread on the Parfait course (Moscatel 31 vs Porto Tawny 21); meaningful separation on dashi courses.

---

### Architectural improvements

**Dominant flavor hierarchy (section 2 of this assessment)**

Implemented via `primary_tag`. Each dish has a declared dominant driver; the engine rewards wines that address it directly. This is a simpler and more transparent realisation of the concept than a fully hierarchical multi-level flavor structure.

**Meal-level pairing optimisation (section 3 of this assessment)**

Implemented via two mechanisms:

- `meal_arcs` grouping (already present at assessment time): courses are grouped into progression arcs (`aperitivo`, `savory_light`, `savory_medium`, `savory_rich`, `dessert`)
- Body escalation added: `sequence_pairing` mode applies a soft body preference per arc (1.5 pts/rank penalty for body mismatch on a 0–4 ordinal scale), nudging the progression from light to fuller-bodied wines without hard-excluding structurally superior candidates

---

## Deferred

**Structural vector matching (section 1 of this assessment)**

Not implemented. See "Implementation Assessment" within section 1 for full analysis. Summary: modest benefit given existing score differentiation achieved through dimensional-max + primary_tag; real overtuning risk when calibrated on a 10-dish tofu/dashi corpus; loss of explainability and generalisability relative to explicit rules. Revisit if the engine expands to multiple menus across diverse cuisines where rule maintenance becomes unmanageable.

**Regional diversity weighting**

The assessment noted over-representation of Vinho Verde and Dão due to their structural properties (high acidity, light body) naturally matching the kaiseki menu. This is structurally correct — the wines suit the food. A diversity penalty would improve visual variety at the cost of culinary accuracy. No action taken; randomisation in `sequence_pairing` and pack slots already provides variety across runs.

**Per-slot `random_top` overrides**

Some slots have a dominant top candidate; others have a tightly clustered field. Not implemented — the default `--random-top 3` produces acceptable results across all slots. Revisit if a specific slot consistently returns the same wine regardless of seed.

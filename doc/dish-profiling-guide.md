# Dish Profiling Guide

How to choose a profiling mode and annotate a dish for the Harmonix pairing engine.

---

## The Three Modes

Mode is auto-detected from the data structure — no explicit flag is written.

| Condition | Mode | Name |
|---|---|---|
| `food_tags` present, no `components` | **Mode 2** | Unified dish |
| `components` present, no `food_tags` | **Mode 1** | Composed plate |
| Both present | **Mode 3** | Dish with highlights |

---

## Choosing the Right Mode

The criterion is **the experience at the table, not the recipe**.

### Mode 2 — Unified dish
Use when the components cook or integrate together and the result presents as a **single flavor surface**. The eater encounters one unified profile, not distinct parts.

Examples: cataplana, bolognese, miso soup, risotto, stews, gratins.

Annotate with a flat `food_tags` list describing the unified profile.

```json
{
  "id": "cataplana-tofu",
  "food_tags": ["shellfish", "clam", "rich", "braised", "salty", "portuguese_dish"]
}
```

---

### Mode 1 — Composed plate
Use when components are **consumed simultaneously but independently** — the eater controls the proportion of each bite. No dish-level flavor profile exists independently of its parts.

Examples: cheese boards, charcuterie platters, sushi courses, composed salads, tapas.

Do not write `food_tags` at the dish level. Define each component separately.

```json
{
  "id": "tabua-queijo",
  "components": [
    { "name": "queijo-sao-jorge-8m", "role": "primary",           "food_tags": ["salty", "umami", "fatty_dairy", "cured"],  "generates_hard_filter": false },
    { "name": "tamaras",             "role": "dominant_challenge", "food_tags": ["sweet", "caramel"],                        "generates_hard_filter": true  },
    { "name": "crackers-alecrim",    "role": "accent",             "food_tags": ["bitter", "herbaceous"],                   "generates_hard_filter": false }
  ]
}
```

The engine derives the effective `food_tags`, `primary_tag`, and `hard_filters` from the components at runtime.

---

### Mode 3 — Dish with highlights
Use when the dish has a **clear primary identity** but one or two components are structurally significant and would be **invisible in a flat profile** — a sauce with a different profile than the protein, a sweet glaze on a savory dish, a bitter garnish that shifts the dominant dimension.

Write both `food_tags` (the base profile) and `components` (the highlights).

```json
{
  "id": "pato-laranja",
  "food_tags": ["red_meat", "grilled", "rich", "fatty_animal"],
  "components": [
    { "name": "molho-laranja", "role": "highlight", "food_tags": ["sweet", "citrus", "acidic"], "generates_hard_filter": false }
  ]
}
```

The engine starts with the dish's `food_tags` and merges the highlight tags into the effective pool. If a highlight has `generates_hard_filter: true`, its extreme tags also derive additional hard filters.

---

## Component Roles

| Role | Weight | Description |
|---|---|---|
| `dominant_challenge` | binding | The constraint that most limits wine selection. Hard filters derived here if `generates_hard_filter: true`. |
| `primary` | full | The dish's identity. Full scoring weight. |
| `secondary` | partial | Important but not dominant. |
| `accent` | minimal | Shapes aromatics. Does not drive hard filters. |
| `highlight` | additive | Mode 3 only. Merged into dish base. |

---

## `generates_hard_filter`

When `true`, the engine automatically derives a hard filter from the component's **extreme structural tags**:

| Tag | Derived hard filter |
|---|---|
| `sweet` | `sweetness_allow: ["sweet", "semi-sweet"]` |
| `bitter` | `type_prefer: ["sparkling"]` |
| `spicy` | `sweetness_allow: ["off-dry", "semi-sweet"]`, `tannins_max: 5` |

When `false`, the component's tags enter the scoring pool but impose no hard constraints. Use `false` for components that contribute flavor nuance without being binding constraints.

---

## Systemic Interactions

When certain tag pairs appear across components, the engine automatically attenuates or amplifies the effective constraint strength of the target tag before scoring. This is defined in `pairing-rules.json → systemic_interactions`.

| Tag pair | Effect | What it models |
|---|---|---|
| `salty` + `sweet` | attenuates `sweet` by 0.3 | Salt suppresses perceived sweetness |
| `salty` + `bitter` | attenuates `bitter` by 0.2 | Salt suppresses perceived bitterness |
| `acidic` + `acidic` | amplifies `acidic` by 1.4 | Stacking acidity from multiple components |
| `bitter` + `bitter` | amplifies `bitter` by 1.4 | Stacking bitterness |
| `fatty_animal` + `bitter` | attenuates `bitter` by 0.25 | Fat coats and suppresses bitterness |

These apply automatically — no annotation needed beyond tagging components correctly.

---

## Tag Reference

Tags are defined in `pairing-rules.json → food_tags_reference`. Always use tags from that vocabulary. Adding a tier-2 tag with no matching rule is safe — it fires nothing and forward-declares the tag for future rules.

**Tier 1** — Universal structural. Every dish should be fully expressible with tier-1 tags alone.
**Tier 2** — Cuisine-specific and aromatic. Optional modifiers for bonus/affinity rules.

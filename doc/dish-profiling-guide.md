# Dish Profiling Guide

How to choose a profiling mode and annotate a dish for the Harmonix pairing engine.

---

## The Three Modes

Mode is auto-detected from the data structure — no explicit flag is written.

| Condition | Mode | Name |
|---|---|---|
| `food_tags` present, no `components` | **Mode 2** | Integrado |
| `components` present, no `food_tags` | **Mode 1** | Composto |
| Both present | **Mode 3** | Com Destaque |

---

## Choosing the Right Mode

The criterion is **the experience at the table, not the recipe**.

### Mode 2 — Integrado
Use when the components cook or integrate together and the result presents as a **single flavor surface**. The eater encounters one unified profile, not distinct parts.

Examples: cataplana, bolognese, miso soup, risotto, stews, gratins.

Annotate with a flat `food_tags` list describing the unified profile.

```json
{
  "id": "cataplana-tofu",
  "food_tags": ["shellfish", "clam", "rich", "braised", "salty"]
}
```

---

### Mode 1 — Composto
Use when components are **consumed simultaneously but independently** — the eater controls the proportion of each bite. No dish-level flavor profile exists independently of its parts.

Examples: cheese boards, charcuterie platters, sushi courses, composed salads, tapas.

Do not write `food_tags` at the dish level. Define each component separately with a name and its own tags.

```json
{
  "id": "tabua-queijo",
  "components": [
    { "name": "queijo-sao-jorge-8m", "food_tags": ["salty", "umami", "fatty_dairy", "cured"] },
    { "name": "tamaras",             "food_tags": ["sweet", "caramel", "nuts"] },
    { "name": "crackers-alecrim",    "food_tags": ["bitter", "herbaceous"] }
  ]
}
```

The engine runs two scoring passes:
1. **Combination** — all component tags pooled. Hard filters auto-derived from extreme tags (`sweet`, `bitter`, `spicy`). Produces the main result set.
2. **Per component** — each component scored independently against its own tags. Only components with ≥ 2 Tier-1 structural tags are shown (narrower components are suppressed as they produce no useful independent insight).

Components have no `role` field and no `generates_hard_filter` — hard filters are always auto-derived from the pooled tag set.

---

### Mode 3 — Com Destaque
Use when the dish has a **clear primary identity** but one or two components are structurally significant and would be **invisible in a flat profile** — a sauce with a different profile from the protein, a sweet glaze on a savory dish, a bitter garnish that shifts the dominant dimension.

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

The engine merges highlight tags into the effective pool. If a highlight has `generates_hard_filter: true`, its extreme tags also derive additional hard filters on top of the base dish profile.

Mode 3 components always have `role: "highlight"`. No other role values exist.

---

## `generates_hard_filter` (Mode 3 only)

When `true`, the engine derives a hard filter from the highlight component's extreme structural tags:

| Tag | Derived hard filter |
|---|---|
| `sweet` | `sweetness_allow: ["sweet", "semi-sweet"]` |
| `bitter` | `type_prefer: ["sparkling"]` |
| `spicy` | `sweetness_allow: ["off-dry", "semi-sweet"]`, `tannins_max: 5` |

When `false`, the component's tags enter the scoring pool but impose no hard constraints. Use `false` for components that contribute flavor nuance without being binding constraints.

In Mode 1 (Composto), hard filters are **always auto-derived** from the pooled extreme tags — this field does not exist on Mode 1 components.

---

## Systemic Interactions

When certain tag pairs appear across components, the engine automatically attenuates or amplifies the effective constraint strength of the target tag before scoring. Defined in `pairing-rules.json → systemic_interactions`.

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

Tags are defined in `pairing-rules.json → food_tags_reference`. Always use tags from that vocabulary.

**Tier 1** — Universal structural. Every dish should be fully expressible with Tier-1 tags alone. Tier-1 count determines whether a Composto component qualifies for per-component display (threshold: ≥ 2).

**Tier 2** — Aromatic and descriptor. Optional modifiers for bonus/affinity rules. Adding a Tier-2 tag with no matching rule is safe — it fires nothing and forward-declares the tag for future rules.

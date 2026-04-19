# CLAUDE.md — Harmonix

Harmonix is a **general-purpose, rule-based wine pairing engine** for Portuguese wines.
It scores any dish against a wine database using deterministic structural rules derived
from the Harrington Sensorial Pyramid. No AI inference at runtime — all computation is
pure deterministic scoring.

Origin: extracted and generalized from the Nanban restaurant project (`rodfig/nanban`).
The nanban menu (Japanese-Portuguese kaiseki) remains in the repo as the **pilot/reference menu**.

---

## Architecture Overview

```
data/wine-profiles/
  wines-compiled.json        ← compiled wine database (~100 Portuguese wines)
  pairing-rules.json         ← scoring rules + tag vocabulary
  producers-*.json           ← regional source files (input to compile-wines.py)

data/menus/<menu-name>/
  menu.json                  ← presentation: dish names, descriptions, sequence
  dish-profiles.json         ← pairing: food_tags, components, hard_filters
  pairings.json              ← generated output (do not edit manually)

scripts/
  generate-pairings.py       ← main scoring engine
  compile-wines.py           ← compiles producers-*.json → wines-compiled.json

js/pairing-engine.js         ← frontend: loads pairings.json, renders pairing modal
css/pairing-modal.css        ← pairing UI styles
```

### Data Flow

```
producers-*.json
    ↓ compile-wines.py
wines-compiled.json  +  pairing-rules.json  +  dish-profiles.json
    ↓ generate-pairings.py
pairings.json
    ↓ pairing-engine.js (browser)
Pairing modal UI
```

### Scoring Algorithm (generate-pairings.py)

For each dish × wine pair:
1. Apply `hard_filters` — eliminate wines that fail type/body/sweetness/tannin constraints
2. For each rule: check `dish.food_tags ∩ rule.food_tags ≠ ∅` AND `wine satisfies rule.wine_condition`
3. `score_bonus` rules accumulate freely; all other rules use **dimensional max** (one best rule per dimension counts)
4. `primary_tag` bonus: rules addressing the dish's dominant element receive +3 pts
5. Sort by total score; top N returned per dish

Dimensions: `acidity` · `body` · `tannin` · `sweetness` · `style` · `finish` · `conflict_acidity` · `conflict_body` · `conflict_tannin`

---

## Pairing Theory — Harrington Sensorial Pyramid

The rules implement Harrington's pyramid in three layers:

### Base — SAUDA (dish) / ADE (wine)
| Layer | Acronym | Components |
|---|---|---|
| Dish base | **SAUDA** | **S**alinidade · **A**cidez · **U**mami · **D**oçura · **A**margor |
| Wine base | **ADE** | **A**cidez · **D**oçura · **E**fervescência |

### Texture — GMPC (dish) / CATA (wine)
| Layer | Acronym | Components |
|---|---|---|
| Dish texture | **GMPC** | **G**ordura · **M**étodo · **P**roteína · **C**orpo |
| Wine texture | **CATA** | **C**orpo · **Á**lcool · **T**aninos · c**A**rvalho |

### Sabores — AIP
**A**roma · **I**ntensidade · **P**ersistência

### Harrington Rules Implemented
| Rule | Description | Engine Coverage |
|---|---|---|
| R1 | Wine ≥ sweetness of dish | `sweet-fortified-*`, `moscatel-*`, `off-dry-*` rules; hard filters on dessert dishes |
| R2 | Wine acidity ≥ dish acidity | Multiple `high-acidity-*` positive rules |
| R3 | Salty dish → sparkling | `sparkling-salty-food` *(Phase 1)* |
| R4 | Bitter dish → sparkling attenuates | `sparkling-bitter-food` *(Phase 1)* |
| R5 | Tannins + animal fat | `high-tannin-red-fatty-meat` |
| R6 | Acidity + vegetal/dairy fat | Covered by high-acidity positive rules |
| R7/R8 | Body/intensity equivalence | `light-body-delicate-dishes`, `full-body-*`, `conflict-light-body-rich-stew`, `conflict-heavy-body-delicate` *(Phase 1)* |
| R9 | Spicy → off-dry, high acidity | `off-dry-spicy-food` *(Phase 1, dormant)* |
| R10 | Similarity or contrast | `bonus-regional-affinity`, `bonus-citrus-citrus-mirror`, `bonus-floral-delicate-steam` |
| R11 | Finish equivalence | `very-long-finish-complex`, `long-finish-lingering` |
| R13 | Salt softens tannins | `bonus-salt-tannin-softening` *(Phase 1)* |
| R14 | Low acidity + acidic dish = flácido | `conflict-low-acid-acidic-food` *(Phase 1)* |
| R15 | Balance — wine complements, not competes | Meta-principle; embedded in dimensional design |

---

## Implementation Plan

### Phase 1 — Rule Additions *(next task)*
**Files:** `data/wine-profiles/pairing-rules.json`, `data/menus/nanban-kaiseki/dish-profiles.json`
**Type:** Data only. No code changes.

Add 6 new rules:

| ID | Harrington | Fires on tags | Wine condition | Score | Dimension |
|---|---|---|---|---|---|
| `conflict-low-acid-acidic-food` | R14 | `acidic`, `citrus`, `lemon_based` | `acidity <= 5` | −5 | `conflict_acidity` |
| `conflict-heavy-body-delicate` | R7/R8 | `delicate`, `light` | `body == "full"` | −6 | `conflict_body` |
| `bonus-salt-tannin-softening` | R13 | `salty` | `tannins >= 5` | +2 (bonus) | — |
| `sparkling-salty-food` | R3 | `salty` | `type == "sparkling"` | +6 | `body` |
| `sparkling-bitter-food` | R4 | `bitter` | `type == "sparkling"` | +5 | `style` |
| `off-dry-spicy-food` | R9 | `spicy` | `sweetness == "off-dry"`, `acidity >= 7` | +7 | `sweetness` |

Also add to `food_tags_reference`:
- New tier-1 tags: `salty`, `bitter`, `spicy`
- Add `"tier"` field (1 = universal structural, 2 = cuisine-specific/aromatic) to all existing tags
- Document two-tier governance rules

Add `salty` to `cataplana-tofu` food_tags in `data/menus/nanban-kaiseki/dish-profiles.json`.

**Not added:** R1 violation (enforced by hard filters at dish level), R6/R12 (redundant with existing acidity coverage), R15 (meta-principle).

### Phase 2 — Three-Mode Dish Profile Schema

#### Phase 2a — Schema Definition + Interaction Table
**Files:** `data/wine-profiles/pairing-rules.json` (new section), `doc/dish-profiling-guide.md` (new)
**Type:** Data + docs. No code changes.

#### The Three Modes

Mode is auto-detected from data structure — no explicit flag:

| Condition | Mode | Description |
|---|---|---|
| `food_tags` present, no `components` | **Mode 2** | Unified dish — current model, unchanged |
| `components` present, no `food_tags` | **Mode 1** | Composed plate — profile derived from components |
| Both present | **Mode 3** | Dish with highlights — base profile + component modifiers |

**When to use each mode:**
- **Mode 2:** Components cooked together into a unified flavor surface (cataplana, bolognese, stews). Profile described as a whole.
- **Mode 1:** Components consumed simultaneously but independently — the eater controls proportions (cheese boards, charcuterie, sushi, composed salads). No dish-level flavor profile exists independent of its parts.
- **Mode 3:** Dish has a clear primary identity but one or two components are structurally significant and invisible in a flat profile (a sauce with a different profile than the protein, a bitter garnish, a sweet glaze).

#### Component Schema

```json
{
  "id": "tabua-queijo",
  "components": [
    {
      "name": "queijo-sao-jorge-8m",
      "role": "primary",
      "food_tags": ["salty", "umami", "fatty_dairy", "cured", "medium_intensity"],
      "generates_hard_filter": false
    },
    {
      "name": "tamaras",
      "role": "dominant_challenge",
      "food_tags": ["sweet", "caramel", "medium_intensity"],
      "generates_hard_filter": true
    },
    {
      "name": "crackers-alecrim",
      "role": "accent",
      "food_tags": ["bitter", "herbaceous"],
      "generates_hard_filter": false
    }
  ]
}
```

**`role` values:**
- `dominant_challenge` — the binding constraint; if `generates_hard_filter: true`, its extreme tags derive hard filters automatically (e.g., `sweet` → `sweetness_allow: ["sweet","semi-sweet"]`)
- `primary` — the dish's identity; full scoring weight
- `secondary` — important but not dominant
- `accent` — shapes aromatics; minimal structural weight
- `highlight` — Mode 3 only; added to dish base profile

#### Systemic Interaction Table

New section in `pairing-rules.json`:

```json
"systemic_interactions": [
  { "tags": ["salty", "sweet"],        "effect": "attenuation", "target": "sweet",  "factor": 0.3 },
  { "tags": ["salty", "bitter"],       "effect": "attenuation", "target": "bitter", "factor": 0.2 },
  { "tags": ["acidic", "acidic"],      "effect": "stacking",    "target": "acidic", "factor": 1.4 },
  { "tags": ["bitter", "bitter"],      "effect": "stacking",    "target": "bitter", "factor": 1.4 },
  { "tags": ["fatty_animal", "bitter"],"effect": "attenuation", "target": "bitter", "factor": 0.25 }
]
```

Applied automatically when tag pairs appear across components. Modifies effective constraint strength before hard filter derivation.

#### Phase 2b — Annotation Guidance Document
**File:** `doc/dish-profiling-guide.md` (new)
**Type:** Docs only.

Short markdown defining when to use each mode. The criterion is the experience at the table, not the recipe:
- **Mode 2** when components cook or integrate together and the result presents as a unified flavor experience
- **Mode 1** when components are consumed simultaneously but independently — the eater controls the proportion of each (boards, platters, sushi, composed salads)
- **Mode 3** when the dish has a clear primary identity but one or two components are structurally significant and would be invisible in the flat profile (sauces, glazes, garnishes that alter the dominant flavor dimension)

#### Phase 2c — Code Change — `resolve_dish_profile()`

Add one preprocessing function in `scripts/generate-pairings.py`, called in `load_data()` before scoring. The `score_wine()` function is unchanged — it always receives a flat resolved profile.

```python
def resolve_dish_profile(dish, interaction_table):
    """
    Detect mode and compute effective food_tags, primary_tag,
    hard_filters from components (Mode 1) or merge highlights
    into dish base (Mode 3). Mode 2 passes through unchanged.
    """
    components = dish.get('components', [])
    has_dish_tags = bool(dish.get('food_tags'))
    if not components:
        return dish  # Mode 2 — unchanged
    if has_dish_tags:
        # Mode 3: merge highlight tags into dish base
        ...
    else:
        # Mode 1: derive everything from components
        ...
```

### Phase 3 — Client-Side JS Engine
**Files:** `js/pairing-engine.js` (new `js/pairing-scorer.js`)
**Type:** Code (JavaScript port of Python scoring logic).

Port `generate-pairings.py` scoring logic to JavaScript. Browser loads raw data files instead of pre-computed `pairings.json`. Computation runs in-browser — no backend, no AI, no server.

**Before (current):**
```javascript
fetch(`data/menus/${ACTIVE_MENU}/pairings.json`)
```

**After:**
```javascript
Promise.all([
  fetch('data/wine-profiles/wines-compiled.json'),
  fetch('data/wine-profiles/pairing-rules.json'),
  fetch(`data/menus/${ACTIVE_MENU}/dish-profiles.json')
]).then(([wines, rules, dishes]) => {
  pairingsData = computePairings(wines, rules, dishes);
});
```

Functions to port: `parse_cond`, `check_condition`, `passes_filters`, `score_wine`, `build_per_dish`, `resolve_dish_profile`.
Total: ~200 lines JS. No external dependencies.

The pre-computed `pairings.json` becomes optional (performance cache). The engine works from source data.

**The Form Extension** (also Phase 3): a client-side dish profiling form that:
1. Loads tag vocabulary from `food_tags_reference` in `pairing-rules.json`
2. Collects dish profile (mode, components, food_tags, hard filters) via UI
3. Calls the in-browser scoring function with the new dish profile
4. Displays results immediately — no backend, no API call, no AI inference

---

## Tag Vocabulary — Two-Tier System

Tags are the bridge between dishes and rules. A rule fires only if `dish.food_tags ∩ rule.food_tags ≠ ∅`.

**Tier 1 — Universal structural tags.** Every dish must be expressible using only these. Rules on tier-1 tags are universal — they apply to any cuisine.

```
Flavor (SAUDA):   salty · acidic · sweet · bitter · umami · spicy
Fat type:         fatty_animal · fatty_dairy · fatty_vegetal · lean
Method:           raw · fried · grilled · roasted · sauteed · poached · braised · steamed · cured · smoked · gratin
Protein:          red_meat · white_meat · poultry · pork · game · oily_fish · fish_fatty · fish_lean · shellfish · egg · plant_protein · tofu
Intensity:        delicate · medium_intensity · rich · intense
Texture:          light · creamy · crunchy · silky · robust · fatty
```

**Tier 2 — Aromatic and descriptor tags.** Optional. Trigger bonus rules for aromatic concordance. Adding a tier-2 tag with no corresponding rule is harmless. No cultural or regional tags — all dish description is structural and universal.

```
Aromatic:     citrus · floral · herbaceous · earthy · warm_spiced · mushroom · marine · nutty · smoky · resinous · oxidative
Descriptors:  sweet_sour · marinade · fermented · pickled · layered · complex · dessert · nuts · caramel · chocolate · custard · lemon_based · honey
```

**Governance:** New tags are added to `food_tags_reference` in `pairing-rules.json` before use. New tier-2 tags in a dish profile without corresponding rules fire nothing — they are forward declarations for rules not yet written.

---

## Wine Database

**Source:** `data/wine-profiles/producers-*.json` (one file per region)
**Compiled output:** `data/wine-profiles/wines-compiled.json`
**Rebuild:** `python scripts/compile-wines.py`

Regions covered: Alentejo · Azores · Bairrada · Beira Interior · Dão · Douro ·
Lisboa · Madeira · Porto · Setúbal · Tâmega-Sousa (Vinho Verde) · Tejo ·
Trás-os-Montes · Távora-Varosa

Wine structural fields used in scoring:
- `structure.acidity` (1–10)
- `structure.tannins` (1–10)
- `structure.body` (light / medium-light / medium / medium-full / full)
- `structure.sweetness` (dry / off-dry / semi-sweet / sweet)
- `structure.finish` (short / medium / long / very-long)
- `type` (white / red / rosé / sparkling / fortified)
- `alcohol` (%)

**Scope decision:** Currently Portuguese wines only, but the engine is designed to accept any wine from any region. Dish descriptions are fully structural — no regional or cultural tags. Any cuisine can be described using the universal tag vocabulary.

---

## Running the Engine

```bash
# Generate pairings for a menu
python scripts/generate-pairings.py --menu nanban-kaiseki

# Options
python scripts/generate-pairings.py --menu nanban-kaiseki \
  --top-per-dish 10 \
  --pack-min-price 15 \
  --pack-max-price 45 \
  --seed 42

# Rebuild wine database after editing producers-*.json
python scripts/compile-wines.py

# Validate wine database
python data/wine-profiles/validate-schema.py
```

Output: `data/menus/<menu>/pairings.json` (consumed by `pairing-engine.js`)

---

## Adding New Rules

1. Open `data/wine-profiles/pairing-rules.json`
2. Add entry to `"rules"` array following the existing schema:
```json
{
  "id": "my-new-rule",
  "dimension": "acidity",
  "food_tags": ["acidic", "citrus"],
  "wine_condition": { "acidity": ">= 8" },
  "score": 8,
  "reason": "Explanation shown in pairing modal",
  "notes": "Internal rationale (not displayed)"
}
```
3. For conflict rules: use negative `score` and prefix id with `conflict-`
4. For bonus rules: use `score_bonus` instead of `score` (no dimension needed)
5. Regenerate: `python scripts/generate-pairings.py --menu <menu>`

---

## Adding a New Menu

1. Create folder: `data/menus/<menu-name>/`
2. Create `menu.json` (dish presentation fields — name, description, sequence, course_label)
3. Create `dish-profiles.json` (pairing fields — food_tags or components, hard_filters, meal_arc)
4. Run: `python scripts/generate-pairings.py --menu <menu-name>`

For `dish-profiles.json`, choose the profiling mode:
- **Mode 2** (default): fill `food_tags` directly. For integrated dishes.
- **Mode 1**: fill `components` array only, no `food_tags`. For composed plates/boards.
- **Mode 3**: fill both `food_tags` (base) and `components` (highlights). For dishes with structurally significant components.

---

## Deployment

Vercel project: **harmonix** (separate from nanban)
GitHub repo: `rodfig/harmonix`
Branch: `main` → auto-deploys to Vercel on push

No build step. No backend. Static files only.

```bash
git add <files>
git commit -m "message"
git push origin main   # triggers Vercel deploy
```

Git email for Vercel auth: `rodfig@gmail.com` (must match Vercel account)
Verify: `git config user.email` → must return `rodfig@gmail.com`

---

## Branch Strategy

Feature branches for planned work:

| Branch | Phase | Scope |
|---|---|---|
| `feature/harrington-rules` | Phase 1 | Add 6 rules + tag tier system + `salty` on cataplana |
| `feature/component-profiling` | Phase 2a/2b/2c | Three-mode schema + annotation guide + `resolve_dish_profile()` |
| `feature/engine-js-port` | Phase 3 | Port scoring to JS + form extension, remove pairings.json dependency |

Phase 3 is independent of 1 and 2 — can be developed in parallel.
Phase 2 depends on Phase 1 being merged first (needs new tags defined).

---

## Relationship to Nanban (`rodfig/nanban`)

- Nanban is a **consumer** of the engine concept — a restaurant product
- Harmonix is the **engine itself** — general-purpose, not restaurant-branded
- The nanban-kaiseki menu in `data/menus/nanban-kaiseki/` is the **pilot/reference menu**, kept for continuity and testing
- Wine DB source files (`wine profiles/*.txt`) remain in Projeto Final as source-of-truth; Harmonix works from the compiled `wines-compiled.json`
- Changes to the wine database should be made in Projeto Final, compiled, and the output copied to Harmonix (until the DB workflow is consolidated here)

---

## Key Files for Context

| File | Purpose |
|---|---|
| `data/wine-profiles/pairing-rules.json` | All scoring rules + tag vocabulary. Read this first. |
| `data/wine-profiles/wines-compiled.json` | Full wine database |
| `data/menus/nanban-kaiseki/dish-profiles.json` | Best example of dish profiling |
| `scripts/generate-pairings.py` | Scoring engine — the core logic |
| `doc/pairing-system-assessment.md` | Critical audit of current rules vs. wine DB |
| `doc/PAIRING-STRATEGY.md` | Strategic context for the engine |
| `doc/PAIRING-QUICKSTART.md` | How to run everything quickly |

---

---

## Consulta / Matriz — Ideas Backlog

Features to consider for future sessions. All client-side, no backend required.

### Result filtering & sorting

| Idea | Description | Notes |
|---|---|---|
| **Region filter** | Filter results by wine region (DOC/DOP). Multi-select or indifferent. Regions come from `wine.doc` field in `wines-compiled.json`. | Implemented as pills like the type filter. |
| **Sort by score** | Results already sort by score by default. Consider explicit sort toggle: score desc / score asc / random. Reshuffle button already covers random. | May be redundant given current defaults. |
| **Score cutoff** | Slider or input to set minimum score threshold (e.g. only show wines scoring ≥ 10). "Indifferent" = no cutoff. | Currently score > 0 is the only filter. A cutoff of 8–10 would focus on strong matches only. |

### Rules gaps identified

| Tag | Gap | Rule needed |
|---|---|---|
| `fatty_dairy` | Rule added (`high-acidity-dairy-fat`, score 7, acidity ≥ 7, no type constraint). | Done. |
| `fatty_animal` | No dedicated rule — covered indirectly by `high-tannin-red-fatty-meat`. Direct acidity rule missing for animal fat + white wine pairings. | Consider `high-acidity-animal-fat` for grilled fish with butter, etc. |
| `fatty_vegetal` | No rule — olive oil, nut-based sauces have no scoring signal. | Consider a body/acidity rule for vegetal fat. |
| `grilled` | No rule — grilling creates Maillard/char complexity that benefits structured wines. | Possible: `structured-wine-grilled-protein` targeting medium+ body and finish. |
| `poultry` | No dedicated rule — covered by generic body/intensity rules. | Acceptable for now. |

### Tag vocabulary notes

- `steamed` fires `light-body-delicate-dishes` — correct.
- `variety` (heterogeneous plate) has no rule — sparkling is the logical recommendation but no rule encodes it.
- Dessert cluster (`dessert`, `nuts`, `caramel`, `chocolate`, `custard`) fires existing sweet-wine rules via the `sweet` tag, but not via the specific descriptors. Consider rules targeting `chocolate` → fortified/tawny, `custard` → moscatel.

*Harmonix — April 2026. Generalized from rodfig/nanban.*

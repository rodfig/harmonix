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

Dimensions: `acidity` · `body` · `tannin` · `sweetness` · `finish` · `bonus` · `conflict_acidity` · `conflict_body` · `conflict_sweetness` · `conflict_tannin`

**Three-stage funnel (implemented):** (1) hard filters eliminate type/body/sweetness incompatibilities before scoring; (2) structural rules — all type-free, property-only conditions; (3) bonus rules accumulate identity-specific concordance (tawny/madeira/moscatel) and categorical advantages (sparkling effervescence). No `type: white/red` in structural rules — any wine scores on its properties alone.

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
| R1 | Wine ≥ sweetness of dish | `sweet-wine-rich-desserts`, `off-dry-sweet-umami`, `off-dry-spicy-food`; hard filters on dessert dishes |
| R2 | Wine acidity ≥ dish acidity | Multiple `high-acidity-*` positive rules |
| R3 | Salty dish → sparkling | `bonus-sparkling-salty` |
| R4 | Bitter dish → sparkling attenuates | `bonus-sparkling-bitter` |
| R5 | Tannins + animal fat | `high-tannin-fatty-meat` |
| R6 | Acidity + vegetal/dairy fat | `high-acidity-fat`, `high-acidity-dairy-fat` |
| R7/R8 | Body/intensity equivalence | `light-body-delicate-dishes`, `full-body-rich-dishes`, `conflict-light-body-rich-stew`, `conflict-heavy-body-delicate` |
| R9 | Spicy → off-dry, high acidity | `off-dry-spicy-food`; `conflict-high-alcohol-spicy` |
| R10 | Similarity or contrast | `bonus-citrus-mirror`, `bonus-floral-delicate-steam`, `bonus-herbaceous-mirror` |
| R11 | Finish equivalence | `very-long-finish-complex`, `long-finish-lingering` |
| R13 | Salt softens tannins | `bonus-salt-tannin-softening` |
| R14 | Low acidity + acidic dish = flácido | `conflict-low-acid-acidic-food` |
| R15 | Balance — wine complements, not competes | Meta-principle; embedded in dimensional design |

---

## Implementation Status

All three planned phases are complete and merged to `main`.

### Phase 1 — Rule Additions ✓
Harrington rules R3, R4, R9, R13, R14, R7/R8 added. Two-tier tag vocabulary established with `_tier` field on all tag groups. `salty` added to `cataplana-tofu`.

### Phase 2 — Three-Mode Dish Profile Schema ✓
- **Schema:** `component_schema` and `systemic_interactions` sections added to `pairing-rules.json`
- **Modes:** auto-detected from data structure (Mode 1: components only; Mode 2: food_tags only; Mode 3: both)
- **Code:** `resolveDishProfile()` implemented in `js/pairing-scorer.js`

### Phase 3 — Client-Side JS Engine ✓
- `js/pairing-scorer.js`: full in-browser scoring engine (45 rules, all modes, dimensional max, bonus accumulation)
- `js/harmonix.js`: dish form, tag picker, `createDishForm()`, `buildWineCardEl()`
- `consulta.html`: interactive Consulta page using the in-browser engine
- No backend, no pre-computed `pairings.json` dependency for the Consulta page

### Three-Stage Funnel Refactor ✓ *(April 2026)*
All `type: white/red` conditions removed from structural rules. `style` dimension eliminated. Identity-specific and sparkling rules converted to accumulating `bonus` dimension (`score_bonus`). 45 rules, 10 dimensions. Engine is now fully property-driven — any wine from any region scores on structural properties alone.

---

## Tag Vocabulary — Two-Tier System

Tags are the bridge between dishes and rules. A rule fires only if `dish.food_tags ∩ rule.food_tags ≠ ∅`.

**Tier 1 — Universal structural tags.** Every dish must be expressible using only these. Rules on tier-1 tags are universal — they apply to any cuisine.

```
Flavor (SAUDA):   salty · acidic · sweet · bitter · umami · spicy
Fat type:         fatty_animal · fatty_dairy · fatty_vegetal · lean
Method:           raw · fried · grilled · roasted · sauteed · poached · braised · steamed · cured · smoked
Protein:          red_meat · poultry · pork · game · fish_lean · fish_rich · shellfish · egg · plant_protein
Intensity:        delicate · rich · intense
Texture:          light · creamy · fatty
```

**Tier 2 — Aromatic and descriptor tags.** Optional. Trigger bonus rules for aromatic concordance. No cultural or regional tags — all dish description is structural and universal.

```
Aromatic:     citrus · floral · herbaceous · earthy · warm_spiced · mushroom · marine · nutty · smoky · oxidative
Descriptors:  sweet_sour · marinade · fermented · pickled · dessert · nuts · caramel · chocolate · custard · honey · lingering
```

**Governance:** New tags are added to `food_tags_reference` in `pairing-rules.json` before use. Every tag in the vocabulary must fire at least one rule — a tag that fires nothing misleads the picker.

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
3. For conflict rules: use negative `score`, prefix id with `conflict-`, use a `conflict_*` dimension
4. For bonus rules: use `score_bonus` instead of `score`, set `"dimension": "bonus"`
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

All planned phases are merged to `main`. Work directly on `main` for incremental rule or vocab changes. Use feature branches only for multi-session structural work (new scoring dimensions, schema changes, new pages).

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

# WINE PAIRING SYSTEM — STRATEGY & REFERENCE

**Status:** Fully implemented and live
**Last updated:** March 2026
**Replaces:** PAIRING-PLAN.md (planning document, now superseded)

---

## CONCEPT

The pairing system is structural, not curatorial. It does not encode a fixed list of
"good pairings" — it scores any wine in the database against any dish using a set of
structural rules (acidity, body, tannins, sweetness, style, finish). This means:

- Adding new wines to the DB automatically makes them eligible candidates
- Adding a new menu requires only a dish-profiles file, not new rules
- Pairing quality scales with DB quality, not with hand-curation effort

The guest-facing output is intentionally minimal: wine name, producer, region, price.
No pairing rationale is shown — the wine speaks for itself.

---

## DATA FLOW

```
producers-[region].json  (14 source files, 443 wines)
         ↓  scripts/compile-wines.py
data/wine-profiles/wines-compiled.json  (flat array, carta_price pre-computed)
         ↓  scripts/generate-pairings.py --menu nanban-kaiseki
         ↓  (merges menu.json + dish-profiles.json)
data/menus/nanban-kaiseki/pairings.json  (pre-computed, 4 modes)
         ↓  js/pairing-engine.js loads on page
         ↓  user clicks 🍷 on dish
pairing modal (top 3 candidates shown, up to 10 available)
```

**Recompile trigger:** rerun `generate-pairings.py` whenever any of these change:
- `data/wine-profiles/wines-compiled.json` (i.e., after `compile-wines.py`)
- `data/menus/<menu>/menu.json`
- `data/menus/<menu>/dish-profiles.json`
- `data/wine-profiles/pairing-rules.json`

---

## SCORING MODEL — DIMENSIONAL MAX

Rules are grouped into **dimensions**. Within each dimension only the highest-scoring
rule contributes to the total. This prevents multiple rules for the same structural
property from stacking unrealistically.

| Dimension | Rules |
|---|---|
| `acidity` | high-acidity-raw-fish, high-acidity-citrus-raw, high-acidity-shellfish, high-acidity-red-fatty-fish, high-acidity-soy-condiment |
| `body` | light-body-delicate-dishes, medium-body-fried-light, full-body-white-rich-dishes, full-body-red-robust-stews, conflict-light-body-rich-stew |
| `tannin` | high-tannin-red-fatty-meat, low-tannin-red-light-meat, medium-red-grilled-meat, fresh-structured-red-umami, conflict-high-tannin-delicate-fish |
| `sweetness` | off-dry-miso-sweet, sweet-fortified-rich-desserts, conflict-sweet-wine-savory-intense |
| `style` | sparkling-aperitif-variety, aromatic-white-umami, madeira-acidic-fortified-acidic-dishes, dry-madeira-acidic-fried, tawny-port-nut-desserts, moscatel-sweet-aromatic-desserts |
| `finish` | very-long-finish-complex (8pts), long-finish-lingering (5pts) |
| `bonus` | bonus-regional-affinity, bonus-citrus-citrus-mirror, bonus-floral-delicate-steam, conflict-sweetness-pickled (−7) *(all stack — each is a distinct matching criterion; negative bonus always applies regardless of positive rules in other dimensions)* |

**Conflict rules** carry negative scores (−7 to −10). If no positive rule fires in that
dimension the penalty applies.

**Score range:** practical top scores 22–37 (2–3 strong dimensions + finish + bonus + primary_tag bonus).
`to_grapes` thresholds: ≥22 → 5, ≥16 → 4, ≥10 → 3, ≥6 → 2, else 1.

### Primary Tag Bonus

Each dish in `dish-profiles.json` carries a `primary_tag` — the single food_tag that most
drives the pairing decision (e.g. `shellfish` for Goma Doufu, `citrus` for Ceviche de Tofu,
`sweet_sour` for Nanban-zuke de Tofu).

When a rule fires **and** the dish's `primary_tag` appears in that rule's `food_tags`
condition, the rule receives an additional **+3 points** (`PRIMARY_BONUS`). This bonus
is applied before the dimensional-max comparison, so it can promote a weaker rule if it
fires on the dominant element.

Effect: wines that directly address the dish's most important flavour signal receive a
meaningful score boost — creating clear separation between structurally similar candidates
that might otherwise cluster at the same score.

### Rule Design Principles

- **One rule per structural fact.** A dish needing high acidity AND light body fires rules
  in two separate dimensions — both contribute. This is correct.
- **Same dimension = competing rules.** A dish tagged `raw_fish + shellfish` fires both
  `high-acidity-raw-fish` (10) and `high-acidity-shellfish` (9) — both in acidity.
  Only 10 contributes.
- **Bonus rules are exempt.** They represent aromatic/cultural resonance (citrus mirror,
  regional affinity) — distinct from structural dimensions and deliberately small (+2 each).

---

## HARD FILTER SYSTEM

Hard filters in `dish-profiles.json` exclude wines before scoring. A wine that fails a
hard filter is never scored, regardless of how well it would otherwise match.

### Supported Keys

| Key | Type | Effect |
|---|---|---|
| `type_allow` | list of strings | Only wines of these types are eligible (`white`, `red`, `sparkling`, `rosé`, `fortified`) |
| `body_allow` | list of strings | Only wines with one of these body values are eligible |
| `body_exclude` | list of strings | Wines with these body values are excluded |
| `sweetness_allow` | list of strings | Only wines with one of these sweetness values are eligible |
| `sweetness_exclude` | list of strings | Wines with these sweetness values are excluded |
| `tannins_max` | number | Wines with tannins above this value are excluded |
| `alcohol_max` | number | Wines with alcohol (%) above this value are excluded |

### Design Principle

Hard filters express **absolute incompatibilities** — cases where no amount of structural
score should override the pairing. They are not used to guide preference (that is the
scoring engine's job). When in doubt, use a softer filter (lower `tannins_max` threshold)
rather than a hard type exclusion.

### Case Study: cataplana-tofu and `sweetness_exclude`

Late harvest whites (Frei João Colheita Tardia, Casal de Santa Maria Colheita Tardia)
have high acidity (8–9/10) which fires the shellfish acidity rule and produces a high
structural score for the cataplana course. However, sweet wines are categorically wrong
for a briny shellfish stew regardless of their acidity.

The `conflict-sweet-wine-savory-intense` rule in the sweetness dimension was not firing
because cataplana lacked the specific tags that activate that rule. Rather than patching
the tags (which would require careful cross-checking against all other dishes), adding
`sweetness_exclude: ["sweet"]` to cataplana's hard filters is the correct fix — it
expresses an absolute constraint, not a structural preference.

**Lesson:** when a wrong wine type keeps appearing despite scoring well, the correct fix
is usually a hard filter addition, not a score adjustment.

---

## GENERATION ALGORITHM

`scripts/generate-pairings.py` generates four pairing modes:

| Mode | Description |
|---|---|
| `per_dish` | Top N candidates per dish, scored and sorted |
| `meal_suggestion` | 3-role recommendation (sparkling/white · red · dessert) |
| `pack_pairings` | 2 curated packs covering the full meal (Pack A: classic, Pack B: two whites) |
| `sequence_pairing` | One wine per course, no repeats, greedy assignment |

### CLI Parameters

```bash
python scripts/generate-pairings.py --menu nanban-kaiseki [options]
```

| Parameter | Default | Description |
|---|---|---|
| `--menu` | *(required)* | Menu subfolder name under `data/menus/` |
| `--top-per-dish` | `20` | Number of candidates to store per dish in `per_dish` mode |
| `--pack-min-price` | `10.0` | Minimum carta price (€) per wine in pack pairings |
| `--pack-max-price` | `50.0` | Maximum carta price (€) per wine in pack pairings |
| `--random-top` | `3` | Pick randomly from the top-N candidates per slot |
| `--seed` | *(none)* | Integer seed for reproducible results; omit for a fresh draw |

### Price Filtering (Pack Mode)

Price filtering applies to `carta_price` (menu markup price), falling back to `price_eur`
(retail) if `carta_price` is not available. Wines with no price data at all are not
excluded — unknown price is not the same as expensive.

**Default range €10–€50** was chosen to:
- Exclude very cheap wines (below €10 carta) that would undermine pack credibility
- Exclude premium bottles (above €50 carta) that price the pack out of accessible range
- Leave a broad mid-range where quality Portuguese wines are well represented

Price filtering does **not** apply to `per_dish` or `sequence_pairing` modes — those modes
are informational and should show the best structural match regardless of price.

### Randomisation Design

Both pack slots and sequence courses use **top-N random selection** (Option A):

1. Score and sort all eligible candidates for the slot
2. Take the top `--random-top` candidates (default: 3)
3. Pick one at random from that pool

**Why top-N and not score-weighted random:** score-weighted selection would almost always
pick the top candidate (if one wine scores 24 and the next scores 8, it wins ~75% of the
time). Top-N random gives each of the genuinely good candidates an equal chance, producing
meaningfully different selections across runs.

**Why 3 as default:** a pool of 3 provides real variety without straying into candidates
that scored significantly worse. At top-5, occasional selections feel arbitrary; at top-2,
diversity is limited.

**Seed usage:**
```bash
# Fresh draw — different result each run
python scripts/generate-pairings.py --menu nanban-kaiseki

# Reproducible — note the seed from console output "Seed: 42"
python scripts/generate-pairings.py --menu nanban-kaiseki --seed 42
```

When you find a result you like, note the seed from the console line `Seed: 42` and
reuse it to lock that selection into `pairings.json` for production.

### Body Escalation (sequence_pairing)

The sequence pairing applies a **soft body preference** to nudge course selection toward
a natural progression from lighter to fuller-bodied wines across the meal.

Each arc has a target body level:

| Arc | Target body |
|---|---|
| `aperitivo` | `light` |
| `savory_light` | `light` |
| `savory_medium` | `medium` |
| `savory_rich` | `medium-full` |
| `dessert` | *(no preference)* |

The penalty is `1.5 pts × |rank_diff|`, where `rank_diff` is the absolute difference
between the wine's body and the arc's target body on the ordinal scale
`light=0, medium-light=1, medium=2, medium-full=3, full=4`.

This is a **soft adjustment** — it re-ranks candidates within the pool but does not
eliminate wines whose body does not match the arc preference. A structurally superior
wine (high score from strong rules) can still be selected even if it sits one body
level away from the arc target.

### Pack Configuration

Packs are defined in `pairing_config.pack_pairings` inside `dish-profiles.json`. Each
pack has a list of slots; each slot defines:

- `arc` — internal identifier
- `arc_label` — display label shown in the UI (e.g. "Espumante", "Branco Encorpado")
- `type_filter` — list of wine types eligible for this slot
- `dish_arcs` — which meal arcs this slot covers
- `prefer_body` — target body level for tiebreaking within the scored pool
- `prefer_fortified` — boolean, used for dessert slot to prefer/avoid fortified wines

To reconfigure packs (e.g. add a third pack, change slot structure), edit
`pairing_config.pack_pairings` in `dish-profiles.json` — no script changes needed.

---

## MENU DATA SCHEMA

### Design: two-file split per menu

Each menu lives under `data/menus/<menu>/` and uses two JSON files with strictly
separated concerns:

| File | Purpose | Author |
|---|---|---|
| `menu.json` | Presentation — what the guest sees (dish names, course labels, descriptions, images, culinary properties) | When menu changes |
| `dish-profiles.json` | Pairing — what the engine uses (food_tags, hard_filters, meal_arcs, pairing_config) | When pairing logic changes |

**Why the split?** A menu author changing a dish description should not need to touch
pairing annotations, and vice versa. `menu.json` has no concept of wine, food_tags, or
scoring — it is cuisine-agnostic. `dish-profiles.json` has no presentation data.

**What reads each file:**
- `generate-menu.py` reads only `menu.json` → writes HTML pages
- `generate-pairings.py` reads both, merges by `id` → writes `pairings.json`

---

### menu.json — presentation layer

```json
{
  "_meta": {
    "menu_id":          "nanban-kaiseki",
    "menu_name":        "Menu Kaiseki Nanban",
    "menu_title":       "Menu Kaiseki",
    "menu_subtitle":    "会席コース",
    "language":         "pt",
    "page_break_after": 6,
    "pages": ["booklet-page-menu1.html", "booklet-page-menu2.html"]
  },
  "dishes": [ ... ]
}
```

**`_meta` fields:**

| Field | Description |
|---|---|
| `menu_id` | Folder name under `data/menus/` |
| `menu_name` | Full name (used in `<title>`) |
| `menu_title` | Short heading shown on the page (falls back to `menu_name`) |
| `menu_subtitle` | Optional subtitle (e.g. Japanese script) |
| `language` | HTML `lang` attribute |
| `page_break_after` | Number of dishes per HTML page |
| `pages` | Output filenames — one per page group, relative to project root |

**Dish fields:**

| Field | Required | Description |
|---|---|---|
| `id` | ✓ | Unique identifier — must match `dish-profiles.json` |
| `sequence` | ✓ | Integer course order (1-based) |
| `name` | ✓ | Display name (Portuguese) |
| `name_alt` | — | Alternative script (e.g. Japanese kanji) — shown in brackets below name |
| `name_pairing` | — | Shorter name used in the pairing modal title; defaults to `name` if absent |
| `course_label` | — | Course category label (e.g. "先付 Sakizuke") |
| `description` | — | One-line dish description |
| `image` | — | Relative path to dish photo (e.g. `images/Goma Doufu.png`) |
| `properties` | — | Culinary property map (see below) |

**`properties` vocabulary:**

| Property | Values |
|---|---|
| `preparation` | `raw` \| `chilled` \| `steamed` \| `fried` \| `grilled` \| `braised` \| `gratinée` \| `cured` \| `smoked` \| `poached` |
| `sauce` | `null` \| `miso` \| `dashi` \| `soy` \| `citrus` \| `cream` \| `vinegar` \| `sweet_sour` \| `wine_reduction` |
| `texture` | `silky` \| `crispy` \| `creamy` \| `chunky` \| `tender` \| `firm` |
| `intensity` | `delicate` \| `light` \| `medium` \| `rich` \| `very_rich` \| `intense` |
| `fat_level` | `low` \| `medium` \| `high` |
| `acidity` | `none` \| `low` \| `medium` \| `high` (vinegar, citrus present in the dish) |
| `sweetness` | `none` \| `low` \| `medium` \| `high` (sugar, mirin, etc.) |
| `key_flavors` | list: `umami` \| `marine` \| `citrus` \| `sweet` \| `acidic` \| `bitter` \| `smoky` \| `earthy` \| `herbaceous` \| `spiced` \| `fermented` |
| `dominant_component` | Free string — the single element that most drives the pairing |

`properties` is informational at this stage. The pairing engine does not read it directly —
it uses `food_tags` from `dish-profiles.json`. The two representations are intentionally
separate: `properties` is a structured description of the dish; `food_tags` are the
operational engine inputs (manually curated for precision, not auto-derived from properties).

---

### dish-profiles.json — pairing layer

```json
{
  "_meta": { "menu_id": "nanban-kaiseki", "menu_source": "menu.json" },
  "meal_arcs": { "aperitivo": [1, 2], "savory_light": [3, 9], ... },
  "pairing_config": { ... },
  "dishes": [ ... ]
}
```

**`meal_arcs`:** Groups courses (by `sequence` number) into named arcs used by
`meal_suggestion` and `pack_pairings` modes. Arc names are free strings; they must
match the arc references inside `pairing_config`.

Nanban-kaiseki arcs:

| Arc | Courses |
|---|---|
| `aperitivo` | 1, 2 |
| `savory_light` | 3, 9 |
| `savory_medium` | 4, 6 |
| `savory_rich` | 5, 7, 8 |
| `dessert` | 10 |

**Dish annotation fields:**

| Field | Description |
|---|---|
| `id` | Must match `menu.json` dish `id` |
| `meal_arc` | Which arc this dish belongs to |
| `primary_tag` | The single `food_tags` value most driving the pairing; earns `PRIMARY_BONUS` (+3 pts) when a matching rule fires on it |
| `food_tags` | List of tags matched against `pairing-rules.json` rule conditions |
| `hard_filters` | Absolute exclusions before scoring (see Hard Filter System section) |
| `notes` | Rationale and benchmark wines — authoring reference only, not read by engine |

---

### pairing_config — pack and meal-suggestion configuration

`pairing_config` in `dish-profiles.json` replaced the hardcoded `PACK_CONFIGS` constant
that was previously in `generate-pairings.py`. Moving it to JSON means each menu defines
its own pairing structure without any code changes.

**`meal_suggestion` sub-object:**

Defines which arcs feed each of the three roles shown in the meal suggestion mode:

```json
"meal_suggestion": {
  "role_light":   ["aperitivo", "savory_light", "savory_medium"],
  "role_red":     ["savory_rich"],
  "role_dessert": ["dessert"]
}
```

The engine picks the highest-scoring wine across all dishes in each role's arc list.

**`pack_pairings` array:**

Each entry is one pack. Slot fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Pack identifier used as JSON key in output (`pack_a`, `pack_b`) |
| `label` | string | Display name shown in the UI |
| `tagline` | string | One-line description shown in the UI |
| `slots` | array | One slot per wine in the pack |

Slot fields:

| Field | Type | Description |
|---|---|---|
| `arc` | string | Internal slot identifier |
| `arc_label` | string | Display label (e.g. "Espumante", "Branco Encorpado") |
| `type_filter` | list or null | Wine types eligible for this slot; `null` = any type |
| `dish_arcs` | list | Arcs whose dishes are scored for this slot |
| `prefer_body` | string | Target body for tiebreaking within the scored pool |
| `prefer_fortified` | bool | Dessert slot: `true` to prefer fortified, `false` to prefer still |

---

### Merge mechanics (generate-pairings.py)

`load_data()` merges the two files by dish `id`:
1. Starts with the `menu.json` dish object (presentation fields + `properties`)
2. Overlays all fields from the matching `dish-profiles.json` dish (`food_tags`, `hard_filters`, `meal_arc`, `notes`)
3. The merged object is used throughout scoring — the engine can access both `properties` and `food_tags`

If a dish `id` exists in `menu.json` but not in `dish-profiles.json`, it is skipped (no
food_tags → cannot be scored). If a dish exists in `dish-profiles.json` but not `menu.json`,
the merge silently uses only the profile fields (no `properties`).

**Optional wine-list filter:**
If `data/menus/<menu>/wine-list.json` exists and is a non-empty array of wine `id` strings,
the engine restricts scoring to that subset of wines. Useful for menus that pair with a
curated wine selection rather than the full database. If the file is absent or empty, the
full `wines-compiled.json` is used.

---

### generate-menu.py

Reads `menu.json` and writes static HTML pages for the booklet. Output files are the
ones listed in `_meta.pages`, written to the project root.

**What it produces:** One HTML file per page group, with all CSS inlined. Each dish gets:
- Course label (`course_label`) in Japanese/romanised script
- Dish name with a 📷 click handler (`openDishImage`) and a 🍷 pairing icon (`openPairing`)
- Description with `name_alt` below in brackets

The last page in `_meta.pages` gets a price footer; earlier pages get `...`.

**`name_pairing` field:** The optional `name_pairing` in `menu.json` lets you specify a
shorter dish name for the pairing modal title — useful when the full `name` is too long
(e.g. "Parfait de Tofu e Castella" instead of "Parfait de Tofu e Castella com Biscoito
de Okara"). Defaults to `name` if absent.

**When to run:**
```bash
python scripts/generate-menu.py --menu nanban-kaiseki
```
Rerun whenever `menu.json` changes. The generated HTML files are committed to git and
served directly by Vercel — there is no server-side rendering.

**Future transition to runtime rendering:**
The generated HTML structure is designed to be identical to what a JS renderer would
produce. When ready: replace the static dish content with a script that fetches `menu.json`
and renders dishes at page load. CSS does not change — only the data injection method
shifts from build-time to runtime.

---

### Dish IDs (nanban-kaiseki)

```
Course 1  goma-doufu              Goma Doufu
Course 2  aperitivos-variados     Aperitivos Variados
Course 3  ceviche-tofu            Ceviche de Tofu Firme
Course 4  agedashi-doufu          Doufu Agedashi
Course 5  cataplana-tofu          Cataplana de Tofu e Ameijoas
Course 6  tofu-nanban             Nanban-zuke de Tofu
Course 7  gratin-tofu             Gratin de Tofu e Cogumelos
Course 8  arroz-misto             Arroz Misto
Course 9  sopa-yuba               Sopa Clara com Yuba
Course 10 parfait-tofu            Parfait de Tofu e Castella
```

---

## ENGINE NATURE — STRUCTURAL, NOT CURATORIAL

The engine scores wines on **structural compatibility** — acidity, body, tannins,
sweetness, finish. It has no opinion on quality, reputation, terroir narrative,
or whether a wine is "good" for a dish in a cultural sense.

**What it knows:**
A wine with acidity 10, off-dry, body light matches the rules for a shoyu-condiment
context and scores 35. A wine with acidity 9, dry scores 26. The numbers determine
the outcome.

**What it does not know:**
- That Rola Pipa from the Açores grows on volcanic soil surrounded by ocean and has
  a saline, iodic character that makes it exceptional with anything from the sea
- That a skin-contact Loureiro creates a texture that resonates with sesame coating
  in a way no number captures
- That certain wines are iconic for pairing with raw fish — decades of human
  experience pointing at them

A sommelier builds a recommendation from both: the structural logic *and* the
accumulated cultural knowledge around a wine and its region. The engine only
has the first half.

**Why this matters in practice:**
The engine will surface a €5 Beira Interior Síria at the same score as a celebrated
Alvarinho if the numbers are equal — which is sometimes a feature (it finds wines
no one would have thought to suggest) and sometimes a gap (it misses wines whose
case rests on terroir character rather than measurable structure).

Engine output is a starting point, not a final list. The wines it systematically
misses are those whose argument is qualitative: saline minerality, oxidative
resonance, fermentation texture, regional narrative. These are precisely the wines
a knowledgeable human would add back after reviewing the structural output.

### Evolving toward a curatorial direction

Three layers, in order of impact and difficulty:

**Layer 1 — Extend the wine schema with sensory/terroir tags**

The most foundational step. Currently wines are described only by numbers (acidity,
body, tannins) and type. To encode qualitative character, each wine needs a controlled
vocabulary of sensory tags — not free-text, but a fixed set the engine can match against.

Candidate tags: `saline`, `mineral`, `volcanic`, `oxidative`, `skin_contact`, `floral`,
`smoky_reduction`, `lactic`, `reductive`, `tannic_textured`

This is a DB editing task: annotate wines in producer files where the qualitative
argument is strong enough to matter in pairing. Not all wines need tags.

**Layer 2 — Add a sensory dimension to the rule engine**

Once wines have sensory tags, new bonus rules can fire on them. New dish-side tags
would be needed to match:

| Dish tag | Wines that benefit |
|---|---|
| `marine_mineral` | `saline`, `volcanic` wines |
| `fermented_resonance` | `oxidative`, `skin_contact` wines |
| `sesame_toasted` | `skin_contact`, `floral` wines |
| `miso_oxidative` | `oxidative`, `dry_madeira` wines |

These are bonus rules (accumulating, not dimensional) — they lift qualified wines without
overriding structural logic. The Rola Pipa case: it already scores well on acidity;
`saline` + `marine_mineral` gives it a further +2–3 that separates it from a mainland
wine with the same number.

**Layer 3 — Operationalise `pairing.affinities`**

The wine profiles already have `pairing.affinities` fields (free-text, not read by the
engine). These could be converted to controlled vocabulary and connected to dish tags —
a middle ground between full annotation and free text.

**What NOT to do**

Avoid a manual override list (e.g. "always show Rola Pipa for seafood"). It solves the
immediate problem but creates a maintenance burden and undermines the system's main
virtue. The right answer is always to encode *why* a wine belongs there, not just that
it does.

**Practical sequencing**

1. Define the sensory tag vocabulary (10–15 tags max, controlled)
2. Annotate the wines most likely to matter: Açores, Madeira, skin-contact whites, notable oxidative styles
3. Add matching dish tags to the 2–3 dishes where the gap is most visible (Goma Doufu, Sopa Yuba, Cataplana)
4. Write the bonus rules
5. Regenerate and compare output against current results

---

## PAIRING PRINCIPLES

**The dominant factor is not always the main ingredient.** Cooking method and
accompaniments (sauces, broths, marinades) carry equal or greater weight.

| Principle | Application |
|---|---|
| Fat needs Acid | Fried dishes, creamy sauces → high-acid wines |
| Umami needs Acid or Off-dry | Dashi → high-acid light whites; Miso → off-dry or aromatic |
| Delicate = Delicate | Light dishes, raw preparations → light-bodied, fresh wines |
| Sweet needs Sweet | Dessert wine must be at least as sweet as the dish |
| Citrus mirrors Citrus | Yuzu dishes → wines with grapefruit or lime notes |
| Regional affinity | Portuguese dish (cataplana) → bonus for Portuguese wine |

---

## FUTURE EXPLORATIONS

### Algorithm

**Per-slot price ranges**
Currently a single min/max applies to all slots. A dessert slot might warrant a higher
ceiling (Madeira 10 years old = €45+ carta) while a branco slot is fine at €25 max.
Would require adding `min_price` / `max_price` fields to each slot in `PACK_CONFIGS`.

**Diversity constraints**
Prevent the same region or producer from appearing twice in the same pack. Currently
possible (though rare). Would require a `used_regions` or `used_producers` set in
`build_pack()`, similar to the existing `used` wine IDs set.

**Minimum score threshold per slot**
Currently `avg_score > 0` is the only threshold. A minimum average score (e.g. `>= 8`)
per slot would ensure every pack wine has a meaningful structural match, not just
"passes hard filters and scores slightly above zero."

**Slot-level `random_top` overrides**
Some slots have a dominant top candidate (e.g. aperitivos course 2 always selects
the same wine because it scores far above the rest). A per-slot `random_top` field in
`PACK_CONFIGS` would allow tighter pools for well-defined slots and wider pools where
the top candidates are clustered.

**Sequence price filtering**
Currently `--pack-min-price` / `--pack-max-price` do not apply to `sequence_pairing`.
A separate `--sequence-max-price` parameter would allow the sequence to stay
within a total budget constraint.

### Rules

**Texture dimension** *(rule work only — no DB changes needed)*
Lees-aged whites, talha wines, and oxidative styles behave differently from their
structural profile alone. Existing fields (`body`, `tannins`, `finish`) already
approximate texture sufficiently as proxies. Work belongs entirely in the rule layer:
add dish texture tags (`silky`, `crunchy`, `oxidative_match`) to dish profiles and
write rules that use existing structure fields as proxies.

**Rule generalisation for broader cuisine**
Current rules were developed against Japanese kaiseki with Portuguese wines. For general
European/Portuguese cuisine, additional rules are needed for: lamb/game, aged cheese,
cured meat, mushroom/earthy, legumes, pasta weight categories. Add when a second menu
is being profiled — untestable rules should not be written in advance.

### Multi-menu

**Adding a new menu:**
1. Create `data/menus/<name>/menu.json` — presentation layer (dishes, course labels, descriptions)
2. Create `data/menus/<name>/dish-profiles.json` — pairing annotations (`food_tags`, `hard_filters`, `pairing_config`)
3. Run `python scripts/generate-menu.py --menu <name>` → generates booklet HTML pages
4. Run `python scripts/generate-pairings.py --menu <name>` → generates pairings.json
5. Set `const ACTIVE_MENU = '<name>'` in `js/pairing-engine.js`

The DB, rules, and engine are all menu-agnostic. Only the two JSON files need authoring.

---

## FILE INVENTORY

```
data/wine-profiles/
  producers-[region].json     source of truth (14 files, 443 wines)
  pairing-rules.json          47 rules, 10 dimensions
  wines-compiled.json         GENERATED — flat array with carta_price

data/menus/nanban-kaiseki/
  menu.json                   presentation layer — dishes, course labels, descriptions
  dish-profiles.json          pairing layer — food_tags, hard_filters, pairing_config
  pairings.json               GENERATED — 4 modes (sequence_pairing, per_dish, etc.)

scripts/
  compile-wines.py            builds wines-compiled.json
  generate-menu.py            builds booklet HTML pages from menu.json
  generate-pairings.py        builds pairings.json (merges menu.json + dish-profiles.json)

js/
  pairing-engine.js           loads pairings.json, renders modal and pairing pages

css/
  pairing-modal.css           modal styling
```

---

## SEE ALSO

- `doc/partial_pairing_example.md` — manual dry run of the engine against all 10 dishes
- `doc/pairing-system-assessment-1.md` — structural audit; findings informed scoring improvements
- `data/wine-profiles/pairing-rules.json` — full rule set with dimension assignments

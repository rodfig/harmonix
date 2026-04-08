# 🇵🇹 Portuguese Wine Database – Operational Checklist

## 1. File Structure

### Source of Truth
producers-<region>.json

This is the only file that should be manually edited.

### Validation Reports (auto-generated)
producers-<region>.validation.json  
producers-<region>.schema_validation.json

These files are overwritten on every run.  
Never edit them manually.

---

## 2. Required Wine Schema (All Wines)

Every wine must contain all keys below.  
Values may be `null` only where explicitly allowed.

### Core Identity
- id — string, required, unique
- name — string, required
- vintage — integer or null (NV wines allowed)
- doc — string, required
- type — string (white, red, rosé, etc.)
- varieties — non-empty list of strings

### Chemistry
- alcohol — number
- acidity_gl — number or null
- ph — number or null

Note: aging_years is NOT stored. Cellaring longevity is derived algorithmically at
query time from structural fields. See doc/proxy-aging-years.md for the formula.

### Winemaking
- winemaking — string or null

### Structure (required object)

structure:
  acidity: integer (1–10) or null
  tannins: integer (1–10) or null
  body: light | medium-light | medium | medium-full | full | null
  sweetness: dry | off-dry | medium | semi-sweet | sweet
  finish: short | medium | medium-long | long | very long | null

### Aromas (required object)

aromas:
  primary: []
  secondary: []
  tertiary: []

Lists may be empty but must exist.

### Pairing (required object)

pairing:
  affinities: []
  notes: string or null

---

## 3. Optional but Allowed Fields

- quinta — string or null
- notes — string or null

No additional top-level fields should be introduced without updating the schema.

---

## 4. Chemistry Logic Rules

### When Total Acidity + pH exist
You may compute:
- structure.acidity

### When pH is not published
- set "ph": null
- set "aging_years": null (unless producer gives longevity)
- assign structure from sensory interpretation

Never fabricate pH values.

---

## 5. Aging

aging_years is not stored in the database. Cellaring longevity is computed
algorithmically from structural fields at query time.

See doc/proxy-aging-years.md for the full derivation formula.

If a producer publishes explicit longevity data, preserve it inside the
wine's `notes` field as a text reference. Do not convert it to a number
or store it as aging_years.

---

## 6. Validation Workflow

Run for every region:

python validate.py producers-<region>.json  
python validate_schema.py producers-<region>.json

Then:
1. Fix real schema errors
2. Ignore stylistic outliers
3. Re-run validation
4. Stop when dataset is structurally stable

---

## 7. Sanity Rules (Quick Interpretation)

| Validator Message | Typical Meaning |
|------------------|-----------------|
| extra key | schema mismatch, not bad data |
| low_acidity_index | warm climate or aged wine |
| high_acidity_index | rosé, altitude, or Vinho Verde |
| extra key `aging_years` | field removed — use notes for producer longevity text |

---

## 8. Do NOT

- Invent analytical data
- Convert months into years
- Remove representative producers due to missing chemistry
- Modify schema per region
- Store temporary calculation fields

---

## 9. Region Completion Criteria

A region is considered stable when:
- No duplicate IDs
- No missing required fields
- Chemistry not fabricated
- Outliers documented when relevant

---

## 10. Guiding Principle

Accuracy over completeness  
Consistency over perfection  
Representativeness over analytical uniformity
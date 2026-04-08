# Proxy Aging Years (Derived — Not Stored)

## Purpose

The database intentionally **does not store numeric longevity (`aging_years`)** because:

- Most producers do not publish reliable drinking windows.
- Longevity is highly contextual (storage, closure, vintage evolution).
- Numeric aging claims are often interpretative rather than factual.
- Storing inferred values conflicts with the project principle:
  
  > **No fabricated or inferred analytical data.**

However, users still benefit from comparing wines by **expected evolution capacity** (cellaring potential, structural longevity, menu sequencing, etc.).

To support this without introducing unverifiable data, the system computes a **derived proxy aging value** using existing structural information already present in the schema.

This proxy is:

- ✅ deterministic  
- ✅ reproducible  
- ✅ region-agnostic  
- ✅ not stored in source files  
- ✅ recalculated dynamically when needed

---

## Conceptual Basis

Bottle evolution potential in dry wines is primarily governed by structural balance:

| Factor | Role in Aging |
|---|---|
| **Acidity** | Slows oxidation and preserves freshness |
| **Tannins / phenolics** | Provide antioxidant buffering and polymerization capacity |
| **Body / extract** | Indicates concentration and material available for evolution |
| **Finish length** | Correlates with structural persistence and balance |

Optional analytical chemistry can slightly refine the estimate:

- lower pH → greater stability
- higher total acidity → greater longevity potential

---

## Design Principles

- Proxy values are **derived only**, never stored.
- Missing chemistry is acceptable and does not penalize wines strongly.
- No regional assumptions (e.g., “Douro ages longer”) are used.
- Output avoids false precision.

---

## Inputs

### Required (always present)

- `structure.acidity` (integer scale 1–10)
- `structure.body`
- `structure.finish`
- `type` (`red | white | rose`)

### Optional

- `structure.tannins` (may be null)
- `ph`
- `acidity_gl`

---

## Step 1 — Normalize Structure Values (0–1)

### Acidity

A = clamp((acidity - 1) / 9, 0, 1)

### Tannins

T = clamp((tannins - 1) / 9, 0, 1)


If tannins are null:
	T = 0
	
### Body Mapping

| Body | Value |
|---|---|
| light | 0.00 |
| medium-light | 0.25 |
| medium | 0.50 |
| medium-full | 0.75 |
| full | 1.00 |

→ result = `B`

### Finish Mapping

| Finish | Value |
|---|---|
| short | 0.00 |
| medium | 0.25 |
| medium-long | 0.50 |
| long | 0.75 |
| very long | 1.00 |

→ result = `F`

---

## Step 2 — Optional Chemistry Adjustment

Chemistry never dominates the result; it only fine-tunes it.

### pH Influence

ph_low = 2.95
ph_high = 3.85

P = clamp((ph_high - ph) / (ph_high - ph_low), 0, 1)


(lower pH increases aging potential)

### Total Acidity Influence

ta_low = 4.0
ta_high = 7.5

TA = clamp((acidity_gl - ta_low) / (ta_high - ta_low), 0, 1)


### Combined Chemistry Adjustment

If neither exists:
	C = 0
Otherwise:
	chem = mean(available(P, TA))
	C = 0.10 * (chem - 0.5)
	

Resulting adjustment range ≈ ±0.05.

---

## Step 3 — Ageworthiness Score (0–1)

### Reds

S_base =
0.30A +
0.35T +
0.20B +
0.15F

### Whites & Rosés

S_base =
0.45A +
0.10T +
0.20B +
0.25F


### Final Score

S = clamp(S_base + C, 0, 1)


---

## Step 4 — Convert Score to Proxy Aging Years

### Conservative Caps

| Type | Min | Max |
|---|---|---|
| Red | 2 | 18 |
| White | 1 | 12 |
| Rosé | 0 | 6 |

### Conversion

Y_proxy = round(Y_min + S * (Y_max - Y_min))


---

## Step 5 — Recommended Presentation (Range)

To avoid false precision:

Y_low = max(Y_min, Y_proxy - 2)
Y_high = min(Y_max, Y_proxy + 2)


Display:

proxy_aging_years: "Y_low–Y_high"


---

## Interpretation Guidelines

- This is **not a drinking window**.
- This is **not producer data**.
- This is a **relative structural ranking**.
- Wines with similar structure will cluster naturally regardless of region.

---

## Example Interpretation

| Structural Profile | Expected Proxy Result |
|---|---|
| High tannin + full body + long finish | Long aging class |
| Medium body + moderate tannin | Medium evolution |
| Light body + low tannin | Early drinking |

---

## Implementation Rule

> Proxy aging values must **never** be written back into  
> `producers-<region>.json`.

They exist only at application/query level.

---

## Why This Approach Fits the Project

- Preserves analytical honesty.
- Removes speculative numeric storage.
- Keeps schema uniform across regions.
- Uses information already encoded in structure fields.
- Allows future recalibration without data migration.

---	
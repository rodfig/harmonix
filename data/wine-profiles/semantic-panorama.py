#!/usr/bin/env python3
"""
Portuguese Wine DB — Semantic Panorama Analysis (Panorama Report 1)

Reads all producers-*.json in current directory (canonical sources) and produces:
  - panorama-summary.json
  - panorama-structure-map.json
  - panorama-clusters.json
  - panorama-anchors.json
  - panorama-outliers.json

Clustering is done on behavioural core:
  type + structure (acidity, tannins, body, sweetness, finish)

No web. Read-only. No file modifications.
"""

import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from statistics import mean, median

# -----------------------------
# Config
# -----------------------------

DATA_DIR = Path(".")
FILES = sorted(DATA_DIR.glob("producers-*.json"))

# Number of clusters for behaviour families.
# 8–14 tends to be readable for 400 wines; script auto-picks within this range
# based on unique signature count, but you can force a number here.
FORCE_K = None  # e.g., 12

# How many anchor wines per cluster
ANCHORS_PER_CLUSTER = 2

# Feature weights (behaviour core)
W_ACIDITY = 1.2
W_TANNINS = 1.1
W_BODY = 1.0
W_SWEETNESS = 1.0
W_FINISH = 1.0
W_TYPE = 0.8

# -----------------------------
# Helpers
# -----------------------------

def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_str(x): return isinstance(x, str)
def is_num(x): return isinstance(x, (int, float)) and not isinstance(x, bool)

def norm_type(t):
    if not is_str(t):
        return None
    t = t.strip().lower()
    # normalize rose spelling variants
    if t in {"rosé", "rose"}:
        return "rosé"
    return t

def bucket_1_10(x):
    """Bucket numeric 1..10 into 1-2,3-4,5-6,7-8,9-10 for structure maps."""
    if not is_num(x):
        return None
    if x <= 2: return "1-2"
    if x <= 4: return "3-4"
    if x <= 6: return "5-6"
    if x <= 8: return "7-8"
    return "9-10"

def safe_get(d, path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def count_aromas(aromas):
    """Total aroma descriptors across tiers, supporting dict tiers or flat list."""
    if aromas is None:
        return 0
    if isinstance(aromas, list):
        return sum(1 for a in aromas if is_str(a) and a.strip())
    if isinstance(aromas, dict):
        total = 0
        for tier in ("primary", "secondary", "tertiary"):
            vals = aromas.get(tier, [])
            if isinstance(vals, list):
                total += sum(1 for a in vals if is_str(a) and a.strip())
        return total
    return 0

def flatten_wines():
    """
    Returns a flat list of wine records with region/producers attached.
    """
    rows = []
    for fp in FILES:
        data = load_json(fp)
        meta = data.get("_meta", {}) if isinstance(data, dict) else {}
        region = meta.get("region", fp.stem.replace("producers-", ""))

        producers = data.get("producers", [])
        if not isinstance(producers, list):
            continue

        for p in producers:
            if not isinstance(p, dict):
                continue
            producer_name = p.get("name")
            quinta = p.get("quinta") or p.get("name")

            wines = p.get("wines", [])
            if not isinstance(wines, list):
                continue

            for w in wines:
                if not isinstance(w, dict):
                    continue
                rows.append({
                    "region": region,
                    "producer": producer_name,
                    "quinta": w.get("quinta") or quinta,
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "vintage": w.get("vintage"),
                    "doc": w.get("doc"),
                    "type": norm_type(w.get("type")),
                    "varieties": w.get("varieties") if isinstance(w.get("varieties"), list) else [],
                    "alcohol": w.get("alcohol"),
                    "acidity_gl": w.get("acidity_gl"),
                    "ph": w.get("ph"),
                    "structure": w.get("structure") if isinstance(w.get("structure"), dict) else {},
                    "aromas": w.get("aromas"),
                    "pairing": w.get("pairing"),
                    "notes": w.get("notes"),
                })
    return rows

# -----------------------------
# Vectorization for clustering
# -----------------------------

BODY_LEVELS = ["light", "medium", "full"]
SWEET_LEVELS = ["dry", "off-dry", "medium", "sweet"]
FINISH_LEVELS = ["short", "medium", "long", "very long"]

def one_hot(value, levels):
    return [1.0 if value == lvl else 0.0 for lvl in levels]

def feature_vector(row, type_levels):
    """
    Behavioural core vector:
      type (one-hot) + acidity + tannins + body one-hot + sweetness one-hot + finish one-hot
    """
    st = row["structure"] if isinstance(row["structure"], dict) else {}
    acidity = st.get("acidity")
    tannins = st.get("tannins")

    # numeric structure fields: treat missing as None; we'll impute with medians later
    v = []

    # type
    t = row["type"]
    v += [W_TYPE * (1.0 if t == tl else 0.0) for tl in type_levels]

    # numeric
    v.append(W_ACIDITY * (float(acidity) if is_num(acidity) else math.nan))
    v.append(W_TANNINS * (float(tannins) if is_num(tannins) else math.nan))

    # categorical
    v += [W_BODY * x for x in one_hot(st.get("body"), BODY_LEVELS)]
    v += [W_SWEETNESS * x for x in one_hot(st.get("sweetness"), SWEET_LEVELS)]
    v += [W_FINISH * x for x in one_hot(st.get("finish"), FINISH_LEVELS)]

    return v

def impute_nans(matrix):
    """Impute NaNs column-wise with median of non-NaNs."""
    cols = len(matrix[0]) if matrix else 0
    med = [0.0] * cols
    for j in range(cols):
        vals = [row[j] for row in matrix if not math.isnan(row[j])]
        med[j] = median(vals) if vals else 0.0
    out = []
    for row in matrix:
        out.append([med[j] if math.isnan(row[j]) else row[j] for j in range(cols)])
    return out

def euclid(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))

def kmeans(points, k, iters=50, seed=42):
    """
    Lightweight k-means (deterministic init).
    Returns (labels, centroids).
    """
    if not points:
        return [], []
    n = len(points)
    k = max(2, min(k, n))

    # deterministic init: pick evenly spaced points
    idxs = [int(i * (n-1) / (k-1)) for i in range(k)]
    centroids = [points[i][:] for i in idxs]

    labels = [0] * n
    for _ in range(iters):
        changed = False
        # assign
        for i, p in enumerate(points):
            best = 0
            best_d = euclid(p, centroids[0])
            for c in range(1, k):
                d = euclid(p, centroids[c])
                if d < best_d:
                    best = c
                    best_d = d
            if labels[i] != best:
                labels[i] = best
                changed = True

        # recompute
        newc = [[0.0]*len(points[0]) for _ in range(k)]
        counts = [0]*k
        for lab, p in zip(labels, points):
            counts[lab] += 1
            for j, val in enumerate(p):
                newc[lab][j] += val
        for c in range(k):
            if counts[c] == 0:
                # re-seed empty cluster
                newc[c] = points[(c * 997) % n][:]
            else:
                newc[c] = [v / counts[c] for v in newc[c]]

        centroids = newc
        if not changed:
            break

    return labels, centroids

# -----------------------------
# Main analysis
# -----------------------------

rows = flatten_wines()

# Basic totals
totals = {
    "wines": len(rows),
    "regions": len(set(r["region"] for r in rows)),
}

# Distributions
type_counts = Counter(r["type"] for r in rows)
region_counts = Counter(r["region"] for r in rows)
doc_counts = Counter(r["doc"] for r in rows)

# Varieties distribution
variety_counts = Counter()
for r in rows:
    for v in r["varieties"]:
        variety_counts[v] += 1

# Aroma counts
aroma_counts = [count_aromas(r["aromas"]) for r in rows]

# Pairing counts (supports dict with affinities)
pairing_counts = []
for r in rows:
    p = r["pairing"]
    if isinstance(p, dict):
        aff = p.get("affinities", [])
        pairing_counts.append(len(aff) if isinstance(aff, list) else 0)
    elif isinstance(p, list):
        pairing_counts.append(len(p))
    else:
        pairing_counts.append(0)

# Structure signature coverage
def structure_signature(r):
    st = r["structure"] if isinstance(r["structure"], dict) else {}
    return (
        r["type"],
        st.get("body"),
        st.get("sweetness"),
        st.get("finish"),
        bucket_1_10(st.get("acidity")),
        bucket_1_10(st.get("tannins")) if r["type"] == "red" else None
    )

sig_counts = Counter(structure_signature(r) for r in rows)
unique_sigs = len(sig_counts)

# Redundancy indicators
largest_sig = max(sig_counts.values()) if sig_counts else 0
redundancy = {
    "unique_structure_signatures": unique_sigs,
    "largest_signature_share": round(largest_sig / len(rows), 4) if rows else 0.0,
    "signatures_with_1_wine": sum(1 for c in sig_counts.values() if c == 1),
    "signatures_with_2_wines": sum(1 for c in sig_counts.values() if c == 2),
}

# Structure map (for heatmap-like inspection)
structure_map = Counter()
for r in rows:
    st = r["structure"] if isinstance(r["structure"], dict) else {}
    key = {
        "type": r["type"],
        "body": st.get("body"),
        "sweetness": st.get("sweetness"),
        "finish": st.get("finish"),
        "acidity_bucket": bucket_1_10(st.get("acidity")),
        "tannins_bucket": bucket_1_10(st.get("tannins")) if r["type"] == "red" else None,
    }
    structure_map[tuple(key.items())] += 1

# Clustering on behaviour core
type_levels = sorted(t for t in type_counts.keys() if t is not None)
vectors = [feature_vector(r, type_levels) for r in rows]
vectors = impute_nans(vectors)

# Choose K
if FORCE_K is not None:
    k = FORCE_K
else:
    # heuristic: based on unique signatures, clamp to 8..14
    if unique_sigs <= 10:
        k = 8
    elif unique_sigs <= 25:
        k = 10
    elif unique_sigs <= 50:
        k = 12
    else:
        k = 14

labels, centroids = kmeans(vectors, k)

# Cluster summaries
clusters = defaultdict(list)
for r, lab, vec in zip(rows, labels, vectors):
    clusters[lab].append((r, vec))

def cluster_profile(items):
    # items: list of (row, vec)
    t = Counter()
    body = Counter()
    sweet = Counter()
    finish = Counter()
    acidity = []
    tannins = []
    aroma = []
    for r, _ in items:
        st = r["structure"] if isinstance(r["structure"], dict) else {}
        t[r["type"]] += 1
        body[st.get("body")] += 1
        sweet[st.get("sweetness")] += 1
        finish[st.get("finish")] += 1
        if is_num(st.get("acidity")):
            acidity.append(float(st.get("acidity")))
        if is_num(st.get("tannins")):
            tannins.append(float(st.get("tannins")))
        aroma.append(count_aromas(r["aromas"]))
    return {
        "size": len(items),
        "top_type": t.most_common(3),
        "top_body": body.most_common(3),
        "top_sweetness": sweet.most_common(3),
        "top_finish": finish.most_common(3),
        "acidity_median": median(acidity) if acidity else None,
        "tannins_median": median(tannins) if tannins else None,
        "aromas_median": median(aroma) if aroma else None,
    }

cluster_report = []
for lab in sorted(clusters.keys()):
    prof = cluster_profile(clusters[lab])
    cluster_report.append({"cluster": lab, **prof})

# Anchors: closest to centroid per cluster
anchors = []
for lab in sorted(clusters.keys()):
    items = clusters[lab]
    c = centroids[lab]
    scored = []
    for r, v in items:
        scored.append((euclid(v, c), r))
    scored.sort(key=lambda x: x[0])
    for dist, r in scored[:ANCHORS_PER_CLUSTER]:
        anchors.append({
            "cluster": lab,
            "distance_to_centroid": round(dist, 4),
            "id": r["id"],
            "name": r["name"],
            "producer": r["producer"],
            "region": r["region"],
            "doc": r["doc"],
            "type": r["type"],
            "vintage": r["vintage"],
            "structure": r["structure"],
            "aromas_count": count_aromas(r["aromas"]),
        })

# Outliers: analytic + structural extremes + rare signatures
def minmax(field):
    vals = [(r[field], r) for r in rows if is_num(r.get(field))]
    if not vals:
        return None
    vals.sort(key=lambda x: x[0])
    lo_v, lo_r = vals[0]
    hi_v, hi_r = vals[-1]
    return {
        "field": field,
        "min": {"value": lo_v, "id": lo_r["id"], "name": lo_r["name"], "region": lo_r["region"], "type": lo_r["type"]},
        "max": {"value": hi_v, "id": hi_r["id"], "name": hi_r["name"], "region": hi_r["region"], "type": hi_r["type"]},
    }

# structure extremes
def struct_minmax(key):
    vals = []
    for r in rows:
        st = r["structure"] if isinstance(r["structure"], dict) else {}
        if is_num(st.get(key)):
            vals.append((float(st[key]), r))
    if not vals:
        return None
    vals.sort(key=lambda x: x[0])
    lo_v, lo_r = vals[0]
    hi_v, hi_r = vals[-1]
    return {
        "field": f"structure.{key}",
        "min": {"value": lo_v, "id": lo_r["id"], "name": lo_r["name"], "region": lo_r["region"], "type": lo_r["type"]},
        "max": {"value": hi_v, "id": hi_r["id"], "name": hi_r["name"], "region": hi_r["region"], "type": hi_r["type"]},
    }

rare_sigs = []
for sig, c in sig_counts.items():
    if c == 1:
        # find the wine
        for r in rows:
            if structure_signature(r) == sig:
                rare_sigs.append({
                    "signature": {
                        "type": sig[0],
                        "body": sig[1],
                        "sweetness": sig[2],
                        "finish": sig[3],
                        "acidity_bucket": sig[4],
                        "tannins_bucket": sig[5],
                    },
                    "wine": {"id": r["id"], "name": r["name"], "region": r["region"], "doc": r["doc"]},
                })
                break

outliers = {
    "analytic_extremes": [x for x in [
        minmax("alcohol"),
        minmax("acidity_gl"),
        minmax("ph"),
    ] if x is not None],
    "structure_extremes": [x for x in [
        struct_minmax("acidity"),
        struct_minmax("tannins"),
    ] if x is not None],
    "rare_structure_signatures": rare_sigs[:50],  # cap for readability
}

# Summary report
summary = {
    "totals": totals,
    "distributions": {
        "by_type": type_counts.most_common(),
        "by_region": region_counts.most_common(),
        "top_docs": doc_counts.most_common(25),
        "top_varieties": variety_counts.most_common(40),
    },
    "signal": {
        "aromas": {
            "count": len(aroma_counts),
            "min": min(aroma_counts) if aroma_counts else None,
            "median": median(aroma_counts) if aroma_counts else None,
            "mean": round(mean(aroma_counts), 3) if aroma_counts else None,
            "max": max(aroma_counts) if aroma_counts else None,
        },
        "pairing_affinities": {
            "count": len(pairing_counts),
            "min": min(pairing_counts) if pairing_counts else None,
            "median": median(pairing_counts) if pairing_counts else None,
            "mean": round(mean(pairing_counts), 3) if pairing_counts else None,
            "max": max(pairing_counts) if pairing_counts else None,
        },
    },
    "redundancy": redundancy,
    "clustering": {
        "k": k,
        "type_levels": type_levels,
        "cluster_sizes": sorted([(c["cluster"], c["size"]) for c in cluster_report], key=lambda x: -x[1]),
    },
}

# -----------------------------
# Write outputs
# -----------------------------

def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

dump("panorama-summary.json", summary)

# structure map as list for JSON friendliness
dump("panorama-structure-map.json", [
    {"key": dict(k), "count": v}
    for k, v in structure_map.most_common()
])

dump("panorama-clusters.json", sorted(cluster_report, key=lambda x: -x["size"]))
dump("panorama-anchors.json", anchors)
dump("panorama-outliers.json", outliers)

print("\nPanorama Report 1 generated:")
print("  panorama-summary.json")
print("  panorama-structure-map.json")
print("  panorama-clusters.json")
print("  panorama-anchors.json")
print("  panorama-outliers.json\n")
#!/usr/bin/env python3
"""
Portuguese Wine DB — Audit (schema-aware)

Reads all producers-<region>.json files in the current folder and produces:
  - audit-summary.json   (per-region counts + headline issue counts)
  - audit-flags.json     (actionable issues with file/producer/wine)
  - audit-taxonomy.json  (value distributions + length distributions)

Key fixes vs earlier version:
  - Supports aromas as either:
      * list[str]
      * {"primary":[...], "secondary":[...], "tertiary":[...]}
    and counts TOTAL descriptors correctly.
  - Structure baseline is {"acidity","body","sweetness","finish"}.
    "tannins" is treated as required for reds, optional otherwise.
  - Counts pairing whether it's list[...] or dict (safely).
  - More defensive typing + clearer flags.
"""

import json
from pathlib import Path
from collections import Counter
from statistics import mean, median

DATA_DIR = Path(".")
FILES = sorted(DATA_DIR.glob("producers-*.json"))

# If you want stricter/looser thresholds:
MIN_AROMAS = 5
MIN_PAIRING = 1  # pairing is required by schema; warn if empty

# -----------------------------
# Helpers
# -----------------------------

def is_nonempty_str(x) -> bool:
    return isinstance(x, str) and x.strip() != ""

def safe_len_list_of_str(x) -> int:
    if not isinstance(x, list):
        return 0
    return sum(1 for v in x if is_nonempty_str(v))

def count_aromas(aromas) -> int:
    """
    Supports:
      - aromas: list[str]
      - aromas: {"primary":[...], "secondary":[...], "tertiary":[...]}
    Returns total number of non-empty string descriptors.
    """
    if aromas is None:
        return 0

    if isinstance(aromas, list):
        return safe_len_list_of_str(aromas)

    if isinstance(aromas, dict):
        total = 0
        for tier in ("primary", "secondary", "tertiary"):
            total += safe_len_list_of_str(aromas.get(tier, []))
        return total

    return 0

def aroma_tier_counts(aromas):
    """
    Returns (primary, secondary, tertiary) counts when aromas is dict,
    otherwise tries to treat list as primary-only.
    """
    if aromas is None:
        return (0, 0, 0)
    if isinstance(aromas, list):
        return (safe_len_list_of_str(aromas), 0, 0)
    if isinstance(aromas, dict):
        p = safe_len_list_of_str(aromas.get("primary", []))
        s = safe_len_list_of_str(aromas.get("secondary", []))
        t = safe_len_list_of_str(aromas.get("tertiary", []))
        return (p, s, t)
    return (0, 0, 0)

def count_pairing(pairing) -> int:
    """
    Supports:
      - pairing: list[str] or list[...]
      - pairing: dict (counts keys or values as 1 each if dict-like)
    """
    if pairing is None:
        return 0
    if isinstance(pairing, list):
        # pairing items may be strings or objects depending on your evolution;
        # count non-empty strings, else count items
        str_count = sum(1 for v in pairing if is_nonempty_str(v))
        return str_count if str_count > 0 else len(pairing)
    if isinstance(pairing, dict):
        return len(pairing)
    return 0

def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def flag(flags_list, region, producer, wine, issue):
    flags_list.append({
        "file": region,
        "producer": producer,
        "wine": wine,
        "issue": issue
    })

def normalize_type(t):
    # keep raw type, but also help spot fragmentation
    if not is_nonempty_str(t):
        return None
    return t.strip()

def extract_producer_list(data):
    """
    Expects:
      { "_meta": {...}, "producers": [...] }
    but returns [] if not found.
    """
    if isinstance(data, dict) and isinstance(data.get("producers"), list):
        return data["producers"]
    return []

def structure_missing_keys(structure):
    expected = {"acidity", "body", "sweetness", "finish"}
    if not isinstance(structure, dict):
        return expected
    return expected - set(structure.keys())

def has_tannins(structure):
    return isinstance(structure, dict) and "tannins" in structure

# -----------------------------
# Collectors
# -----------------------------

summary = {}
flags = []

taxonomy = {
    "type": Counter(),
    "doc": Counter(),
    "varieties": Counter(),

    # lengths / distributions
    "aroma_total_lengths": [],
    "aroma_primary_lengths": [],
    "aroma_secondary_lengths": [],
    "aroma_tertiary_lengths": [],
    "pairing_lengths": [],

    # structure typing info (optional)
    "structure_body_values": Counter(),
    "structure_sweetness_values": Counter(),
    "structure_finish_values": Counter(),
    "structure_acidity_types": Counter(),   # "int"/"float"/"str"/"null"/"other"
    "structure_tannins_types": Counter(),
}

global_wine_ids = set()
duplicate_wine_ids = set()

global_producer_ids = set()
duplicate_producer_ids = set()

total_producers = 0
total_wines = 0

# -----------------------------
# Main scan
# -----------------------------

for file_path in FILES:
    data = load_json(file_path)

    meta = data.get("_meta", {}) if isinstance(data, dict) else {}
    required = set(meta.get("fields_required", []))
    optional = set(meta.get("fields_optional", []))
    region = meta.get("region", file_path.stem.replace("producers-", ""))

    producers = extract_producer_list(data)

    region_stats = {
        "producers": 0,
        "wines": 0,

        "missing_required": 0,
        "unknown_fields": 0,

        "thin_aromas": 0,
        "empty_pairing": 0,

        "missing_structure_keys": 0,
        "missing_tannins_on_red": 0,

        "duplicate_wine_ids": 0,
        "duplicate_producer_ids": 0,
    }

    for producer in producers:
        if not isinstance(producer, dict):
            flag(flags, region, "UNKNOWN_PRODUCER", None, "producer entry is not an object")
            continue

        producer_name = producer.get("name", "UNKNOWN_PRODUCER")
        producer_id = producer.get("id")

        # Producer id checks (if you use them)
        if producer_id is not None:
            if producer_id in global_producer_ids:
                duplicate_producer_ids.add(producer_id)
                region_stats["duplicate_producer_ids"] += 1
                flag(flags, region, producer_name, None, "duplicate producer id")
            else:
                global_producer_ids.add(producer_id)

        wines = producer.get("wines", [])
        if not isinstance(wines, list):
            flag(flags, region, producer_name, None, "producer.wines is not a list")
            continue

        total_producers += 1
        region_stats["producers"] += 1

        for wine in wines:
            if not isinstance(wine, dict):
                flag(flags, region, producer_name, None, "wine entry is not an object")
                continue

            total_wines += 1
            region_stats["wines"] += 1

            wine_name = wine.get("name", "UNKNOWN_WINE")
            wine_id = wine.get("id")

            # Duplicate wine id
            if wine_id is not None:
                if wine_id in global_wine_ids:
                    duplicate_wine_ids.add(wine_id)
                    region_stats["duplicate_wine_ids"] += 1
                    flag(flags, region, producer_name, wine_name, "duplicate wine id")
                else:
                    global_wine_ids.add(wine_id)
            else:
                # id is required per meta; this should be caught below, but keep explicit note
                flag(flags, region, producer_name, wine_name, "missing wine id (null/absent)")

            # Required fields
            if required:
                missing = required - set(wine.keys())
                if missing:
                    region_stats["missing_required"] += 1
                    flag(flags, region, producer_name, wine_name,
                         f"missing required fields: {sorted(missing)}")

            # Unknown fields (schema drift)
            if required or optional:
                allowed = required | optional
                unknown = set(wine.keys()) - allowed
                if unknown:
                    region_stats["unknown_fields"] += 1
                    flag(flags, region, producer_name, wine_name,
                         f"unknown fields: {sorted(unknown)}")

            # Taxonomy: type/doc/varieties
            t = normalize_type(wine.get("type"))
            taxonomy["type"][t] += 1

            d = wine.get("doc")
            taxonomy["doc"][d] += 1

            varieties = wine.get("varieties", [])
            if isinstance(varieties, list):
                for grape in varieties:
                    taxonomy["varieties"][grape] += 1
            else:
                flag(flags, region, producer_name, wine_name, "varieties is not a list")

            # Aromas
            aromas = wine.get("aromas")
            total_ar = count_aromas(aromas)
            p_cnt, s_cnt, t_cnt = aroma_tier_counts(aromas)

            taxonomy["aroma_total_lengths"].append(total_ar)
            taxonomy["aroma_primary_lengths"].append(p_cnt)
            taxonomy["aroma_secondary_lengths"].append(s_cnt)
            taxonomy["aroma_tertiary_lengths"].append(t_cnt)

            if total_ar < MIN_AROMAS:
                region_stats["thin_aromas"] += 1
                flag(flags, region, producer_name, wine_name,
                     f"aromas too short (<{MIN_AROMAS}): {total_ar}")

            # Pairing
            pairing = wine.get("pairing")
            pairing_len = count_pairing(pairing)
            taxonomy["pairing_lengths"].append(pairing_len)

            if pairing_len < MIN_PAIRING:
                region_stats["empty_pairing"] += 1
                flag(flags, region, producer_name, wine_name, "empty pairing")

            # Structure
            structure = wine.get("structure")
            missing_struct = structure_missing_keys(structure)
            if missing_struct:
                region_stats["missing_structure_keys"] += 1
                flag(flags, region, producer_name, wine_name,
                     f"structure missing keys: {sorted(missing_struct)}")

            # tannins expectation: required on red (project-typical), optional otherwise
            if t == "red" and not has_tannins(structure):
                region_stats["missing_tannins_on_red"] += 1
                flag(flags, region, producer_name, wine_name, "red wine missing structure.tannins")

            # Capture structure value distributions (for later semantic audit)
            if isinstance(structure, dict):
                body = structure.get("body")
                sweetness = structure.get("sweetness")
                finish = structure.get("finish")
                acidity = structure.get("acidity")
                tannins = structure.get("tannins")

                if is_nonempty_str(body):
                    taxonomy["structure_body_values"][body] += 1
                if is_nonempty_str(sweetness):
                    taxonomy["structure_sweetness_values"][sweetness] += 1
                if is_nonempty_str(finish):
                    taxonomy["structure_finish_values"][finish] += 1

                def type_bucket(x):
                    if x is None:
                        return "null"
                    if isinstance(x, bool):
                        return "bool"
                    if isinstance(x, int):
                        return "int"
                    if isinstance(x, float):
                        return "float"
                    if isinstance(x, str):
                        return "str"
                    return "other"

                taxonomy["structure_acidity_types"][type_bucket(acidity)] += 1
                taxonomy["structure_tannins_types"][type_bucket(tannins)] += 1

    summary[region] = region_stats

# -----------------------------
# Totals + derived stats
# -----------------------------

def dist_stats(values):
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": round(mean(values), 3),
        "median": median(values),
    }

summary["_totals"] = {
    "producers": total_producers,
    "wines": total_wines,
    "duplicate_wine_ids": len(duplicate_wine_ids),
    "duplicate_producer_ids": len(duplicate_producer_ids),
}

taxonomy["unique_types"] = len([k for k, v in taxonomy["type"].items() if v > 0])
taxonomy["unique_docs"] = len([k for k, v in taxonomy["doc"].items() if v > 0])
taxonomy["unique_varieties"] = len([k for k, v in taxonomy["varieties"].items() if v > 0])

taxonomy["aroma_total_stats"] = dist_stats(taxonomy["aroma_total_lengths"])
taxonomy["pairing_stats"] = dist_stats(taxonomy["pairing_lengths"])

# -----------------------------
# Write reports
# -----------------------------

Path("audit-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
Path("audit-flags.json").write_text(json.dumps(flags, indent=2, ensure_ascii=False), encoding="utf-8")
Path("audit-taxonomy.json").write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False), encoding="utf-8")

# -----------------------------
# Terminal output
# -----------------------------

print("\nPortuguese Wine DB — Audit Summary\n")
print("-" * 72)
for region, stats in summary.items():
    if region == "_totals":
        continue
    print(
        f"{region:<18}"
        f" wines={stats['wines']:>4}"
        f" producers={stats['producers']:>3}"
        f" missing_req={stats['missing_required']:>3}"
        f" unknown={stats['unknown_fields']:>3}"
        f" thin_aromas={stats['thin_aromas']:>4}"
        f" empty_pairing={stats['empty_pairing']:>3}"
        f" miss_struct={stats['missing_structure_keys']:>3}"
        f" red_no_tan={stats['missing_tannins_on_red']:>3}"
    )
print("-" * 72)
print(f"TOTAL WINES:     {total_wines}")
print(f"TOTAL PRODUCERS: {total_producers}")
print(f"DUP WINE IDS:    {len(duplicate_wine_ids)}")
print(f"DUP PROD IDS:    {len(duplicate_producer_ids)}")

if taxonomy["aroma_total_lengths"]:
    print("\nAROMAS (total descriptors per wine):")
    print(f"  min={min(taxonomy['aroma_total_lengths'])} "
          f"median={median(taxonomy['aroma_total_lengths'])} "
          f"mean={round(mean(taxonomy['aroma_total_lengths']), 2)} "
          f"max={max(taxonomy['aroma_total_lengths'])}")

if taxonomy["pairing_lengths"]:
    print("\nPAIRING (items per wine):")
    print(f"  min={min(taxonomy['pairing_lengths'])} "
          f"median={median(taxonomy['pairing_lengths'])} "
          f"mean={round(mean(taxonomy['pairing_lengths']), 2)} "
          f"max={max(taxonomy['pairing_lengths'])}")

print("\nReports written:")
print("  audit-summary.json")
print("  audit-flags.json")
print("  audit-taxonomy.json")
print()
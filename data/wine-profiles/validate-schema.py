import json
import sys
import os
import math
from collections import Counter

# -----------------------------
# Schema definition (edit here)
# -----------------------------
# Rule format:
#   "field": {"type": <python type or tuple>, "required": True/False, "nullable": True/False}
# For nested dicts: use "schema": {...}
# For lists: set "item_type"
SCHEMA = {
    "id": {"type": str, "required": True, "nullable": False},
    "name": {"type": str, "required": True, "nullable": False},
    "vintage": {"type": int, "required": True, "nullable": True},
    "doc": {"type": str, "required": True, "nullable": False},
    "type": {"type": str, "required": True, "nullable": False, "enum": ["white", "red", "rosé", "rose", "sparkling", "fortified"]},
    "varieties": {"type": list, "required": True, "nullable": False, "item_type": str, "non_empty": True},
    "quinta": {"type": str, "required": False, "nullable": True},
    "notes": {"type": str, "required": False, "nullable": True},
    
    "alcohol": {"type": (int, float), "required": True, "nullable": False},
    "acidity_gl": {"type": (int, float), "required": True, "nullable": True},
    "ph": {"type": (int, float), "required": True, "nullable": True},

    "winemaking": {"type": str, "required": True, "nullable": True},

    # Optional but recommended provenance field; require it if you want full uniformity
    # If you truly want it mandatory for all wines, set required=True.
    "structure_source": {"type": str, "required": False, "nullable": False, "enum": ["calculated", "sensory", "unknown"]},

    "structure": {
        "type": dict,
        "required": True,
        "nullable": False,
        "schema": {
            "acidity": {"type": int, "required": True, "nullable": True, "range": [1, 10]},
            "tannins": {"type": int, "required": True, "nullable": True, "range": [1, 10]},
            "body": {"type": str, "required": True, "nullable": True, "enum": ["light", "medium-light", "medium", "medium-full", "full"]},
            "sweetness": {"type": str, "required": True, "nullable": False, "enum": ["dry", "off-dry", "medium", "semi-sweet", "sweet"]},
            "finish": {"type": str, "required": True, "nullable": True, "enum": ["short", "medium", "medium-long", "long", "very long"]},
        },
    },

    "aromas": {
        "type": dict,
        "required": True,
        "nullable": False,
        "schema": {
            "primary": {"type": list, "required": True, "nullable": False, "item_type": str},
            "secondary": {"type": list, "required": True, "nullable": False, "item_type": str},
            "tertiary": {"type": list, "required": True, "nullable": False, "item_type": str},
        },
    },

    "pairing": {
        "type": dict,
        "required": True,
        "nullable": False,
        "schema": {
            "affinities": {"type": list, "required": True, "nullable": False, "item_type": str},
            "notes": {"type": str, "required": True, "nullable": True},
        },
    },
}


# -----------------------------
# Utilities
# -----------------------------
def is_number(x):
    return isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))


def iter_wines(db):
    # Producer-centric: {"producers":[{"producer":..,"wines":[...]}, ...]}
    if isinstance(db, dict) and "producers" in db:
        for p in db["producers"]:
            producer_name = p.get("producer") or p.get("name") or "UNKNOWN_PRODUCER"
            for w in p.get("wines", []) or []:
                yield producer_name, w

    # Flat dict: {"wines":[...]}
    elif isinstance(db, dict) and "wines" in db:
        for w in db.get("wines", []) or []:
            yield w.get("producer") or "UNKNOWN_PRODUCER", w

    # Flat list
    elif isinstance(db, list):
        for w in db:
            yield w.get("producer") or "UNKNOWN_PRODUCER", w

    else:
        raise ValueError("Unknown JSON structure (expected producers-centric or flat wines list).")


def check_value(path, rule, value, errors, warnings):
    # required presence is handled by caller; here we validate type/value
    if value is None:
        if not rule.get("nullable", False):
            errors.append(f"{path}: null_not_allowed")
        return

    expected_type = rule.get("type")
    if expected_type:
        # Special-case numbers: allow int/float for numeric rules
        if expected_type == (int, float):
            if not is_number(value):
                errors.append(f"{path}: expected_number got {type(value).__name__}")
        else:
            if not isinstance(value, expected_type):
                errors.append(f"{path}: expected_{getattr(expected_type, '__name__', str(expected_type))} got {type(value).__name__}")
                return

    # enum
    if "enum" in rule and value is not None:
        if value not in rule["enum"]:
            errors.append(f"{path}: invalid_enum '{value}' allowed={rule['enum']}")

    # numeric range
    if "range" in rule and value is not None:
        lo, hi = rule["range"]
        if not isinstance(value, int):
            errors.append(f"{path}: expected_int_in_range got {type(value).__name__}")
        else:
            if value < lo or value > hi:
                errors.append(f"{path}: out_of_range {value} expected[{lo}..{hi}]")

    # list item type
    if rule.get("type") == list and value is not None:
        item_type = rule.get("item_type")
        if item_type:
            for i, item in enumerate(value):
                if not isinstance(item, item_type):
                    errors.append(f"{path}[{i}]: expected_{item_type.__name__} got {type(item).__name__}")
        if rule.get("non_empty") and len(value) == 0:
            errors.append(f"{path}: must_not_be_empty")


def validate_wine(wine, schema):
    errors = []
    warnings = []

    # Presence check + validate each required field
    for field, rule in schema.items():
        required = rule.get("required", False)

        if field not in wine:
            if required:
                errors.append(f"{field}: missing_required_field")
            continue

        value = wine.get(field)

        # Nested dict schema
        if rule.get("type") == dict and "schema" in rule:
            if value is None:
                if not rule.get("nullable", False):
                    errors.append(f"{field}: null_not_allowed")
                continue
            if not isinstance(value, dict):
                errors.append(f"{field}: expected_dict got {type(value).__name__}")
                continue

            # Validate required subfields
            for subfield, subrule in rule["schema"].items():
                subpath = f"{field}.{subfield}"
                if subfield not in value:
                    if subrule.get("required", False):
                        errors.append(f"{subpath}: missing_required_field")
                    continue
                check_value(subpath, subrule, value.get(subfield), errors, warnings)

            # Extra subfields warning (optional)
            extras = set(value.keys()) - set(rule["schema"].keys())
            if extras:
                warnings.append(f"{field}: extra_keys {sorted(extras)}")

        else:
            check_value(field, rule, value, errors, warnings)

    # Extra top-level fields warning (optional)
#    extras_top = set(wine.keys()) - set(schema.keys())
#    if extras_top:
#        warnings.append(f"extra_top_level_keys {sorted(extras_top)}")

    return errors, warnings


def validate_file(db):
    issues = []
    ids = []

    for producer, wine in iter_wines(db):
        wid = wine.get("id")
        ids.append(wid)

        errors, warnings = validate_wine(wine, SCHEMA)
        if errors or warnings:
            issues.append({
                "producer": producer,
                "id": wid,
                "errors": errors,
                "warnings": warnings,
            })

    # Duplicate id check
    counts = Counter([i for i in ids if i])
    duplicates = [i for i, c in counts.items() if c > 1]
    if duplicates:
        issues.insert(0, {
            "producer": None,
            "id": None,
            "errors": [f"duplicate_ids {duplicates}"],
            "warnings": []
        })

    return {
        "total_wines": len(ids),
        "count_issues": len(issues),
        "issues": issues
    }


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_schema.py <producers-file.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        db = json.load(f)

    report = validate_file(db)

    base = os.path.splitext(os.path.basename(input_path))[0]
    out_path = f"{base}.schema_validation.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Schema validation complete.")
    print("Report written to:", out_path)
    print("Total wines:", report["total_wines"])
    print("Issues:", report["count_issues"])
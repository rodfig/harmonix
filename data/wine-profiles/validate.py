import json
import math
import sys
import os
from collections import Counter


# -----------------------------
# Helpers
# -----------------------------
def is_number(x):
    return isinstance(x, (int, float)) and not (
        isinstance(x, float) and math.isnan(x)
    )


def iter_wines(db):
    """
    Supports:
      producer-centric:
        {"producers":[{"producer":..,"wines":[...]}, ...]}
      flat:
        {"wines":[...]} or [...]
    """
    if isinstance(db, dict) and "producers" in db:
        for p in db["producers"]:
            producer_name = p.get("producer", "UNKNOWN_PRODUCER")
            for w in p.get("wines", []) or []:
                yield producer_name, w

    elif isinstance(db, dict) and "wines" in db:
        for w in db["wines"]:
            yield w.get("producer", "UNKNOWN_PRODUCER"), w

    elif isinstance(db, list):
        for w in db:
            yield w.get("producer", "UNKNOWN_PRODUCER"), w

    else:
        raise ValueError("Unknown JSON structure")


# -----------------------------
# Validation Core
# -----------------------------
def validate(db):

    rows = []
    ids = []

    for producer, wine in iter_wines(db):

        wid = wine.get("id")
        ids.append(wid)

        acidity_gl = wine.get("acidity_gl")
        ph = wine.get("ph")
        alcohol = wine.get("alcohol")

        structure = wine.get("structure") or {}
        structure_acidity = structure.get("acidity")

        missing_required = []
        if not wid:
            missing_required.append("id")
        if not wine.get("name"):
            missing_required.append("name")
        if not wine.get("doc"):
            missing_required.append("doc")
        if not wine.get("type"):
            missing_required.append("type")
        if not wine.get("varieties"):
            missing_required.append("varieties")
        if not is_number(alcohol):
            missing_required.append("alcohol")

        missing_chemistry = []
        if not is_number(acidity_gl):
            missing_chemistry.append("acidity_gl")
        if not is_number(ph):
            missing_chemistry.append("ph")

        plausibility = []

        if is_number(alcohol):
            wine_type = wine.get("type")

            # Alcohol plausibility depends on wine category
            if wine_type == "fortified":
                min_alc, max_alc = 16.0, 22.0
            else:
                min_alc, max_alc = 7.0, 17.0

            if not (min_alc <= alcohol <= max_alc):
                plausibility.append(f"alcohol_out_of_range:{alcohol}")
        
        if is_number(acidity_gl) and not (2.5 <= acidity_gl <= 12):
            plausibility.append(f"ta_out_of_range:{acidity_gl}")

        if is_number(ph) and not (2.7 <= ph <= 4.2):
            plausibility.append(f"ph_out_of_range:{ph}")

        wtype = (wine.get("type") or "").lower()

        # AI (TA/pH) plausibility is calibrated for dry table wines.
        # Skip for fortified wines (Port, etc.) where sugar/alcohol distort the signal.
        if wtype != "fortified":
            if is_number(acidity_gl) and is_number(ph):
                ai = acidity_gl / ph

                # Type-specific plausibility ranges for AI (TA/pH)
                if wtype == "white":
                    lo, hi = 1.6, 2.8
                elif wtype == "red":
                    lo, hi = 1.3, 2.4
                elif wtype == "rose":
                    lo, hi = 1.3, 3.2
                else:
                    lo, hi = 1.4, 2.8  # fallback

                if ai < lo:
                    plausibility.append(f"low_acidity_index:{ai:.2f}")
                elif ai > hi:
                    plausibility.append(f"high_acidity_index:{ai:.2f}")
            
        if structure_acidity is None:
            missing_required.append("structure.acidity")

        rows.append({
            "producer": producer,
            "id": wid,
            "missing_required": missing_required,
            "missing_chemistry": missing_chemistry,
            "plausibility_flags": plausibility
        })

    # Duplicate IDs
    counts = Counter(ids)
    duplicates = [i for i, c in counts.items() if i and c > 1]

    return {
        "total_wines": len(rows),
        "duplicate_ids": duplicates,
        "count_duplicate_ids": len(duplicates),
        "count_missing_required": sum(1 for r in rows if r["missing_required"]),
        "count_missing_chemistry": sum(1 for r in rows if r["missing_chemistry"]),
        "count_plausibility_flagged": sum(1 for r in rows if r["plausibility_flags"]),
        "details": rows
    }


# -----------------------------
# Main entry
# -----------------------------
if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python validate.py <producers-file.json>")
        sys.exit(1)

    db_path = sys.argv[1]

    if not os.path.exists(db_path):
        print(f"File not found: {db_path}")
        sys.exit(1)

    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)

    report = validate(db)

    base = os.path.splitext(os.path.basename(db_path))[0]
    out_path = f"{base}.validation.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Validation complete.")
    print("Report written to:", out_path)
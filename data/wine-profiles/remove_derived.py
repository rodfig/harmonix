import json
import sys
import os


def remove_derived_blocks(db):
    """
    Supports producer-centric and flat wine structures.
    Removes 'derived' key wherever found.
    """

    def clean_wine(w):
        if isinstance(w, dict) and "derived" in w:
            del w["derived"]

    # producer-centric structure
    if isinstance(db, dict) and "producers" in db:
        for producer in db["producers"]:
            for wine in producer.get("wines", []):
                clean_wine(wine)

    # flat {"wines": [...]}
    elif isinstance(db, dict) and "wines" in db:
        for wine in db["wines"]:
            clean_wine(wine)

    # flat list
    elif isinstance(db, list):
        for wine in db:
            clean_wine(wine)

    return db


# -----------------------------
# main
# -----------------------------
if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python remove_derived.py <producers-file.json>")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        db = json.load(f)

    cleaned = remove_derived_blocks(db)

    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = f"{base}.cleaned.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print("✅ Cleanup complete.")
    print("Output written to:", output_path)
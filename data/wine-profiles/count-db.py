import json
from pathlib import Path

DATA_DIR = Path(".")

def is_validation_file(p: Path) -> bool:
    name = p.name
    return name.endswith(".validation.json") or name.endswith(".schema_validation.json")

def load_producer_list(obj):
    """
    Returns a list of producer dicts from a few common top-level shapes.
    """
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        # common pattern: {"producers": [...]}
        if isinstance(obj.get("producers"), list):
            return obj["producers"]
        # sometimes keyed dict of producers: {"Producer A": {...}, ...}
        # treat dict values as producers if they look like dicts
        values = list(obj.values())
        if values and all(isinstance(v, dict) for v in values):
            return values
    return []

def count_wines_for_producer(prod: dict) -> int:
    wines = prod.get("wines", None)

    if wines is None:
        return 0

    # Standard: list of wine dicts
    if isinstance(wines, list):
        return sum(1 for w in wines if isinstance(w, dict))

    # Alternative: dict of wines keyed by name/id
    if isinstance(wines, dict):
        return sum(1 for v in wines.values() if isinstance(v, dict)) or len(wines)

    return 0

producer_files = sorted(
    p for p in DATA_DIR.glob("producers-*.json")
    if not is_validation_file(p)
)

grand_total_producers = 0
grand_total_wines = 0

print("\nPortuguese Wine DB — Counts\n")
print("-" * 60)

for file_path in producer_files:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        producers = load_producer_list(raw)

        # Count only producer entries that are dicts
        producer_dicts = [p for p in producers if isinstance(p, dict)]
        producers_count = len(producer_dicts)
        wines_count = sum(count_wines_for_producer(p) for p in producer_dicts)

        grand_total_producers += producers_count
        grand_total_wines += wines_count

        region_name = file_path.stem.replace("producers-", "")

        print(f"{region_name:<25} Producers: {producers_count:>4} | Wines: {wines_count:>5}")

        # Optional: warn if there were non-dict producer entries (e.g., strings)
        non_dicts = len(producers) - producers_count
        if non_dicts > 0:
            print(f"  ⚠️  Skipped {non_dicts} non-dict producer entries in {file_path.name}")

    except Exception as e:
        print(f"Error reading {file_path.name}: {e}")

print("-" * 60)
print(f"{'TOTAL':<25} Producers: {grand_total_producers:>4} | Wines: {grand_total_wines:>5}")
print()
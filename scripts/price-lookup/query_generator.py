#!/usr/bin/env python3
"""
Generate price lookup queries from wine DB JSON files.

Usage:
    python query_generator.py                          # all producer files, no limit
    python query_generator.py --source vinho-verde     # single region
    python query_generator.py --limit 10               # first N wines (for testing)
    python query_generator.py --source vinho-verde --limit 10
"""

import json
import sys
import argparse
from datetime import date
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR     = PROJECT_ROOT / "data" / "price-lookup"
PROFILES_DIR = PROJECT_ROOT / "data" / "wine-profiles"
OUTPUT_FILE  = DATA_DIR / "price-queries.json"


def load_source_files(source_region=None):
    if source_region:
        pattern = f"producers-{source_region}.json"
        files = list(PROFILES_DIR.glob(pattern))
        if not files:
            print(f"ERROR: No file matching '{pattern}' in {PROFILES_DIR}")
            sys.exit(1)
    else:
        files = sorted(PROFILES_DIR.glob("producers-*.json"))
    return files


def extract_wines(source_files):
    wines = []
    for source_file in source_files:
        with open(source_file, encoding='utf-8') as f:
            data = json.load(f)

        for producer_entry in data.get("producers", []):
            producer_name = producer_entry.get("producer", "")
            for wine in producer_entry.get("wines", []):
                wine_id = wine.get("id")
                name    = wine.get("name")
                vintage = wine.get("vintage")

                if not wine_id or not name:
                    continue

                # query = producer + wine-unique-name, no year.
                # Wine names sometimes repeat the producer brand (e.g. producer="Quinta de Soalheiro",
                # name="Soalheiro Granit") — deduplicate to avoid "Quinta de Soalheiro Soalheiro Granit".
                prod_tokens = set(producer_name.lower().split())
                unique_name_tokens = [t for t in name.split() if t.lower() not in prod_tokens]
                unique_name = " ".join(unique_name_tokens) if unique_name_tokens else name
                query = f"{producer_name} {unique_name}".strip()

                wines.append({
                    "wine_id":     wine_id,
                    "producer":    producer_name,
                    "name":        name,
                    "vintage":     vintage,
                    "query":       query,
                    "source_file": source_file.name,
                })

    return wines


def main():
    parser = argparse.ArgumentParser(description="Generate wine price lookup queries")
    parser.add_argument(
        "--source",
        help="Region slug (e.g. vinho-verde, dao, bairrada). Default: all regions.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit to first N wines (for testing)",
    )
    args = parser.parse_args()

    source_files = load_source_files(args.source)
    wines = extract_wines(source_files)

    if args.limit:
        wines = wines[: args.limit]

    output = {
        "generated_at": date.today().isoformat(),
        "source_files": [f.name for f in source_files],
        "wine_count":   len(wines),
        "wines":        wines,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✓ Generated {len(wines)} queries → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

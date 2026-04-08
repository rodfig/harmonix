#!/usr/bin/env python3
"""
compile-wines.py

Flattens all producers-*.json files into data/wine-profiles/wines-compiled.json.

For each wine:
  - Injects producer name and region from the parent producer object
  - Injects region_key derived from the source filename (e.g. "dao")
  - Appends best known retail price from the price lookup system

Price sources (in order of preference):
  1. data/price-lookup/prices/*.json  → best_retail (per-producer files from csv_matcher)
  2. data/price-lookup/price-results.json → lowest non-null price (manual fallback)

Run from project root or from scripts/ directory.

Rerun this script whenever source data changes:
  - Any producers-*.json modified
  - data/price-lookup/prices/*.json updated (after csv_matcher run)
  - data/price-lookup/price-results.json updated (manual price entry)
"""

import json
import glob
import math
import os

# ---------------------------------------------------------------------------
# Paths (resolved relative to this script's location)
# ---------------------------------------------------------------------------

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
BASE_DIR        = os.path.dirname(SCRIPT_DIR)
PROFILES_DIR    = os.path.join(BASE_DIR, 'data', 'wine-profiles')
PRICE_LOOKUP    = os.path.join(BASE_DIR, 'data', 'price-lookup')
PRICES_DIR      = os.path.join(PRICE_LOOKUP, 'prices')
PRICE_CSV       = os.path.join(PRICE_LOOKUP, 'csv-results.json')  # legacy fallback
PRICE_MANUAL    = os.path.join(PRICE_LOOKUP, 'price-results.json')
OUTPUT          = os.path.join(BASE_DIR, 'data', 'wine-profiles', 'wines-compiled.json')


# ---------------------------------------------------------------------------
# Price lookup
# ---------------------------------------------------------------------------

def load_prices():
    """Return dict: wine_id → best retail price (float or None)."""
    prices = {}

    # Primary: per-producer price files written by csv_matcher.py
    if os.path.isdir(PRICES_DIR):
        for price_file in sorted(glob.glob(os.path.join(PRICES_DIR, '*.json'))):
            with open(price_file, encoding='utf-8') as f:
                data = json.load(f)
            for w in data.get('wines', []):
                wid   = w.get('wine_id')
                price = w.get('best_retail')
                if wid and price is not None:
                    prices[wid] = round(price, 2)
    elif os.path.exists(PRICE_CSV):
        # Legacy fallback: single csv-results.json (pre-migration)
        with open(PRICE_CSV, encoding='utf-8') as f:
            data = json.load(f)
        for w in data.get('wines', []):
            wid   = w.get('wine_id')
            price = w.get('best_retail')
            if wid and price is not None:
                prices[wid] = round(price, 2)

    # Secondary fallback: manual price entries (producer_direct, wprofile data)
    if os.path.exists(PRICE_MANUAL):
        with open(PRICE_MANUAL, encoding='utf-8') as f:
            data = json.load(f)
        for w in data.get('wines', []):
            wid = w.get('wine_id')
            if not wid or wid in prices:
                continue  # already have a scraped price
            best = None
            for source_data in w.get('prices', {}).values():
                p = source_data.get('price')
                if p is not None and (best is None or p < best):
                    best = p
            if best is not None:
                prices[wid] = round(best, 2)

    return prices


# ---------------------------------------------------------------------------
# Compile
# ---------------------------------------------------------------------------

CARTA_THRESHOLD = 20.0   # retail <= this → 1.5×; above → 1.3×

def carta_price(retail):
    """Tiered restaurant markup, rounded up to nearest €0.50."""
    if retail is None:
        return None
    factor = 1.5 if retail <= CARTA_THRESHOLD else 1.3
    return math.ceil(retail * factor / 0.5) * 0.5


def compile_wines():
    prices         = load_prices()
    all_wines      = []
    region_files   = sorted(glob.glob(os.path.join(PROFILES_DIR, 'producers-*.json')))
    priced_count   = 0

    for filepath in region_files:
        # Derive short region key from filename, e.g. "dao"
        filename   = os.path.basename(filepath)
        region_key = filename.replace('producers-', '').replace('.json', '')

        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)

        for producer in data.get('producers', []):
            producer_name = producer.get('producer', '')
            region_label  = producer.get('region', '')

            for wine in producer.get('wines', []):
                entry = dict(wine)                  # shallow copy of all wine fields
                entry['producer']    = producer_name
                entry['region']      = region_label
                entry['region_key']  = region_key
                entry['price_eur']   = prices.get(wine.get('id'))
                entry['carta_price'] = carta_price(entry['price_eur'])

                if entry['price_eur'] is not None:
                    priced_count += 1

                all_wines.append(entry)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(all_wines, f, ensure_ascii=False, indent=2)

    print(f'Regions processed : {len(region_files)}')
    print(f'Wines compiled    : {len(all_wines)}')
    print(f'Wines with price  : {priced_count} / {len(all_wines)}')
    print(f'Output            : {OUTPUT}')


if __name__ == '__main__':
    compile_wines()

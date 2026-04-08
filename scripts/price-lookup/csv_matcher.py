#!/usr/bin/env python3
"""
Wine price matcher — CSV-based (no browser needed).

Writes per-producer price files to prices/{producer-slug}.json.
Each file contains all wines for that producer (found and not-found),
so results are browsable and editable per producer.

Usage:
    python csv_matcher.py                   # all producer files
    python csv_matcher.py --source dao      # single region slug
    python csv_matcher.py --limit 10        # first N wines (testing)
    python csv_matcher.py --verbose         # print match scores per source
"""

import json
import re
import sys
import math
import argparse
import unicodedata
import csv
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

SCRIPT_DIR      = Path(__file__).parent
PROJECT_ROOT    = SCRIPT_DIR.parent.parent
DATA_DIR        = PROJECT_ROOT / "data" / "price-lookup"
PROFILES_DIR    = PROJECT_ROOT / "data" / "wine-profiles"
GARRAFEIRAS_DIR = DATA_DIR / "garrafeiras"
PRICES_DIR      = DATA_DIR / "prices"

# Legacy flat files — used only for one-time migration on first run
_LEGACY_RESULTS   = DATA_DIR / "csv-results.json"
_LEGACY_NOT_FOUND = DATA_DIR / "csv-not-found.json"

MARKUP_LOW  = 1.5
MARKUP_HIGH = 2.0

# Minimum producer name similarity to include a CSV row as candidate.
PRODUCER_MIN = 0.60

# Name similarity thresholds (TF-IDF weighted token F1).
# Higher when producer is confirmed; much higher when falling back to full catalog.
CONFIDENCE_HIGH_PROD   = 0.72
CONFIDENCE_HIGH_NOPROD = 0.88
CONFIDENCE_LOW         = 0.45   # show name_found for manual review


# ──────────────────────────────────────────────────────────────────────────────
# NORMALIZATION
# ──────────────────────────────────────────────────────────────────────────────

# Strip only pure color/classification noise.
# "espumante", "rosé", "reserva" etc. are kept — they discriminate wine types.
# Roman numeral suffixes (iii, iv, vi, ix…) are stripped — edition numbers in CSV names.
NOISE_WORDS = {
    "branco", "tinto", "white", "red", "doc", "igp", "vinho",
    "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii",
}

# Style words that discriminate wine type: if present in our name but absent from
# the matched name, the match is the wrong SKU — downgrade confidence to low.
TYPE_DISCRIMINATORS = {"espumante", "reserva"}


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def normalize_name(text: str) -> str:
    """
    Normalize wine name for token-based comparison:
      - strip diacritics, lowercase
      - remove 4-digit years
      - keep only alphabetic tokens
      - remove color/classification noise words
      - deduplicate consecutive identical tokens
    Variety words, wine types (espumante, reserva...) are preserved.
    """
    if not text:
        return ""
    text = _strip_accents(text).lower()
    text = re.sub(r"\b(19|20)\d{2}\b", "", text)
    tokens = re.findall(r"[a-z]+", text)
    out = []
    for t in tokens:
        if t not in NOISE_WORDS:
            out.append(t)
    deduped = []
    for t in out:
        if not deduped or t != deduped[-1]:
            deduped.append(t)
    return " ".join(deduped).strip()


def normalize_producer(text: str) -> str:
    if not text:
        return ""
    return _strip_accents(text).lower().strip()


def is_subformat(row: dict) -> bool:
    """Skip 375ml half-bottles and magnums — different SKU, not the standard 750ml.
    Checks both 'name' and 'raw_name' because some sources (PortugalVineyards)
    store volume info only in raw_name."""
    combined = (row.get("name", "") + " " + row.get("raw_name", "")).lower()
    return "375" in combined or "magnum" in combined or "1500" in combined


def strip_producer_prefix(csv_name: str, csv_producer: str) -> str:
    """
    Remove leading tokens from csv_name that appear in csv_producer.
    Example: "ANSELMO MENDES CONTACTO ALVARINHO", "ANSELMO MENDES" → "CONTACTO ALVARINHO"
    Only strips from the start to avoid accidentally removing brand words mid-name.
    """
    prod_tokens = set(_strip_accents(csv_producer).lower().split())
    name_tokens = _strip_accents(csv_name).lower().split()
    while name_tokens and name_tokens[0] in prod_tokens:
        name_tokens.pop(0)
    return " ".join(name_tokens)


# ──────────────────────────────────────────────────────────────────────────────
# TF-IDF WEIGHTED TOKEN SIMILARITY
# ──────────────────────────────────────────────────────────────────────────────

def build_idf(rows: list[dict]) -> tuple[Counter, int]:
    """
    Build token document-frequency map from CSV rows (one doc = one wine name).
    Returns (df_counter, total_docs).
    """
    df: Counter = Counter()
    total = 0
    for row in rows:
        tokens = set(normalize_name(row.get("name", "")).split())
        if tokens:
            df.update(tokens)
            total += 1
    return df, total


def idf_weight(token: str, df: Counter, total: int) -> float:
    """Inverse document frequency weight: log((N+1)/(df+1))."""
    return math.log((total + 1) / (df.get(token, 0) + 1)) + 1.0


def token_f1(
    our_name: str,
    csv_name: str,
    csv_producer: str,
    df: Counter,
    total: int,
) -> float:
    """
    TF-IDF weighted token F1 between our wine name and a CSV name.
    Tries both the raw csv_name and the producer-prefix-stripped variant,
    returning the maximum score.
    Rare tokens (like 'granit', 'jurassico') outweigh common ones ('alvarinho').
    """
    norm_ours = normalize_name(our_name)
    a_tokens  = set(norm_ours.split()) if norm_ours else set()
    if not a_tokens:
        return 0.0

    def _f1(b_tokens: set) -> float:
        if not b_tokens:
            return 0.0
        intersection = a_tokens & b_tokens
        if not intersection:
            return 0.0
        w_inter = sum(idf_weight(t, df, total) for t in intersection)
        w_a     = sum(idf_weight(t, df, total) for t in a_tokens)
        w_b     = sum(idf_weight(t, df, total) for t in b_tokens)
        recall    = w_inter / w_a if w_a else 0.0
        precision = w_inter / w_b if w_b else 0.0
        if recall + precision == 0:
            return 0.0
        return 2 * recall * precision / (recall + precision)

    # Direct comparison
    norm_csv  = normalize_name(csv_name)
    b1 = set(norm_csv.split()) if norm_csv else set()
    s1 = _f1(b1)

    # Stripped-producer comparison
    stripped  = strip_producer_prefix(csv_name, csv_producer)
    norm_str  = normalize_name(stripped)
    b2 = set(norm_str.split()) if norm_str else set()
    s2 = _f1(b2) if b2 else 0.0

    return max(s1, s2)


def producer_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_producer(a), normalize_producer(b)).ratio()


# ──────────────────────────────────────────────────────────────────────────────
# PRICE PARSING & RESTAURANT ESTIMATES
# ──────────────────────────────────────────────────────────────────────────────

def parse_price(raw) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    cleaned = str(raw).replace("\xa0", "").replace(" ", "").replace(",", ".")
    m = re.search(r"\d+\.\d+|\d+", cleaned)
    return float(m.group()) if m else None


def round_menu_price(price: float) -> float:
    return math.ceil(price * 2) / 2


def restaurant_estimates(retail: float) -> dict:
    return {
        "1.5x": round_menu_price(retail * MARKUP_LOW),
        "2.0x": round_menu_price(retail * MARKUP_HIGH),
    }


# ──────────────────────────────────────────────────────────────────────────────
# CSV LOADING
# ──────────────────────────────────────────────────────────────────────────────

def load_csv(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("not_available", "").strip().lower() == "true":
                continue
            if is_subformat(row):
                continue
            rows.append(row)
    return rows


def load_all_csvs() -> dict[str, tuple[list[dict], Counter, int]]:
    """Returns {source_name: (rows, df, total)} per garrafeira."""
    sources = {}
    if not GARRAFEIRAS_DIR.exists():
        print(f"ERROR: {GARRAFEIRAS_DIR} not found.")
        sys.exit(1)
    for garrafeira_dir in sorted(GARRAFEIRAS_DIR.iterdir()):
        if not garrafeira_dir.is_dir():
            continue
        csv_path = garrafeira_dir / "wine_data.csv"
        if csv_path.exists():
            rows = load_csv(csv_path)
            df, total = build_idf(rows)
            sources[garrafeira_dir.name] = (rows, df, total)
            print(f"  Loaded {garrafeira_dir.name:25s}: {len(rows):>5} wines")
    return sources


# ──────────────────────────────────────────────────────────────────────────────
# MATCHING
# ──────────────────────────────────────────────────────────────────────────────

def match_in_source(
    wine_producer: str,
    wine_name: str,
    rows: list[dict],
    df: Counter,
    total: int,
    verbose: bool = False,
) -> dict:
    """
    Two-stage matching within one garrafeira.

    Stage 1 — producer filter:
        Only consider rows where producer sim >= PRODUCER_MIN.
        Falls back to full catalog if no producer candidates found.

    Stage 2 — name match:
        Score each candidate with TF-IDF weighted token F1.
        Returns the best match; price stored only for high-confidence hits.
    """
    null_result = {
        "retail_price": None,
        "name_found":   None,
        "confidence":   "no_result",
        "score":        0.0,
        "url":          None,
    }

    candidates = [
        row for row in rows
        if producer_sim(wine_producer, row.get("producer", "")) >= PRODUCER_MIN
    ]
    producer_confirmed = len(candidates) > 0
    search_pool   = candidates if producer_confirmed else rows
    high_threshold = CONFIDENCE_HIGH_PROD if producer_confirmed else CONFIDENCE_HIGH_NOPROD

    if verbose:
        print(f"      candidates: {len(candidates)}, fallback={not producer_confirmed}")

    best_score = 0.0
    best_row   = None
    for row in search_pool:
        score = token_f1(wine_name, row.get("name", ""), row.get("producer", ""), df, total)
        if score > best_score:
            best_score = score
            best_row   = row

    if best_row is None:
        return null_result

    if verbose:
        print(f"      best={best_score:.3f}  {best_row.get('name','')[:60]!r}")

    if best_score >= high_threshold:
        confidence = "high"
    elif best_score >= CONFIDENCE_LOW:
        confidence = "low"
    else:
        confidence = "no_match"

    # Type-discriminator check: if our wine name contains a style word
    # (espumante, reserva) that is absent from the matched name, the match
    # is the wrong wine — downgrade from high to low so no price is recorded.
    if confidence == "high":
        our_style  = TYPE_DISCRIMINATORS & set(normalize_name(wine_name).split())
        if our_style:
            match_norm = normalize_name(best_row.get("name", ""))
            if our_style - set(match_norm.split()):
                confidence = "low"

    price = parse_price(best_row.get("price")) if confidence == "high" else None

    return {
        "retail_price": price,
        "name_found":   best_row.get("raw_name") or best_row.get("name"),
        "confidence":   confidence,
        "score":        round(best_score, 3),
        "url":          best_row.get("url") if confidence == "high" else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# WINE EXTRACTION FROM PRODUCER FILES
# ──────────────────────────────────────────────────────────────────────────────

def load_source_files(source_region=None) -> list[Path]:
    if source_region:
        pattern = f"producers-{source_region}.json"
        files = list(PROFILES_DIR.glob(pattern))
        if not files:
            print(f"ERROR: No file matching '{pattern}' in {PROFILES_DIR}")
            sys.exit(1)
    else:
        files = sorted(PROFILES_DIR.glob("producers-*.json"))
    return files


def extract_wines(source_files: list[Path]) -> list[dict]:
    wines = []
    for source_file in source_files:
        with open(source_file, encoding="utf-8") as f:
            data = json.load(f)
        for producer_entry in data.get("producers", []):
            producer_name = producer_entry.get("producer", "")
            for wine in producer_entry.get("wines", []):
                wine_id = wine.get("id")
                name    = wine.get("name")
                if not wine_id or not name:
                    continue
                wines.append({
                    "wine_id":  wine_id,
                    "producer": producer_name,
                    "name":     name,
                    "vintage":  wine.get("vintage"),
                })
    return wines


# ──────────────────────────────────────────────────────────────────────────────
# PER-PRODUCER FILE MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

def slugify(producer: str) -> str:
    """Convert producer name to a filesystem-safe slug."""
    s = _strip_accents(producer).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _producer_path(producer: str) -> Path:
    return PRICES_DIR / f"{slugify(producer)}.json"


def load_producer_file(producer: str) -> list[dict]:
    """Load wine list from a producer's price file. Returns [] if file missing."""
    path = _producer_path(producer)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("wines", [])


def save_producer_file(producer: str, wines: list[dict]) -> None:
    """Write per-producer price file."""
    PRICES_DIR.mkdir(exist_ok=True)
    found = sum(1 for w in wines if w.get("status") in ("found", "manual"))
    out = {
        "producer":        producer,
        "generated_at":    datetime.now().isoformat(),
        "found_count":     found,
        "not_found_count": len(wines) - found,
        "wines":           wines,
    }
    with open(_producer_path(producer), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────────────────
# MIGRATION FROM LEGACY FLAT FILES
# ──────────────────────────────────────────────────────────────────────────────

def migrate_from_legacy() -> dict[str, dict]:
    """
    One-time migration: split csv-results.json + csv-not-found.json
    into per-producer files under prices/.
    Returns existing_by_id {wine_id → entry} so the caller can use the
    migrated data immediately without re-reading the new files.
    """
    if not _LEGACY_RESULTS.exists() and not _LEGACY_NOT_FOUND.exists():
        return {}

    print("First run: migrating legacy csv-results.json / csv-not-found.json → prices/ ...")

    by_producer: dict[str, dict[str, dict]] = {}  # producer → {wine_id → entry}

    if _LEGACY_RESULTS.exists():
        data = json.loads(_LEGACY_RESULTS.read_text(encoding="utf-8"))
        for w in data.get("wines", []):
            wid = w.get("wine_id")
            if not wid:
                continue
            prod = w.get("producer", "unknown")
            by_producer.setdefault(prod, {})[wid] = {**w, "status": "found"}

    if _LEGACY_NOT_FOUND.exists():
        data = json.loads(_LEGACY_NOT_FOUND.read_text(encoding="utf-8"))
        for w in data.get("wines", []):
            wid = w.get("wine_id")
            if not wid:
                continue
            prod = w.get("producer", "unknown")
            if prod in by_producer and wid in by_producer[prod]:
                continue  # already in results
            status = "manual" if w.get("best_retail") is not None else "not_found"
            by_producer.setdefault(prod, {})[wid] = {**w, "status": status}

    PRICES_DIR.mkdir(exist_ok=True)
    for producer, wines_dict in by_producer.items():
        save_producer_file(producer, list(wines_dict.values()))

    total = sum(len(v) for v in by_producer.values())
    print(f"  {total} wines across {len(by_producer)} producers → prices/")
    print()

    return {
        wid: entry
        for wines_dict in by_producer.values()
        for wid, entry in wines_dict.items()
    }


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Wine price matcher (CSV-based)")
    parser.add_argument("--source",  help="Region slug (e.g. dao, bairrada). Default: all.")
    parser.add_argument("--limit",   type=int, help="Process only first N wines (testing).")
    parser.add_argument("--verbose", action="store_true", help="Show match details per source.")
    args = parser.parse_args()

    print("Loading garrafeira CSVs ...")
    sources = load_all_csvs()
    source_names = list(sources.keys())
    print()

    # ── Wines in scope ────────────────────────────────────────────────────────
    source_files = load_source_files(args.source)
    all_wines    = extract_wines(source_files)
    if args.limit:
        all_wines = all_wines[: args.limit]

    # In-scope producers in source-file order (unique, order-preserving)
    producers_in_scope = list(dict.fromkeys(w["producer"] for w in all_wines))

    # ── Load persistent state ─────────────────────────────────────────────────
    # First run: migrate legacy flat files if prices/ dir doesn't exist yet.
    if not PRICES_DIR.exists():
        existing_by_id = migrate_from_legacy()
    else:
        existing_by_id = {}

    # Load per-producer files for all in-scope producers.
    # output_by_producer tracks the full wine set (keyed by wine_id) per producer,
    # including wines from other regions loaded in previous runs.
    output_by_producer: dict[str, dict[str, dict]] = {}
    for producer in producers_in_scope:
        wines = load_producer_file(producer)
        wine_dict = {w["wine_id"]: w for w in wines if w.get("wine_id")}
        output_by_producer[producer] = wine_dict
        existing_by_id.update(wine_dict)

    # Wines already resolved (found by CSV or confirmed manually)
    found_ids = {
        wid for wid, w in existing_by_id.items()
        if w.get("status") in ("found", "manual")
    }
    # Not-found map for manual-fix detection (user added best_retail to the file)
    not_found_map = {
        wid: w for wid, w in existing_by_id.items()
        if w.get("status") == "not_found"
    }

    to_process = [w for w in all_wines if w["wine_id"] not in found_ids]

    print(f"Wines in scope  : {len(all_wines)}")
    print(f"Already found   : {len(all_wines) - len(to_process)}")
    print(f"To process      : {len(to_process)}")
    print(f"Garrafeiras     : {', '.join(source_names)}")
    print(f"Markup          : {MARKUP_LOW}x / {MARKUP_HIGH}x retail")
    print()

    newly_found     = []
    still_not_found = []
    n_manual        = 0

    for i, wine in enumerate(to_process, 1):
        wid = wine["wine_id"]

        # ── Manual fix ───────────────────────────────────────────────────────
        # User added best_retail directly to prices/{producer}.json (status: not_found).
        existing = not_found_map.get(wid)
        if existing and existing.get("best_retail") is not None:
            retail = existing["best_retail"]
            existing["status"] = "manual"
            existing["restaurant_estimates"] = restaurant_estimates(retail)
            manual = existing.get("manual")
            if manual:
                src = existing.get("best_source", "manual")
                existing.setdefault("prices", {})[src] = {
                    "retail_price": retail,
                    "name_found":   manual.get("name_found"),
                    "confidence":   "manual",
                    "score":        1.0,
                    "url":          manual.get("url"),
                }
            print(f"[{i}/{len(to_process)}] {wine['name']}  -- manual: €{retail:.2f}")
            newly_found.append(existing)
            n_manual += 1
            continue

        # ── CSV matching ─────────────────────────────────────────────────────
        print(f"[{i}/{len(to_process)}] {wine['producer']} - {wine['name']}")

        prices = {}
        for source_label, (rows, df, total) in sources.items():
            if args.verbose:
                print(f"    [{source_label}]")
            result = match_in_source(
                wine["producer"], wine["name"], rows, df, total, verbose=args.verbose
            )
            prices[source_label] = result

        high_results = {s: r for s, r in prices.items() if r["retail_price"] is not None}

        entry = {
            "wine_id":  wid,
            "producer": wine["producer"],
            "name":     wine["name"],
            "vintage":  wine.get("vintage"),
            "prices":   prices,
        }

        if high_results:
            best_source = min(high_results, key=lambda s: high_results[s]["retail_price"])
            best_price  = high_results[best_source]["retail_price"]
            est         = restaurant_estimates(best_price)
            entry.update({
                "best_retail":          best_price,
                "best_source":          best_source,
                "restaurant_estimates": est,
                "status":               "found",
            })
            print(f"  OK {best_source}: {high_results[best_source]['name_found']}")
            print(f"     Retail: €{best_price:.2f}  |  Menu: €{est['1.5x']:.2f} - €{est['2.0x']:.2f}")
            for s, r in high_results.items():
                if s != best_source:
                    print(f"     Also {s}: €{r['retail_price']:.2f}")
            newly_found.append(entry)
        else:
            entry.update({
                "best_retail":          None,
                "best_source":          None,
                "restaurant_estimates": None,
                "status":               "not_found",
            })
            low_matches = {s: r for s, r in prices.items() if r.get("name_found")}
            if low_matches:
                for s, r in low_matches.items():
                    print(f"  !! {s}: {r['confidence']} -- {r['name_found']!r} (score {r['score']})")
            else:
                print(f"  !! not found in any source")
            still_not_found.append(entry)

    # ── Update in-memory output ───────────────────────────────────────────────
    for entry in newly_found + still_not_found:
        producer = entry["producer"]
        if producer in output_by_producer:
            output_by_producer[producer][entry["wine_id"]] = entry

    # ── Write per-producer files ──────────────────────────────────────────────
    # Preserve original source-file ordering within each producer.
    # Wines from other regions (loaded from a previous run) are appended after.
    source_wids_by_producer: dict[str, list[str]] = {}
    for w in all_wines:
        source_wids_by_producer.setdefault(w["producer"], []).append(w["wine_id"])

    PRICES_DIR.mkdir(exist_ok=True)
    for producer in producers_in_scope:
        wine_dict    = output_by_producer.get(producer, {})
        source_order = source_wids_by_producer.get(producer, [])
        ordered      = [wine_dict[wid] for wid in source_order if wid in wine_dict]
        seen         = set(source_order)
        extras       = [w for wid, w in wine_dict.items() if wid not in seen]
        save_producer_file(producer, ordered + extras)

    # ── Summary ───────────────────────────────────────────────────────────────
    all_resolved = {w["wine_id"] for w in newly_found} | found_ids
    in_scope_found   = sum(1 for w in all_wines if w["wine_id"] in all_resolved)
    in_scope_unfound = len(all_wines) - in_scope_found

    print(f"\n{'=' * 50}")
    print(f"Resolved this run  : {len(newly_found)}  ({n_manual} manual, {len(newly_found) - n_manual} CSV)")
    print(f"In-scope found     : {in_scope_found} / {len(all_wines)}")
    print(f"In-scope not found : {in_scope_unfound}")
    print(f"Output             : prices/  ({len(producers_in_scope)} producer files updated)")


if __name__ == "__main__":
    main()

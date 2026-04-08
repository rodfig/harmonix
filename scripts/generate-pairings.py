#!/usr/bin/env python3
"""
generate-pairings.py

Generates all pairing modes for a specified menu and writes pairings.json.

Usage:
    python scripts/generate-pairings.py --menu nanban-kaiseki
    python scripts/generate-pairings.py --menu nanban-kaiseki --top-per-dish 10

Output:
    data/menus/<menu>/pairings.json

Pairing modes generated:
    per_dish         — top N candidate wines per dish (scored by structural rules)
    meal_suggestion  — 3-wine recommendation: sparkling/white + red + dessert
    pack_pairings    — 2 variants of 4 wine selections covering the full meal
    sequence_pairing — one wine per dish, no repeats, greedy best-available

Rerun whenever wines-compiled.json, menu.json, or dish-profiles.json changes.
"""

import json
import argparse
import os
import random as _random
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)

def get_paths(menu_name):
    menu_dir = os.path.join(BASE_DIR, 'data', 'menus', menu_name)
    return {
        'wines':     os.path.join(BASE_DIR, 'data', 'wine-profiles', 'wines-compiled.json'),
        'rules':     os.path.join(BASE_DIR, 'data', 'wine-profiles', 'pairing-rules.json'),
        'menu':      os.path.join(menu_dir, 'menu.json'),
        'dishes':    os.path.join(menu_dir, 'dish-profiles.json'),
        'wine_list': os.path.join(menu_dir, 'wine-list.json'),
        'output':    os.path.join(menu_dir, 'pairings.json'),
    }

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(menu_name):
    paths = get_paths(menu_name)

    with open(paths['wines'], encoding='utf-8') as f:
        wines = json.load(f)

    with open(paths['rules'], encoding='utf-8') as f:
        rules_data = json.load(f)

    with open(paths['menu'], encoding='utf-8') as f:
        menu_data = json.load(f)

    with open(paths['dishes'], encoding='utf-8') as f:
        dishes_data = json.load(f)

    # Optional wine list filter
    if os.path.exists(paths['wine_list']):
        with open(paths['wine_list'], encoding='utf-8') as f:
            wine_list = json.load(f)
        if wine_list:  # non-empty list → filter
            allowed = set(wine_list)
            wines = [w for w in wines if w['id'] in allowed]

    rules = rules_data['rules']

    # Merge menu.json (presentation + properties) into dish-profiles (pairing) by id.
    # Menu fields are the base; dish-profile fields overlay (food_tags, hard_filters, etc.)
    menu_by_id = {d['id']: d for d in menu_data['dishes']}
    dishes = []
    for dp in dishes_data['dishes']:
        dish = dict(menu_by_id.get(dp['id'], {}))  # start with menu fields
        dish.update(dp)                              # overlay pairing fields
        dishes.append(dish)

    pairing_config = dishes_data['pairing_config']

    # meal_arcs uses sequence numbers (from menu.json via merged dish objects)
    sequence_to_id = {d['sequence']: d['id'] for d in dishes}
    meal_arcs = {}
    for k, seqs in dishes_data['meal_arcs'].items():
        if k.startswith('_'):
            continue
        meal_arcs[k] = [sequence_to_id[s] for s in seqs if s in sequence_to_id]

    return wines, rules, dishes, meal_arcs, pairing_config

# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

def parse_cond(val_str):
    """Parse '>= 7' → ('>=', 7.0) or 'white' → ('==', 'white')."""
    s = str(val_str).strip()
    for op in ['>=', '<=', '!=', '>', '<']:
        if s.startswith(op):
            tail = s[len(op):].strip()
            try:
                return op, float(tail)
            except ValueError:
                return op, tail
    try:
        return '==', float(s)
    except ValueError:
        return '==', s

def get_field(wine, key):
    """Retrieve a wine field — structural keys come from wine['structure']."""
    STRUCTURAL = {'acidity', 'tannins', 'body', 'sweetness', 'finish'}
    if key in STRUCTURAL:
        return wine.get('structure', {}).get(key)
    if key == 'id_ref':
        return wine.get('id', '')
    if key == 'region_ref':
        return wine.get('region', '')
    return wine.get(key)

def check_condition(wine, conditions):
    """Return True if wine satisfies every condition in the dict."""
    for key, cond_str in conditions.items():
        op, expected = parse_cond(cond_str)
        val = get_field(wine, key)
        if val is None:
            return False
        # Substring match for reference fields
        if key in ('id_ref', 'region_ref'):
            if str(expected).lower() not in str(val).lower():
                return False
            continue
        try:
            v, e = float(val), float(expected)
            ok = {'>=': v >= e, '<=': v <= e, '>': v > e,
                  '<': v < e,  '==': v == e, '!=': v != e}[op]
        except (ValueError, TypeError):
            ok = {'==': str(val) == str(expected),
                  '!=': str(val) != str(expected)}.get(op, False)
        if not ok:
            return False
    return True

# ---------------------------------------------------------------------------
# Hard filters
# ---------------------------------------------------------------------------

def passes_filters(wine, filt):
    """Return True if wine passes all hard filters for a dish."""
    if not filt:
        return True
    wtype   = wine.get('type', '')
    struct  = wine.get('structure', {})
    body    = struct.get('body')
    sweet   = struct.get('sweetness')
    tannins = struct.get('tannins')

    if 'type_allow' in filt and wtype not in filt['type_allow']:
        return False
    if 'body_allow' in filt and body and body not in filt['body_allow']:
        return False
    if 'body_exclude' in filt and body and body in filt['body_exclude']:
        return False
    if 'sweetness_allow' in filt and sweet and sweet not in filt['sweetness_allow']:
        return False
    if 'sweetness_exclude' in filt and sweet and sweet in filt['sweetness_exclude']:
        return False
    if 'tannins_max' in filt and tannins is not None and tannins > filt['tannins_max']:
        return False
    if 'alcohol_max' in filt:
        alcohol = wine.get('alcohol')
        if alcohol is not None and alcohol > filt['alcohol_max']:
            return False
    return True

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

PRIMARY_BONUS = 3   # extra pts when a rule fires on the dish's dominant element

def score_wine(wine, dish, rules):
    """
    Score a wine against a dish using dimensional max-per-dimension scoring.

    Each rule belongs to a 'dimension' (acidity, body, tannin, sweetness, style).
    Within each dimension only the highest-scoring rule contributes to the total,
    preventing multiple rules for the same structural property from stacking.

    Bonus rules (score_bonus field) are an exception: they represent distinct
    aromatic/cultural matching criteria and still accumulate.

    Conflict rules carry negative scores.  If no positive rule fires in that
    dimension the penalty applies; if a positive rule also fires, max() selects
    the positive (mutually-exclusive conditions in practice).

    primary_tag: if a dish defines a primary_tag (dominant pairing driver), any
    rule whose food_tags include that tag receives PRIMARY_BONUS added to its pts
    before the dimensional max comparison.  This rewards wines that address the
    dish's main pairing challenge over wines that only match secondary elements.

    Returns (total_score, best_rule_id, best_reason).
    Assumes hard filters already applied.
    """
    dish_tags   = set(dish.get('food_tags', []))
    primary_tag = dish.get('primary_tag')          # dominant pairing driver
    dim_scores  = {}   # dimension -> best score so far
    bonus_total = 0
    best_pos_score, best_rule = 0, None

    for rule in rules:
        rule_tags = set(rule.get('food_tags', []))
        if not dish_tags & rule_tags:
            continue
        if not check_condition(wine, rule.get('wine_condition', {})):
            continue

        if 'score_bonus' in rule:
            bonus_total += rule['score_bonus']
        else:
            pts = rule.get('score', 0)
            # Reward rules that fire on the dominant element
            if primary_tag and primary_tag in rule_tags:
                pts += PRIMARY_BONUS
            dim = rule.get('dimension', '_unassigned')
            prev = dim_scores.get(dim)
            if prev is None or pts > prev:
                dim_scores[dim] = pts
            # Track best positive rule for reason display
            if pts > best_pos_score:
                best_pos_score = pts
                best_rule = rule

    total   = sum(dim_scores.values()) + bonus_total
    reason  = best_rule['reason'] if best_rule else None
    rule_id = best_rule['id']     if best_rule else None
    return total, rule_id, reason

def to_grapes(score):
    """Map dimensional score to 1-5 grape display value.

    With dimensional scoring, top practical scores are ~20-26 (2-3 strong
    dimensions + bonuses). Thresholds are calibrated accordingly.
    """
    if score >= 22: return 5
    if score >= 16: return 4
    if score >= 10: return 3
    if score >=  6: return 2
    return 1

def wine_card(wine, score, rule_id, reason):
    """Return a display-ready wine dict for pairings.json."""
    return {
        'wine_id':       wine['id'],
        'name':          wine['name'],
        'producer':      wine['producer'],
        'region':        wine['region'],
        'region_key':    wine['region_key'],
        'doc':           wine.get('doc'),
        'type':          wine.get('type'),
        'vintage':       wine.get('vintage'),
        'varieties':     wine.get('varieties', []),
        'price_eur':     wine.get('price_eur'),
        'carta_price':   wine.get('carta_price'),
        'structure':     wine.get('structure', {}),
        'score_raw':     round(score, 1),
        'score_display': to_grapes(score),
        'primary_rule':  rule_id,
        'reason':        reason,
    }

# ---------------------------------------------------------------------------
# Mode 1 — Per-dish
# ---------------------------------------------------------------------------

def build_per_dish(dishes, wines, rules, top_n=10, min_score=4):
    result = {}
    for dish in dishes:
        filt = dish.get('hard_filters', {})
        candidates = []
        for wine in wines:
            if not passes_filters(wine, filt):
                continue
            s, rid, reason = score_wine(wine, dish, rules)
            if s >= min_score:
                candidates.append((s, wine, rid, reason))

        def sort_key(item):
            s, wine, rid, reason = item
            struct   = wine.get('structure', {})
            acidity  = struct.get('acidity') or 0
            price    = wine.get('price_eur') or 999
            return (-s, -acidity, price)

        candidates.sort(key=sort_key)
        result[dish['id']] = [wine_card(w, s, r, rz) for s, w, r, rz in candidates[:top_n]]
    return result

# ---------------------------------------------------------------------------
# Mode 2 — Meal suggestion
# ---------------------------------------------------------------------------

def build_meal_suggestion(dishes, wines, rules, meal_arcs, pairing_config):
    """
    3-wine recommendation: sparkling/white · red · dessert.
    Each role returns top 5 candidates so the user can choose.
    Arc lists come from pairing_config['meal_suggestion'].
    """
    dish_by_id = {d['id']: d for d in dishes}
    arc_dishes  = {arc: courses for arc, courses in meal_arcs.items()}
    ms = pairing_config['meal_suggestion']

    savory_ids  = [d for arc in ms['role_light']   for d in arc_dishes.get(arc, [])]
    rich_ids    = [d for arc in ms['role_red']     for d in arc_dishes.get(arc, [])]
    dessert_ids = [d for arc in ms['role_dessert'] for d in arc_dishes.get(arc, [])]

    def avg_score(wine, dish_ids, force_filters=True):
        scores = []
        for did in dish_ids:
            dish = dish_by_id[did]
            if force_filters and not passes_filters(wine, dish.get('hard_filters', {})):
                continue
            s, _, _ = score_wine(wine, dish, rules)
            scores.append(s)
        return sum(scores) / len(scores) if scores else 0

    # Role 1: white/sparkling/rosé across savory arcs
    r1 = []
    for wine in wines:
        if wine.get('type') not in ('white', 'sparkling', 'rosé'):
            continue
        s = avg_score(wine, savory_ids)
        if s > 0:
            # Find best individual reason
            best_s, best_rid, best_reason = 0, None, None
            for did in savory_ids:
                dish = dish_by_id[did]
                if not passes_filters(wine, dish.get('hard_filters', {})):
                    continue
                ds, rid, reason = score_wine(wine, dish, rules)
                if ds > best_s:
                    best_s, best_rid, best_reason = ds, rid, reason
            r1.append((s, wine, best_rid, best_reason))
    r1.sort(key=lambda x: -x[0])

    # Role 2: red across savory_rich (no hard filter — reds not in type_allow)
    r2 = []
    for wine in wines:
        if wine.get('type') != 'red':
            continue
        s = avg_score(wine, rich_ids, force_filters=False)
        if s > 0:
            r2.append((s, wine, None, 'Tinto de estrutura moderada para os pratos mais ricos'))
    r2.sort(key=lambda x: -x[0])

    # Role 3: dessert — any wine passing dessert hard filters
    r3 = []
    for wine in wines:
        for did in dessert_ids:
            dish = dish_by_id[did]
            if not passes_filters(wine, dish.get('hard_filters', {})):
                continue
            s, rid, reason = score_wine(wine, dish, rules)
            if s > 0:
                r3.append((s, wine, rid, reason))
    r3.sort(key=lambda x: -x[0])
    # Deduplicate by wine_id
    seen, r3_dedup = set(), []
    for item in r3:
        if item[1]['id'] not in seen:
            seen.add(item[1]['id'])
            r3_dedup.append(item)

    def role_entry(role, description, covers, items, n=5):
        return {
            'role': role,
            'description': description,
            'covers': covers,
            'candidates': [wine_card(w, s, rid, reason) for s, w, rid, reason in items[:n]]
        }

    return {
        'sparkling_white': role_entry(
            'sparkling_white',
            'Para a abertura e pratos leves a médios (cursos 1–6, 9)',
            savory_ids, r1
        ),
        'red': role_entry(
            'red',
            'Tinto para os pratos mais ricos (cursos 5, 7, 8)',
            rich_ids, r2
        ),
        'dessert': role_entry(
            'dessert',
            'Vinho doce ou fortificado para a sobremesa (curso 10)',
            dessert_ids, r3_dedup
        ),
    }

# ---------------------------------------------------------------------------
# Mode 3 — Pack pairings
# ---------------------------------------------------------------------------
#
# Pack configurations are defined in dish-profiles.json under pairing_config.
# Each pack has slots with arc, type_filter, dish_arcs, and body/fortified prefs.
# ---------------------------------------------------------------------------

BODY_RANK = {'light': 0, 'medium-light': 1, 'medium': 2, 'medium-full': 3, 'full': 4}

def build_pack_pairings(dishes, wines, rules, meal_arcs, pairing_config,
                        max_price=50.0, min_price=10.0, rng=None, random_top=3):
    dish_by_id = {d['id']: d for d in dishes}

    def dish_ids_for_arcs(arc_names):
        ids = []
        for arc in arc_names:
            ids.extend(meal_arcs.get(arc, []))
        return ids

    def avg_score_for(wine, dish_ids):
        scores = []
        for did in dish_ids:
            dish = dish_by_id[did]
            if not passes_filters(wine, dish.get('hard_filters', {})):
                continue
            s, _, _ = score_wine(wine, dish, rules)
            scores.append(s)
        return sum(scores) / len(scores) if scores else 0

    def best_reason_for(wine, dish_ids):
        best_s, best_rid, best_r = 0, None, None
        for did in dish_ids:
            dish = dish_by_id[did]
            if not passes_filters(wine, dish.get('hard_filters', {})):
                continue
            s, rid, reason = score_wine(wine, dish, rules)
            if s > best_s:
                best_s, best_rid, best_r = s, rid, reason
        return best_s, best_rid, best_r

    def pick_best(slot, dish_ids, used):
        """Score all eligible wines for a slot, apply style preference, return best unused."""
        type_filter      = slot.get('type_filter')
        prefer_body      = slot.get('prefer_body', 'medium')
        prefer_fortified = slot.get('prefer_fortified', False)
        target_body_rank = BODY_RANK.get(prefer_body, 2)

        candidates = []
        for wine in wines:
            if wine['id'] in used:
                continue
            if type_filter and wine.get('type') not in type_filter:
                continue
            price_check = wine.get('carta_price') or wine.get('price_eur')
            if price_check is not None and price_check > max_price:
                continue
            if price_check is not None and price_check < min_price:
                continue
            s = avg_score_for(wine, dish_ids)
            if s <= 0:
                continue
            bs, rid, reason = best_reason_for(wine, dish_ids)
            struct = wine.get('structure', {})
            body_rank  = BODY_RANK.get(struct.get('body', 'medium'), 2)
            is_fortified = 1 if wine.get('type') == 'fortified' else 0

            body_dist    = abs(body_rank - target_body_rank)
            fortified_pen = 0 if (prefer_fortified == (is_fortified == 1)) else 1
            no_price     = 0 if wine.get('price_eur') is not None else 1
            candidates.append((s, no_price, body_dist, fortified_pen, wine, rid, reason))

        if not candidates:
            return None

        candidates.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
        pool = candidates[:random_top]
        s, _, _, _, best_wine, rid, reason = (rng or _random).choice(pool)
        entry = wine_card(best_wine, s, rid, reason)
        entry['arc']       = slot['arc']
        entry['arc_label'] = slot['arc_label']
        entry['covers']    = dish_ids
        return entry

    def build_pack(cfg):
        used, wines_out = set(), []
        for slot in cfg['slots']:
            dish_ids = dish_ids_for_arcs(slot['dish_arcs'])
            entry = pick_best(slot, dish_ids, used)
            if entry:
                wines_out.append(entry)
                used.add(entry['wine_id'])
        return {
            'label':   cfg['label'],
            'tagline': cfg['tagline'],
            'wines':   wines_out,
        }

    return {cfg['id']: build_pack(cfg) for cfg in pairing_config['pack_pairings']}

# ---------------------------------------------------------------------------
# Mode 4 — Sequence pairing (one per dish, no repeats)
# ---------------------------------------------------------------------------

# Preferred body per meal arc — drives soft body escalation in sequence pairing
ARC_BODY_PREF = {
    'aperitivo':     'light',
    'savory_light':  'light',
    'savory_medium': 'medium',
    'savory_rich':   'medium-full',
    'dessert':       None,   # sweetness filter already constrains dessert wines
}
BODY_ESCALATION_PENALTY = 1.5   # pts deducted per body rank step from arc target


def build_sequence_pairing(dishes, wines, rules, per_dish, rng=None, random_top=3):
    """Greedy assignment: best available wine per course in sequence order.

    Applies a soft body-escalation preference: wines whose body matches the
    arc's target body are ranked higher.  The penalty (1.5 pts per rank step)
    is intentionally small — it breaks ties and nudges selection without
    overriding a clearly better structural match.
    """
    used, result = set(), []
    rand = rng or _random

    for dish in sorted(dishes, key=lambda d: d['sequence']):
        chosen = None

        # Soft body preference for this arc
        arc          = dish.get('meal_arc', '')
        pref_body    = ARC_BODY_PREF.get(arc)
        target_brank = BODY_RANK.get(pref_body, 2) if pref_body else None

        def body_adjusted(candidate):
            if target_brank is None:
                return candidate['score_raw']
            brank = BODY_RANK.get(
                candidate.get('structure', {}).get('body', 'medium'), 2)
            return candidate['score_raw'] - abs(brank - target_brank) * BODY_ESCALATION_PENALTY

        # Try per_dish candidates first (already scored and sorted)
        pool = [c for c in per_dish.get(dish['id'], []) if c['wine_id'] not in used]
        if pool:
            pool = sorted(pool, key=lambda c: -body_adjusted(c))
            chosen = rand.choice(pool[:random_top])

        # Fallback: scan full wine list
        if not chosen:
            filt = dish.get('hard_filters', {})
            fb = []
            for wine in wines:
                if wine['id'] in used or not passes_filters(wine, filt):
                    continue
                s, rid, reason = score_wine(wine, dish, rules)
                if s > 0:
                    if target_brank is not None:
                        brank = BODY_RANK.get(
                            wine.get('structure', {}).get('body', 'medium'), 2)
                        s_adj = s - abs(brank - target_brank) * BODY_ESCALATION_PENALTY
                    else:
                        s_adj = s
                    fb.append((s_adj, wine, rid, reason))
            if fb:
                fb.sort(key=lambda x: -x[0])
                s_adj, w, rid, reason = rand.choice(fb[:random_top])
                chosen = wine_card(w, score_wine(w, dish, rules)[0], rid, reason)

        if chosen:
            used.add(chosen['wine_id'])

        result.append({
            'course':    dish['sequence'],   # 'course' key kept for JS compatibility
            'dish_id':   dish['id'],
            'dish_name': dish['name'],
            'wine':      chosen,
        })

    return result

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Generate wine pairings for a menu.')
    parser.add_argument('--menu',           required=True, help='Menu folder name')
    parser.add_argument('--top-per-dish',   type=int,   default=20)
    parser.add_argument('--pack-min-price', type=float, default=10.0,
                        help='Min carta price per wine in pack pairings (default: 10)')
    parser.add_argument('--pack-max-price', type=float, default=50.0,
                        help='Max carta price per wine in pack pairings (default: 50)')
    parser.add_argument('--random-top',     type=int,   default=3,
                        help='Pick randomly from top-N candidates per slot (default: 3)')
    parser.add_argument('--seed',           type=int,   default=None,
                        help='Random seed for reproducible results (omit for fresh draw)')
    args = parser.parse_args()

    rng = _random.Random(args.seed) if args.seed is not None else _random.Random()
    seed_label = str(args.seed) if args.seed is not None else 'random'

    print(f'Menu : {args.menu}')
    print(f'Seed : {seed_label}  random-top: {args.random_top}')
    wines, rules, dishes, meal_arcs, pairing_config = load_data(args.menu)
    print(f'Wines: {len(wines)}  Rules: {len(rules)}  Dishes: {len(dishes)}')

    print('\nPer-dish...')
    per_dish = build_per_dish(dishes, wines, rules, top_n=args.top_per_dish)
    for did, cands in per_dish.items():
        top = cands[0]['score_raw'] if cands else 0
        print(f'  {did}: {len(cands)} candidates  top={top}')

    print('\nMeal suggestion...')
    meal = build_meal_suggestion(dishes, wines, rules, meal_arcs, pairing_config)
    for role, data in meal.items():
        top = data['candidates'][0]['name'] if data['candidates'] else '—'
        print(f'  {role}: {top}')

    print(f'\nPack pairings (carta price: €{args.pack_min_price:.0f}–€{args.pack_max_price:.0f})...')
    packs = build_pack_pairings(dishes, wines, rules, meal_arcs, pairing_config,
                                max_price=args.pack_max_price, min_price=args.pack_min_price,
                                rng=rng, random_top=args.random_top)
    for vid, data in packs.items():
        print(f'  {vid}: {data["label"]}')
        for w in data['wines']:
            carta = w.get('carta_price') or w.get('price_eur')
            print(f'    [{w["arc_label"]}] {w["name"]} / {w["producer"]}  score={w["score_raw"]}  carta=€{carta}')

    print('\nSequence pairing...')
    sequence = build_sequence_pairing(dishes, wines, rules, per_dish,
                                      rng=rng, random_top=args.random_top)
    for entry in sequence:
        name = entry['wine']['name'] if entry['wine'] else '—'
        print(f'  Course {entry["course"]:2d} {entry["dish_id"]:25s} -> {name}')

    output = {
        '_meta': {
            'menu':              args.menu,
            'generated_at':      datetime.now().isoformat(),
            'wines_total':       len(wines),
            'wine_list_filter':  'full_db',
            'active_pack':       'pack_a',
        },
        'per_dish':        per_dish,
        'meal_suggestion': meal,
        'pack_pairings':   packs,
        'sequence_pairing': sequence,
    }

    paths = get_paths(args.menu)
    with open(paths['output'], 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\nWritten -> {paths["output"]}')


if __name__ == '__main__':
    main()

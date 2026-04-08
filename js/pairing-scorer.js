/**
 * pairing-scorer.js
 * =================
 * Client-side port of scripts/generate-pairings.py.
 * Deterministic rule-based scoring — no inference, no external calls.
 *
 * Exports one public function:
 *   computePairings(winesData, rulesData, dishesData, menuData, options)
 *     → { per_dish, meal_suggestion, pack_pairings, sequence_pairing }
 *
 * The output shape is identical to pairings.json so all existing render
 * functions in pairing-engine.js work without changes.
 */

'use strict';

// ─── Constants ───────────────────────────────────────────────────────────────

const PRIMARY_BONUS = 3;

const BODY_RANK = {
    'light': 0, 'medium-light': 1, 'medium': 2, 'medium-full': 3, 'full': 4
};

const ARC_BODY_PREF = {
    'aperitivo':     'light',
    'savory_light':  'light',
    'savory_medium': 'medium',
    'savory_rich':   'medium-full',
    'dessert':       null,
};

const BODY_ESCALATION_PENALTY = 1.5;

// Tags that auto-derive hard filters (used by resolve_dish_profile)
const EXTREME_TAG_FILTERS = {
    sweet:  { sweetness_allow: ['sweet', 'semi-sweet'] },
    bitter: { type_prefer:     ['sparkling'] },
    spicy:  { sweetness_allow: ['off-dry', 'semi-sweet'], tannins_max: 5 },
};
const HARD_FILTER_WEIGHT_THRESHOLD = 0.5;

// ─── Condition evaluation ────────────────────────────────────────────────────

function parseCond(valStr) {
    const s = String(valStr).trim();
    for (const op of ['>=', '<=', '!=', '>', '<']) {
        if (s.startsWith(op)) {
            const tail = s.slice(op.length).trim();
            const n = Number(tail);
            return [op, isNaN(n) ? tail : n];
        }
    }
    const n = Number(s);
    return ['==', isNaN(n) ? s : n];
}

function getField(wine, key) {
    const STRUCTURAL = new Set(['acidity', 'tannins', 'body', 'sweetness', 'finish']);
    if (STRUCTURAL.has(key)) return (wine.structure || {})[key];
    if (key === 'id_ref')     return wine.id    || '';
    if (key === 'region_ref') return wine.region || '';
    return wine[key];
}

function checkCondition(wine, conditions) {
    for (const [key, condStr] of Object.entries(conditions)) {
        const [op, expected] = parseCond(condStr);
        const val = getField(wine, key);
        if (val == null) return false;

        if (key === 'id_ref' || key === 'region_ref') {
            if (!String(val).toLowerCase().includes(String(expected).toLowerCase()))
                return false;
            continue;
        }

        const vn = Number(val), en = Number(expected);
        let ok;
        if (!isNaN(vn) && !isNaN(en)) {
            ok = { '>=': vn >= en, '<=': vn <= en, '>': vn > en,
                   '<': vn < en,  '==': vn === en, '!=': vn !== en }[op];
        } else {
            ok = { '==': String(val) === String(expected),
                   '!=': String(val) !== String(expected) }[op] ?? false;
        }
        if (!ok) return false;
    }
    return true;
}

// ─── Hard filters ─────────────────────────────────────────────────────────────

function passesFilters(wine, filt) {
    if (!filt) return true;
    const wtype   = wine.type || '';
    const struct  = wine.structure || {};
    const body    = struct.body;
    const sweet   = struct.sweetness;
    const tannins = struct.tannins;

    if (filt.type_allow    && !filt.type_allow.includes(wtype))  return false;
    if (filt.body_allow    && body && !filt.body_allow.includes(body))    return false;
    if (filt.body_exclude  && body && filt.body_exclude.includes(body))   return false;
    if (filt.sweetness_allow   && sweet && !filt.sweetness_allow.includes(sweet))  return false;
    if (filt.sweetness_exclude && sweet && filt.sweetness_exclude.includes(sweet)) return false;
    if (filt.tannins_max != null && tannins != null && tannins > filt.tannins_max) return false;
    if (filt.alcohol_max != null) {
        const alc = wine.alcohol;
        if (alc != null && alc > filt.alcohol_max) return false;
    }
    return true;
}

// ─── Dish profile resolution ──────────────────────────────────────────────────

function computeTagWeights(tagSet, interactionTable) {
    const weights = {};
    for (const tag of tagSet) weights[tag] = 1.0;
    for (const entry of interactionTable) {
        const pair = entry.tags;
        if (!pair || pair.length !== 2) continue;
        const [tagA, tagB] = pair;
        if (tagSet.has(tagA) && tagSet.has(tagB)) {
            const target = entry.target;
            if (target in weights) weights[target] *= entry.factor ?? 1.0;
        }
    }
    return weights;
}

function deriveHardFilters(tags, weights) {
    const filters = {};
    for (const [tag, filt] of Object.entries(EXTREME_TAG_FILTERS)) {
        if (tags.has(tag) && (weights[tag] ?? 1.0) >= HARD_FILTER_WEIGHT_THRESHOLD) {
            for (const [k, v] of Object.entries(filt)) {
                if (!(k in filters)) filters[k] = v;
            }
        }
    }
    return filters;
}

function resolveDishProfile(dish, interactionTable) {
    const components  = dish.components || [];
    const hasDishTags = !!(dish.food_tags && dish.food_tags.length);

    if (!components.length) return dish;   // Mode 2 — pass through

    if (hasDishTags) {
        // ── Mode 3 ───────────────────────────────────────────────────────
        const highlights = components.filter(c => c.role === 'highlight');
        if (!highlights.length) return dish;

        const effectiveTags = new Set(dish.food_tags);
        for (const comp of highlights)
            for (const t of (comp.food_tags || [])) effectiveTags.add(t);

        const weights = computeTagWeights(effectiveTags, interactionTable);

        const extraFilters = {};
        for (const comp of highlights) {
            if (comp.generates_hard_filter) {
                const derived = deriveHardFilters(new Set(comp.food_tags || []), weights);
                Object.assign(extraFilters, derived);
            }
        }

        const resolved = Object.assign({}, dish, { food_tags: [...effectiveTags] });
        if (Object.keys(extraFilters).length) {
            const merged = Object.assign({}, resolved.hard_filters || {});
            for (const [k, v] of Object.entries(extraFilters))
                if (!(k in merged)) merged[k] = v;
            resolved.hard_filters = merged;
        }
        return resolved;

    } else {
        // ── Mode 1 ───────────────────────────────────────────────────────
        const allTags = new Set();
        let dominant = null;
        for (const comp of components) {
            for (const t of (comp.food_tags || [])) allTags.add(t);
            if (comp.role === 'dominant_challenge') dominant = comp;
        }

        const weights = computeTagWeights(allTags, interactionTable);

        const hardFilters = Object.assign({}, dish.hard_filters || {});
        if (dominant && dominant.generates_hard_filter) {
            const derived = deriveHardFilters(new Set(dominant.food_tags || []), weights);
            Object.assign(hardFilters, derived);
        }

        let primaryTag = dish.primary_tag || null;
        if (!primaryTag && dominant) {
            const domTags = dominant.food_tags || [];
            primaryTag = domTags.find(t => t in EXTREME_TAG_FILTERS) ?? domTags[0] ?? null;
        }

        const resolved = Object.assign({}, dish, {
            food_tags:   [...allTags],
            hard_filters: hardFilters,
        });
        if (primaryTag) resolved.primary_tag = primaryTag;
        return resolved;
    }
}

// ─── Scoring ──────────────────────────────────────────────────────────────────

function scoreWine(wine, dish, rules) {
    const dishTags   = new Set(dish.food_tags || []);
    const primaryTag = dish.primary_tag || null;
    const dimScores  = {};
    let bonusTotal = 0, bestPosScore = 0, bestRule = null;

    for (const rule of rules) {
        const ruleTags = new Set(rule.food_tags || []);
        if (![...dishTags].some(t => ruleTags.has(t))) continue;
        if (!checkCondition(wine, rule.wine_condition || {})) continue;

        if ('score_bonus' in rule) {
            bonusTotal += rule.score_bonus;
        } else {
            let pts = rule.score || 0;
            if (primaryTag && ruleTags.has(primaryTag)) pts += PRIMARY_BONUS;
            const dim = rule.dimension || '_unassigned';
            if (!(dim in dimScores) || pts > dimScores[dim]) dimScores[dim] = pts;
            if (pts > bestPosScore) { bestPosScore = pts; bestRule = rule; }
        }
    }

    const total  = Object.values(dimScores).reduce((a, b) => a + b, 0) + bonusTotal;
    return {
        score:   total,
        ruleId:  bestRule ? bestRule.id     : null,
        reason:  bestRule ? bestRule.reason : null,
    };
}

function toGrapes(score) {
    if (score >= 22) return 5;
    if (score >= 16) return 4;
    if (score >= 10) return 3;
    if (score >=  6) return 2;
    return 1;
}

function wineCard(wine, score, ruleId, reason) {
    return {
        wine_id:       wine.id,
        name:          wine.name,
        producer:      wine.producer,
        region:        wine.region,
        region_key:    wine.region_key,
        doc:           wine.doc,
        type:          wine.type,
        vintage:       wine.vintage,
        varieties:     wine.varieties || [],
        price_eur:     wine.price_eur,
        carta_price:   wine.carta_price,
        structure:     wine.structure || {},
        score_raw:     Math.round(score * 10) / 10,
        score_display: toGrapes(score),
        primary_rule:  ruleId,
        reason:        reason,
    };
}

// ─── Per-dish ─────────────────────────────────────────────────────────────────

function buildPerDish(dishes, wines, rules, topN = 10, minScore = 4) {
    const result = {};
    for (const dish of dishes) {
        const filt = dish.hard_filters || {};
        const candidates = [];
        for (const wine of wines) {
            if (!passesFilters(wine, filt)) continue;
            const { score, ruleId, reason } = scoreWine(wine, dish, rules);
            if (score >= minScore) candidates.push({ score, wine, ruleId, reason });
        }
        candidates.sort((a, b) => {
            if (b.score !== a.score) return b.score - a.score;
            const aa = (a.wine.structure || {}).acidity || 0;
            const ba = (b.wine.structure || {}).acidity || 0;
            if (ba !== aa) return ba - aa;
            return (a.wine.price_eur || 999) - (b.wine.price_eur || 999);
        });
        result[dish.id] = candidates.slice(0, topN)
            .map(c => wineCard(c.wine, c.score, c.ruleId, c.reason));
    }
    return result;
}

// ─── Meal suggestion ──────────────────────────────────────────────────────────

function buildMealSuggestion(dishes, wines, rules, mealArcs, pairingConfig) {
    const dishById = Object.fromEntries(dishes.map(d => [d.id, d]));
    const ms = pairingConfig.meal_suggestion;

    const savoryIds  = (ms.role_light  || []).flatMap(arc => mealArcs[arc] || []);
    const richIds    = (ms.role_red    || []).flatMap(arc => mealArcs[arc] || []);
    const dessertIds = (ms.role_dessert|| []).flatMap(arc => mealArcs[arc] || []);

    function avgScore(wine, dishIds, forceFilters = true) {
        const scores = [];
        for (const did of dishIds) {
            const dish = dishById[did];
            if (!dish) continue;
            if (forceFilters && !passesFilters(wine, dish.hard_filters || {})) continue;
            scores.push(scoreWine(wine, dish, rules).score);
        }
        return scores.length ? scores.reduce((a, b) => a + b) / scores.length : 0;
    }

    function bestReason(wine, dishIds) {
        let bestS = 0, bestRid = null, bestR = null;
        for (const did of dishIds) {
            const dish = dishById[did];
            if (!dish || !passesFilters(wine, dish.hard_filters || {})) continue;
            const { score, ruleId, reason } = scoreWine(wine, dish, rules);
            if (score > bestS) { bestS = score; bestRid = ruleId; bestR = reason; }
        }
        return { score: bestS, ruleId: bestRid, reason: bestR };
    }

    // Role 1: white / sparkling / rosé
    const r1 = [];
    for (const wine of wines) {
        if (!['white', 'sparkling', 'rosé'].includes(wine.type)) continue;
        const s = avgScore(wine, savoryIds);
        if (s > 0) {
            const { ruleId, reason } = bestReason(wine, savoryIds);
            r1.push({ score: s, wine, ruleId, reason });
        }
    }
    r1.sort((a, b) => b.score - a.score);

    // Role 2: red (no hard filter)
    const r2 = [];
    for (const wine of wines) {
        if (wine.type !== 'red') continue;
        const s = avgScore(wine, richIds, false);
        if (s > 0) r2.push({
            score: s, wine,
            ruleId: null, reason: 'Tinto de estrutura moderada para os pratos mais ricos'
        });
    }
    r2.sort((a, b) => b.score - a.score);

    // Role 3: dessert
    const r3 = [], seen = new Set();
    for (const wine of wines) {
        for (const did of dessertIds) {
            const dish = dishById[did];
            if (!dish || !passesFilters(wine, dish.hard_filters || {})) continue;
            const { score, ruleId, reason } = scoreWine(wine, dish, rules);
            if (score > 0 && !seen.has(wine.id)) {
                seen.add(wine.id);
                r3.push({ score, wine, ruleId, reason });
            }
        }
    }
    r3.sort((a, b) => b.score - a.score);

    function roleEntry(role, description, covers, items, n = 5) {
        return {
            role, description, covers,
            candidates: items.slice(0, n)
                .map(c => wineCard(c.wine, c.score, c.ruleId, c.reason)),
        };
    }

    return {
        sparkling_white: roleEntry('sparkling_white',
            'Para a abertura e pratos leves a médios', savoryIds, r1),
        red: roleEntry('red',
            'Tinto para os pratos mais ricos', richIds, r2),
        dessert: roleEntry('dessert',
            'Vinho doce ou fortificado para a sobremesa', dessertIds, r3),
    };
}

// ─── Pack pairings ────────────────────────────────────────────────────────────

function buildPackPairings(dishes, wines, rules, mealArcs, pairingConfig,
                           { maxPrice = 50, minPrice = 10, randomTop = 3 } = {}) {
    const dishById = Object.fromEntries(dishes.map(d => [d.id, d]));

    function dishIdsForArcs(arcNames) {
        return arcNames.flatMap(arc => mealArcs[arc] || []);
    }

    function avgScoreFor(wine, dishIds) {
        const scores = [];
        for (const did of dishIds) {
            const dish = dishById[did];
            if (!dish || !passesFilters(wine, dish.hard_filters || {})) continue;
            scores.push(scoreWine(wine, dish, rules).score);
        }
        return scores.length ? scores.reduce((a, b) => a + b) / scores.length : 0;
    }

    function bestReasonFor(wine, dishIds) {
        let bestS = 0, bestRid = null, bestR = null;
        for (const did of dishIds) {
            const dish = dishById[did];
            if (!dish || !passesFilters(wine, dish.hard_filters || {})) continue;
            const { score, ruleId, reason } = scoreWine(wine, dish, rules);
            if (score > bestS) { bestS = score; bestRid = ruleId; bestR = reason; }
        }
        return { score: bestS, ruleId: bestRid, reason: bestR };
    }

    function pickBest(slot, dishIds, used) {
        const typeFilter    = slot.type_filter;
        const preferBody    = slot.prefer_body || 'medium';
        const preferFort    = slot.prefer_fortified || false;
        const targetBRank   = BODY_RANK[preferBody] ?? 2;
        const candidates    = [];

        for (const wine of wines) {
            if (used.has(wine.id)) continue;
            if (typeFilter && !typeFilter.includes(wine.type)) continue;
            const price = wine.carta_price ?? wine.price_eur;
            if (price != null && (price > maxPrice || price < minPrice)) continue;
            const s = avgScoreFor(wine, dishIds);
            if (s <= 0) continue;
            const { ruleId, reason } = bestReasonFor(wine, dishIds);
            const bodyRank   = BODY_RANK[((wine.structure || {}).body || 'medium')] ?? 2;
            const isFort     = wine.type === 'fortified';
            const bodyDist   = Math.abs(bodyRank - targetBRank);
            const fortPen    = (preferFort === isFort) ? 0 : 1;
            const noPrice    = wine.price_eur != null ? 0 : 1;
            candidates.push({ s, noPrice, bodyDist, fortPen, wine, ruleId, reason });
        }

        if (!candidates.length) return null;
        candidates.sort((a, b) =>
            (b.s - a.s) || (a.noPrice - b.noPrice) ||
            (a.bodyDist - b.bodyDist) || (a.fortPen - b.fortPen));

        const pool  = candidates.slice(0, randomTop);
        const pick  = pool[Math.floor(Math.random() * pool.length)];
        const entry = wineCard(pick.wine, pick.s, pick.ruleId, pick.reason);
        entry.arc       = slot.arc;
        entry.arc_label = slot.arc_label;
        entry.covers    = dishIds;
        return entry;
    }

    function buildPack(cfg) {
        const used = new Set(), winesOut = [];
        for (const slot of cfg.slots) {
            const dishIds = dishIdsForArcs(slot.dish_arcs);
            const entry   = pickBest(slot, dishIds, used);
            if (entry) { winesOut.push(entry); used.add(entry.wine_id); }
        }
        return { label: cfg.label, tagline: cfg.tagline, wines: winesOut };
    }

    const result = {};
    for (const cfg of pairingConfig.pack_pairings) result[cfg.id] = buildPack(cfg);
    return result;
}

// ─── Sequence pairing ─────────────────────────────────────────────────────────

function buildSequencePairing(dishes, wines, rules, perDish,
                               { randomTop = 3 } = {}) {
    const used = new Set(), result = [];
    const sorted = [...dishes].sort((a, b) => a.sequence - b.sequence);

    function bodyAdjusted(candidate, targetBRank) {
        if (targetBRank == null) return candidate.score_raw;
        const brank = BODY_RANK[((candidate.structure || {}).body || 'medium')] ?? 2;
        return candidate.score_raw - Math.abs(brank - targetBRank) * BODY_ESCALATION_PENALTY;
    }

    for (const dish of sorted) {
        const arc        = dish.meal_arc || '';
        const prefBody   = ARC_BODY_PREF[arc];
        const targetBRank = prefBody != null ? (BODY_RANK[prefBody] ?? 2) : null;

        let chosen = null;

        // Try per_dish candidates first
        const pool = (perDish[dish.id] || []).filter(c => !used.has(c.wine_id));
        if (pool.length) {
            const ranked = [...pool].sort(
                (a, b) => bodyAdjusted(b, targetBRank) - bodyAdjusted(a, targetBRank));
            chosen = ranked[Math.floor(Math.random() * Math.min(randomTop, ranked.length))];
        }

        // Fallback: scan full wine list
        if (!chosen) {
            const filt = dish.hard_filters || {};
            const fb = [];
            for (const wine of wines) {
                if (used.has(wine.id) || !passesFilters(wine, filt)) continue;
                const { score, ruleId, reason } = scoreWine(wine, dish, rules);
                if (score <= 0) continue;
                const brank = BODY_RANK[((wine.structure || {}).body || 'medium')] ?? 2;
                const sAdj  = targetBRank != null
                    ? score - Math.abs(brank - targetBRank) * BODY_ESCALATION_PENALTY
                    : score;
                fb.push({ sAdj, wine, ruleId, reason, score });
            }
            if (fb.length) {
                fb.sort((a, b) => b.sAdj - a.sAdj);
                const pick = fb[Math.floor(Math.random() * Math.min(randomTop, fb.length))];
                chosen = wineCard(pick.wine, pick.score, pick.ruleId, pick.reason);
            }
        }

        if (chosen) used.add(chosen.wine_id);

        result.push({
            course:    dish.sequence,
            dish_id:   dish.id,
            dish_name: dish.name,
            wine:      chosen || null,
        });
    }
    return result;
}

// ─── Top-level entry point ────────────────────────────────────────────────────

/**
 * computePairings(winesData, rulesData, dishesData, menuData, options)
 *
 * winesData  — parsed wines-compiled.json (array)
 * rulesData  — parsed pairing-rules.json  (object with .rules, .systemic_interactions)
 * dishesData — parsed dish-profiles.json  (object with .dishes, .meal_arcs, .pairing_config)
 * menuData   — parsed menu.json           (object with .dishes)
 * options    — { topN, maxPrice, minPrice, randomTop }
 *
 * Returns the same shape as pairings.json.
 */
function computePairings(winesData, rulesData, dishesData, menuData, options = {}) {
    const wines            = winesData;
    const rules            = rulesData.rules;
    const interactionTable = rulesData.systemic_interactions || [];

    // Merge menu.json (presentation) + dish-profiles.json (pairing) by id
    const menuById = Object.fromEntries((menuData.dishes || []).map(d => [d.id, d]));
    const dishes   = (dishesData.dishes || []).map(dp => {
        const merged = Object.assign({}, menuById[dp.id] || {}, dp);
        return resolveDishProfile(merged, interactionTable);
    });

    // Build meal_arcs mapping (sequence → dish id)
    const seqToId = Object.fromEntries(dishes.map(d => [d.sequence, d.id]));
    const mealArcs = {};
    for (const [k, seqs] of Object.entries(dishesData.meal_arcs || {})) {
        if (k.startsWith('_')) continue;
        mealArcs[k] = seqs.filter(s => seqToId[s]).map(s => seqToId[s]);
    }

    const pairingConfig = dishesData.pairing_config;
    const topN = options.topN || 20;

    const perDish        = buildPerDish(dishes, wines, rules, topN);
    const mealSuggestion = buildMealSuggestion(dishes, wines, rules, mealArcs, pairingConfig);
    const packPairings   = buildPackPairings(dishes, wines, rules, mealArcs, pairingConfig, options);
    const sequencePairing = buildSequencePairing(dishes, wines, rules, perDish, options);

    return {
        _meta: {
            source:       'client-side',
            computed_at:  new Date().toISOString(),
            wines_total:  wines.length,
            rules_total:  rules.length,
            dishes_total: dishes.length,
        },
        per_dish:         perDish,
        meal_suggestion:  mealSuggestion,
        pack_pairings:    packPairings,
        sequence_pairing: sequencePairing,
    };
}

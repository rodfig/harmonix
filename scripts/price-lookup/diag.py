"""Diagnostic: understand why certain wines are mismatching."""
import csv
import re
from difflib import SequenceMatcher
from pathlib import Path

from csv_matcher import _strip_accents, strip_producer_prefix

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR     = PROJECT_ROOT / "data" / "price-lookup"
GARRAFEIRAS  = DATA_DIR / "garrafeiras"

# Broader noise set than csv_matcher (includes espumante/sparkling — not discriminators here)
NOISE = {'tinto','branco','rose','rosé','white','red','sparkling','espumante','doc','igp','vinho'}

def norm(text):
    t = _strip_accents(text).lower()
    t = re.sub(r'\b(19|20)\d{2}\b', '', t)
    tokens = re.findall(r'[a-z]+', t)
    return ' '.join(x for x in tokens if x not in NOISE).strip()

def prod_sim(a, b):
    return SequenceMatcher(None, _strip_accents(a).lower(), _strip_accents(b).lower()).ratio()

def name_sim(our_name, csv_name, csv_prod):
    n1 = norm(our_name)
    n2 = norm(csv_name)
    s1 = SequenceMatcher(None, n1, n2).ratio()
    stripped = strip_producer_prefix(csv_name, csv_prod)
    n3 = norm(stripped)
    s2 = SequenceMatcher(None, n1, n3).ratio() if n3 else 0.0
    return max(s1, s2), n1, n2, n3, s1, s2

def load_csv(path):
    with open(path, encoding='utf-8') as f:
        return [r for r in csv.DictReader(f) if r.get('not_available','').lower() != 'true']

gn = load_csv(GARRAFEIRAS / 'GarrafeiraNacional/wine_data.csv')
pv = load_csv(GARRAFEIRAS / 'PortugalVineyards/wine_data.csv')
cl = load_csv(GARRAFEIRAS / 'CaveLusa/wine_data.csv')

print('=== GN rows with REGUEIRO ===')
for r in gn:
    if 'regueiro' in (r.get('producer','') + r.get('name','')).lower():
        print(f'  name={r["name"][:60]}  prod={r["producer"]}  price={r["price"]}')

print()
print('=== GN: top producer sims for Quinta do Regueiro ===')
test_prod = 'Quinta do Regueiro'
seen = set()
cands = []
for r in gn:
    p = r.get('producer','')
    if p not in seen:
        seen.add(p)
        cands.append((prod_sim(test_prod, p), p))
cands.sort(reverse=True)
for sim, p in cands[:8]:
    print(f'  sim={sim:.3f}  prod={p!r}')

print()
print('=== GN: top name_sim for Alvarinho Jurassico ===')
test_wine = 'Alvarinho Jurassico'
results = []
for r in gn:
    best, n1, n2, n3, s1, s2 = name_sim(test_wine, r.get('name',''), r.get('producer',''))
    results.append((best, s1, s2, r.get('name','')[:60], r.get('producer','')[:40], n2, n3))
results.sort(reverse=True)
for best, s1, s2, name, prod, n2, n3 in results[:8]:
    print(f'  best={best:.3f} (direct={s1:.3f}, stripped={s2:.3f})  name={name!r}')
    print(f'    norm_csv={n2!r}   norm_stripped={n3!r}')

print()
print('=== CaveLusa: top name_sim for Contacto Alvarinho ===')
test_wine2 = 'Contacto Alvarinho'
test_prod2 = 'Anselmo Mendes'
cands_cl = [r for r in cl if prod_sim(test_prod2, r.get('producer','')) >= 0.60]
print(f'  Producer candidates: {len(cands_cl)}')
results2 = []
for r in cands_cl:
    best, n1, n2, n3, s1, s2 = name_sim(test_wine2, r.get('name',''), r.get('producer',''))
    results2.append((best, s1, s2, r.get('name','')[:60], r.get('producer',''), n2, n3, r.get('price','')))
results2.sort(reverse=True)
for best, s1, s2, name, prod, n2, n3, price in results2[:8]:
    print(f'  best={best:.3f} (direct={s1:.3f}, stripped={s2:.3f})  price={price}  name={name!r}')
    print(f'    norm_csv={n2!r}   norm_stripped={n3!r}')

print()
print('=== PV: top name_sim for Soalheiro Granit Alvarinho ===')
test_wine3 = 'Soalheiro Granit Alvarinho'
test_prod3 = 'Quinta de Soalheiro'
cands_pv = [r for r in pv if prod_sim(test_prod3, r.get('producer','')) >= 0.60]
print(f'  Producer candidates: {len(cands_pv)}')
results3 = []
for r in cands_pv:
    best, n1, n2, n3, s1, s2 = name_sim(test_wine3, r.get('name',''), r.get('producer',''))
    results3.append((best, s1, s2, r.get('name','')[:60], r.get('producer',''), n2, n3, r.get('price','')))
results3.sort(reverse=True)
for best, s1, s2, name, prod, n2, n3, price in results3[:8]:
    print(f'  best={best:.3f} (direct={s1:.3f}, stripped={s2:.3f})  price={price}  name={name!r}')
    print(f'    norm_csv={n2!r}   norm_stripped={n3!r}')

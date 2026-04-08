#!/usr/bin/env python3
"""
generate-pairings-experimental.py

Thin wrapper around generate-pairings.py that swaps in experimental files:
  - pairing-rules-experimental.json  (instead of pairing-rules.json)
  - dish-profiles-experimental.json  (if present in the menu dir, otherwise dish-profiles.json)
  - pairings-experimental.json       (output, instead of pairings.json)

Usage (same flags as original):
    python scripts/generate-pairings-experimental.py --menu nanban-kaiseki
    python scripts/generate-pairings-experimental.py --menu sushi-test --top-per-dish 20
"""

import importlib.util
import os
import sys

# ---------------------------------------------------------------------------
# Load the original module without executing main()
# ---------------------------------------------------------------------------

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
ORIG_SCRIPT = os.path.join(SCRIPT_DIR, 'generate-pairings.py')

spec = importlib.util.spec_from_file_location('generate_pairings', ORIG_SCRIPT)
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# ---------------------------------------------------------------------------
# Patch get_paths() to point at experimental files
# ---------------------------------------------------------------------------

_original_get_paths = mod.get_paths

def _experimental_get_paths(menu_name):
    paths = _original_get_paths(menu_name)

    # Experimental rules file (same dir as original rules)
    rules_dir             = os.path.dirname(paths['rules'])
    paths['rules']        = os.path.join(rules_dir, 'pairing-rules-experimental.json')

    # Experimental dish profiles (optional — falls back to standard if absent)
    exp_dishes = paths['dishes'].replace(
        'dish-profiles.json', 'dish-profiles-experimental.json'
    )
    if os.path.exists(exp_dishes):
        paths['dishes'] = exp_dishes

    # Experimental output file
    paths['output'] = paths['output'].replace(
        'pairings.json', 'pairings-experimental.json'
    )

    return paths

mod.get_paths = _experimental_get_paths

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    mod.main()

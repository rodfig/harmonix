import json
import sys
from collections import OrderedDict
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python reindent_json.py <input.json> [output.json]", file=sys.stderr)
        sys.exit(2)

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else in_path.with_suffix(".reindented.json")

    # Read with BOM support
    raw = in_path.read_text(encoding="utf-8-sig")

    # Parse (this is where you'll get a precise error if JSON is broken)
    try:
        data = json.loads(raw, object_pairs_hook=OrderedDict)
    except json.JSONDecodeError as e:
        print(f"JSON INVALID: {in_path}", file=sys.stderr)
        print(f"  {e.msg} at line {e.lineno}, column {e.colno} (char {e.pos})", file=sys.stderr)

        # Show a small window around the error location
        lines = raw.splitlines()
        lo = max(1, e.lineno - 3)
        hi = min(len(lines), e.lineno + 3)
        print("\nContext:", file=sys.stderr)
        for n in range(lo, hi + 1):
            prefix = ">>" if n == e.lineno else "  "
            print(f"{prefix} {n:5}: {lines[n-1]}", file=sys.stderr)

        sys.exit(1)

    # Pretty-print with 2 spaces, preserve key order, keep UTF-8 chars
    out_text = json.dumps(data, ensure_ascii=False, indent=2, separators=(",", ": "))
    out_path.write_text(out_text + "\n", encoding="utf-8", newline="\n")

    print(f"OK: wrote reindented JSON to: {out_path}")

if __name__ == "__main__":
    main()
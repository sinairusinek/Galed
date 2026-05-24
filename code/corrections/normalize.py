"""Character-level normalization for HTR ground truth (TASKS.md #1, #4 fixes).

Inconsistent *encoding* of the same handwritten glyph teaches the HTR model
contradictory targets, so the ground truth collapses each set of variants onto
one canonical character. Rules are grouped into named families and applied to
the text inside <Unicode>; geometry is never touched.

Families (see the surveys in code/diagnostics/):

  quotes   every quote-like mark -> Hebrew punctuation by width
           single ' ` ´ ’ ‘ ʼ ′  -> ׳ GERESH    (U+05F3)
           double " “ ” ″ „ ‟    -> ״ GERSHAYIM (U+05F4)
           Includes quotation/scare quotes on purpose (uniform glyphs help
           training); see code/diagnostics/quote_survey.py.

  dashes   dash/hyphen variants -> ASCII hyphen-minus '-' (U+002D)
           – — ‒ ― ‐ ‑ -> -      (the tilde '~' = "approximately" is left
           alone; it is a real semantic, not a hyphen variant.)

Families intentionally NOT included yet (they need date order fixed first, or
context-aware handling, not a flat swap): Roman-numeral and slash/backslash
normalization inside date tokens.

Run (directory -> page_final, default families quotes+dashes):
    python3 -m code.corrections.normalize data/notebook_15908163/page \\
        --out-dir data/notebook_15908163/page_final
    python3 -m code.corrections.normalize <dir> --rules dashes --report
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
NS = {"p": PAGE_NS}
ET.register_namespace("", PAGE_NS)

GERESH = "׳"      # U+05F3
GERSHAYIM = "״"   # U+05F4

FAMILIES: dict[str, dict[int, str]] = {
    "quotes": {
        **{ord(c): GERESH for c in "'’‘ʼ′`´"},
        **{ord(c): GERSHAYIM for c in '"“”″„‟'},
    },
    "dashes": {ord(c): "-" for c in "–—‒―‐‑"},
}
DEFAULT_RULES = ("quotes", "dashes")


def build_table(rules: tuple[str, ...]) -> dict[int, str]:
    table: dict[int, str] = {}
    for r in rules:
        if r not in FAMILIES:
            raise SystemExit(f"unknown rule family {r!r}; have {list(FAMILIES)}")
        table.update(FAMILIES[r])
    return table


def normalize_text(s: str, table: dict[int, str]) -> tuple[str, collections.Counter]:
    changes: collections.Counter = collections.Counter()
    out = []
    for ch in s:
        repl = table.get(ord(ch))
        if repl is not None and repl != ch:
            changes[(ch, repl)] += 1
            out.append(repl)
        else:
            out.append(ch)
    return "".join(out), changes


def transform(tree: ET.ElementTree, table: dict[int, str]) -> collections.Counter:
    changes: collections.Counter = collections.Counter()
    for uni in tree.iterfind(".//p:Unicode", NS):
        if not uni.text:
            continue
        new, c = normalize_text(uni.text, table)
        if c:
            uni.text = new
            changes.update(c)
    return changes


def _write(tree: ET.ElementTree, path: Path) -> None:
    body = ET.tostring(tree.getroot(), encoding="unicode")
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body,
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="PAGE-XML file or directory")
    ap.add_argument("--out", type=Path, help="output file (single-file mode)")
    ap.add_argument("--out-dir", type=Path, help="output directory (same filenames)")
    ap.add_argument("--rules", default=",".join(DEFAULT_RULES),
                    help=f"comma-separated families (default: {','.join(DEFAULT_RULES)}; "
                         f"available: {','.join(FAMILIES)})")
    ap.add_argument("--report", action="store_true", help="count only, don't write")
    args = ap.parse_args(argv)

    table = build_table(tuple(r.strip() for r in args.rules.split(",") if r.strip()))
    if args.path.is_dir():
        files = sorted(p for p in args.path.glob("*.xml") if not p.name.startswith("_"))
    else:
        files = [args.path]
    if not files:
        print(f"no PAGE-XML found at {args.path}", file=sys.stderr)
        return 1

    total: collections.Counter = collections.Counter()
    changed = 0
    for f in files:
        tree = ET.parse(f)
        c = transform(tree, table)
        if not c:
            continue
        changed += 1
        total.update(c)
        print(f"  {f.name}: {sum(c.values())} marks")
        if args.report:
            continue
        if args.out_dir is not None:
            out = args.out_dir / f.name
            out.parent.mkdir(parents=True, exist_ok=True)
            _write(tree, out)
        elif args.out is not None:
            _write(tree, args.out)

    print(f"\n{changed}/{len(files)} files changed, "
          f"{sum(total.values())} chars normalized  (rules: {args.rules})")
    for (src, dst), n in total.most_common():
        print(f"  U+{ord(src):04X} [{src}] -> U+{ord(dst):04X} [{dst}]   {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Find slash/backslash date expressions (TASKS.md #1, diagnosis).

The notebook writes calendar dates as day / Roman-month / year, e.g. ``15/IV/88``
or ``28/VI/1969``. The separator is usually ``/`` but sometimes ``\\``; the month
is a Roman numeral that may be written with ASCII letters (``IV``) or with the
Unicode Roman-numeral codepoints (``Ⅳ`` U+2163); the year is 2- or 4-digit; and
because the surrounding text is RTL, some dates come out reversed as
year / month / day (``88/VIII/20``).

A token is a date iff, after stripping a Hebrew prefix (ב-/ה-/כ-/ל-/ו-) and
trailing punctuation, it splits on ``/`` or ``\\`` into parts where exactly one
part is a Roman-numeral month (I..XII) and the others are Arabic numbers. That
Roman-month test is what separates dates from fractions like ``1/2``, ``3/4``.

The report classifies each date by component order and flags the things the
normalization pass (#1) should fix: backslash separators, Unicode Roman
numerals, and reversed (year-first) order.

Run:  python3 -m code.diagnostics.date_spans data/notebook_15908163/page
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
import unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET

PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
NS = {"p": PAGE_NS}

PREFIX = re.compile(r"^[בהכלומש]-?")           # Hebrew proclitic + optional maqaf
TRIM = "().,;:?־-~־"                       # trailing junk to strip
SEP = re.compile(r"[/\\]")
ROMAN_RE = re.compile(r"^[IVXLCDMivxlcdmⅠ-ⅿ]+$")
ROMAN_MAP = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _deroman(s: str) -> int | None:
    """Roman numeral -> int, accepting ASCII or Unicode Roman codepoints."""
    ascii_form = []
    for ch in s.upper():
        if "Ⅰ" <= ch <= "ⅿ":
            name = unicodedata.name(ch, "")
            # e.g. 'ROMAN NUMERAL FOUR' -> map via numeric value
            v = unicodedata.numeric(ch, None)
            if v is None:
                return None
            ascii_form.append(("?", int(v)))
        elif ch in ROMAN_MAP:
            ascii_form.append((ch, ROMAN_MAP[ch]))
        else:
            return None
    # subtractive evaluation over the resolved values
    vals = [v for _, v in ascii_form]
    total, prev = 0, 0
    for v in reversed(vals):
        total += -v if v < prev else v
        prev = max(prev, v)
    return total or None


def _has_unicode_roman(s: str) -> bool:
    return any("Ⅰ" <= ch <= "ⅿ" for ch in s)


def parse_date(token: str) -> dict | None:
    core = PREFIX.sub("", token).strip(TRIM)
    parts = SEP.split(core)
    if len(parts) < 2:
        return None
    roman_idx = [i for i, p in enumerate(parts) if ROMAN_RE.match(p) and not p.isdigit()]
    if len(roman_idx) != 1:
        return None
    mi = roman_idx[0]
    month = _deroman(parts[mi])
    others = [p for i, p in enumerate(parts) if i != mi]
    if month is None or not (1 <= month <= 12):
        return None
    if not all(p.isdigit() for p in others):
        return None
    nums = [int(p) for p in others]
    # order: month should be in the middle; first part decides day-first vs year-first
    if mi == 1 and len(parts) == 3:
        order = "year/month/day" if nums[0] > 31 or len(parts[0]) == 4 else "day/month/year"
    elif mi == len(parts) - 1:
        order = "day/month" if int(parts[0]) <= 31 else "?/month"
    elif mi == 0:
        order = "month/..."
    else:
        order = "other"
    return {
        "token": token,
        "month": month,
        "order": order,
        "sep": "\\" if "\\" in core else "/",
        "unicode_roman": _has_unicode_roman(core),
    }


def _lines(path: Path):
    for uni in ET.parse(path).iterfind(".//p:Unicode", NS):
        if uni.text:
            yield uni.text


def survey(files: list[Path]) -> None:
    dates: list[dict] = []
    pages_with = set()
    for f in sorted(files):
        for line in _lines(f):
            for tok in line.split():
                d = parse_date(tok)
                if d:
                    dates.append(d)
                    pages_with.add(f.name)

    print(f"# Date-span survey  ({len(files)} pages)\n")
    print(f"Found {len(dates)} date expressions on {len(pages_with)} pages.\n")

    by_order = collections.Counter(d["order"] for d in dates)
    print("## By component order")
    for order, n in by_order.most_common():
        egs = "  ".join(sorted({d["token"] for d in dates if d["order"] == order})[:6])
        print(f"  {order:16s} {n:3d}   e.g. {egs}")

    print("\n## Issues to normalize (TASKS #1)")
    back = sorted({d["token"] for d in dates if d["sep"] == "\\"})
    uni = sorted({d["token"] for d in dates if d["unicode_roman"]})
    rev = sorted({d["token"] for d in dates if d["order"] == "year/month/day"})
    print(f"  backslash separator ({len(back)}): {'  '.join(back)}")
    print(f"  Unicode Roman numerals ({len(uni)}): {'  '.join(uni)}")
    print(f"  reversed year/month/day ({len(rev)}): {'  '.join(rev)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="PAGE-XML file or directory")
    args = ap.parse_args(argv)
    if args.path.is_dir():
        files = sorted(p for p in args.path.glob("*.xml") if not p.name.startswith("_"))
    else:
        files = [args.path]
    if not files:
        print(f"no PAGE-XML found at {args.path}", file=sys.stderr)
        return 1
    survey(files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

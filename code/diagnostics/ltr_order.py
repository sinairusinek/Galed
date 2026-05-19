"""Diagnose suspect LTR runs (dates, Roman numerals) in PAGE-XML.

Scans every <TextLine>/<Unicode> in a directory of PAGE-XML files and flags:

  1. Dates that violate the notebook's dominant convention DD/MM/YY(YY).
     Specifically: tokens shaped (NUM)/(NUM-OR-ROMAN)/(NUM) where the
     LEADING field looks like a year (> 31, or 4 digits) and the TRAILING
     field looks like a day (1..31). These are likely visual-mirror
     transcription errors (transcriber typed the leftmost characters they
     saw on the manuscript first, producing reversed logical order).
  2. Roman-numeral runs that don't parse as a valid Roman numeral
     (e.g. "IIV", "IIX", "XLL"). These are bidi-asymmetric and are the
     strongest evidence of mirror-order entry.

Run:
    python3 -m code.diagnostics.ltr_order data/notebook_15908163/page
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


ROMAN_RE = re.compile(r"\b[IVXLCDM]{2,}\b")
# date candidates: number / roman-or-number / number, slashes or dots
DATE_RE = re.compile(
    r"\b(\d{1,4})\s*[./]\s*([IVXLCDM]+|\d{1,2})\s*[./]\s*(\d{1,4})\b"
)


def is_valid_roman(s: str) -> bool:
    """True iff s is a syntactically valid Roman numeral (1..3999)."""
    if not s or not re.fullmatch(r"[IVXLCDM]+", s):
        return False
    pat = r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
    return re.fullmatch(pat, s) is not None and s != ""


def roman_to_int(s: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total, prev = 0, 0
    for ch in reversed(s):
        v = vals[ch]
        total += -v if v < prev else v
        prev = v
    return total


def parse_field(s: str) -> int | None:
    if s.isdigit():
        return int(s)
    if is_valid_roman(s):
        return roman_to_int(s)
    return None


def scan_file(path: Path) -> list[dict]:
    xml = path.read_text(encoding="utf-8")
    lines = re.findall(r"<TextLine\b[^>]*\bid=\"([^\"]+)\"[^>]*>.*?</TextLine>",
                       xml, re.DOTALL)
    # we need line id + Unicode; pull them together
    issues = []
    for m in re.finditer(r"<TextLine\b[^>]*\bid=\"([^\"]+)\"[^>]*>(.*?)</TextLine>",
                         xml, re.DOTALL):
        line_id, body = m.group(1), m.group(2)
        u_match = re.search(r"<Unicode>(.*?)</Unicode>", body, re.DOTALL)
        if not u_match:
            continue
        text = u_match.group(1)

        # 1. suspect dates
        for dm in DATE_RE.finditer(text):
            a_raw, b_raw, c_raw = dm.group(1), dm.group(2), dm.group(3)
            a, c = parse_field(a_raw), parse_field(c_raw)
            if a is None or c is None:
                continue
            # Notebook convention is DD/MM/YY(YY): leading 1..31, trailing year.
            # Flag the reverse: leading looks like a year (> 31 or 4 digits)
            # and trailing looks like a day (1..31).
            leading_is_year = a > 31 or len(a_raw) == 4
            trailing_is_day = 1 <= c <= 31 and len(c_raw) <= 2
            if leading_is_year and trailing_is_day:
                issues.append({
                    "file": path.name, "line_id": line_id, "kind": "date_reversed",
                    "match": dm.group(0), "text": text,
                })

        # 2. invalid roman numerals
        for rm in ROMAN_RE.finditer(text):
            tok = rm.group(0)
            if not is_valid_roman(tok):
                issues.append({
                    "file": path.name, "line_id": line_id, "kind": "roman_invalid",
                    "match": tok, "text": text,
                })

    return issues


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = Path(argv[1])
    files = sorted(root.glob("*.xml"))
    files = [f for f in files if not f.name.startswith("_")]
    all_issues: list[dict] = []
    for f in files:
        all_issues.extend(scan_file(f))

    by_kind: dict[str, list[dict]] = {}
    for i in all_issues:
        by_kind.setdefault(i["kind"], []).append(i)

    print(f"Scanned {len(files)} files. Found {len(all_issues)} issue(s).\n")
    for kind, items in by_kind.items():
        print(f"=== {kind} ({len(items)}) ===")
        for i in items:
            print(f"  {i['file']}  line {i['line_id']}")
            print(f"    match: {i['match']!r}")
            print(f"    line : {i['text']}")
        print()

    if not all_issues:
        print("No suspect dates or invalid Roman numerals detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

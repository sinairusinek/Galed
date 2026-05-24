"""Survey of geresh / gershayim / quotation-mark usage (TASKS.md #4, diagnosis).

Hebrew keyboards and OCR produce the same *function* with several different
*characters*: the ASCII apostrophe/quote (' ") and the dedicated Hebrew
punctuation geresh/gershayim (׳ U+05F3 / ״ U+05F4), and occasionally curly
quotes or primes. This script is read-only: it scans the PAGE-XML and reports
which characters appear, what each occurrence is *doing*, and where the forms
disagree — so the normalization pass (#4) knows what to target.

Each occurrence is assigned a *function* from its neighbours inside the
whitespace token that contains it:

    acronym    double mark, sole mark in token, right before the last Hebrew
               letter           -> gershayim: ס"מ, ז"א, בד"כ, הנ"ל
    translit   single mark between two Hebrew letters
                                -> Arabic/foreign phoneme geresh: רוג'ם, ח'אד
    abbrev     single mark after a Hebrew letter at token end
                                -> abbreviation geresh: מס', וכד', ר'
    quote      any other double mark (opening, closing, paired, scare, or a
               mark after a prefix letter like ה"סלע")
    measure    a digit/Latin neighbour -> measurement or transliteration
    other      anything left over

The interesting output is the same function written with different characters
(ASCII " ' vs Hebrew ״ ׳) — that is the "diversity" the normalization pass
(#4) has to collapse. The report also pairs double marks per line to flag
dangling (unbalanced) quotes.

Run:  python3 -m code.diagnostics.quote_survey data/notebook_15908163/page
"""
from __future__ import annotations

import argparse
import collections
import sys
import unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET

PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
NS = {"p": PAGE_NS}

SINGLE = {"'", "׳", "‘", "’", "ʼ", "′", "`", "´"}
DOUBLE = {'"', "״", "“", "”", "″", "„", "‟"}
MARKS = SINGLE | DOUBLE
HEBREW = lambda c: "א" <= c <= "ת"  # noqa: E731  (incl. final forms)


def _label(cp: str) -> str:
    try:
        return unicodedata.name(cp)
    except ValueError:
        return "?"


def _last_hebrew(token: str) -> int:
    for j in range(len(token) - 1, -1, -1):
        if HEBREW(token[j]):
            return j
    return -1


def _classify(token: str, i: int) -> str:
    ch = token[i]
    left = token[i - 1] if i > 0 else None
    right = token[i + 1] if i + 1 < len(token) else None
    if (left and (left.isdigit() or (left.isascii() and left.isalpha()))) or \
       (right and (right.isdigit() or (right.isascii() and right.isalpha()))):
        return "measure"
    lh, rh = (left is not None and HEBREW(left)), (right is not None and HEBREW(right))
    if ch in SINGLE:
        if lh and rh:
            return "translit"          # ג'/צ' foreign phoneme inside a word
        if lh and right is None:
            return "abbrev"            # מס', ר', וכד'
        return "quote"
    # double mark
    n_marks = sum(token.count(m) for m in MARKS)
    if lh and n_marks == 1 and i == _last_hebrew(token) - 1:
        return "acronym"               # gershayim before the last letter
    return "quote"                     # opening / closing / paired / scare


def _lines(path: Path):
    for uni in ET.parse(path).iterfind(".//p:Unicode", NS):
        if uni.text:
            yield uni.text


FUNCTIONS = ("acronym", "translit", "abbrev", "quote", "measure", "other")
FUNC_DESC = {
    "acronym": "gershayim in acronym (ס\"מ, ז\"א)",
    "translit": "foreign-phoneme geresh (רוג'ם, ח'אד)",
    "abbrev": "abbreviation geresh (מס', ר')",
    "quote": "quotation / scare quote",
    "measure": "next to a digit / Latin",
    "other": "unclassified",
}


def survey(files: list[Path], examples: int = 6) -> None:
    char_counts: collections.Counter = collections.Counter()
    func: collections.Counter = collections.Counter()          # function -> count
    by_char: collections.Counter = collections.Counter()       # (function, char)
    egs: dict[str, set] = collections.defaultdict(set)
    dangling_lines = 0
    total_lines = 0

    for f in sorted(files):
        for line in _lines(f):
            total_lines += 1
            line_quotes = 0          # double marks used as quotation, this line
            for tok in line.split():
                for i, ch in enumerate(tok):
                    if ch not in MARKS:
                        continue
                    char_counts[ch] += 1
                    fn = _classify(tok, i)
                    func[fn] += 1
                    by_char[(fn, ch)] += 1
                    if len(egs[fn]) < examples:
                        egs[fn].add(tok)
                    if fn == "quote" and ch in DOUBLE:
                        line_quotes += 1
            if line_quotes % 2:
                dangling_lines += 1

    print(f"# Quote / geresh / gershayim survey  ({len(files)} pages, "
          f"{total_lines} text lines)\n")

    print("## Characters present")
    for ch, n in char_counts.most_common():
        kind = "double" if ch in DOUBLE else "single"
        print(f"  {n:5d}  U+{ord(ch):04X}  {_label(ch):32s} [{ch}]  ({kind})")

    print("\n## Function  (inferred from token context)")
    for fn in FUNCTIONS:
        if not func[fn]:
            continue
        forms = ", ".join(f"[{c}]×{n}" for (g, c), n in
                          sorted(by_char.items(), key=lambda kv: -kv[1]) if g == fn)
        sample = "  ".join(sorted(egs[fn]))
        print(f"\n  {fn:9s} {func[fn]:4d}   {FUNC_DESC[fn]}")
        print(f"      forms: {forms}")
        print(f"      e.g.   {sample}")

    print("\n## Form diversity to normalize (same function, ASCII vs Hebrew)")
    for fn, ascii_ch, heb_ch in [("acronym", '"', "״"),
                                 ("translit", "'", "׳"),
                                 ("abbrev", "'", "׳")]:
        a, h = by_char[(fn, ascii_ch)], by_char[(fn, heb_ch)]
        if a or h:
            tgt = heb_ch if fn != "quote" else ascii_ch
            print(f"  {fn:9s}: ASCII [{ascii_ch}]×{a}  vs  Hebrew [{heb_ch}]×{h}"
                  f"   -> normalize to [{tgt}]")

    print("\n## Flags")
    print(f"  lines with an odd number of double marks (dangling quote): "
          f"{dangling_lines} / {total_lines}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path,
                    help="PAGE-XML file or directory of *.xml")
    ap.add_argument("--examples", type=int, default=6,
                    help="example tokens to show per bucket (default 4)")
    args = ap.parse_args(argv)

    if args.path.is_dir():
        files = sorted(p for p in args.path.glob("*.xml") if not p.name.startswith("_"))
    else:
        files = [args.path]
    if not files:
        print(f"no PAGE-XML found at {args.path}", file=sys.stderr)
        return 1
    survey(files, examples=args.examples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

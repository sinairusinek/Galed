"""Line extension + horizontal merge (TASKS.md #3).

For each TextRegion, cluster TextLines that share the same vertical band,
merge each cluster into a single logical line, and make every resulting line
span the full width of its region.

Clustering
----------
Two lines belong to the same physical row when the gap between their baseline
centres is below ``SAME_ROW_FRAC`` of the page's median line spacing. This
catches HTR fragments that sit side-by-side on one written line — a lone
letter pushed to the right margin, or a right/left split around a gap (e.g. an
inline illustration the writer wrote around). Fragments are concatenated
right-to-left (Hebrew is RTL: largest x first).

Subscript / marginal comments written below the baseline are a separate,
unsolved recognition problem and are intentionally left untouched here.

Per merged row
--------------
  - text  : fragments concatenated right-to-left (largest x first).
  - baseline : all fragment baseline points, sorted by x and clamped so the
               first/last point sit on the region's left/right border.
  - Coords : a full-width band [region_xmin .. region_xmax], top/bottom taken
             from the midpoints to the neighbouring rows' baselines.

Reading order is renumbered top-to-bottom. Output goes to page_final/ (or a
stdout report with --report); the file can then be pushed back as a new
transcript layer with `code.transkribus.sync push`.
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
NS = {"p": PAGE_NS}
ET.register_namespace("", PAGE_NS)

# A pair of lines belongs to the same physical row when the gap between their
# baseline centres is below this fraction of the page's median line spacing.
SAME_ROW_FRAC = 0.5


def _pts(s: str) -> list[tuple[int, int]]:
    out = []
    for tok in s.split():
        x, y = tok.split(",")
        out.append((int(x), int(y)))
    return out


def _pts_str(pts: list[tuple[int, int]]) -> str:
    return " ".join(f"{x},{y}" for x, y in pts)


class Line:
    def __init__(self, el: ET.Element):
        self.el = el
        co = el.find("p:Coords", NS)
        bl = el.find("p:Baseline", NS)
        uni = el.find("p:TextEquiv/p:Unicode", NS)
        self.coords = _pts(co.get("points")) if co is not None else []
        self.baseline = _pts(bl.get("points")) if bl is not None else []
        self.text = (uni.text or "") if uni is not None else ""
        ref = self.baseline or self.coords
        self.cy = statistics.fmean(y for _, y in ref) if ref else 0.0
        self.xmax = max((x for x, _ in ref), default=0)  # right edge (RTL start)


def _cluster(lines: list[Line]) -> list[list[Line]]:
    """Group lines into rows by vertical proximity.

    The same-row cutoff is ``SAME_ROW_FRAC`` of the page's median baseline
    gap, so fragments on one written line (gap ~0) stay together while
    genuinely separate lines (gap ~one line height) do not.
    """
    lines = sorted(lines, key=lambda ln: ln.cy)
    gaps = [b.cy - a.cy for a, b in zip(lines, lines[1:])]
    median = statistics.median(gaps) if gaps else 0.0
    thresh = median * SAME_ROW_FRAC
    rows: list[list[Line]] = [[lines[0]]] if lines else []
    for prev, ln in zip(lines, lines[1:]):
        if ln.cy - prev.cy < thresh:
            rows[-1].append(ln)
        else:
            rows.append([ln])
    return rows


def _region_bbox(region: ET.Element) -> tuple[int, int, int, int]:
    co = region.find("p:Coords", NS)
    pts = _pts(co.get("points"))
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    return min(xs), max(xs), min(ys), max(ys)


def _merge_row(row: list[Line], xmin: int, xmax: int) -> tuple[str, list[tuple[int, int]]]:
    """Return (text, extended_baseline) for a clustered row."""
    # RTL: the rightmost fragment is read first.
    ordered = sorted(row, key=lambda ln: ln.xmax, reverse=True)
    text = " ".join(ln.text for ln in ordered if ln.text.strip())

    pts = sorted((p for ln in row for p in ln.baseline), key=lambda p: p[0])
    if not pts:
        return text, pts
    if pts[0][0] > xmin:
        pts.insert(0, (xmin, pts[0][1]))
    else:
        pts[0] = (xmin, pts[0][1])
    if pts[-1][0] < xmax:
        pts.append((xmax, pts[-1][1]))
    else:
        pts[-1] = (xmax, pts[-1][1])
    return text, pts


def _band(centres: list[float], i: int, ymin: int, ymax: int) -> tuple[int, int]:
    c = centres[i]
    if i == 0:
        top = c - (centres[1] - c) / 2 if len(centres) > 1 else ymin
    else:
        top = (centres[i - 1] + c) / 2
    if i == len(centres) - 1:
        bottom = c + (c - centres[i - 1]) / 2 if len(centres) > 1 else ymax
    else:
        bottom = (c + centres[i + 1]) / 2
    return max(ymin, round(top)), min(ymax, round(bottom))


def transform(tree: ET.ElementTree, report: bool = False) -> list[str]:
    notes: list[str] = []
    root = tree.getroot()
    page = root.find("p:Page", NS)
    for region in page.findall("p:TextRegion", NS):
        rid = region.get("id")
        xmin, xmax, ymin, ymax = _region_bbox(region)
        line_els = region.findall("p:TextLine", NS)
        lines = [Line(el) for el in line_els]
        if not lines:
            continue
        rows = _cluster(lines)
        centres = [statistics.fmean(ln.cy for ln in r) for r in rows]

        merged = sum(1 for r in rows if len(r) > 1)
        notes.append(f"{rid}: {len(lines)} lines -> {len(rows)} rows "
                     f"({merged} merged), width clamped to [{xmin},{xmax}]")
        for ri, r in enumerate(rows):
            if len(r) > 1:
                frags = " + ".join(repr(ln.text) for ln in
                                   sorted(r, key=lambda ln: ln.xmax, reverse=True))
                notes.append(f"    row {ri}: merge {frags}")

        if report:
            continue

        # detach old lines, keep region <Coords> and trailing <TextEquiv>
        for el in line_els:
            region.remove(el)
        coords_el = region.find("p:Coords", NS)
        insert_at = list(region).index(coords_el) + 1

        for ri, r in enumerate(rows):
            text, baseline = _merge_row(r, xmin, xmax)
            top, bottom = _band(centres, ri, ymin, ymax)
            tl = ET.Element(f"{{{PAGE_NS}}}TextLine")
            tl.set("id", f"{rid}_l{ri + 1}")
            tl.set("custom", f"readingOrder {{index:{ri};}}")
            co = ET.SubElement(tl, f"{{{PAGE_NS}}}Coords")
            co.set("points", _pts_str([(xmin, top), (xmax, top),
                                       (xmax, bottom), (xmin, bottom)]))
            bl = ET.SubElement(tl, f"{{{PAGE_NS}}}Baseline")
            bl.set("points", _pts_str(baseline))
            te = ET.SubElement(tl, f"{{{PAGE_NS}}}TextEquiv")
            uni = ET.SubElement(te, f"{{{PAGE_NS}}}Unicode")
            uni.text = text
            region.insert(insert_at, tl)
            insert_at += 1
    return notes


def _write(tree: ET.ElementTree, path: Path) -> None:
    body = ET.tostring(tree.getroot(), encoding="unicode")
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body,
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("infile", type=Path)
    ap.add_argument("--out", type=Path, help="output PAGE-XML (default: print report)")
    ap.add_argument("--report", action="store_true",
                    help="only print the clustering plan, don't write")
    args = ap.parse_args(argv)

    tree = ET.parse(args.infile)
    report_only = args.report or args.out is None
    notes = transform(tree, report=report_only)
    for n in notes:
        print(n)
    if not report_only:
        _write(tree, args.out)
        print(f"\n[wrote] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

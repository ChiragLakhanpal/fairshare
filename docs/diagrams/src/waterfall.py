"""08: why Harbor's September revenue moved, as a waterfall: last year's total, the three parts the SQL splits the
change into (volume, mix, share), this year's total. The share bar is the focal bar.

    python3 docs/diagrams/src/waterfall.py   # writes docs/diagrams/08-why-it-moved.html

Values come from ops.decomposition through data_numbers_2.py, in $ thousands to one decimal because the waterfall
verifier reads each printed value as a plain number. scripts/verify-waterfall.py in the plugin checks conservation,
geometry, carries, printed values and sign fills.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import aa

ROOT = Path(__file__).resolve().parents[3]
VW, VH = 1280, 720
BASE, TOP = 520, 140                 # baseline (the $0 floor) and the top of the plot band
X0, BAR, PITCH = 192, 120, 200       # first bar's x, bar width, bar pitch
AXIS_X, AXIS_R = 128, 1176
INK_A = lambda a: f"rgba(54,73,90,{a})"
MUTED_TINT = "rgba(90,113,129,0.15)"
FOCAL_TINT = "rgba(0,108,191,0.12)"


def numbers():
    """Harbor's row, re-run read-only through the venv that has duckdb."""
    py = ROOT / ".venv" / "bin" / "python"
    code = ("import sys; sys.path.insert(0, %r); import data_numbers_2 as d, duckdb; "
            "con = duckdb.connect(str(d.DB), read_only=True); h = d.harbor(con); "
            "print(*(h[k] for k in ('prior', 'volume', 'mix', 'share', 'now', 'fair_share_effect', 'delta')))") % str(Path(__file__).parent)
    out = subprocess.run([str(py), "-c", code], capture_output=True, text=True, check=True).stdout.split()
    return [float(v) for v in out]


def k1(v):  # $ thousands, one decimal
    return round(v / 1000, 1)


def money(v):
    return f"{'−' if v < 0 else '+' if v > 0 else ''}${abs(v):,.0f}"


def fmt(v, signed):
    s = f"{abs(v):.1f}"
    return (("+" if v > 0 else "−") + s) if signed else s


def build():
    prior, volume, mix, share, now, fair, delta = numbers()
    start, d_vol, d_mix, d_share, end = k1(prior), k1(volume), k1(mix), k1(share), k1(now)
    assert round(start + d_vol + d_mix + d_share, 1) == end, "rounded parts must still reconcile"
    top0 = round(BASE - start * (BASE - TOP) / 450)
    s = (BASE - top0) / start                       # the verifier fits the scale from the start anchor
    y = lambda v: BASE - v * s
    bars = [("total", start, "September 2025", "total", False),
            ("delta", d_vol, "Sold more travel", "volume", False),
            ("delta", d_mix, "Route mix", "mix", False),
            ("delta", d_share, "AA’s share fell", "share", True),
            ("total", end, "September 2026", "total", False)]
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    # what the chart is about, inside the image because a slide takes the SVG alone
    out.append(f'<text x="40" y="100" fill="{aa.INK}" font-size="16" font-weight="600" font-family="{aa.SANS}">Harbor Business Travel</text>')
    out.append(f'<text x="40" y="120" fill="{aa.MUTED}" font-size="12" font-family="{aa.MONO}">AA revenue in $ thousands, September 2025 vs September 2026</text>')
    # grid, axes, ticks
    for v in (100, 200, 300, 400):
        out.append(f'<line x1="{AXIS_X}" y1="{y(v):.2f}" x2="{AXIS_R}" y2="{y(v):.2f}" stroke="{INK_A(0.08)}" stroke-width="0.8"/>')
        out.append(f'<text x="{AXIS_X - 8}" y="{y(v) + 4:.2f}" fill="{aa.MUTED}" font-size="11" font-family="{aa.MONO}" text-anchor="end">${v}K</text>')
    out.append(f'<text x="{AXIS_X - 8}" y="{BASE + 4}" fill="{aa.MUTED}" font-size="11" font-family="{aa.MONO}" text-anchor="end">$0</text>')
    out.append(f'<line x1="{AXIS_X}" y1="{y(450):.2f}" x2="{AXIS_X}" y2="{BASE}" stroke="{INK_A(0.25)}" stroke-width="1"/>')
    out.append(f'<line x1="{AXIS_X}" y1="{BASE}" x2="{AXIS_R}" y2="{BASE}" stroke="{INK_A(0.25)}" stroke-width="1"/>')
    # carries first, so the bars paint over their ends
    running, levels = 0.0, []
    for role, v, *_ in bars:
        before = running if role == "delta" else 0.0
        running = round(running + v, 1) if role == "delta" else v
        levels.append((before, running))
    for i in range(len(bars) - 1):
        lvl = levels[i][1]
        x1, x2 = X0 + i * PITCH + BAR, X0 + (i + 1) * PITCH
        out.append(f'<line x1="{x1}" y1="{y(lvl):.2f}" x2="{x2}" y2="{y(lvl):.2f}" stroke="{INK_A(0.55)}" stroke-width="1" data-carry="{lvl:.1f}"/>')
    for i, ((role, v, name, tag, focal), (before, after)) in enumerate(zip(bars, levels)):
        x, cx = X0 + i * PITCH, X0 + i * PITCH + BAR / 2
        lo, hi = (0.0, v) if role == "total" else (min(before, after), max(before, after))
        top, bottom = round(y(hi)), round(y(lo))
        h = bottom - top
        if h <= 0:                                  # a bridge too small to see keeps a hairline, on its exact level
            top, h = round(y(hi), 2), 0.5
            bottom = top + h
        if role == "total":
            fill, stroke = INK_A(0.08), aa.INK
        elif v > 0:
            fill, stroke = MUTED_TINT, aa.MUTED
        else:
            fill, stroke = "#ffffff", aa.MUTED
        if focal:
            stroke = aa.ACCENT
        declared = f"{v:.1f}" if role == "total" else fmt(v, True).replace("−", "-")
        out.append(f'<rect x="{x}" y="{top}" width="{BAR}" height="{h}" fill="{aa.PAPER}"/>')
        out.append(f'<rect x="{x}" y="{top}" width="{BAR}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="1" '
                   f'data-role="{role}" data-value="{declared}" data-name="{name}"/>')
        if focal:
            # ponytail: the verifier knows only the shipped accent strokes, so the declared fill stays the hollow decrease
            # fill and the AA focal tint is laid over it
            out.append(f'<rect x="{x}" y="{top}" width="{BAR}" height="{h}" fill="{FOCAL_TINT}"/>')
        ly = bottom + 12 if (role == "delta" and v < 0) else top - 8
        weight = ' font-weight="600"' if focal else ""
        out.append(f'<text x="{cx}" y="{ly:g}" fill="{aa.ACCENT if focal else aa.MUTED}" font-size="12" font-family="{aa.MONO}"{weight} '
                   f'text-anchor="middle">{fmt(v, role == "delta")}</text>')
        out.append(f'<text x="{cx}" y="{BASE + 28}" fill="{aa.INK}" font-size="16" font-weight="600" font-family="{aa.SANS}" text-anchor="middle">{name}</text>')
        out.append(f'<text x="{cx}" y="{BASE + 48}" fill="{aa.ACCENT if focal else aa.MUTED}" font-size="12" font-family="{aa.MONO}" text-anchor="middle">{tag}</text>')
    # the one callout, and the note that the parts add up
    out.append(f'<text x="40" y="616" fill="{aa.MUTED}" font-size="8" font-weight="500" font-family="{aa.MONO}" letter-spacing="0.18em">FOCAL BAR</text>')
    out.append(f'<text x="144" y="616" fill="{aa.INK}" font-size="14" font-style="italic" font-family="{aa.SANS}">'
               f'AA’s own seat changes would have predicted {money(fair)}, so the drop is not about AA’s seats.</text>')
    out.append(aa.icon("databricks", 144, 630, 16))
    out.append(f'<text x="168" y="643" fill="{aa.MUTED}" font-size="12" font-family="{aa.MONO}">volume + mix + share = {money(delta)}, the whole change, exactly · ops.decomposition</text>')
    # legend strip
    out.append(f'<line x1="40" y1="664" x2="1240" y2="664" stroke="{aa.RULE}" stroke-width="0.8"/>')
    out.append(f'<text x="40" y="694" fill="{aa.MUTED}" font-size="8" font-weight="500" font-family="{aa.MONO}" letter-spacing="0.18em">LEGEND</text>')
    keys = [(INK_A(0.08), aa.INK, "Total"), (MUTED_TINT, aa.MUTED, "Increase"), ("#ffffff", aa.MUTED, "Decrease"), (FOCAL_TINT, aa.ACCENT, "Focal: AA’s share")]
    for i, (fill, stroke, text) in enumerate(keys):
        kx = 144 + i * 200
        out.append(f'<rect x="{kx}" y="682" width="20" height="14" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        out.append(f'<text x="{kx + 28}" y="694" fill="{aa.INK}" font-size="11" font-family="{aa.SANS}">{text}</text>')
    return "\n        ".join(out)


TITLE = "Why a number moved"
DESC = ("Waterfall of Harbor Business Travel's AA revenue from September 2025 to September 2026: more travel added revenue, "
        "the route mix barely moved, and AA's share inside its routes fell, which is the focal bar.")

if __name__ == "__main__":
    html = aa.page(slug="08-why-it-moved", title=TITLE, desc=DESC, eyebrow="fairshare · the data", body=build())
    (aa.OUT / "08-why-it-moved.html").write_text(html, encoding="utf-8")
    print("wrote 08-why-it-moved.html")

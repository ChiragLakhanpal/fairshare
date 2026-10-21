"""08: why Harbor's September revenue moved, as a waterfall: last year's total, the three parts the SQL splits the
change into (volume, mix, share), this year's total. The share bar is the focal bar. The mix part is named in plain words, the
shift between routes: selling more on some routes and less on others, valued at last year's AA share on each route
(lakehouse/06_decomposition.sql), with a note under its bar that for Harbor it barely moved.

    .venv/bin/python docs/diagrams/src/waterfall.py   # writes docs/diagrams/08-why-it-moved.html and 08-why-it-moved-animated.html

Values come from ops.decomposition through deck_facts.py (whole dollars), shown in $ thousands to one decimal because the
waterfall verifier reads each printed value as a plain number. scripts/verify-waterfall.py in the plugin checks conservation,
geometry, carries, printed values and sign fills. The animated page brings the bars in left to right, each with the carry line into it;
the title, the axes and the legend's first three keys stay put. What gives a bar's point away comes in with it: the mix bar's note,
the focal key and the callout with the focal bar, and the sum note with the last total.
"""
from __future__ import annotations

import aa
from deck_facts import fact

VW, VH = 1280, 720
BASE, TOP = 500, 140                 # baseline (the $0 floor) and the top of the plot band; what sits under the floor ends above y 680
X0, BAR, PITCH = 192, 120, 200       # first bar's x, bar width, bar pitch
AXIS_X, AXIS_R = 128, 1176
INK_A = lambda a: f"rgba(54,73,90,{a})"
MUTED_TINT = "rgba(90,113,129,0.15)"
FOCAL_TINT = "rgba(0,108,191,0.12)"
CHART_TITLE = "Why Harbor fell in September"  # the moved slide's title in web/src/deck/slides.ts, word for word


def numbers():
    """Harbor's row: last year's revenue, the three parts, this year's revenue, the fair share effect, the whole change."""
    keys = ("harbor_revenue_sep25_usd", "harbor_volume_usd", "harbor_mix_usd", "harbor_share_usd",
            "harbor_revenue_sep26_usd", "harbor_fair_share_effect_usd", "harbor_delta_usd")
    return [float(fact(k)) for k in keys]


def k1(v):  # $ thousands, one decimal
    return round(v / 1000, 1)


def money(v):
    return f"{'−' if v < 0 else '+' if v > 0 else ''}${abs(v):,.0f}"


def fmt(v, signed):
    s = f"{abs(v):.1f}"
    return (("+" if v > 0 else "−") + s) if signed else s


def build(motion=False):
    prior, volume, mix, share, now, fair, delta = numbers()
    start, d_vol, d_mix, d_share, end = k1(prior), k1(volume), k1(mix), k1(share), k1(now)
    assert round(start + d_vol + d_mix + d_share, 1) == end, "rounded parts must still reconcile"
    top0 = round(BASE - start * (BASE - TOP) / 450)
    s = (BASE - top0) / start                       # the verifier fits the scale from the start anchor
    y = lambda v: BASE - v * s
    bars = [("total", start, "September 2025", "total", False),
            ("delta", d_vol, "Sold more travel", "volume", False),
            ("delta", d_mix, "Shift between routes", "mix", False),
            ("delta", d_share, "AA's share fell", "share", True),
            ("total", end, "September 2026", "total", False)]
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    # what the chart is about, inside the image because a slide takes the SVG alone: the slide's title, since the deck draws none over a figure
    out.append(f'<text data-title x="40" y="100" fill="{aa.INK}" font-size="16" font-weight="600" font-family="{aa.SANS}">{CHART_TITLE}</text>')
    out.append(f'<text x="40" y="120" fill="{aa.MUTED}" font-size="12" font-family="{aa.MONO}">AA revenue in $ thousands, September 2025 vs September 2026</text>')
    # grid, axes, ticks
    for v in (100, 200, 300, 400):
        out.append(f'<line x1="{AXIS_X}" y1="{y(v):.2f}" x2="{AXIS_R}" y2="{y(v):.2f}" stroke="{INK_A(0.08)}" stroke-width="0.8"/>')
        out.append(f'<text x="{AXIS_X - 8}" y="{y(v) + 4:.2f}" fill="{aa.MUTED}" font-size="11" font-family="{aa.MONO}" text-anchor="end">${v}K</text>')
    out.append(f'<text x="{AXIS_X - 8}" y="{BASE + 4}" fill="{aa.MUTED}" font-size="11" font-family="{aa.MONO}" text-anchor="end">$0</text>')
    out.append(f'<line x1="{AXIS_X}" y1="{y(450):.2f}" x2="{AXIS_X}" y2="{BASE}" stroke="{INK_A(0.25)}" stroke-width="1"/>')
    out.append(f'<line x1="{AXIS_X}" y1="{BASE}" x2="{AXIS_R}" y2="{BASE}" stroke="{INK_A(0.25)}" stroke-width="1"/>')
    # Every mark that moves is kept with its motion step (1 to 5, one per bar), in paint order. Static flattens them as they are;
    # motion groups them, so each bar comes in with the carry line into it.
    parts = []

    def put(step, markup):
        parts.append((step, markup))

    # carries first, so the bars paint over their ends
    running, levels = 0.0, []
    for role, v, *_ in bars:
        before = running if role == "delta" else 0.0
        running = round(running + v, 1) if role == "delta" else v
        levels.append((before, running))
    for i in range(len(bars) - 1):
        lvl = levels[i][1]
        x1, x2 = X0 + i * PITCH + BAR, X0 + (i + 1) * PITCH
        put(i + 2, f'<line x1="{x1}" y1="{y(lvl):.2f}" x2="{x2}" y2="{y(lvl):.2f}" stroke="{INK_A(0.55)}" stroke-width="1" data-carry="{lvl:.1f}"/>')
    value_y = []  # each bar's value label's baseline
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
        put(i + 1, f'<rect x="{x}" y="{top}" width="{BAR}" height="{h}" fill="{aa.PAPER}"/>')
        put(i + 1, f'<rect x="{x}" y="{top}" width="{BAR}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="1" '
                   f'data-role="{role}" data-value="{declared}" data-name="{name}"/>')
        if focal:
            # ponytail: the verifier knows only the shipped accent strokes, so the declared fill stays the hollow decrease
            # fill and the AA focal tint is laid over it
            put(i + 1, f'<rect x="{x}" y="{top}" width="{BAR}" height="{h}" fill="{FOCAL_TINT}"/>')
        ly = bottom + 12 if (role == "delta" and v < 0) else top - 8
        value_y.append(ly)
        weight = ' font-weight="600"' if focal else ""
        put(i + 1, f'<text x="{cx}" y="{ly:g}" fill="{aa.ACCENT if focal else aa.MUTED}" font-size="12" font-family="{aa.MONO}"{weight} '
                   f'text-anchor="middle">{fmt(v, role == "delta")}</text>')
        put(i + 1, f'<text x="{cx}" y="{BASE + 28}" fill="{aa.INK}" font-size="16" font-weight="600" font-family="{aa.SANS}" text-anchor="middle">{name}</text>')
        put(i + 1, f'<text x="{cx}" y="{BASE + 48}" fill="{aa.ACCENT if focal else aa.MUTED}" font-size="12" font-family="{aa.MONO}" text-anchor="middle">{tag}</text>')
    # what the mix bar means, in a column under its value label, between the volume and share bars; the last line says how
    # much it moved for Harbor, so it comes in with the bar
    mix_step, mix_cx = 3, X0 + 2 * PITCH + BAR / 2
    assert bars[mix_step - 1][3] == "mix" and abs(d_mix) < 1, "the mix note says the mix barely moved, so it must stay under $1K"
    for k, line in enumerate(("Selling more on some routes", "and less on others, valued at", "last year's AA share on each route.",
                              "For Harbor it barely moved.")):
        put(mix_step, f'<text x="{mix_cx:g}" y="{round(value_y[mix_step - 1]) + 26 + 18 * k}" fill="{aa.INK if k == 3 else aa.MUTED}" '
                      f'font-size="13" font-family="{aa.SANS}" text-anchor="middle">{line}</text>')
    # the one callout comes in with the focal bar, and the note that the parts add up with the last total
    focal_step = 1 + [b[4] for b in bars].index(True)
    put(focal_step, f'<text x="40" y="{BASE + 96}" fill="{aa.MUTED}" font-size="8" font-weight="500" font-family="{aa.MONO}" letter-spacing="0.18em">FOCAL BAR</text>')
    put(focal_step, f'<text x="144" y="{BASE + 96}" fill="{aa.INK}" font-size="14" font-style="italic" font-family="{aa.SANS}">'
                    f'The made-up seat shares would have predicted {money(fair)}, so the drop is not about seats.</text>')
    put(len(bars), aa.icon("databricks", 144, BASE + 110, 16))
    put(len(bars), f'<text x="168" y="{BASE + 123}" fill="{aa.MUTED}" font-size="12" font-family="{aa.MONO}">volume + mix + share = {money(delta)}, the whole change, exactly · ops.decomposition</text>')
    # legend strip: the first three keys never move, and the focal key, which names AA's share, comes in with its bar
    ky = BASE + 174  # the keys' baseline
    assert ky + aa.TEXT_DESCENT * 11 <= aa.STAGE_BOTTOM, "the legend runs under the deck's footer"
    legend = [f'<line x1="40" y1="{BASE + 144}" x2="1240" y2="{BASE + 144}" stroke="{aa.RULE}" stroke-width="0.8"/>',
              f'<text x="40" y="{ky}" fill="{aa.MUTED}" font-size="8" font-weight="500" font-family="{aa.MONO}" letter-spacing="0.18em">LEGEND</text>']
    keys = [(INK_A(0.08), aa.INK, "Total"), (MUTED_TINT, aa.MUTED, "Increase"), ("#ffffff", aa.MUTED, "Decrease"), (FOCAL_TINT, aa.ACCENT, "Focal: AA's share")]
    for i, (fill, stroke, text) in enumerate(keys):
        kx = 144 + i * 200
        key = [f'<rect x="{kx}" y="{ky - 12}" width="20" height="14" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
               f'<text x="{kx + 28}" y="{ky}" fill="{aa.INK}" font-size="11" font-family="{aa.SANS}">{text}</text>']
        if stroke == aa.ACCENT:
            for markup in key:
                put(focal_step, markup)
        else:
            legend += key
    if motion:
        up = lambda v: "added" if v > 0 else "took off"  # noqa: E731
        words = [f"September 2025: Harbor's AA revenue is ${start:.1f}K",
                 f"Volume: Harbor sold more travel, which {up(d_vol)} ${abs(d_vol):.1f}K",
                 f"Shift between routes: Harbor sold more on some routes and less on others, which at last year's AA share on each route "
                 f"{up(d_mix)} ${abs(d_mix):.1f}K, so for Harbor it barely moved",
                 f"Share: AA's share fell, which {up(d_share)} ${abs(d_share):.1f}K",
                 f"September 2026: Harbor's AA revenue is ${end:.1f}K"]
        assert len(words) == len(bars) and {n for n, _ in parts} == set(range(1, len(bars) + 1))
        out += [aa.motion_item(n, w, [m for step, m in parts if step == n]) for n, w in enumerate(words, 1)]
    else:
        out += [m for _, m in parts]
    return "\n        ".join(out + legend)


TITLE = "Why a number moved"
EYEBROW = "fairshare · the data"
DESC = ("Waterfall of Harbor Business Travel's AA revenue from September 2025 to September 2026: more travel added revenue, "
        "the shift between routes, selling more on some and less on others, barely moved it, and AA's share inside its routes fell, "
        "which is the focal bar.")

if __name__ == "__main__":
    html = aa.page(slug="08-why-it-moved", title=TITLE, desc=DESC, eyebrow=EYEBROW, body=build())
    (aa.OUT / "08-why-it-moved.html").write_text(html, encoding="utf-8")
    html = aa.animated(slug="08-why-it-moved-animated", title=TITLE, desc=DESC, eyebrow=EYEBROW, body=build(True), steps=5, css=aa.FADE_ONLY)  # one step per bar
    (aa.OUT / "08-why-it-moved-animated.html").write_text(html, encoding="utf-8")
    print("wrote 08-why-it-moved.html and 08-why-it-moved-animated.html")

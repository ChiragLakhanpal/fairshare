"""02: how an answer gets checked, as a service blueprint. What the account manager does and sees sits above the line
of visibility; the work that stays hidden sits below it. The one focal cell is the verifier. A platform mark in a cell's
corner says where that work runs.

    python3 docs/diagrams/src/blueprint.py   # writes docs/diagrams/02-answer-checked.html and 02-answer-checked-animated.html

The data-* contract is diagram-design's; scripts/verify-service-blueprint.py in the plugin reads it back. The animated page steps
one layer at a time: the stage headers, the lane labels, the three lines and the legend stay put, and each row of cells comes in as
one group. The caption and the legend entry that name the verifier give the point away, so they come in with its row.
"""
from __future__ import annotations

import aa

VW, VH = 1280, 720
LEFT, COL, GUT = 112, 212, 16           # plot starts after the layer labels; five equal columns
ROW = 80                                # one row of cells
X = [LEFT + i * (COL + GUT) for i in range(5)]
RIGHT = X[-1] + COL
MARK = 16                               # platform mark, top-right corner of a cell

STAGES = [("ask", "Ask"), ("look-up", "Look up"), ("write", "Write"), ("check", "Check"), ("show", "Show")]

# (layer, printed label lines, row top, cells): a cell is (name, real name or None, platform marks)
DBX, AZ = "databricks", "azure"
ROWS = [
    ("customer", ("ACCOUNT", "MANAGER"), 128, [
        ("Asks a question", None, ()), ("Watches the steps", None, ()), ("Keeps waiting", None, ()),
        ("Sees nothing yet", None, ()), ("Clicks a number", None, ())]),
    ("frontstage", ("THE APP",), 216, [
        ("Suggested questions", None, ()), ("Progress steps", None, ()), ("Steps keep moving", None, ()),
        ("Answer held back", None, ()), ("Answer with its query", None, ())]),
    ("backstage", ("BEHIND THE", "SCREEN"), 304, [
        ("Router picks tools", None, ()), ("Genie runs the query", "fairshare sales metrics", (DBX,)),
        ("Model writes from rows", None, (DBX, AZ)), ("Unproven sentences cut", "verifier", ()),
        ("Trace on laptop runs", "MLflow fairshare", (DBX,))]),
    ("support", ("FOUNDATIONS",), 392, [
        ("Runs as the viewer", "Unity Catalog aa_demo", (DBX,)), ("Defined once", "gold.sales_metrics", (DBX,)),
        ("Clauses cite the page", None, ()), ("Numbers only from tools", None, ()), ("Tested on 20 questions", None, ())]),
]
FOCAL = ("backstage", "check")
LINES = [("interaction", 212, "rgba(54,73,90,0.18)", 1), ("visibility", 300, "rgba(54,73,90,0.65)", 2),
         ("internal-interaction", 388, "rgba(54,73,90,0.18)", 1)]
HIDDEN_FILL, HIDDEN_STROKE = "rgba(54,73,90,0.06)", aa.MUTED
CAPTION = ("FOCAL CELL", "A sentence whose number no query returned is cut from the answer, and the app shows what it cut.")
# the motion steps, one per layer from the top row down; the verifier's caption comes in with the backstage row it explains
STEPS = ["The account manager asks, watches, waits, then clicks a number",
         "The app shows its steps and holds the answer back, then shows it with its query",
         "Behind the screen, the verifier cuts any sentence whose number no query returned",
         "The foundations under every step: access, definitions, clauses, tools and tests"]


def text(x, y, s, *, size, fill, family, weight=None, anchor="middle", spacing=None, italic=False):
    attrs = [f'x="{x}"', f'y="{y}"', f'fill="{fill}"', f'font-size="{size}"', f'font-family="{family}"', f'text-anchor="{anchor}"']
    if weight:
        attrs.append(f'font-weight="{weight}"')
    if spacing:
        attrs.append(f'letter-spacing="{spacing}"')
    if italic:
        attrs.append('font-style="italic"')
    return f'<text {" ".join(attrs)}>{aa.esc(s)}</text>'


def cell(layer, stage, x, y, name, real, marks, focal):
    hidden = layer in ("backstage", "support")
    cx = x + COL // 2
    out = []
    if focal:
        out.append(f'<rect x="{x}" y="{y}" width="{COL}" height="{ROW}" rx="4" fill="{aa.ACCENT_TINT}" stroke="{aa.ACCENT}" stroke-width="1" '
                   f'data-stage="{stage}" data-name="{aa.esc(name)}" data-focal="true"/>')
    elif hidden:
        out.append(f'<rect x="{x}" y="{y}" width="{COL}" height="{ROW}" rx="4" fill="{HIDDEN_FILL}" stroke="{HIDDEN_STROKE}" stroke-width="1" '
                   f'data-stage="{stage}" data-name="{aa.esc(name)}"/>')
    else:
        out.append(f'<rect x="{x}" y="{y}" width="{COL}" height="{ROW}" rx="4" fill="#ffffff"/>')
        out.append(f'<rect x="{x}" y="{y}" width="{COL}" height="{ROW}" rx="4" fill="#ffffff" stroke="{aa.INK}" stroke-width="1" '
                   f'data-stage="{stage}" data-name="{aa.esc(name)}"/>')
    for k, m in enumerate(marks):  # right to left from the top-right corner
        out.append(aa.icon(m, x + COL - 8 - MARK - k * (MARK + 6), y + 8, MARK))
    fill = aa.ACCENT if focal else aa.INK
    if real:
        out.append(text(cx, y + 42, name, size=16, fill=fill, family=aa.SANS, weight=600))
        out.append(text(cx, y + 62, real, size=12, fill=aa.SOFT if focal else aa.MUTED, family=aa.MONO))
    else:
        out.append(text(cx, y + 48, name, size=16, fill=fill, family=aa.SANS, weight=600))
    return out


def body(motion=False):
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(),
           # the hidden-work band behind the backstage and support rows
           f'<rect x="{LEFT}" y="304" width="{RIGHT - LEFT}" height="168" fill="rgba(54,73,90,0.03)"/>']
    for i, ((sid, sname), x) in enumerate(zip(STAGES, X)):
        out.append(f'<rect x="{x}" y="72" width="{COL}" height="40" fill="none" data-stage="{sid}"/>')
        out.append(text(x + COL // 2, 86, f"STEP {i + 1}", size=8, fill=aa.MUTED, family=aa.MONO, spacing="0.14em"))
        out.append(text(x + COL // 2, 108, sname, size=16, fill=aa.INK, family=aa.SANS, weight=600))
    for role, y, stroke, w in LINES:
        out.append(f'<line x1="{LEFT}" y1="{y}" x2="{RIGHT}" y2="{y}" stroke="{stroke}" stroke-width="{w}" data-role="{role}"/>')
    caption = [text(LEFT, 532, CAPTION[0], size=8, fill=aa.MUTED, family=aa.MONO, anchor="start", spacing="0.18em"),
               text(LEFT + 104, 532, CAPTION[1], size=14, fill=aa.INK, family=aa.SANS, anchor="start", italic=True)]
    # the legend's last entry, since it names the verifier and so waits for the verifier's row
    focal_key = [f'<rect x="872" y="619" width="16" height="10" rx="2" fill="{aa.ACCENT_TINT}" stroke="{aa.ACCENT}" stroke-width="1"/>',
                 text(896, 628, "Focal: the verifier", size=11, fill=aa.MUTED, family=aa.SANS, anchor="start")]
    assert len(STEPS) == len(ROWS)
    for n, (layer, label, top, cells) in enumerate(ROWS):
        mid = top + ROW // 2
        for k, line in enumerate(label):  # the lane's label is a row heading, so it shows on arrival, outside the row's step
            y = mid + 3 + (k - (len(label) - 1) / 2) * 12
            out.append(text(LEFT - 8, int(y), line, size=8, fill=aa.MUTED, family=aa.MONO, anchor="end", spacing="0.12em"))
        row = [f'<g data-layer="{layer}">']
        for (sid, _), x, (name, real, marks) in zip(STAGES, X, cells):
            row += cell(layer, sid, x, top, name, real, marks, (layer, sid) == FOCAL)
        row.append("</g>")
        if motion:
            out.append(aa.motion_item(n + 1, STEPS[n], row + (caption + focal_key if layer == FOCAL[0] else [])))
        else:
            out += row
    if not motion:
        out += caption
    # legend strip: the bottom of the frame, after a hairline
    out.append(f'<line x1="{LEFT}" y1="596" x2="{RIGHT}" y2="596" stroke="rgba(54,73,90,0.10)" stroke-width="0.8"/>')
    out.append(text(LEFT, 628, "LEGEND", size=8, fill=aa.MUTED, family=aa.MONO, anchor="start", spacing="0.14em"))
    out.append(f'<line x1="216" y1="624" x2="244" y2="624" stroke="rgba(54,73,90,0.65)" stroke-width="2"/>')
    out.append(text(252, 628, "Line of visibility", size=11, fill=aa.MUTED, family=aa.SANS, anchor="start"))
    out.append(f'<rect x="384" y="619" width="16" height="10" rx="2" fill="{HIDDEN_FILL}" stroke="{HIDDEN_STROKE}" stroke-width="1"/>')
    out.append(text(408, 628, "Hidden work", size=11, fill=aa.MUTED, family=aa.SANS, anchor="start"))
    out.append(aa.icon(DBX, 528, 616, 14))
    out.append(text(548, 628, "Runs on Databricks", size=11, fill=aa.MUTED, family=aa.SANS, anchor="start"))
    out.append(aa.icon(AZ, 700, 616, 14))
    out.append(text(720, 628, "Runs on AI Foundry", size=11, fill=aa.MUTED, family=aa.SANS, anchor="start"))
    if not motion:
        out += focal_key
    return "\n        ".join(out)


TITLE = "How an answer gets checked"
EYEBROW = "fairshare · how an answer is checked"
DESC = ("Service blueprint of one question in five steps, with what the account manager does and sees above the line of "
        "visibility and the hidden lookup, writing and checking below it, marked by where each piece runs; the focal cell "
        "is the verifier cutting any sentence whose number no query returned.")

if __name__ == "__main__":
    html = aa.page(slug="02-answer-checked", title=TITLE, desc=DESC, eyebrow=EYEBROW, body=body(), vw=VW, vh=VH)
    (aa.OUT / "02-answer-checked.html").write_text(html, encoding="utf-8")
    html = aa.animated(slug="02-answer-checked-animated", title=TITLE, desc=DESC, eyebrow=EYEBROW, body=body(True), steps=len(STEPS),
                       css=aa.FADE_ONLY, vw=VW, vh=VH)
    (aa.OUT / "02-answer-checked-animated.html").write_text(html, encoding="utf-8")
    print("wrote 02-answer-checked.html and 02-answer-checked-animated.html")

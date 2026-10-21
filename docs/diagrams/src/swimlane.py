"""03: Delegate as a swimlane. The nightly job runs the agents, fixed queries pull the facts, a Foundry writer drafts from
those facts only, the verifier checks every number, and nothing reaches the CRM or Outlook until the account manager approves.

    python3 docs/diagrams/src/swimlane.py   # writes docs/diagrams/03-delegate.html and 03-delegate-animated.html

Coordinates are fixed on the 4px grid of the 1280 x 720 slide, everything under the AA logo band (y >= 72) and over the
deck's footer (aa.STAGE_BOTTOM); the plugin's verify-geometry.py checks the routing. Box widths come from measured text
(Inter 600 16px names, Geist Mono 12px lines). The animated page runs the flow in the order it happens, one stage a press,
each stage bringing its boxes with the arrows into them and their labels. The lanes, their names and the key to the marks
stay put. What gives the point away waits for its step: the key entries that name the handoff to a person and the person's
decision come in with them, and the caption comes in last.
"""
from __future__ import annotations

import aa

SLUG = "03-delegate"
TITLE = "Agents draft, people decide"
EYEBROW = "fairshare · delegate"
DESC = ("Swimlane of Delegate. The nightly Databricks job runs four agents, the runtime pulls the facts with fixed SQL, a writer "
        "agent in Azure AI Foundry drafts the page from those facts only, the verifier checks every number, and the page waits "
        "until an account manager approves, which logs the activity in a made-up CRM shaped like Dynamics 365 Sales and opens "
        "an Outlook draft.")

LEFT, RIGHT, ACTOR_X, NODE_X0 = 40, 1240, 216, 240
CAPTION_Y, RULE_Y, LEGEND_Y = 628, 644, 668  # the caption row, the hairline over the key, and the key, all over the deck's footer

# Tabler Icons `user` (MIT), from diagram-design's references/primitive-icons.md, stroked in ink
USER = ('<svg x="{x}" y="{y}" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="' + aa.INK + '" stroke-width="1.75" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0"/>'
        '<path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"/></svg>')

# lanes, top to bottom: (key, marks, short name, top, bottom); a mark says where the step runs, the name says who does it
LANES = [
    ("job", ("databricks",), "Nightly job", 72, 168),
    ("runtime", ("databricks",), "Agent runtime", 168, 272),
    ("foundry", ("azure",), "AI Foundry", 272, 380),
    ("manager", ("user",), "Account manager", 380, 476),
    ("crm", ("dynamics365", "outlook"), "CRM + mail", 476, 600),
]

# the steps of the flow in the order it runs: key -> (x, y, w, h, name, one mono line or None)
NODES = {
    "job": (240, 88, 200, 64, "Runs the four agents", "fairshare nightly · 6 am"),
    "queries": (240, 188, 200, 64, "Pulls the facts", "fixed SQL"),
    "writer": (320, 296, 256, 64, "Drafts the page", "fairshare-precall-pack + 3 more"),
    "verifier": (520, 188, 200, 64, "Checks every number", "verifier"),
    "waits": (768, 188, 200, 64, "Waits for a decision", "ops.agent_runs"),
    "review": (768, 396, 200, 64, "Reviews the page", None),
    "decide": (1016, 396, 200, 64, "Approves or rejects", None),
    "crm": (1016, 520, 200, 64, "Logs the activity", "Dynamics 365 (stand-in)"),
    "mail": (768, 520, 200, 64, "Opens the email draft", "Outlook"),
}
FOCAL = "decide"

# the arrow into every step but the first, keyed by the step it points to: (from, path d, stroke, marker, width, dash); straight
# runs share an x or a y, every bend is an r=8 quarter arc
MUTED, LINK, ACC = (aa.MUTED, "arrow", 1.2), (aa.NAVY, "arrow-link", 1.2), (aa.ACCENT, "arrow-accent", 1.4)
CONNECTORS = {
    "queries": ("job", "M 340 152 V 188", *MUTED, None),
    "writer": ("queries", "M 380 252 V 296", *LINK, None),                                                # a request out to Foundry
    "verifier": ("writer", "M 576 328 H 632 Q 640 328 640 320 V 252", *LINK, "5,4"),                    # the draft comes back
    "waits": ("verifier", "M 720 220 H 768", *MUTED, None),
    "review": ("waits", "M 868 252 V 396", *ACC, None),                                                   # the handoff to a person
    "decide": ("review", "M 968 428 H 1016", *MUTED, None),
    "crm": ("decide", "M 1116 460 V 520", *LINK, None),
    "mail": ("decide", "M 1040 460 V 480 Q 1040 488 1032 488 H 960 Q 952 488 952 496 V 520", *LINK, None),
}

# arrow labels, keyed like their arrows: (text, mask x, mask y, color); each mask sits 8px beside its vertical segment, centered on it
LABELS = {
    "writer": ("FACTS ONLY", 388, 267, aa.NAVY),     # beside x=380, segment 252..296
    "verifier": ("DRAFT", 648, 279, aa.NAVY),        # beside x=640, segment 252..320
    "review": ("TO A PERSON", 876, 317, aa.ACCENT),  # beside x=868, segment 252..396
    "crm": ("APPROVED", 1124, 483, aa.NAVY),         # beside x=1116, segment 460..520
}
MONO_ADVANCE = 0.62 + 0.06  # em per character at 0.06em tracking, the style guide's mono budget

# the motion steps, one stage of the flow a press: what the controller announces, and the steps each one brings in
STEPS = [
    ("Every night at 6 am the job runs the four agents", ["job"]),
    ("The agent runtime pulls the facts with fixed SQL", ["queries"]),
    ("A writer agent in AI Foundry drafts the page from those facts only", ["writer"]),
    ("The verifier checks every number in the draft, and the page waits in ops.agent_runs for a decision", ["verifier", "waits"]),
    ("The page goes to the account manager, who reviews it and approves or rejects it", ["review", "decide"]),
    ("The approval logs the activity in the CRM stand-in and opens the email draft in Outlook. Nothing reaches the CRM or Outlook "
     "until a person approves", ["crm", "mail"]),
]
CAPTION = ("FOCAL STEP", "Nothing reaches the CRM or Outlook until a person approves.")

# the key to the marks, in reading order: (kind, look, words, the step it waits for on the animated page or None). The last two
# name the handoff to a person and the person's decision, which give the point away, so they come in with that arrow and that box
LEGEND = [
    ("box", (aa.PAPER, aa.INK), "Step", None),
    ("line", (aa.MUTED, "arrow", None), "Next step", None),
    ("line", (aa.NAVY, "arrow-link", None), "Request", None),
    ("line", (aa.NAVY, "arrow-link", "5,4"), "Reply", None),
    ("line", (aa.ACCENT, "arrow-accent", None), "Handoff to a person", "review"),
    ("box", (aa.ACCENT_TINT, aa.ACCENT), "A person decides", FOCAL),
]


def defs() -> str:
    marker = '<marker id="{id}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{c}"/></marker>'
    return ("<defs>" + "".join(marker.format(id=i, c=c) for i, c in (("arrow", aa.MUTED), ("arrow-accent", aa.ACCENT), ("arrow-link", aa.NAVY)))
            + "</defs>")


def lanes() -> str:
    """The lanes with their rules, marks and names, in one group: the figure's structure."""
    edges = sorted({top for *_, top, _ in LANES} | {LANES[-1][4]})
    out = [f'<line x1="{ACTOR_X}" y1="{edges[0]}" x2="{ACTOR_X}" y2="{edges[-1]}" stroke="{aa.RULE}" stroke-width="1"/>']
    for y in edges:
        strong = y in (edges[0], edges[-1])
        out.append(f'<line x1="{LEFT}" y1="{y}" x2="{RIGHT}" y2="{y}" stroke="{aa.RULE_SOLID if strong else aa.RULE}" stroke-width="1"/>')
    for key, marks, name, top, bottom in LANES:
        mid = (top + bottom) / 2
        x, lane = 48, []
        for m in marks:
            lane.append(USER.format(x=x, y=mid - 11) if m == "user" else aa.icon(m, x, mid - 11, 22))
            x += 28
        lane.append(f'<text x="{x + 2}" y="{mid + 5:g}" fill="{aa.INK}" font-size="14" font-weight="600" font-family="{aa.SANS}">{aa.esc(name)}</text>')
        out.append(f'<g data-lane="{key}">' + "".join(lane) + "</g>")
    return '<g data-role="lanes">\n          ' + "\n          ".join(out) + "\n        </g>"


def connector(key: str) -> str:
    _, d, color, marker, width, dash = CONNECTORS[key]
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash_attr} marker-end="url(#{marker})" data-to="{key}"/>'


def label(key: str) -> list[str]:
    text, x, y, color = LABELS[key]
    w = round((len(text) * MONO_ADVANCE * 12 + 8) / 4) * 4
    return [f'<rect x="{x}" y="{y}" width="{w}" height="14" rx="2" fill="{aa.PAPER}"/>',
            f'<text x="{x + w / 2:g}" y="{y + 11}" fill="{color}" font-size="12" font-family="{aa.MONO}" text-anchor="middle" '
            f'letter-spacing="0.06em" data-to="{key}">{text}</text>']


def node(key: str) -> str:
    x, y, w, h, name, sub = NODES[key]
    fill, stroke = (aa.ACCENT_TINT, aa.ACCENT) if key == FOCAL else (aa.PAPER, aa.INK)
    cx = x + w / 2
    name_y = y + (h / 2 - 4 if sub else h / 2 + 6)  # one line centers on the box; two lines share it
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{aa.PAPER}"/>',
             f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
             f'<text x="{cx:g}" y="{name_y:g}" fill="{aa.INK}" font-size="16" font-weight="600" font-family="{aa.SANS}" text-anchor="middle">{aa.esc(name)}</text>']
    if sub:
        parts.append(f'<text x="{cx:g}" y="{name_y + 19:g}" fill="{aa.MUTED}" font-size="12" font-family="{aa.MONO}" text-anchor="middle">{aa.esc(sub)}</text>')
    focal = ' data-focal="true"' if key == FOCAL else ""
    return f'<g data-node="{key}"{focal}>' + "".join(parts) + "</g>"


def caption() -> list[str]:
    eyebrow, line = CAPTION
    return [f'<text x="48" y="{CAPTION_Y}" fill="{aa.MUTED}" font-size="8" font-family="{aa.MONO}" letter-spacing="0.18em">{eyebrow}</text>',
            f'<text x="{NODE_X0}" y="{CAPTION_Y}" fill="{aa.INK}" font-size="16" font-family="{aa.SANS}">{aa.esc(line)}</text>']


def legend() -> tuple[list[str], dict[str, list[str]]]:
    """The key under the caption: the marks that show on arrival, and the entries that wait, by the step they wait for."""
    y, x = LEGEND_Y, NODE_X0
    shown = [f'<line x1="{LEFT}" y1="{RULE_Y}" x2="{RIGHT}" y2="{RULE_Y}" stroke="{aa.RULE}" stroke-width="0.8"/>',
             f'<text x="48" y="{y}" fill="{aa.MUTED}" font-size="8" font-family="{aa.MONO}" letter-spacing="0.18em">LEGEND</text>']
    waiting: dict[str, list[str]] = {}
    for kind, look, text, waits in LEGEND:
        if kind == "box":
            fill, stroke = look
            swatch = f'<rect x="{x}" y="{y - 10}" width="16" height="12" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            tx = x + 24
        else:
            color, marker, dash = look
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            width = 1.4 if marker == "arrow-accent" else 1.2
            swatch = f'<line x1="{x}" y1="{y - 4}" x2="{x + 28}" y2="{y - 4}" stroke="{color}" stroke-width="{width}"{dash_attr} marker-end="url(#{marker})"/>'
            tx = x + 36
        entry = [swatch, f'<text x="{tx}" y="{y}" fill="{aa.MUTED}" font-size="11" font-family="{aa.SANS}">{aa.esc(text)}</text>']
        if waits:
            waiting.setdefault(waits, []).extend(entry)
        else:
            shown += entry
        x = tx + round(len(text) * 0.6 * 11 / 4) * 4 + 40
    assert x - 40 <= RIGHT, f"legend runs past the margin: {x - 40}"
    return shown, waiting


def check():
    """The layout promises this diagram makes; cheap to re-run after any edit."""
    for key, (x, y, w, h, *_rest) in NODES.items():
        assert all(v % 4 == 0 for v in (x, y, w, h)), f"{key} off the 4px grid"
        assert NODE_X0 <= x and x + w <= RIGHT and y >= 72, f"{key} outside the lane area"
        assert [l for l in LANES if l[3] <= y and y + h <= l[4]], f"{key} crosses a lane border"
    keys = list(NODES)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ax, ay, aw, ah = NODES[a][:4]
            bx, by, bw, bh = NODES[b][:4]
            assert ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay, f"{a} overlaps {b}"
    assert len(NODES) <= 9 and len(CONNECTORS) <= 12 and len(LANES) <= 5 and LANES[0][3] >= 72
    # the motion: every step of the flow in exactly one press, inside the plugin's budget, and no arrow from a step still to come
    order = [k for _, ks in STEPS for k in ks]
    assert sorted(order) == sorted(NODES) and len(order) == len(NODES), "every step of the flow comes in once"
    assert len(STEPS) <= 8, "the plugin's motion budget: at most eight steps"
    press = {k: n for n, (_, ks) in enumerate(STEPS) for k in ks}
    assert set(CONNECTORS) == set(NODES) - {order[0]} and set(LABELS) <= set(CONNECTORS), "an arrow into every step but the first"
    assert all(press[src] <= press[dst] for dst, (src, *_rest) in CONNECTORS.items()), "the flow comes in the order it runs"
    assert {k for *_, k in LEGEND if k} <= set(NODES), "a key entry waits for a step of the flow"
    # the caption and the key sit under the lanes and over the deck's footer: a text's box runs 1em over its baseline, TEXT_DESCENT under
    assert LANES[-1][4] < CAPTION_Y - 16 and CAPTION_Y + aa.TEXT_DESCENT * 16 < RULE_Y < LEGEND_Y - 11, "caption, hairline and key, in that order"
    assert LEGEND_Y + aa.TEXT_DESCENT * 11 <= aa.STAGE_BOTTOM, "the key stays over the deck's footer"


def build(motion: bool = False) -> str:
    """The figure's marks. On the animated page the flow comes in one stage a press: each step brings its arrows, their labels and its
    boxes, in the plugin's paint order, with the key entries that wait for it; the last one also brings the caption."""
    check()
    body = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', defs(), aa.brand(), lanes()]
    shown, waiting = legend()
    if not motion:
        body += [connector(k) for k in CONNECTORS] + [m for k in LABELS for m in label(k)] + [node(k) for k in NODES]
        body += caption() + shown + [m for _, ks in STEPS for k in ks for m in waiting.get(k, [])]
        return "\n        ".join(body)
    body += shown
    for n, (say, keys) in enumerate(STEPS, 1):
        marks = [connector(k) for k in keys if k in CONNECTORS] + [m for k in keys if k in LABELS for m in label(k)] + [node(k) for k in keys]
        marks += [m for k in keys for m in waiting.get(k, [])] + (caption() if n == len(STEPS) else [])
        body.append(aa.motion_item(n, say, marks))
    return "\n        ".join(body)


if __name__ == "__main__":
    (aa.OUT / f"{SLUG}.html").write_text(aa.page(slug=SLUG, title=TITLE, desc=DESC, eyebrow=EYEBROW, body=build()), encoding="utf-8")
    html = aa.animated(slug=f"{SLUG}-animated", title=TITLE, desc=DESC, eyebrow=EYEBROW, body=build(True), steps=len(STEPS), css=aa.FADE_ONLY)
    (aa.OUT / f"{SLUG}-animated.html").write_text(html, encoding="utf-8")
    print(f"wrote {SLUG}.html and {SLUG}-animated.html")

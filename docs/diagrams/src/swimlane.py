"""03: Delegate as a swimlane. The nightly job runs the agents, a Foundry writer drafts from facts only, the verifier
checks every number, and nothing is logged or drafted until the account manager approves.

    python3 docs/diagrams/src/swimlane.py   # writes docs/diagrams/03-delegate.html

Coordinates are fixed on the 4px grid of the 1280 x 720 slide, everything under the AA logo band (y >= 72); the plugin's
verify-geometry.py checks the routing. Box widths come from measured text (Inter 600 16px names, Geist Mono 12px lines).
"""
from __future__ import annotations

import aa

SLUG = "03-delegate"
TITLE = "Agents draft, people decide"
EYEBROW = "fairshare · delegate"
DESC = ("Swimlane of Delegate: the nightly Databricks job runs four agents, the runtime pulls the facts, a writer agent in "
        "Azure AI Foundry drafts the page from those facts only, the verifier checks every number, and the page waits until "
        "an account manager approves, which logs the activity in Dynamics 365 and opens an Outlook draft.")

LEFT, RIGHT, ACTOR_X, NODE_X0 = 40, 1240, 216, 240

# Tabler Icons `user` (MIT), from diagram-design's references/primitive-icons.md, stroked in ink
USER = ('<svg x="{x}" y="{y}" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="' + aa.INK + '" stroke-width="1.75" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0"/>'
        '<path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"/></svg>')

# lanes, top to bottom: (marks, short name, top, bottom); a mark says where the step runs, the name says who does it
LANES = [
    (("databricks",), "Nightly job", 72, 168),
    (("databricks",), "Agent runtime", 168, 272),
    (("azure",), "AI Foundry", 272, 380),
    (("user",), "Account manager", 380, 476),
    (("dynamics365", "outlook"), "CRM + mail", 476, 600),
]

# nodes: key -> (x, y, w, h, name, one mono line of real names or None)
NODES = {
    "n1": (240, 88, 200, 64, "Runs the four agents", "fairshare nightly · 6 am"),
    "n2": (240, 188, 200, 64, "Pulls the facts", None),
    "n3": (320, 296, 256, 64, "Writes the page", "fairshare-precall-pack + 3 more"),
    "n4": (520, 188, 200, 64, "Checks every number", None),
    "n5": (768, 188, 200, 64, "Waits for a decision", "ops.agent_runs"),
    "n6": (768, 396, 200, 64, "Reviews the page", None),
    "n7": (1016, 396, 200, 64, "Approves or rejects", None),
    "n8": (1016, 520, 200, 64, "Logs the activity", "Dynamics 365 (stand-in)"),
    "n9": (768, 520, 200, 64, "Opens the email draft", "Outlook"),
}
FOCAL = "n7"

# connectors: (path d, stroke, marker, width, dash); straight runs share an x or a y, every bend is an r=8 quarter arc
MUTED, LINK, ACC = (aa.MUTED, "arrow", 1.2), (aa.NAVY, "arrow-link", 1.2), (aa.ACCENT, "arrow-accent", 1.4)
CONNECTORS = [
    ("M 340 152 V 188", *MUTED, None),                                                     # n1 -> n2
    ("M 380 252 V 296", *LINK, None),                                                      # n2 -> n3, a call out to Foundry
    ("M 576 328 H 632 Q 640 328 640 320 V 252", *LINK, "5,4"),                            # n3 -> n4, the draft comes back
    ("M 720 220 H 768", *MUTED, None),                                                     # n4 -> n5
    ("M 868 252 V 396", *ACC, None),                                                       # n5 -> n6, the handoff to a person
    ("M 968 428 H 1016", *MUTED, None),                                                    # n6 -> n7
    ("M 1116 460 V 520", *LINK, None),                                                     # n7 -> n8
    ("M 1040 460 V 480 Q 1040 488 1032 488 H 960 Q 952 488 952 496 V 520", *LINK, None),  # n7 -> n9
]

# arrow labels: (text, mask x, mask y, color); each mask sits 8px beside its vertical segment, centered on it
LABELS = [
    ("FACTS ONLY", 388, 267, aa.NAVY),    # beside x=380, segment 252..296
    ("DRAFT", 648, 279, aa.NAVY),         # beside x=640, segment 252..320
    ("TO A PERSON", 876, 317, aa.ACCENT), # beside x=868, segment 252..396
    ("APPROVED", 1124, 483, aa.NAVY),     # beside x=1116, segment 460..520
]
MONO_ADVANCE = 0.62 + 0.06  # em per character at 0.06em tracking, the style guide's mono budget


def defs() -> str:
    marker = '<marker id="{id}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{c}"/></marker>'
    return ("<defs>" + "".join(marker.format(id=i, c=c) for i, c in (("arrow", aa.MUTED), ("arrow-accent", aa.ACCENT), ("arrow-link", aa.NAVY)))
            + "</defs>")


def lanes() -> list[str]:
    edges = sorted({top for *_, top, _ in LANES} | {LANES[-1][3]})
    out = [f'<line x1="{ACTOR_X}" y1="{edges[0]}" x2="{ACTOR_X}" y2="{edges[-1]}" stroke="{aa.RULE}" stroke-width="1"/>']
    for y in edges:
        strong = y in (edges[0], edges[-1])
        out.append(f'<line x1="{LEFT}" y1="{y}" x2="{RIGHT}" y2="{y}" stroke="{aa.RULE_SOLID if strong else aa.RULE}" stroke-width="1"/>')
    for marks, name, top, bottom in LANES:
        mid = (top + bottom) / 2
        x = 48
        for m in marks:
            out.append(USER.format(x=x, y=mid - 11) if m == "user" else aa.icon(m, x, mid - 11, 22))
            x += 28
        out.append(f'<text x="{x + 2}" y="{mid + 5:g}" fill="{aa.INK}" font-size="14" font-weight="600" font-family="{aa.SANS}">{aa.esc(name)}</text>')
    return out


def connectors() -> list[str]:
    out = []
    for d, color, marker, width, dash in CONNECTORS:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash_attr} marker-end="url(#{marker})"/>')
    return out


def labels() -> list[str]:
    out = []
    for text, x, y, color in LABELS:
        w = round((len(text) * MONO_ADVANCE * 12 + 8) / 4) * 4
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="14" rx="2" fill="{aa.PAPER}"/>')
        out.append(f'<text x="{x + w / 2:g}" y="{y + 11}" fill="{color}" font-size="12" font-family="{aa.MONO}" text-anchor="middle" letter-spacing="0.06em">{text}</text>')
    return out


def nodes() -> list[str]:
    out = []
    for key, (x, y, w, h, name, sub) in NODES.items():
        fill, stroke = (aa.ACCENT_TINT, aa.ACCENT) if key == FOCAL else (aa.PAPER, aa.INK)
        cx = x + w / 2
        name_y = y + (h / 2 - 4 if sub else h / 2 + 6)  # one line centers on the box; two lines share it
        parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{aa.PAPER}"/>',
                 f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
                 f'<text x="{cx:g}" y="{name_y:g}" fill="{aa.INK}" font-size="16" font-weight="600" font-family="{aa.SANS}" text-anchor="middle">{aa.esc(name)}</text>']
        if sub:
            parts.append(f'<text x="{cx:g}" y="{name_y + 19:g}" fill="{aa.MUTED}" font-size="12" font-family="{aa.MONO}" text-anchor="middle">{aa.esc(sub)}</text>')
        out.append(f'<g data-node="{key}">' + "".join(parts) + "</g>")
    return out


def caption() -> list[str]:
    return [f'<text x="48" y="632" fill="{aa.MUTED}" font-size="8" font-family="{aa.MONO}" letter-spacing="0.18em">FOCAL STEP</text>',
            f'<text x="{NODE_X0}" y="632" fill="{aa.INK}" font-size="14" font-style="italic" font-family="{aa.SANS}">'
            'Nothing is logged or sent until a person approves.</text>']


def legend() -> list[str]:
    y = 688
    out = [f'<line x1="{LEFT}" y1="656" x2="{RIGHT}" y2="656" stroke="{aa.RULE}" stroke-width="0.8"/>',
           f'<text x="48" y="{y}" fill="{aa.MUTED}" font-size="8" font-family="{aa.MONO}" letter-spacing="0.18em">LEGEND</text>']
    x = NODE_X0
    items = [("box", aa.PAPER, aa.INK, "Step"), ("box", aa.ACCENT_TINT, aa.ACCENT, "A person decides"),
             ("line", aa.MUTED, "arrow", "Next step", None), ("line", aa.NAVY, "arrow-link", "Call out", None),
             ("line", aa.NAVY, "arrow-link", "Reply", "5,4"), ("line", aa.ACCENT, "arrow-accent", "Handoff to a person", None)]
    for item in items:
        if item[0] == "box":
            _, fill, stroke, text = item
            out.append(f'<rect x="{x}" y="{y - 10}" width="16" height="12" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
            tx = x + 24
        else:
            _, color, marker, text, dash = item
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            width = 1.4 if marker == "arrow-accent" else 1.2
            out.append(f'<line x1="{x}" y1="{y - 4}" x2="{x + 28}" y2="{y - 4}" stroke="{color}" stroke-width="{width}"{dash_attr} marker-end="url(#{marker})"/>')
            tx = x + 36
        out.append(f'<text x="{tx}" y="{y}" fill="{aa.MUTED}" font-size="11" font-family="{aa.SANS}">{aa.esc(text)}</text>')
        x = tx + round(len(text) * 0.6 * 11 / 4) * 4 + 40
    assert x - 40 <= RIGHT, f"legend runs past the margin: {x - 40}"
    return out


def check():
    """The layout promises this diagram makes; cheap to re-run after any edit."""
    for key, (x, y, w, h, *_rest) in NODES.items():
        assert all(v % 4 == 0 for v in (x, y, w, h)), f"{key} off the 4px grid"
        assert NODE_X0 <= x and x + w <= RIGHT and y >= 72, f"{key} outside the lane area"
        assert [l for l in LANES if l[2] <= y and y + h <= l[3]], f"{key} crosses a lane border"
    keys = list(NODES)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ax, ay, aw, ah = NODES[a][:4]
            bx, by, bw, bh = NODES[b][:4]
            assert ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay, f"{a} overlaps {b}"
    assert len(NODES) <= 9 and len(CONNECTORS) <= 12 and len(LANES) <= 5 and LANES[0][2] >= 72


def build() -> str:
    check()
    body = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', defs(), aa.brand()]
    body += lanes() + connectors() + labels() + nodes() + caption() + legend()
    return "\n        ".join(body)


if __name__ == "__main__":
    (aa.OUT / f"{SLUG}.html").write_text(aa.page(slug=SLUG, title=TITLE, desc=DESC, eyebrow=EYEBROW, body=build()), encoding="utf-8")
    print(f"wrote {SLUG}.html")

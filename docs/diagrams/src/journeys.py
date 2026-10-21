"""04 and 05: two journeys as sequence diagrams, step by step, for the two people the director cares about most.

    .venv/bin/python docs/diagrams/src/journeys.py   # writes 04-journey-sales-director.html and 05-journey-account-manager.html, each with an -animated.html twin

diagram-design's sequence grammar (references/type-sequence.md): actors in a row, dashed lifelines, time flows down,
calls solid with a filled head, replies dashed with a filled head, a one-way notice dashed with an open head, self
messages as U loops, at most one combined fragment, two accent elements. A label sits in one gap between two lifelines,
never over a third; builder asserts keep every label mask clear of every lifeline. The animated twins keep the actors, the lifelines and the
legend in place and bring in the messages a few at a time: each diagram's `groups` lists the motion steps, a label and the step indexes it shows.
The payoff, the italic line on the legend's right, gives the point away, so it comes in with the last step, and the legend key for the
accent, which names the check, comes in with the verifier's group, the first to hold an accent message.

The numbers on 04 come from src/deck_facts.py (Harbor Business Travel, Sep 2026 vs Sep 2025, ops.decomposition):
harbor_volume_usd, harbor_mix_usd and harbor_share_usd, shown in $ thousands to one decimal.
"""
from __future__ import annotations

import aa
from deck_facts import fact

VW, VH = 1280, 720
BOX_TOP, BOX_H = 72, 72
LOOP = 16  # a self message's U loop
LIFE_TOP = BOX_TOP + BOX_H
NOTE = "Today's process is how the role was described in round one."
EYEBROW = "fairshare · step by step"
NOTE_CSS = "    .note { margin-top: 1rem; font-size: 0.875rem; line-height: 1.5; color: var(--color-muted); }\n"

# Tabler generics from diagram-design's references/primitive-icons.md (MIT), stroked like the rest of the skill
TABLER = {
    "user": ["M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0", "M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"],
}

# a message label is a list of runs; a run in backticks is a real name, set in mono
M, S = "mono", "sans"


def runs(s: str):
    """'`ask_metrics`, as the viewer' -> [(mono, 'ask_metrics'), (sans, ', as the viewer')]"""
    parts = s.split("`")
    return [(M if i % 2 else S, p) for i, p in enumerate(parts) if p]


def kilo(key: str) -> str:
    """A Harbor part in $ thousands to one decimal, with its sign: 32836 is +32.8K."""
    return f"{fact(key) / 1000:+.1f}K"


def width(s: str) -> float:
    # ponytail: Inter 12 averages 6.2px a character (measured on these labels, it overestimates), Geist Mono is 7.2 exactly
    return sum(len(t) * (7.2 if k == M else 6.2) for k, t in runs(s))


DIAGRAMS = [
    dict(
        file="04-journey-sales-director.html", slug="04-journey-sales-director",
        title="Sales director: a question in the Monday meeting",
        tag="fairshare · synthetic data",  # it prints Harbor's numbers, so its logo band says the data is made up
        desc=("Sequence of one question from a sales director: the fairshare app asks Genie as the viewer, explains the change "
              "from ops.decomposition, has the model write from the rows only, and the verifier checks every number before "
              "the answer comes back with its query attached."),
        actors=[  # key, centre x, box width, icons, plain name, mono real names
            ("dir", 120, 160, ["user"], "Sales director", ["the viewer"]),
            ("app", 352, 200, ["databricks"], "fairshare app", ["Agent Framework harness"]),
            ("genie", 632, 216, ["databricks"], "Genie", ["fairshare sales metrics"]),
            ("sql", 912, 200, ["databricks"], "Databricks SQL", ["gold.sales_metrics"]),
            ("model", 1140, 200, ["databricks", "azure"], "Model", ["Qwen3-Next · gpt-5-mini"]),
        ],
        row=36,
        steps=[  # (kind, from, to, label, accent)
            ("call", "dir", "app", "Why is Harbor down in September?", False),
            ("call", "app", "genie", "`ask_metrics`, as the viewer", False),
            ("call", "genie", "sql", "`MEASURE()` on `gold.sales_metrics`", False),
            ("ret", "sql", "genie", "rows", False),
            ("ret", "genie", "app", "rows + the SQL", False),
            ("call", "app", "sql", "`explain_change` on `ops.decomposition`", False),
            ("ret", "sql", "app", f"volume {kilo('harbor_volume_usd')}, mix {kilo('harbor_mix_usd')}, share {kilo('harbor_share_usd')}", False),
            ("call", "app", "model", "write from these rows only", False),
            ("ret", "model", "app", "draft", False),
            ("self", "app", None, "verifier: every number vs. rows|unmatched sentence cut", True),
            ("ret", "app", "dir", "answer with its query attached", True),
            ("call", "dir", "app", f"clicks {kilo('harbor_share_usd')}: sees its rows", False),
        ],
        bars=[("app", 0, 10), ("genie", 1, 4), ("sql", 2, 3), ("sql", 5, 6), ("model", 7, 8)],
        groups=[  # (what the controller announces, the indexes in `steps` it brings in)
            ("The sales director asks why Harbor is down in September", [0]),
            ("The app asks Genie as the viewer, and Genie runs the query and sends back the rows and the SQL", [1, 2, 3, 4]),
            (f"The app runs explain_change on ops.decomposition and gets volume {kilo('harbor_volume_usd')}, "
             f"mix {kilo('harbor_mix_usd')} and share {kilo('harbor_share_usd')}", [5, 6]),
            ("The model writes a draft from those rows only", [7, 8]),
            ("The verifier checks every number against the rows and cuts any sentence that has no match", [9]),
            ("The answer goes back to the director with its query attached", [10]),
            (f"The director clicks {kilo('harbor_share_usd')} and sees its rows", [11]),
        ],
        legend=[("call", "Request"), ("ret", "Reply"), ("accent", "Checked, then answered")],
        payoff="Today the same question becomes a ticket to sales BI.",
    ),
    dict(
        file="05-journey-account-manager.html", slug="05-journey-account-manager",
        title="Account manager: Monday before agency calls",
        desc=("Sequence of Delegate's Monday pre-call pack: the nightly job asks the fairshare runtime for one page per agency, "
              "an AI Foundry writer drafts it from facts only, the verifier checks every number, and the page waits for the "
              "account manager, who approves it (the activity is logged and the email draft opens) or rejects it."),
        actors=[  # the writer sits left of the runtime so the ALT frame spans only runtime, account manager and CRM
            ("job", 132, 184, ["databricks"], "Nightly job", ["fairshare nightly, 6 am"]),
            ("writer", 380, 200, ["azure"], "AI Foundry writer", ["fairshare-precall-pack"]),
            ("rt", 624, 200, ["databricks"], "fairshare runtime", ["ops.agent_runs"]),
            ("am", 872, 184, ["user"], "Account manager", ["Delegate mode"]),
            ("crm", 1128, 224, ["dynamics365", "outlook"], "Dynamics 365 + Outlook", ["stand-in CRM"]),
        ],
        row=28,
        steps=[
            ("call", "job", "rt", "write one page per agency", False),
            ("self", "rt", None, "fixed SQL: numbers, why,|agreement, open deals", False),
            ("call", "rt", "writer", "facts only, no tools", False),
            ("ret", "writer", "rt", "`gpt-5-mini` drafts page + email", False),
            ("self", "rt", None, "verifier: every number|vs. rows", True),
            ("async", "rt", "am", "page waits; older version retired", False),
            ("call", "am", "rt", "opens Delegate, Monday", False),
            ("ret", "rt", "am", "numbers, why, cited clause, email", False),
            ("alt", ("rt", "crm"), None, "[approves]", False),
            ("call", "am", "rt", "approve (edits checked again)", True),
            ("call", "rt", "crm", "log activity `ops.crm_activities`", False),
            ("call", "rt", "crm", "open the draft; app sends nothing", False),
            ("else", None, None, "[rejects]", False),
            ("self", "rt", None, "page closed, nothing|logged or sent", False),
            ("end", None, None, "", False),
        ],
        bars=[("rt", 0, 5), ("writer", 2, 3), ("rt", 6, 13)],
        groups=[
            ("The nightly job asks the runtime to write one page per agency", [0]),
            ("The runtime pulls the numbers, the reasons, the agreement and the open deals with fixed SQL", [1]),
            ("The AI Foundry writer drafts the page and the email from facts only, with no tools", [2, 3]),
            ("The verifier checks every number against the rows", [4]),
            ("The page waits and the older version is retired. On Monday the account manager opens Delegate "
             "and sees the numbers, the reason, the cited clause and the email", [5, 6, 7]),
            ("If the account manager approves, the edits are checked again, the activity is logged and the email draft opens", [8, 9, 10, 11]),
            ("If the account manager rejects, the page is closed and nothing is logged or sent", [12, 13, 14]),
        ],
        legend=[("call", "Request"), ("ret", "Reply"), ("async", "Notice, no reply"), ("accent", "Checked, then approved")],
        payoff="Today the account manager builds this by hand before every call.",
    ),
]


def text(x, y, s, *, size, fill, family, weight=None, anchor="start", spacing=None, italic=False):
    w = f' font-weight="{weight}"' if weight else ""
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    it = ' font-style="italic"' if italic else ""
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-family="{family}"{w}{ls}{it} text-anchor="{anchor}">{aa.esc(s)}</text>'


def label(cx, y, s, color, *, anchor="middle"):
    """A message label on its paper mask; backticked runs are mono. Returns (markup, left, right)."""
    w = width(s)
    left = cx - w / 2 if anchor == "middle" else cx
    spans = "".join(f'<tspan font-family="{aa.MONO if k == M else aa.SANS}">{aa.esc(t)}</tspan>' for k, t in runs(s))
    mask = f'<rect x="{left - 4:.1f}" y="{y - 12}" width="{w + 8:.1f}" height="16" rx="2" fill="{aa.PAPER}"/>'
    tx = f'<text x="{cx}" y="{y}" fill="{color}" font-size="12" text-anchor="{anchor}">{spans}</text>'
    return mask + tx, left - 4, left + w + 4


def actor_box(cx, w, icons, name, subs):
    x, y = cx - w // 2, BOX_TOP
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{BOX_H}" rx="6" fill="#ffffff" stroke="{aa.INK}" stroke-width="1"/>']
    for k, ic in enumerate(icons):  # one or two marks, centred on the top row
        ix = cx - 12 * len(icons) - 4 * (len(icons) - 1) + k * 28
        if ic in aa.ICONS:
            out.append(aa.icon(ic, ix + 2, y + 8, 20, aa.INK))
        else:
            paths = "".join(f'<path d="{d}"/>' for d in TABLER[ic])
            out.append(f'<svg x="{ix + 2}" y="{y + 8}" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
                       f'stroke="{aa.INK}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')
    out.append(text(cx, y + 46, name, size=16, fill=aa.INK, family=aa.SANS, weight=600, anchor="middle"))
    for k, s in enumerate(subs):
        out.append(text(cx, y + 62 + 14 * k, s, size=12, fill=aa.MUTED, family=aa.MONO, anchor="middle"))
    return out


def build(d, motion=False) -> str:
    xs = {a[0]: a[1] for a in d["actors"]}
    lifelines = sorted(xs.values())
    row = d["row"]

    def gaps(a, b):
        """Where a label may sit: the gap next to the source, then the gap next to the target, never over a third lifeline."""
        out = []
        for end, other in ((a, b), (b, a)):
            i = lifelines.index(xs[end])
            nxt = lifelines[i + 1] if xs[other] > xs[end] else lifelines[i - 1]
            out.append((xs[end] + nxt) / 2)
        return out

    def clear(left, right):
        return not any(left - 6 < x < right + 6 for x in lifelines)

    # pass 1: y for every step
    y, ys, frame = LIFE_TOP + 12, [], None
    for i, (kind, a, b, s, hot) in enumerate(d["steps"]):
        if kind == "alt":  # the frame starts 8px under the last message; its guard sits under the tab
            frame = dict(top=y + 8, lanes=a, guards=[(y + 40, s)], who=set(), at=[i])  # guard 16px under the 16px tab
            y += 40
            ys.append(None)
            continue
        if kind == "else":  # divider 16px clear of the message above, the second guard 20px under it
            frame["divider"] = y + 16
            frame["guards"].append((y + 36, s))
            frame["at"].append(i)  # [alt step, else step]: the frame, tab and first guard belong to the first, the divider and second guard to the second
            y += 36
            ys.append(None)
            continue
        if kind == "end":
            frame["bottom"] = y + 12
            y += 12
            ys.append(None)
            continue
        if frame and "bottom" not in frame:
            frame["who"] |= {a, b} - {None}
        y += row
        ys.append(y)
        if kind == "self":
            y += LOOP
    life_bottom = y + 16
    assert life_bottom <= 644, f"{d['file']}: sequence runs to {life_bottom}"
    rule_y = life_bottom + 8  # the legend strip's rule; its keys and the payoff sit on one baseline under it
    assert rule_y + 20 + aa.TEXT_DESCENT * 14 <= aa.STAGE_BOTTOM, f"{d['file']}: the legend runs under the deck's footer"
    payoff = text(VW - 40, rule_y + 20, d["payoff"], size=14, fill=aa.INK, family=aa.SANS, anchor="end", italic=True)
    keys, lx = [], 40  # the legend's keys, left to right, each an arrow and its words
    for kind, words in d["legend"]:
        tone = aa.ACCENT if kind == "accent" else aa.MUTED
        head = "arrow-accent" if kind == "accent" else ("arrow-open" if kind == "async" else "arrow")
        dash = ' stroke-dasharray="5,4"' if kind in ("ret", "async") else ""
        keys.append((kind, [f'<line x1="{lx}" y1="{rule_y + 16}" x2="{lx + 28}" y2="{rule_y + 16}" stroke="{tone}" stroke-width="1.2"{dash} marker-end="url(#{head})"/>',
                            text(lx + 36, rule_y + 20, words, size=11, fill=aa.MUTED, family=aa.SANS)]))
        lx += 36 + len(words) * 6 + 32
    checked_key = [m for kind, key_marks in keys if kind == "accent" for m in key_marks]
    first_hot = next(i for i, (*_, hot) in enumerate(d["steps"]) if hot)
    checked_group = next(n for n, (_, idxs) in enumerate(d["groups"], 1) if first_hot in idxs)

    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag=d["tag"]) if "tag" in d else aa.brand()]
    out.append('<defs>'
               f'<marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{aa.MUTED}"/></marker>'
               f'<marker id="arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{aa.ACCENT}"/></marker>'
               f'<marker id="arrow-open" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polyline points="0 0, 8 3, 0 6" fill="none" stroke="{aa.MUTED}" stroke-width="1.2"/></marker>'
               '</defs>')
    for x in lifelines:
        out.append(f'<line x1="{x}" y1="{LIFE_TOP}" x2="{x}" y2="{life_bottom}" stroke="rgba(54,73,90,0.20)" stroke-width="1" stroke-dasharray="3,3"/>')

    # Every mark that belongs to one of the figure's steps is kept with that step's index, in paint order: the frame, the activation
    # bars, the message lines, then their labels. Static flattens them as they are; motion gathers each group's marks into one item.
    marks = {"frame": [], "bars": [], "lines": [], "labels": []}

    # the ALT frame paints before its messages
    if frame:
        lo, hi = sorted((xs[frame["lanes"][0]], xs[frame["lanes"][1]]))
        # the left inset holds the tab and the guards, so neither sits on the first lifeline or its activation bar
        inset = max(len(g) for _, g in frame["guards"]) * 7.2 + 12 + 16
        fx = int((lo - inset) // 4 * 4)  # on the 4px grid
        fw = hi + 28 - fx
        # the frame may only cover lifelines that have a message inside it (type-sequence.md anti-pattern)
        assert all(x in {xs[k] for k in frame["who"]} for x in lifelines if lo <= x <= hi), "frame covers an idle lifeline"
        alt_at, else_at = frame["at"]
        marks["frame"].append((alt_at, f'<rect x="{fx}" y="{frame["top"]}" width="{fw}" height="{frame["bottom"] - frame["top"]}" rx="4" fill="rgba(54,73,90,0.02)" stroke="rgba(54,73,90,0.22)" stroke-width="1"/>'))
        marks["frame"].append((alt_at, f'<rect x="{fx}" y="{frame["top"]}" width="40" height="16" rx="2" fill="{aa.PAPER}" stroke="rgba(54,73,90,0.22)" stroke-width="1"/>'))
        marks["frame"].append((alt_at, text(fx + 20, frame["top"] + 12, "ALT", size=8, fill=aa.MUTED, family=aa.MONO, anchor="middle", spacing="0.12em")))
        marks["frame"].append((else_at, f'<line x1="{fx + 8}" y1="{frame["divider"]}" x2="{fx + fw - 8}" y2="{frame["divider"]}" stroke="rgba(54,73,90,0.20)" stroke-width="1" stroke-dasharray="4,3"/>'))
        for at, (gy, g) in zip(frame["at"], frame["guards"]):
            marks["frame"].append((at, text(fx + 12, gy, g, size=12, fill=aa.MUTED, family=aa.MONO)))

    # activation bars, each with the step its first message sits in
    for who, i, j in d["bars"]:
        top, bottom = ys[i] - 4, (ys[j] + (LOOP if d["steps"][j][0] == "self" else 0)) + 4
        marks["bars"].append((i, f'<rect x="{xs[who] - 4}" y="{top}" width="8" height="{bottom - top}" fill="rgba(54,73,90,0.06)" stroke="{aa.MUTED}" stroke-width="0.8"/>'))

    # messages, then their labels
    labels = []
    for i, ((kind, a, b, s, hot), y) in enumerate(zip(d["steps"], ys)):
        if y is None:
            continue
        tone = aa.ACCENT if hot else aa.MUTED
        head = "arrow-accent" if hot else ("arrow-open" if kind == "async" else "arrow")
        if kind == "self":
            x = xs[a]
            marks["lines"].append((i, f'<path d="M {x + 4} {y} L {x + 36} {y} L {x + 36} {y + LOOP} L {x + 4} {y + LOOP}" fill="none" stroke="{tone}" '
                                      f'stroke-width="{1.4 if hot else 1.2}" marker-end="url(#{head})"/>'))
            lines = s.split("|")
            for k, ln in enumerate(lines):
                ly = y + (12 if len(lines) == 1 else -2 + 14 * k)  # two lines straddle the loop's top edge, clear of the next label
                markup, left, right = label(x + 48, ly, ln, tone, anchor="start")
                labels.append((i, markup, left, right))
            continue
        x1, x2 = xs[a], xs[b]
        sgn = 1 if x2 > x1 else -1
        dash = ' stroke-dasharray="5,4"' if kind in ("ret", "async") and not hot else ""  # the headline is solid
        marks["lines"].append((i, f'<line x1="{x1 + 4 * sgn}" y1="{y}" x2="{x2 - 4 * sgn}" y2="{y}" stroke="{tone}" stroke-width="{1.4 if hot else 1.2}"{dash} marker-end="url(#{head})"/>'))
        for cx in gaps(a, b):
            markup, left, right = label(cx, y - 10, s, tone)
            if clear(left, right):
                break
        labels.append((i, markup, left, right))
    for i, markup, left, right in labels:  # no label mask may sit over a lifeline
        assert not any(left - 6 < x < right + 6 for x in lifelines), f"{d['file']}: label over a lifeline: {markup[-80:]}"
        marks["labels"].append((i, markup))
    if motion:  # one item per group, its marks in the static paint order; every step lands in exactly one group, and the payoff with the last
        assert sorted(i for _, idxs in d["groups"] for i in idxs) == list(range(len(d["steps"]))), f"{d['file']}: groups must cover every step once"
        last = len(d["groups"])
        for n, (words, idxs) in enumerate(d["groups"], 1):
            shown = [m for part in marks.values() for i, m in part if i in idxs]
            shown += ([payoff] if n == last else []) + (checked_key if n == checked_group else [])
            out.append(aa.motion_item(n, f"{words}. {d['payoff']}" if n == last else words, shown))
    else:
        out += [m for part in marks.values() for _, m in part]

    # actor boxes paint last, over the lifeline tops
    for key, cx, w, icons, name, subs in d["actors"]:
        out += actor_box(cx, w, icons, name, subs)

    # legend strip, with the one italic line on its right; on the animated page the accent key and the payoff wait for their steps
    out.append(f'<line x1="40" y1="{rule_y}" x2="{VW - 40}" y2="{rule_y}" stroke="rgba(54,73,90,0.10)" stroke-width="0.8"/>')
    for kind, key_marks in keys:
        if kind != "accent" or not motion:
            out += key_marks
    if not motion:
        out.append(payoff)
    return "\n        ".join(out)


def add_note(html: str) -> str:
    """The one line under the figure: where the "today" line comes from."""
    return html.replace("      </svg>\n    </div>\n", f"      </svg>\n    </div>\n    <p class=\"note\">{aa.esc(NOTE)}</p>\n", 1)


def page(d) -> str:
    html = aa.page(slug=d["slug"], title=d["title"], desc=d["desc"], eyebrow=EYEBROW, body=build(d), vw=VW, vh=VH)
    return add_note(html.replace("  </style>", NOTE_CSS + "  </style>", 1))


def animated(d) -> str:
    """The same figure as a reveal page. The note stays, but the /present deck hides it with the rest of the page around the figure."""
    css = f"    {aa.FADE_ONLY}\n{NOTE_CSS}    html[data-embed] .note {{ display: none; }}\n"
    html = aa.animated(slug=d["slug"] + "-animated", title=d["title"], desc=d["desc"], eyebrow=EYEBROW, body=build(d, True),
                       steps=len(d["groups"]), css=css, vw=VW, vh=VH)
    return add_note(html)


if __name__ == "__main__":
    for d in DIAGRAMS:
        (aa.OUT / d["file"]).write_text(page(d), encoding="utf-8")
        twin = d["file"].replace(".html", "-animated.html")
        (aa.OUT / twin).write_text(animated(d), encoding="utf-8")
        print("wrote", d["file"], "and", twin)

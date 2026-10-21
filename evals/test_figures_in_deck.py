"""What the figures show inside the /present deck: nothing before its step, and nothing under the deck's frame.

The deck's frame covers y 0 to 64 of a figure's 1280 by 720 view box with its header and y 690 to 720 with its footer, so every figure the deck shows
keeps its marks between y 64 and y 680; the logo band at the top is hidden in the deck. In the deck's embed mode (aa.EMBED_CSS, baked into every
animated page when it is built) an item the controller has not reached shows nothing, and whatever gives a figure's point away (a legend entry that
names the focal item, a caption, a payoff line) comes in with the step that brings in its item. A figure's structure (its axes, headings, actors and
frame) shows on arrival, and a chart's lines draw then; its notes come one per press. An item marked data-recede leads in ink while it is the current
step and recedes to the muted text once a later one arrives (aa.EMBED_CSS again), so the newest note or card leads; a text in it marked data-keep (a
value drawn in the accent) keeps the color it is drawn in. These read the generated pages; rebuild them with the commands in docs/diagrams/README.md.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docs/diagrams/src"))
import aa  # noqa: E402
from aa import MUTED  # noqa: E402  the figures' muted text

DIAGRAMS = ROOT / "docs" / "diagrams"
FACTS = json.loads((ROOT / "web/src/deck/facts.json").read_text(encoding="utf-8"))["facts"]
ANIMATED = ["01-system-exploded", "02-answer-checked", "03-delegate", "04-journey-sales-director", "05-journey-account-manager",
            "06-data-pipeline", "08-why-it-moved", "09a-numbers-share", "09b-numbers-gaps", "11-revenue-by-month", "12-share-vs-fair", "15-at-aa"]
# every page the deck shows a figure from: the animated pages in their frames, and the static pages whose PNGs are the thumbs and the backup slides
SHOWN = [f"{n}-animated" for n in ANIMATED] + ANIMATED + ["07-fair-share", "14-what-was-planted"]
TOP, BOTTOM = 64, 680
# A text's box, as the browser measures it: from 1em over its baseline (Inter's ascent is 0.97em, Geist Mono's 1em) to 0.3em under it (Inter's
# descent is 0.24em, Geist Mono's 0.27em), so the rule holds in either face with a little to spare.
ASCENT, DESCENT = 1.0, 0.3


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids, self.text = tag, attrs, parent, [], ""

    def walk(self):
        yield self
        for k in self.kids:
            yield from k.walk()

    def words(self):
        """All the text under this node, as one string."""
        return "".join(n.text for n in self.walk())


class Tree(HTMLParser):
    """A page's figure (its first <svg>) as a tree of nodes. HTML lowercases attribute names, which none of these checks reads."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root, self.stack, self.done = None, [], False

    def handle_starttag(self, tag, attrs):
        if self.done or (self.root is None and tag != "svg"):
            return
        node = Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.stack[-1] if self.stack else None)
        if self.stack:
            self.stack[-1].kids.append(node)
        else:
            self.root = node
        self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1].tag == tag and not self.done:
            self.stack.pop()
            self.done = not self.stack and self.root is not None

    def handle_endtag(self, tag):
        while self.stack:
            if self.stack.pop().tag == tag:
                break
        self.done = self.done or (not self.stack and self.root is not None)

    def handle_data(self, data):
        if self.stack:
            self.stack[-1].text += data


def html(name):
    return (DIAGRAMS / f"{name}.html").read_text(encoding="utf-8")


def figure(name) -> Node:
    tree = Tree()
    tree.feed(html(name))
    assert tree.root is not None, f"{name} has no figure"
    return tree.root


# ---------------------------------------------------------------- where each mark sits

TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def path_ys(d: str) -> list[float]:
    """Every y a path passes through or bends toward: its points, its control points, and the ends of its arcs (a corner arc stays between them)."""
    toks, ys, x, y, sx, sy, cmd, i = TOKEN.findall(d), [], 0.0, 0.0, 0.0, 0.0, "M", 0
    while i < len(toks):
        if toks[i].isalpha():
            cmd, i = toks[i], i + 1
            if cmd in "Zz":
                x, y = sx, sy
                continue
        up, rel = cmd.upper(), cmd.islower()
        vals = [float(v) for v in toks[i:i + ARGS[up]]]
        i += ARGS[up]
        if up == "H":
            x = vals[0] + (x if rel else 0)
        elif up == "V":
            y = vals[0] + (y if rel else 0)
        elif up == "A":
            x, y = (x + vals[5], y + vals[6]) if rel else (vals[5], vals[6])
        else:  # the control points of a curve, then where it ends
            pts = [(px + (x if rel else 0), py + (y if rel else 0)) for px, py in zip(vals[0::2], vals[1::2])]
            ys += [py for _, py in pts[:-1]]
            x, y = pts[-1]
        ys.append(y)
        if up == "M":
            sx, sy, cmd = x, y, ("l" if rel else "L")  # the pairs after a move draw lines
    return ys


def extent(node: Node) -> tuple[float, float]:
    """How far up and down a mark reaches in the view box: a text by its font box, a shape by its geometry and half its stroke, a nested <svg>
    (an icon) by its box."""
    a = node.attrs
    n = lambda k: float(a.get(k, 0))  # noqa: E731
    half = float(a.get("stroke-width", 1)) / 2 if a.get("stroke", "none") != "none" else 0.0
    if node.tag == "text":
        size, y = float(a["font-size"]), float(a["y"])
        return y - ASCENT * size, y + DESCENT * size
    if node.tag in ("rect", "svg", "image", "use"):
        return n("y") - half, n("y") + n("height") + half
    if node.tag == "line":
        return min(n("y1"), n("y2")) - half, max(n("y1"), n("y2")) + half
    if node.tag == "circle":
        return n("cy") - n("r") - half, n("cy") + n("r") + half
    if node.tag == "ellipse":
        return n("cy") - n("ry") - half, n("cy") + n("ry") + half
    if node.tag in ("polyline", "polygon"):
        ys = [float(v) for v in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", a["points"])][1::2]
        return min(ys) - half, max(ys) + half
    if node.tag == "path":
        ys = path_ys(a["d"])
        return min(ys) - half, max(ys) + half
    raise AssertionError(f"no extent for <{node.tag}>")


QUIET = {"defs", "title", "desc", "style", "lineargradient", "radialgradient", "clippath", "mask", "marker", "filter"}


def marks(name) -> list[tuple[float, float, str]]:
    """Every mark a figure paints, with its extent: all but the logo band, the paper under the figure, defs, and the insides of its icons."""
    out = []

    def walk(node):
        for k in node.kids:
            if k.tag in QUIET or "data-brand" in k.attrs:
                continue
            if k.tag == "g":
                walk(k)
            elif k.tag == "rect" and "%" in k.attrs.get("width", "") + k.attrs.get("height", ""):
                continue  # the paper behind the whole figure
            else:
                top, bottom = extent(k)
                out.append((top, bottom, f"<{k.tag}> {k.words().strip()[:60]!r}" if k.tag == "text" else f"<{k.tag}>"))

    walk(figure(name))
    return out


def test_the_measure_reads_paths_and_text_boxes():
    assert path_ys("M 408,200 V 160 A 8 8 0 0 1 416,152 H 540 Z") == [200, 160, 152, 152]
    assert path_ys("M 10 20 l 5 5 5 5 c 0 10 0 10 0 0") == [20, 25, 30, 40, 40, 30]
    assert extent(Node("text", {"x": "0", "y": "680", "font-size": "14"}, None)) == (666, 684.2)


def test_the_builders_assert_the_same_stage():
    assert (aa.STAGE_TOP, aa.STAGE_BOTTOM, aa.TEXT_DESCENT) == (TOP, BOTTOM, DESCENT)


@pytest.mark.parametrize("name", SHOWN)
def test_a_figure_the_deck_shows_keeps_every_mark_between_its_header_and_footer(name):
    found = marks(name)
    assert len(found) > 20, f"{name}: the measure found almost nothing"
    bad = [f"{what} spans y {top:.1f} to {bottom:.1f}" for top, bottom, what in found if top < TOP or bottom > BOTTOM]
    assert not bad, f"{name} reaches under the deck's frame (y {TOP} to {BOTTOM} is the stage):\n" + "\n".join(bad)


# ---------------------------------------------------------------- what waits for its step

def step_of(node: Node):
    """The step of the motion item a node sits in, or None for a node that shows on arrival."""
    while node is not None:
        if "data-motion-item" in node.attrs:
            return int(node.attrs["data-step"])
        node = node.parent
    return None


def step_count(name) -> int:
    return int(re.search(r'data-motion-root[^>]*data-step-count="(\d+)"', html(name)).group(1))


def texts(root: Node, pattern: str) -> list[Node]:
    return [n for n in root.walk() if n.tag == "text" and re.search(pattern, n.words())]


def in_logo(node: Node) -> bool:
    while node is not None:
        if "data-brand" in node.attrs:
            return True
        node = node.parent
    return False


@pytest.mark.parametrize("name", [n for n in ANIMATED if n != "01-system-exploded"])
def test_a_figure_shows_some_structure_in_words_on_arrival(name):
    # 01 arrives as its assembled stack, which has no words; every other figure names what the room is looking at before the first press
    fig = figure(f"{name}-animated")
    shown = [n for n in fig.walk() if n.tag == "text" and step_of(n) is None and not in_logo(n)]
    assert shown, f"{name} arrives with every word held back for a step"


def test_06_shows_its_headings_and_tier_cards_on_arrival_and_keeps_each_number_for_its_step():
    fig = figure("06-data-pipeline-animated")
    for words in ("SOURCES", "READ BY", "As delivered", "bronze", "Cleaned", "silver", "Ready to use", "gold", "Defined once", "gold.sales_metrics"):
        found = texts(fig, rf"^{re.escape(words)}$")
        assert found and all(step_of(n) is None for n in found), f"{words!r} is structure, so it shows on arrival"
    cards = [n for n in fig.walk() if n.tag == "g" and "data-tier" in n.attrs]
    assert len(cards) == 4 and all(step_of(c) is None for c in cards), "the four tier cards' outlines show on arrival"
    numbers = [n for n in fig.walk() if n.tag == "text" and n.attrs.get("font-size") == "40"]
    assert len(numbers) == 4 and all(step_of(n) is not None for n in numbers), "each tier's number waits for its step"


def test_02_shows_its_lane_labels_on_arrival():
    labels = texts(figure("02-answer-checked-animated"), r"^(ACCOUNT|MANAGER|THE APP|BEHIND THE|SCREEN|FOUNDATIONS)$")
    assert len(labels) == 6 and all(step_of(n) is None for n in labels), "the blueprint's row headings are structure"


@pytest.mark.parametrize("name", ["04-journey-sales-director-animated", "05-journey-account-manager-animated"])
def test_a_journey_shows_its_checked_key_only_with_the_verifier(name):
    fig = figure(name)
    key = texts(fig, r"^Checked, then (answered|approved)$")
    verifier = texts(fig, r"^verifier: every number")
    assert len(key) == 1 and verifier, "one legend key for the checked style, and the verifier's message"
    assert step_of(key[0]) is not None and step_of(key[0]) == step_of(verifier[0]), "the key that names the check comes in with the verifier"
    arrow = key[0].parent.kids[key[0].parent.kids.index(key[0]) - 1]
    assert arrow.tag == "line" and step_of(arrow) == step_of(key[0]), "and so does its arrow"


def rules(css: str) -> list[tuple[list[str], str]]:
    """The top-level rules of a stylesheet as (selectors, declarations); at-rules such as media queries and keyframes are left out."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, depth, head, body = [], 0, "", ""
    for ch in css:
        if ch == "{":
            depth += 1
            if depth == 1:
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                if not head.strip().startswith("@"):
                    out.append(([s.strip() for s in head.split(",")], body))
                head, body = "", ""
                continue
        if depth == 0:
            head += ch
        else:
            body += ch
    return out


@pytest.mark.parametrize("name", ANIMATED)
def test_in_the_deck_an_unreached_item_shows_nothing_and_the_logo_band_goes(name):
    page = html(f"{name}-animated")
    css = rules("".join(re.findall(r"<style>(.*?)</style>", page, re.S)))
    declares = lambda body, prop, value: re.search(rf"(^|;)\s*{prop}\s*:\s*{value}\s*(;|$)", body.strip()) is not None  # noqa: E731
    unreached = [s for sels, body in css for s in sels if declares(body, "opacity", "0")
                 and s.startswith("html[data-embed]") and ".motion-ready" in s and "[data-motion-item]" in s
                 and ":not(.is-visible)" in s and ":not([data-part])" in s]  # 01's slabs stay, assembled, and lift on each press
    assert unreached, f"{name}: in the deck an item the controller has not reached must have opacity 0, not the plugin's faded .12"
    logo = [s for sels, body in css for s in sels if declares(body, "display", "none") and s == 'html[data-embed] [data-brand="aa-logo"]']
    assert logo, f"{name}: the deck's frame draws the logo, so the figure's own logo band hides in the deck"


@pytest.mark.parametrize("name", ANIMATED)
def test_every_animated_page_carries_the_embed_css_as_aa_writes_it_today(name):
    assert aa.EMBED_CSS in html(f"{name}-animated"), f"{name}: rebuild it, its embed CSS is not aa.EMBED_CSS"


def css_of(name) -> dict[str, str]:
    """A page's top-level rules as {selector: declarations}."""
    return {s: body for sels, body in rules("".join(re.findall(r"<style>(.*?)</style>", html(name), re.S))) for s in sels}


# the hook recolors an item's words but spares a text marked data-keep, such as a value drawn in the accent
RECEDE = "html[data-embed] .motion-ready [data-motion-item][data-recede] text:not([data-keep])"
LEAD = "html[data-embed] .motion-ready [data-motion-item][data-recede].is-current text:not([data-keep])"
OUTLINE = "html[data-embed] .motion-ready [data-motion-item][data-recede] [data-lead]"
OUTLINE_LEADS = "html[data-embed] .motion-ready [data-motion-item][data-recede].is-current [data-lead]"


@pytest.mark.parametrize("name", ANIMATED)
def test_in_the_deck_an_item_marked_to_recede_leads_in_ink_while_current_and_goes_muted_after(name):
    # one hook for every figure: the words of an item marked data-recede are ink on its own press and muted once a later press comes, over the
    # plugin's step time; outside the deck (no data-embed) they keep the color they are drawn in
    css = css_of(f"{name}-animated")
    fill = lambda body, var: re.search(rf"(^|;)\s*fill:\s*var\(--color-{var}\)\s*(;|$)", body.strip()) is not None  # noqa: E731
    assert fill(css.get(RECEDE, ""), "muted") and re.search(r"transition:\s*fill var\(--motion-step\) var\(--motion-ease\)", css.get(RECEDE, "")), \
        "an earlier item's words recede to the muted text over the step time"
    assert fill(css.get(LEAD, ""), "ink"), "the current item's words lead in ink"
    outline, leads = css.get(OUTLINE, ""), css.get(OUTLINE_LEADS, "")
    assert re.search(r"stroke:\s*var\(--color-accent\)", outline) and re.search(r"stroke-opacity:\s*0\s*(;|$)", outline.strip()) \
        and re.search(r"transition:\s*stroke-opacity var\(--motion-step\) var\(--motion-ease\)", outline), \
        "a lead mark is blue but unseen until its item is current, and fades over the step time"
    assert re.search(r"stroke-opacity:\s*1\s*(;|$)", leads.strip()), "the current item's lead mark shows its blue outline"
    unscoped = [s for s in css if "[data-recede]" in s and re.search(r"\btext$", s)]
    assert not unscoped, f"a rule that recolors every word of a receding item would take a kept value's color too: {unscoped}"


def test_the_draw_in_classes_play_once_in_the_deck_and_not_under_reduced_motion():
    # for the charts: a line traces left to right over 900ms, a dot fades in after its line, a bar grows from its baseline over 600ms
    page = html("06-data-pipeline-animated")
    css = "".join(re.findall(r"<style>(.*?)</style>", page, re.S))
    play = {s: body for sels, body in rules(css) for s in sels}
    for cls, timing in (("draw-line", "900ms ease-out forwards"), ("draw-dot", "300ms ease-out 900ms forwards"), ("draw-bar", "600ms ease-out forwards")):
        body = play.get(f"html[data-embed] .{cls}", "")
        assert re.search(rf"animation:\s*aa-{cls}\s+{timing}", body), f".{cls} plays once, only in the deck: {body!r}"
        assert "infinite" not in body
    reduced = re.search(r"@media \(prefers-reduced-motion: reduce\) \{\s*html\[data-embed\] \.draw-line, html\[data-embed\] \.draw-dot, "
                        r"html\[data-embed\] \.draw-bar \{ animation: none;", css)
    assert reduced, "under reduced motion nothing draws in"


def test_02_names_the_verifier_in_its_legend_only_with_the_verifier():
    fig = figure("02-answer-checked-animated")
    focal = [n for n in fig.walk() if n.attrs.get("data-focal") == "true"]
    assert len(focal) == 1 and step_of(focal[0]) is not None
    entry = texts(fig, r"^Focal: the verifier$")
    assert len(entry) == 1, "one legend entry names the verifier"
    assert step_of(entry[0]) == step_of(focal[0]), "the legend entry that names the verifier comes in with the verifier's row"
    swatch = entry[0].parent.kids[entry[0].parent.kids.index(entry[0]) - 1]
    assert swatch.tag == "rect" and step_of(swatch) == step_of(focal[0]), "and so does its swatch"


def test_08_names_aas_share_in_its_legend_only_with_the_share_bar():
    fig = figure("08-why-it-moved-animated")
    share = [n for n in fig.walk() if n.attrs.get("data-role") == "delta" and "share" in n.attrs.get("data-name", "").lower()]
    assert len(share) == 1 and step_of(share[0]) is not None
    entry = texts(fig, r"^Focal: AA.s share$")
    assert len(entry) == 1, "one legend entry names AA's share"
    assert step_of(entry[0]) == step_of(share[0]), "the legend entry that names AA's share comes in with the share bar"


@pytest.mark.parametrize("name", ["08-why-it-moved", "08-why-it-moved-animated"])
def test_08_says_what_route_mix_is_in_plain_words_and_that_it_barely_moved(name):
    page = html(name)
    assert not re.search(r"route mix", page, re.I), "the mix bar is named in plain words, not as route mix"
    fig = figure(name)
    deltas = sorted((n for n in fig.walk() if n.attrs.get("data-role") == "delta"), key=lambda n: float(n.attrs["x"]))
    assert len(deltas) == 3, "volume, mix and share"
    mix = deltas[1]
    note = texts(fig, r"(?i)barely moved")
    assert note, "the mix bar's note says it barely moved for Harbor"
    if name.endswith("-animated"):
        assert {step_of(n) for n in note} == {step_of(mix)}, "the note comes in with the mix bar"


def test_01_shows_its_caption_only_on_its_last_step():
    name = "01-system-exploded-animated"
    fig = figure(name)
    caption = texts(fig, r"^FOCAL LAYER$") + [n for n in fig.walk() if n.tag == "text" and n.attrs.get("font-style") == "italic"]
    assert len(caption) == 2, "the caption: its eyebrow and its one italic line"
    assert {step_of(n) for n in caption} == {step_count(name)}, "01's caption comes in with the last step"


@pytest.mark.parametrize("name", ["04-journey-sales-director", "04-journey-sales-director-animated", "05-journey-account-manager",
                                  "05-journey-account-manager-animated"])
def test_a_journey_keeps_its_legend_and_payoff_under_its_lifelines(name):
    fig = figure(name)
    lifelines = [n for n in fig.walk() if n.tag == "line" and n.attrs.get("stroke-dasharray") == "3,3"]
    keys = texts(fig, r"^(Request|Reply)$") + [n for n in fig.walk() if n.tag == "text" and n.attrs.get("font-style") == "italic"]
    assert lifelines and len(keys) == 3, "the lifelines, two legend keys and the payoff"
    assert min(extent(k)[0] for k in keys) > max(float(n.attrs["y2"]) for n in lifelines), "the legend strip sits under the sequence"


@pytest.mark.parametrize("name", ["04-journey-sales-director-animated", "05-journey-account-manager-animated"])
def test_a_journey_shows_its_payoff_only_on_its_last_step(name):
    fig = figure(name)
    payoff = [n for n in fig.walk() if n.tag == "text" and n.attrs.get("font-style") == "italic"]
    assert len(payoff) == 1 and payoff[0].words().startswith("Today"), "the one italic line is the payoff"
    assert step_of(payoff[0]) == step_count(name), "the payoff comes in with the last step"


# ---------------------------------------------------------------- 03: Delegate, a swimlane that runs one stage a press

DELEGATE = "03-delegate"
DELEGATE_PAGES = [DELEGATE, f"{DELEGATE}-animated"]
# the lanes top to bottom, each with its name: who does a step, and where it runs
LANES = ["Nightly job", "Agent runtime", "AI Foundry", "Account manager", "CRM + mail"]
# the flow in the order it runs, one stage a press: the nightly job, the fixed queries, the writer, the verifier, the person who approves, and then the
# CRM and Outlook together; each key is a data-node, and what its box says shows the stage is the one named
FLOW = ["job", "queries", "writer", "verifier", "decide", "crm"]
SAYS = {"job": r"^Runs the agents", "queries": r"fixed SQL", "writer": r"fairshare-precall-pack", "verifier": r"Checks every number", "waits": r"Waits for a decision",
        "review": r"Reviews the page", "decide": r"Approves or rejects", "crm": r"Dynamics 365 \(stand-in\)", "mail": r"Outlook"}
CAPTION = "Nothing reaches the CRM or Outlook until a person approves."


def flow_nodes(fig: Node) -> dict[str, Node]:
    """The steps of the flow, by key, in the order the figure draws them."""
    return {n.attrs["data-node"]: n for n in fig.walk() if "data-node" in n.attrs}


def test_delegate_steps_inside_the_plugins_budget():
    name = f"{DELEGATE}-animated"
    steps = [int(n.attrs["data-step"]) for n in figure(name).walk() if "data-motion-item" in n.attrs]
    assert step_count(name) <= 8 and len(steps) <= 12, f"at most eight steps and twelve marked items: {step_count(name)} and {len(steps)}"
    assert sorted(set(steps)) == list(range(1, step_count(name) + 1)) and max(steps.count(s) for s in steps) <= 2, "every step brings something, two items at most"


def test_delegate_shows_its_lanes_and_their_names_on_arrival():
    fig = figure(f"{DELEGATE}-animated")
    (lanes,) = [n for n in fig.walk() if n.attrs.get("data-role") == "lanes"]
    assert step_of(lanes) is None, "the lanes are the figure's structure, so they show on arrival"
    named = [n for n in lanes.walk() if "data-lane" in n.attrs]
    assert [n.words().strip() for n in named] == LANES, "five lanes, each with its name"
    assert all(len([k for k in n.walk() if k.tag == "svg"]) >= 1 for n in named), "each lane's mark says where its steps run"
    assert len([n for n in lanes.walk() if n.tag == "line"]) == len(LANES) + 2, "a rule over and under every lane, and the line after the names"
    assert flow_nodes(fig) and all(step_of(n) is not None for n in flow_nodes(fig).values()), "every step of the flow waits for its press"


def test_delegate_brings_in_the_flow_one_stage_a_press_in_the_order_it_runs():
    name = f"{DELEGATE}-animated"
    fig = figure(name)
    nodes = flow_nodes(fig)
    assert sorted(nodes) == sorted(SAYS), "the nine steps of the flow"
    for key, words in SAYS.items():
        assert re.search(words, nodes[key].words()), f"{key} says {words!r}: {nodes[key].words()!r}"
    step = {key: step_of(n) for key, n in nodes.items()}
    assert [step[k] for k in FLOW] == list(range(1, step_count(name) + 1)), \
        f"the nightly job, the fixed queries, the writer, the verifier, the person who approves, then the CRM and Outlook, a press each: {step}"
    assert step["mail"] == step["crm"], "Outlook comes in with the CRM, once a person has approved"
    assert step["verifier"] <= step["waits"] <= step["review"] <= step["decide"], "the checked page waits, and a person reviews it, before the decision"
    arrows = [n for n in fig.walk() if n.tag == "path" and "data-to" in n.attrs]
    assert sorted(a.attrs["data-to"] for a in arrows) == sorted(set(nodes) - {"job"}), "one arrow into every step but the first"
    for a in arrows:
        assert step_of(a) == step[a.attrs["data-to"]], f"the arrow into {a.attrs['data-to']} comes in with it"
    labels = [n for n in fig.walk() if n.tag == "text" and "data-to" in n.attrs]
    assert len(labels) == 4, "four arrows carry a label"
    for label in labels:
        assert step_of(label) == step[label.attrs["data-to"]], f"{label.words()!r} comes in with its arrow"


def test_delegate_names_the_person_who_decides_in_its_legend_only_with_that_step():
    fig = figure(f"{DELEGATE}-animated")
    focal = [n for n in fig.walk() if n.attrs.get("data-focal") == "true"]
    assert len(focal) == 1 and focal[0].attrs.get("data-node") == "decide", "the focal step is the person's decision"
    (entry,) = texts(fig, r"^A person decides$")
    assert step_of(entry) == step_of(focal[0]), "the legend entry that names the focal step comes in with it"
    swatch = entry.parent.kids[entry.parent.kids.index(entry) - 1]
    assert swatch.tag == "rect" and step_of(swatch) == step_of(focal[0]), "and so does its swatch"
    (handoff,) = [n for n in fig.walk() if n.tag == "path" and n.attrs.get("stroke") == aa.ACCENT]
    (key,) = texts(fig, r"^Handoff to a person$")
    assert step_of(key) == step_of(handoff), "the key for the handoff to a person comes in with the handoff"
    rest = texts(fig, r"^(LEGEND|Step|Next step|Request|Reply)$")
    assert len(rest) == 5 and all(step_of(n) is None for n in rest), "the rest of the key reads the figure's marks, so it shows on arrival"


def test_delegate_shows_its_caption_only_on_its_last_step():
    name = f"{DELEGATE}-animated"
    fig = figure(name)
    caption = texts(fig, r"^FOCAL STEP$") + texts(fig, rf"^{re.escape(CAPTION)}$")
    assert len(caption) == 2, "the caption: its eyebrow and its line"
    assert {step_of(n) for n in caption} == {step_count(name)}, "the caption gives the point away, so it comes in with the last step"


@pytest.mark.parametrize("name", DELEGATE_PAGES)
def test_delegate_gives_no_count_of_the_agents_the_nightly_job_runs(name):
    # the nightly job runs the Monday pre-call pack, the agreement watch and CRM versus reality (lakehouse/job_tasks.py, agents_task), while prospect
    # research runs when a person picks a market, so "the four agents" on the job's box was false; the box, its step and the description give no count
    (job,) = [n for n in figure(name).walk() if n.attrs.get("data-node") == "job"]
    assert [n.words() for n in job.walk() if n.tag == "text"][0] == "Runs the agents", "the job's box names no count"
    counted = re.findall(r"(?i)\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(?:\w+\s+)?agents\b", html(name))
    assert not counted, f"no count of agents anywhere on the page, its step announcements and description included: {counted}"


@pytest.mark.parametrize("name", DELEGATE_PAGES)
def test_delegate_says_it_in_plain_words_and_keeps_saying_the_crm_is_a_stand_in(name):
    fig = figure(name)
    assert not [n.words() for n in fig.walk() if n.tag == "text" and n.attrs.get("font-style") == "italic"], "no italic display type"
    assert not re.search("[–—]", html(name)), "no em or en dash on the page"
    assert len(texts(fig, rf"^{re.escape(CAPTION)}$")) == 1, "the caption says who decides, in the active voice"
    named = texts(fig, r"Dynamics 365")
    assert named and all("stand-in" in n.words() for n in named), "wherever the figure names Dynamics 365, it says the CRM is a stand-in"
    (desc,) = [n for n in fig.walk() if n.tag == "desc"]
    assert "made-up CRM shaped like Dynamics 365 Sales" in desc.words(), "and so does its description"


# ---------------------------------------------------------------- 11: revenue by month, a chart that draws itself

REVENUE = "11-revenue-by-month"


def year_lines(fig: Node) -> list[Node]:
    """The chart's lines, each declaring the year it plots."""
    return [n for n in fig.walk() if n.tag == "path" and "data-series" in n.attrs]


def classes(node: Node) -> list[str]:
    return node.attrs.get("class", "").split()


def test_revenue_draws_its_two_year_lines_on_arrival_and_their_dots_after_them():
    fig = figure(f"{REVENUE}-animated")
    lines = year_lines(fig)
    assert sorted(n.attrs["data-series"] for n in lines) == ["2025", "2026"], "one line per year"
    for line in lines:
        assert "draw-line" in classes(line) and line.attrs.get("pathlength") == "1", "in the deck each line traces itself left to right"
        assert step_of(line) is None, "the lines are the chart's marks, so they draw on arrival"
    dots = [n for n in fig.walk() if n.tag == "circle" and not in_logo(n)]
    assert dots and all("draw-dot" in classes(d) and step_of(d) is None for d in dots), "the dots fade in after their line"


def test_revenue_brings_in_the_band_with_its_net_change_then_one_note_per_press():
    name = f"{REVENUE}-animated"
    fig = figure(name)
    items = [n for n in fig.walk() if "data-motion-item" in n.attrs]
    assert step_count(name) == 4 and sorted(int(n.attrs["data-step"]) for n in items) == [1, 2, 3, 4], "the band, then three notes, one item each"
    band = [n for n in fig.walk() if n.attrs.get("data-role") == "band"]
    assert len(band) == 1 and step_of(band[0]) == 1, "the March and April band is the first press"
    label = texts(fig, r"^Mar and Apr 2026$")
    net = texts(fig, r"^[+-]?\d+\.\d%$")
    assert len(label) == 1 and len(net) == 2, "the band names its months, and carries each month's net change against last year"
    assert {step_of(n) for n in label + net + texts(fig, r"^Net, 2026 vs 2025$")} == {1}, "and they come in with it"
    notes = {}
    for n in fig.walk():
        if n.tag == "text" and "data-note" in n.attrs:
            notes.setdefault(n.attrs["data-note"], []).append(n)
    assert list(notes) == ["sunbelt", "harbor", "others"], "three notes: Sunbelt, Harbor, the other agencies"
    for (key, lines), step, subject in zip(notes.items(), (2, 3, 4), ("Sunbelt", "Harbor", "other")):
        assert {step_of(n) for n in lines} == {step}, f"the {key} note is press {step}"
        assert subject in " ".join(n.words() for n in lines)


@pytest.mark.parametrize("name", [REVENUE, f"{REVENUE}-animated"])
def test_revenue_has_no_legend_since_each_line_ends_in_its_year(name):
    fig = figure(name)
    assert not texts(fig, r"(?i)^legend$"), "both lines carry their year, so the legend goes"
    lines = year_lines(fig)
    assert len(lines) == 2
    for line in lines:
        year = line.attrs["data-series"]
        x, y = (float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", line.attrs["d"])[-2:])
        label = texts(fig, rf"^{year}$")
        assert len(label) == 1, f"one label for {year}"
        lx, ly = float(label[0].attrs["x"]), float(label[0].attrs["y"])
        assert x < lx <= x + 24 and abs(ly - y) <= 8, f"{year}'s label sits just past the end of its line"


@pytest.mark.parametrize("name", [REVENUE, f"{REVENUE}-animated"])
def test_revenue_keeps_one_order_of_weight_title_then_notes_then_the_source(name):
    fig = figure(name)
    words = [n for n in fig.walk() if n.tag == "text" and not in_logo(n)]
    size = lambda n: float(n.attrs["font-size"])  # noqa: E731
    weight = lambda n: int(n.attrs.get("font-weight", 400))  # noqa: E731
    assert not [n.words() for n in words if n.attrs.get("font-style") == "italic"], "no italic display type"
    (title,) = texts(fig, r"^AA revenue by month$")
    assert size(title) == max(size(n) for n in words) and weight(title) == max(weight(n) for n in words), "the title is the strongest text"
    notes = [n for n in words if "data-note" in n.attrs]
    assert notes and all(size(n) < size(title) and weight(n) < weight(title) for n in notes), "a note is smaller and lighter than the title"
    (source,) = texts(fig, r"gold\.fact_agency_sales_monthly")
    assert size(source) == min(size(n) for n in words) and source.attrs["fill"] == MUTED, "the source line is the smallest text, and grey"


def item_of(node: Node):
    """The motion item a node sits in, or None."""
    while node is not None and "data-motion-item" not in node.attrs:
        node = node.parent
    return node


def test_revenue_lets_the_newest_note_lead_and_the_earlier_ones_recede():
    # a note is drawn in the muted text, as the static page and the plugin's own page show it; in the deck the note on the current press
    # leads in ink, and when the next one comes it recedes to the muted text again, through the hook every figure shares
    name = f"{REVENUE}-animated"
    notes = [n for n in figure(name).walk() if n.tag == "text" and "data-note" in n.attrs]
    assert len(notes) == 3 and {n.attrs["fill"] for n in notes} == {MUTED}
    assert all("data-recede" in item_of(n).attrs for n in notes), "each note's item is marked to recede"
    assert not [s for s in css_of(name) if "data-note" in s], "the page keeps no recede rule of its own; the hook in aa.EMBED_CSS does it"


# ---------------------------------------------------------------- 09a and 09b: the seven numbers over two slides, one card a press

# Each page's numbers in order: the key in ops.kpi_definitions, the name on the card, how it is calculated in the plain words of the spec's
# "Explainability fixes" section (docs/superpowers/specs/2026-10-20-deck-redesign-design.md), and the fact the card prints for Harbor in Sep 2026.
NUMBERS = {
    "09a-numbers-share": [
        ("aa_revenue", "AA revenue", "AA revenue is AA's revenue on the rows in question.", "harbor_revenue_sep26_usd"),
        ("aa_share", "AA share", "AA share is AA revenue divided by everything the agency sold on the same routes, all airlines together.",
         "harbor_share_sep26"),
        ("fair_share", "Fair share", "Fair share is AA's share of the seats on each route, weighted by how much the agency sold there. "
                                     "The seat shares are made up.", "harbor_fair_share_sep26"),
    ],
    "09b-numbers-gaps": [
        ("share_gap_pts", "Share gap in points", "The share gap in points is AA share minus fair share.", "harbor_gap_pts_sep26"),
        ("share_gap_usd", "Share gap in dollars", "The share gap in dollars is AA revenue minus what fair share would have brought in.",
         "harbor_gap_usd_sep26"),
        ("yoy_revenue_pct", "Year over year", "Year over year compares AA revenue with the same month last year.", "harbor_yoy_sep26"),
        ("pace_pct", "Pace", "Pace is revenue so far this year divided by the goal so far, counting only the months the agency reported. "
                             "The goals are made up.", "harbor_pace_sep26"),
    ],
}
NUMBER_PAGES = [n for page in NUMBERS for n in (page, f"{page}-animated")]
# where the seven numbers live and why that matters, as the same spec words it; each page closes on it
WHERE = ("Six of the seven numbers are measures in the metric view gold.sales_metrics, worked out from the gold tables when a query runs, "
         "so a share comes out right at any grouping. Pace is stored in gold.agency_pace, because its goal is set per agency and year. "
         "Genie, the dashboard and Ask read the six from that one metric view, so their numbers agree.")


def marked(fig: Node, part: str, key=None) -> list[Node]:
    """The marks that carry data-<part>, or data-<part>="<key>"."""
    return [n for n in fig.walk() if f"data-{part}" in n.attrs and (key is None or n.attrs[f"data-{part}"] == key)]


def said(nodes) -> str:
    """The words of a run of text lines, as one sentence."""
    return " ".join(n.words().strip() for n in nodes)


@pytest.mark.parametrize("page", NUMBERS)
def test_a_numbers_page_brings_in_one_card_a_press_and_closes_on_where_the_numbers_live(page):
    name = f"{page}-animated"
    fig, cards = figure(name), NUMBERS[page]
    items = sorted((n for n in fig.walk() if "data-motion-item" in n.attrs), key=lambda n: int(n.attrs["data-step"]))
    assert step_count(name) == len(cards) + 1 and [int(n.attrs["data-step"]) for n in items] == list(range(1, len(cards) + 2)), \
        "one item a press: a card for each number, then where the numbers live"
    for step, (key, title, _, _) in enumerate(cards, 1):
        frame, (heading,) = marked(fig, "card", key), marked(fig, "name", key)
        assert frame and heading.words() == title and all(step_of(n) is None for n in frame + [heading]), \
            f"{title}: its card's frame and its name are structure, so they show on arrival"
        definition, value = marked(fig, "def", key), marked(fig, "value", key)
        assert definition and len(value) == 1 and {step_of(n) for n in definition + value} == {step}, f"{title}: how it is calculated and its value are press {step}"
        assert "data-recede" in item_of(value[0]).attrs, f"{title}: once the next press comes, the card recedes so the newest one leads"
        (outline,) = marked(item_of(value[0]), "lead")
        geometry = lambda n: [n.attrs[k] for k in ("x", "y", "width", "height")]  # noqa: E731
        assert step_of(outline) == step and outline.attrs["stroke"] == "none" and geometry(outline) == geometry(frame[0].kids[0]), \
            f"{title}: its press brings the card's outline again, unstroked, for the deck to draw in blue while the card is the newest"
    where = marked(fig, "where")
    assert where and {step_of(n) for n in where} == {len(cards) + 1}, "where the numbers live closes the page, on the last press"
    assert "data-recede" not in item_of(where[0]).attrs, "the close is the last press, so it never recedes"
    harbor = texts(fig, r"(?i)^harbor, sep 2026$")
    assert len(harbor) == 1 and step_of(harbor[0]) is None, "the heading over the values names the agency and month they are for, on arrival"


@pytest.mark.parametrize("name", NUMBER_PAGES)
def test_each_card_says_how_its_number_is_calculated_and_prints_harbors_value_from_the_facts(name):
    fig = figure(name)
    for key, title, words, fact in NUMBERS[name.removesuffix("-animated")]:
        assert said(marked(fig, "def", key)) == words, f"{title}: the spec's plain words"
        (value,) = marked(fig, "value", key)
        shown = FACTS[fact]["display"]
        assert value.words().startswith(shown) and not re.search(r"\d", value.words()[len(shown):]), \
            f"{title}: the card prints {fact} as the deck shows it ({shown!r}), with at most a unit word after it: {value.words()!r}"


@pytest.mark.parametrize("name", NUMBER_PAGES)
def test_each_numbers_page_closes_on_where_the_numbers_live_and_why_that_matters(name):
    assert said(marked(figure(name), "where")) == WHERE


@pytest.mark.parametrize("name", NUMBER_PAGES)
def test_a_numbers_page_reads_from_the_back_of_the_room(name):
    fig = figure(name)
    size = lambda n: float(n.attrs["font-size"])  # noqa: E731
    weight = lambda n: int(n.attrs.get("font-weight", 400))  # noqa: E731
    defs, values, names, where = marked(fig, "def"), marked(fig, "value"), marked(fig, "name"), marked(fig, "where")
    assert min(size(n) for n in defs + values) >= 18 and min(size(n) for n in where) >= 16, "the words a press brings in are big enough to read from the back"
    assert all(weight(n) > weight(d) for n in names for d in defs), "a card's name is heavier than its definition"
    assert not [n.words() for n in fig.walk() if n.tag == "text" and n.attrs.get("font-style") == "italic"], "no italic display type"


def test_the_drift_strip_stays_on_the_glossary_and_off_the_two_numbers_pages():
    assert texts(figure("09-definitions"), r"^HOW A DEFINITION STAYS HONEST$"), "09-definitions keeps building as it did"
    for name in NUMBER_PAGES:
        assert not re.search(r"STAYS HONEST|twin_sql_retired|kpi_parity", html(name)), f"{name} holds no part of the drift strip"


# ---------------------------------------------------------------- 12: AA share against fair share, a dumbbell in steps

SHARE = "12-share-vs-fair"
SHARE_PAGES = [SHARE, f"{SHARE}-animated"]
SHARE_FACT = re.compile(r"agency_q3_(aa|fair)_share_(\w+)")
# the note under the chart, as share_fair.py words it: why fair share barely moves (check_claims proves the reason on every build), and that the
# seat shares are made up, as the seats row's column meaning says it
SEATS_NOTE = ("Fair share is nearly the same for every agency because each one spreads its sales over the same twelve routes in similar proportions. "
              "The seat shares are made up, one base share per route, moved a little each month.")


def series(fig: Node, name: str) -> list[Node]:
    """The dots of one series: fair share's hollow ones, or AA share's solid ones."""
    return [n for n in fig.walk() if n.tag == "circle" and n.attrs.get("data-series") == name]


def rows_top_down(fig: Node) -> list[str]:
    """The agencies, in the order their rows run down the chart."""
    return [n.attrs["data-row-label"] for n in sorted((n for n in fig.walk() if "data-row-label" in n.attrs), key=lambda n: float(n.attrs["y"]))]


def values_printed(fig: Node) -> list[Node]:
    """Every text that prints a value from the data: a number with a decimal point. The ticks are whole numbers and the title's year has none."""
    return [n for n in fig.walk() if n.tag == "text" and re.search(r"\d\.\d", n.words())]


def test_share_fair_steps_inside_the_plugins_budget():
    name = f"{SHARE}-animated"
    steps = [int(n.attrs["data-step"]) for n in figure(name).walk() if "data-motion-item" in n.attrs]
    assert step_count(name) <= 8 and len(steps) <= 12, f"at most eight steps and twelve marked items: {step_count(name)} and {len(steps)}"
    assert sorted(set(steps)) == list(range(1, step_count(name) + 1)) and max(steps.count(s) for s in steps) <= 2, "every step brings something, two items at most"


def test_share_fair_shows_its_agencies_and_its_axis_on_arrival():
    fig = figure(f"{SHARE}-animated")
    names = [n for n in fig.walk() if "data-row-label" in n.attrs]
    assert len(names) == FACTS["agencies"]["value"] and all(step_of(n) is None for n in names), "every agency's name is structure, so it shows on arrival"
    ticks = [n for n in fig.walk() if n.tag == "text" and "data-tick" in n.attrs]
    grid = [n for n in fig.walk() if n.tag == "line" and "data-grid" in n.attrs]
    assert len(ticks) >= 4 and len(grid) == len(ticks), "a gridline and a tick for every step of the axis"
    assert all(step_of(n) is None for n in ticks + grid), "the axis shows on arrival"
    assert all(re.fullmatch(r"\d+%", n.words()) for n in ticks), "each tick carries its unit, so the axis needs no title"


def test_share_fair_brings_in_fair_share_then_the_made_up_seats_then_aa_share_then_one_callout_a_press():
    name = f"{SHARE}-animated"
    fig = figure(name)
    fair, solid = series(fig, "fair"), series(fig, "aa")
    assert len(fair) == len(solid) == FACTS["agencies"]["value"], "a fair share dot and an AA share dot for every agency"
    fair_step, solid_step = {step_of(d) for d in fair}, {step_of(d) for d in solid}
    assert fair_step == {1} and len(solid_step) == 1, "each series comes in whole, fair share first"
    (seats,) = texts(fig, r"(?i)made.up")
    words = [n for n in item_of(seats).walk() if n.tag == "text"]
    assert all(n.attrs.get("data-note") == "seats" for n in words) and 1 < step_of(seats) < min(solid_step), \
        "the note about the made-up seat shares is a step of its own, before AA share"
    connectors = [n for n in fig.walk() if n.tag == "line" and "data-agency" in n.attrs]
    assert connectors and {step_of(c) for c in connectors} == solid_step, "the line between the two dots comes in with AA share"
    callouts: dict[str, set] = {}
    for n in fig.walk():
        if "data-callout" in n.attrs:
            callouts.setdefault(n.attrs["data-callout"], set()).add(step_of(n))
    order = rows_top_down(fig)
    assert list(callouts) == [order[0], order[-1]], "two agencies carry the story: the top row, furthest above fair share, then the bottom row"
    assert [s for (s,) in callouts.values()] == [min(solid_step) + 1, min(solid_step) + 2] == [step_count(name) - 1, step_count(name)], \
        "after AA share, one callout a press, and they close the page"


@pytest.mark.parametrize("name", SHARE_PAGES)
def test_share_fair_prints_four_values_at_most_each_one_a_fact(name):
    fig = figure(name)
    values = values_printed(fig)
    assert 0 < len(values) <= 4, f"at most four values on the finished page, found {[v.words() for v in values]}"
    by_agency: dict[str, dict[str, str]] = {}
    for v in values:
        key = v.attrs.get("data-fact", "")
        assert key in FACTS and v.words() == FACTS[key]["display"], f"{v.words()!r} prints {key or 'no fact'} as the deck shows it"
        share = SHARE_FACT.fullmatch(key)
        assert share, f"{key}: a value on this chart is an agency's AA share or fair share"
        by_agency.setdefault(v.attrs["data-callout"], {})[share.group(1)] = share.group(2)
    order = rows_top_down(fig)
    assert list(by_agency) == [order[0], order[-1]], "the values belong to the agencies that carry the story"
    assert all(set(ends) == {"aa", "fair"} and len(set(ends.values())) == 1 for ends in by_agency.values()), "each of them with both its ends"
    if name.endswith("-animated"):
        assert all(step_of(v) is not None for v in values), "a value waits for its callout"


@pytest.mark.parametrize("name", SHARE_PAGES)
def test_share_fair_keeps_the_made_up_seat_shares_labeled_in_plain_words(name):
    fig = figure(name)
    note = sorted(marked(fig, "note", "seats"), key=lambda n: float(n.attrs["y"]))
    assert said(note) == SEATS_NOTE, "the note says why fair share barely moves, and that the seat shares are made up, in share_fair.py's words"
    assert ":" not in said(note), "no colon used as a connector"
    assert not re.search("[\u2013\u2014]", html(name)), "no em or en dash on the page"


@pytest.mark.parametrize("name", SHARE_PAGES)
def test_share_fair_names_each_series_over_its_top_dot_and_has_no_legend(name):
    fig = figure(name)
    assert not texts(fig, r"(?i)^legend$"), "the marks are labeled where they are, so the legend goes"
    for key, words in (("fair", "Fair share"), ("aa", "AA share")):
        (label,) = [n for n in fig.walk() if n.attrs.get("data-label") == key]
        top = min(series(fig, key), key=lambda d: float(d.attrs["cy"]))
        assert label.words() == words and abs(float(label.attrs["x"]) - float(top.attrs["cx"])) <= 24 \
            and 12 <= float(top.attrs["cy"]) - float(label.attrs["y"]) <= 32, f"{words!r} sits over the top row's dot"
        if name.endswith("-animated"):
            assert step_of(label) == step_of(top), f"{words!r} comes in with its dots"


@pytest.mark.parametrize("name", SHARE_PAGES)
def test_share_fair_keeps_one_order_of_weight_title_then_notes_then_the_source(name):
    fig = figure(name)
    words = [n for n in fig.walk() if n.tag == "text" and not in_logo(n)]
    size = lambda n: float(n.attrs["font-size"])  # noqa: E731
    weight = lambda n: int(n.attrs.get("font-weight", 400))  # noqa: E731
    assert not [n.words() for n in words if n.attrs.get("font-style") == "italic"], "no italic display type"
    (title,) = texts(fig, r"^AA share against fair share, Q3 2026$")
    assert size(title) == max(size(n) for n in words) and weight(title) == max(weight(n) for n in words), "the title is the strongest text"
    notes = [n for n in words if "data-note" in n.attrs]
    assert {n.attrs["data-note"] for n in notes} == {"seats", "above", "below"} and all(size(n) < size(title) and weight(n) < weight(title) for n in notes), \
        "the note under the chart and the two callouts' words are smaller and lighter than the title"
    (source,) = texts(fig, r"gold\.fact_agency_sales_monthly")
    assert size(source) == min(size(n) for n in words) and source.attrs["fill"] == MUTED, "the source line is the smallest text, and grey"


def test_share_fair_lets_the_newest_note_lead_and_keeps_aa_shares_values_in_the_accent():
    fig = figure(f"{SHARE}-animated")
    notes = [n for n in fig.walk() if n.tag == "text" and "data-note" in n.attrs]
    assert notes and all("data-recede" in item_of(n).attrs for n in notes), "the sentence and each callout recede once a later press comes"
    kept = [n for n in fig.walk() if n.tag == "text" and "data-keep" in n.attrs]
    assert kept and all(n.attrs.get("data-series") == "aa" and n.attrs["fill"] == aa.ACCENT for n in kept), "AA share's values keep the accent of AA share's dots"
    assert all("data-keep" not in n.attrs for n in values_printed(fig) if n.attrs.get("data-series") != "aa"), "fair share's values lead and recede with their callout"
    assert all("data-recede" not in item_of(d).attrs for d in series(fig, "aa") + series(fig, "fair")), "the dots are the chart, so they never recede"


# ---------------------------------------------------------------- 15: the same layers at AA, a kind of mark a press, then the feeds hardest first

AT_AA = "15-at-aa"
AT_AA_PAGES = [AT_AA, f"{AT_AA}-animated"]
# the five layers of 01, top to bottom
AT_AA_LAYERS = ["The app", "Checks", "Agents", "Definitions", "Data"]
# the three marks in the order they come, a press each, with the words the legend gives each one
AT_AA_MARKS = {"run": "Running today", "built": "Built, not deployed", "wait": "Waiting on AA's Microsoft account"}
# the made-up tables the AA feeds would replace, hardest first in the data lead's order, and the press each feed comes in on: the hardest
# alone, the seat capacity alone, then two a press
AT_AA_TABLES = ["fact_agency_sales_monthly", "fact_market_capacity", "fact_corporate_bookings", "contract_clauses", "crm_contacts", "agency_goals"]
AT_AA_FEED_STEPS = [4, 5, 6, 6, 7, 7]


def at_aa_pieces(fig: Node) -> list[tuple[str, str, str, Node]]:
    """Each piece listed under a layer: its mark, its words, its layer and its node, in the order the page draws them."""
    return [(n.attrs["data-piece"], n.words().strip(), n.attrs["data-layer"], n) for n in fig.walk() if "data-piece" in n.attrs]


def at_aa_baseline(node: Node) -> float:
    """The baseline of the first text in a mark."""
    return float(next(t for t in node.walk() if t.tag == "text").attrs["y"])


def at_aa_tree(node: Node):
    """A mark and everything in it, as a value two pages can be compared by."""
    return node.tag, tuple(sorted(node.attrs.items())), node.text.strip(), tuple(at_aa_tree(k) for k in node.kids)


def at_aa_feed_lines(fig: Node, table: str) -> list[Node]:
    """The text lines of one table's feed."""
    (feed,) = [n for n in fig.walk() if n.attrs.get("data-feed") == table]
    return [n for n in feed.walk() if n.tag == "text"]


def test_at_aa_steps_inside_the_plugins_budget():
    name = f"{AT_AA}-animated"
    steps = [int(n.attrs["data-step"]) for n in figure(name).walk() if "data-motion-item" in n.attrs]
    assert step_count(name) <= 8 and len(steps) <= 12, f"at most eight steps and twelve marked items: {step_count(name)} and {len(steps)}"
    assert sorted(set(steps)) == list(range(1, step_count(name) + 1)) and max(steps.count(s) for s in steps) <= 2, "every step brings something, two items at most"


def test_at_aa_shows_its_five_layers_and_their_names_on_arrival_at_rest_as_01_draws_them():
    # the layers are the structure, so they show on arrival; nothing lifts, since lifting the layers is 01's reveal, and in the deck the rule that
    # leaves 01's slabs alone never has to, because none of 15's slabs is a step
    fig = figure(f"{AT_AA}-animated")
    parts = [n for n in fig.walk() if "data-part" in n.attrs]
    assert [p.attrs["data-name"] for p in parts][::-1] == AT_AA_LAYERS, "the five layers of 01, drawn from the bottom up"
    assert all(step_of(p) is None and "data-motion-item" not in p.attrs for p in parts), "no layer is a step or sits in one"
    assert not [p.attrs["data-part"] for p in parts if "style" in p.attrs or "data-closed-z" in p.attrs], "no layer carries a lift"
    seat = lambda n: tuple(n.attrs[k] for k in ("data-rect", "data-z", "data-t", "data-level"))  # noqa: E731
    assert {p.attrs["data-part"]: seat(p) for p in parts} == {n.attrs["data-part"]: seat(n) for n in figure("01-system-exploded").walk() if "data-part" in n.attrs}, \
        "every layer has the size and the height 01 gives it"
    names = [n for n in fig.walk() if n.attrs.get("data-role") == "name"]
    assert [n.words() for n in names][::-1] == AT_AA_LAYERS and all(step_of(n) is None for n in names), "each layer's name shows on arrival"
    (stack,) = [n for n in fig.walk() if "data-exploded" in n.attrs]
    assert not [n for n in stack.walk() if "data-motion-item" in n.attrs], "nothing in the stack waits for a press"
    (still,) = [n for n in figure(AT_AA).walk() if "data-exploded" in n.attrs]
    assert at_aa_tree(stack) == at_aa_tree(still), "the stepped page draws the same stack as the static one"


def test_at_aa_brings_in_what_runs_then_what_is_built_then_what_waits_a_press_each_with_its_legend_entry():
    fig = figure(f"{AT_AA}-animated")
    pieces = at_aa_pieces(fig)
    steps: dict[str, set] = {}
    for kind, words, _, node in pieces:
        assert [m.attrs["data-mark"] for m in node.walk() if "data-mark" in m.attrs] == [kind], f"{words!r} sits behind its own mark"
        steps.setdefault(kind, set()).add(step_of(node))
    assert {k: sorted(v) for k, v in steps.items()} == {"run": [1], "built": [2], "wait": [3]}, \
        "a press each: what runs today, then what is built but not deployed, then what waits on AA's Microsoft account"
    order = list(AT_AA_MARKS)
    for layer in {layer for _, _, layer, _ in pieces}:
        kinds = [kind for kind, _, at, node in sorted(pieces, key=lambda p: at_aa_baseline(p[3])) if at == layer]
        assert kinds == sorted(kinds, key=order.index), f"{layer}: each press fills the rows under the last one's, so its pieces run in the order the presses come"
    keys = {n.attrs["data-key"]: n for n in fig.walk() if "data-key" in n.attrs}
    assert {k: n.words().strip() for k, n in keys.items()} == AT_AA_MARKS, "the legend names the three marks"
    for kind, entry in keys.items():
        assert [m.attrs["data-mark"] for m in entry.walk() if "data-mark" in m.attrs] == [kind], f"the legend entry for {kind} shows its mark"
        assert step_of(entry) == min(steps[kind]), f"the legend entry for {kind} comes in with its marks"
    (legend,) = texts(fig, r"^LEGEND$")
    rule = legend.parent.kids[legend.parent.kids.index(legend) - 1]
    assert step_of(legend) == 1 and rule.tag == "line" and step_of(rule) == 1, "the legend, its heading and its rule arrive with the first marks"


def test_at_aa_brings_in_each_feed_beside_its_table_hardest_first_once_the_marks_are_in():
    name = f"{AT_AA}-animated"
    fig = figure(name)
    tables = sorted((n for n in fig.walk() if "data-table" in n.attrs), key=at_aa_baseline)
    assert [n.attrs["data-table"] for n in tables] == AT_AA_TABLES, "the made-up tables down the list, hardest first"
    assert all(step_of(n) is None for n in tables), "a table heads its row, so the tables show on arrival"
    feeds = {n.attrs["data-feed"]: n for n in fig.walk() if "data-feed" in n.attrs}
    assert sorted(feeds, key=lambda k: at_aa_baseline(feeds[k])) == AT_AA_TABLES, "one feed for each table"
    assert [step_of(feeds[t]) for t in AT_AA_TABLES] == AT_AA_FEED_STEPS, \
        "once the marks are in, the feeds hardest first: the agency's sales alone, the seat capacity alone, then two a press"
    assert max(AT_AA_FEED_STEPS) == step_count(name), "the feeds close the figure"
    for table in tables:
        assert at_aa_baseline(feeds[table.attrs["data-table"]]) == at_aa_baseline(table), f"the feed for {table.attrs['data-table']} sits beside its table, on its first line"
    lines = at_aa_feed_lines(fig, AT_AA_TABLES[0])
    feed, why = said(n for n in lines if "data-note" not in n.attrs), said(n for n in lines if "data-note" in n.attrs)
    assert "the agency's sales on other airlines" in feed and why.startswith("The hardest, because AA sees its own sales"), \
        "the hardest says what it needs, the agency's sales on other airlines, and in a note why it is the hardest"


def test_at_aa_lets_the_newest_press_lead_and_keeps_the_legend_heading_as_drawn():
    # the words a press brings lead in ink while it is current and recede to the muted text once a later press comes (aa.EMBED_CSS), so the room
    # finds the one built piece among the running ones, and then each new feed
    fig = figure(f"{AT_AA}-animated")
    items = [n for n in fig.walk() if "data-motion-item" in n.attrs]
    assert items and all("data-recede" in n.attrs for n in items), "every step's words lead while it is current and recede after"
    kept = [n.words() for n in fig.walk() if n.tag == "text" and "data-keep" in n.attrs]
    assert kept == ["LEGEND"], "only the legend's heading keeps the muted color it is drawn in"
    notes = [n for n in fig.walk() if n.tag == "text" and "data-note" in n.attrs]
    assert notes and notes == [n for n in at_aa_feed_lines(fig, AT_AA_TABLES[0]) if "data-note" in n.attrs], "the one note says why the hardest feed is the hardest"
    assert all(n.attrs["fill"] == MUTED for n in notes), "it is drawn in the muted text, as a note is, and leads in ink on its own press in the deck"


@pytest.mark.parametrize("name", AT_AA_PAGES)
def test_at_aa_says_it_in_plain_words_and_marks_every_azure_possibility_as_waiting(name):
    fig = figure(name)
    assert not [n.words() for n in fig.walk() if n.tag == "text" and n.attrs.get("font-style") == "italic"], "no italic display type"
    assert not re.search("[\u2013\u2014]", html(name)), "no em or en dash on the page"
    pieces = {words: kind for kind, words, _, _ in at_aa_pieces(fig)}
    slides = (ROOT / "web/src/deck/slides.ts").read_text(encoding="utf-8")
    possible = re.findall(r'head: "([^"]+)", body: "[^"]*", tag: "Possibility"', slides)
    assert len(possible) == 4, "the azure slide's four possibilities"
    for p in possible:
        assert pieces.get(p) == "wait", f"{p!r} is a possibility on the azure slide, so here it waits on AA's Microsoft account"
    built = json.loads(re.search(r"export const BUILT = (\[.*?\]);", slides).group(1))
    for words, kind in pieces.items():
        if any(b.lower() in words.lower() for b in built):
            assert kind != "wait", f"{words!r} names something built, so it is not marked as waiting"
    assert (pieces["Foundry writers"], pieces["Harness as a Foundry hosted agent"]) == ("run", "built"), "the Foundry writers run, the hosted agent is built"

"""What the figures show inside the /present deck: nothing before its step, and nothing under the deck's frame.

The deck's frame covers y 0 to 64 of a figure's 1280 by 720 view box with its header and y 690 to 720 with its footer, so every figure the deck shows
keeps its marks between y 64 and y 680; the logo band at the top is hidden in the deck. In the deck's embed mode (aa.EMBED_CSS, baked into every
animated page when it is built) an item the controller has not reached shows nothing, and whatever gives a figure's point away (a legend entry that
names the focal item, a caption, a payoff line) comes in with the step that brings in its item. A figure's structure (its axes, headings, actors and
frame) shows on arrival, and a chart's lines draw then; its notes come one per press. These read the generated pages; rebuild them with the commands
in docs/diagrams/README.md.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIAGRAMS = ROOT / "docs" / "diagrams"
ANIMATED = ["01-system-exploded", "02-answer-checked", "04-journey-sales-director", "05-journey-account-manager", "06-data-pipeline",
            "08-why-it-moved", "11-revenue-by-month"]
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
    sys.path.insert(0, str(ROOT / "docs/diagrams/src"))
    import aa
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


# ---------------------------------------------------------------- 11: revenue by month, a chart that draws itself

REVENUE = "11-revenue-by-month"
MUTED = "#5a7181"  # the figures' muted text (aa.MUTED)


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


def test_revenue_lets_the_newest_note_lead_and_the_earlier_ones_recede():
    # a note is drawn in the muted text, as the static page and the plugin's own page show it; in the deck the note on the current press
    # leads in ink, and when the next one comes it recedes to the muted text again
    name = f"{REVENUE}-animated"
    notes = [n for n in figure(name).walk() if n.tag == "text" and "data-note" in n.attrs]
    assert len(notes) == 3 and {n.attrs["fill"] for n in notes} == {MUTED}
    css = {s: body for sels, body in rules("".join(re.findall(r"<style>(.*?)</style>", html(name), re.S))) for s in sels}
    lead = css.get("html[data-embed] .motion-ready [data-motion-item].is-current [data-note]", "")
    assert re.search(r"(^|;)\s*fill:\s*var\(--color-ink\)", lead.strip()), "the note on the current press leads in ink"
    ease = css.get("html[data-embed] .motion-ready [data-motion-item] [data-note]", "")
    assert re.search(r"transition:\s*fill var\(--motion-step\)", ease), "and changes color over the plugin's step time"

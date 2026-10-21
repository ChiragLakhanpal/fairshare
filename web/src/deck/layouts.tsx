// The deck's native slides, in the app's AA tokens, inside the content box the frame (Frame.tsx) leaves them: a statement,
// tiles (a "Possibility" tile carries a chip), the columns of a table or the basic checks, and a live demo with its
// button. The results, agenda and close layouts draw nothing yet. Every string a slide carries goes through fill(), so
// its {placeholders} show the facts' display strings. A demo button hands its demo to onDemo, which the deck answers by
// jumping into the app in its own tab (the notes window's small previews pass none, so their buttons do nothing); the
// dashboard link needs no jump, because it only opens a new tab.
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowUp, Check, ChevronRight, Close, External } from "../components/Icons";
import { copy } from "../copy";
import { api } from "../lib/api";
import { fill, knownTables, type DeckFacts, type Demo, type Jump, type Slide, type Tile } from "../lib/deck";
import { REPORT_URL } from "./slides";

/** The figures' mono face and muted ink (MONO and MUTED in docs/diagrams/src/aa.py). */
export const MONO = "'Geist Mono', ui-monospace, monospace";
export const MUTED = "#5a7181";

// styles.css gives every button `font: inherit`, which outranks Tailwind's text sizes, so a button takes its type from
// its parent (BUTTON_TYPE) and only its box from BUTTON
const BUTTON_TYPE = "text-[19px] font-semibold";
const BUTTON = "press inline-flex items-center gap-2.5 rounded-xl px-6 py-3.5 text-white transition-colors";
const DOT = "h-2 w-2 shrink-0 rounded-full bg-blue";

/** A native slide: the title and the layout, in the frame's content box (x 64 to 1216, y 88 to 664) and centered in its
 * height. A layout taller than the box shrinks to it, and a table then steps its type down until it fits (Tables). */
export function NativeSlide({ slide, facts, onDemo }: { slide: Slide; facts: DeckFacts; onDemo?: (demo: Jump) => void }) {
  const n = slide.native!;
  const f = (t: string) => fill(t, facts);
  return (
    <div className="absolute inset-0 bg-white text-ink">
      <div className="absolute inset-x-[64px] bottom-[56px] top-[88px] flex flex-col justify-center">
        <h1 className="shrink-0 text-[30px] font-semibold leading-[1.15] tracking-[-0.02em]">{f(slide.title)}</h1>
        <div className="mt-8 min-h-0">
          {n.layout === "statement" && <Statement lines={n.lines.map(f)} link={slide.id === "start" ? REPORT_URL : null} />}
          {n.layout === "tiles" && <Tiles tiles={n.tiles.map((t) => ({ ...t, head: f(t.head), body: f(t.body) }))} />}
          {n.layout === "table" && <Tables keys={n.tables} facts={facts} />}
          {n.layout === "checks" && <Tables keys={["checks"]} facts={facts} />}
          {n.layout === "demo" && <DemoLayout demo={n.demo} question={n.demo.kind === "ask" ? f(n.demo.question) : null} lines={n.lines.map(f)} onDemo={onDemo} />}
        </div>
      </div>
    </div>
  );
}

/** Lines said one after another, large, and the report link on the start slide once the report exists. */
function Statement({ lines, link }: { lines: string[]; link: string | null }) {
  return (
    <div className="flex flex-col">
      <ul className="flex max-w-[1120px] flex-col gap-7">
        {lines.map((l) => (
          <li key={l} className="flex gap-5 text-[31px] font-medium leading-[1.28]">
            <span aria-hidden="true" className={`mt-[15px] ${DOT}`} />
            {l}
          </li>
        ))}
      </ul>
      {link && (
        <a href={link} target="_blank" rel="noreferrer" className="mt-10 inline-flex items-center gap-2 self-start text-[21px] font-semibold">
          {copy.deckReport}
          <External width={19} height={19} />
        </a>
      )}
    </div>
  );
}

/** Two or three tiles to a row (four make two rows of two), each a head and a body, with a chip for a possibility. Two
 * tiles get larger type, and a last tile that would leave a gap in a row of three spans two columns. */
function Tiles({ tiles }: { tiles: Tile[] }) {
  const cols = tiles.length === 4 ? 2 : Math.min(tiles.length, 3);
  const big = tiles.length <= 2;
  const widen = cols === 3 && tiles.length % 3 === 2;
  return (
    <div className="grid gap-5" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
      {tiles.map((t, i) => (
        <section key={t.head} className="flex flex-col rounded-xl border border-line px-6 pb-6 pt-5" style={widen && i === tiles.length - 1 ? { gridColumn: "span 2" } : undefined}>
          {t.tag && (
            <span className="mb-3 self-start rounded-full bg-tint px-2.5 py-[3px] text-[11px] font-semibold uppercase tracking-[0.12em] text-navy" style={{ fontFamily: MONO }}>
              {t.tag}
            </span>
          )}
          <h2 className={`${big ? "text-[26px]" : "text-[21px]"} font-semibold leading-snug`}>{t.head}</h2>
          <p className={`${big ? "mt-3 text-[21px]" : "mt-2 text-[17px]"} leading-[1.45] text-ink-2`}>{t.body}</p>
        </section>
      ))}
    </div>
  );
}

const HEAD = "text-[0.68em] font-semibold uppercase tracking-[0.1em] text-ink-2";
// the checks' values are at most "2026-09-01 and 2026-09-01"
const CHECKS = "minmax(0,1fr) 15em 15em 1.4em";

/** Each table's columns in plain words with one example from the data, or the basic checks. More than sixteen rows take
 * two columns. The name and example columns are as wide as the slide's longest name and example need (an example wraps
 * to two lines at most), and the type steps down until every row fits on the slide, again once the fonts arrive. */
function Tables({ keys: named, facts }: { keys: string[]; facts: DeckFacts }) {
  const box = useRef<HTMLDivElement>(null);
  const keys = knownTables(named, facts.columns); // a key facts.json does not describe is skipped, not thrown on
  const columns = keys.filter((k) => k !== "checks").flatMap((k) => facts.columns[k]);
  const rows = columns.length + (keys.includes("checks") ? facts.checks.length : 0);
  const two = rows > 16;
  const longest = (pick: (c: (typeof columns)[number]) => string) => Math.max(0, ...columns.map((c) => pick(c).length));
  const mono = (chars: number) => chars * 0.56 + 0.6; // em for that many mono characters at 0.9em, and a little air
  const template = `${Math.max(7, mono(longest((c) => c.name)))}em minmax(0,1fr) ${Math.min(two ? 8.5 : 16, Math.max(6, mono(longest((c) => c.example))))}em`;
  const [px, setPx] = useState(two ? 14 : 16);
  const [fonts, setFonts] = useState(0);
  useEffect(() => void document.fonts?.ready.then(() => setFonts((n) => n + 1)), []);
  useLayoutEffect(() => {
    const el = box.current;
    if (el && px > 10 && (el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth)) setPx((p) => p - 0.5);
  }, [px, fonts]);
  return (
    <div ref={box} className="h-full overflow-hidden leading-[1.3]" style={{ fontSize: px, columnCount: two ? 2 : 1, columnGap: 48 }}>
      {keys.map((k) => (k === "checks" ? <Checks key={k} checks={facts.checks} /> : <Columns key={k} table={k} columns={facts.columns[k]} template={template} />))}
    </div>
  );
}

function Columns({ table, columns, template }: { table: string; columns: DeckFacts["columns"][string]; template: string }) {
  return (
    <section className="mb-[1.3em]">
      <div style={{ breakInside: "avoid", breakAfter: "avoid" }}>
        <h2 className="mb-[0.45em] text-[0.82em] font-semibold" style={{ fontFamily: MONO, color: MUTED }}>{table}</h2>
        <div className="grid gap-x-[1.1em] pb-[0.3em]" style={{ gridTemplateColumns: template }}>
          <span className={HEAD}>{copy.deckHead.column}</span>
          <span className={HEAD}>{copy.deckHead.meaning}</span>
          <span className={HEAD}>{copy.deckHead.example}</span>
        </div>
      </div>
      {columns.map((c) => (
        <div key={c.name} className="grid gap-x-[1.1em] border-t border-line-2 py-[0.4em]" style={{ gridTemplateColumns: template, breakInside: "avoid" }}>
          <span className="text-[0.9em] font-medium [overflow-wrap:anywhere]" style={{ fontFamily: MONO }}>{c.name}</span>
          <span>{c.meaning}</span>
          <span className="line-clamp-2 self-start text-[0.9em] [overflow-wrap:anywhere]" style={{ fontFamily: MONO, color: MUTED }}>{c.example}</span>
        </div>
      ))}
    </section>
  );
}

function Checks({ checks }: { checks: DeckFacts["checks"] }) {
  const show = (v: unknown) => (typeof v === "number" ? v.toLocaleString("en-US") : String(v));
  return (
    <section>
      <div className="grid gap-x-[1.1em] pb-[0.3em]" style={{ gridTemplateColumns: CHECKS }}>
        <span className={HEAD}>{copy.deckHead.check}</span>
        <span className={HEAD}>{copy.deckHead.expected}</span>
        <span className={HEAD}>{copy.deckHead.actual}</span>
        <span />
      </div>
      {checks.map((c) => (
        <div key={c.name} className="grid items-baseline gap-x-[1.1em] border-t border-line-2 py-[0.6em]" style={{ gridTemplateColumns: CHECKS }}>
          <span>{c.name}</span>
          <span className="text-[0.92em]" style={{ fontFamily: MONO }}>{show(c.expected)}</span>
          <span className="text-[0.92em]" style={{ fontFamily: MONO }}>{show(c.actual)}</span>
          <span className="self-center">
            {c.ok ? <Check width="1.2em" height="1.2em" className="text-blue" /> : <Close width="1.2em" height="1.2em" className="text-red" />}
            <span className="sr-only">{c.ok ? copy.deckPass : copy.deckFail}</span>
          </span>
        </div>
      ))}
    </section>
  );
}

/** A live demo: the Ask question in a box like the app's chat bar, what to watch for, and the button that starts it. */
function DemoLayout({ demo, question, lines, onDemo }: { demo: Demo; question: string | null; lines: string[]; onDemo?: (demo: Jump) => void }) {
  return (
    <div className="flex flex-col">
      {question && (
        <div className="floating mb-9 flex max-w-[980px] items-center gap-4 rounded-[20px] py-4 pl-7 pr-4">
          <span className="min-w-0 flex-1 text-[28px] font-medium">{question}</span>
          <span aria-hidden="true" className="flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-[14px] bg-blue text-white">
            <ArrowUp width={24} height={24} />
          </span>
        </div>
      )}
      <ul className="flex flex-col gap-4">
        {lines.map((l) => (
          <li key={l} className="flex gap-4 text-[25px] leading-[1.35]">
            <span aria-hidden="true" className={`mt-[13px] ${DOT}`} />
            {l}
          </li>
        ))}
      </ul>
      <div className={`mt-10 ${BUTTON_TYPE}`}>
        {demo.kind === "dashboard" ? (
          <DashboardLink />
        ) : (
          <button type="button" onClick={() => onDemo?.(demo.kind)} className={`${BUTTON} bg-blue hover:bg-navy`}>
            {demo.kind === "ask" ? copy.askLive : copy.openPrecall}
            <ChevronRight width={20} height={20} />
          </button>
        )}
      </div>
    </div>
  );
}

/** The sales dashboard, from the link the server gives in /api/me, in a new tab: closing the tab returns to the deck. */
function DashboardLink() {
  const [href, setHref] = useState<string | null>(null);
  useEffect(() => {
    api.me().then((m) => setHref(m.links.dashboard ?? null)).catch(() => setHref(null));
  }, []);
  if (!href) {
    return (
      <button type="button" disabled className={`${BUTTON} cursor-default bg-grey`}>
        {copy.openDashboard}
        <External width={20} height={20} />
      </button>
    );
  }
  return (
    <a href={href} target="_blank" rel="noreferrer" className={`${BUTTON} bg-blue hover:bg-navy`} style={{ color: "#fff", textDecoration: "none" }}>
      {copy.openDashboard}
      <External width={20} height={20} />
    </a>
  );
}

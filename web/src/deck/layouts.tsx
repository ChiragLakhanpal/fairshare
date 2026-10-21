// The deck's native slides, on the type ramp (ramp.ts), inside the content box the frame (Frame.tsx) leaves them: x 64 to 1216 and
// y 88 to 664, centered in its height. A statement is points and then the question to the room in a callout; tiles are two to six boxes,
// a possibility labeled as one; a table lists its tables' columns, each with what it means and an example; the checks are the ones a
// slide names, each with what it guards against, or all of them in a table; results are tests, each with what it tests, who grades it,
// its result and its miss; the agenda is the five topics; the close is its lines; a live demo is its question, its button and what to
// watch for. The title shows on arrival and each item comes in on a press (Step): `step` is how many show, the complete slide by
// default. A layout taller than the space under the title zooms out as a whole until it fits (Fit). Every string a slide carries goes
// through fill(), so its {placeholders} show the facts' display strings. A demo button hands its demo to onDemo, which the deck answers
// by jumping into the app in its own tab (the notes window's small previews pass none, so their buttons do nothing); the dashboard link
// needs no jump, because it only opens a new tab.
import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Check, ChevronRight, Close, External } from "../components/Icons";
import { copy } from "../copy";
import { api } from "../lib/api";
import { fill, knownTables, stepCount, TOPIC_ORDER, TOPICS, type DeckFacts, type Demo, type Jump, type Result, type Slide, type Tile } from "../lib/deck";
import { ACTION, ASK, BLUE_TEXT, BODY, DISPLAY, HEAD, LABEL, MARKER, MISS, MONO_FACE, NOTE, NUMBER, SHOWN, STEP, TABLE, TITLE, UNREACHED } from "./ramp";
import { REPORT_URL } from "./slides";

// styles.css gives every button `font: inherit`, which outranks Tailwind's text sizes, so a button takes its type from its parent
// (ACTION) and only its box from BUTTON
const BUTTON = "press inline-flex items-center gap-2 rounded-xl px-6 py-4 text-white transition-colors";
/** How wide a run of body text may go: about seventy characters at the body's size. */
const MEASURE = "max-w-[1040px]";
/** A tile's or a result's box: a hairline border, blue on the newest one. */
const CARD = "rounded-lg border border-line [&[data-current]]:border-blue";
/** A column name or an example in a table: the figures' mono face, a touch smaller than the sans beside it so the two look one size. */
const MONO_CELL = `${MONO_FACE} text-[0.9em]`;

/** A native slide at a step: the title, and the layout with its first `step` items showing (all of them by default). The slide's root says
 * where it stands, as the diagrams' controller does: data-step-current of data-step-count. */
export function NativeSlide({ slide, facts, onDemo, step }: { slide: Slide; facts: DeckFacts; onDemo?: (demo: Jump) => void; step?: number }) {
  const n = slide.native!;
  const f = (t: string) => fill(t, facts);
  const count = stepCount(slide);
  const at = Math.max(0, Math.min(step ?? count, count));
  return (
    <div data-step-current={at} data-step-count={count} className="absolute inset-0 bg-white text-ink">
      <div className="absolute inset-x-[64px] bottom-[56px] top-[88px] flex flex-col justify-center">
        <h1 className={`shrink-0 ${TITLE}`}>{f(slide.title)}</h1>
        <Fit>
          {n.layout === "statement" && (
            <Statement lines={n.lines.map(f)} ask={n.ask ? f(n.ask) : null} link={slide.id === "start" ? REPORT_URL : null} step={at} />
          )}
          {n.layout === "tiles" && <Tiles tiles={n.tiles.map((t) => ({ ...t, head: f(t.head), body: f(t.body) }))} step={at} />}
          {n.layout === "table" && <Tables keys={n.tables} only={n.columns} facts={facts} step={at} />}
          {n.layout === "checks" && <Checks keys={n.keys} checks={facts.checks} step={at} />}
          {n.layout === "results" && (
            <Results items={n.items.map((r) => ({ head: f(r.head), body: f(r.body), result: f(r.result), miss: r.miss ? f(r.miss) : undefined }))} step={at} />
          )}
          {n.layout === "agenda" && <Agenda step={at} />}
          {n.layout === "close" && <Closing lines={n.lines.map(f)} />}
          {n.layout === "demo" && (
            <DemoLayout demo={n.demo} question={n.demo.kind === "ask" ? f(n.demo.question) : null} lines={n.lines.map(f)} onDemo={onDemo} step={at} />
          )}
        </Fit>
      </div>
    </div>
  );
}

const MIN_ZOOM = 0.4;
const ZOOM_STEP = 0.025;

/** The layout's box under the title. A layout taller than the space left (a dense table, or more than a slide should hold) zooms out as a
 * whole, a step at a time, until it fits, so nothing runs under the footer; a layout that fits stays on the ramp. Items that have not
 * arrived keep their places, so the zoom holds while the slide steps. It starts again from full size once the fonts arrive. The height
 * test compares the two boxes, not scrollHeight: an item waiting 8px low reaches past the box, and scrollHeight counts that. */
function Fit({ children }: { children: ReactNode }) {
  const box = useRef<HTMLDivElement>(null);
  const inner = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [fonts, setFonts] = useState(0);
  useEffect(() => {
    let live = true;
    document.fonts?.ready.then(() => {
      if (!live) return;
      setZoom(1);
      setFonts((k) => k + 1);
    });
    return () => {
      live = false;
    };
  }, []);
  useLayoutEffect(() => {
    const el = box.current;
    const content = inner.current;
    if (!el || !content || zoom <= MIN_ZOOM) return;
    const tall = content.getBoundingClientRect().height > el.getBoundingClientRect().height + 1;
    if (tall || el.scrollWidth > el.clientWidth) setZoom((z) => Math.max(MIN_ZOOM, z - ZOOM_STEP));
  }, [zoom, fonts]);
  return (
    <div ref={box} className="mt-12 min-h-0 overflow-hidden">
      <div ref={inner} style={zoom < 1 ? { zoom } : undefined}>
        {children}
      </div>
    </div>
  );
}

/** An item a press brings in, the n-th of its slide. It is hidden until the slide reaches its step, current on it, and receded once the
 * next one arrives (ramp.ts draws each state). It is drawn all along, so it holds its place while it waits. */
function Step({ n, step, as: Tag = "div", ask, className = "", style, children }: {
  n: number;
  step: number;
  as?: "div" | "li" | "section";
  ask?: boolean;
  className?: string;
  style?: CSSProperties;
  children: ReactNode;
}) {
  const shown = n <= step;
  return (
    <Tag
      data-step={n}
      data-current={n === step ? "" : undefined}
      data-receded={n < step ? "" : undefined}
      data-ask={ask ? "" : undefined}
      aria-hidden={shown ? undefined : true}
      className={`${STEP} ${shown ? SHOWN : UNREACHED} ${className}`}
      style={style}
    >
      {children}
    </Tag>
  );
}

/** A point's marker, a dot centered on its first line: blue on the newest point, muted with its text once the point recedes. */
function Dot() {
  return (
    <span aria-hidden="true" className={`${MARKER} text-blue`}>
      <span className="h-2 w-2 rounded-full bg-current" />
    </span>
  );
}

/** Points said one after another, a press each, and then the question to the room, set apart in a callout. The start slide links the
 * report once it is published. */
function Statement({ lines, ask, link, step }: { lines: string[]; ask: string | null; link: string | null; step: number }) {
  return (
    <div className="flex flex-col">
      <ul className={`flex flex-col gap-6 ${MEASURE}`}>
        {lines.map((l, i) => (
          <Step key={i} n={i + 1} step={step} as="li" className="flex gap-4">
            <Dot />
            <span className={`${BODY} text-pretty`}>{l}</span>
          </Step>
        ))}
      </ul>
      {ask && (
        <Step n={lines.length + 1} step={step} ask className={`mt-12 w-fit border-l-4 border-blue bg-tint px-[28px] py-[20px] ${MEASURE}`}>
          <p className={`${ASK} text-pretty`}>{ask}</p>
        </Step>
      )}
      {link && (
        // blue text in the figures' darker blue; styles.css colors every link outside Tailwind's layers, so only a style outranks it
        <a href={link} target="_blank" rel="noreferrer" className={`mt-12 inline-flex items-center gap-2 self-start ${ACTION}`} style={{ color: BLUE_TEXT }}>
          {copy.deckReport}
          <External width={20} height={20} />
        </a>
      )}
    </div>
  );
}

/** Two to six tiles, a press each, each a head and a note, with its tag above the head when it has one: two or three to a row, four in
 * two rows of two, and a last tile that would leave a gap in a row of three spans two columns. */
function Tiles({ tiles, step }: { tiles: Tile[]; step: number }) {
  const cols = tiles.length === 4 ? 2 : Math.max(1, Math.min(tiles.length, 3));
  const widen = cols === 3 && tiles.length % 3 === 2;
  return (
    <div className="grid gap-6" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
      {tiles.map((t, i) => (
        <Step
          key={i}
          n={i + 1}
          step={step}
          as="section"
          className={`flex flex-col ${CARD} ${cols === 3 ? "p-6" : "p-8"}`}
          style={widen && i === tiles.length - 1 ? { gridColumn: "span 2" } : undefined}
        >
          {t.tag && <p className={`mb-2 ${LABEL}`}>{t.tag}</p>}
          <h2 className={HEAD}>{t.head}</h2>
          <p className={`mt-2 ${NOTE}`}>{t.body}</p>
        </Step>
      ))}
    </div>
  );
}

/** Each table's columns in plain words with one example from the data, a table a press. A slide may keep only some of the columns (only,
 * by name). More than sixteen rows take two columns. The name and example columns are as wide as the slide's longest name and example
 * need, and an example wraps to two lines at most. */
function Tables({ keys: named, only, facts, step }: { keys: string[]; only?: string[]; facts: DeckFacts; step: number }) {
  // a key facts.json does not describe is skipped, not thrown on
  const tables = knownTables(named, facts.columns).map((key) => ({ key, columns: facts.columns[key].filter((c) => !only || only.includes(c.name)) }));
  const all = tables.flatMap((t) => t.columns);
  const two = all.length > 16;
  const longest = (pick: (c: (typeof all)[number]) => string) => Math.max(0, ...all.map((c) => pick(c).length));
  const mono = (chars: number) => chars * 0.56 + 0.6; // em for that many mono characters at 0.9em, and a little air
  const template = `${Math.max(7, mono(longest((c) => c.name)))}em minmax(0,1fr) ${Math.min(two ? 8.5 : 16, Math.max(6, mono(longest((c) => c.example))))}em`;
  return (
    <div className={TABLE} style={{ columnCount: two ? 2 : 1, columnGap: 48 }}>
      {tables.map((t, i) => (
        <Step key={t.key} n={i + 1} step={step} as="section" className="not-last:mb-6">
          <Columns table={t.key} columns={t.columns} template={template} />
        </Step>
      ))}
    </div>
  );
}

/** A table's name (blue while it is the newest), its column headings, and a row for each column. */
function Columns({ table, columns, template }: { table: string; columns: DeckFacts["columns"][string]; template: string }) {
  return (
    <>
      <div style={{ breakInside: "avoid", breakAfter: "avoid" }}>
        <h2 className={`mb-2 ${MONO_CELL} font-semibold text-[#006cbf]`}>{table}</h2>
        <div className="grid gap-x-4 pb-2" style={{ gridTemplateColumns: template }}>
          <span className={LABEL}>{copy.deckHead.column}</span>
          <span className={LABEL}>{copy.deckHead.meaning}</span>
          <span className={LABEL}>{copy.deckHead.example}</span>
        </div>
      </div>
      {columns.map((c) => (
        <div key={c.name} className="grid gap-x-4 border-t border-line-2 py-2" style={{ gridTemplateColumns: template, breakInside: "avoid" }}>
          <span className={`${MONO_CELL} font-medium [overflow-wrap:anywhere]`}>{c.name}</span>
          <span>{c.meaning}</span>
          <span className={`${MONO_CELL} line-clamp-2 self-start [overflow-wrap:anywhere]`}>{c.example}</span>
        </div>
      ))}
    </>
  );
}

/** The checks a slide names, a press each and in its order: what each makes sure of, what it guards against, and whether it passes. With
 * none named, all of them at once, as a table. */
function Checks({ keys, checks, step }: { keys?: string[]; checks: DeckFacts["checks"]; step: number }) {
  if (!keys) return <ChecksTable checks={checks} />;
  const named = keys.flatMap((k) => checks.filter((c) => c.key === k)); // a key facts.json does not hold is skipped, not thrown on
  return (
    <ul className={`flex flex-col gap-6 ${MEASURE}`}>
      {named.map((c, i) => (
        <Step key={c.key} n={i + 1} step={step} as="li" className="flex gap-4">
          <span className={MARKER}>
            <Mark ok={c.ok} />
          </span>
          <div className="min-w-0">
            <p className={HEAD}>{c.name}</p>
            <p className={`mt-2 ${NOTE}`}>{c.why}</p>
          </div>
        </Step>
      ))}
    </ul>
  );
}

// the checks' values are at most "2026-09-01 and 2026-09-01"
const CHECK_COLUMNS = "minmax(0,1fr) 14em 14em 1.4em";

/** Every check at once: what it makes sure of, what it should be, what it is, and whether it passes. */
function ChecksTable({ checks }: { checks: DeckFacts["checks"] }) {
  const show = (v: unknown) => (typeof v === "number" ? v.toLocaleString("en-US") : String(v));
  return (
    <div className={TABLE}>
      <div className="grid gap-x-4 pb-2" style={{ gridTemplateColumns: CHECK_COLUMNS }}>
        <span className={LABEL}>{copy.deckHead.check}</span>
        <span className={LABEL}>{copy.deckHead.expected}</span>
        <span className={LABEL}>{copy.deckHead.actual}</span>
        <span />
      </div>
      {checks.map((c) => (
        <div key={c.key} className="grid items-baseline gap-x-4 border-t border-line-2 py-2" style={{ gridTemplateColumns: CHECK_COLUMNS }}>
          <span>{c.name}</span>
          <span className={MONO_CELL}>{show(c.expected)}</span>
          <span className={MONO_CELL}>{show(c.actual)}</span>
          <span className="self-center">
            <Mark ok={c.ok} />
          </span>
        </div>
      ))}
    </div>
  );
}

/** Whether a check passes: a blue tick, or a red cross for a miss, with the word for a screen reader. */
function Mark({ ok }: { ok: boolean }) {
  return (
    <>
      {ok ? <Check width="1em" height="1em" className="text-blue" /> : <Close width="1em" height="1em" className="text-red" />}
      <span className="sr-only">{ok ? copy.deckPass : copy.deckFail}</span>
    </>
  );
}

/** Tests, a press each, side by side: what each tests and who grades it, its result as a display number, and its miss in red. Each box is
 * a subgrid of three rows, so the parts line up across the boxes: a result sits on the foot of its row, and the numbers share a line
 * even when one wraps. Four make two rows of two. */
function Results({ items, step }: { items: Result[]; step: number }) {
  const cols = items.length === 4 ? 2 : Math.max(1, Math.min(items.length, 3));
  return (
    <div className="grid gap-6" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
      {items.map((r, i) => (
        <Step key={i} n={i + 1} step={step} as="section" className={`row-span-3 grid grid-rows-subgrid gap-y-0 ${CARD} ${cols === 3 ? "p-6" : "p-8"}`}>
          <div>
            <h2 className={HEAD}>{r.head}</h2>
            <p className={`${NOTE} mt-2`}>{r.body}</p>
          </div>
          <p className={`${DISPLAY} mt-8 self-end`}>{r.result}</p>
          {r.miss && <p className={`${MISS} mt-4`}>{r.miss}</p>}
        </Step>
      ))}
    </div>
  );
}

/** The five topics, a press each: the topic's number, its name and its line. */
function Agenda({ step }: { step: number }) {
  return (
    <ol className="flex flex-col gap-6">
      {TOPIC_ORDER.map((t, i) => (
        <Step key={t} n={i + 1} step={step} as="li" className="flex gap-6">
          <span aria-hidden="true" className={`w-6 shrink-0 ${NUMBER}`}>
            {i + 1}
          </span>
          <div className="min-w-0">
            <p className={HEAD}>{TOPICS[t].name}</p>
            <p className={NOTE}>{TOPICS[t].line}</p>
          </div>
        </Step>
      ))}
    </ol>
  );
}

/** The close: its lines, all at once. */
function Closing({ lines }: { lines: string[] }) {
  return (
    <div className="flex flex-col gap-2">
      {lines.map((l, i) => (
        <p key={i} className={BODY}>
          {l}
        </p>
      ))}
    </div>
  );
}

/** A live demo: the Ask question in a box like the app's chat bar, with the button that asks it in the place of the app's send button, or
 * the button alone; then what to watch for, a press a line. The button shows from the start. */
function DemoLayout({ demo, question, lines, onDemo, step }: {
  demo: Demo;
  question: string | null;
  lines: string[];
  onDemo?: (demo: Jump) => void;
  step: number;
}) {
  const action = (
    <span className={`shrink-0 ${ACTION}`}>
      {demo.kind === "dashboard" ? (
        <DashboardLink />
      ) : (
        <button type="button" onClick={() => onDemo?.(demo.kind)} className={`${BUTTON} bg-blue hover:bg-navy`}>
          {demo.kind === "ask" ? copy.askLive : copy.openPrecall}
          <ChevronRight width={20} height={20} />
        </button>
      )}
    </span>
  );
  return (
    <div className="flex flex-col">
      {question ? (
        <div className={`flex items-center gap-6 rounded-[20px] border border-line bg-white py-2 pl-8 pr-2 ${MEASURE}`}>
          <span className={`min-w-0 flex-1 ${BODY}`}>{question}</span>
          {action}
        </div>
      ) : (
        <div className="self-start">{action}</div>
      )}
      <ul className="mt-12 flex flex-col gap-6">
        {lines.map((l, i) => (
          <Step key={i} n={i + 1} step={step} as="li" className="flex gap-4">
            <Dot />
            <span className={`${BODY} text-pretty`}>{l}</span>
          </Step>
        ))}
      </ul>
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

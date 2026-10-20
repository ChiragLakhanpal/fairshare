import * as Tooltip from "@radix-ui/react-tooltip";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { AgencyPicker } from "./components/AgencyPicker";
import { BriefPage } from "./components/BriefPage";
import { Conversation } from "./components/Conversation";
import { DefinitionWindow } from "./components/DefinitionWindow";
import { Delegate } from "./components/Delegate";
import { FloatingBar } from "./components/FloatingBar";
import { HowItWorks } from "./components/HowItWorks";
import { ChevronLeft } from "./components/Icons";
import { Present } from "./components/Present";
import { Sidebar, type QuickAction } from "./components/Sidebar";
import { Summary } from "./components/Summary";
import { SummaryStrip } from "./components/SummaryStrip";
import { TopBar } from "./components/TopBar";
import { copy } from "./copy";
import { api, ask, lastAnswerOf } from "./lib/api";
import { KEYS } from "./lib/deck";
import { monthLabel } from "./lib/format";
import { SPRING, slideDirection, slideVariants } from "./lib/motion";
import { chipsFrom } from "./lib/signals";
import { store, useStore } from "./lib/store";
import type { Agency, AgentsCatalog, Brief as BriefT, Me, Mover, Scope, SignalAction, Signals, Summary as SummaryT, Turn } from "./lib/types";

function scopeFromUrl(): Scope {
  const u = new URL(location.href);
  return { region: u.searchParams.get("region") || "All", month: u.searchParams.get("month") || "" };
}

// The slide the deck left to open the app, while its way back is set. Blocked storage keeps nothing, and then there is none.
function deckReturn(): string | null {
  try {
    return sessionStorage.getItem(KEYS.ret);
  } catch {
    return null;
  }
}
function clearDeckReturn(): void {
  try {
    sessionStorage.removeItem(KEYS.ret);
  } catch {
    // the deck clears it when it opens again
  }
}

export function App() {
  const path = location.pathname;
  if (path === "/present") return <Present />;
  if (path.startsWith("/brief/")) return <BriefPage runId={path.slice("/brief/".length)} />;
  return <Main />;
}

function Main() {
  const reduced = useReducedMotion();
  const [me, setMe] = useState<Me | null>(null);
  const [scope, setScopeState] = useState<Scope>(scopeFromUrl);
  const [summary, setSummary] = useState<SummaryT | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [signals, setSignals] = useState<Signals | null>(null);
  const [how, setHow] = useState(false);
  const [picker, setPicker] = useState<null | "call" | "agreement">(null);
  const [kpi, setKpi] = useState<string | null>(null);
  const [prefill, setPrefill] = useState<{ text: string; n: number } | undefined>();
  const [busy, setBusy] = useState(false);
  const [barHeight, setBarHeight] = useState(0);
  const [catalog, setCatalog] = useState<AgentsCatalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [fromDeck] = useState(deckReturn); // read once: the deck's jump is a full page load
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const conversations = useStore((s) => s.conversations);
  const activeId = useStore((s) => s.activeId);
  const summaryExpanded = useStore((s) => s.summaryExpanded);
  const collapsed = useStore((s) => s.sidebarCollapsed);
  const mode = useStore((s) => s.mode);
  const delegateView = useStore((s) => s.delegate);
  const active = conversations.find((c) => c.id === activeId) ?? null;

  // The agents with their pages: loaded when Delegate opens, refreshed after a run starts or a decision lands, and
  // polled every two seconds while any agent is running, so the sidebar's dot pulses even from Ask.
  const loadDelegate = useCallback(
    () => api.agents().then((c) => { setCatalog(c); setCatalogError(null); }).catch((e) => setCatalogError(e.message ?? "The agents did not load.")),
    [],
  );
  useEffect(() => {
    void loadDelegate(); // once at the start too: the home page says how many pages wait for a decision
  }, [loadDelegate]);
  useEffect(() => {
    if (mode === "delegate" && !catalog) void loadDelegate();
  }, [mode, catalog, loadDelegate]);
  const waiting = catalog?.agents.reduce((n, a) => n + a.waiting, 0) ?? 0;
  const anyRunning = !!catalog?.agents.some((a) => a.running);
  useEffect(() => {
    if (!anyRunning) return;
    const id = setInterval(() => void loadDelegate(), 2000);
    return () => clearInterval(id);
  }, [anyRunning, loadDelegate]);

  const setScope = useCallback((s: Scope) => {
    setScopeState(s);
    const u = new URL(location.href);
    u.searchParams.set("region", s.region);
    u.searchParams.set("month", s.month);
    history.replaceState(null, "", u);
  }, []);

  // The deck's "Ask it live" opens /?q=<question>: the question goes into the box once, and the URL is clean again. The timer
  // is not cleared on cleanup: StrictMode runs this effect twice in development, and the second run finds no q.
  useEffect(() => {
    const u = new URL(location.href);
    const q = u.searchParams.get("q");
    if (!q) return;
    setPrefill({ text: q, n: Date.now() });
    u.searchParams.delete("q");
    history.replaceState(null, "", u);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, []);

  useEffect(() => {
    api.me().then((m) => {
      setMe(m);
      if (!scope.month || !m.months.includes(scope.month)) setScope({ region: m.regions.includes(scope.region) ? scope.region : "All", month: m.data_through });
    }).catch((e) => setSummaryError(e.message ?? "The server did not answer."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!me || !scope.month) return;
    let gone = false;
    setSummaryLoading(true);
    setSummaryError(null);
    api.summary(scope).then((s) => !gone && setSummary(s)).catch((e) => !gone && setSummaryError(e.message ?? "The summary did not load.")).finally(() => !gone && setSummaryLoading(false));
    return () => {
      gone = true;
    };
  }, [me, scope]);

  // What is worth knowing this month, loaded beside the summary so the five numbers never wait for it; a failure shows no
  // block. The old lines stay until the new ones arrive (the summary shows them only when they belong to its month).
  useEffect(() => {
    if (!me || !scope.month) return;
    let gone = false;
    api.signals(scope).then((s) => !gone && setSignals(s)).catch(() => !gone && setSignals(null));
    return () => {
      gone = true;
    };
  }, [me, scope]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const typing = (document.activeElement?.tagName ?? "") in { INPUT: 1, TEXTAREA: 1, SELECT: 1 };
      const windowOpen = !!document.querySelector('[role="dialog"]');
      if (e.key === "Escape" && !windowOpen && activeId && store.get().summaryExpanded) store.setSummaryExpanded(false);
      if (e.key === "/" && !typing && store.get().mode === "ask") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [activeId]);

  const patch = (id: string, idx: number, p: Partial<Turn> | ((t: Turn) => Partial<Turn>)) => {
    const t = store.get().conversations.find((c) => c.id === id)?.turns[idx];
    if (t) store.patchTurn(id, idx, typeof p === "function" ? p(t) : p);
  };

  const send = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    const current = store.get().conversations.find((c) => c.id === store.get().activeId) ?? null;
    const history = (current?.turns ?? []).filter((t) => t.text && !t.pending && !t.error).slice(-6).map((t) => ({ role: t.role, text: t.role === "assistant" ? t.answer?.verified_text || t.text : t.text }));
    const last_answer = lastAnswerOf([...(current?.turns ?? [])].reverse().find((t) => t.role === "assistant" && t.answer)?.answer);
    const id = current ? current.id : store.startConversation(q, scope);
    if (current) store.addTurn(id, { role: "user", text: q, at: Date.now() });
    const idx = store.get().conversations.find((c) => c.id === id)!.turns.length;
    store.addTurn(id, { role: "assistant", text: "", at: Date.now(), pending: true, steps: [] });
    const ac = new AbortController();
    abortRef.current = ac;
    setBusy(true);
    try {
      await ask({ question: q, history, genie_conversation_id: current?.genieConversationId ?? null, scope, last_answer }, {
        onStep: (s) => patch(id, idx, (t) => ({ steps: [...(t.steps ?? []), { ...s, at: Date.now() }] })),
        onAnswer: (a) => {
          patch(id, idx, { pending: false, answer: a, text: a.verified_text || a.text, fresh: true });
          if (a.genie_conversation_id) store.setGenieConversation(id, a.genie_conversation_id);
        },
        onError: (e) => patch(id, idx, { pending: false, error: e }),
      }, ac.signal);
      patch(id, idx, (t) => (t.pending ? { pending: false, error: { code: "network", message: "The stream ended early." } } : {}));
    } catch (e) {
      patch(id, idx, { pending: false, error: ac.signal.aborted ? { code: "cancelled", message: copy.stopped } : { code: "network", message: (e as Error).message } });
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  const sendBrief = async () => {
    if (busy) return;
    const id = store.startConversation(copy.actionBrief + ".", scope);
    store.addTurn(id, { role: "assistant", text: "", at: Date.now(), pending: true, steps: [{ phase: "model", text: "I am writing the brief from this month's queries.", t_ms: 0, at: Date.now() }] });
    setBusy(true);
    try {
      const b = await api.brief(scope);
      patch(id, 1, { pending: false, brief: b, text: b.verified_text, fresh: true });
    } catch (e) {
      patch(id, 1, { pending: false, error: { code: "network", message: (e as Error).message } });
    } finally {
      setBusy(false);
    }
  };

  const onAction = (a: QuickAction) => {
    if (a === "summary") {
      if (activeId) store.setSummaryExpanded(true);
      else store.newChat();
      window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
    } else if (a === "brief") void sendBrief();
    else setPicker(a);
  };
  const onPick = (agency: Agency) => {
    const kind = picker;
    setPicker(null);
    if (kind === "call") void send(copy.callPrep(agency.agency_name));
    else {
      setPrefill({ text: copy.agreementPrefix(agency.agency_name), n: Date.now() });
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };
  const onWhy = (m: Mover) => void send(`Why is ${m.agency} ${m.share_chg_pts < 0 ? "down" : "up"} in ${monthLabel(scope.month)}?`);
  const onApproved = (index: number, b: BriefT) => active && patch(active.id, index, { brief: b });
  const onTyped = (index: number) => active && patch(active.id, index, { fresh: false });
  const openDelegate = (agent: string | null) => {
    store.setDelegate({ agent, runId: null, itemId: null });
    store.setMode("delegate");
  };
  // a "worth knowing" line's one action: ask its question, open the agent whose pages hold it, or open a definition
  const onSignal = (a: SignalAction) => {
    if (a.kind === "ask") void send(a.question);
    else if (a.kind === "delegate") openDelegate(a.agent);
    else setKpi(a.kpi);
  };
  // the suggestion chips follow the month's signals while a model is connected; without one, the three recorded answers
  const chips = me && me.model !== "none" ? chipsFrom(signals?.signals, copy.chips) : copy.chips;

  const summaryBlock = (
    <div className="mx-auto w-full max-w-[760px] px-6 pb-2 pt-9">
      <Summary summary={summary} loading={summaryLoading} error={summaryError} name={me?.name ?? null} onWhy={onWhy} onAsk={(q) => void send(q)}
        signals={signals} waiting={waiting} onAction={onSignal} onOpenDelegate={() => openDelegate(null)} />
    </div>
  );

  return (
    <Tooltip.Provider delayDuration={200}>
      <div className="flex min-h-screen">
        <motion.div className="sticky top-0 h-screen shrink-0 overflow-hidden" animate={{ width: collapsed ? 56 : 256 }} transition={reduced ? { duration: 0 } : SPRING} initial={false}>
          <Sidebar collapsed={collapsed} onToggle={() => store.setSidebarCollapsed(!collapsed)} conversations={conversations} activeId={activeId}
            onSelect={(id) => store.setActive(id)} onRemove={(id) => store.remove(id)} onNew={() => store.newChat()} onAction={onAction} email={me?.email ?? null} inSummary={!activeId || summaryExpanded}
            mode={mode} onMode={(m) => store.setMode(m)} agents={catalog?.agents ?? []} view={delegateView.agent}
            onOverview={() => { store.setDelegate({ agent: null, runId: null, itemId: null }); store.setMode("delegate"); }}
            onAgent={(k) => { store.setDelegate({ agent: k, runId: null, itemId: null }); store.setMode("delegate"); }} />
        </motion.div>
        <section className="flex min-w-0 flex-1 flex-col">
          <TopBar me={me} scope={scope} onScope={setScope} />
          {/* The two modes trade places along a takeoff diagonal: Delegate arrives from the right, Ask from the left. */}
          <AnimatePresence mode="wait" initial={false} custom={slideDirection(mode)}>
          {mode === "delegate" ? (
            <motion.div key="delegate" custom={1} variants={slideVariants(reduced)} initial="initial" animate="animate" exit="exit" className="flex-1">
              <Delegate catalog={catalog} catalogError={catalogError} scope={scope} onRefresh={loadDelegate} />
            </motion.div>
          ) : (
            <motion.div key="ask" custom={-1} variants={slideVariants(reduced)} initial="initial" animate="animate" exit="exit" className="flex min-w-0 flex-1 flex-col">
              {active && <SummaryStrip summary={summary} expanded={summaryExpanded} onToggle={() => store.setSummaryExpanded(!summaryExpanded)} />}
              <div className="flex-1" style={{ paddingBottom: barHeight ? barHeight + 16 : active ? 144 : 280 }}>
                {active ? (
                  <>
                    <AnimatePresence initial={false}>
                      {summaryExpanded && (
                        <motion.div key="summary" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={reduced ? { duration: 0.15 } : SPRING} style={{ overflow: "hidden" }}>
                          {summaryBlock}
                          <div className="mx-auto max-w-[760px] px-6"><div className="border-b border-line" /></div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                    <Conversation c={active} onFollowUp={(q) => void send(q)} onHow={() => setHow(true)} onApproved={onApproved} onTyped={onTyped} signals={signals} onAction={onSignal} />
                  </>
                ) : (
                  summaryBlock
                )}
              </div>
              <FloatingBar ref={inputRef} busy={busy} showChips={!active} chips={chips} followUp={!!active} onSend={(q) => void send(q)} onStop={() => abortRef.current?.abort()} onHow={() => setHow(true)} prefill={prefill} onHeight={setBarHeight} />
            </motion.div>
          )}
          </AnimatePresence>
        </section>
      </div>
      <HowItWorks open={how} onOpenChange={setHow} me={me} />
      <AgencyPicker open={picker !== null} onOpenChange={(o) => !o && setPicker(null)} onPick={onPick} title={copy.pickAgency} />
      <DefinitionWindow kpi={kpi} onClose={() => setKpi(null)} />
      <KpiBridge onOpen={setKpi} />
      <Toast />
      {fromDeck && (
        <a href={`/present#${fromDeck}`} onClick={clearDeckReturn} className="floating no-print press fixed bottom-5 right-5 z-20 inline-flex items-center gap-1.5 rounded-full py-2 pl-3 pr-4 text-[13.5px] font-medium !text-ink hover:!text-blue hover:!no-underline">
          <ChevronLeft width={15} height={15} />{copy.backToDeck}
        </a>
      )}
    </Tooltip.Provider>
  );
}

// Copy buttons anywhere raise a custom event; one small pill above the bar shows the message for a moment.
function Toast() {
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    let timer: number | undefined;
    const h = (e: Event) => {
      const d = (e as CustomEvent<string | { message: string; ms?: number }>).detail;
      setMsg(typeof d === "string" ? d : d.message);
      clearTimeout(timer);
      timer = window.setTimeout(() => setMsg(null), typeof d === "string" ? 1800 : d.ms ?? 1800);
    };
    window.addEventListener("fairshare:toast", h);
    return () => {
      window.removeEventListener("fairshare:toast", h);
      clearTimeout(timer);
    };
  }, []);
  return (
    <AnimatePresence>
      {msg && (
        <motion.div role="status" initial={{ opacity: 0, y: 8, x: "-50%" }} animate={{ opacity: 1, y: 0, x: "-50%" }} exit={{ opacity: 0, y: 8, x: "-50%" }} transition={{ duration: 0.18 }}
          className="fixed bottom-28 left-1/2 z-30 rounded-full bg-ink px-4 py-2 text-[13.5px] font-medium text-white shadow-lg">{msg}</motion.div>
      )}
    </AnimatePresence>
  );
}

// Term buttons live deep in Summary; a click bubbles a custom event up so the one definition window can open.
function KpiBridge({ onOpen }: { onOpen: (k: string) => void }) {
  useEffect(() => {
    const h = (e: Event) => onOpen((e as CustomEvent<string>).detail);
    window.addEventListener("fairshare:kpi", h);
    return () => window.removeEventListener("fairshare:kpi", h);
  }, [onOpen]);
  return null;
}

/**
 * Airliner: a narrow-body twin in flight over its spot on the ground: a round
 * fuselage with a nose cone and a raised tail cone, low swept wings with an
 * engine under each, a fin and two tailplanes, a row of windows on the near
 * side. The pointer's place left or right of the aircraft banks it toward the
 * pointer and its height pitches the nose, each on a spring, about a centre
 * that never moves; the wing on the pointer's side takes the bright edge. At
 * rest it climbs in a shallow right turn with the fin bright. The slider is
 * the most it banks.
 */
const {
  Cam, clamp, fit, flatDot, hull, open, poly, proj, rad, seg,
  spring, stepS, disposer, mk, place, pointer, put, register, solid,
} = HL;

const ALT = 50, PMAX = 8, DX0 = 0.3, DY0 = 0.35;
// body frame: X forward, Y to the left, Z up. Fuselage stations: [X, radius, centre height]
const STA = [[60, 0.8, -0.6], [57, 2.8, -0.4], [52, 4.8, 0], [46, 6, 0], [-36, 6, 0], [-48, 4.2, 1.6], [-60, 1.4, 3.4]];
const ring = (X, r, zc, n = 14) => Array.from({ length: n }, (_, k) => [X, r * Math.cos((2 * Math.PI * k) / n), zc + r * Math.sin((2 * Math.PI * k) / n)]);
const WING = (s) => [[2, 6 * s, -2.5], [-20, 58 * s, -1], [-28, 58 * s, -1], [-24, 6 * s, -2.5]];
const TAIL = (s) => [[-50, 2 * s, 2.5], [-58, 20 * s, 3.5], [-62, 20 * s, 3.5], [-60, 2 * s, 2.5]];
const FIN = [[-38, 0, 6], [-53, 0, 30], [-61, 0, 30], [-58, 0, 6]];

/** A convex outline in two of its three coordinates moved in by b, the third carried along: the plate's crease. */
function inset(pts, b, i = 0, j = 1) {
  const c = pts.reduce((a, p) => [a[0] + p[i] / pts.length, a[1] + p[j] / pts.length], [0, 0]);
  return pts.map((p) => {
    const d = Math.hypot(p[i] - c[0], p[j] - c[1]), k = (d - b * 1.6) / d, q = p.slice();
    q[i] = c[0] + (p[i] - c[0]) * k; q[j] = c[1] + (p[j] - c[1]) * k;
    return q;
  });
}

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let bmax = clamp(value, 6, 34);
  const sp = { b: spring(rad(DX0 * bmax)), p: spring(rad(DY0 * PMAX)) };

  // the attitude: pitch about Y, then bank about X; body to world puts the nose to the upper right
  const turn = ([X, Y, Z], b, p) => {
    const X1 = X * Math.cos(p) - Z * Math.sin(p), Z1 = X * Math.sin(p) + Z * Math.cos(p);
    return [-(Y * Math.cos(b) - Z1 * Math.sin(b)), -X1, Z1 * Math.cos(b) + Y * Math.sin(b) + ALT];
  };
  const C = Cam(45, 0.5, 2.5);
  const tips = [[60, 0, 0], [-62, 0, 30], [-24, 58, -1], [-24, -58, -1], [-60, 0, 3], [10, 21, -10.4], [10, -21, -10.4]];
  const ext = [[0, 0, 0]];
  for (const b of [-34, 34]) for (const p of [-PMAX, PMAX]) for (const t of tips) ext.push(turn(t, rad(b), rad(p)));
  fit(C, ext, 200, 166);
  const P = proj(C), T = (pt) => P(...turn(pt, sp.b.x, sp.p.x));

  const g = mk("g", {}, svg);
  mk("path", { class: "dash nf", d: seg(P(0, 0, 0), P(0, 0, ALT - 8)) }, g);
  place(flatDot(g, C, 1.4, "dot off"), P(0, 0, 0));

  const plate = (pts, t, axis) => ({ pts, back: pts.map((q) => q.map((v, k) => (k === axis ? v - t : v))), crease: inset(pts, 0.7, 0, axis === 2 ? 1 : 2) });
  const engine = (s) => ({ eng: true, s, a: ring(12, 3.4, -7, 12).map((q) => [q[0], q[1] + 21 * s, q[2]]), z: ring(-4, 3.4, -7, 12).map((q) => [q[0], q[1] + 21 * s, q[2]]) });
  // painted back to front: the far (left) side, the fuselage and fin, then the near (right) side
  const parts = [
    { key: "left", ...engine(1) }, { key: "left", ...plate(WING(1), 1.2, 2) }, { key: "tl", ...plate(TAIL(1), 0.8, 2) },
    { key: "body" }, { key: "fin", ...plate(FIN.map((q) => [q[0], q[1] - 0.6, q[2]]), -1.2, 1) },
    { key: "right", ...engine(-1) }, { key: "right", ...plate(WING(-1), 1.2, 2) }, { key: "tr", ...plate(TAIL(-1), 0.8, 2) },
  ].map((p) => ({ ...p, el: solid(g) }));
  const body = parts.find((p) => p.key === "body");
  const exhaust = parts.filter((p) => p.eng).map((p) => { const disc = mk("path", {}, p.el.g); return { p, disc, nozzle: mk("path", { class: "nf lo" }, p.el.g) }; });
  const windows = [];
  for (let X = -32; X <= 42; X += 4) windows.push([X, -5.8, 1.6]);
  windows.push([51, -4.2, 2.2], [53, -3.6, 2.0]);
  const dots = windows.map(() => mk("circle", { r: 0.95, class: "dot m" }, body.el.g));
  const belly = mk("path", { class: "nf lo" }, body.el.g);

  let drawn = "";
  function draw() {
    const key = sp.b.x.toFixed(4) + sp.p.x.toFixed(4);
    if (key === drawn) return;
    drawn = key;
    for (const p of parts) {
      if (p.key === "body") put(p.el, { sil: poly(hull(STA.flatMap(([X, r, zc]) => ring(X, r, zc)).map(T))), crease: "" });
      else if (p.eng) put(p.el, { sil: poly(hull(p.a.concat(p.z).map(T))), crease: "" });
      else put(p.el, { sil: poly(hull(p.pts.concat(p.back).map(T))), crease: poly(p.crease.map(T)) });
    }
    for (const e of exhaust) {
      e.disc.setAttribute("d", poly(e.p.z.map(T)));
      e.nozzle.setAttribute("d", poly(e.p.z.map((q) => [q[0], (q[1] - 21 * e.p.s) * 0.5 + 21 * e.p.s, (q[2] + 7) * 0.5 - 7]).map(T)));
    }
    belly.setAttribute("d", open([-36, -20, 0, 20, 46].map((X) => T([X, -5.4, -2.6]))));
    dots.forEach((el, k) => place(el, T(windows[k])));
  }

  const L = register(stage, (dt) => { const m = stepS(sp.b, dt) | stepS(sp.p, dt); draw(); return !!m; });
  bag.add(L.unregister);

  let cur = [DX0, DY0, "rest"];
  function aim(dx, dy, label) {
    cur = [dx, dy, label];
    sp.b.t = rad(dx * bmax);
    sp.p.t = rad(dy * PMAX);
    const lit = label === "rest" ? "fin" : dx > 0.15 ? "right" : dx < -0.15 ? "left" : "fin";
    parts.forEach((p) => p.el.sil.classList.toggle("hi", p.key === lit && !p.eng));
    read.textContent = label ?? `bank ${Math.round(Math.abs(dx * bmax))}°`;
    L.wake();
  }
  aim(...cur);

  bag.add(pointer(stage, {
    move: (pt) => aim(clamp((pt[0] - 200) / 160, -1, 1), clamp((166 - pt[1]) / 130, -1, 1)),
    leave: () => aim(DX0, DY0, "rest"),
  }));
  bag.add(() => svg.replaceChildren());

  return { set: (v) => { bmax = clamp(v, 6, 34); aim(...cur); }, destroy: bag.dispose };
}

hairline({
  name: "airliner",
  means: "A narrow-body airliner in flight: it banks toward the pointer and pitches its nose with the pointer's height.",
  rules: [3, 4, 5, 8],
  range: [10, 20, 34],
  tour: [[80, 150], [320, 120], [200, 240], null],
  mount,
});

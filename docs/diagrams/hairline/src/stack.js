/**
 * Stack: fairshare in five plates, in the exploded diagram's order: data at
 * the base, then definitions, agents, checks, and the app on top. The
 * pointer's height picks a plate from static bands along the plates' resting
 * front corners; the plates above it lift away on the 700ms curve, staggered
 * outwards from it, and it rises clear with the bright edge. At rest the app
 * sits a little higher, so the checks plate shows its mesh and holds the
 * bright edge. Each plate carries what it holds: tables, two matching cards,
 * a chip with four agents, a sieve, a screen with a chat bar. The slider is
 * the gap the plates above open.
 */
const {
  Cam, clamp, facing, fit, poly, prism, proj, ringAt, rings, rrect, seg,
  tdone, tset, tval, tween, disposer, flatDot, mk, place, pointer, put, register, solid,
} = HL;

const W = 80, R = 9, T = 5, B = 1.6, SELF = 0.25, STEP = 30, GMAX = 50;  // a 30ms step keeps every plate clear of the one above while both rise
const REST = [0, 15, 30, 45, 66], NAMES = ["data", "definitions", "agents", "checks", "app"], FOCAL = 3;

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let gap = clamp(value, 10, GMAX);
  const top = REST[4] + T + GMAX;
  const C = Cam(45, 0.5, 1.7);
  fit(C, [[0, 0, 0], [W, W, 0], [W, 0, 0], [0, W, 0], [0, 0, top], [W, W, top], [W, 0, top], [0, W, top]], 200, 166);
  const P = proj(C), front = facing(C);
  const [ring, inner] = rings(0, 0, W, W, R, B);
  const g = mk("g", {}, svg);

  // what each plate holds, as parts drawn at the plate's top height zt; made back to front
  function block(grp, x0, y0, x1, y1, r, b, h) {
    const [rg, inr] = rings(x0, y0, x1, y1, r, b), el = solid(grp);
    return (zt) => put(el, prism(P, front, rg, inr, zt, zt + h));
  }
  function lines(grp, cls, list) {
    const el = mk("path", { class: cls }, grp);
    return (zt) => el.setAttribute("d", list.map(([a, b, c, d, z]) => seg(P(a, b, zt + z), P(c, d, zt + z))).join(""));
  }
  function outline(grp, cls, x0, y0, x1, y1, r, z) {
    const el = mk("path", { class: cls }, grp), rr = rrect(x0, y0, x1, y1, r, 5);
    return (zt) => el.setAttribute("d", poly(ringAt(P, rr, zt + z)));
  }
  function dots(grp, cls, pts) {
    const els = pts.map(() => flatDot(grp, C, 1.25, cls));
    return (zt) => els.forEach((el, k) => place(el, P(pts[k][0], pts[k][1], zt)));
  }
  const at = [20, 40, 60], mesh = [15, 25, 35, 45, 55, 65];
  const HOLD = [
    (grp) => [outline(grp, "nf lo", 6, 6, W - 6, W - 6, R - 4, 0),
      ...at.flatMap((y) => at.map((x) => [x, y])).sort((p, q) => p[0] + p[1] - q[0] - q[1]).map(([x, y]) => block(grp, x - 7, y - 7, x + 7, y + 7, 7, 1.2, 5))],
    (grp) => [block(grp, 10, 10, 44, 70, 2, 1, 1.5), lines(grp, "nf lo", [0, 1, 2, 3, 4, 5, 6].map((k) => [15 + k * 4.4, 15, 15 + k * 4.4, 15 + [44, 36, 50, 30, 46, 40, 34][k], 1.5])),
      block(grp, 52, 18, 72, 62, 2, 1, 1.5), lines(grp, "nf lo", [0, 1, 2, 3, 4, 5, 6].map((k) => [55 + k * 2.3, 22, 55 + k * 2.3, 22 + [30, 24, 34, 20, 31, 27, 23][k], 1.5]))],
    (grp) => [block(grp, 34, 6, 46, 20, 2, 0.8, 1.5), block(grp, 6, 34, 20, 46, 2, 0.8, 1.5),
      lines(grp, "nf lo", [[40, 20, 40, 30, 0], [20, 40, 30, 40, 0], [50, 40, 60, 40, 0], [40, 50, 40, 60, 0]]),
      block(grp, 30, 30, 50, 50, 3, 1, 4), block(grp, 60, 34, 74, 46, 2, 0.8, 1.5), block(grp, 34, 60, 46, 74, 2, 0.8, 1.5)],
    (grp) => [outline(grp, "nf", 8, 8, W - 8, W - 8, R - 3, 0), dots(grp, "dot m", mesh.flatMap((y) => mesh.map((x) => [x, y])))],
    (grp) => [outline(grp, "nf", 7, 7, W - 7, W - 7, R - 3, 0), outline(grp, "nf lo", 12, 14, 16, 50, 1.5, 0),
      lines(grp, "nf lo", [[22, 14, 22, 58, 0], [27, 14, 27, 50, 0], [32, 14, 32, 64, 0]]),
      outline(grp, "nf", 40, 14, 48, 24, 2, 0), outline(grp, "nf", 40, 28, 48, 38, 2, 0), outline(grp, "nf", 40, 42, 48, 52, 2, 0),
      outline(grp, "nf", 60, 12, 67, 68, 3.5, 0)],
  ];
  const plates = NAMES.map((name, i) => {
    const grp = mk("g", {}, g), body = solid(grp);
    return { i, body, hold: HOLD[i](grp), z: tween(REST[i]), drawn: NaN };
  });

  function draw(p, z) {
    if (z === p.drawn) return;
    p.drawn = z;
    put(p.body, prism(P, front, ring, inner, z, z + T));
    p.hold.forEach((d) => d(z + T));
  }

  // hit bands: the plates' RESTING front corners, at mid thickness. They never move.
  const band = REST.map((z) => P(W, W, z + T / 2)[1]);
  const xl = P(0, W, 0)[0] - 8, xr = P(W, 0, 0)[0] + 8, yt = P(0, 0, REST[4] + T)[1] - 10, yb = P(W, W, 0)[1] + 10;
  function hit([x, y]) {
    if (x < xl || x > xr || y < yt || y > yb) return -1;
    let best = 0;
    band.forEach((b, i) => { if (Math.abs(y - b) < Math.abs(y - band[best])) best = i; });
    return best;
  }

  const L = register(stage, (_dt, now) => {
    let moving = false;
    for (const p of plates) { draw(p, tval(p.z, now)); if (!tdone(p.z, now)) moving = true; }
    return moving;
  });
  bag.add(L.unregister);

  let act = -2;
  function choose(a) {
    if (a === act) return;
    const now = performance.now(), from = a >= 0 ? a : Math.max(act, 0);
    act = a;
    for (const p of plates) {
      const lift = a < 0 ? 0 : p.i > a ? gap : p.i === a ? gap * SELF : 0;
      tset(p.z, REST[p.i] + lift, now, Math.abs(p.i - from) * STEP);
      p.body.sil.classList.toggle("hi", a < 0 ? p.i === FOCAL : p.i === a);
    }
    read.textContent = a < 0 ? "rest" : NAMES[a];
    L.wake();
  }
  choose(-1);

  bag.add(pointer(stage, { move: (pt) => choose(hit(pt)), leave: () => choose(-1) }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { gap = clamp(v, 10, GMAX); const a = act; act = -2; choose(a); },
    destroy: bag.dispose,
  };
}

hairline({
  name: "stack",
  means: "fairshare in five plates, data at the base and the app on top: point at a height and that layer lifts clear.",
  rules: [1, 2, 4, 5],
  range: [18, 34, 50],
  tour: [[200, 299], [200, 255], [200, 233], null],
  mount,
});

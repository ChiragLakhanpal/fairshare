/**
 * Seats: a cabin seat map, seven rows of three-and-three on a capsule floor,
 * a bulkhead at the nose and an aisle down the middle, seen from behind the
 * last row. The pointer is projected onto the floor, which never moves, and
 * its place along the aisle sets a share: the seats from the nose back to it
 * lift, one after another, staggered outwards from the pointer. The read-out
 * is the share of seats raised. At rest about two rows and a half are up and
 * the last raised seat holds the bright edge. The slider is the lift.
 */
const {
  Cam, clamp, facing, fit, prism, proj, rings, rrect, unproj,
  tdone, tset, tval, tween, disposer, mk, pointer, put, register, solid,
} = HL;

const ROWS = 7, PITCH = 11, PAN = 7, BACK = 2, SW = 7, COLS = [4, 12, 20, 37, 45, 53];
const PH = 3.5, BH = 10, LMAX = 14, STEP = 30, N = ROWS * COLS.length, K0 = 16;
const X0 = 0, X1 = (ROWS - 1) * PITCH + PAN + BACK;

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let lift = clamp(value, 1, LMAX);
  const C = Cam(45, 0.5, 2.4);
  fit(C, [[-24, -4, -4], [86, 66, -4], [86, -4, -4], [-24, 66, -4], [-24, -4, BH + LMAX], [86, 66, BH + LMAX], [-8, 4, 12]], 200, 166);
  const P = proj(C), front = facing(C);
  const g = mk("g", {}, svg);

  // the floor's round ends are large on screen, so its two rings take 14 steps a corner instead of rings()'s four
  put(solid(g), prism(P, front, rrect(-24, -4, 86, 66, 30, 14), rrect(-22, -2, 84, 64, 28, 14), -4, 0));
  const [hr, hi] = rings(-10, 4, -7, 60, 1, 0.6);
  put(solid(g), prism(P, front, hr, hi, 0, 12));

  // seats in raising order: row by row from the nose, window to window
  const seats = [];
  for (let j = 0; j < ROWS; j++) for (const y of COLS) {
    const x = j * PITCH;
    seats.push({ x, y, pan: rings(x, y, x + PAN, y + SW, 1.4, 0.6), back: rings(x + PAN, y, x + PAN + BACK, y + SW, 0.8, 0.5), z: tween(0), drawn: NaN });
  }
  // paint back to front by the middle of each solid, so a seat's back covers its own pan and the row behind
  const parts = [];
  seats.forEach((s) => {
    parts.push({ s, key: s.x + PAN / 2 + s.y + SW / 2, ring: s.pan, h: PH });
    parts.push({ s, key: s.x + PAN + BACK / 2 + s.y + SW / 2, ring: s.back, h: BH });
  });
  parts.sort((a, b) => a.key - b.key).forEach((p) => { p.el = solid(g); (p.s.els ||= []).push(p); });

  function draw(s, z) {
    if (z === s.drawn) return;
    s.drawn = z;
    for (const p of s.els) put(p.el, prism(P, front, p.ring[0], p.ring[1], z, z + p.h));
  }

  const L = register(stage, (_dt, now) => {
    let moving = false;
    for (const s of seats) { draw(s, tval(s.z, now)); if (!tdone(s.z, now)) moving = true; }
    return moving;
  });
  bag.add(L.unregister);

  let k = -1;
  function share(next, label) {
    next = clamp(next, 0, N);
    const now = performance.now(), from = Math.max(next - 1, 0);
    seats.forEach((s, i) => {
      tset(s.z, i < next ? lift : 0, now, Math.abs(i - from) * STEP);
      s.els[1].el.sil.classList.toggle("hi", i === next - 1);
    });
    k = next;
    read.textContent = label ?? `share ${Math.round((100 * next) / N)}%`;
    L.wake();
  }
  share(K0, "rest");

  bag.add(pointer(stage, {
    move: (pt) => {
      const [x] = unproj(C, pt[0], pt[1], 0);
      share(Math.round(clamp((x - X0) / (X1 - X0), 0, 1) * N));
    },
    leave: () => share(K0, "rest"),
  }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { lift = clamp(v, 1, LMAX); const r = read.textContent; share(k, r === "rest" ? "rest" : undefined); },
    destroy: bag.dispose,
  };
}

hairline({
  name: "seats",
  means: "A cabin's seats: sweep along the aisle and the seats from the nose back to the pointer lift. The read-out is their share.",
  rules: [1, 2, 3, 5],
  range: [4, 8, 14],
  tour: [[169, 173], [214, 195], [258, 217], null],
  mount,
});

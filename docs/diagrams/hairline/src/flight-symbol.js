/**
 * Flight symbol: American Airlines' mark rebuilt as three plates on a round
 * stand: the blue band above, the silver head in the middle, standing a
 * little proud of the red band it overlaps. Each plate is a filleted outline
 * with the source's proportions, read from its ink box, never its paths. The
 * mark leans back to face the eye, so at rest it reads as the mark. The
 * pointer's place left or right of the stand turns it toward the pointer and
 * banks it into the turn, each on a spring, and the band on the pointer's
 * side takes the bright edge. At rest it is turned a little to the left,
 * banked into that turn, the blue band bright. The slider is the bank.
 */
const {
  Cam, clamp, facing, fillet, fit, hull, poly, prism, proj, rad, rings,
  spring, stepS, disposer, mk, pointer, put, register, solid,
} = HL;

const K = 1.5, T = 4, B = 0.8, YAW = 26, HC = 42, DX0 = -0.35, BMAX = 26;
// the source's three parts in its own units, about the centre of its ink box (u right, v up), clockwise, a radius per corner
const PARTS = [
  { key: "red", w: 0, pts: [[-7.3, -3.0], [5.2, -1.0], [23.1, -22.8], [3.1, -22.8]], r: [0.6, 0.6, 0.6, 3.0] },
  { key: "head", w: 4.6, pts: [[-8.6, -0.6], [-5.5, 2.8], [2.8, 3.7], [9.0, 2.4], [11.7, -1.4], [-2.9, -10.2], [-7.3, -4.5]], r: [2.6, 2, 2, 1.6, 0.5, 1.2, 1.6] },
  { key: "blue", w: 0, pts: [[-23.3, 22.7], [-15.2, 22.7], [0.6, 4.5], [-12.2, 4.5]], r: [0.6, 3.4, 0.6, 3.0] },
];
// the mark's axes: u across the screen, v up the mark leaning back 30° to face the eye, w toward the eye
const S30 = Math.sin(rad(30)), C30 = Math.cos(rad(30)), H = Math.SQRT1_2;
const AX = { u: [H, -H, 0], v: [-S30 * H, -S30 * H, C30], w: [C30 * H, C30 * H, S30] };

/** A convex clockwise outline moved in by b on every side. */
function inset(pts, b) {
  const n = pts.length, L = pts.map((p, i) => {
    const q = pts[(i + 1) % n], dx = q[0] - p[0], dy = q[1] - p[1], l = Math.hypot(dx, dy);
    return [p[0] + (dy / l) * b, p[1] - (dx / l) * b, dx, dy];
  });
  return L.map((l1, i) => {
    const l0 = L[(i + n - 1) % n], den = l0[2] * l1[3] - l0[3] * l1[2];
    const t = ((l1[0] - l0[0]) * l1[3] - (l1[1] - l0[1]) * l1[2]) / den;
    return [l0[0] + l0[2] * t, l0[1] + l0[3] * t];
  });
}

/** A point of the mark in the world: rolled in its own plane, then the whole mark turned about the stand. */
function world(u, v, w, yaw, roll) {
  const u1 = u * Math.cos(roll) - v * Math.sin(roll), v1 = u * Math.sin(roll) + v * Math.cos(roll);
  const [x, y, z] = [0, 1, 2].map((k) => u1 * AX.u[k] + v1 * AX.v[k] + w * AX.w[k]);
  return [x * Math.cos(yaw) - y * Math.sin(yaw), x * Math.sin(yaw) + y * Math.cos(yaw), HC + z];
}

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let bank = clamp(value, 4, BMAX);
  const parts = PARTS.map((p) => ({
    ...p,
    outer: fillet(p.pts.map(([u, v]) => [u * K, v * K]), p.r.map((r) => r * K), 4),
    inner: fillet(inset(p.pts.map(([u, v]) => [u * K, v * K]), B), p.r.map((r) => Math.max(0.3, r * K - B)), 4),
  }));
  const ext = [[-24, -24, 0], [24, 24, 0], [24, -24, 0], [-24, 24, 0]];
  for (const yw of [-YAW, 0, YAW]) for (const rl of [-BMAX, 0, BMAX]) for (const p of parts) for (const [u, v] of p.outer) ext.push(world(u, v, p.w + T, rad(yw), rad(rl)));
  const C = Cam(45, 0.5, 2.5);
  fit(C, ext, 200, 166);
  const P = proj(C), front = facing(C), at = (u, v, w, yw, rl) => P(...world(u, v, w, yw, rl));

  const g = mk("g", {}, svg);
  const [pr, pi] = rings(-24, -24, 24, 24, 24, 1.6);
  put(solid(g), prism(P, front, pr, pi, 0, 4));
  const [qr, qi] = rings(-2.4, -2.4, 2.4, 2.4, 2.4, 0.7);
  put(solid(g), prism(P, front, qr, qi, 4, HC));
  for (const p of parts) p.el = solid(g);

  const ys = spring(-DX0 * rad(YAW)), rs = spring(-DX0 * rad(bank));
  let drawn = "";
  function draw() {
    const key = ys.x.toFixed(4) + rs.x.toFixed(4);
    if (key === drawn) return;
    drawn = key;
    for (const p of parts) {
      const face = (w) => p.outer.map(([u, v]) => at(u, v, w, ys.x, rs.x));
      put(p.el, { sil: poly(hull(face(p.w).concat(face(p.w + T)))), crease: poly(p.inner.map(([u, v]) => at(u, v, p.w + T, ys.x, rs.x))) });
    }
  }

  const L = register(stage, (dt) => { const m = stepS(ys, dt) | stepS(rs, dt); draw(); return !!m; });
  bag.add(L.unregister);

  let cur = [DX0, "rest"];
  function aim(dx, label) {
    cur = [dx, label];
    ys.t = -dx * rad(YAW);
    rs.t = -dx * rad(bank);
    const lit = dx < -0.15 ? "blue" : dx > 0.15 ? "red" : "head";
    parts.forEach((p) => p.el.sil.classList.toggle("hi", p.key === lit));
    read.textContent = label ?? `bank ${Math.round(Math.abs(dx * bank))}°`;
    L.wake();
  }
  aim(...cur);

  bag.add(pointer(stage, { move: (pt) => aim(clamp((pt[0] - 200) / 150, -1, 1)), leave: () => aim(DX0, "rest") }));
  bag.add(() => svg.replaceChildren());

  return { set: (v) => { bank = clamp(v, 4, BMAX); aim(...cur); }, destroy: bag.dispose };
}

hairline({
  name: "flight-symbol",
  means: "American Airlines' Flight Symbol as three plates on a stand: it turns toward the pointer and banks into the turn.",
  rules: [3, 4, 5, 8],
  range: [6, 14, 26],
  tour: [[90, 160], [310, 160], [200, 160], null],
  mount,
});

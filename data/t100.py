"""Turns raw BTS T-100 Domestic Segment (All Carriers) files into AA seat share per market and month.

Why: "fair share" in the demo is AA's share of seats on a route. Agencies and
their sales are made up; the seat denominators are real.

How to get the raw files (no stable download URL exists; verified Oct 11, 2026):
  1. https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=GEE&QO_fu146_anzr=Nv4+Pn44vr45
     (T-100 Domestic Segment, All Carriers)
  2. Tick UNIQUE_CARRIER, ORIGIN, DEST, YEAR, MONTH, PASSENGERS, SEATS, CLASS; pick the year;
     tick "Prezipped File"; download. Do it for 2025 and 2026.
  3. Drop the zips or CSVs into data/t100/raw/ (gitignored) and run: python data/t100.py

Output: data/t100/aa_seat_share.csv (committed, small). Months the BTS has not
published yet (three-month lag; July 2026 was the latest on Oct 11, 2026) take
the same month of the prior year and are flagged is_projected = true.

"AA network" = AA mainline plus the wholly owned American Eagle carriers
(Envoy MQ, PSA OH, Piedmont PT). Republic and SkyWest fly for several brands
and are left out, so the share slightly undercounts AA. Said plainly in README.
"""
import csv
import io
import sys
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "t100" / "raw"
OUT = HERE / "t100" / "aa_seat_share.csv"
AA_NETWORK = {"AA", "MQ", "OH", "PT"}
FIRST, LAST = date(2025, 1, 1), date(2026, 9, 1)

sys.path.insert(0, str(HERE))
from make_data import markets  # noqa: E402  (the same 12 markets the generator uses)


def months():
    y, m = FIRST.year, FIRST.month
    while (y, m) <= (LAST.year, LAST.month):
        yield date(y, m, 1)
        m += 1
        if m == 13:
            y, m = y + 1, 1


def rows_from(path: Path):
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.lower().endswith(".csv"):
                    yield from csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"))
    else:
        with open(path, newline="", encoding="utf-8-sig") as f:
            yield from csv.DictReader(f)


def main():
    files = sorted(p for p in RAW.glob("*") if p.suffix.lower() in (".csv", ".zip"))
    if not files:
        raise SystemExit(f"no raw T-100 files in {RAW}; see the docstring for the download steps")
    pair_to_market = {}
    for mid, o, d, *_ in markets:
        pair_to_market[(o, d)] = mid
        pair_to_market[(d, o)] = mid  # a market is both directions
    seats = defaultdict(lambda: [0, 0])  # (market_id, month) -> [aa_seats, total_seats]
    n = 0
    for p in files:
        for r in rows_from(p):
            key = (r.get("ORIGIN", "").strip(), r.get("DEST", "").strip())
            mid = pair_to_market.get(key)
            if mid is None:
                continue
            if "CLASS" in r and r["CLASS"].strip() not in ("F", ""):  # F = scheduled passenger service
                continue
            try:
                mo = date(int(float(r["YEAR"])), int(float(r["MONTH"])), 1)
                s = int(float(r["SEATS"] or 0))
            except (KeyError, ValueError):
                continue
            if not (FIRST <= mo <= LAST):
                continue
            cell = seats[(mid, mo)]
            cell[1] += s
            if r.get("UNIQUE_CARRIER", "").strip() in AA_NETWORK:
                cell[0] += s
            n += 1
    print(f"read {n} matching segment rows from {len(files)} file(s)")

    out = []
    projected = set()
    for mid, o, d, *_ in markets:
        for mo in months():
            aa, tot = seats.get((mid, mo), (0, 0))
            flag = False
            if tot == 0:  # not published yet: carry the same month of the prior year
                aa, tot = seats.get((mid, date(mo.year - 1, mo.month, 1)), (0, 0))
                flag = True
                projected.add(mo)
            share = round(aa / tot, 4) if tot else None
            out.append((mid, o, d, mo.isoformat(), aa, tot, share, str(flag).lower()))
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["market_id", "origin", "dest", "sales_month", "aa_seats", "total_seats", "aa_seat_share", "is_projected"])
        w.writerows(out)
    print(f"wrote {OUT} ({len(out)} rows); projected months: {sorted(m.isoformat() for m in projected)}")

    # Markets where AA has no seats cannot have agencies selling AA on them: swap those in make_data.py.
    for mid, o, d, *_ in markets:
        aa_total = sum(seats.get((mid, mo), (0, 0))[0] for mo in months())
        if aa_total == 0:
            print(f"WARNING market {mid} {o}-{d}: AA network has zero seats in T-100; swap it for a route AA flies")
    missing = [(mid, mo) for (mid, mo), (aa, tot) in seats.items() if tot == 0]
    if missing:
        print(f"WARNING {len(missing)} market-months have zero total seats")


if __name__ == "__main__":
    main()

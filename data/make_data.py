"""Builds the demo dataset: airline indirect sales shaped like AA's agency business.

Made-up agencies, corporate accounts and sales, deterministic (seeded) so every
number in the demo is reproducible. AA's seat share per market comes from real
BTS T-100 data when data/t100/aa_seat_share.csv exists (see t100.py); otherwise
a synthetic stand-in is written and labeled as such.

Writes CSVs to data/out/. Nothing here is confidential and nothing is AA's.

Planted data-quality traps (kept on purpose; silver fixes them):
  - channel labels with stray case and whitespace
  - six tickets loaded twice
  - agency 9 has no rows for Mar and Apr 2026 (a gap)
  - agency 5's AA share collapses Feb to Jun 2026
  - agency 4 sells no AA on market 12 in Jan 2026 (zero revenue)
  - corporate 104 declines every month until its contract ends in Jun 2026
  - corporate 108 declines Mar to Jul 2026 then recovers
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(88201)
HERE = Path(__file__).parent
OUT = HERE / "out"
T100 = HERE / "t100" / "aa_seat_share.csv"

MONTHS = []
y, m = 2025, 1
while (y, m) <= (2026, 9):
    MONTHS.append(date(y, m, 1))
    m += 1
    if m == 13:
        y, m = y + 1, 1

agencies = [
    # id, name, type, region, account_manager
    (1, "Summit Travel Partners", "TMC", "Central", "Dana Whitfield"),
    (2, "BlueSky Corporate Travel", "TMC", "East", "Marcus Lee"),
    (3, "FareHub Online", "OTA", "West", "Priya Raman"),
    (4, "Northstar Leisure", "Leisure", "Central", "Dana Whitfield"),
    (5, "Harbor Business Travel", "TMC", "East", "Marcus Lee"),
    (6, "Pacific Gateway Travel", "Consolidator", "West", "Priya Raman"),
    (7, "Lone Star Travel Group", "TMC", "Central", "Dana Whitfield"),
    (8, "Capitol Corporate Travel", "TMC", "East", "Marcus Lee"),
    (9, "Sunbelt Vacations", "Leisure", "Central", "Tom Okafor"),
    (10, "Golden Coast Travel", "OTA", "West", "Priya Raman"),
    (11, "Midway Travel Services", "Consolidator", "Central", "Tom Okafor"),
    (12, "Atlantic Premier Travel", "TMC", "East", "Marcus Lee"),
]

corporates = [
    # id, name, industry, hq_city, contract_start, contract_end, annual_commitment_usd
    (101, "Redwood Consulting", "Professional Services", "Chicago", date(2025, 1, 1), date(2026, 12, 31), 2400000),
    (102, "Vantage Energy", "Energy", "Houston", date(2025, 1, 1), date(2026, 12, 31), 3100000),
    (103, "Meridian Health", "Healthcare", "Dallas", date(2025, 4, 1), date(2027, 3, 31), 1800000),
    (104, "Northwind Logistics", "Transportation", "Memphis", date(2025, 1, 1), date(2026, 6, 30), 950000),
    (105, "Pinnacle Software", "Technology", "Austin", date(2025, 1, 1), date(2026, 12, 31), 2050000),
    (106, "Beacon Financial", "Financial Services", "New York", date(2025, 7, 1), date(2027, 6, 30), 4200000),
    (107, "Ironbridge Manufacturing", "Manufacturing", "Pittsburgh", date(2025, 1, 1), date(2026, 12, 31), 1200000),
    (108, "Coastal Media Group", "Media", "Los Angeles", date(2025, 1, 1), date(2026, 12, 31), 700000),
    (109, "Summit Biotech", "Healthcare", "Boston", date(2026, 1, 1), date(2027, 12, 31), 1500000),
    (110, "Prairie Retail Holdings", "Retail", "Minneapolis", date(2025, 1, 1), date(2026, 12, 31), 600000),
]

markets = [
    # id, origin, dest, region, aa_hub_origin
    (1, "DFW", "LAX", "West", True),
    (2, "DFW", "ORD", "Central", True),
    (3, "CLT", "LGA", "East", True),
    (4, "MIA", "JFK", "East", True),
    (5, "PHX", "SEA", "West", True),
    (6, "DFW", "DCA", "East", True),
    (7, "ORD", "SFO", "West", True),
    (8, "DCA", "BOS", "East", True),
    (9, "LAX", "JFK", "East", True),
    (10, "DFW", "DEN", "Central", True),
    (11, "AUS", "ORD", "Central", False),
    (12, "SEA", "DEN", "West", False),
]

# Synthetic AA seat share by market, used only when the T-100 file is missing
synthetic_fair_share = {1: 0.42, 2: 0.38, 3: 0.55, 4: 0.47, 5: 0.33, 6: 0.51, 7: 0.29, 8: 0.36, 9: 0.31, 10: 0.40, 11: 0.22, 12: 0.18}

# Per-agency base monthly market revenue (all carriers), AA share level, monthly drift
agency_profile = {
    1: (900000, 0.45, 0.004),    # steady, above fair share
    2: (750000, 0.40, 0.000),
    3: (1400000, 0.30, -0.006),  # OTA, big volume, drifting down
    4: (300000, 0.44, 0.002),
    5: (650000, 0.52, -0.009),   # falls for a run of months
    6: (520000, 0.35, 0.001),
    7: (820000, 0.48, 0.003),
    8: (700000, 0.41, -0.001),
    9: (260000, 0.39, 0.000),
    10: (1100000, 0.27, 0.002),
    11: (410000, 0.36, -0.003),
    12: (880000, 0.50, 0.001),
}


def build_sales():
    rows = []
    for aid, (base, share0, drift) in agency_profile.items():
        for i, mo in enumerate(MONTHS):
            if aid == 9 and mo in (date(2026, 3, 1), date(2026, 4, 1)):
                continue
            season = 1.0 + 0.18 * (1 if mo.month in (3, 6, 7, 10) else 0) - 0.12 * (1 if mo.month in (1, 2, 9) else 0)
            growth = 1.0 + 0.004 * i
            for mid, origin, dest, region, hub in markets:
                weight = 1.6 if hub else 0.6
                if region == next(a[3] for a in agencies if a[0] == aid):
                    weight *= 1.5
                mkt_rev = base * season * growth * weight / 14.0 * random.uniform(0.85, 1.15)
                share = share0 + drift * i + random.uniform(-0.03, 0.03)
                if aid == 5 and date(2026, 2, 1) <= mo <= date(2026, 6, 1):
                    share -= 0.03 * (mo.month - 1)
                share = max(0.05, min(0.85, share))
                aa_rev = 0.0 if (aid == 4 and mid == 12 and mo == date(2026, 1, 1)) else mkt_rev * share
                avg_fare_mkt = random.uniform(280, 520)
                mkt_pax = int(mkt_rev / avg_fare_mkt)
                aa_pax = int(aa_rev / (avg_fare_mkt * random.uniform(0.95, 1.08)))
                rows.append((aid, mid, mo.isoformat(), round(aa_rev, 2), aa_pax, round(mkt_rev, 2), mkt_pax))
    return rows


def build_capacity():
    """AA seat share per market and month: real T-100 if present, synthetic otherwise.

    Exactly one random draw per market-month in both branches, so the bookings that
    follow come out identical to the SQL drill's answer key either way.
    """
    t100 = {}
    if T100.exists():
        with open(T100, newline="") as f:
            t100 = {(int(r["market_id"]), r["sales_month"]): r for r in csv.DictReader(f)}
    rows = []
    for mid, *_ in markets:
        for mo in MONTHS:
            noise = random.uniform(-0.01, 0.01)
            if t100:
                r = t100.get((mid, mo.isoformat()))
                if r is None:
                    raise SystemExit(f"t100 file has no row for market {mid} {mo}; rerun t100.py")
                rows.append((mid, mo.isoformat(), int(r["aa_seats"]), int(r["total_seats"]), round(float(r["aa_seat_share"]), 4),
                             r["is_projected"].lower() == "true", "t100"))
            else:
                share = round(synthetic_fair_share[mid] + noise, 4)
                total = 150000
                rows.append((mid, mo.isoformat(), int(total * share), total, share, False, "synthetic"))
    return rows, ("t100" if t100 else "synthetic")


def build_goals():
    goals = []
    for aid, (base, share0, drift) in agency_profile.items():
        for yr in (2025, 2026):
            annual_mkt = base * 12 * 1.0
            goals.append((aid, yr, round(annual_mkt * (share0 + 0.03), 0), round(share0 + 0.03, 3)))
    return goals


def build_bookings():
    channels = ["NDC", "GDS", "Direct", "OTA"]
    cabins = ["Economy", "Economy", "Economy", "Premium Economy", "Business"]
    bookings = []
    bid = 500000
    for cid, name, ind, hq, cstart, cend, commit in corporates:
        monthly_target = commit / 12.0
        for i, mo in enumerate(MONTHS):
            if mo < cstart or mo > cend:
                continue
            factor = 1.0
            if cid == 104 and mo >= date(2026, 1, 1):
                factor = 1.0 - 0.12 * (mo.month)
            if cid == 108 and date(2026, 3, 1) <= mo <= date(2026, 7, 1):
                factor = 1.0 - 0.10 * (mo.month - 2)
            month_rev = monthly_target * random.uniform(0.75, 1.25) * factor
            n = max(3, int(month_rev / 1000))
            for _ in range(n):
                bid += 1
                booking_date = mo + timedelta(days=random.randint(0, 27))
                lead = random.choice([1, 2, 3, 5, 7, 10, 14, 21, 30, 45, 60])
                travel_date = booking_date + timedelta(days=lead)
                mid, origin, dest, region, hub = random.choice(markets)
                channel = random.choice(channels)
                if random.random() < 0.04:
                    channel = channel.lower()
                if random.random() < 0.02:
                    channel = " " + channel + " "
                fare = random.uniform(180, 1400)
                fare = round(fare * (1.35 if lead <= 3 else 1.15 if lead <= 7 else 1.0 if lead <= 21 else 0.8), 2)
                cabin = random.choice(cabins)
                if cabin == "Business":
                    fare = round(fare * 2.4, 2)
                agency = random.choice([1, 2, 5, 7, 8, 12, None]) if channel.strip().upper() != "DIRECT" else None
                ticket = f"001{bid:010d}"
                bookings.append((bid, ticket, cid, booking_date.isoformat(), travel_date.isoformat(), origin, dest, channel, fare, 1, cabin, agency))
    dups = random.sample(bookings, 6)
    for row in dups:
        bid += 1
        bookings.append((bid,) + row[1:])
    return bookings


def build_crm():
    """The CRM stand-in: contacts, opportunities and activities shaped like Dynamics 365 Sales, all fictional.
    Its own generator (not the module's), so the sales stream above and every existing number stay identical.

    Planted on purpose: Harbor's renewal says Negotiate and On track while its share collapsed (the CRM-versus-reality
    story); FareHub's says At risk and is; Summit's says On track and is.
    """
    rng = random.Random(88202)
    first = ["Avery", "Jordan", "Morgan", "Riley", "Casey", "Quinn", "Taylor", "Drew", "Reese", "Harper", "Rowan", "Sage"]
    last = ["Patel", "Nguyen", "Garcia", "Okoro", "Kim", "Silva", "Brennan", "Haddad", "Larsen", "Mehta", "Flores", "Walsh"]
    titles = ["Director of Air", "VP Supplier Relations", "Air Sourcing Manager", "Head of Corporate Travel", "Operations Lead"]
    kinds = [("Call", "Monthly check-in"), ("Email", "Performance report sent"), ("Meeting", "Quarterly business review"), ("Email", "Follow-up on fare display")]
    today = date(2026, 10, 1)
    contacts, opps, acts = [], [], []
    cid, oid, actid = 9000, 7000, 30000
    for aid, name, _atype, _region, am in agencies:
        domain = name.lower().replace(" ", "") + ".example"
        people = []
        for _ in range(rng.choice([1, 2, 2, 3])):
            cid += 1
            fn, ln = rng.choice(first), rng.choice(last)
            contacts.append((cid, aid, f"{fn} {ln}", rng.choice(titles), f"{fn.lower()}.{ln.lower()}@{domain}"))
            people.append(cid)
        base = agency_profile[aid][0]
        health = {5: "On track", 3: "At risk", 1: "On track"}.get(aid, rng.choice(["On track", "On track", "At risk", "Stalled"]))
        stage = {5: "Negotiate", 3: "Propose", 1: "Negotiate"}.get(aid, rng.choice(["Qualify", "Propose", "Negotiate"]))
        oid += 1
        opps.append((oid, aid, f"{name} 2027 renewal", stage, round(base * 12 * 0.45 * 1.5, -3), date(2026, 12, 15).isoformat(), health, am,
                     (today - timedelta(days=rng.randint(3, 40))).isoformat()))
        if base >= 700000:
            oid += 1
            opps.append((oid, aid, f"{name} NDC adoption", rng.choice(["Qualify", "Propose"]), round(base * 1.2, -3), date(2027, 3, 31).isoformat(),
                         rng.choice(["On track", "Stalled"]), am, (today - timedelta(days=rng.randint(10, 90))).isoformat()))
        cutoff = today - timedelta(days=rng.randint(5, 45))   # the last touch is between five and seventy days old
        d = date(2026, 1, 10)
        while d < cutoff:
            actid += 1
            kind, subject = rng.choice(kinds)
            acts.append((actid, aid, rng.choice(people), kind, subject, d.isoformat(), am, ""))
            d += timedelta(days=rng.randint(10, 25))
    return contacts, opps, acts


def write(name, header, rows):
    with open(OUT / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def main():
    OUT.mkdir(exist_ok=True)
    # Order matters: the random stream must match across runs, so build in a fixed sequence.
    sales = build_sales()
    capacity, source = build_capacity()
    goals = build_goals()
    bookings = build_bookings()
    write("dim_agency.csv", ["agency_id", "agency_name", "agency_type", "region", "account_manager"], agencies)
    write("dim_corporate.csv", ["corp_id", "corp_name", "industry", "hq_city", "contract_start", "contract_end", "annual_commitment_usd"],
          [(c[0], c[1], c[2], c[3], c[4].isoformat(), c[5].isoformat(), c[6]) for c in corporates])
    write("dim_market.csv", ["market_id", "origin", "dest", "region", "aa_hub_origin"], markets)
    write("fact_agency_sales_monthly.csv", ["agency_id", "market_id", "sales_month", "aa_revenue", "aa_pax", "market_revenue", "market_pax"], sales)
    write("fact_market_capacity.csv", ["market_id", "sales_month", "aa_seats", "total_seats", "aa_seat_share", "is_projected", "source"], capacity)
    write("agency_goals.csv", ["agency_id", "goal_year", "revenue_goal_usd", "share_goal"], goals)
    write("fact_corporate_bookings.csv", ["booking_id", "ticket_number", "corp_id", "booking_date", "travel_date", "origin", "dest", "channel", "fare_usd", "ticket_count", "cabin", "agency_id"], bookings)
    contacts, opps, acts = build_crm()
    write("crm_contacts.csv", ["contact_id", "agency_id", "contact_name", "title", "email"], contacts)
    write("crm_opportunities.csv", ["opp_id", "agency_id", "opp_name", "stage", "amount_usd", "close_date", "health", "owner", "updated_at"], opps)
    write("crm_activities.csv", ["activity_id", "agency_id", "contact_id", "activity_type", "subject", "happened_at", "owner", "notes"], acts)
    print(f"fair share source: {source}")


if __name__ == "__main__":
    main()

"""The AI/BI dashboard, as code: the sales director's Monday view over the metric view.

  python lakehouse/dashboard.py build   # writes lakehouse/dashboard.lvdash.json from the definitions below
  python lakehouse/dashboard.py push    # creates (first time) or updates the draft from the JSON file, then publishes it
  python lakehouse/dashboard.py pull    # downloads the live draft into the JSON file (after hand-tuning in the UI)
  python lakehouse/dashboard.py url     # prints the published URL

The JSON file is the source of truth (it is what the UI edits and what a Declarative Automation Bundle would deploy);
`build` is the scaffold that wrote it the first time. Every dataset is MEASURE() on aa_demo.gold.sales_metrics except
pace (gold.agency_pace) and the parity tile (ops.kpi_parity), so the tiles cannot disagree with the agent.
Ratios are never summed: datasets carry the additive pieces (AA revenue, market revenue, fair-share revenue) and every
widget divides them, which is also what makes the Region and Agency filters correct for share.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fairshare.dbx import warehouse_id, workspace_client  # noqa: E402

FILE = ROOT / "lakehouse" / "dashboard.lvdash.json"
TITLE = "fairshare: agency sales"
MONTH = "2026-09"  # the close the walkthrough opens on

MV = """SELECT region, account_manager, agency, agency_type, {dims}sales_month,
         MEASURE(aa_revenue) AS aa_revenue, MEASURE(market_revenue) AS market_revenue,
         MEASURE(aa_revenue) - MEASURE(share_gap_usd) AS fair_revenue
  FROM aa_demo.gold.sales_metrics
  GROUP BY ALL"""

DATASETS = {
    "agency_month": f"""WITH mv AS (
  {MV.format(dims="")}),
pace AS (
  SELECT a.agency_name AS agency, p.sales_month, p.ytd_revenue, p.ytd_goal, p.revenue_goal_usd
  FROM aa_demo.gold.agency_pace p JOIN aa_demo.gold.dim_agency a USING (agency_id))
SELECT n.region, n.account_manager, n.agency, n.agency_type, n.sales_month,
       date_format(n.sales_month, 'yyyy-MM') AS month_label,
       n.aa_revenue, n.market_revenue, n.fair_revenue,
       l.aa_revenue AS aa_revenue_ly, l.market_revenue AS market_revenue_ly, l.fair_revenue AS fair_revenue_ly,
       p.ytd_revenue, p.ytd_goal, p.revenue_goal_usd,
       (n.aa_revenue / l.aa_revenue - 1) * 100 AS yoy_pct, n.aa_revenue / n.market_revenue * 100 AS share_pct, n.fair_revenue / n.market_revenue * 100 AS fair_pct,
       (n.aa_revenue - n.fair_revenue) / n.market_revenue * 100 AS gap_pts, n.aa_revenue - n.fair_revenue AS gap_usd,
       (n.aa_revenue / n.market_revenue - l.aa_revenue / l.market_revenue) * 100 AS share_chg_pts,
       p.ytd_revenue / p.ytd_goal * 100 AS pace_pct, p.ytd_revenue / p.revenue_goal_usd * 100 AS attainment_pct
FROM mv n
LEFT JOIN mv l ON l.agency = n.agency AND l.sales_month = add_months(n.sales_month, -12)
LEFT JOIN pace p ON p.agency = n.agency AND p.sales_month = n.sales_month""",
    "trend": f"""WITH mv AS (
  {MV.format(dims="")})
SELECT region, agency, sales_month, 'AA share' AS series, aa_revenue AS numerator, market_revenue AS denominator FROM mv
UNION ALL
SELECT region, agency, sales_month, 'Fair share' AS series, fair_revenue AS numerator, market_revenue AS denominator FROM mv""",
    "markets": f"""WITH mv AS (
  {MV.format(dims="market, ")})
SELECT n.region, n.agency, n.market, n.sales_month, date_format(n.sales_month, 'yyyy-MM') AS month_label,
       n.aa_revenue, n.market_revenue, n.fair_revenue, l.aa_revenue AS aa_revenue_ly
FROM mv n
LEFT JOIN mv l ON l.agency = n.agency AND l.market = n.market AND l.sales_month = add_months(n.sales_month, -12)""",
    "parity": """SELECT MAX(run_at) AS last_run, COUNT(*) AS checks, COUNT_IF(status <> 'ok') AS red
FROM aa_demo.ops.kpi_parity
WHERE run_id = (SELECT run_id FROM aa_demo.ops.kpi_parity ORDER BY run_at DESC LIMIT 1)""",
}

# widget expressions over agency_month (the dashboard compiles these into SQL on the warehouse)
REV, REV_LY, MKT, MKT_LY, FAIR = "SUM(`aa_revenue`)", "SUM(`aa_revenue_ly`)", "SUM(`market_revenue`)", "SUM(`market_revenue_ly`)", "SUM(`fair_revenue`)"
SHARE, FAIR_SHARE = f"{REV} / {MKT}", f"{FAIR} / {MKT}"
CHG_PTS = "AVG(`share_chg_pts`)"  # one row per agency and month in the dataset, so the average is the value; the widget expression parser rejects the two-ratio form
USD = {"type": "number-currency", "currencyCode": "USD", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
PCT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 1}}
RED, BLUE, GREY = "#B3261E", "#2E6FD6", "#8A8F98"


def pos(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def frame(title, description=""):
    return {"showTitle": True, "title": title, "showDescription": bool(description), "description": description}


def widget(name, dataset, fields, spec, position, disaggregated=False):
    query = {"datasetName": dataset, "fields": [{"name": n, "expression": e} for n, e in fields], "disaggregated": disaggregated}
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": query}], "spec": spec}, "position": position}


def text(name, lines, position):
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": [l + "\n" for l in lines]}}, "position": position}


def counter(name, title, expr, fmt, position, description="", target=None):
    enc = {"value": {"fieldName": "value", "displayName": title, "format": fmt}}
    fields = [("value", expr)]
    if target:
        enc["target"] = {"fieldName": "target", "displayName": target[0], "format": fmt}
        fields.append(("target", target[1]))
    return widget(name, "agency_month", fields, {"version": 2, "widgetType": "counter", "encodings": enc, "frame": frame(title, description)}, position)


def bars(name, title, description, expr, fmt, position, dataset="agency_month", by="agency"):
    """Horizontal bars by agency (or market), most negative first, red below zero."""
    fields = [(by, f"`{by}`"), ("value", expr), ("below", f"{expr} < 0")]  # a boolean: string literals do not survive the expression parser
    x = {"fieldName": "value", "scale": {"type": "quantitative"}, "displayName": title}
    if fmt:
        x["format"] = fmt
    spec = {"version": 3, "widgetType": "bar", "mark": {"colors": [BLUE, RED]}, "encodings": {  # series sort alphabetically: above, below
        "x": x,
        "y": {"fieldName": by, "scale": {"type": "categorical", "sort": {"by": "x"}}, "displayName": by.capitalize()},
        "color": {"fieldName": "below", "scale": {"type": "categorical", "mappings": [{"value": "true", "color": RED}, {"value": "false", "color": BLUE}]},
                  "displayName": "below zero", "legend": {"hide": True}}},
        "frame": frame(title, description)}
    return widget(name, dataset, fields, spec, position)


def column(field, title, kind="float", fmt="0,0", order=0):
    """A table column with the full property set the UI writes (the renderer shows 'no fields selected' when keys are missing)."""
    c = {"fieldName": field, "displayName": title, "title": title, "type": kind, "displayAs": "number" if kind == "float" else "string",
         "order": 100000 + order, "visible": True, "alignContent": "right" if kind == "float" else "left",
         "allowHTML": False, "allowSearch": False, "booleanValues": ["false", "true"], "highlightLinks": False, "preserveWhitespace": False,
         "useMonospaceFont": False, "imageHeight": "", "imageWidth": "", "imageTitleTemplate": "{{ @ }}", "imageUrlTemplate": "{{ @ }}",
         "linkOpenInNewTab": True, "linkTextTemplate": "{{ @ }}", "linkTitleTemplate": "{{ @ }}", "linkUrlTemplate": "{{ @ }}"}
    if kind == "float":
        c["numberFormat"] = fmt
    return c


def table(name, title, description, dataset, columns, position):
    """A row view of dataset columns (tables do not aggregate; ratios are columns of the dataset)."""
    spec = {"version": 1, "widgetType": "table", "encodings": {"columns": [column(*c, order=i) for i, c in enumerate(columns)]},
            "frame": frame(title, description), "invisibleColumns": [], "allowHTMLByDefault": False, "itemsPerPage": 25,
            "paginationSize": "default", "condensed": True, "withRowNumber": False}
    return widget(name, dataset, [(c[0], f"`{c[0]}`") for c in columns], spec, position, disaggregated=True)


def filt(name, kind, title, bindings, position, default=None):
    """One filter widget bound to the same column in several datasets. kind: filter-single-select | filter-multi-select."""
    queries, fields = [], []
    for ds, f in bindings:
        qn = f"filter_{ds}_{f}"
        queries.append({"name": qn, "query": {"datasetName": ds, "disaggregated": False, "fields": [
            {"name": f, "expression": f"`{f}`"}, {"name": f"{f}_associativity", "expression": "COUNT_IF(`associative_filter_predicate_group`)"}]}})
        fields.append({"fieldName": f, "displayName": title, "queryName": qn})
    spec = {"version": 2, "widgetType": kind, "encodings": {"fields": fields}, "frame": frame(title)}
    if default is not None:
        spec["selection"] = {"defaultSelection": {"values": {"dataType": "STRING", "values": [{"value": default}]}}}
    return {"widget": {"name": name, "queries": queries, "spec": spec}, "position": position}


def build() -> dict:
    app_url = os.environ.get("DATABRICKS_APP_URL") or "the fairshare app (streamlit run app/app.py)"
    layout = [
        text("header", ["## Agency sales: share, fair share, pace",
                        "Every number on this page is a `MEASURE()` on `aa_demo.gold.sales_metrics`, the metric view the agent and Genie use; "
                        "pace comes from `gold.agency_pace`. At American this is the Power BI report on the mirrored catalog, same definitions."],
             pos(0, 0, 6, 2)),
        filt("f_region", "filter-single-select", "Region", [("agency_month", "region"), ("trend", "region"), ("markets", "region")], pos(0, 2, 2, 1)),
        filt("f_month", "filter-single-select", "Month", [("agency_month", "month_label"), ("markets", "month_label")], pos(2, 2, 2, 1), default=MONTH),
        filt("f_agency", "filter-multi-select", "Agency", [("agency_month", "agency"), ("trend", "agency"), ("markets", "agency")], pos(4, 2, 2, 1)),
        counter("c_revenue", "AA revenue, month", REV, USD, pos(0, 3, 1, 3), "MEASURE(aa_revenue)"),
        counter("c_pace", "Pace to 2026 goal", "SUM(`ytd_revenue`) / SUM(`ytd_goal`)", PCT, pos(1, 3, 1, 3), "year to date revenue over year to date goal"),
        counter("c_share", "AA share", SHARE, PCT, pos(2, 3, 1, 3), "against fair share, AA's seat share on the same markets", target=("Fair share", FAIR_SHARE)),
        counter("c_gap", "Share gap, dollars", f"{REV} - {FAIR}", USD, pos(3, 3, 1, 3), "AA revenue minus revenue at fair share"),
        table("t_parity", "Definitions check", "last nightly parity run: metric view against the Power BI twin, red = cells that disagree",
              "parity", [("last_run", "Last run", "string"), ("checks", "Checks", "float", "0,0"), ("red", "Red", "float", "0,0")], pos(4, 3, 2, 3)),
        bars("b_moved", "What moved: AA share vs last year, points", "same month last year; the biggest move is the first question for the account manager",
             CHG_PTS, None, pos(0, 6, 3, 7)),
        widget("l_trend", "trend", [("sales_month", "`sales_month`"), ("series", "`series`"), ("share", "SUM(`numerator`) / SUM(`denominator`)")],
               {"version": 3, "widgetType": "line", "encodings": {
                   "x": {"fieldName": "sales_month", "scale": {"type": "temporal"}, "displayName": "Month"},
                   "y": {"fieldName": "share", "scale": {"type": "quantitative"}, "displayName": "Share", "format": PCT},
                   "color": {"fieldName": "series", "scale": {"type": "categorical", "mappings": [{"value": "AA share", "color": BLUE}, {"value": "Fair share", "color": GREY}]},
                             "displayName": "Series"}},
                "frame": frame("AA share vs fair share by month", "click an agency on the left to isolate it; fair share is what AA's seats would predict")},
               pos(3, 6, 3, 7)),
        bars("b_gap", "Where the gap sits: share gap in dollars", "a steady gap is structure (an OTA sells every carrier); a new gap is the one to chase",
             f"{REV} - {FAIR}", USD, pos(0, 13, 3, 7)),
        bars("b_markets", "Share gap by market, dollars", "the selected agencies' markets for the month; click an agency above to isolate it",
             f"{REV} - {FAIR}", USD, pos(3, 13, 3, 7), dataset="markets", by="market"),
        table("t_agencies", "Agencies", "revenue, share and pace for the month", "agency_month",
              [("account_manager", "Account manager", "string"), ("agency", "Agency", "string"), ("agency_type", "Type", "string"),
               ("aa_revenue", "AA revenue", "float", "$0,0"), ("yoy_pct", "vs last year", "float", "0.0%"), ("share_pct", "AA share", "float", "0.0%"),
               ("fair_pct", "Fair share", "float", "0.0%"), ("gap_pts", "Gap, pts", "float", "0.0"), ("gap_usd", "Gap $", "float", "$0,0"),
               ("pace_pct", "Pace", "float", "0.0%"), ("attainment_pct", "Attainment YTD", "float", "0.0%")], pos(0, 20, 6, 8)),
        text("footer", [f"**Why is an account down?** This page stops at what and where. For why, the agreement, and a verified Monday summary, open {app_url}. "
                        "Definitions: `aa_demo.ops.kpi_definitions`. Nightly check: `aa_demo.ops.kpi_parity`."], pos(0, 28, 6, 1)),
    ]
    return {"datasets": [{"name": n, "displayName": n, "queryLines": sql.splitlines(keepends=True)} for n, sql in DATASETS.items()],  # the server stores one line per element
            "pages": [{"name": "monday", "displayName": "Monday", "layout": layout, "pageType": "PAGE_TYPE_CANVAS"}],
            # Ask Genie on the published page goes to the curated space (instructions, trusted SQL, the 20/20 benchmark), not to an auto-generated one
            "uiSettings": {"theme": {"widgetHeaderAlignment": "ALIGNMENT_UNSPECIFIED"}, "applyModeEnabled": False,
                           "genieSpace": {"isEnabled": True, "enablementMode": "ENABLED", "overrideId": os.environ.get("GENIE_SPACE_ID", "")}}}


def write_env(key: str, value: str):
    p = ROOT / ".env"
    s = p.read_text()
    s, n = re.subn(rf"^{key}=.*$", f"{key}={value}", s, flags=re.M)
    p.write_text(s if n else s.rstrip("\n") + f"\n{key}={value}\n")
    os.environ[key] = value


def push():
    from databricks.sdk.service.dashboards import Dashboard
    w = workspace_client()
    body = FILE.read_text()
    did = os.environ.get("DASHBOARD_ID", "").strip()
    if did:
        d = w.lakeview.update(did, Dashboard(serialized_dashboard=body, warehouse_id=warehouse_id()))
        print("updated draft", d.dashboard_id)
    else:
        me = w.current_user.me().user_name
        d = w.lakeview.create(Dashboard(display_name=TITLE, serialized_dashboard=body, warehouse_id=warehouse_id(), parent_path=f"/Users/{me}"))
        print("created", d.dashboard_id)
        write_env("DASHBOARD_ID", d.dashboard_id)
    w.lakeview.publish(d.dashboard_id, embed_credentials=False, warehouse_id=warehouse_id())  # viewers query as themselves
    host = os.environ["DATABRICKS_HOST"].rstrip("/")
    write_env("DASHBOARD_URL", f"{host}/dashboardsv3/{d.dashboard_id}/published")
    print("published", os.environ["DASHBOARD_URL"])


def pull():
    d = workspace_client().lakeview.get(os.environ["DASHBOARD_ID"])
    FILE.write_text(json.dumps(json.loads(d.serialized_dashboard), indent=2) + "\n")
    print("pulled", FILE)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        FILE.write_text(json.dumps(build(), indent=2) + "\n")
        print("wrote", FILE)
    elif cmd == "push":
        push()
    elif cmd == "pull":
        pull()
    elif cmd == "url":
        print(os.environ.get("DASHBOARD_URL", "not published yet"))
    else:
        sys.exit(__doc__)

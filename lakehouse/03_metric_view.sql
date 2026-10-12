-- Databricks only. The semantic layer: every KPI defined once, queried at any grain with MEASURE().
-- Syntax checked against the metric view YAML 1.1 reference on Oct 11, 2026 (window measures with offset, MEASURE() composability).
-- Join aliases (ag, mkt, cap) must differ from dimension names: a dimension called `agency` makes `agency.agency_name` a field lookup on a STRING.
-- If the workspace rejects a `format` key, delete that line; nothing else depends on it.

CREATE OR REPLACE VIEW aa_demo.gold.sales_metrics
WITH METRICS
LANGUAGE YAML
COMMENT 'Agency sales KPIs: AA revenue, AA share of agency sales, fair share (AA seat share from BTS T-100), share gap, year over year. Defined once here; the Power BI measures are kept equal by ops.kpi_parity.'
AS $$
version: 1.1
comment: Agency indirect sales. One row of the source is one agency, one market, one month. Share is revenue based.
source: aa_demo.gold.fact_agency_sales_monthly
joins:
  - name: ag
    source: aa_demo.gold.dim_agency
    on: source.agency_id = ag.agency_id
  - name: mkt
    source: aa_demo.gold.dim_market
    on: source.market_id = mkt.market_id
  - name: cap
    source: aa_demo.gold.fact_market_capacity
    on: source.market_id = cap.market_id AND source.sales_month = cap.sales_month
dimensions:
  - name: agency
    expr: ag.agency_name
    display_name: Agency
    synonyms: [account, travel agency, TMC, agency name]
  - name: agency_type
    expr: ag.agency_type
    display_name: Agency type
    synonyms: [channel type, TMC or OTA]
  - name: region
    expr: ag.region
    display_name: Agency region
    synonyms: [sales region, territory]
  - name: account_manager
    expr: ag.account_manager
    display_name: Account manager
    synonyms: [AM, sales rep, rep]
  - name: market
    expr: CONCAT(mkt.origin, '-', mkt.dest)
    display_name: Market
    synonyms: [route, city pair, O&D, origin destination]
  - name: origin
    expr: mkt.origin
  - name: dest
    expr: mkt.dest
    display_name: Destination
  - name: market_region
    expr: mkt.region
    display_name: Market region
  - name: sales_month
    expr: source.sales_month
    display_name: Month
    synonyms: [month, period]
  - name: quarter
    expr: CONCAT('Q', QUARTER(source.sales_month), ' ', YEAR(source.sales_month))
    display_name: Quarter
  - name: year
    expr: YEAR(source.sales_month)
    display_name: Year
  - name: capacity_is_projected
    expr: cap.is_projected
    display_name: Capacity projected
    comment: true where BTS has not published the month yet and the prior year's month stands in
measures:
  - name: aa_revenue
    expr: SUM(source.aa_revenue)
    display_name: AA revenue
    synonyms: [revenue, AA sales, ticketed revenue, our revenue]
    format:
      type: currency
      currency_code: USD
  - name: market_revenue
    expr: SUM(source.market_revenue)
    display_name: Agency market revenue
    synonyms: [total agency sales, all-carrier revenue, agency total]
    comment: what the agency sold on the market across all carriers; the denominator of share
    format:
      type: currency
      currency_code: USD
  - name: aa_pax
    expr: SUM(source.aa_pax)
    display_name: AA passengers
    synonyms: [passengers, pax, tickets]
  - name: market_pax
    expr: SUM(source.market_pax)
    display_name: Agency market passengers
  - name: aa_share
    expr: SUM(source.aa_revenue) / NULLIF(SUM(source.market_revenue), 0)
    display_name: AA share
    synonyms: [share, RSP, revenue share, AA share of agency sales, market share]
    comment: revenue based. AA revenue divided by the agency's all-carrier revenue on the same markets and months. A ratio, so it is computed at query grain, never pre-aggregated.
    format:
      type: percentage
  - name: fair_share
    expr: SUM(source.market_revenue * cap.aa_seat_share) / NULLIF(SUM(source.market_revenue), 0)
    display_name: Fair share
    synonyms: [seat share, capacity share, expected share, QSI]
    comment: AA's share of scheduled seats on the market (BTS T-100), weighted by the agency's market revenue so it is comparable with aa_share at any grain
    format:
      type: percentage
  - name: share_gap_pts
    expr: (MEASURE(aa_share) - MEASURE(fair_share)) * 100
    display_name: Share gap (points)
    synonyms: [share premium, points above fair share, share gap, over or under fair share]
    comment: positive means the agency sells more AA than AA's seat share would predict
  - name: share_gap_usd
    expr: SUM(source.aa_revenue) - SUM(source.market_revenue * cap.aa_seat_share)
    display_name: Share gap (dollars)
    synonyms: [share gap in dollars, revenue above fair share, revenue opportunity]
    comment: AA revenue minus the revenue AA would have at fair share
    format:
      type: currency
      currency_code: USD
  - name: aa_revenue_prior_year
    expr: SUM(source.aa_revenue)
    display_name: AA revenue, same month prior year
    synonyms: [last year revenue, prior year, LY]
    window:
      - order: sales_month
        range: current
        semiadditive: last
        offset: -12 month
  - name: yoy_revenue_pct
    expr: (MEASURE(aa_revenue) - MEASURE(aa_revenue_prior_year)) / NULLIF(MEASURE(aa_revenue_prior_year), 0)
    display_name: Year over year revenue change
    synonyms: [YoY, year over year, growth, versus last year, vs LY]
    comment: month grain. Group by sales_month for a correct answer; for quarters use the trusted SQL asset in the Genie agent.
    format:
      type: percentage
$$;

-- Smoke test (expected on first run: 12 agencies, revenue, share near 0.3 to 0.5, fair share near 0.2 to 0.55)
-- SELECT agency, MEASURE(aa_revenue) AS aa_revenue, MEASURE(aa_share) AS aa_share, MEASURE(fair_share) AS fair_share,
--        MEASURE(share_gap_pts) AS gap_pts, MEASURE(share_gap_usd) AS gap_usd
-- FROM aa_demo.gold.sales_metrics WHERE year = 2026 GROUP BY ALL ORDER BY aa_revenue DESC;

-- The definitions desk: one row per KPI. English first, then the metric view expression, then the Power BI (DAX)
-- twin, then a second SQL implementation that stands in for the DAX measure in the parity job (Power BI Desktop is
-- Windows only). twin_sql returns (agency, sales_month, value) and is compared with MEASURE() by lakehouse/parity.py.
-- twin_sql_retired keeps the definition that parity caught, so the drift story is on record rather than staged.
-- Portable SQL.

CREATE OR REPLACE TABLE aa_demo.ops.kpi_definitions (
  kpi STRING, display_name STRING, definition_en STRING, owner STRING, source_columns STRING,
  metric_view_expr STRING, dax_twin STRING, twin_sql STRING, twin_version STRING, twin_sql_retired STRING, retired_note STRING
);

INSERT INTO aa_demo.ops.kpi_definitions VALUES
('aa_revenue', 'AA revenue',
 'Ticketed revenue on AA sold by the agency, in US dollars, for the markets and months selected.',
 'Sales BI', 'gold.fact_agency_sales_monthly.aa_revenue',
 'SUM(source.aa_revenue)',
 'AA Revenue = SUM ( fact_agency_sales_monthly[aa_revenue] )',
 'SELECT a.agency_name AS agency, s.sales_month, SUM(s.aa_revenue) AS value FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id GROUP BY ALL',
 'v1', NULL, NULL),

('aa_share', 'AA share',
 'AA revenue divided by everything the agency sold on the same markets and months, across all carriers. Revenue based, not passenger based. A ratio: computed at the grain of the question, never averaged from pre-computed shares.',
 'Sales BI', 'gold.fact_agency_sales_monthly.aa_revenue, market_revenue',
 'SUM(source.aa_revenue) / NULLIF(SUM(source.market_revenue), 0)',
 'AA Share = DIVIDE ( SUM ( fact_agency_sales_monthly[aa_revenue] ), SUM ( fact_agency_sales_monthly[market_revenue] ) )',
 'SELECT a.agency_name AS agency, s.sales_month, SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) AS value FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id GROUP BY ALL',
 'v2',
 'SELECT a.agency_name AS agency, s.sales_month, SUM(s.aa_pax) * 1.0 / NULLIF(SUM(s.market_pax), 0) AS value FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id GROUP BY ALL',
 'v1 was passenger based (AA passengers over agency passengers). Parity against the metric view ran red on every month; retired and replaced by the revenue-based v2 in the same pull request.'),

('fair_share', 'Fair share',
 'AA''s share of scheduled seats on the market, weighted by the agency''s market revenue so it is comparable with AA share at any grain. The share an agency would sell if it were carrier neutral. The seat shares here are made up, one per route; the T-100 loader (data/t100.py) has never run.',
 'Sales BI', 'gold.fact_market_capacity.aa_seat_share, gold.fact_agency_sales_monthly.market_revenue',
 'SUM(source.market_revenue * capacity.aa_seat_share) / NULLIF(SUM(source.market_revenue), 0)',
 'Fair Share = DIVIDE ( SUMX ( fact_agency_sales_monthly, fact_agency_sales_monthly[market_revenue] * RELATED ( fact_market_capacity[aa_seat_share] ) ), SUM ( fact_agency_sales_monthly[market_revenue] ) )',
 'SELECT a.agency_name AS agency, s.sales_month, SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0) AS value FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month GROUP BY ALL',
 'v1', NULL, NULL),

('share_gap_pts', 'Share gap (points)',
 'AA share minus fair share, in percentage points. Positive: the agency sells more AA than AA''s seats would predict. The number account managers call the share premium.',
 'Sales BI', 'derived from aa_share and fair_share',
 '(MEASURE(aa_share) - MEASURE(fair_share)) * 100',
 'Share Gap Pts = ( [AA Share] - [Fair Share] ) * 100',
 'SELECT a.agency_name AS agency, s.sales_month, (SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) - SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0)) * 100 AS value FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month GROUP BY ALL',
 'v1', NULL, NULL),

('share_gap_usd', 'Share gap (dollars)',
 'AA revenue minus the revenue AA would have if the agency sold exactly fair share. The dollar value of being above or below fair share.',
 'Sales BI', 'gold.fact_agency_sales_monthly.aa_revenue, market_revenue; gold.fact_market_capacity.aa_seat_share',
 'SUM(source.aa_revenue) - SUM(source.market_revenue * capacity.aa_seat_share)',
 'Share Gap USD = SUM ( fact_agency_sales_monthly[aa_revenue] ) - SUMX ( fact_agency_sales_monthly, fact_agency_sales_monthly[market_revenue] * RELATED ( fact_market_capacity[aa_seat_share] ) )',
 'SELECT a.agency_name AS agency, s.sales_month, SUM(s.aa_revenue) - SUM(s.market_revenue * c.aa_seat_share) AS value FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month GROUP BY ALL',
 'v1', NULL, NULL),

('yoy_revenue_pct', 'Year over year revenue change',
 'AA revenue this month versus the same calendar month one year earlier, as a percentage of the earlier month. Calendar months, not fiscal. A month with no prior-year row has no YoY.',
 'Sales BI', 'gold.fact_agency_sales_monthly.aa_revenue (window measure, offset -12 month)',
 'window measure aa_revenue_prior_year: order sales_month, range current, offset -12 month; yoy_revenue_pct = (MEASURE(aa_revenue) - MEASURE(aa_revenue_prior_year)) / NULLIF(MEASURE(aa_revenue_prior_year), 0)',
 'YoY Revenue % = VAR ly = CALCULATE ( [AA Revenue], DATEADD ( ''Date''[Date], -1, YEAR ) ) RETURN DIVIDE ( [AA Revenue] - ly, ly )',
 'WITH m AS (SELECT a.agency_name AS agency, s.sales_month, SUM(s.aa_revenue) AS rev FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id GROUP BY ALL) SELECT c.agency, c.sales_month, (c.rev - p.rev) / NULLIF(p.rev, 0) AS value FROM m c JOIN m p ON p.agency = c.agency AND EXTRACT(YEAR FROM p.sales_month) = EXTRACT(YEAR FROM c.sales_month) - 1 AND EXTRACT(MONTH FROM p.sales_month) = EXTRACT(MONTH FROM c.sales_month)',
 'v1', NULL, NULL),

('pace_pct', 'Pace against goal',
 'Year-to-date AA revenue divided by the year-to-date share of the annual revenue goal: one twelfth of the goal for each month the agency reported, so a month with no rows never counts as zero. 100 means on pace. Lives in gold.agency_pace, not in the metric view, because the goal is set per agency and year.',
 'Sales planning', 'gold.agency_pace.pace_pct (from fact_agency_sales_monthly and agency_goals)',
 'not a metric view measure; see gold.agency_pace',
 'Pace % = VAR ytdRevenue = TOTALYTD ( [AA Revenue], ''Date''[Date] ) VAR ytdGoal = SUMX ( VALUES ( dim_agency[agency_id] ), [Revenue Goal] * CALCULATE ( DISTINCTCOUNT ( fact_agency_sales_monthly[sales_month] ), DATESYTD ( ''Date''[Date] ) ) / 12 ) RETURN DIVIDE ( ytdRevenue, ytdGoal ) * 100',
 'SELECT a.agency_name AS agency, p.sales_month, p.pace_pct AS value FROM aa_demo.gold.agency_pace p JOIN aa_demo.gold.dim_agency a ON a.agency_id = p.agency_id',
 'v1', NULL, NULL);

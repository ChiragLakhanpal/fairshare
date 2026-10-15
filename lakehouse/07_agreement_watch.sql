-- Agreement watch: every measurable clause checked against the data for every month of 2026. Portable SQL.
-- gold.contract_clauses is the thinking model's reading of the four agreements (lakehouse/clauses.py), reviewed and
-- committed. This file is the checker: one row per clause per month with the value, the line, the distance, the
-- consecutive closed quarters below the line, the dollars attached, and a status the Agreement watch agent reads:
--   breached        the rule's condition holds: quarters_below >= window_quarters, or the projected year-end attainment
--                   sits under a line a consequence attaches to
--   watch           within two points of a floor (ten for a revenue ratio), within three points of a tier line, one
--                   quarter short of the window, within five attainment points, or a goal or commitment not on pace
--   ok              nothing to do
--   not_checkable   notice periods, due dates, service levels, display rules: not in the sales data
-- Year-to-date measures use the months of the year up to the as-of month; quarter rules use closed calendar quarters only.
-- The model never computes: projections, distances and dollars are columns here.

CREATE OR REPLACE TABLE aa_demo.ops.agreement_checks AS
WITH months AS (
  SELECT DISTINCT sales_month AS as_of FROM aa_demo.gold.fact_agency_sales_monthly WHERE sales_month >= DATE '2026-01-01'
), cl AS (
  SELECT c.clause_id, c.agency_id, a.agency_name, c.file, c.page, c.section, c.clause_type, c.metric,
         c.threshold, c.threshold_2, c.window_quarters, c.consequence, c.quote
  FROM aa_demo.gold.contract_clauses c JOIN aa_demo.gold.dim_agency a ON a.agency_id = c.agency_id
), ytd AS (
  SELECT m.as_of, s.agency_id, CAST(EXTRACT(MONTH FROM m.as_of) AS INT) AS months_elapsed,
         SUM(s.aa_revenue) AS ytd_revenue, SUM(s.market_revenue) AS ytd_market, SUM(s.market_revenue * c.aa_seat_share) AS ytd_fair
  FROM months m
  JOIN aa_demo.gold.fact_agency_sales_monthly s ON s.sales_month >= DATE '2026-01-01' AND s.sales_month <= m.as_of
  JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
  GROUP BY ALL
), ytd_m AS (
  SELECT as_of, agency_id, months_elapsed, ytd_revenue,
         ytd_revenue / NULLIF(ytd_market, 0) * 100 AS share_pct,
         (ytd_revenue - ytd_fair) / NULLIF(ytd_market, 0) * 100 AS premium_pts
  FROM ytd
), q AS (
  SELECT agency_id, CAST(EXTRACT(YEAR FROM sales_month) AS INT) AS yr, CAST(EXTRACT(QUARTER FROM sales_month) AS INT) AS qtr,
         SUM(aa_revenue) / NULLIF(SUM(market_revenue), 0) * 100 AS share_pct, SUM(aa_revenue) AS revenue,
         COUNT(DISTINCT sales_month) AS months_in, MAX(sales_month) AS last_month
  FROM aa_demo.gold.fact_agency_sales_monthly GROUP BY ALL
), qq AS (
  SELECT c.agency_id, c.yr * 4 + c.qtr AS qn, c.share_pct, c.last_month,
         c.revenue / NULLIF(p.revenue, 0) * 100 AS yoy_ratio_pct
  FROM q c LEFT JOIN q p ON p.agency_id = c.agency_id AND p.yr = c.yr - 1 AND p.qtr = c.qtr
  WHERE c.months_in = 3
), qf AS (
  SELECT cl.clause_id, m.as_of, qq.qn,
         CASE cl.clause_type WHEN 'share_floor_quarters' THEN qq.share_pct ELSE qq.yoy_ratio_pct END AS q_value,
         CASE WHEN cl.clause_type = 'share_floor_quarters' AND qq.share_pct < cl.threshold THEN 1
              WHEN cl.clause_type = 'revenue_decline_quarters' AND qq.yoy_ratio_pct < cl.threshold THEN 1 ELSE 0 END AS below,
         ROW_NUMBER() OVER (PARTITION BY cl.clause_id, m.as_of ORDER BY qq.qn DESC) AS rn
  FROM cl CROSS JOIN months m
  JOIN qq ON qq.agency_id = cl.agency_id AND qq.last_month <= m.as_of
  WHERE cl.clause_type IN ('share_floor_quarters', 'revenue_decline_quarters')
), qs AS (
  SELECT f.clause_id, f.as_of,
         COALESCE(MIN(CASE WHEN f.below = 0 THEN f.rn END) - 1, MAX(f.rn)) AS quarters_below,
         MAX(CASE WHEN f.rn = 1 THEN f.q_value END) AS latest_value
  FROM qf f GROUP BY ALL
), quarter_rows AS (
  SELECT cl.clause_id, cl.agency_id, cl.agency_name, m.as_of, cl.clause_type, cl.section, cl.metric,
         qs.latest_value AS value, cl.threshold, qs.latest_value - cl.threshold AS distance,
         CASE WHEN cl.clause_type = 'share_floor_quarters' THEN 'pts' ELSE 'pct' END AS unit,
         CAST(COALESCE(qs.quarters_below, 0) AS INT) AS quarters_below, cl.window_quarters,
         CAST(NULL AS DOUBLE) AS dollars, CAST(NULL AS STRING) AS dollars_label,
         CASE WHEN COALESCE(qs.quarters_below, 0) >= cl.window_quarters THEN 'breached'
              WHEN COALESCE(qs.quarters_below, 0) > 0 AND COALESCE(qs.quarters_below, 0) >= cl.window_quarters - 1 THEN 'watch'
              WHEN qs.latest_value - cl.threshold < CASE WHEN cl.clause_type = 'share_floor_quarters' THEN 2 ELSE 10 END THEN 'watch'
              ELSE 'ok' END AS status,
         cl.consequence, cl.file, cl.page, cl.quote
  FROM cl CROSS JOIN months m
  LEFT JOIN qs ON qs.clause_id = cl.clause_id AND qs.as_of = m.as_of
  WHERE cl.clause_type IN ('share_floor_quarters', 'revenue_decline_quarters')
), tv AS (
  SELECT cl.*, m.as_of, y.ytd_revenue,
         CASE cl.clause_type WHEN 'share_tiers' THEN y.share_pct ELSE y.premium_pts END AS value,
         MIN(COALESCE(cl.threshold, -1000000000)) OVER (PARTITION BY cl.agency_id, cl.clause_type) AS lowest
  FROM cl CROSS JOIN months m
  JOIN ytd_m y ON y.agency_id = cl.agency_id AND y.as_of = m.as_of
  WHERE cl.clause_type IN ('share_premium_tiers', 'share_tiers', 'gap_tiers')
), tier_rows AS (
  SELECT clause_id, agency_id, agency_name, as_of, clause_type, section, metric,
         value, threshold, value - threshold AS distance,
         CASE WHEN clause_type = 'share_tiers' THEN 'pct' ELSE 'pts' END AS unit,
         CAST(NULL AS INT) AS quarters_below, window_quarters,
         ytd_revenue * COALESCE(threshold_2, 0) / 100 AS dollars, 'incentive at this tier, year to date' AS dollars_label,
         -- a tier's lower bound is a line worth watching only when a band exists below it: the band with no lower bound
         -- (NULL) never is, and the lowest band that earns nothing (Summit's tier 1) is not a line either
         CASE WHEN threshold IS NULL OR (threshold = lowest AND COALESCE(threshold_2, 0) = 0) THEN 'ok'
              WHEN ABS(value - threshold) < 3 THEN 'watch' ELSE 'ok' END AS status,
         consequence, file, page, quote
  FROM tv
), cv AS (
  SELECT cl.*, m.as_of, y.ytd_revenue, y.months_elapsed,
         y.ytd_revenue * 12.0 / NULLIF(y.months_elapsed, 0) AS projected,
         y.ytd_revenue * 12.0 / NULLIF(y.months_elapsed, 0) / NULLIF(cl.threshold, 0) * 100 AS value,
         COALESCE(cl.threshold_2, 100) AS line, fe.threshold AS fe_pct
  FROM cl CROSS JOIN months m
  JOIN ytd_m y ON y.agency_id = cl.agency_id AND y.as_of = m.as_of
  LEFT JOIN cl fe ON fe.agency_id = cl.agency_id AND fe.clause_type = 'front_end_incentive'
  WHERE cl.clause_type IN ('annual_commitment', 'goal') AND cl.metric = 'aa_revenue'
), commit_rows AS (
  SELECT clause_id, agency_id, agency_name, as_of, clause_type, section, metric,
         value, line AS threshold, value - line AS distance, 'pct' AS unit,
         CAST(NULL AS INT) AS quarters_below, window_quarters,
         CASE WHEN clause_type = 'annual_commitment' THEN ytd_revenue * COALESCE(fe_pct, 0) / 100 ELSE GREATEST(threshold - projected, 0) END AS dollars,
         CASE WHEN clause_type = 'annual_commitment' THEN 'advanced incentive at risk' ELSE 'shortfall at this pace' END AS dollars_label,
         CASE WHEN clause_type = 'annual_commitment' AND threshold_2 IS NOT NULL AND value < line THEN 'breached'
              WHEN value < line THEN 'watch'
              WHEN value - line < 5 THEN 'watch' ELSE 'ok' END AS status,
         consequence, file, page, quote
  FROM cv
), goal_share_rows AS (
  SELECT cl.clause_id, cl.agency_id, cl.agency_name, m.as_of, cl.clause_type, cl.section, cl.metric,
         y.share_pct AS value, cl.threshold, y.share_pct - cl.threshold AS distance, 'pts' AS unit,
         CAST(NULL AS INT) AS quarters_below, cl.window_quarters,
         CAST(NULL AS DOUBLE) AS dollars, CAST(NULL AS STRING) AS dollars_label,
         CASE WHEN y.share_pct < cl.threshold THEN 'watch' ELSE 'ok' END AS status,
         cl.consequence, cl.file, cl.page, cl.quote
  FROM cl CROSS JOIN months m
  JOIN ytd_m y ON y.agency_id = cl.agency_id AND y.as_of = m.as_of
  WHERE cl.clause_type = 'goal' AND cl.metric = 'aa_share'
), capv AS (
  SELECT cl.clause_id, m.as_of, MIN((c.aa_seats - p.aa_seats) * 100.0 / NULLIF(p.aa_seats, 0)) AS value
  FROM cl CROSS JOIN months m
  JOIN (SELECT DISTINCT agency_id, market_id FROM aa_demo.gold.fact_agency_sales_monthly) am ON am.agency_id = cl.agency_id
  JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = am.market_id AND c.sales_month = m.as_of
  JOIN aa_demo.gold.fact_market_capacity p ON p.market_id = am.market_id
   AND EXTRACT(YEAR FROM p.sales_month) = EXTRACT(YEAR FROM m.as_of) - 1 AND EXTRACT(MONTH FROM p.sales_month) = EXTRACT(MONTH FROM m.as_of)
  WHERE cl.clause_type = 'capacity_exclusion'
  GROUP BY ALL
), capacity_rows AS (
  SELECT cl.clause_id, cl.agency_id, cl.agency_name, v.as_of, cl.clause_type, cl.section, cl.metric,
         v.value, cl.threshold, v.value - cl.threshold AS distance, 'pct' AS unit,
         CAST(NULL AS INT) AS quarters_below, cl.window_quarters,
         CAST(NULL AS DOUBLE) AS dollars, CAST(NULL AS STRING) AS dollars_label,
         CASE WHEN v.value < cl.threshold THEN 'watch' ELSE 'ok' END AS status,
         cl.consequence, cl.file, cl.page, cl.quote
  FROM cl JOIN capv v ON v.clause_id = cl.clause_id
), incentive_rows AS (
  SELECT cl.clause_id, cl.agency_id, cl.agency_name, m.as_of, cl.clause_type, cl.section, cl.metric,
         y.ytd_revenue AS value, cl.threshold, CAST(NULL AS DOUBLE) AS distance, 'usd' AS unit,
         CAST(NULL AS INT) AS quarters_below, cl.window_quarters,
         y.ytd_revenue * cl.threshold / 100 AS dollars, 'advanced incentive to date' AS dollars_label,
         'ok' AS status, cl.consequence, cl.file, cl.page, cl.quote
  FROM cl CROSS JOIN months m
  JOIN ytd_m y ON y.agency_id = cl.agency_id AND y.as_of = m.as_of
  WHERE cl.clause_type = 'front_end_incentive'
), other_rows AS (
  SELECT cl.clause_id, cl.agency_id, cl.agency_name, m.as_of, cl.clause_type, cl.section, cl.metric,
         CAST(NULL AS DOUBLE) AS value, cl.threshold, CAST(NULL AS DOUBLE) AS distance, CAST(NULL AS STRING) AS unit,
         CAST(NULL AS INT) AS quarters_below, cl.window_quarters,
         CAST(NULL AS DOUBLE) AS dollars, CAST(NULL AS STRING) AS dollars_label,
         'not_checkable' AS status, cl.consequence, cl.file, cl.page, cl.quote
  FROM cl CROSS JOIN months m
  WHERE cl.clause_type = 'not_checkable'
     OR (cl.clause_type = 'goal' AND cl.metric NOT IN ('aa_revenue', 'aa_share'))
), u AS (
  SELECT * FROM quarter_rows UNION ALL SELECT * FROM tier_rows UNION ALL SELECT * FROM commit_rows UNION ALL SELECT * FROM goal_share_rows
  UNION ALL SELECT * FROM capacity_rows UNION ALL SELECT * FROM incentive_rows UNION ALL SELECT * FROM other_rows
)
SELECT clause_id, agency_id, agency_name, as_of, clause_type, section, metric,
       ROUND(value, 1) AS value, threshold, ROUND(distance, 1) AS distance, unit, quarters_below, window_quarters,
       ROUND(dollars, 0) AS dollars, dollars_label, status, consequence, file, page, quote
FROM u;

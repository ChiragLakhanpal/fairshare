-- Why did an agency's AA revenue change versus the same month last year? Portable SQL.
--
-- For agency a, month m versus m-12, with T = the agency's all-carrier revenue on its markets,
-- w_k = market k's weight in T (mix), s_k = AA share within market k:
--   volume = (T' - T) * (R / T)                        the agency sold more or less travel overall
--   mix    = T' * sum_k (w'_k - w_k) * s_k             it shifted which markets it sells, at old shares
--   share  = T' * sum_k (s'_k - s_k) * w'_k            AA won or lost share within markets
--   volume + mix + share = R' - R exactly (cross terms cancel; a market new this year uses s_k = s'_k, so it lands in mix)
--   fair_share_effect = T' * sum_k (f'_k - f_k) * w'_k   diagnostic, not part of the sum: the share move AA's own capacity would explain
-- evals/test_decomposition.py asserts the identity on every row.
-- Column names: SQL identifiers are case-insensitive, so market-level t_now and agency-level totals get different names (tot_now).

CREATE OR REPLACE TABLE aa_demo.ops.decomposition_markets AS
WITH cur AS (
  SELECT s.agency_id, s.market_id, s.sales_month, s.aa_revenue, s.market_revenue, c.aa_seat_share
  FROM aa_demo.gold.fact_agency_sales_monthly s
  JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
), pri AS (
  SELECT agency_id, market_id, sales_month, aa_revenue, market_revenue, aa_seat_share FROM cur
), paired AS (
  SELECT COALESCE(a.agency_id, b.agency_id) AS agency_id,
         COALESCE(a.market_id, b.market_id) AS market_id,
         COALESCE(a.sales_month, CAST(CONCAT(CAST(EXTRACT(YEAR FROM b.sales_month) + 1 AS STRING), '-', LPAD(CAST(EXTRACT(MONTH FROM b.sales_month) AS STRING), 2, '0'), '-01') AS DATE)) AS sales_month,
         COALESCE(a.aa_revenue, 0) AS r_now, COALESCE(a.market_revenue, 0) AS t_now, a.aa_seat_share AS f_now,
         COALESCE(b.aa_revenue, 0) AS r_prior, COALESCE(b.market_revenue, 0) AS t_prior, b.aa_seat_share AS f_prior
  FROM cur a
  FULL OUTER JOIN pri b
    ON a.agency_id = b.agency_id AND a.market_id = b.market_id
   AND EXTRACT(YEAR FROM a.sales_month) = EXTRACT(YEAR FROM b.sales_month) + 1
   AND EXTRACT(MONTH FROM a.sales_month) = EXTRACT(MONTH FROM b.sales_month)
), tot AS (
  SELECT agency_id, sales_month, SUM(t_now) AS tot_now, SUM(t_prior) AS tot_prior, SUM(r_now) AS rev_now, SUM(r_prior) AS rev_prior
  FROM paired GROUP BY ALL
), k AS (
  SELECT p.agency_id, p.sales_month, p.market_id, p.r_now, p.t_now, p.r_prior, p.t_prior, p.f_now, p.f_prior,
         p.t_now / NULLIF(t.tot_now, 0) AS w_now,
         p.t_prior / NULLIF(t.tot_prior, 0) AS w_prior,
         p.r_now / NULLIF(p.t_now, 0) AS s_now,
         CASE WHEN p.t_prior > 0 THEN p.r_prior / p.t_prior ELSE p.r_now / NULLIF(p.t_now, 0) END AS s_prior,
         t.tot_now, t.tot_prior, t.rev_now, t.rev_prior
  FROM paired p JOIN tot t ON t.agency_id = p.agency_id AND t.sales_month = p.sales_month
)
SELECT agency_id, sales_month, market_id,
       ROUND(r_now, 2) AS aa_revenue_now, ROUND(r_prior, 2) AS aa_revenue_prior,
       ROUND(t_now, 2) AS market_revenue_now, ROUND(t_prior, 2) AS market_revenue_prior,
       ROUND(s_now, 4) AS aa_share_now, ROUND(CASE WHEN t_prior > 0 THEN r_prior / t_prior END, 4) AS aa_share_prior,
       ROUND(f_now, 4) AS fair_share_now, ROUND(f_prior, 4) AS fair_share_prior,
       -- unrounded so the agency-level sums reconcile to the cent; the app rounds for display
       tot_now * (COALESCE(w_now, 0) - COALESCE(w_prior, 0)) * COALESCE(s_prior, 0) AS mix_effect,
       tot_now * (COALESCE(s_now, 0) - COALESCE(s_prior, 0)) * COALESCE(w_now, 0) AS share_effect,
       tot_now * (COALESCE(f_now, 0) - COALESCE(f_prior, 0)) * COALESCE(w_now, 0) AS fair_share_effect
FROM k
WHERE tot_prior > 0 AND tot_now > 0;

CREATE OR REPLACE TABLE aa_demo.ops.decomposition AS
WITH tot AS (
  SELECT agency_id, sales_month,
         SUM(aa_revenue_now) AS revenue_now, SUM(aa_revenue_prior) AS revenue_prior,
         SUM(market_revenue_now) AS market_now, SUM(market_revenue_prior) AS market_prior,
         SUM(mix_effect) AS mix_effect, SUM(share_effect) AS share_effect, SUM(fair_share_effect) AS fair_share_effect,
         SUM(market_revenue_now * COALESCE(fair_share_now, 0)) / NULLIF(SUM(market_revenue_now), 0) AS fair_share_now,
         SUM(market_revenue_prior * COALESCE(fair_share_prior, 0)) / NULLIF(SUM(market_revenue_prior), 0) AS fair_share_prior
  FROM aa_demo.ops.decomposition_markets
  GROUP BY ALL
)
SELECT agency_id, sales_month,
       ROUND(revenue_now, 2) AS revenue_now, ROUND(revenue_prior, 2) AS revenue_prior,
       ROUND(revenue_now - revenue_prior, 2) AS delta_revenue,
       ROUND((revenue_now - revenue_prior) / NULLIF(revenue_prior, 0) * 100, 1) AS delta_pct,
       ROUND(market_now, 2) AS market_now, ROUND(market_prior, 2) AS market_prior,
       ROUND((market_now - market_prior) / NULLIF(market_prior, 0) * 100, 1) AS market_delta_pct,
       ROUND(revenue_now / NULLIF(market_now, 0), 4) AS aa_share_now,
       ROUND(revenue_prior / NULLIF(market_prior, 0), 4) AS aa_share_prior,
       ROUND(fair_share_now, 4) AS fair_share_now, ROUND(fair_share_prior, 4) AS fair_share_prior,
       ROUND((market_now - market_prior) * (revenue_prior / NULLIF(market_prior, 0)), 2) AS volume_effect,
       ROUND(mix_effect, 2) AS mix_effect,
       ROUND(share_effect, 2) AS share_effect,
       ROUND(fair_share_effect, 2) AS fair_share_effect,
       ROUND((market_now - market_prior) * (revenue_prior / NULLIF(market_prior, 0)) + mix_effect + share_effect - (revenue_now - revenue_prior), 2) AS residual
FROM tot;

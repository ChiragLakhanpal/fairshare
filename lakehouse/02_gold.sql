-- Gold: the tables the metric view, Genie, the decomposition, and the app read. Portable SQL.

CREATE OR REPLACE TABLE aa_demo.gold.dim_agency AS SELECT * FROM aa_demo.silver.dim_agency;
CREATE OR REPLACE TABLE aa_demo.gold.dim_corporate AS SELECT * FROM aa_demo.silver.dim_corporate;
CREATE OR REPLACE TABLE aa_demo.gold.dim_market AS SELECT * FROM aa_demo.silver.dim_market;
CREATE OR REPLACE TABLE aa_demo.gold.agency_goals AS SELECT * FROM aa_demo.silver.agency_goals;
CREATE OR REPLACE TABLE aa_demo.gold.fact_market_capacity AS SELECT * FROM aa_demo.silver.fact_market_capacity;
CREATE OR REPLACE TABLE aa_demo.gold.fact_agency_sales_monthly AS SELECT * FROM aa_demo.silver.fact_agency_sales_monthly;
CREATE OR REPLACE TABLE aa_demo.gold.fact_corporate_bookings AS SELECT * FROM aa_demo.silver.fact_corporate_bookings;
CREATE OR REPLACE TABLE aa_demo.gold.crm_contacts AS SELECT * FROM aa_demo.silver.crm_contacts;
CREATE OR REPLACE TABLE aa_demo.gold.crm_opportunities AS SELECT * FROM aa_demo.silver.crm_opportunities;
CREATE OR REPLACE TABLE aa_demo.gold.crm_activities AS SELECT * FROM aa_demo.silver.crm_activities;

-- Pace against the annual revenue goal, agency by month. Kept as a gold table rather than a metric view
-- measure because the goal lives at agency-year grain and would multiply across markets in the fact join.
CREATE OR REPLACE TABLE aa_demo.gold.agency_pace AS
WITH m AS (
  SELECT agency_id, sales_month, CAST(EXTRACT(YEAR FROM sales_month) AS INT) AS goal_year, SUM(aa_revenue) AS aa_revenue
  FROM aa_demo.gold.fact_agency_sales_monthly
  GROUP BY ALL
), y AS (
  SELECT m.agency_id, m.goal_year, m.sales_month, m.aa_revenue,
         SUM(m.aa_revenue) OVER (PARTITION BY m.agency_id, m.goal_year ORDER BY m.sales_month) AS ytd_revenue,
         g.revenue_goal_usd, g.revenue_goal_usd * EXTRACT(MONTH FROM m.sales_month) / 12.0 AS ytd_goal
  FROM m JOIN aa_demo.gold.agency_goals g ON g.agency_id = m.agency_id AND g.goal_year = m.goal_year
)
SELECT agency_id, goal_year, sales_month, ROUND(aa_revenue, 2) AS aa_revenue, ROUND(ytd_revenue, 2) AS ytd_revenue,
       revenue_goal_usd, ROUND(ytd_goal, 2) AS ytd_goal, ROUND(ytd_revenue / NULLIF(ytd_goal, 0) * 100, 1) AS pace_pct,
       ROUND(ytd_revenue / NULLIF(revenue_goal_usd, 0) * 100, 1) AS attainment_pct
FROM y;

-- Weekly corporate bookings with week-over-week change. The column is called wow_pct on purpose:
-- it is the one the Monday summary's model is tempted to misread, and the verifier catches it.
CREATE OR REPLACE TABLE aa_demo.gold.fact_corporate_bookings_weekly AS
WITH w AS (
  SELECT CAST(DATE_TRUNC('week', booking_date) AS DATE) AS week_start, corp_id,
         SUM(fare_usd * ticket_count) AS booked_revenue, SUM(ticket_count) AS tickets
  FROM aa_demo.gold.fact_corporate_bookings
  GROUP BY ALL
), l AS (
  SELECT *, LAG(booked_revenue) OVER (PARTITION BY corp_id ORDER BY week_start) AS prior_week_revenue FROM w
)
SELECT week_start, corp_id, ROUND(booked_revenue, 2) AS booked_revenue, tickets, ROUND(prior_week_revenue, 2) AS prior_week_revenue,
       ROUND((booked_revenue - prior_week_revenue) / NULLIF(prior_week_revenue, 0) * 100, 1) AS wow_pct
FROM l;

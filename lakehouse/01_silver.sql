-- Silver: typed, cleaned, deduplicated. Portable SQL: runs on Databricks SQL and on DuckDB (lakehouse/run.py).

CREATE OR REPLACE TABLE aa_demo.silver.dim_agency AS
SELECT CAST(agency_id AS INT) AS agency_id, agency_name, agency_type, region, account_manager
FROM aa_demo.bronze.dim_agency;

CREATE OR REPLACE TABLE aa_demo.silver.dim_corporate AS
SELECT CAST(corp_id AS INT) AS corp_id, corp_name, industry, hq_city,
       CAST(contract_start AS DATE) AS contract_start, CAST(contract_end AS DATE) AS contract_end,
       CAST(annual_commitment_usd AS DOUBLE) AS annual_commitment_usd
FROM aa_demo.bronze.dim_corporate;

CREATE OR REPLACE TABLE aa_demo.silver.dim_market AS
SELECT CAST(market_id AS INT) AS market_id, origin, dest, region, CAST(aa_hub_origin AS BOOLEAN) AS aa_hub_origin
FROM aa_demo.bronze.dim_market;

CREATE OR REPLACE TABLE aa_demo.silver.fact_agency_sales_monthly AS
SELECT CAST(agency_id AS INT) AS agency_id, CAST(market_id AS INT) AS market_id, CAST(sales_month AS DATE) AS sales_month,
       CAST(aa_revenue AS DOUBLE) AS aa_revenue, CAST(aa_pax AS INT) AS aa_pax,
       CAST(market_revenue AS DOUBLE) AS market_revenue, CAST(market_pax AS INT) AS market_pax
FROM aa_demo.bronze.fact_agency_sales_monthly;

CREATE OR REPLACE TABLE aa_demo.silver.fact_market_capacity AS
SELECT CAST(market_id AS INT) AS market_id, CAST(sales_month AS DATE) AS sales_month,
       CAST(aa_seats AS BIGINT) AS aa_seats, CAST(total_seats AS BIGINT) AS total_seats,
       CAST(aa_seat_share AS DOUBLE) AS aa_seat_share, CAST(is_projected AS BOOLEAN) AS is_projected, source
FROM aa_demo.bronze.fact_market_capacity;

CREATE OR REPLACE TABLE aa_demo.silver.agency_goals AS
SELECT CAST(agency_id AS INT) AS agency_id, CAST(goal_year AS INT) AS goal_year,
       CAST(revenue_goal_usd AS DOUBLE) AS revenue_goal_usd, CAST(share_goal AS DOUBLE) AS share_goal
FROM aa_demo.bronze.agency_goals;

-- The two data-quality traps live here: stray case and whitespace in channel, and tickets loaded twice.
CREATE OR REPLACE TABLE aa_demo.silver.fact_corporate_bookings AS
SELECT CAST(booking_id AS BIGINT) AS booking_id, CAST(ticket_number AS STRING) AS ticket_number, CAST(corp_id AS INT) AS corp_id,
       CAST(booking_date AS DATE) AS booking_date, CAST(travel_date AS DATE) AS travel_date, origin, dest,
       CASE UPPER(TRIM(channel)) WHEN 'NDC' THEN 'NDC' WHEN 'GDS' THEN 'GDS' WHEN 'OTA' THEN 'OTA' WHEN 'DIRECT' THEN 'Direct' ELSE 'Unknown' END AS channel,
       CAST(fare_usd AS DOUBLE) AS fare_usd, CAST(ticket_count AS INT) AS ticket_count, cabin, CAST(agency_id AS INT) AS agency_id
FROM aa_demo.bronze.fact_corporate_bookings
QUALIFY ROW_NUMBER() OVER (PARTITION BY ticket_number ORDER BY booking_id) = 1;

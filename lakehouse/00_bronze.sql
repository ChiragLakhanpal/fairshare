-- Databricks only. Creates the catalog, the schemas, the landing volume, and loads the CSVs as bronze.
-- Before running: upload data/out/*.csv and data/contracts/*.md to the landing volume, for example
--   databricks fs cp -r data/out dbfs:/Volumes/aa_demo/bronze/landing
--   databricks fs cp -r data/contracts dbfs:/Volumes/aa_demo/ops/contracts
-- (or drag them in through Catalog Explorer).
-- At AA the landing step is Fabric Data Factory into OneLake, read by Databricks through Unity Catalog;
-- here the files go straight into a Unity Catalog volume.

CREATE CATALOG IF NOT EXISTS aa_demo;
CREATE SCHEMA IF NOT EXISTS aa_demo.bronze;
CREATE SCHEMA IF NOT EXISTS aa_demo.silver;
CREATE SCHEMA IF NOT EXISTS aa_demo.gold;
CREATE SCHEMA IF NOT EXISTS aa_demo.ops;
CREATE VOLUME IF NOT EXISTS aa_demo.bronze.landing;
CREATE VOLUME IF NOT EXISTS aa_demo.ops.contracts;

CREATE OR REPLACE TABLE aa_demo.bronze.dim_agency AS
SELECT * EXCEPT (_rescued_data) FROM read_files('/Volumes/aa_demo/bronze/landing/dim_agency.csv', format => 'csv', header => true);

CREATE OR REPLACE TABLE aa_demo.bronze.dim_corporate AS
SELECT * EXCEPT (_rescued_data) FROM read_files('/Volumes/aa_demo/bronze/landing/dim_corporate.csv', format => 'csv', header => true);

CREATE OR REPLACE TABLE aa_demo.bronze.dim_market AS
SELECT * EXCEPT (_rescued_data) FROM read_files('/Volumes/aa_demo/bronze/landing/dim_market.csv', format => 'csv', header => true);

CREATE OR REPLACE TABLE aa_demo.bronze.fact_agency_sales_monthly AS
SELECT * EXCEPT (_rescued_data) FROM read_files('/Volumes/aa_demo/bronze/landing/fact_agency_sales_monthly.csv', format => 'csv', header => true);

CREATE OR REPLACE TABLE aa_demo.bronze.fact_market_capacity AS
SELECT * EXCEPT (_rescued_data) FROM read_files('/Volumes/aa_demo/bronze/landing/fact_market_capacity.csv', format => 'csv', header => true);

CREATE OR REPLACE TABLE aa_demo.bronze.agency_goals AS
SELECT * EXCEPT (_rescued_data) FROM read_files('/Volumes/aa_demo/bronze/landing/agency_goals.csv', format => 'csv', header => true);

-- ticket_number must stay a string (leading zeros), so the schema is spelled out for this one
CREATE OR REPLACE TABLE aa_demo.bronze.fact_corporate_bookings AS
SELECT * FROM read_files('/Volumes/aa_demo/bronze/landing/fact_corporate_bookings.csv', format => 'csv', header => true,
  schema => 'booking_id BIGINT, ticket_number STRING, corp_id INT, booking_date DATE, travel_date DATE, origin STRING, dest STRING, channel STRING, fare_usd DOUBLE, ticket_count INT, cabin STRING, agency_id INT');

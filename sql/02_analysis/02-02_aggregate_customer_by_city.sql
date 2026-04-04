-- ============================================
-- [METADATA]
-- file: 02-02_aggregate_customer_by_city.sql
-- category: analysis
-- tags: #customer #distribution #aggregation #municipality #data-quality
-- difficulty: ★★☆ (intermediate)
-- execution_time: 1-5s
-- estimated_complexity: low-medium — point-in-polygon join with aggregation
-- ============================================
-- purpose: Aggregate customer records by municipality
-- input:   customer table (customer_id, customer_name, longitude, latitude)
-- output:  customer count and population ratio per municipality; anomaly records with alert flags
-- tables:  work.customers, admin_jp.municipalities_v2 (Query A), e_stat.v_census_municipality (Query B)
-- created: 2026-02-20
-- updated: 2026-03-27 (added city_name_en to Query B)
-- ============================================

-- [SETUP] Create customer table and import CSV
-- ============================================
-- Run the following only if the table does not yet exist (first time only)
--
-- CREATE SCHEMA IF NOT EXISTS work;
--
-- CREATE TABLE IF NOT EXISTS work.customers (
--     customer_id    VARCHAR(20),
--     customer_name  VARCHAR(100),
--     longitude      DOUBLE PRECISION,
--     latitude       DOUBLE PRECISION
-- );
--
-- -- pgAdmin: right-click the table → Import/Export Data
-- -- psql:
-- -- \COPY work.customers FROM '../data/sample_02-02_customers.csv' WITH CSV HEADER ENCODING 'UTF8';
-- ============================================


-- ============================================
-- [QUERY A] Full customer check with alert flags
-- Run this first to identify data quality issues before aggregating.
-- ============================================
SELECT
    customer_id,
    customer_name,
    longitude,
    latitude,
    -- Alert flags — comma-separated when multiple issues apply
    TRIM(BOTH ',' FROM
        CONCAT(
            CASE WHEN customer_id IS NULL OR customer_id = ''
                THEN 'no_customer_id,' ELSE '' END,
            CASE WHEN customer_name IS NULL OR customer_name = ''
                THEN 'no_name,' ELSE '' END,
            CASE WHEN longitude IS NULL OR latitude IS NULL
                THEN 'no_coordinates,' ELSE '' END,
            CASE WHEN longitude IS NOT NULL AND (longitude < 122 OR longitude > 154)
                THEN 'longitude_out_of_range,' ELSE '' END,
            CASE WHEN latitude IS NOT NULL AND (latitude < 20 OR latitude > 46)
                THEN 'latitude_out_of_range,' ELSE '' END,
            CASE WHEN customer_id IS NOT NULL AND customer_id != '' AND
                 (SELECT COUNT(*) FROM work.customers c2
                  WHERE c2.customer_id = c.customer_id) > 1
                THEN 'duplicate_customer_id,' ELSE '' END
        )
    ) AS alert_flags,
    -- Overall row status
    CASE
        WHEN customer_id IS NULL OR customer_id = ''    THEN 'invalid'
        WHEN longitude IS NULL OR latitude IS NULL      THEN 'invalid'
        WHEN longitude < 122 OR longitude > 154         THEN 'invalid'
        WHEN latitude  < 20  OR latitude  > 46          THEN 'invalid'
        ELSE 'valid'
    END AS status
FROM
    work.customers c
ORDER BY
    status DESC,
    customer_id NULLS FIRST;


-- ============================================
-- [QUERY B] Customer count by municipality (valid records only)
-- Run after reviewing Query A results and correcting any data issues.
-- ============================================
-- WITH valid_customers AS (
--     -- Valid records only
--     SELECT
--         customer_id,
--         customer_name,
--         longitude,
--         latitude
--     FROM work.customers
--     WHERE
--         customer_id IS NOT NULL             -- exclude records without an ID
--         AND longitude IS NOT NULL
--         AND latitude IS NOT NULL
--         AND longitude BETWEEN 122 AND 154   -- valid longitude range for Japan
--         AND latitude  BETWEEN 20  AND 46    -- valid latitude range for Japan
-- )
-- SELECT
--     m.pref_name,
--     m.full_name,
--     m.city_name_en,
--     COUNT(c.customer_id)                AS customer_count,
--     m.population,
--     ROUND(
--         COUNT(c.customer_id)::numeric
--         / NULLIF(m.population, 0) * 10000,
--     2)                                  AS customers_per_10k_population
-- FROM
--     e_stat.v_census_municipality m
--     JOIN valid_customers c
--         ON ST_Contains(
--             m.geom,
--             ST_SetSRID(ST_MakePoint(c.longitude, c.latitude), 4326)
--         )
-- GROUP BY
--     m.pref_name, m.full_name, m.population, m.city_name_en
-- ORDER BY
--     customer_count DESC, m.pref_name;

-- [NOTES]
-- · Recommended workflow: run Query A to identify issues, fix source data if needed, then run Query B
-- · Valid coordinate range for Japan: longitude 122–154°, latitude 20–46°
-- · The duplicate ID check uses a correlated subquery; comment it out if the table is large
-- · Query B uses e_stat.v_census_municipality for population figures

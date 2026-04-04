-- ============================================
-- [METADATA]
-- file: 02-05c_list_cities_along_route_from_gps_log.sql
-- category: analysis
-- tags: #route #municipality #gps #postgres_fdw #foreign-table
-- difficulty: ★★☆ (intermediate)
-- execution_time: 1-3s
-- estimated_complexity: medium — cross-database spatial join via postgres_fdw, 1-3s
-- ============================================
-- purpose: List municipalities along a route from a GPS log table (via postgres_fdw)
-- input:   record_id in the gps_log table
-- output:  municipalities the route passes through, in travel order
-- created: 2026-03-04
-- updated: 2026-03-27 (added city_name_en column)
-- tables:  public.v_census_municipality (foreign table via postgres_fdw), gps_log
-- use-cases: detailed GPS route analysis, travel logging
-- prerequisite: postgres_fdw configured (see 04-06_setup_postgres_fdw.sql)
-- ============================================

-- ============================================
-- [IMPORTANT] Prerequisites
-- ============================================
-- Before running this query, ensure the following are in place:
-- 
-- 1. Set up postgres_fdw
--    → Run 04-06_setup_postgres_fdw.sql
--    → This makes v_census_municipality available as a foreign table
--
-- 2. Import the foreign schema (first time only)
--    Import v_census_municipality from the e_stat schema on the gis DB:
--    IMPORT FOREIGN SCHEMA e_stat
--    LIMIT TO (v_census_municipality)
--    FROM SERVER gis
--    INTO public;
--
-- 3. Verify the foreign table
--    Confirm the foreign table is accessible:
--    SELECT city_code, city_name FROM public.v_census_municipality LIMIT 1;
--
-- If prerequisites are met, edit the parameters below and run.
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================

-- ▼ Schema setting (choose based on your setup)
-- ────────────────────────────────────────────

-- [Case A: project schema]
-- Uncomment and set the project schema name:
-- SET search_path TO project_a, public;  -- ← change schema name

-- [Case B: personal use (public schema)]
-- Leave the SET statement commented out.
-- The gps_log table in the public schema will be used automatically.

-- ────────────────────────────────────────────

-- ▼ Target record
WITH params AS (
    SELECT 
        228 as target_record_id  -- record_id to analyse from the gps_log table
)
-- ============================================

-- [MAIN QUERY] No changes needed below this line
-- Extract municipalities that intersect the GPS log geometry
SELECT 
    m.full_name,
    m.pref_name,
    m.city_name,
    m.city_name_en,
    m.region,
    ROUND(m.area_km2::numeric, 2) as area_km2,
    -- Route length within this municipality (km)
    ROUND(
        (ST_Length(
            ST_Intersection(m.geom, g.geom)::geography
        ) / 1000)::numeric, 2
    ) as route_length_in_city_km,
    -- Distance from route start to entry point (used for travel-order sort)
    ROUND(
        (ST_Length(
            ST_LineSubstring(
                g.geom,
                0,
                ST_LineLocatePoint(g.geom, 
                    ST_ClosestPoint(m.geom, ST_StartPoint(g.geom))
                )
            )::geography
        ) / 1000)::numeric, 2
    ) as distance_from_start_km,
    -- GPS log metadata
    g.start_date,
    g.start_timestamp,
    g.travel_distance AS total_distance_km,
    g.drive,
    g.bike,
    g.walk,
    g.flight,
    g.train,
    g.sail
FROM public.v_census_municipality m
-- JOIN public.prefectures p USING (pref_code)  -- removed: region is now available in v_census_municipality
CROSS JOIN gps_log g  -- no schema prefix; resolved via search_path
CROSS JOIN params
WHERE 
    g.record_id = params.target_record_id
    AND ST_Intersects(m.geom, g.geom) 
ORDER BY distance_from_start_km;

-- ============================================
-- [NOTES]
-- ============================================
-- · Typical execution time: 1–3 s (depends on route length)
-- · Typical row count: 20–200 municipalities
-- 
-- Output columns:
--   full_name              - full official name
--   pref_name              - prefecture name
--   city_name              - municipality name
--   city_name_en           - municipality name in English (NULL for 2015 data)
--   region                 - regional grouping
--   area_km2               - municipality area (km²)
--   route_length_in_city_km - route length within this municipality (km)
--   distance_from_start_km  - distance from start to municipality entry point (km)
--   start_date             - trip start date
--   start_timestamp        - trip start timestamp
--   total_distance_km      - total trip distance (km)
--   drive/bike/walk etc.   - transport mode flags
--
-- gps_log table location:
--   Personal use:  public.gps_log  (no SET search_path needed)
--   Project use:   project_a.gps_log, project_b.gps_log etc.
--                  (SET search_path TO project_a, public; required)
--
-- How search_path works:
--   SET search_path TO project_a, public;
--   When a table name is given without a schema prefix:
--     1. PostgreSQL looks in project_a first
--     2. Falls back to public if not found
--   e.g. SELECT * FROM gps_log;           → resolves to project_a.gps_log
--        SELECT * FROM v_census_municipality; → resolves to public.v_census_municipality
--
-- Advantages of postgres_fdw:
--   ✓ Uses all GPS coordinate points (no subsampling needed)
--   ✓ No CSV export required
--   ✓ Real-time cross-database queries
--   ✓ Works directly with the existing gps_log table
--
-- Use cases:
--   - Generate travel logs from GPS data
--   - Detailed sales route analysis
--   - Cycling and driving route records
--   - Analysis by transport mode
--
-- Customisation:
--   1. Filter by transport mode: WHERE g.bike = 'yes' AND ...
--   
--   2. Filter by date range: WHERE g.start_date BETWEEN '2025-01-01' AND '2025-12-31' AND ...
--   
--   3. Process multiple records: WHERE g.record_id IN (228, 229, 230) AND ...
--
-- Troubleshooting:
--
--   ERROR: relation "v_census_municipality" does not exist
--   → postgres_fdw is not configured, or foreign schema has not been imported
--   → Run 04-06_setup_postgres_fdw.sql, then complete prerequisite step 2 above
--
--   ERROR: relation "gps_log" does not exist
--   → Table does not exist or wrong schema is active
--   → For public schema: run section ③ in 04-06_setup_postgres_fdw.sql
--   → For project schema: ensure SET search_path is correct
--
--   No rows returned
--   → Check that the specified record_id exists in the gps_log table
--
-- Choosing within the 02-05 series:
--   02-05a: prefecture level, direct coordinate input (good for quick overview)
--   02-05b: municipality level, direct coordinate input (routes with ≤10 waypoints)
--   02-05c: municipality level, postgres_fdw (GPS log DB integration) ← this template
--
-- Example database layout:
--   DB1: gis
--     ├── admin_jp.municipalities_v2  (boundary polygons for spatial operations)
--     └── e_stat.v_census_municipality (census + employment unified view)
--   
--   DB2: travel_imais (or project DB)
--     ├── public.gps_log               (personal GPS log)
--     ├── public.v_census_municipality  (foreign table → DB1 e_stat schema)
--     ├── project_a.gps_log            (project A GPS log)
--     └── project_b.gps_log            (project B GPS log)
-- ============================================

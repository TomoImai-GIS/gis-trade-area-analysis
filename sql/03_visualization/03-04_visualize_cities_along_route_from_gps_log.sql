-- ============================================
-- [METADATA]
-- file: 03-04_visualize_cities_along_route_from_gps_log.sql
-- category: visualization
-- tags: #route #municipality #gps #qgis #choropleth #postgres_fdw #foreign-table
-- difficulty: ★★☆ (intermediate)
-- execution_time: 1-3s
-- estimated_complexity: medium — cross-database spatial join via postgres_fdw, polygon geometry for QGIS
-- ============================================
-- purpose: List municipalities a GPS route passes through and return municipality
--          polygons (m.geom) plus a unique id (city_code) for QGIS visualisation.
--          A template for mapping the municipalities a route traverses as filled polygons.
-- input:   record_id in the gps_log table
-- output:  municipalities the route passes through, in travel order, with polygon geometry
-- created: 2026-07-05
-- updated: 2026-07-05
-- tables:  public.v_census_municipality (foreign table via postgres_fdw), gps_log
-- use-cases: mapping GPS routes, travel logging with a spatial layer
-- prerequisite: postgres_fdw configured (see 04-06_setup_postgres_fdw.sql)
-- ============================================
-- ■ Relationship to 02-05c
--   This is the visualisation counterpart of 02-05c_list_cities_along_route_from_gps_log.
--   02-05c returns a tabular list of municipalities; this template adds two columns so the
--   traversed municipalities can be drawn as polygons in QGIS:
--     - city_code : nationally unique municipality code (used as the QGIS feature id)
--     - m.geom    : municipality polygon (MultiPolygon, SRID 4326)
--   Note: v_census_municipality is a foreign table (postgres_fdw), so ctid is unavailable;
--   QGIS requires an explicit unique integer/code column (city_code) to build a query layer.
--   Do NOT use city_name as the unique id — municipality names are not nationally unique
--   (e.g. Fuchu-shi exists in both Tokyo and Hiroshima).
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
--    IMPORT FOREIGN SCHEMA e_stat
--    LIMIT TO (v_census_municipality)
--    FROM SERVER gis
--    INTO public;
--
-- 3. Verify the foreign table
--    SELECT city_code, city_name FROM public.v_census_municipality LIMIT 1;
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================

-- ▼ Schema setting (choose based on your setup)
-- ────────────────────────────────────────────
-- [Case A: personal use] The gps_log table in the public schema is used automatically.
-- [Case B: project use]  SET search_path TO project_a, public;  -- change schema name
-- ────────────────────────────────────────────

-- ▼ Target record
WITH params AS (
    SELECT
        228 as target_record_id  -- record_id to analyse from the gps_log table
)
-- ============================================

-- [MAIN QUERY] No changes needed below this line
-- Extract municipalities that intersect the GPS log geometry, with polygon geometry
SELECT
    m.city_code,                     -- unique id for QGIS (nationally unique)
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
    g.sail,
    m.geom                           -- municipality polygon for QGIS (MultiPolygon, 4326)
FROM public.v_census_municipality m
CROSS JOIN gps_log g  -- no schema prefix; resolved via search_path
CROSS JOIN params
WHERE
    g.record_id = params.target_record_id
    AND ST_Intersects(m.geom, g.geom)
ORDER BY distance_from_start_km;

-- ============================================
-- [QGIS VISUALISATION]
-- ============================================
-- In the DB Manager SQL window, run this query, then "Load as new layer" with:
--   Geometry column : geom
--   Unique id column: city_code   ← required (a query layer fails to build without it)
--
-- · Do not use city_name (or another non-unique column) as the unique id, or features
--   will be dropped/duplicated on routes containing same-named municipalities.
-- · The rendered layer shows municipality polygons. To overlay the route line itself,
--   load gps_log as a separate layer (geometry = g.geom).
--
-- Styling ideas:
--   - Graduated on route_length_in_city_km  → darker where the route runs longer
--   - Graduated on distance_from_start_km   → gradient by arrival order from the start
-- ============================================

-- ============================================
-- [NOTES]
-- ============================================
-- · Typical execution time: 1–3 s (depends on route length)
-- · Typical row count: 20–200 municipalities
--
-- Output columns:
--   city_code               - municipality code (5-digit, nationally unique, QGIS id)
--   full_name               - full official name
--   pref_name               - prefecture name
--   city_name               - municipality name
--   city_name_en            - municipality name in English (NULL for 2015 data)
--   region                  - regional grouping
--   area_km2                - municipality area (km²)
--   route_length_in_city_km - route length within this municipality (km)
--   distance_from_start_km  - distance from start to municipality entry point (km)
--   start_date              - trip start date
--   start_timestamp         - trip start timestamp
--   total_distance_km       - total trip distance (km)
--   drive/bike/walk etc.    - transport mode flags
--   geom                    - municipality polygon (MultiPolygon, SRID 4326)
--
-- On SRID:
--   Both m.geom (municipality) and g.geom (route) are SRID 4326 (WGS84), so
--   ST_Intersects / ST_Intersection run directly without ST_Transform.
--
-- Customisation:
--   1. Filter by transport mode: WHERE g.bike = 'yes' AND ...
--   2. Process multiple records: WHERE g.record_id IN (228, 229, 230) AND ...
--   3. Colour by demographics:   add m.population, m.elderly_rate etc. to the SELECT
--
-- Troubleshooting:
--
--   QGIS: failed to create SQL layer
--   → Unique id column not set / not unique. Use city_code.
--
--   ERROR: relation "v_census_municipality" does not exist
--   → postgres_fdw not configured or foreign schema not imported (see 04-06)
--
--   ERROR: relation "gps_log" does not exist
--   → Wrong schema active. Check the FROM schema or SET search_path.
--
--   No rows returned
--   → Check that the specified record_id exists in the gps_log table
--
-- Related templates:
--   02-05c: tabular version of the same logic (municipality list, no geometry)
--   03-02 : elderly-rate choropleth
--   03-03 : octant population-growth choropleth
-- ============================================

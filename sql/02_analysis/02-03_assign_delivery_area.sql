-- ============================================
-- [METADATA]
-- file: 02-03_assign_delivery_area.sql
-- category: analysis
-- tags: #delivery #area #logistics #depot #radius #voronoi
-- difficulty: ★★☆ (intermediate)
-- execution_time: 1-3s
-- estimated_complexity: medium — nearest-neighbour assignment across full municipality set
-- ============================================
-- purpose: Assign municipalities to delivery depots based on proximity
-- input:   [Query A] multiple depots — assign each municipality to its nearest depot
--           [Query B] single depot — extract municipalities within a given radius
-- output:  assigned depot, distance, and census statistics per municipality
-- tables:  e_stat.v_census_municipality
-- created: 2026-02-21
-- updated: 2026-03-27 (added city_name_en column)
-- ============================================


-- ============================================
-- [QUERY A] Multiple depots — assign each municipality to its nearest depot
-- ============================================

-- [PARAMETERS] Edit depot list below
WITH depots AS (
    SELECT 'Nagoya DC' AS depot_name, 136.8816 AS lon, 35.1706 AS lat
    UNION ALL
    SELECT 'Osaka DC',               135.4959,        34.7024
    UNION ALL
    SELECT 'Tokyo DC',               139.7671,        35.6812
    -- Add more depots by appending UNION ALL rows above
),

-- Calculate distance from each municipality to every depot
city_depot_distances AS (
    SELECT
        m.pref_name,
        m.full_name,
        m.city_name_en,
        m.population,
        m.area_km2,
        d.depot_name,
        ROUND(
            ST_Distance(
                m.geom::geography,
                ST_SetSRID(ST_MakePoint(d.lon, d.lat), 4326)::geography
            )::numeric / 1000,
        2) AS distance_km
    FROM
        e_stat.v_census_municipality m
        CROSS JOIN depots d
),

-- Identify the nearest depot for each municipality
nearest_depot AS (
    SELECT DISTINCT ON (pref_name, full_name)
        pref_name,
        full_name,
        city_name_en,
        population,
        area_km2,
        depot_name  AS assigned_depot,
        distance_km AS distance_to_depot_km
    FROM city_depot_distances
    ORDER BY pref_name, full_name, distance_km ASC
)

SELECT
    assigned_depot,
    pref_name,
    full_name,
    city_name_en,
    population,
    area_km2,
    distance_to_depot_km
FROM nearest_depot
ORDER BY
    assigned_depot,
    distance_to_depot_km ASC;


-- ============================================
-- [QUERY B] Single depot — extract municipalities within delivery radius
-- ============================================
-- WITH params AS (
--     SELECT
--         'Nagoya DC' AS depot_name,
--         136.8816   AS depot_lon,   -- depot longitude
--         35.1706    AS depot_lat,   -- depot latitude
--         50000      AS radius_m     -- delivery radius in metres (example: 50000 = 50 km)
-- )
-- SELECT
--     p.depot_name,
--     m.pref_name,
--     m.full_name,
--     m.city_name_en,
--     m.population,
--     m.area_km2,
--     ROUND(
--         ST_Distance(
--             m.geom::geography,
--             ST_SetSRID(ST_MakePoint(p.depot_lon, p.depot_lat), 4326)::geography
--         )::numeric / 1000,
--     2)                                      AS distance_to_depot_km
-- FROM
--     e_stat.v_census_municipality m,
--     params p
-- WHERE
--     ST_DWithin(
--         m.geom::geography,
--         ST_SetSRID(ST_MakePoint(p.depot_lon, p.depot_lat), 4326)::geography,
--         p.radius_m
--     )
-- ORDER BY
--     distance_to_depot_km ASC;

-- [NOTES]
-- · Query A covers all municipalities nationwide; add a WHERE filter to restrict by prefecture
--   e.g. WHERE m.pref_code IN ('23','24','25')
-- · Distance is measured to the nearest point on the polygon boundary, not the centroid
-- · Query B is structurally similar to 02-01_calc_trade_area_population.sql,
--   but is designed for delivery zone determination, so depot name is explicitly shown
-- · Designated cities are assigned at ward level; use GROUP BY for city-level totals

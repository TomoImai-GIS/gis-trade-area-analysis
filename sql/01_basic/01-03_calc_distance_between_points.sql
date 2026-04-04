-- ============================================
-- [METADATA]
-- file: 01-03_calc_distance_between_points.sql
-- category: basic
-- tags: #distance #two-points #km #geography #straight-line
-- difficulty: ★☆☆ (beginner)
-- estimated_complexity: low — no table scan, pure coordinate calculation
-- execution_time: <1s
-- ============================================
-- purpose: Calculate the straight-line (great-circle) distance between
--          two coordinate pairs, returned in both km and m.
-- input:   two lon/lat pairs (point1, point2)
-- output:  distance_km, distance_m
-- tables:  none (coordinate-only calculation)
-- created: 2026-02-19
-- updated: 2026-02-19
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================
WITH params AS (
    SELECT
        136.8816 AS point1_lon,   -- longitude of point 1  (example: Nagoya Station)
        35.1706  AS point1_lat,   -- latitude  of point 1
        135.4959 AS point2_lon,   -- longitude of point 2  (example: Osaka Station)
        34.7024  AS point2_lat    -- latitude  of point 2
)
-- ============================================

-- [QUERY A] Straight-line distance between two points
SELECT
    ROUND(
        ST_Distance(
            ST_SetSRID(ST_MakePoint(p.point1_lon, p.point1_lat), 4326)::geography,
            ST_SetSRID(ST_MakePoint(p.point2_lon, p.point2_lat), 4326)::geography
        )::numeric / 1000,
    2) AS distance_km,
    ROUND(
        ST_Distance(
            ST_SetSRID(ST_MakePoint(p.point1_lon, p.point1_lat), 4326)::geography,
            ST_SetSRID(ST_MakePoint(p.point2_lon, p.point2_lat), 4326)::geography
        )::numeric,
    0) AS distance_m
FROM params p;


-- ============================================
-- [QUERY B] Distance from a base point to the centroid of each municipality
--           (uncomment to use)
-- ============================================
-- WITH params AS (
--     SELECT
--         136.8816 AS base_lon,   -- longitude of the base point
--         35.1706  AS base_lat    -- latitude  of the base point
-- )
-- SELECT
--     m.full_name,
--     m.pref_name,
--     ROUND(
--         ST_Distance(
--             ST_Centroid(m.geom)::geography,
--             ST_SetSRID(ST_MakePoint(p.base_lon, p.base_lat), 4326)::geography
--         )::numeric / 1000,
--     2) AS distance_to_centroid_km
-- FROM
--     admin_jp.municipalities_v2 m,
--     params p
-- ORDER BY
--     distance_to_centroid_km ASC
-- LIMIT 20;

-- [NOTES]
-- · Cast to ::geography to compute great-circle (spherical) distance in metres.
--   Without this cast, ST_Distance operates on raw degree values, which is
--   geometrically meaningless for distance calculations.
--
-- · ST_Distance(geography) always returns metres; divide by 1000 for km.
--
-- · This is straight-line distance. Road distance and travel time will differ.
--   For road distance, consider pgRouting or an external routing API
--   (e.g. Google Maps Distance Matrix, OSRM).
--
-- [EXAMPLES] (straight-line)
--   Nagoya Station → Osaka Station : ~137 km  (road distance: ~148 km)
--   Nagoya Station → Tokyo Station : ~227 km  (road distance: ~354 km)

-- ============================================
-- [METADATA]
-- file: 01-01_find_city_from_point.sql
-- category: basic
-- tags: #coordinate #municipality #geocoding #reverse-geocoding
-- difficulty: ★☆☆ (beginner)
-- estimated_complexity: low — single spatial predicate, sub-second on indexed geometry
-- execution_time: <1s
-- ============================================
-- purpose: Identify the municipality (city/ward/town/village) that contains
--          a given coordinate (longitude, latitude).
-- input:   target_lon (longitude), target_lat (latitude)
-- output:  prefecture name, municipality name, full official name,
--          JIS code, city code, area (km²)
-- tables:  admin_jp.municipalities_v2
-- created: 2026-02-19
-- updated: 2026-02-19
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================
WITH params AS (
    SELECT
        136.8816 AS target_lon,   -- longitude  (example: Nagoya Station)
        35.1706  AS target_lat    -- latitude   (example: Nagoya Station)
)
-- ============================================

-- [MAIN QUERY] No changes needed below this line
SELECT
    m.pref_name   AS prefecture,
    m.city_name   AS municipality,
    m.full_name   AS official_name,
    m.jis_code    AS jis_code,
    m.city_code   AS city_code,
    m.area_km2    AS area_km2
FROM
    admin_jp.municipalities_v2 m,
    params p
WHERE
    ST_Contains(
        m.geom,
        ST_SetSRID(ST_MakePoint(p.target_lon, p.target_lat), 4326)
    );

-- [NOTES]
-- · ST_Contains returns TRUE when the point lies strictly inside the polygon.
--   Points exactly on a boundary may return FALSE depending on floating-point
--   precision. Use ST_Intersects instead if you need to capture boundary cases.
--
-- · No rows returned?
--     → The coordinate may be offshore, outside Japan, or in a data gap.
--
-- · Multiple rows returned?
--     → Overlapping geometries exist in the boundary data.
--       Run 04_maintenance/04-04_validate_geometries.sql to investigate.
--
-- [EXAMPLES]
--   Nagoya Station  (136.8816, 35.1706) → Nakamura-ku, Nagoya
--   Tokyo Station   (139.7671, 35.6812) → Chiyoda-ku, Tokyo
--   Osaka Station   (135.4959, 34.7024) → Kita-ku, Osaka

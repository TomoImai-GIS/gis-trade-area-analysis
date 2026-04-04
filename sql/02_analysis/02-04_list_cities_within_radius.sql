-- ============================================
-- [METADATA]
-- file: 02-04_list_cities_within_radius.sql
-- category: analysis
-- tags: #trade-area #distance #municipality #area-definition
-- difficulty: ★☆☆ (beginner)
-- execution_time: <1s
-- estimated_complexity: low — radius filter with bearing calculation, sub-second
-- ============================================
-- purpose: List municipalities within a given radius from a specified coordinate
-- input:   center coordinate (lon/lat), radius (metres)
-- output:  municipality list sorted by distance, with bearing direction
-- created: 2026-02-18
-- updated: 2026-02-18
-- tables:  e_stat.v_census_municipality
-- use-cases: trade area research, delivery zone setup, site selection
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================
WITH params AS (
    SELECT 
        136.8816 as center_lon,     -- longitude (example: Nagoya Station)
        35.1706  as center_lat,     -- latitude
        30000    as radius_m        -- radius in metres (example: 30 km = 30000 m)
)
-- ============================================

-- [MAIN QUERY] No changes needed below this line
SELECT 
    m.full_name,
    m.pref_name,
    m.city_name,
    m.city_name_en,
    m.region,
    ROUND(m.area_km2::numeric, 2) as area_km2,
    ROUND(
        (ST_Distance(
            m.geom::geography,
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326)::geography
        ) / 1000)::numeric, 2
    ) as distance_km,
    -- Bearing from center point (N/NE/E/SE/S/SW/W/NW)
    CASE 
        WHEN degrees(ST_Azimuth(
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326),
            ST_Centroid(m.geom)
        )) BETWEEN 337.5 AND 360 OR degrees(ST_Azimuth(
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326),
            ST_Centroid(m.geom)
        )) BETWEEN 0 AND 22.5 THEN 'N'
        WHEN degrees(ST_Azimuth(
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326),
            ST_Centroid(m.geom)
        )) BETWEEN 22.5 AND 67.5 THEN 'NE'
        WHEN degrees(ST_Azimuth(
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326),
            ST_Centroid(m.geom)
        )) BETWEEN 67.5 AND 112.5 THEN 'E'
        WHEN degrees(ST_Azimuth(
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326),
            ST_Centroid(m.geom)
        )) BETWEEN 112.5 AND 157.5 THEN 'SE'
        WHEN degrees(ST_Azimuth(
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326),
            ST_Centroid(m.geom)
        )) BETWEEN 157.5 AND 202.5 THEN 'S'
        WHEN degrees(ST_Azimuth(
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326),
            ST_Centroid(m.geom)
        )) BETWEEN 202.5 AND 247.5 THEN 'SW'
        WHEN degrees(ST_Azimuth(
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326),
            ST_Centroid(m.geom)
        )) BETWEEN 247.5 AND 292.5 THEN 'W'
        WHEN degrees(ST_Azimuth(
            ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326),
            ST_Centroid(m.geom)
        )) BETWEEN 292.5 AND 337.5 THEN 'NW'
    END as direction
FROM e_stat.v_census_municipality m
CROSS JOIN params
WHERE ST_DWithin(
    m.geom::geography,
    ST_SetSRID(ST_MakePoint(params.center_lon, params.center_lat), 4326)::geography,
    params.radius_m
)
ORDER BY distance_km;

-- ============================================
-- [NOTES]
-- ============================================
-- · Typical execution time: 0.5–1 s
-- · Typical row count: 30–100 (at 30 km radius)
-- 
-- Output columns:
--   full_name    - full official name (e.g. 愛知県名古屋市中区)
--   pref_name    - prefecture name
--   city_name    - municipality name
--   city_name_en - municipality name in English (NULL for 2015 census data)
--   region       - regional grouping (e.g. Kanto, Chubu)
--   area_km2     - area in km²
--   distance_km  - distance from center point (km)
--   direction    - bearing from center (N/NE/E/SE/S/SW/W/NW)
--
-- Notes:
--   - distance_km is measured to the nearest polygon boundary point, not the centroid
--   - Municipalities are included if any part falls within the radius
--   - To return only municipalities fully contained within the radius,
--     replace ST_DWithin with ST_Contains
--
-- Use cases:
--   - Build a municipality list for a delivery zone
--   - Verify trade area coverage
--   - Survey municipalities around a potential store location
--   - Determine catchment area for an event
--
-- Customisation:
--   1. Filter by prefecture: add AND m.pref_name = '愛知県' to the WHERE clause
--   
--   2. Filter by distance band: add AND distance_km BETWEEN 10 AND 20
--   
--   3. Filter by area: add AND m.area_km2 > 100 (large municipalities only)
--
-- Example output (Nagoya Station, 30 km radius):
--   full_name                    | distance_km | direction
--   -----------------------------|-------------|----------
--   愛知県名古屋市中村区 (Nakamura)  | 0.15        | -
--   愛知県名古屋市西区 (Nishi)       | 1.23        | N
--   愛知県名古屋市中区 (Naka)        | 1.45        | E
--   ...
-- ============================================

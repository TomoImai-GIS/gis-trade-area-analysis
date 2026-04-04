-- ============================================
-- [METADATA]
-- file: 02-01_calc_trade_area_population.sql
-- category: analysis
-- tags: #trade-area #population #site-selection #marketing #radius
-- difficulty: ★☆☆ (beginner)
-- execution_time: <1s
-- estimated_complexity: low — single spatial predicate with census join, sub-second
-- ============================================
-- purpose: Aggregate municipality-level population statistics within a given radius from a specified coordinate
-- input:   center coordinate (lon/lat), radius (metres)
-- output:  population, elderly rate, density, and distance from center — per municipality
-- tables:  e_stat.v_census_municipality
-- created: 2026-02-20
-- updated: 2026-03-27 (added city_name_en column)
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================
WITH params AS (
    SELECT
        136.8816 AS center_lon,   -- longitude (example: Nagoya Station)
        35.1706  AS center_lat,   -- latitude
        30000    AS radius_m      -- radius in metres (example: 30000 = 30 km)
)
-- ============================================

-- [MAIN QUERY] No changes needed below this line
SELECT
    m.pref_name,
    m.full_name,
    m.city_name_en,
    m.population,
    m.pop_density,
    m.elderly_rate,
    m.area_km2,
    ROUND(
        ST_Distance(
            m.geom::geography,
            ST_SetSRID(ST_MakePoint(p.center_lon, p.center_lat), 4326)::geography
        )::numeric / 1000,
    2)                                      AS distance_km
FROM
    e_stat.v_census_municipality m,
    params p
WHERE
    ST_DWithin(
        m.geom::geography,
        ST_SetSRID(ST_MakePoint(p.center_lon, p.center_lat), 4326)::geography,
        p.radius_m
    )
ORDER BY
    distance_km ASC;

-- [NOTES]
-- · ST_DWithin(geography) radius is in metres
-- · Distance is measured to the nearest point on the polygon boundary, not the centroid
-- · Designated cities (政令市) are aggregated at ward level; use GROUP BY for city-level totals
-- · Municipalities with population IS NULL have no census data loaded (2020 census base)
-- · For a fixed census year, use v_census_municipality_2015 or v_census_municipality_2020
-- · To get total catchment population, wrap the query:
--   SELECT SUM(population) FROM (...above query...) sub WHERE population IS NOT NULL

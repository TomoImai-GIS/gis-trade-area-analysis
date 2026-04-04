-- ============================================
-- [METADATA]
-- file: 03-02_generate_choropleth_elderly_rate.sql
-- category: visualization
-- tags: #choropleth #elderly-rate #demographics #qgis #map
-- difficulty: ★☆☆ (beginner)
-- estimated_complexity: low — full-table scan with filter, geometry included for QGIS
-- execution_time: <1s
-- ============================================
-- purpose: Export municipality-level elderly rate data with geometry for
--          choropleth map rendering in QGIS or other GIS tools.
--          Based on 02-06_rank_cities_by_elderly_rate.sql with geometry added
--          and limit removed for full-coverage map output.
-- input:   region or prefecture name filter (optional), minimum population threshold
-- output:  municipality polygons with elderly rate and demographic breakdown —
--          load directly into QGIS as a PostGIS layer
-- tables:  e_stat.v_census_municipality
-- created: 2026-04-02
-- updated: 2026-04-02
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================
WITH params AS (
    SELECT
        -- Filter by region (NULL = nationwide)
        -- Options: '北海道' '東北' '関東' '中部' '近畿' '中国' '四国' '九州沖縄'
        NULL::text AS target_region,

        -- Filter by prefecture name (NULL = all)
        NULL::text AS target_pref,

        -- Minimum population threshold (exclude very small municipalities)
        50 AS min_population
)
-- ============================================

-- [MAIN QUERY] No changes needed below this line
SELECT
    m.full_name,
    m.pref_name,
    m.city_name,
    m.city_name_en,
    m.region,
    m.population,
    m.pop_elderly,
    m.elderly_rate,
    m.age_avg,
    m.households,
    m.single_hh_65,
    ROUND((m.single_hh_65::numeric / NULLIF(m.households, 0) * 100), 1) AS single_elderly_hh_rate,
    ROUND(m.area_km2::numeric, 2)                                        AS area_km2,
    m.pop_density,
    m.geom                          -- geometry column for QGIS rendering
FROM e_stat.v_census_municipality m
CROSS JOIN params p
WHERE
    m.population IS NOT NULL
    AND m.population >= p.min_population
    AND (p.target_region IS NULL OR m.region    = p.target_region)
    AND (p.target_pref   IS NULL OR m.pref_name = p.target_pref)
ORDER BY m.elderly_rate DESC;

-- [NOTES]
-- · This query is designed to be loaded as a PostGIS layer in QGIS.
--   In QGIS DB Manager or the Add PostGIS Layer dialog, paste the query
--   and set the geometry column to "geom".
--
-- · Choropleth classification suggestion (5 classes, quantile or natural breaks):
--     < 26.8 %  — low
--     26.8–30.6 — below average
--     30.6–34.7 — average
--     34.7–39.0 — above average
--     > 39.0 %  — high
--   (Adjust thresholds based on your target region.)
--
-- · To restrict output to a specific region, set target_region or target_pref
--   in the params block. This is useful for prefecture-level maps.
--
-- · The geometry column (m.geom) is inherited from admin_jp.municipalities_v2
--   via e_stat.v_census_municipality. SRID: 4326 (WGS84).
--
-- · For population density choropleth, see:
--   03-01_generate_choropleth_population.sql (in progress)
--
-- [EXAMPLES]
--   Nationwide map (all municipalities with population >= 5,000):
--     -> set both filters to NULL  (default)
--
--   Tohoku region only:
--     -> set target_region = '東北'
--
--   Akita prefecture only:
--     -> set target_pref = '秋田県'

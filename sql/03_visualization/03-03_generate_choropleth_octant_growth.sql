-- ============================================
-- [METADATA]
-- file: 03-03_generate_choropleth_octant_growth.sql
-- category: visualization
-- tags: #octant #aging #demographics #qgis #choropleth #population-growth
-- difficulty: ★☆☆ (beginner)
-- execution_time: ~1s
-- estimated_complexity: low — two-year census join with octant classification, geometry included for QGIS
-- ============================================
-- purpose: Classify all municipalities by 2015→2020 age-group growth direction (octant)
--          and return polygon geometry for QGIS spatial visualisation.
--          One row per municipality; no population filter applied so every matched
--          record appears — add a WHERE clause in QGIS to restrict as needed.
-- input:   none (no parameters; filtering is done in QGIS or by adding a WHERE clause)
-- output:  one row per municipality with 2015/2020 population counts, deltas,
--          3-char octant key, and WGS84 polygon geometry
-- created: 2026-04-16
-- updated: 2026-04-16
-- tables:  e_stat.census_population, e_stat.v_census_municipality
-- use-cases: spatial distribution map of demographic trajectory types;
--            companion layer for 01-07_octant_histogram_analysis.md
-- ============================================

-- [PARAMETERS]
-- ============================================
-- No editable parameters — this query returns all municipalities.
-- To filter output, add a WHERE clause directly in QGIS (Layer Filter / DB Manager):
--
--   Filter to specific octant groups:
--     octant IN ('+++', '-++', '---', '+-+')
--
--   Filter by prefecture:
--     prefecture_name = '愛知県'
--
--   Exclude very small municipalities:
--     population_2020 >= 5000
-- ============================================

-- [MAIN QUERY] No changes needed below this line
WITH city_code_map AS (
    -- Municipalities that changed city_code between the two census years.
    -- For 2015→2020 there are 2 cases:
    --   04423 富谷町  → 04216 富谷市   (upgraded 2016-10-10)
    --   40305 那珂川町 → 40231 那珂川市  (upgraded 2018-10-01)
    -- We remap 2015 old_city_code → new_city_code so the JOIN with 2020 rows succeeds.
    SELECT old_city_code, new_city_code
    FROM admin_jp.city_code_history
    WHERE updated_census_year = 2020
),
y15 AS (
    -- 2015 Census: total population and age-group counts per municipality.
    -- admin_type <> '1' excludes 政令指定都市 city-level totals and
    -- 東京都区部 aggregate to avoid double-counting with ward-level rows.
    -- COALESCE remaps any 2015 city_code that was superseded by a new code in 2020;
    -- municipalities not in city_code_map keep their original code unchanged.
    SELECT
        COALESCE(h.new_city_code, cp.city_code) AS city_code,
        cp.population                           AS population_2015,
        cp.lt_15                                AS lt_15_2015,
        cp.mid_15_64                            AS mid_15_64_2015,
        cp.gt_65                                AS gt_65_2015
    FROM e_stat.census_population cp
    LEFT JOIN city_code_map h ON h.old_city_code = cp.city_code
    WHERE cp.survey_year = 2015
      AND cp.admin_type <> '1'
),
y20 AS (
    -- 2020 Census: same structure.
    SELECT
        city_code,
        population                              AS population_2020,
        lt_15                                   AS lt_15_2020,
        mid_15_64                               AS mid_15_64_2020,
        gt_65                                   AS gt_65_2020
    FROM e_stat.census_population
    WHERE survey_year = 2020
      AND admin_type <> '1'
),
combined AS (
    SELECT
        y15.city_code,

        -- Total population
        y15.population_2015,
        y20.population_2020,
        (y20.population_2020 - y15.population_2015)         AS population_delta,

        -- Under-15
        y15.lt_15_2015,
        y20.lt_15_2020,
        (y20.lt_15_2020     - y15.lt_15_2015)               AS lt_15_delta,

        -- Ages 15–64
        y15.mid_15_64_2015,
        y20.mid_15_64_2020,
        (y20.mid_15_64_2020 - y15.mid_15_64_2015)           AS mid_15_64_delta,

        -- Ages 65+
        y15.gt_65_2015,
        y20.gt_65_2020,
        (y20.gt_65_2020     - y15.gt_65_2015)               AS gt_65_delta,

        -- Octant key: 3-char ASCII string encoding growth direction
        -- Position 1: Under-15,  Position 2: Ages 15–64,  Position 3: Ages 65+
        -- '+' = increased 2015→2020,  '-' = decreased or unchanged
        CASE WHEN (y20.lt_15_2020     - y15.lt_15_2015)     > 0 THEN '+' ELSE '-' END ||
        CASE WHEN (y20.mid_15_64_2020 - y15.mid_15_64_2015) > 0 THEN '+' ELSE '-' END ||
        CASE WHEN (y20.gt_65_2020     - y15.gt_65_2015)     > 0 THEN '+' ELSE '-' END
                                                             AS octant

    FROM y15
    JOIN y20 USING (city_code)
)
SELECT
    c.city_code,
    m.pref_name                                             AS prefecture_name,
    m.city_name,
    m.city_name_en,
    c.population_2015,
    c.population_2020,
    c.population_delta,
    c.lt_15_2015,
    c.lt_15_2020,
    c.lt_15_delta,
    c.mid_15_64_2015,
    c.mid_15_64_2020,
    c.mid_15_64_delta,
    c.gt_65_2015,
    c.gt_65_2020,
    c.gt_65_delta,
    c.octant,
    m.geom                  -- WGS84 polygon (SRID 4326); set as geometry column in QGIS
FROM combined c
JOIN e_stat.v_census_municipality m ON m.city_code = c.city_code
ORDER BY c.city_code;

-- ============================================
-- [NOTES]
-- ============================================
--
-- Octant key reference (8 possible combinations):
--   '--+'  Under-15−, Ages 15-64−, Ages 65+  ← dominant pattern (~69 % of municipalities)
--   '+++'  all three increasing
--   '-++'  Under-15−, Ages 15-64+, Ages 65+
--   '+-+'  Under-15+, Ages 15-64−, Ages 65+
--   '---'  all three declining
--   '++-'  Under-15+, Ages 15-64+, Ages 65−
--   '+--'  Under-15+, Ages 15-64−, Ages 65−
--   '-+-'  Under-15−, Ages 15-64+, Ages 65−
--
-- Row count:
--   Municipalities that have matched records in both 2015 and 2020 census tables
--   AND have a corresponding boundary in e_stat.v_census_municipality.
--   Expected: ~1,700–1,900 rows (varies by admin_type filter and boundary coverage).
--
-- City code remapping (admin_jp.city_code_history):
--   Two municipalities changed their city_code between the 2015 and 2020 censuses:
--     04423 富谷町  → 04216 富谷市   (town upgraded to city, effective 2016-10-10)
--     40305 那珂川町 → 40231 那珂川市  (town upgraded to city, effective 2018-10-01)
--   The city_code_map CTE remaps these old codes in the 2015 CTE so that the
--   JOIN with 2020 rows (which carry the new codes) succeeds for both municipalities.
--   The filter updated_census_year = 2020 selects only changes reflected in the
--   2020 census; extend this filter if additional census years are added in future.
--
-- admin_type filter:
--   admin_type <> '1' excludes:
--     - 政令指定都市 (designated city) city-level aggregate rows
--       (ward-level rows with admin_type = '2' are retained)
--     - 東京都区部 (Tokyo 23-ward combined) aggregate row
--
-- Geometry:
--   m.geom is inherited from admin_jp.municipalities_v2 via e_stat.v_census_municipality.
--   SRID: 4326 (WGS84). If a municipality has no matching boundary record (e.g. due to
--   boundary revision), it will be silently excluded by the INNER JOIN.
--   Use LEFT JOIN ... m ON ... if you want to diagnose unmatched city_code values.
--
-- QGIS usage — load via DB Manager → SQL window:
--   1. Paste the full query into the SQL window
--   2. Tick "Load as new layer"; set Geometry column = geom, SRID = 4326
--   3. Style the layer with a Categorized renderer on the "octant" field
--   Recommended colours (consistent with Python outputs 01-06 / 01-07):
--     '--+'  →  #e87700  (amber)
--     '+++'  →  #1f77b4  (blue)
--     '-++'  →  #aec7e8  (light blue)
--     '+-+'  →  #9467bd  (purple)
--     '---'  →  #d62728  (red)
--     other  →  #cccccc  (gray)
--
-- Optional additional columns (add to the SELECT if needed for QGIS styling):
--   ROUND((y20.lt_15_2020     - y15.lt_15_2015    )::numeric / NULLIF(y15.lt_15_2015,     0) * 100, 1) AS d_lt_15_pct
--   ROUND((y20.mid_15_64_2020 - y15.mid_15_64_2015)::numeric / NULLIF(y15.mid_15_64_2015, 0) * 100, 1) AS d_mid_15_64_pct
--   ROUND((y20.gt_65_2020     - y15.gt_65_2015    )::numeric / NULLIF(y15.gt_65_2015,     0) * 100, 1) AS d_gt_65_pct
--   (These growth rate % columns are useful for graduated symbol size in QGIS.)
-- ============================================

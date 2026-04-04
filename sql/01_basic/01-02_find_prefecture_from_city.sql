-- ============================================
-- [METADATA]
-- file: 01-02_find_prefecture_from_city.sql
-- category: basic
-- tags: #municipality #prefecture #code-lookup #region
-- difficulty: ★☆☆ (beginner)
-- estimated_complexity: low — simple key lookup, sub-second on indexed city_code
-- execution_time: <1s
-- ============================================
-- purpose: Retrieve prefecture, region, and census statistics for a given
--          municipality code (city_code) or prefecture code (pref_code).
-- input:   city_code (5-digit) for Query A
--          pref_code (2-digit) for Query B
-- output:  prefecture name, region, municipality name, population,
--          population density, elderly rate, area
-- tables:  e_stat.v_census_municipality (unified census view, latest year)
-- created: 2026-02-19
-- updated: 2026-02-19
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================
WITH params AS (
    SELECT
        '23101' AS target_city_code   -- city_code (5 digits)
        -- examples:
        --   '23101' = Chikusa-ku, Nagoya
        --   '13101' = Chiyoda-ku, Tokyo
        --   '27101' = Miyakojima-ku, Osaka
        --
        -- NOTE: For designated cities (政令指定都市), records exist at the
        -- ward (区) level only — there is no single row for the city as a whole.
        -- To query an entire designated city, use Query B with pref_code
        -- and filter by city_name prefix, or aggregate across all ward codes.
)
-- ============================================

-- [QUERY A] Single municipality lookup
SELECT
    m.pref_code       AS pref_code,
    m.pref_name       AS prefecture,
    m.region          AS region,
    m.city_code       AS city_code,
    m.city_name       AS municipality,
    m.full_name       AS official_name,
    m.population      AS population,
    m.pop_density     AS pop_density_per_km2,
    m.elderly_rate    AS elderly_rate_pct,
    m.area_km2        AS area_km2
FROM
    e_stat.v_census_municipality m,
    params p
WHERE
    m.city_code = p.target_city_code;


-- ============================================
-- [QUERY B] List all municipalities in a prefecture (uncomment to use)
-- ============================================
-- WITH params AS (
--     SELECT '23' AS target_pref_code   -- pref_code (2 digits)
--     -- examples: '23' = Aichi, '13' = Tokyo, '27' = Osaka
-- )
-- SELECT
--     m.city_code       AS city_code,
--     m.city_name       AS municipality,
--     m.full_name       AS official_name,
--     m.population      AS population,
--     m.elderly_rate    AS elderly_rate_pct,
--     m.area_km2        AS area_km2
-- FROM
--     e_stat.v_census_municipality m,
--     params p
-- WHERE
--     m.pref_code = p.target_pref_code
-- ORDER BY
--     m.population DESC NULLS LAST;

-- [NOTES]
-- · city_code is a 5-digit string: first 2 digits = pref_code,
--   last 3 digits = municipality number.
--
-- · region (e.g. "Chubu", "Kanto") is available in the census view
--   but not in admin_jp.municipalities_v2 directly.
--
-- · Rows with population IS NULL indicate municipalities where census
--   data has not yet been loaded or matched.
--
-- · Designated cities (政令指定都市) and Tokyo special wards (東京23区):
--   Data exists at ward level only. There is no aggregate row for the
--   city as a whole in this dataset.
--   Example — to find all wards in Nagoya:
--     use Query B with pref_code = '23' and filter by city_name LIKE '名古屋市%'
--
-- · v_census_municipality references the latest available census year (currently 2020).
--   For year-specific queries, use v_census_municipality_2015 or v_census_municipality_2020.

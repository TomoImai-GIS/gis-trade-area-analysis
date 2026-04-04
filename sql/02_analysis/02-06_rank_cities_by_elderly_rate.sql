-- ============================================
-- [METADATA]
-- file: 02-06_rank_cities_by_elderly_rate.sql
-- category: analysis
-- tags: #aging #demographics #elderly-care #ranking #site-selection
-- difficulty: ★☆☆ (beginner)
-- execution_time: <1s
-- estimated_complexity: low — full-table scan with filter and sort, sub-second
-- ============================================
-- purpose: Rank municipalities by elderly population rate (useful for healthcare facility site selection)
-- input:   region or prefecture name filter (optional)
-- output:  municipalities ranked by elderly rate with demographic breakdown
-- created: 2026-03-01
-- updated: 2026-03-01
-- tables:  e_stat.v_census_municipality
-- use-cases: nursing home site selection, senior services market analysis
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================
WITH params AS (
    SELECT 
        -- Filter by region (NULL = nationwide)
        -- Options: '北海道' '東北' '関東' '中部' '近畿' '中国' '四国' '九州沖縄'
        NULL::text as target_region,
        
        -- Filter by prefecture name (NULL = all)
        NULL::text as target_pref,
        
        -- Minimum population threshold (exclude very small municipalities)
        5000 as min_population,
        
        -- Number of results to return
        20 as limit_count
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
    ROUND((m.single_hh_65::numeric / NULLIF(m.households, 0) * 100), 1) as single_elderly_hh_rate,
    ROUND(m.area_km2::numeric, 2) as area_km2,
    m.pop_density
FROM e_stat.v_census_municipality m
CROSS JOIN params p
WHERE 
    -- Only municipalities with census data loaded
    m.population IS NOT NULL
    
    -- Minimum population filter
    AND m.population >= p.min_population
    
    -- Region filter (NULL = nationwide)
    AND (p.target_region IS NULL OR m.region = p.target_region)
    
    -- Prefecture filter (NULL = all)
    AND (p.target_pref IS NULL OR m.pref_name = p.target_pref)
    
ORDER BY m.elderly_rate DESC
LIMIT (SELECT limit_count FROM params);

-- ============================================
-- [NOTES]
-- ============================================
-- · Typical execution time: < 1 s
-- · Row count: determined by limit_count parameter (default 20)
-- 
-- Output columns:
--   full_name              - full official name (e.g. 秋田県男鹿市)
--   pref_name              - prefecture name
--   city_name              - municipality name
--   city_name_en           - municipality name in English (NULL for 2015 data)
--   region                 - regional grouping
--   population             - total population (2020 census)
--   pop_elderly            - population aged 65+
--   elderly_rate           - elderly rate (%)
--   age_avg                - average age
--   households             - total households
--   single_hh_65           - single-person households aged 65+
--   single_elderly_hh_rate - elderly single-person household rate (%)
--   area_km2               - area (km²)
--   pop_density            - population density (persons/km²)
--
-- Use cases:
--   - Site selection for nursing homes and care facilities
--   - Market research for senior-oriented services
--   - Cross-municipality comparison of aging trends
--
-- Customisation:
--   1. Restrict to a region: target_region = '東北'
--   2. Restrict to a prefecture: target_pref = '秋田県'
--   3. Higher population threshold: min_population = 10000
--   4. Sort ascending (lowest elderly rate first): ORDER BY m.elderly_rate ASC
-- ============================================

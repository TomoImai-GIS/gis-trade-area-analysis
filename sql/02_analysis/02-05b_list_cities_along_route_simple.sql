-- ============================================
-- [METADATA]
-- file: 02-05b_list_cities_along_route_simple.sql
-- category: analysis
-- tags: #route #municipality #travel #sales #delivery #detailed-log
-- difficulty: ★☆☆ (beginner)
-- execution_time: 1-3s
-- estimated_complexity: low — line/polygon intersection across municipality set, 1-3s
-- ============================================
-- purpose: List municipalities along a route (direct coordinate input)
-- input:   list of waypoint coordinates (lon/lat)
-- output:  municipalities the route passes through, in travel order
-- created: 2026-03-01
-- updated: 2026-03-27 (switched source to v_census_municipality; added city_name_en)
-- tables:  e_stat.v_census_municipality
-- use-cases: detailed travel logging, sales route management, delivery route analysis
-- ============================================

-- [PARAMETERS] Edit this block only
-- ============================================
-- List waypoints in order
-- Format: (sequence_number, longitude, latitude)
WITH route_points AS (
    SELECT * FROM (VALUES
        (1, 139.7673, 35.6809),  -- Tokyo Station
        (2, 138.3888, 34.9718),  -- Shizuoka Station
        (3, 137.7347, 34.7040),  -- Hamamatsu Station
        (4, 136.8816, 35.1706),  -- Nagoya Station
        (5, 136.7570, 35.4095),  -- Gifu Station
        (6, 136.6179, 35.3671),  -- Ogaki Station
        (7, 136.2632, 35.2720),  -- Hikone Station
        (8, 135.7597, 34.9853),  -- Kyoto Station
        (9, 135.4952, 34.7020)   -- Osaka Station
    ) AS t(seq, lon, lat)
),
-- ============================================

-- [MAIN QUERY] No changes needed below this line
-- Build a LineString from the waypoint list
route_line AS (
    SELECT ST_MakeLine(
        ST_SetSRID(ST_MakePoint(lon, lat), 4326) ORDER BY seq
    ) as geom
    FROM route_points
)

-- Extract municipalities that intersect the route
SELECT 
    m.full_name,
    m.pref_name,
    m.city_name,
    m.city_name_en,
    m.region,
    ROUND(m.area_km2::numeric, 2) as area_km2,
    -- Route length within this municipality (km)
    ROUND(
        (ST_Length(
            ST_Intersection(m.geom, r.geom)::geography
        ) / 1000)::numeric, 2
    ) as route_length_in_city_km,
    -- Distance from route start to entry point of this municipality (used for travel-order sort)
    ROUND(
        (ST_Length(
            ST_LineSubstring(
                r.geom,
                0,
                ST_LineLocatePoint(r.geom, 
                    ST_ClosestPoint(m.geom, ST_StartPoint(r.geom))
                )
            )::geography
        ) / 1000)::numeric, 2
    ) as distance_from_start_km
FROM e_stat.v_census_municipality m
CROSS JOIN route_line r
WHERE ST_Intersects(m.geom, r.geom)
ORDER BY distance_from_start_km;  -- sorted in travel order

-- ============================================
-- [NOTES]
-- ============================================
-- · Typical execution time: 1–3 s (slower than the prefecture-level version)
-- · Typical row count: 50–200 municipalities
-- 
-- Output columns:
--   full_name              - full official name (e.g. 愛知県名古屋市中区)
--   pref_name              - prefecture name
--   city_name              - municipality name (e.g. 名古屋市中区)
--   city_name_en           - municipality name in English (NULL for 2015 census data)
--   region                 - regional grouping (e.g. Kanto, Chubu)
--   area_km2               - municipality area (km²)
--   route_length_in_city_km - route length within this municipality (km)
--   distance_from_start_km  - distance from route start to municipality entry point (km)
--
-- Notes:
--   - Waypoints must be listed in route order
--   - At least 2 waypoints required
--   - Performance degrades above ~100 waypoints
--   - Waypoints are connected by straight lines, not actual roads
--   - Results are sorted in travel order
--   - More detailed than 02-05a (prefecture level), but slower
--
-- Use cases:
--   - Detailed travel log (which municipalities were visited)
--   - Sales route detail management (visited municipality list)
--   - Delivery route analysis (identify municipalities along the route)
--   - Detailed route reports for business trips
--   - Cycling and walking route logging
--
-- Customisation:
--   1. Add census data: the template already uses v_census_municipality,
--      so just add population, elderly_rate etc. to the SELECT list
--   
--   2. Sort by route length: ORDER BY route_length_in_city_km DESC
--   
--   3. Filter by prefecture: WHERE m.pref_name = '静岡県'
--   
--   4. Remove short crossings (noise): WHERE route_length_in_city_km > 0.5
--   
--   5. Designated city wards only: WHERE m.city_name LIKE '%区'
--
-- When to use 02-05a vs 02-05b:
--   02-05a: prefecture level (8–15 rows) — quick overview of the route
--   
--   02-05b: municipality level (50–200 rows) ← this template
--              — detailed route record; preferred for client deliverables
--
-- Example output (Tokyo → Nagoya → Osaka):
--   full_name                        | pref_name | distance_from_start
--   ---------------------------------|-----------|--------------------
--   東京都千代田区 (Chiyoda-ku)         | Tokyo     | 0.0
--   東京都港区 (Minato-ku)              | Tokyo     | 2.5
--   東京都品川区 (Shinagawa-ku)         | Tokyo     | 6.8
--   神奈川県横浜市西区 (Yokohama Nishi) | Kanagawa  | 15.2
--   ...
--
-- Performance tips:
--   - Fewer waypoints = faster execution
--   - Sample key waypoints (e.g. every 10 km)
--   - For routes over 1000 km, limit waypoints to 10–20
--
-- How to get coordinates:
--   - Google Maps: right-click → copy coordinates
--   - GSI Maps (Japan): click → coordinate display
--   - GPS device: extract key waypoints from GPX
--   - Route planner apps: manually enter station coordinates
--
-- Extracting waypoints from a GPX file (reference):
--   Using Python + gpxpy:
--   ```python
--   import gpxpy
--   gpx = gpxpy.parse(open('route.gpx'))
--   for track in gpx.tracks:
--       for segment in track.segments:
--           for i, point in enumerate(segment.points):
--               if i % 100 == 0:  # sample every 100th point
--                   print(f"({point.longitude}, {point.latitude}),")
--   ```
--
-- Related templates:
--   - 02-05c: municipality-level route analysis reading from a GPS log table (postgres_fdw)
-- ============================================

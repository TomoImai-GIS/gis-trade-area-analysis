-- ============================================
-- [METADATA]
-- file: 02-05a_list_prefectures_along_route_simple.sql
-- category: analysis
-- tags: #route #prefecture #travel #sales #delivery
-- difficulty: ★☆☆ (beginner)
-- execution_time: <1s
-- estimated_complexity: low — line/polygon intersection across prefecture set, sub-second
-- ============================================
-- purpose: List prefectures along a route (direct coordinate input)
-- input:   list of waypoint coordinates (lon/lat)
-- output:  prefectures the route passes through, in travel order
-- created: 2026-02-18
-- updated: 2026-02-18
-- tables:  admin_jp.prefectures
-- use-cases: travel logging, sales route management, delivery route analysis
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

-- Extract prefectures that intersect the route
SELECT 
    p.pref_code,
    p.pref_name,
    p.region,
    ROUND(p.area_km2::numeric, 0) as area_km2,
    -- Route length within this prefecture (km)
    ROUND(
        (ST_Length(
            ST_Intersection(p.geom, r.geom)::geography
        ) / 1000)::numeric, 2
    ) as route_length_in_pref_km,
    -- Distance from route start to entry point of this prefecture (used for travel-order sort)
    ROUND(
        (ST_Length(
            ST_LineSubstring(
                r.geom,
                0,
                ST_LineLocatePoint(r.geom, 
                    ST_ClosestPoint(p.geom, ST_StartPoint(r.geom))
                )
            )::geography
        ) / 1000)::numeric, 2
    ) as distance_from_start_km
FROM admin_jp.prefectures p
CROSS JOIN route_line r
WHERE ST_Intersects(p.geom, r.geom)
ORDER BY distance_from_start_km;  -- sorted in travel order

-- ============================================
-- [NOTES]
-- ============================================
-- · Typical execution time: 0.5–1 s
-- · Typical row count: 5–15 prefectures
-- 
-- Output columns:
--   pref_code              - prefecture code (01–47)
--   pref_name              - prefecture name
--   region                 - regional grouping (e.g. Kanto, Chubu)
--   area_km2               - prefecture area (km²)
--   route_length_in_pref_km - route length within this prefecture (km)
--   distance_from_start_km  - distance from route start to prefecture entry point (km)
--
-- Notes:
--   - Waypoints must be listed in route order
--   - At least 2 waypoints required
--   - Performance degrades above ~100 waypoints
--   - Waypoints are connected by straight lines, not actual roads
--   - Results are sorted in travel order
--
-- Use cases:
--   - Visualise travel routes
--   - Track sales routes
--   - Analyse delivery routes
--   - Generate route reports for business trips
--   - Detect cross-prefecture travel
--
-- Customisation:
--   1. For municipality-level detail, use 02-05b
--   
--   2. Sort by route length: ORDER BY route_length_in_pref_km DESC
--   
--   3. Filter by region: WHERE p.region = '関東'
--   
--   4. Exclude short crossings: WHERE route_length_in_pref_km > 10
--
-- How to get coordinates:
--   - Google Maps: right-click → copy coordinates
--   - GSI Maps (Japan): click → coordinate display
--   - GPS device: extract key waypoints from a GPX file
--   - Route planner apps: manually enter station coordinates
--
-- Example output (Tokyo → Nagoya → Osaka):
--   pref_name  | region | route_length_km | distance_from_start_km
--   -----------|--------|-----------------|------------------------
--   Tokyo      | Kanto  | 15.2            | 0.0
--   Kanagawa   | Kanto  | 28.5            | 15.2
--   Shizuoka   | Chubu  | 145.3           | 43.7
--   Aichi      | Chubu  | 42.1            | 189.0
--   Gifu       | Chubu  | 38.4            | 231.1
--   Shiga      | Kinki  | 35.2            | 269.5
--   Kyoto      | Kinki  | 28.9            | 304.7
--   Osaka      | Kinki  | 12.8            | 333.6
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
-- Loading coordinates from CSV:
--   Prepare a route.csv (columns: seq, lon, lat) and use 02-05b
-- ============================================

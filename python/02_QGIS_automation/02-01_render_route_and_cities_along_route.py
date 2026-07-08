"""
02-01_render_route_and_cities_along_route.py
Draw a GPS route and the municipalities it passes through, from a gps_log record_id.

Given a single `record_id` in the gps_log table, this QGIS Python-console script
builds and styles three map layers to reproduce the reference project:

    Cities along Route  (top)    - municipality polygons the route traverses
    Route               (middle) - the GPS track line
    OpenStreetMap       (bottom) - XYZ tile basemap

It is the automation counterpart of the SQL template
`sql/03_visualization/03-04_visualize_cities_along_route_from_gps_log.sql`:
the same cross-database spatial join is issued as a PostgreSQL query layer, then
symbolised and labelled in one step so the map is ready without manual styling.

Environment:
    QGIS 3.x Python console only (uses PyQGIS + `iface`). Not a standalone script.

Prerequisites:
    1. A saved QGIS PostgreSQL connection to the gps_log database
       (default name: "GPS_log"). host/port/password are read from this saved
       connection, so no credentials are stored in this file.
    2. The municipality polygons + names, reachable in the gps_log database as
       MUNI_TABLE. postgres_fdw makes `public.v_census_municipality` available, but
       querying that FDW view directly is slow (~70-90 s per route) because the
       remote re-runs its census joins every call. For large routes, build a LOCAL
       materialized copy once and set MUNI_TABLE = "cache.census_municipality":

           CREATE SCHEMA IF NOT EXISTS cache;
           CREATE MATERIALIZED VIEW cache.census_municipality AS
               SELECT * FROM public.v_census_municipality;
           CREATE INDEX ON cache.census_municipality USING gist (geom);
           CREATE UNIQUE INDEX ON cache.census_municipality (city_code);
           ANALYZE cache.census_municipality;
           -- refresh when the source updates (rare):
           -- REFRESH MATERIALIZED VIEW cache.census_municipality;

Usage (in the QGIS Python console):
    1. Edit the [PARAMETERS] block below (RECORD_ID, CONNECTION_NAME).
    2. Run this file:  Plugins > Python Console > "Show Editor" > Run Script,
       or  exec(open(r"...\\02-01_render_route_and_cities_along_route.py").read())
    3. To draw another record without re-running the whole file:  render(229)

Notes:
    - The query layer uses `city_code` as its unique id (an FDW view has no ctid,
      and it is the natural key on the local matview too). Municipality names are
      not nationally unique, so do not key on city_name.
    - The polygon has a 30 %-opacity fill and a thin outline in the same RGB but a
      higher opacity, so municipal boundaries read clearly over the busy basemap.
    - A light white label buffer is added for legibility over the busy basemap;
      set LABEL_BUFFER_SIZE_MM = 0 to disable it.
    - Set CITY_LABEL_LANG = "en" or "jp". This one switch drives the label column
      (CITY_LABEL_FIELDS), the label font (CITY_LABEL_FONTS), and the layer names
      (CITIES_LAYER_NAMES / ROUTE_LAYER_NAMES) together. Adjust CITY_LABEL_FONTS if a
      chosen font is missing on your system.
"""

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsDataSourceUri,
    QgsProviderRegistry,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsVectorLayerSimpleLabeling,
    QgsCoordinateTransform,
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.utils import iface

# ============================================================
# [PARAMETERS] Edit this block only
# ============================================================

RECORD_ID       = 228          # gps_log.record_id to visualise
CONNECTION_NAME = "GPS_log"    # saved QGIS PostgreSQL connection (gps_log database)
GPS_LOG_SCHEMA  = "personal"   # schema holding the gps_log table (not on the search_path)

# Source of the municipality polygons + names (schema-qualified). The default FDW
# view works out of the box once postgres_fdw is set up. For large routes it is slow
# (~70-90 s/route) because the remote re-runs its heavy census joins on every call;
# build a LOCAL materialized copy once (see the module docstring) and set this to
# "cache.census_municipality" for ~1 s renders.
MUNI_TABLE      = "public.v_census_municipality"  # or a local matview, e.g. "cache.census_municipality" (fast)

# --- Cities along Route: fill (values captured from the reference project) ---
CITY_FILL_COLOR       = "#0318ff"  # blue  (RGB 3, 24, 255); also used for the outline
CITY_FILL_OPACITY     = 0.30       # 30 % (applied as the fill colour's alpha)
CITY_OUTLINE_OPACITY  = 0.40       # outline: same RGB as the fill, its own opacity
CITY_OUTLINE_WIDTH_MM = 0.2        # thin boundary line

# --- Cities along Route: labels ---
# Pick the language once; the label column, font, and layer names all follow it.
CITY_LABEL_LANG      = "en"         # "en" = English, "jp" = Japanese
CITY_LABEL_SIZE_PT   = 10           # points
CITY_LABEL_COLOR     = "#0318ff"
LABEL_BUFFER_SIZE_MM = 1.0          # white halo for legibility; set 0 to disable

# Per-language settings (both name columns are present in the query output)
CITY_LABEL_FIELDS    = {"en": "city_name_en", "jp": "city_name"}
CITY_LABEL_FONTS     = {"en": "Arial",        "jp": "Yu Gothic UI"}  # jp: any CJK-capable font

# --- Route: line ---
ROUTE_COLOR          = "#91522d"   # brown (RGB 145, 82, 45)
ROUTE_WIDTH_MM       = 0.66

# --- Behaviour ---
REPLACE_EXISTING     = True        # remove same-named layers first (re-runnable)
ADD_BASEMAP          = True        # add an OpenStreetMap XYZ basemap at the bottom

# --- Layer names (also follow CITY_LABEL_LANG) ---
CITIES_LAYER_NAMES   = {"en": "Cities along Route", "jp": "ルート沿い市区町村"}
ROUTE_LAYER_NAMES    = {"en": "Route",              "jp": "ルート"}
BASEMAP_NAME         = "OpenStreetMap"   # kept as-is in both languages

# ============================================================
# [MAIN LOGIC] No changes needed below this line
# ============================================================


def _cities_sql(record_id):
    """Municipalities the route passes through, with polygon geometry for QGIS.

    Mirrors the main query of 03-04; record_id is inlined and the [NOTES]/params
    CTE are dropped so the statement works as a query-layer subquery.
    """
    return f"""
        SELECT
            m.city_code,
            m.full_name,
            m.pref_name,
            m.city_name,
            m.city_name_en,
            m.region,
            ROUND(m.area_km2::numeric, 2) AS area_km2,
            ROUND(
                (ST_Length(ST_Intersection(m.geom, g.geom)::geography) / 1000)::numeric, 2
            ) AS route_length_in_city_km,
            ROUND(
                (ST_Length(
                    ST_LineSubstring(
                        g.geom, 0,
                        ST_LineLocatePoint(g.geom,
                            ST_ClosestPoint(m.geom, ST_StartPoint(g.geom)))
                    )::geography
                ) / 1000)::numeric, 2
            ) AS distance_from_start_km,
            m.geom
        FROM {MUNI_TABLE} m
        CROSS JOIN {GPS_LOG_SCHEMA}.gps_log g
        WHERE g.record_id = {int(record_id)}
          AND ST_Intersects(m.geom, g.geom)
    """


def _route_sql(record_id):
    """The GPS track line for this record."""
    return f"""
        SELECT record_id, start_date, travel_distance, geom
        FROM {GPS_LOG_SCHEMA}.gps_log
        WHERE record_id = {int(record_id)}
    """


def _base_uri(connection_name):
    """Build a QgsDataSourceUri from a saved QGIS PostgreSQL connection by name."""
    md = QgsProviderRegistry.instance().providerMetadata("postgres")
    conn = md.findConnection(connection_name)
    if conn is None:
        raise RuntimeError(
            f"Saved PostgreSQL connection '{connection_name}' not found.\n"
            "Create it in the QGIS Browser (PostgreSQL > New Connection), or set "
            "CONNECTION_NAME to an existing connection that points at the gps_log DB."
        )
    return QgsDataSourceUri(conn.uri())


def _query_layer(base_uri, sql, geom_col, key_col, name, record_id):
    """Create a PostgreSQL query layer from a SQL subquery."""
    uri = QgsDataSourceUri(base_uri.uri(False))
    uri.setDataSource("", f"({sql})", geom_col, "", key_col)
    layer = QgsVectorLayer(uri.uri(False), name, "postgres")
    if not layer.isValid():
        raise RuntimeError(
            f"Failed to load layer '{name}'. Check that:\n"
            f"  - record_id={record_id} exists in gps_log\n"
            "  - postgres_fdw is configured (v_census_municipality is reachable)\n"
            "  - the connection points at the correct database"
        )
    return layer


def _rgba(hex_color, opacity):
    """'#rrggbb' + opacity(0-1) -> QGIS 'r,g,b,a' colour string."""
    color = QColor(hex_color)
    return f"{color.red()},{color.green()},{color.blue()},{int(round(opacity * 255))}"


def _lang():
    """Validated language key; falls back to 'en' for any unexpected value."""
    return CITY_LABEL_LANG if CITY_LABEL_LANG in CITY_LABEL_FIELDS else "en"


def _style_cities(layer):
    """Blue fill + a thin same-RGB, less-transparent outline + labels.

    The label column and font both follow the selected language (_lang()).
    Transparency is set per colour alpha (not symbol opacity) so the outline can be
    more opaque than the 30 % fill.
    """
    symbol = QgsFillSymbol.createSimple({
        "color": _rgba(CITY_FILL_COLOR, CITY_FILL_OPACITY),
        "outline_color": _rgba(CITY_FILL_COLOR, CITY_OUTLINE_OPACITY),
        "outline_width": str(CITY_OUTLINE_WIDTH_MM),
        "outline_style": "solid",
    })
    layer.renderer().setSymbol(symbol)

    lang = _lang()
    label = QgsPalLayerSettings()
    label.fieldName = CITY_LABEL_FIELDS[lang]

    text = QgsTextFormat()
    text.setFont(QFont(CITY_LABEL_FONTS[lang]))
    text.setSize(CITY_LABEL_SIZE_PT)           # points (QgsTextFormat default unit)
    text.setColor(QColor(CITY_LABEL_COLOR))

    if LABEL_BUFFER_SIZE_MM > 0:
        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(LABEL_BUFFER_SIZE_MM)
        buffer.setColor(QColor("white"))
        text.setBuffer(buffer)

    label.setFormat(text)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(label))
    layer.setLabelsEnabled(True)


def _style_route(layer):
    """Solid brown line."""
    symbol = QgsLineSymbol.createSimple({
        "color": ROUTE_COLOR,
        "width": str(ROUTE_WIDTH_MM),          # createSimple width unit is mm
    })
    layer.renderer().setSymbol(symbol)


def _basemap():
    """OpenStreetMap XYZ tile layer."""
    url = ("type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
           "&zmax=19&zmin=0")
    return QgsRasterLayer(url, BASEMAP_NAME, "wms")


def render(record_id=RECORD_ID, connection_name=CONNECTION_NAME):
    """Build, style, and add the three layers for one gps_log record."""
    project = QgsProject.instance()

    lang = _lang()
    cities_name = CITIES_LAYER_NAMES[lang]
    route_name  = ROUTE_LAYER_NAMES[lang]

    if REPLACE_EXISTING:
        # Remove every language variant so switching CITY_LABEL_LANG and re-running
        # refreshes cleanly instead of leaving stale, differently-named layers.
        stale = (list(CITIES_LAYER_NAMES.values())
                 + list(ROUTE_LAYER_NAMES.values())
                 + [BASEMAP_NAME])
        for name in stale:
            for existing in project.mapLayersByName(name):
                project.removeMapLayer(existing.id())

    base_uri = _base_uri(connection_name)

    cities = _query_layer(base_uri, _cities_sql(record_id),
                          "geom", "city_code", cities_name, record_id)
    route  = _query_layer(base_uri, _route_sql(record_id),
                          "geom", "record_id", route_name, record_id)

    _style_cities(cities)
    _style_route(route)

    # Add bottom-to-top; addMapLayer() inserts at the top of the layer tree, so the
    # final order is: Cities along Route (top) > Route > OpenStreetMap (bottom).
    if ADD_BASEMAP:
        osm = _basemap()
        if osm.isValid():
            project.addMapLayer(osm)
        else:
            print("Warning: OpenStreetMap basemap failed to load (offline?). Skipping.")
    project.addMapLayer(route)
    project.addMapLayer(cities)

    # Zoom to the municipalities' extent (transformed to the canvas CRS).
    if iface is not None and not cities.extent().isEmpty():
        canvas = iface.mapCanvas()
        dest_crs = canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(cities.crs(), dest_crs, project)
        extent = transform.transformBoundingBox(cities.extent())
        extent.scale(1.05)
        canvas.setExtent(extent)
        canvas.refresh()

    print(f"record_id={record_id}: {cities.featureCount()} municipalities, "
          "route and basemap loaded.")
    return cities, route


# Auto-run with the parameters above when executed from the QGIS console.
render()

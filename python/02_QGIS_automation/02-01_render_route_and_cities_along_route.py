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
    2. The municipality polygons + names. postgres_fdw makes
       `public.v_census_municipality` available, but querying that FDW view directly
       is slow (~70-90 s per route) because the remote re-runs its census joins every
       call. The script prefers a LOCAL materialized copy and falls back to the FDW
       view automatically (see MUNI_TABLE_PREFERRED / MUNI_TABLE_FALLBACK). Build the
       local copy once for fast (~1 s) renders:

           CREATE SCHEMA IF NOT EXISTS cache;
           CREATE MATERIALIZED VIEW cache.census_municipality AS
               SELECT * FROM public.v_census_municipality;
           CREATE INDEX ON cache.census_municipality USING gist (geom);
           CREATE UNIQUE INDEX ON cache.census_municipality (city_code);
           ANALYZE cache.census_municipality;
           -- refresh when the source updates (rare):
           -- REFRESH MATERIALIZED VIEW cache.census_municipality;

Usage (in the QGIS Python console):
    1. Set CONNECTION_NAME and styling defaults in [PARAMETERS] once (the municipality
       source is auto-resolved: local matview if present, else the FDW view).
    2. Run this file:  Plugins > Python Console > "Show Editor" > Run Script,
       or  exec(open(r"...\\02-01_render_route_and_cities_along_route.py").read())
       Small dialogs ask for the record_id, label language (en/jp), and whether to
       include census attributes each run, so you can redraw different records
       without editing and saving the file.
    3. To draw a specific record directly (no prompt):  render(229, lang="jp")

Notes:
    - The query layer uses `city_code` as its unique id (an FDW view has no ctid,
      and it is the natural key on the local matview too). Municipality names are
      not nationally unique, so do not key on city_name.
    - The polygon has a 30 %-opacity fill and a thin outline in the same RGB but a
      higher opacity, so municipal boundaries read clearly over the busy basemap.
    - A light white label buffer is added for legibility over the busy basemap;
      set LABEL_BUFFER_SIZE_MM = 0 to disable it.
    - Answer "yes" to the census prompt (or set INCLUDE_CENSUS = True) to carry every
      municipality column on the Cities layer, so clicking a polygon shows the full
      census profile (population, elderly rate, density, industry, ...) in Identify.
      Fast on the local matview; slow if it falls back to the FDW view.
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
from qgis.PyQt.QtWidgets import QInputDialog
from qgis.utils import iface

# ============================================================
# [PARAMETERS] Edit this block only
# ============================================================

RECORD_ID       = 228          # default record_id offered at the run-time prompt (Enter accepts it)
CONNECTION_NAME = "GPS_log"    # saved QGIS PostgreSQL connection (gps_log database)
GPS_LOG_SCHEMA  = "personal"   # schema holding the gps_log table (not on the search_path)

# Source of the municipality polygons + names (schema-qualified), resolved at run
# time: the script prefers the fast local matview and automatically falls back to the
# FDW view when the matview is absent. So it runs fast where the local cache exists
# (see the module docstring for how to build it) and still works out of the box on a
# plain postgres_fdw setup (slower on large routes, ~70-90 s/route).
MUNI_TABLE_PREFERRED = "cache.census_municipality"     # local materialized copy (fast)
MUNI_TABLE_FALLBACK  = "public.v_census_municipality"  # FDW view (works everywhere, slow)

# --- Cities along Route: fill (values captured from the reference project) ---
CITY_FILL_COLOR       = "#0318ff"  # blue  (RGB 3, 24, 255); also used for the outline
CITY_FILL_OPACITY     = 0.30       # 30 % (applied as the fill colour's alpha)
CITY_OUTLINE_OPACITY  = 0.40       # outline: same RGB as the fill, its own opacity
CITY_OUTLINE_WIDTH_MM = 0.2        # thin boundary line

# --- Cities along Route: labels ---
# Default label language offered at the run-time prompt; drives the label column,
# font, and layer names together. "en" = English, "jp" = Japanese.
CITY_LABEL_LANG      = "en"
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
INCLUDE_CENSUS       = False       # default for the prompt: carry full census attributes on the Cities layer

# --- Layer names (also follow CITY_LABEL_LANG) ---
CITIES_LAYER_NAMES   = {"en": "Cities along Route", "jp": "ルート沿い市区町村"}
ROUTE_LAYER_NAMES    = {"en": "Route",              "jp": "ルート"}
BASEMAP_NAME         = "OpenStreetMap"   # kept as-is in both languages

# ============================================================
# [MAIN LOGIC] No changes needed below this line
# ============================================================


# Identity columns shown in both modes; they always lead the attribute order.
# (area_km2 is emitted rounded; the rest are plain m.<col> references.)
_BASE_COLUMNS = ("city_code", "full_name", "pref_name", "city_name",
                 "city_name_en", "region", "area_km2")


def _cities_sql(record_id, muni_table, include_census, census_columns=None):
    """Municipalities the route passes through, with polygon geometry for QGIS.

    Mirrors the main query of 03-04; record_id is inlined and the [NOTES]/params CTE
    are dropped so the statement works as a query-layer subquery. muni_table is the
    resolved municipality source (local matview or FDW view).

    Column order is always: the base identity columns (_BASE_COLUMNS) + route metrics
    first, then (when include_census) the remaining census columns, then geom. So the
    familiar fields lead the Identify panel and the demographics follow.
    census_columns is the ordered list of extra columns to append (base/geom removed).
    """
    base_select = [
        "ROUND(m.area_km2::numeric, 2) AS area_km2" if col == "area_km2" else f"m.{col}"
        for col in _BASE_COLUMNS
    ]
    # Per-municipality route metrics (computed on the matched rows).
    route_metrics = [
        "ROUND((ST_Length(ST_Intersection(m.geom, g.geom)::geography) / 1000)::numeric, 2)"
        " AS route_length_in_city_km",
        "ROUND((ST_Length(ST_LineSubstring(g.geom, 0,"
        " ST_LineLocatePoint(g.geom, ST_ClosestPoint(m.geom, ST_StartPoint(g.geom)))"
        ")::geography) / 1000)::numeric, 2) AS distance_from_start_km",
    ]
    columns = base_select + route_metrics
    if include_census:
        columns += [f"m.{col}" for col in (census_columns or [])]
    columns += ["m.geom"]
    select_list = ",\n            ".join(columns)
    return f"""
        SELECT
            {select_list}
        FROM {muni_table} m
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


def _connection(connection_name):
    """Return the saved QGIS PostgreSQL connection (provider connection) by name."""
    md = QgsProviderRegistry.instance().providerMetadata("postgres")
    conn = md.findConnection(connection_name)
    if conn is None:
        raise RuntimeError(
            f"Saved PostgreSQL connection '{connection_name}' not found.\n"
            "Create it in the QGIS Browser (PostgreSQL > New Connection), or set "
            "CONNECTION_NAME to an existing connection that points at the gps_log DB."
        )
    return conn


def _resolve_muni_table(conn):
    """Pick the municipality source: the fast local matview if present, else the FDW view.

    Uses to_regclass(), which returns NULL for a missing/invisible relation without
    raising, so the preferred local cache is used automatically when it exists and the
    FDW view is used everywhere else.
    """
    for table in (MUNI_TABLE_PREFERRED, MUNI_TABLE_FALLBACK):
        try:
            result = conn.executeSql(f"SELECT to_regclass('{table}')")
        except Exception:
            continue
        if result and result[0] and result[0][0]:
            return table
    raise RuntimeError(
        "No municipality source is reachable. Checked:\n"
        f"  preferred (local matview): {MUNI_TABLE_PREFERRED}\n"
        f"  fallback  (FDW view)     : {MUNI_TABLE_FALLBACK}\n"
        "Configure postgres_fdw and/or build the local matview (see the docstring)."
    )


def _muni_columns(conn, muni_table):
    """Ordered column names of muni_table (pg_attribute → works for matviews/views/FDW)."""
    schema, _, table = muni_table.partition(".")
    rows = conn.executeSql(
        "SELECT a.attname FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        f"WHERE n.nspname = '{schema}' AND c.relname = '{table}' "
        "AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum"
    )
    return [row[0] for row in rows]


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


def _valid_lang(lang):
    """Validated language key; falls back to 'en' for any unexpected value."""
    return lang if lang in CITY_LABEL_FIELDS else "en"


def _style_cities(layer, lang):
    """Blue fill + a thin same-RGB, less-transparent outline + labels.

    The label column and font both follow the given language ("en"/"jp").
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


def render(record_id=RECORD_ID, connection_name=CONNECTION_NAME, lang=CITY_LABEL_LANG,
           include_census=INCLUDE_CENSUS):
    """Build, style, and add the three layers for one gps_log record."""
    project = QgsProject.instance()

    lang = _valid_lang(lang)
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

    conn = _connection(connection_name)
    base_uri = QgsDataSourceUri(conn.uri())
    muni_table = _resolve_muni_table(conn)

    # For census output, append the remaining columns after the base ones (in table
    # order), excluding the identity columns already emitted and geom.
    census_columns = None
    if include_census:
        skip = set(_BASE_COLUMNS) | {"geom"}
        census_columns = [c for c in _muni_columns(conn, muni_table) if c not in skip]

    cities = _query_layer(
        base_uri, _cities_sql(record_id, muni_table, include_census, census_columns),
        "geom", "city_code", cities_name, record_id)
    route  = _query_layer(base_uri, _route_sql(record_id),
                          "geom", "record_id", route_name, record_id)

    _style_cities(cities, lang)
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

    print(f"record_id={record_id}: {cities.featureCount()} municipalities "
          f"(source: {muni_table}, census attributes: "
          f"{'on' if include_census else 'off'}), route and basemap loaded.")
    if muni_table == MUNI_TABLE_FALLBACK:
        print(f"  Note: using the FDW view (slow on large routes). Build the local "
              f"matview {MUNI_TABLE_PREFERRED} for ~1 s renders (see the docstring).")
    return cities, route


def _ask_record_id(parent, default):
    """Modal dialog for the gps_log record_id. Returns None if cancelled."""
    value, ok = QInputDialog.getInt(
        parent, "Render route", "gps_log record_id:", default, 0)
    return value if ok else None


def _ask_lang(parent, default):
    """Modal dialog for the label language ('en'/'jp'). Returns None if cancelled."""
    items = list(CITY_LABEL_FIELDS.keys())          # ["en", "jp"]
    current = items.index(default) if default in items else 0
    text, ok = QInputDialog.getItem(
        parent, "Render route", "Label language:", items, current, False)
    return text if ok else None


def _ask_census(parent, default):
    """Modal dialog: include full census attributes on the Cities layer? bool or None."""
    items = ["no", "yes"]
    current = 1 if default else 0
    text, ok = QInputDialog.getItem(
        parent, "Render route",
        "Include census attributes on the municipality layer?", items, current, False)
    if not ok:
        return None
    return text == "yes"


def prompt_parameters():
    """Ask for the record_id, label language, and census option via modal dialogs.

    input() is not usable here: under "Run Script" the QGIS console has no stdin
    ("lost sys.stdin"), so Qt dialogs are used instead. Returns None if any dialog is
    cancelled, otherwise (record_id, lang, include_census).
    """
    parent = iface.mainWindow() if iface is not None else None
    record_id = _ask_record_id(parent, RECORD_ID)
    if record_id is None:
        return None
    lang = _ask_lang(parent, _valid_lang(CITY_LABEL_LANG))
    if lang is None:
        return None
    include_census = _ask_census(parent, INCLUDE_CENSUS)
    if include_census is None:
        return None
    return record_id, lang, include_census


# Auto-run: ask for the record_id, language, and census option (modal dialogs), then
# render. This lets you change them at run time without editing and saving the file.
_params = prompt_parameters()
if _params is not None:
    _record_id, _label_lang, _include_census = _params
    render(_record_id, lang=_label_lang, include_census=_include_census)
else:
    print("Cancelled - no layers rendered.")

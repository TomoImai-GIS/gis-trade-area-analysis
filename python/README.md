# Python Tools

Python tools for GIS data processing, spatial analysis, and visualization. Complements the PostGIS SQL templates in [`sql/`](../sql/).

> **Execution environments:** Scripts in `01_data_analytics`, `03_data_cleansing`, and `04_data_conversion` are designed for standard Python environments (PyCharm, VS Code, etc.). Scripts in `02_QGIS_automation` are designed to run in the QGIS Python console. The `99_snippets/gis_utils` package can be imported into any Python project.

---

## Folder Index

| Folder | Purpose | Environment |
|--------|---------|-------------|
| [00_notebooks/](00_notebooks/) | Jupyter Notebook showcase — analysis walkthroughs with inline output | Jupyter |
| [01_data_analytics/](01_data_analytics/) | Distribution analysis, regression, non-spatial visualization (pandas, numpy, matplotlib) | Python / PyCharm |
| [02_QGIS_automation/](02_QGIS_automation/) | Multi-layer map automation via QGIS Python console | QGIS only |
| [03_data_cleansing/](03_data_cleansing/) | Data quality checks and cleanup — null coordinates, encoding errors, duplicate records | Python / PyCharm |
| [04_data_conversion/](04_data_conversion/) | Format conversion between CSV, Excel, GeoJSON, Shapefile, and others | Python / PyCharm |
| [99_snippets/gis_utils/](99_snippets/gis_utils/) | Importable utility library for coordinate and mesh code operations | Any Python project |

---

## 01_data_analytics — Scripts

Statistical analysis and non-spatial visualization using pandas, numpy, and matplotlib.
Reads data from PostgreSQL via psycopg2. Credentials loaded from `AccessKeys/my_access.py`.

| File | Purpose | Output |
|------|---------|--------|
| [01-01_scatter_density_vs_elderly_rate.py](01_data_analytics/01-01_scatter_density_vs_elderly_rate.py) | Bubble scatter: population density vs elderly rate, colored by region, outlier-labeled | [PNG](../output/python/01-01_scatter_density_vs_elderly_rate.png) |
| [01-02_scatter_density_vs_elderly_rate_by_region.py](01_data_analytics/01-02_scatter_density_vs_elderly_rate_by_region.py) | 8-panel version of 01-01: one subplot per region, regional vs national OLS trend comparison | [PNG](../output/python/01-02_scatter_density_vs_elderly_rate_by_region.png) |

![Population density vs elderly rate](../output/python/01-01_scatter_density_vs_elderly_rate.png)
*Population density vs elderly rate by municipality (2020 Census) — bubble size = population, color = region, dashed line = OLS trend*

---

## 99_snippets/gis_utils — Utility Library

An importable Python package for common GIS coordinate operations in Japan.

### Installation

No installation required — add `99_snippets/` to your Python path:

```python
import sys
sys.path.insert(0, 'path/to/python/99_snippets')
from gis_utils import to_mesh2, to_mesh3, dms_to_dd, wgs84_to_jpr
```

> **Optional dependency:** `jpr.py` (Japan Plane Rectangular conversion) requires [pyproj](https://pypi.org/project/pyproj/): `pip install pyproj`. All other modules have no external dependencies.

### Function Index

#### mesh_code.py — JIS X 0410 Mesh Code (Japan Standard Statistical Grid)

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `to_mesh2(lat, lon)` | decimal degrees | `str` (6 digits) | Coordinate → secondary mesh code (~10 km grid) |
| `to_mesh3(lat, lon)` | decimal degrees | `str` (8 digits) | Coordinate → tertiary mesh code (~1 km grid) |
| `mesh2_to_bbox(code)` | 6-digit code | `dict` | Secondary mesh → bounding box (lat/lon min/max) |
| `mesh2_to_center(code)` | 6-digit code | `(lat, lon)` | Secondary mesh → center coordinate |
| `mesh3_to_bbox(code)` | 8-digit code | `dict` | Tertiary mesh → bounding box |
| `mesh3_to_center(code)` | 8-digit code | `(lat, lon)` | Tertiary mesh → center coordinate |

```python
from gis_utils import to_mesh2, to_mesh3, mesh2_to_center

to_mesh2(35.68, 139.77)          # → '533946'   (central Tokyo, ~10 km grid)
to_mesh3(35.68, 139.77)          # → '53394611' (~1 km grid)
mesh2_to_center('533946')        # → (35.708, 139.8125)
```

#### dms.py — Degrees-Minutes-Seconds ↔ Decimal Degrees

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `dms_to_dd(deg, min, sec, direction)` | DMS + N/S/E/W | `float` | DMS → decimal degrees |
| `dd_to_dms(dd, axis)` | decimal degrees | `(deg, min, sec, direction)` | Decimal degrees → DMS |

```python
from gis_utils import dms_to_dd, dd_to_dms

dms_to_dd(35, 40, 48, 'N')       # → 35.68
dd_to_dms(139.77, axis='lon')    # → (139, 46, 12.0, 'E')
```

#### jpr.py — WGS84 ↔ Japan Plane Rectangular Coordinate System *(requires pyproj)*

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `wgs84_to_jpr(lat, lon, zone)` | decimal degrees + zone (1-19) | `(X, Y)` metres | WGS84 → JPR (X=northing, Y=easting) |
| `jpr_to_wgs84(x, y, zone)` | metres + zone | `(lat, lon)` | JPR → WGS84 |
| `get_zone(prefecture)` | prefecture name (kanji or romaji) | `int` (1-19) | Prefecture → recommended zone number |

```python
from gis_utils import wgs84_to_jpr, jpr_to_wgs84, get_zone

get_zone('東京')                          # → 9
get_zone('osaka')                         # → 6
x, y = wgs84_to_jpr(35.6812, 139.7671, zone=9)   # Tokyo Station → (-35367, -5995) m
lat, lon = jpr_to_wgs84(x, y, zone=9)             # → (35.6812, 139.7671)
```

---

## Requirements

| Module | Dependency | Install |
|--------|-----------|---------|
| mesh_code.py | none | — |
| dms.py | none | — |
| jpr.py | pyproj >= 2.2 | `pip install pyproj` |
| 01_data_analytics | pandas, numpy, matplotlib | `pip install pandas numpy matplotlib` |
| 02_QGIS_automation | QGIS 3.x (built-in PyQGIS) | — |

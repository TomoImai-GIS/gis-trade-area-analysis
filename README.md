# GIS Trade Area Analysis

> Spatial analysis toolkit for Japan — PostGIS SQL templates and Python GIS utilities for location intelligence.

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12%2B-336791?logo=postgresql&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-3.0%2B-4CAF50)
![QGIS](https://img.shields.io/badge/QGIS-3.x-589632?logo=qgis&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)

> 🌎 Looking for the US market version? See [GIS Trade Area Analysis — US](https://github.com/TomoImai-GIS/gis-trade-area-analysis-us)

---

## Overview

A spatial analysis toolkit built on PostgreSQL + PostGIS and Python, focused on Japanese administrative boundary and census data. The SQL templates cover real-world business scenarios — retail site selection, delivery optimization, and demographic analysis — and can be run immediately by editing the `WITH params AS (...)` block at the top. The Python tools provide coordinate utilities, data processing, and QGIS automation to complement the SQL workflows.

Census data covers **1,917 municipalities** across Japan (2015 & 2020, sourced from e-Stat). Administrative boundary geometries are sourced from the national land information portal (国土数値情報, MLIT).

---

## Sample Output

![Elderly rate choropleth — nationwide](output/sql/03-02_elderly_rate_choropleth_wide.png)
*Elderly rate by municipality (nationwide) — generated with [`sql/03_visualization/03-02_generate_choropleth_elderly_rate.sql`](sql/03_visualization/03-02_generate_choropleth_elderly_rate.sql) + QGIS*

![Population density choropleth — nationwide](output/sql/03-02_population_density_choropleth_wide.png)
*Population density by municipality (nationwide) — same query styled by `pop_density` in QGIS*

---

## Use Cases

### 🏪 Trade Area Analysis
Aggregate population, elderly rate, household data, and population density within a given radius. The starting point for **retail site selection** and **franchise territory planning**.

### 👴 Demographic & Aging Analysis
Rank municipalities by elderly population rate with flexible region and population filters. Used for **healthcare facility planning** and **senior services market research**.

![Population density vs elderly rate](output/python/01-01_scatter_density_vs_elderly_rate.png)
*Population density vs elderly rate by municipality (2020 Census) — bubble size = population, color = region, dashed line = OLS trend. Generated with [`python/01_data_analytics/01-01_scatter_density_vs_elderly_rate.py`](python/01_data_analytics/01-01_scatter_density_vs_elderly_rate.py) — see [Python README](python/README.md) for details.*

The national scatter plot is not static. Tracking **how municipalities moved between 2015 and 2020** reveals four distinct demographic trajectories: urban cores are rejuvenating, inner suburbs are aging faster than expected, outer suburbs face a slow squeeze, and rural areas are entering freefall. Each trajectory carries different implications for retail siting, healthcare planning, and local fiscal sustainability.

#### Further Detailed Analysis

- **[Urban Aging Dynamics: 2015–2020 shift analysis with hypothesis testing](docs/analysis/01-03_urban_aging_dynamics.md)** — Four urban-type groups tracked across the Tokyo Metropolitan Area; hypothesis-driven narrative with verification and implications for site selection and fiscal planning.
- **[Nationwide Aging Dynamics: 3-D age-group growth rate scatter across all municipalities](docs/analysis/01-05_nationwide_aging_dynamics.md)** — All ~1,700 municipalities plotted in 3-D; reveals that Under-15 and Ages 15–64 move together as a household unit, while Ages 65+ growth is structurally independent and positive across nearly all municipalities.

### 🚚 Delivery Area Assignment & Route Analysis
Assign municipalities to their nearest depot; calculate route length through each prefecture or municipality from waypoints or a GPS log table. Built for **delivery network design** and **vehicle routing analysis**.

![Cities along route — Nagoya to Haneda Airport](output/sql/02-05c_list_cities_along_route_from_gps_log.png)
*Municipalities intersected by a route from Nagoya Station to Haneda Airport — generated with [`sql/02_analysis/02-05c_list_cities_along_route_from_gps_log.sql`](sql/02_analysis/02-05c_list_cities_along_route_from_gps_log.sql) + QGIS*

### 📦 Customer Distribution & Territory Design
Geocode customer records to municipality level, calculate penetration rates against census population, and flag data quality issues (missing IDs, out-of-range coordinates, duplicates). Supports **sales territory design** and **marketing area reporting**.

---

## SQL Templates

**13 production-ready templates** across 3 categories. All follow the same pattern — edit the params block, run the file.

| Category | Count | Description |
|----------|-------|-------------|
| [`sql/01_basic/`](sql/01_basic/) | 3 | Reverse geocoding, prefecture lookup, straight-line distance |
| [`sql/02_analysis/`](sql/02_analysis/) | 8 | Trade area population, customer aggregation, delivery assignment, route analysis, demographic ranking |
| [`sql/03_visualization/`](sql/03_visualization/) | 2 | Municipality polygon output for QGIS choropleth — elderly rate / population density; octant growth trajectory by municipality |

→ **[Full template index with code examples and output descriptions](sql/README.md)**

---

## Python Tools

Utility scripts and an importable library for coordinate operations, data processing, and QGIS automation. Designed to complement the SQL templates above.

| Folder | Purpose |
|--------|---------|
| [`python/99_snippets/gis_utils/`](python/99_snippets/gis_utils/) | Importable library: JIS mesh code, DMS ↔ decimal degrees, WGS84 ↔ Japan Plane Rectangular |
| [`python/01_data_analytics/`](python/01_data_analytics/) | Distribution analysis, regression, non-spatial visualization (pandas, numpy, matplotlib) |
| [`python/02_QGIS_automation/`](python/02_QGIS_automation/) | Multi-layer map automation via QGIS Python console |
| [`python/03_data_cleansing/`](python/03_data_cleansing/) | Data quality checks and cleanup — null coordinates, encoding errors, duplicate records |
| [`python/04_data_conversion/`](python/04_data_conversion/) | Format conversion between CSV, Excel, GeoJSON, and Shapefile |

→ **[Full Python tools index and usage examples](python/README.md)**

---

## Quick Start

### Prerequisites

- PostgreSQL 12+ with PostGIS 3.0+
- Administrative boundary data loaded into `admin_jp` schema
- Census data loaded into `e_stat` schema

See [Data Sources](#data-sources) below for download links. For census schema design and step-by-step ingestion instructions, see [`docs/census_jp_README.md`](docs/census_jp_README.md).

### 1. Enable PostGIS

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 2. Run your first query

Open any template, edit the coordinates in the `params` block, and run:

```bash
# Reverse-geocode a coordinate to municipality
psql -d your_database -f sql/01_basic/01-01_find_city_from_point.sql

# Trade area population within 30 km of Nagoya Station
psql -d your_database -f sql/02_analysis/02-01_calc_trade_area_population.sql
```

---

## Data Sources

| Dataset | Provider | License | Notes |
|---------|----------|---------|-------|
| Administrative boundaries (市区町村・都道府県) | [国土数値情報, MLIT](https://nlftp.mlit.go.jp/ksj/) | Free, attribution required | 2023 edition, 1,917 municipalities |
| Census — population & employment (国勢調査) | [e-Stat, Statistics Bureau of Japan](https://www.e-stat.go.jp/) | Free, attribution required | 2015 & 2020 |
| Road network | [OpenStreetMap](https://www.openstreetmap.org/) | ODbL — attribution required | Major roads materialized view |

> For census schema design, table definitions, and full ingestion documentation, see [`docs/census_jp_README.md`](docs/census_jp_README.md).

---

## Repository Layout

```
gis-trade-area-analysis/
├── sql/                      # SQL templates (13 production-ready)
│   ├── README.md             # Full template index with code examples
│   ├── 01_basic/             # Foundational spatial operations (3 templates)
│   ├── 02_analysis/          # Core spatial analysis (8 templates)
│   └── 03_visualization/     # QGIS / map output queries (2 templates)
├── python/                   # Python tools
│   ├── README.md             # Full tool index and usage examples
│   ├── 00_notebooks/         # Jupyter Notebook showcase
│   ├── 01_data_analytics/    # Data analysis and non-spatial visualization
│   ├── 02_QGIS_automation/   # QGIS Python console scripts
│   ├── 03_data_cleansing/    # Data quality checks and cleanup
│   ├── 04_data_conversion/   # Format conversion utilities
│   └── 99_snippets/
│       └── gis_utils/        # Importable GIS utility library
├── data/                     # Sample CSV data for testing templates
├── output/
│   ├── sql/                  # Map output examples from SQL + QGIS workflows
│   └── python/               # Chart and plot output from Python scripts
└── docs/                     # Analysis write-ups and extended documentation
    ├── README.md             # Analysis index
    ├── analysis/             # In-depth analysis documents (hypothesis → verification → implications)
    ├── images/               # Concept diagrams and hand-drawn figures
    └── census_jp_README.md   # Census data schema & ingestion design
```

---

## Attribution

Data used in this repository is sourced from:

- **国土数値情報 (MLIT)** — Administrative boundary data. Free for commercial use with attribution. [Terms](https://nlftp.mlit.go.jp/ksj/other/agreement.html)
- **e-Stat, Statistics Bureau of Japan** — Census data (国勢調査). Free for commercial use with attribution. [Terms](https://www.e-stat.go.jp/terms-of-use)
- **OpenStreetMap contributors** — Road network data. © OpenStreetMap contributors, ODbL. [Terms](https://www.openstreetmap.org/copyright)

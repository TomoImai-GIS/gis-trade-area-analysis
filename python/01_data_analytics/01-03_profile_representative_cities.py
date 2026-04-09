"""
01-03_profile_representative_cities.py
=======================================
Profile 8 representative municipalities across 4 urban-type groups,
comparing 2015 and 2020 Census data.

City codes and group definitions are configured in the ★ EDIT HERE section.
Edit only that section; the rest of the script runs automatically.

This script generates multiple figure files (one per visualisation type).

  Figure 1 — 01-03_scatter_shift.png
    Population density × elderly rate scatter plot showing how each
    municipality shifted from 2015 to 2020.
      - Open circle  : 2015 data point
      - Filled circle: 2020 data point
      - Bubble size  : population
      - Arrow        : 2015 → 2020 direction of change
      - Dashed line  : national 2020 OLS trend (reference)

Data source : e_stat.census_population (PostgreSQL / PostGIS)
Execution   : PyCharm or any standard Python environment (not QGIS)
Requirements: pandas, numpy, matplotlib, psycopg2, AccessKeys/my_access.py
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import psycopg2

# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
sys.path.append(r'C:\path\to\AccessKeys')   # ← edit before running
import my_access as ma

# ===========================================================================
# ★ EDIT HERE: 8 representative municipalities  (2 cities per group A–D)
#   Verify city_code values against 01-04_cluster_assignments.csv
# ===========================================================================
GROUP_CONFIG = [
    {
        'group': 'A',
        'label': 'Urban Core',
        'color': '#e74c3c',      # coral red
        'cities': [
            {'code': 13102, 'name': 'Chuo-ku'},       # 中央区
            {'code': 13103, 'name': 'Minato-ku'},      # 港区
        ],
    },
    {
        'group': 'B',
        'label': 'Urban Residential',
        'color': '#f39c12',      # amber
        'cities': [
            {'code': 13112, 'name': 'Setagaya-ku'},    # 世田谷区
            {'code': 13114, 'name': 'Suginami-ku'},    # 杉並区
        ],
    },
    {
        'group': 'C',
        'label': 'Suburban',
        'color': '#1abc9c',      # teal green
        'cities': [
            {'code': 13201, 'name': 'Hachioji-shi'},   # 八王子市
            {'code': 13209, 'name': 'Machida-shi'},    # 町田市
        ],
    },
    {
        'group': 'D',
        'label': 'Rural',
        'color': '#8e44ad',      # purple
        'cities': [
            {'code': 13307, 'name': 'Okutama-machi'},  # 奥多摩町
            {'code': 13361, 'name': 'Oshima-machi'},   # 大島町
        ],
    },
]
# ===========================================================================
# (end of user-editable section)
# ===========================================================================

TARGET_DB            = 'gis'
MIN_POPULATION_TREND = 5_000   # population filter for national trend line


def fmt_code(code) -> str:
    """Return city_code as a zero-padded 5-digit string.

    Handles both int and str input so users can write either form in
    GROUP_CONFIG.  Single-digit prefecture codes are padded correctly,
    e.g.  1219 → '01219'  (Hokkaido),  13102 → '13102'  (Tokyo Chuo-ku).
    """
    return str(code).zfill(5)


# Build lookup structures  (always use 5-digit string keys)
all_codes     = [fmt_code(c['code']) for grp in GROUP_CONFIG for c in grp['cities']]
code_to_group = {fmt_code(c['code']): grp for grp in GROUP_CONFIG for c in grp['cities']}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 1. Load data from PostgreSQL
# ---------------------------------------------------------------------------
SQL_NATIONAL_2020 = """
SELECT
    cp.city_code,
    cp.population,
    ROUND(cp.density::numeric, 1)                                 AS pop_density,
    ROUND(cp.gt_65::numeric / NULLIF(cp.population, 0) * 100, 1) AS elderly_rate
FROM  e_stat.census_population cp
WHERE cp.survey_year = 2020
  AND cp.population  >= %(min_pop)s
  AND cp.density      > 0
"""

SQL_CITIES_2YR = """
SELECT
    cp.city_code,
    cp.survey_year,
    cp.population,
    ROUND(cp.density::numeric, 1)                                 AS pop_density,
    ROUND(cp.gt_65::numeric / NULLIF(cp.population, 0) * 100, 1) AS elderly_rate
FROM  e_stat.census_population cp
WHERE cp.survey_year IN (2015, 2020)
  AND cp.city_code  IN %(codes)s
  AND cp.density     > 0
ORDER BY cp.city_code, cp.survey_year
"""

conn = psycopg2.connect(
    f'user={ma.pg_user()} dbname={TARGET_DB} password={ma.pg_pass()}'
)
df_nat    = pd.read_sql(SQL_NATIONAL_2020, conn,
                        params={'min_pop': MIN_POPULATION_TREND})
df_cities = pd.read_sql(SQL_CITIES_2YR, conn,
                        params={'codes': tuple(all_codes)})
conn.close()

df_nat['log_density']    = np.log10(df_nat['pop_density'])
df_cities['log_density'] = np.log10(df_cities['pop_density'])

print(f"National 2020 : {len(df_nat):,} municipalities")
print(f"Cities loaded : {df_cities['city_code'].nunique()} cities  "
      f"({len(df_cities)} rows total)")

# Warn about any missing city/year  (all_codes already contains 5-digit strings)
for code in all_codes:
    for yr in (2015, 2020):
        if df_cities[(df_cities['city_code'] == code) &
                     (df_cities['survey_year'] == yr)].empty:
            print(f"  ⚠  Missing data: city_code={code}  year={yr}")

# ---------------------------------------------------------------------------
# 2. National 2020 OLS trend line
# ---------------------------------------------------------------------------
coeffs_nat = np.polyfit(df_nat['log_density'], df_nat['elderly_rate'], deg=1)
x_trend    = np.linspace(df_nat['log_density'].min(),
                         df_nat['log_density'].max(), 300)
y_trend    = np.polyval(coeffs_nat, x_trend)

# ---------------------------------------------------------------------------
# 3. Bubble size helper
#    Scaled relative to the maximum population among the 8 cities
#    so that differences between cities are visually meaningful.
# ---------------------------------------------------------------------------
_max_pop = df_cities['population'].max()
MAX_BUBBLE = 600   # point² size for the largest city


def bubble_size(pop: float) -> float:
    return float(np.sqrt(pop) / np.sqrt(_max_pop) * MAX_BUBBLE)


# ===========================================================================
# Figure 1: Scatter shift  (density × elderly rate, 2015 → 2020)
# ===========================================================================
fig, ax = plt.subplots(figsize=(11, 8))
fig.patch.set_facecolor('white')

# ── Background: all national 2020 municipalities as gray context dots ──────
df_bg = df_nat[~df_nat['city_code'].isin(all_codes)]
ax.scatter(df_bg['log_density'], df_bg['elderly_rate'],
           c='#cccccc', s=8, alpha=0.4, linewidths=0, zorder=1,
           label='_nolegend_')

# ── National 2020 OLS trend line ──────────────────────────────────────────
ax.plot(x_trend, y_trend,
        linestyle='--', color='#aaaaaa', linewidth=1.5, zorder=2)

# ── 8 cities: 2015 open bubble → 2020 filled bubble with arrow ────────────
for grp in GROUP_CONFIG:
    color = grp['color']

    for city in grp['cities']:
        code = fmt_code(city['code'])   # always 5-digit string
        name = city['name']

        r15 = df_cities[(df_cities['city_code']   == code) &
                        (df_cities['survey_year'] == 2015)]
        r20 = df_cities[(df_cities['city_code']   == code) &
                        (df_cities['survey_year'] == 2020)]

        if r15.empty or r20.empty:
            continue

        x15 = float(r15['log_density'].iloc[0])
        y15 = float(r15['elderly_rate'].iloc[0])
        x20 = float(r20['log_density'].iloc[0])
        y20 = float(r20['elderly_rate'].iloc[0])
        s15 = bubble_size(r15['population'].iloc[0])
        s20 = bubble_size(r20['population'].iloc[0])

        # 2015 — open circle
        ax.scatter(x15, y15, s=s15,
                   facecolors='none', edgecolors=color,
                   linewidths=2.0, alpha=0.80, zorder=4)

        # 2020 — filled circle
        ax.scatter(x20, y20, s=s20,
                   c=color, alpha=0.88, linewidths=0, zorder=5)

        # Arrow 2015 → 2020
        # shrinkA/B in display points; approximate bubble radius = sqrt(s / π)
        shrink_15 = max(4.0, np.sqrt(s15 / np.pi) * 0.85)
        shrink_20 = max(4.0, np.sqrt(s20 / np.pi) * 0.85)
        ax.annotate(
            "", xy=(x20, y20), xytext=(x15, y15),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                lw=1.8,
                mutation_scale=14,
                shrinkA=shrink_15,
                shrinkB=shrink_20,
            ),
            zorder=3,
        )

        # City name label (offset from 2020 bubble)
        ax.annotate(
            name,
            xy=(x20, y20),
            xytext=(7, 4), textcoords='offset points',
            fontsize=10, color=color, fontweight='bold',
            zorder=6,
        )

# ── Axis styling ──────────────────────────────────────────────────────────
X_LIM = (-0.2, 4.8)
Y_LIM = (0, 58)
ax.set_xlim(*X_LIM)
ax.set_ylim(*Y_LIM)
ax.set_xticks([0, 1, 2, 3, 4])
ax.set_xticklabels(['1', '10', '100', '1k', '10k'])
ax.set_xlabel('Population Density (persons/km²)', fontsize=12)
ax.set_ylabel('Elderly Rate (%)', fontsize=12)
ax.grid(True, which='major', color='#dddddd', linewidth=0.8, zorder=0)
ax.set_axisbelow(True)

# ── Legend ────────────────────────────────────────────────────────────────
group_patches = [
    mpatches.Patch(color=grp['color'],
                   label=f"Group {grp['group']}: {grp['label']}")
    for grp in GROUP_CONFIG
]

year_2015 = ax.scatter([], [], s=80,
                       facecolors='none', edgecolors='#666666',
                       linewidths=2.0, label='2015  (open)')
year_2020 = ax.scatter([], [], s=80,
                       c='#666666', label='2020  (filled)')
trend_line = plt.Line2D([0], [0], linestyle='--', color='#aaaaaa',
                        linewidth=1.5,
                        label=f'National trend  (OLS, 2020, n={len(df_nat):,})')

ax.legend(
    handles=group_patches + [year_2015, year_2020, trend_line],
    fontsize=9.5, framealpha=0.92,
    loc='upper right', bbox_to_anchor=(0.99, 0.99),
)

# ── Title & source note ───────────────────────────────────────────────────
ax.set_title(
    'Population Density vs Elderly Rate: 2015 → 2020 Shift\n'
    '8 Representative Municipalities  (Tokyo)',
    fontsize=13, fontweight='bold', pad=12,
)
fig.text(
    0.5, 0.01,
    f'Source: e-Stat 2015 / 2020 Population Census  |  '
    f'bubble size = population  |  '
    f'national background: municipalities with population ≥ {MIN_POPULATION_TREND:,}',
    ha='center', fontsize=8.5, color='#888888',
)

plt.tight_layout(rect=[0, 0.03, 1, 1])

out_fig1 = os.path.join(SCRIPT_DIR, '01-03_scatter_shift.png')
fig.savefig(out_fig1, dpi=150, bbox_inches='tight', facecolor='white')
print(f"\nSaved → {out_fig1}")
plt.close()

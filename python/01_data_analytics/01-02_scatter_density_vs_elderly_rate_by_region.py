"""
01-02_scatter_density_vs_elderly_rate_by_region.py
8-panel scatter: population density vs elderly rate, one subplot per region

Same axis range and bubble-size scaling as 01-01 for direct comparison.
Each subplot shows:
  - Bubbles : municipalities in that region (region color)
  - Dark dashed line  : regional OLS trend  + slope annotation
  - Light gray dashed : national OLS trend  (reference)

Data source : e_stat.v_census_municipality (PostgreSQL / PostGIS)
Output      : PNG saved to output/python/

Execution   : PyCharm or any standard Python environment (not QGIS)
Requirements: pandas, numpy, matplotlib, psycopg2, AccessKeys/my_access.py
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator
import psycopg2

# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
sys.path.append(r'C:\path\to\AccessKeys')   # ← edit before running
import my_access as ma

# ---------------------------------------------------------------------------
# Parameters  (edit here)
# ---------------------------------------------------------------------------
TARGET_DB      = 'gis'
MIN_POPULATION = 5000

OUTPUT_DIR  = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'python')
)
OUTPUT_FILE = '01-02_scatter_density_vs_elderly_rate_by_region.png'

REGION_MAP = {
    '北海道':   'Hokkaido',
    '東北':     'Tohoku',
    '関東':     'Kanto',
    '中部':     'Chubu',
    '近畿':     'Kinki',
    '中国':     'Chugoku',
    '四国':     'Shikoku',
    '九州沖縄': 'Kyushu / Okinawa',
}

REGION_COLORS = {
    'Hokkaido':         '#1f77b4',
    'Tohoku':           '#ff7f0e',
    'Kanto':            '#d62728',
    'Chubu':            '#2ca02c',
    'Kinki':            '#9467bd',
    'Chugoku':          '#8c564b',
    'Shikoku':          '#e377c2',
    'Kyushu / Okinawa': '#7f7f7f',
}

# Subplot order: left→right, top→bottom
REGION_ORDER = [
    'Hokkaido', 'Tohoku',           'Kanto',   'Chubu',
    'Kinki',    'Chugoku',          'Shikoku', 'Kyushu / Okinawa',
]

# ---------------------------------------------------------------------------
# DB connection & data load
# ---------------------------------------------------------------------------
conn = psycopg2.connect(
    f'user={ma.pg_user()} dbname={TARGET_DB} password={ma.pg_pass()}'
)

query = """
    SELECT
        city_name_en,
        region,
        population,
        elderly_rate,
        pop_density
    FROM e_stat.v_census_municipality
    WHERE population   IS NOT NULL
      AND elderly_rate  IS NOT NULL
      AND pop_density   IS NOT NULL
      AND pop_density   > 0
      AND population   >= %(min_pop)s
"""

df = pd.read_sql(query, conn, params={'min_pop': MIN_POPULATION})
conn.close()
print(f'Loaded {len(df):,} municipalities.')

df['region'] = df['region'].map(REGION_MAP).fillna('Other')

# ---------------------------------------------------------------------------
# Derived columns  (use global max for consistent bubble sizing)
# ---------------------------------------------------------------------------
df['log_density'] = np.log10(df['pop_density'])

max_pop = df['population'].max()
df['bubble_size'] = ((np.sqrt(df['population']) / np.sqrt(max_pop)) * 400).clip(lower=15)

# National OLS (shown as reference in each subplot)
coeffs_national = np.polyfit(df['log_density'], df['elderly_rate'], deg=1)

# Shared axis limits with padding
x_min = df['log_density'].min() - 0.15
x_max = df['log_density'].max() + 0.15
y_min = df['elderly_rate'].min() - 1.5
y_max = df['elderly_rate'].max() + 1.5

reg_x = np.linspace(x_min, x_max, 300)

# Tick definitions (same as 01-01)
xtick_vals = [1, 10, 100, 1_000, 10_000]
x_minor = [np.log10(m * 10 ** d) for d in range(0, 5) for m in range(2, 10)]
x_minor = [v for v in x_minor if x_min <= v <= x_max]
y_major = np.arange(10, 60, 10)   # 10, 20, 30, 40, 50
y_minor = np.arange(5,  60, 10)   #  5, 15, 25, 35, 45, 55

# ---------------------------------------------------------------------------
# Plot  (2 rows × 4 cols)
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(2, 4, figsize=(20, 10), sharex=True, sharey=True)
fig.subplots_adjust(hspace=0.38, wspace=0.08)

for ax, region in zip(axes.flatten(), REGION_ORDER):
    df_r = df[df['region'] == region]
    color = REGION_COLORS[region]

    # Grid
    ax.set_axisbelow(True)
    ax.grid(which='major', color='#dddddd', linewidth=0.6, linestyle='-')
    ax.grid(which='minor', color='#eeeeee', linewidth=0.3, linestyle='-')
    ax.xaxis.set_minor_locator(FixedLocator(x_minor))
    ax.yaxis.set_major_locator(FixedLocator(y_major))
    ax.yaxis.set_minor_locator(FixedLocator(y_minor))

    # Bubbles
    ax.scatter(
        df_r['log_density'], df_r['elderly_rate'],
        s=df_r['bubble_size'], c=color,
        alpha=0.5, linewidths=0.3, edgecolors='white', zorder=3,
    )

    # National OLS trend (light gray, reference)
    ax.plot(reg_x, np.polyval(coeffs_national, reg_x),
            color='#cccccc', linewidth=1.2, linestyle='--', zorder=4)

    # Regional OLS trend (dark)
    if len(df_r) >= 3:
        coeffs_r = np.polyfit(df_r['log_density'], df_r['elderly_rate'], deg=1)
        ax.plot(reg_x, np.polyval(coeffs_r, reg_x),
                color='#333333', linewidth=1.5, linestyle='--', zorder=5)
        ax.text(0.04, 0.05, f'slope = {coeffs_r[0]:.2f}',
                transform=ax.transAxes, fontsize=8, va='bottom', color='#444444')

    ax.set_title(f'{region}  (n={len(df_r):,})', fontsize=10, pad=5,
                 color=color, fontweight='bold')
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

# X tick labels: bottom row only (top row hidden automatically via sharex)
axes.flatten()[0].set_xticks([np.log10(v) for v in xtick_vals])
for ax in axes[1]:
    ax.set_xticklabels([f'{v:,}' for v in xtick_vals], fontsize=8)

# ---------------------------------------------------------------------------
# Shared axis labels, title, source note
# ---------------------------------------------------------------------------
fig.supxlabel('Population Density (persons/km²)  — log scale', fontsize=11, y=0.01)
fig.supylabel('Elderly Rate  (%, aged 65+)', fontsize=11, x=0.005)

fig.suptitle(
    'Population Density vs Elderly Rate by Region — Japan (2020 Census)',
    fontsize=14, y=0.98
)

fig.text(
    0.01, -0.02,
    f'Source: e-Stat / Statistics Bureau of Japan, National Census 2020'
    f'  |  n={len(df):,} municipalities (population ≥ {MIN_POPULATION:,})'
    f'  |  Dark dashed = regional trend,  Gray dashed = national trend',
    fontsize=7.5, color='gray',
)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # reserve space for suptitle (top) and source note (bottom)

os.makedirs(OUTPUT_DIR, exist_ok=True)
out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f'Saved: {out_path}')
plt.show()

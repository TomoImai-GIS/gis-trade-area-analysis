"""
01-01_scatter_density_vs_elderly_rate.py
Bubble scatter plot: population density vs elderly rate by municipality (Japan)

X axis : population density (persons/km², log scale)
Y axis : elderly rate (%, aged 65+)
Bubble : size = population, color = region

Outlier labels are determined by residual from OLS regression line:
  - top N above trend  → higher elderly rate than density would predict
  - top N below trend  → lower elderly rate than density would predict

Data source : e_stat.v_census_municipality (PostgreSQL / PostGIS)
Output      : PNG saved to output/ at repository root

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
# AccessKeys/my_access.py must be on the Python path.
# Adjust the path below to match your environment, or add it via IDE settings.
sys.path.append(r'C:\path\to\AccessKeys')   # ← edit before running
import my_access as ma

# ---------------------------------------------------------------------------
# Parameters  (edit here)
# ---------------------------------------------------------------------------
TARGET_DB      = 'gis'
MIN_POPULATION    = 5000    # municipalities below this threshold are excluded
OUTLIER_N         = 5       # number of outlier municipalities to label per side
OUTLIER_MIN_POP   = 50_000  # only municipalities above this size are outlier candidates

OUTPUT_DIR  = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'python')
)
OUTPUT_FILE = '01-01_scatter_density_vs_elderly_rate.png'

# Mapping from DB values (Japanese) to English display labels
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
    WHERE population  IS NOT NULL
      AND elderly_rate IS NOT NULL
      AND pop_density  IS NOT NULL
      AND pop_density  > 0
      AND population  >= %(min_pop)s
"""

df = pd.read_sql(query, conn, params={'min_pop': MIN_POPULATION})
conn.close()
print(f'Loaded {len(df):,} municipalities.')

# Map region values from Japanese (DB) to English (display)
df['region'] = df['region'].map(REGION_MAP).fillna('Other')

# ---------------------------------------------------------------------------
# Derived columns
# ---------------------------------------------------------------------------
df['log_density'] = np.log10(df['pop_density'])

# Bubble size: sqrt-scaled so large cities don't overwhelm the chart
max_pop = df['population'].max()
df['bubble_size'] = ((np.sqrt(df['population']) / np.sqrt(max_pop)) * 400).clip(lower=15)

# OLS regression: elderly_rate ~ log_density
coeffs = np.polyfit(df['log_density'], df['elderly_rate'], deg=1)
df['residual'] = df['elderly_rate'] - np.polyval(coeffs, df['log_density'])

# Restrict outlier candidates to municipalities above size threshold
df_candidates = df[df['population'] >= OUTLIER_MIN_POP]
top_outliers = df_candidates.nlargest(OUTLIER_N, 'residual')    # above trend line
bot_outliers = df_candidates.nsmallest(OUTLIER_N, 'residual')   # below trend line

# Regression line points for plotting
reg_x = np.linspace(df['log_density'].min(), df['log_density'].max(), 300)
reg_y = np.polyval(coeffs, reg_x)

# National medians for quadrant dividers
med_log_density = df['log_density'].median()
med_elderly     = df['elderly_rate'].median()

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(13, 8))

# --- Bubbles (one series per region for legend) ---
for region, color in REGION_COLORS.items():
    mask = df['region'] == region
    if not mask.any():
        continue
    ax.scatter(
        df.loc[mask, 'log_density'],
        df.loc[mask, 'elderly_rate'],
        s=df.loc[mask, 'bubble_size'],
        c=color,
        alpha=0.45,
        linewidths=0.4,
        edgecolors='white',
    )

# --- Regression line ---
ax.plot(reg_x, reg_y,
        color='#333333', linewidth=1.8, linestyle='--',
        label=f'Trend (OLS,  slope={coeffs[0]:.2f})')

# --- Median dividers ---
ax.axvline(med_log_density, color='gray', linewidth=0.8, linestyle=':', alpha=0.6)
ax.axhline(med_elderly,     color='gray', linewidth=0.8, linestyle=':', alpha=0.6)

# --- Quadrant labels ---
xmin, xmax = df['log_density'].min(), df['log_density'].max()
ymin, ymax = df['elderly_rate'].min(), df['elderly_rate'].max()
quad_style = dict(fontsize=12, color='#bbbbbb', va='top', fontweight='bold')
ax.text(xmin + 0.05, ymax - 0.3, 'High aging / Low density',  **quad_style)
ax.text(xmax - 0.05, ymax - 0.3, 'High aging / High density', **quad_style, ha='right')
ax.text(xmin + 0.05, ymin + 0.5, 'Low aging / Low density',
        fontsize=12, color='#bbbbbb', va='bottom', fontweight='bold')
ax.text(xmax - 0.05, ymin + 0.5, 'Low aging / High density',
        fontsize=12, color='#bbbbbb', va='bottom', ha='right', fontweight='bold')

# --- Outlier labels ---
for _, row in pd.concat([top_outliers, bot_outliers]).iterrows():
    ax.annotate(
        row['city_name_en'],
        xy=(row['log_density'], row['elderly_rate']),
        xytext=(6, 2),
        textcoords='offset points',
        fontsize=7,
        color='#222222',
        arrowprops=dict(arrowstyle='-', color='#aaaaaa', lw=0.6),
    )

# ---------------------------------------------------------------------------
# Axis labels & title
# ---------------------------------------------------------------------------
ax.set_xlabel('Population Density (persons/km²)  — log scale', fontsize=11)
ax.set_ylabel('Elderly Rate  (%, aged 65+)', fontsize=11)
ax.set_title(
    'Population Density vs Elderly Rate by Municipality — Japan (2020 Census)',
    fontsize=13, pad=14
)

# X tick labels: show actual density values instead of log10
xtick_vals = [1, 10, 100, 1_000, 10_000]
ax.set_xticks([np.log10(v) for v in xtick_vals])
ax.set_xticklabels([f'{v:,}' for v in xtick_vals])

# ---------------------------------------------------------------------------
# Legends
# ---------------------------------------------------------------------------
# Region color legend (upper right)
region_patches = [
    mpatches.Patch(facecolor=c, alpha=0.7, label=r)
    for r, c in REGION_COLORS.items()
]
legend_region = ax.legend(
    handles=region_patches,
    title='Region', loc='upper right',
    bbox_to_anchor=(0.99, 0.90),   # shift down to clear "High aging / High density" label
    fontsize=8, title_fontsize=9, framealpha=0.85
)

# Bubble size reference legend (lower left)
for ref_pop, label in [(50_000, '50k'), (500_000, '500k'), (3_000_000, '3M')]:
    ref_size = max(15, (np.sqrt(ref_pop) / np.sqrt(max_pop)) * 400)
    ax.scatter([], [], s=ref_size, c='gray', alpha=0.5, label=label)

ax.legend(title='Population', loc='lower left',
          bbox_to_anchor=(0.01, 0.11),   # shift up to clear "Low aging / Low density" label
          fontsize=8, title_fontsize=9, framealpha=0.85)
ax.add_artist(legend_region)   # restore region legend overwritten above

# ---------------------------------------------------------------------------
# Source note
# ---------------------------------------------------------------------------
ax.text(
    0.0, -0.07,
    f'Source: e-Stat / Statistics Bureau of Japan, National Census 2020'
    f'  |  n={len(df):,} municipalities (population ≥ {MIN_POPULATION:,})',
    transform=ax.transAxes, fontsize=7.5, color='gray'
)

plt.tight_layout()

os.makedirs(OUTPUT_DIR, exist_ok=True)
out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f'Saved: {out_path}')
plt.show()

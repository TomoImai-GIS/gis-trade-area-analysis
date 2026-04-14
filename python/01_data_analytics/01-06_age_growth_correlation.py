"""
01-06_age_growth_correlation.py

Pearson correlation heatmap and scatter pair plots
2015→2020 age-group population growth rates — all Japanese municipalities

Figures
-------
  Figure 1 : 3×3 Pearson correlation heatmap
             Quantifies Finding 1 (Under-15 ↔ Ages 15-64: strong positive)
             and Finding 2 (Ages 65+ largely independent of other cohorts)
  Figure 2 : Scatter pair plots — 3 panels, one per variable pair
             Visual inspection of each pairwise relationship with OLS line,
             coloured by 8-region scheme (matching 01-01 and 01-05)

Same data pipeline as 01-05; admin_type <> '1' excludes aggregate parent records
(政令指定都市 city-level totals and 東京都区部).

Outputs (→ output/python/)
--------------------------
  01-06_correlation_heatmap.png
  01-06_scatter_pairs.png

Requirements
------------
  pip install scipy   (pandas / numpy / matplotlib / psycopg2 assumed present)
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import psycopg2
from scipy import stats

sys.path.append(r'C:\path\to\AccessKeys')   # ← edit before running
import my_access as ma

# ===========================================================================
# [PARAMETERS]  ← edit here
# ===========================================================================
TARGET_DB      = 'gis'
MIN_POPULATION = 5_000     # 2020 population threshold (matches 01-05)
CLIP_PCT       = 200.0     # clip extreme outliers at ±200 %
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR     = os.path.normpath(
    os.path.join(SCRIPT_DIR, '..', '..', 'output', 'python')
)

# Prefecture code → 8-region  (JIS X 0401 standard, matches 01-01 / 01-05)
PREF_CODE_TO_REGION: dict = {
     1: '北海道',
    **{c: '東北'     for c in range( 2,  8)},
    **{c: '関東'     for c in range( 8, 15)},
    **{c: '中部'     for c in range(15, 24)},
    **{c: '近畿'     for c in range(24, 31)},
    **{c: '中国'     for c in range(31, 36)},
    **{c: '四国'     for c in range(36, 40)},
    **{c: '九州沖縄' for c in range(40, 48)},
}
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

# Column metadata
PCT_COLS     = ['d_lt_15_pct', 'd_mid_15_64_pct', 'd_gt_65_pct']
SHORT_LABELS = ['Under-15', 'Ages 15–64', 'Ages 65+']
AXIS_LABELS  = [
    'Under-15 growth (% vs 2015)',
    'Ages 15–64 growth (% vs 2015)',
    'Ages 65+ growth (% vs 2015)',
]

# Scatter pairs: (x_col, y_col, x_label_idx, y_label_idx)
PAIRS = [
    ('d_lt_15_pct',     'd_mid_15_64_pct', 0, 1),   # Finding 1
    ('d_lt_15_pct',     'd_gt_65_pct',     0, 2),   # Finding 2a
    ('d_mid_15_64_pct', 'd_gt_65_pct',     1, 2),   # Finding 2b
]

# ===========================================================================
# [MAIN QUERY]  — identical pipeline to 01-05
# ===========================================================================
SQL = """
WITH y15 AS (
    SELECT city_code, lt_15, mid_15_64, gt_65
    FROM e_stat.census_population
    WHERE survey_year = 2015
      AND admin_type <> '1'     -- exclude 政令指定都市 & 東京都区部 aggregates
      AND lt_15     >= 50        -- minimum count to avoid noise from tiny base
      AND mid_15_64 >= 500
      AND gt_65     >= 50
),
y20 AS (
    SELECT city_code, city_name_en, population, lt_15, mid_15_64, gt_65
    FROM e_stat.census_population
    WHERE survey_year  = 2020
      AND admin_type  <> '1'
      AND population  >= %(min_pop)s
      AND lt_15     IS NOT NULL
      AND mid_15_64 IS NOT NULL
      AND gt_65     IS NOT NULL
)
SELECT
    y20.city_code,
    y20.city_name_en,
    y20.population,
    ROUND((y20.lt_15     - y15.lt_15    )::numeric / y15.lt_15     * 100, 1) AS d_lt_15_pct,
    ROUND((y20.mid_15_64 - y15.mid_15_64)::numeric / y15.mid_15_64 * 100, 1) AS d_mid_15_64_pct,
    ROUND((y20.gt_65     - y15.gt_65    )::numeric / y15.gt_65     * 100, 1) AS d_gt_65_pct
FROM y20
JOIN y15 USING (city_code)
ORDER BY y20.city_code
"""

conn = psycopg2.connect(
    f'user={ma.pg_user()} dbname={TARGET_DB} password={ma.pg_pass()}'
)
df = pd.read_sql(SQL, conn, params={'min_pop': MIN_POPULATION})
conn.close()
print(f'Loaded {len(df):,} municipalities.')

# Clip extreme outliers (tiny 2015 base → noisy growth rate)
before = (df[PCT_COLS].abs() > CLIP_PCT).any(axis=1).sum()
df[PCT_COLS] = df[PCT_COLS].clip(lower=-CLIP_PCT, upper=CLIP_PCT)
print(f'Clipped {before} rows with |growth| > {CLIP_PCT}%')

# Region assignment
df['pref_code'] = df['city_code'].str[:2].astype(int)
df['region'] = (
    df['pref_code']
    .map(PREF_CODE_TO_REGION)
    .map(REGION_MAP)
    .fillna('Other')
)
print(df['region'].value_counts().to_string())

n = len(df)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===========================================================================
# Helper
# ===========================================================================
def sig_stars(p: float) -> str:
    """Return significance stars for a p-value."""
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    return ''


# ===========================================================================
# Figure 1 — Pearson Correlation Heatmap (3×3)
# ===========================================================================
k        = len(PCT_COLS)
corr_mat = np.zeros((k, k))
pval_mat = np.ones((k, k))

for i in range(k):
    for j in range(k):
        if i == j:
            corr_mat[i, j] = 1.0
            pval_mat[i, j] = 0.0
        else:
            r, p = stats.pearsonr(df[PCT_COLS[i]], df[PCT_COLS[j]])
            corr_mat[i, j] = r
            pval_mat[i, j] = p

fig1, ax1 = plt.subplots(figsize=(6, 5.2))

im = ax1.imshow(corr_mat, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

for i in range(k):
    for j in range(k):
        r      = corr_mat[i, j]
        stars  = '' if i == j else sig_stars(pval_mat[i, j])
        tc     = 'white' if abs(r) > 0.5 else 'black'
        label  = f'r = {r:+.2f}' if i != j else 'r = 1.00'
        ax1.text(j, i, f'{label}{stars}',
                 ha='center', va='center',
                 fontsize=12, color=tc, fontweight='bold')

ax1.set_xticks(range(k))
ax1.set_yticks(range(k))
ax1.set_xticklabels(SHORT_LABELS, fontsize=11)
ax1.set_yticklabels(SHORT_LABELS, fontsize=11)
ax1.set_title(
    f'Pearson Correlation Matrix — Age-Group Growth Rates (2015→2020)\n'
    f'n = {n:,} municipalities  |  *** p < 0.001  ** p < 0.01  * p < 0.05',
    fontsize=10, pad=10,
)

cbar = fig1.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
cbar.set_label('Pearson r', fontsize=10)
cbar.set_ticks([-1.0, -0.5, 0.0, 0.5, 1.0])

fig1.tight_layout()
out1 = os.path.join(OUTPUT_DIR, '01-06_correlation_heatmap.png')
fig1.savefig(out1, dpi=150, bbox_inches='tight', facecolor='white')
print(f'Saved → {out1}')
plt.close(fig1)

# ===========================================================================
# Figure 2 — Scatter Pair Plots (1 row × 3 panels)
# ===========================================================================
fig2, axes = plt.subplots(1, 3, figsize=(16, 5.5))
fig2.suptitle(
    f'Scatter Pair Plots — Age-Group Growth Rates (2015→2020)'
    f'  |  n = {n:,} municipalities',
    fontsize=12, y=1.01,
)

for ax, (cx, cy, ix, iy) in zip(axes, PAIRS):
    # ── Scatter by region ──────────────────────────────────────────────────
    for region, color in REGION_COLORS.items():
        mask = df['region'] == region
        if not mask.any():
            continue
        ax.scatter(
            df.loc[mask, cx], df.loc[mask, cy],
            c=color, alpha=0.30, s=8, linewidths=0, rasterized=True,
        )

    # ── Zero reference lines ───────────────────────────────────────────────
    ax.axhline(0, color='#aaaaaa', linewidth=0.8, linestyle='--', zorder=1)
    ax.axvline(0, color='#aaaaaa', linewidth=0.8, linestyle='--', zorder=1)

    # ── OLS regression line ────────────────────────────────────────────────
    x_arr = df[cx].values
    y_arr = df[cy].values
    slope, intercept, r_val, p_val, _ = stats.linregress(x_arr, y_arr)
    x_fit = np.linspace(x_arr.min(), x_arr.max(), 200)
    ax.plot(x_fit, slope * x_fit + intercept,
            color='#222222', linewidth=1.5, zorder=5)

    # ── Annotation (r + p-value) ───────────────────────────────────────────
    stars = sig_stars(p_val)
    p_str = 'p < 0.001' if p_val < 0.001 else f'p = {p_val:.3f}'
    ax.text(
        0.97, 0.97,
        f'r = {r_val:+.2f}{stars}\n{p_str}',
        transform=ax.transAxes,
        ha='right', va='top', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#cccccc', alpha=0.85),
    )

    ax.set_xlabel(AXIS_LABELS[ix], fontsize=9)
    ax.set_ylabel(AXIS_LABELS[iy], fontsize=9)
    ax.tick_params(labelsize=8)

# ── Shared region legend (inside last panel, lower-right) ─────────────────
region_patches = [
    mpatches.Patch(facecolor=c, alpha=0.85, label=r)
    for r, c in REGION_COLORS.items()
]
axes[-1].legend(
    handles=region_patches,
    title='Region', fontsize=8, title_fontsize=9,
    loc='lower right', framealpha=0.9,
)

fig2.tight_layout()
out2 = os.path.join(OUTPUT_DIR, '01-06_scatter_pairs.png')
fig2.savefig(out2, dpi=150, bbox_inches='tight', facecolor='white')
print(f'Saved → {out2}')
plt.close(fig2)

# ===========================================================================
# [NOTES]
# ===========================================================================
# Pearson r interpretation guide
# --------------------------------
#   |r| > 0.7  — strong
#   |r| 0.4–0.7 — moderate
#   |r| < 0.4  — weak
#
# Expected results (informed by visual inspection of 01-05 3-D scatter):
#   Under-15  ↔ Ages 15–64 : r ≈ +0.85 (strong positive)  — Finding 1
#   Under-15  ↔ Ages 65+   : r ≈ +0.10 (weak)             — Finding 2
#   Ages 15–64 ↔ Ages 65+  : r ≈ +0.10 (weak)             — Finding 2
#
# Note on statistical significance vs. effect size:
#   With n ≈ 1,600, even r = 0.05 is statistically significant (p < 0.05).
#   Focus on the magnitude of r (effect size), not just the stars.
#
# Note on OLS in Figure 2:
#   The regression line is fitted to all municipalities.
#   Outlier municipalities with very high growth rates (e.g. central Tokyo wards
#   with Under-15 growth > +30%) can leverage the slope.
#   If needed, fit on the ±50% trimmed range for a robustness check.

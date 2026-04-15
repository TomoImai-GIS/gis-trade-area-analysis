"""
temp_octant_histogram.py  [exploratory — rename / assign ID when findings confirmed]

Distribution of age-group growth rates within the (−, −, +) octant
(Under-15 ↓, Ages 15–64 ↓, Ages 65+ ↑)

This is the modal trajectory for Japan: 1,107 / 1,603 municipalities (69.1 %).
Histograms answer:
  - How deep are the Under-15 and Ages 15–64 declines concentrated?
  - How strongly is the 65+ cohort growing?
  - Is the overall (3-cohort-sum) population still declining for most of these municipalities?
  - Are the distributions symmetric, left-/right-skewed, unimodal?

Figure layout: 2 × 2
  [Under-15 growth]   [Ages 15–64 growth]
  [Ages 65+  growth]  [Total* growth     ]

  *Total = (lt_15 + mid_15_64 + gt_65) sum across both years
   (uses the three age-group counts, not the raw census total,
    for internal consistency)

Each panel:
  - Light-gray bars   : full dataset (n ≈ 1,603)
  - Coloured bars     : (−, −, +) subset (n ≈ 1,107)
  - Solid line        : KDE for the subset
  - Dashed vert. line : mean of the subset
  - Dotted vert. line : median of the subset
  - Annotation box    : n, mean, median, std for the subset

Output → output/python/temp_octant_histogram.png

Same data pipeline as 01-06:
  admin_type <> '1'  excludes 政令指定都市 & 東京都区部 aggregates
  population  ≥ 5,000  (2020)
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
from scipy import stats
from scipy.stats import gaussian_kde

sys.path.append(r'C:\path\to\AccessKeys')   # ← edit before running
import my_access as ma

# ===========================================================================
# [PARAMETERS]
# ===========================================================================
TARGET_DB      = 'gis'
MIN_POPULATION = 5_000
CLIP_PCT       = 200.0
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR     = os.path.normpath(
    os.path.join(SCRIPT_DIR, '..', '..', 'output', 'python')
)

# Colour scheme: one accent colour per panel
PANEL_COLORS = {
    'lt15':  '#4878cf',   # blue   — Under-15
    'mid':   '#d65f00',   # amber  — Ages 15–64
    'gt65':  '#3a9e3a',   # green  — Ages 65+
    'total': '#8a4fbf',   # purple — Total
}

# ===========================================================================
# [MAIN QUERY]  — identical filter logic to 01-06
# ===========================================================================
SQL = """
WITH y15 AS (
    SELECT city_code, lt_15, mid_15_64, gt_65
    FROM e_stat.census_population
    WHERE survey_year = 2015
      AND admin_type <> '1'
      AND lt_15     >= 50
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
    y15.lt_15     AS lt_15_2015,
    y15.mid_15_64 AS mid_15_64_2015,
    y15.gt_65     AS gt_65_2015,
    y20.lt_15     AS lt_15_2020,
    y20.mid_15_64 AS mid_15_64_2020,
    y20.gt_65     AS gt_65_2020,
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
cur = conn.cursor()
cur.execute(SQL, {'min_pop': MIN_POPULATION})
cols = [desc[0] for desc in cur.description]
df   = pd.DataFrame(cur.fetchall(), columns=cols)
cur.close()
conn.close()

# Convert Decimal → float64
_num_cols = [
    'population',
    'lt_15_2015', 'mid_15_64_2015', 'gt_65_2015',
    'lt_15_2020', 'mid_15_64_2020', 'gt_65_2020',
    'd_lt_15_pct', 'd_mid_15_64_pct', 'd_gt_65_pct',
]
df[_num_cols] = df[_num_cols].apply(pd.to_numeric)

# Clip and compute totals
PCT_COLS = ['d_lt_15_pct', 'd_mid_15_64_pct', 'd_gt_65_pct']
df[PCT_COLS] = df[PCT_COLS].clip(lower=-CLIP_PCT, upper=CLIP_PCT)

df['total_2015'] = df['lt_15_2015'] + df['mid_15_64_2015'] + df['gt_65_2015']
df['total_2020'] = df['lt_15_2020'] + df['mid_15_64_2020'] + df['gt_65_2020']
df['d_total_pct'] = (
    (df['total_2020'] - df['total_2015']) / df['total_2015'] * 100
).clip(lower=-CLIP_PCT, upper=CLIP_PCT)

print(f'Total municipalities : {len(df):,}')

# Octant filter
mask_mmp = (
    (df['d_lt_15_pct']    < 0) &
    (df['d_mid_15_64_pct'] < 0) &
    (df['d_gt_65_pct']    > 0)
)
sub = df[mask_mmp].copy()
print(f'(−, −, +) subset     : {len(sub):,}  ({len(sub)/len(df)*100:.1f} %)')

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===========================================================================
# Helper
# ===========================================================================
def stats_str(s: pd.Series) -> str:
    return (
        f'n = {len(s):,}\n'
        f'mean  = {s.mean():+.1f} %\n'
        f'median= {s.median():+.1f} %\n'
        f'std   = {s.std():.1f} %'
    )


def draw_panel(ax, col_all, col_sub, color, xlabel,
               x_lo=None, x_hi=None, n_bins=40):
    """
    Draw one histogram panel.

    Parameters
    ----------
    ax       : matplotlib Axes
    col_all  : column name for the full dataset series
    col_sub  : column name for the (−,−,+) subset series (same name, different df)
    color    : accent colour for the subset
    xlabel   : x-axis label
    x_lo/hi  : manual x-axis limits (optional)
    n_bins   : histogram bin count for the subset
    """
    all_vals = df[col_all].dropna()
    sub_vals = sub[col_sub].dropna()

    # Determine x range
    lo = x_lo if x_lo is not None else all_vals.min()
    hi = x_hi if x_hi is not None else all_vals.max()
    margin = (hi - lo) * 0.02
    lo -= margin
    hi += margin

    # Full dataset (background, gray)
    ax.hist(all_vals, bins=50, range=(lo, hi),
            color='#cccccc', edgecolor='white', linewidth=0.3,
            alpha=0.6, label=f'All  (n={len(all_vals):,})', zorder=1)

    # (−,−,+) subset (foreground, colour)
    bin_edges = np.linspace(sub_vals.min() * 1.02,
                            sub_vals.max() * 1.02, n_bins + 1)
    ax.hist(sub_vals, bins=bin_edges,
            color=color, edgecolor='white', linewidth=0.3,
            alpha=0.75, label=f'(\u2212,\u2212,+)  (n={len(sub_vals):,})', zorder=2)

    # KDE for subset
    if len(sub_vals) > 10:
        kde_x = np.linspace(sub_vals.min(), sub_vals.max(), 300)
        kde_y = gaussian_kde(sub_vals)(kde_x)
        # Scale KDE to approximate histogram height
        bin_width = (sub_vals.max() - sub_vals.min()) / n_bins
        kde_y_scaled = kde_y * len(sub_vals) * bin_width
        ax.plot(kde_x, kde_y_scaled, color=color, linewidth=1.8,
                zorder=4, label='KDE (subset)')

    # Mean / Median vertical lines
    mn  = sub_vals.mean()
    med = sub_vals.median()
    ymax = ax.get_ylim()[1]
    ax.axvline(mn,  color='#111111', linewidth=1.4, linestyle='--',
               zorder=5, label=f'Mean {mn:+.1f} %')
    ax.axvline(med, color='#111111', linewidth=1.0, linestyle=':',
               zorder=5, label=f'Median {med:+.1f} %')

    # Zero reference
    ax.axvline(0, color='#999999', linewidth=0.7, linestyle='-', zorder=3)

    # Stats annotation
    ax.text(0.97, 0.96, stats_str(sub_vals),
            transform=ax.transAxes, ha='right', va='top',
            fontsize=8.5, family='monospace',
            bbox=dict(boxstyle='round,pad=0.4', fc='white',
                      ec='#cccccc', alpha=0.90),
            zorder=6)

    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel('Count', fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_xlim(lo, hi)
    ax.legend(fontsize=7.5, loc='upper left', framealpha=0.85)


# ===========================================================================
# Figure — 2 × 2 histogram grid
# ===========================================================================
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
fig.suptitle(
    'Growth Rate Distribution within the (\u2212, \u2212, +) Octant\n'
    f'(Under-15\u2193, Ages 15\u201364\u2193, Ages 65+\u2191)  '
    f'n\u2009=\u2009{len(sub):,} municipalities  ({len(sub)/len(df)*100:.1f}\u2009% of all)',
    fontsize=12, y=1.01,
)

draw_panel(
    axes[0, 0],
    col_all='d_lt_15_pct', col_sub='d_lt_15_pct',
    color=PANEL_COLORS['lt15'],
    xlabel='Under-15 growth rate (% vs 2015)',
    x_lo=-60, x_hi=5,
)
draw_panel(
    axes[0, 1],
    col_all='d_mid_15_64_pct', col_sub='d_mid_15_64_pct',
    color=PANEL_COLORS['mid'],
    xlabel='Ages 15\u201364 growth rate (% vs 2015)',
    x_lo=-45, x_hi=5,
)
draw_panel(
    axes[1, 0],
    col_all='d_gt_65_pct', col_sub='d_gt_65_pct',
    color=PANEL_COLORS['gt65'],
    xlabel='Ages 65+ growth rate (% vs 2015)',
    x_lo=-5, x_hi=40,
)
draw_panel(
    axes[1, 1],
    col_all='d_total_pct', col_sub='d_total_pct',
    color=PANEL_COLORS['total'],
    xlabel='Total (age-sum) growth rate (% vs 2015)',
    x_lo=-25, x_hi=10,
)

# Panel titles
panel_titles = [
    'Under-15',
    'Ages 15\u201364',
    'Ages 65+',
    'Total (age-group sum)',
]
for ax, title in zip(axes.flat, panel_titles):
    ax.set_title(title, fontsize=10, pad=6)

fig.tight_layout()
out = os.path.join(OUTPUT_DIR, 'temp_octant_histogram.png')
fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
print(f'Saved \u2192 {out}')
plt.close(fig)

# ===========================================================================
# Console summary
# ===========================================================================
print('\n--- (−, −, +) subset statistics ---')
summary_cols = {
    'Under-15 growth (%)':    'd_lt_15_pct',
    'Ages 15-64 growth (%)':  'd_mid_15_64_pct',
    'Ages 65+ growth (%)':    'd_gt_65_pct',
    'Total growth (%)':       'd_total_pct',
}
for label, col in summary_cols.items():
    s = sub[col]
    sk = stats.skew(s)
    ku = stats.kurtosis(s)
    print(f'\n{label}')
    print(f'  mean={s.mean():+.2f}  median={s.median():+.2f}  '
          f'std={s.std():.2f}  skew={sk:+.2f}  kurtosis={ku:.2f}')
    print(f'  10th pct={np.percentile(s,10):+.1f}  '
          f'25th={np.percentile(s,25):+.1f}  '
          f'75th={np.percentile(s,75):+.1f}  '
          f'90th={np.percentile(s,90):+.1f}')

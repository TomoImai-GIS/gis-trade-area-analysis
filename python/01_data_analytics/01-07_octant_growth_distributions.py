"""
01-07_octant_growth_distributions.py

Age-group growth rate distributions -- five major octant groups vs. full dataset
2015 to 2020 -- all Japanese municipalities

Five octant groups (all n >= 50):
  (-,-,+)  1,107  (69.1%)  Sequential depopulation -- dominant trajectory
  (-,+,+)    165  (10.3%)  15-64 growing, Under-15 declining
  (-,-,-)    143   (8.9%)  Advanced depopulation -- all cohorts negative
  (+,+,+)    136   (8.5%)  All cohorts growing
  (+,-,+)     51   (3.2%)  Under-15 growing, 15-64 declining

Outputs (one PNG per age group -> output/python/)
-------------------------------------------------
  01-07_octant_distributions_under15.png
  01-07_octant_distributions_15-64.png
  01-07_octant_distributions_65more.png
  01-07_octant_distributions_total.png

Each figure:
  Left  Y-axis : municipality count  (histogram bars)
  Right Y-axis : density             (KDE smoothing curves)
  Histogram bars: full dataset (gray) + each octant group (semi-transparent, colour)
  Legend       : sorted by n descending
  Stats box    : median / mean / std for each group (table format)

Colour scheme: identical to 01-06_octant_analysis.png

Same data pipeline as 01-05 / 01-06:
  admin_type <> '1'  excludes aggregate parent records
  population >= 5,000  (2020)
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import psycopg2
from scipy.stats import gaussian_kde

sys.path.append(r'C:\path\to\AccessKeys')   # <- edit before running
import my_access as ma

# ===========================================================================
# [PARAMETERS]
# ===========================================================================
TARGET_DB      = 'gis'
MIN_POPULATION = 5_000
CLIP_PCT       = 200.0
N_BINS         = 45          # histogram bin count (applied to the full x range)
FIG_SIZE       = (13, 7)
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR     = os.path.normpath(
    os.path.join(SCRIPT_DIR, '..', '..', 'output', 'python')
)

# Octant groups -- colours identical to 01-06_octant_analysis.png OCTANT_COLORS
GROUPS = {
    '--+': {'label': '(\u2212,\u2212,+)',            'color': '#e87700'},
    '-++': {'label': '(\u2212,+,+)',                 'color': '#aec7e8'},
    '---': {'label': '(\u2212,\u2212,\u2212)',        'color': '#d62728'},
    '+++': {'label': '(+,+,+)',                      'color': '#1f77b4'},
    '+-+': {'label': '(+,\u2212,+)',                 'color': '#9467bd'},
}

# Panel definitions: (col, x_label, x_lo, x_hi, output_filename, title)
PANELS = [
    (
        'd_lt_15_pct',
        'Under-15 growth rate (% vs 2015)',
        -30, 30,
        '01-07_octant_distributions_under15.png',
        'Under-15 Population Growth Rate by Octant Group',
    ),
    (
        'd_mid_15_64_pct',
        'Ages 15\u201364 growth rate (% vs 2015)',
        -30, 30,
        '01-07_octant_distributions_15-64.png',
        'Ages 15\u201364 Population Growth Rate by Octant Group',
    ),
    (
        'd_gt_65_pct',
        'Ages 65+ growth rate (% vs 2015)',
        -30, 30,
        '01-07_octant_distributions_65more.png',
        'Ages 65+ Population Growth Rate by Octant Group',
    ),
    (
        'd_total_pct',
        'Total (age-group sum) growth rate (% vs 2015)',
        -30, 30,
        '01-07_octant_distributions_total.png',
        'Total Population Growth Rate by Octant Group',
    ),
]

# ===========================================================================
# [MAIN QUERY]
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

# Type conversion
_num_cols = [
    'population',
    'lt_15_2015', 'mid_15_64_2015', 'gt_65_2015',
    'lt_15_2020', 'mid_15_64_2020', 'gt_65_2020',
    'd_lt_15_pct', 'd_mid_15_64_pct', 'd_gt_65_pct',
]
df[_num_cols] = df[_num_cols].apply(pd.to_numeric)

PCT_COLS = ['d_lt_15_pct', 'd_mid_15_64_pct', 'd_gt_65_pct']
df[PCT_COLS] = df[PCT_COLS].clip(lower=-CLIP_PCT, upper=CLIP_PCT)

df['total_2015'] = df['lt_15_2015'] + df['mid_15_64_2015'] + df['gt_65_2015']
df['total_2020'] = df['lt_15_2020'] + df['mid_15_64_2020'] + df['gt_65_2020']
df['d_total_pct'] = (
    (df['total_2020'] - df['total_2015']) / df['total_2015'] * 100
).clip(-CLIP_PCT, CLIP_PCT)

# Octant assignment
df['octant'] = (
    df['d_lt_15_pct'].apply(    lambda x: '+' if x >= 0 else '-') +
    df['d_mid_15_64_pct'].apply(lambda x: '+' if x >= 0 else '-') +
    df['d_gt_65_pct'].apply(    lambda x: '+' if x >= 0 else '-')
)

n_total = len(df)
print('Loaded {:,} municipalities.'.format(n_total))

# Sort group keys by n descending (used for plot order and legend)
sorted_keys = sorted(
    GROUPS.keys(),
    key=lambda k: (df['octant'] == k).sum(),
    reverse=True,
)

print('\nOctant group sizes (n-descending):')
for key in sorted_keys:
    n = (df['octant'] == key).sum()
    print('  {}: {:,}  ({:.1f}%)'.format(GROUPS[key]['label'], n, n / n_total * 100))

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ===========================================================================
# Helpers
# ===========================================================================
def build_stats_text(col):
    """Return a fixed-width stats table string for the annotation box."""
    # Column widths are set for the unicode group labels
    hdr = '{:<16} {:>6}  {:>7}  {:>7}  {:>6}'.format(
        'Group', 'n', 'Mean', 'Median', 'Std')
    sep = '\u2500' * len(hdr)
    lines = [hdr, sep]

    # "All" row first
    v = df[col].dropna()
    lines.append('{:<16} {:>6,}  {:>+6.1f}%  {:>+6.1f}%  {:>5.1f}%'.format(
        'All', len(v), v.mean(), v.median(), v.std()))

    # Each group, n-descending
    for key in sorted_keys:
        sv = df.loc[df['octant'] == key, col].dropna()
        lines.append('{:<16} {:>6,}  {:>+6.1f}%  {:>+6.1f}%  {:>5.1f}%'.format(
            GROUPS[key]['label'], len(sv), sv.mean(), sv.median(), sv.std()))

    return '\n'.join(lines)


def plot_panel(col, xlabel, xlo, xhi, fname, title):
    """
    Generate and save one histogram panel.

    Left  Y-axis: municipality count (histogram bars)
    Right Y-axis: density (KDE smoothing curves)
    """
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax2 = ax.twinx()          # right Y-axis for KDE (density)

    bin_edges = np.linspace(xlo, xhi, N_BINS + 1)
    all_vals  = df[col].dropna()

    # ── Gray histogram: full dataset (left axis, count) ──────────────────
    ax.hist(all_vals, bins=bin_edges,
            color='#cccccc', alpha=0.55,
            edgecolor='white', linewidth=0.3,
            zorder=1)

    # ── Coloured histograms: each octant group (largest first) ───────────
    for key in sorted_keys:
        sub_vals = df.loc[df['octant'] == key, col].dropna()
        ax.hist(sub_vals, bins=bin_edges,
                color=GROUPS[key]['color'], alpha=0.45,
                edgecolor='white', linewidth=0.3,
                zorder=2)

    # ── KDE curves: each octant group (right axis, density) ──────────────
    for key in sorted_keys:
        sub_vals = df.loc[df['octant'] == key, col].dropna()
        if len(sub_vals) < 5:
            continue
        sub_clipped = sub_vals.clip(xlo, xhi)
        kde   = gaussian_kde(sub_clipped)
        x_kde = np.linspace(xlo, xhi, 500)
        y_kde = kde(x_kde)
        ax2.plot(x_kde, y_kde,
                 color=GROUPS[key]['color'], linewidth=2.0,
                 alpha=0.90, zorder=5)

    # ── Group mean lines (dashed, per group colour) ───────────────────────
    # zorder=4: above histograms but below stats box (zorder=10)
    for key in sorted_keys:
        sub_vals = df.loc[df['octant'] == key, col].dropna()
        if len(sub_vals) < 5:
            continue
        ax.axvline(sub_vals.mean(),
                   color=GROUPS[key]['color'], linewidth=1.2,
                   linestyle='--', alpha=0.75, zorder=4)

    # ── Zero reference line ───────────────────────────────────────────────
    ax.axvline(0, color='#666666', linewidth=0.9, linestyle='-', zorder=3)

    # ── Axis labels ───────────────────────────────────────────────────────
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel('Count', fontsize=10, color='#333333')
    ax2.set_ylabel('Density (KDE)', fontsize=10, color='#555555')
    ax2.set_ylim(bottom=0)
    ax.set_xlim(xlo, xhi)
    ax.tick_params(labelsize=9)
    ax2.tick_params(labelsize=9)

    # ── Title ─────────────────────────────────────────────────────────────
    ax.set_title(
        '{title}\n2015\u21922020  |  n\u2009=\u2009{n:,} municipalities'.format(
            title=title, n=n_total),
        fontsize=11, pad=8,
    )

    # ── Legend (n-descending, left axis patches) ──────────────────────────
    legend_handles = [
        mpatches.Patch(facecolor='#cccccc', alpha=0.75,
                       label='All  (n={:,})'.format(n_total))
    ]
    for key in sorted_keys:
        n_sub = (df['octant'] == key).sum()
        legend_handles.append(
            mpatches.Patch(
                facecolor=GROUPS[key]['color'], alpha=0.7,
                label='{label}  n={n:,}  ({pct:.1f}%)'.format(
                    label=GROUPS[key]['label'],
                    n=n_sub,
                    pct=n_sub / n_total * 100,
                )
            )
        )
    ax.legend(handles=legend_handles,
              loc='upper left', fontsize=8.5, framealpha=0.90)

    # ── Stats annotation box ──────────────────────────────────────────────
    ax.text(
        0.985, 0.975,
        build_stats_text(col),
        transform=ax.transAxes,
        ha='right', va='top',
        fontsize=8, family='monospace',
        bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='#aaaaaa', alpha=0.92),
        zorder=10,
    )

    fig.tight_layout()
    out = os.path.join(OUTPUT_DIR, fname)
    fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    print('Saved -> {}'.format(out))
    plt.close(fig)


# ===========================================================================
# Generate all four panels
# ===========================================================================
for panel_args in PANELS:
    plot_panel(*panel_args)

print('\nDone.')

# ===========================================================================
# Console summary
# ===========================================================================
print('\n--- Mean growth rate (%) by octant group ---')
col_mid = '15\u201364'
hdr = '{:<18} {:>10} {:>10} {:>8} {:>8}'.format(
    'Group', 'Under-15', col_mid, '65+', 'Total')
print(hdr)
print('-' * len(hdr))
for key in sorted_keys:
    sub = df[df['octant'] == key]
    print('{:<18} {:>+9.1f}% {:>+9.1f}% {:>+7.1f}% {:>+7.1f}%'.format(
        GROUPS[key]['label'],
        sub['d_lt_15_pct'].mean(),
        sub['d_mid_15_64_pct'].mean(),
        sub['d_gt_65_pct'].mean(),
        sub['d_total_pct'].mean(),
    ))
print('{:<18} {:>+9.1f}% {:>+9.1f}% {:>+7.1f}% {:>+7.1f}%'.format(
    'All municipalities',
    df['d_lt_15_pct'].mean(),
    df['d_mid_15_64_pct'].mean(),
    df['d_gt_65_pct'].mean(),
    df['d_total_pct'].mean(),
))

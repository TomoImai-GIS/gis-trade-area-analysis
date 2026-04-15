"""
01-06_age_growth_correlation.py

Correlation analysis and octant breakdown
2015→2020 age-group population growth rates — all Japanese municipalities

Figures
-------
  Figure 1 : Three-panel correlation heatmap (1 row × 3 columns)
             Left   : Pearson r  on raw growth rates (%)
             Centre : Pearson r  on log growth ratio  ln(pop₂₀₂₀/pop₂₀₁₅)
             Right  : Spearman ρ (rank-based, outlier-robust)
             Shows how outlier sensitivity inflates raw Pearson for 65+ vs others.

  Figure 2 : Scatter pair plots (log growth ratio axes) — 3 panels
             OLS line + r annotation, coloured by 8-region scheme.
             Log axes compress extreme outliers for a cleaner linear view.

  Figure 3 : Octant analysis — bar chart of municipality counts by
             (+/−) sign combination of the three growth rates.
             Directly quantifies Finding 2: Q2 dominance
             (Under-15−, Ages 15–64−, Ages 65+) without distributional
             assumptions.

Same data pipeline as 01-05; admin_type <> '1' excludes aggregate parent records.
Raw counts (lt_15, mid_15_64, gt_65) are retrieved alongside growth rates
so that log ratios can be computed directly from integer counts,
avoiding the ±200 % clip issue that would make log(1 + g/100) undefined.

Outputs (→ output/python/)
--------------------------
  01-06_correlation_heatmap.png
  01-06_scatter_pairs.png
  01-06_octant_analysis.png

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
CLIP_PCT       = 200.0     # clip extreme raw-% outliers (not applied to log)
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR     = os.path.normpath(
    os.path.join(SCRIPT_DIR, '..', '..', 'output', 'python')
)

# Prefecture code → 8-region  (JIS X 0401, matches 01-01 / 01-05)
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
LOG_COLS     = ['log_lt_15',   'log_mid_15_64',   'log_gt_65']
SHORT_LABELS = ['Under-15', 'Ages 15\u201364', 'Ages 65+']
AXIS_LABELS_LOG = [
    r'Under-15  $\ln$(pop$_{2020}$/pop$_{2015}$)',
    r'Ages 15\u201364  $\ln$(pop$_{2020}$/pop$_{2015}$)',
    r'Ages 65+  $\ln$(pop$_{2020}$/pop$_{2015}$)',
]

# Scatter pairs: (x_idx, y_idx into SHORT_LABELS / LOG_COLS)
PAIRS = [
    (0, 1),   # Finding 1 : Under-15 vs Ages 15–64
    (0, 2),   # Finding 2a: Under-15 vs Ages 65+
    (1, 2),   # Finding 2b: Ages 15–64 vs Ages 65+
]

# Octant key: 3-char string using ASCII +/- (U15, 15-64, 65+)
# Display labels use the proper minus sign (U+2212)
OCTANT_ORDER  = ['--+', '+++', '-++', '+-+', '---', '++-', '+--', '-+-']
OCTANT_LABELS = {
    '--+': '(\u2212, \u2212, +)',
    '+++': '(+, +, +)',
    '-++': '(\u2212, +, +)',
    '+-+': '(+, \u2212, +)',
    '---': '(\u2212, \u2212, \u2212)',
    '++-': '(+, +, \u2212)',
    '+--': '(+, \u2212, \u2212)',
    '-+-': '(\u2212, +, \u2212)',
}
OCTANT_COLORS = {
    '--+': '#e87700',   # Sequential depopulation early/mid — amber
    '+++': '#1f77b4',   # All growing — blue
    '-++': '#aec7e8',
    '+-+': '#9467bd',
    '---': '#d62728',   # Advanced depopulation — red
    '++-': '#98df8a',
    '+--': '#ff9896',
    '-+-': '#c5b0d5',
}

# ===========================================================================
# [MAIN QUERY]  — same filter logic as 01-05; also retrieves raw counts
#               for direct log-ratio computation (avoids clip-related undefined)
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
    -- raw 2015 counts (for log-ratio computation in Python)
    y15.lt_15     AS lt_15_2015,
    y15.mid_15_64 AS mid_15_64_2015,
    y15.gt_65     AS gt_65_2015,
    -- raw 2020 counts
    y20.lt_15     AS lt_15_2020,
    y20.mid_15_64 AS mid_15_64_2020,
    y20.gt_65     AS gt_65_2020,
    -- growth rates (pct)
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

# psycopg2 returns PostgreSQL NUMERIC/DECIMAL columns as Python Decimal objects,
# which pandas stores as object dtype.  scipy.stats requires float64 arrays.
# Convert only the explicitly listed numeric columns; city_code / city_name_en
# must stay as strings (city_code is zero-padded, e.g. '01100').
_num_cols = [
    'population',
    'lt_15_2015', 'mid_15_64_2015', 'gt_65_2015',
    'lt_15_2020', 'mid_15_64_2020', 'gt_65_2020',
    'd_lt_15_pct', 'd_mid_15_64_pct', 'd_gt_65_pct',
]
df[_num_cols] = df[_num_cols].apply(pd.to_numeric)

print(f'Loaded {len(df):,} municipalities.')

# Clip raw growth rates (for Pearson-raw and octant sign)
before = (df[PCT_COLS].abs() > CLIP_PCT).any(axis=1).sum()
df[PCT_COLS] = df[PCT_COLS].clip(lower=-CLIP_PCT, upper=CLIP_PCT)
print(f'Clipped {before} rows with |growth| > {CLIP_PCT}%')

# Compute log growth ratios from raw integer counts
# log(pop_2020 / pop_2015) — always well-defined since both counts > 0
# Equivalent to log(1 + growth_pct/100) but bypasses the ±200% clip issue
df['log_lt_15']     = np.log(df['lt_15_2020']     / df['lt_15_2015'])
df['log_mid_15_64'] = np.log(df['mid_15_64_2020'] / df['mid_15_64_2015'])
df['log_gt_65']     = np.log(df['gt_65_2020']     / df['gt_65_2015'])
print('\nLog growth ratio summary:')
print(df[LOG_COLS].describe().round(3).to_string())

# Region assignment
df['pref_code'] = df['city_code'].str[:2].astype(int)
df['region'] = (
    df['pref_code']
    .map(PREF_CODE_TO_REGION)
    .map(REGION_MAP)
    .fillna('Other')
)

# Octant assignment: sign pattern of (Under-15, Ages 15-64, Ages 65+) growth
df['octant'] = (
    df['d_lt_15_pct'].apply(lambda x: '+' if x >= 0 else '-') +
    df['d_mid_15_64_pct'].apply(lambda x: '+' if x >= 0 else '-') +
    df['d_gt_65_pct'].apply(lambda x: '+' if x >= 0 else '-')
)
print('\nOctant distribution  (Under-15, Ages 15\u201364, Ages 65+):')
for key in OCTANT_ORDER:
    cnt = (df['octant'] == key).sum()
    pct = cnt / len(df) * 100
    print(f'  {OCTANT_LABELS[key]}: {cnt:4d}  ({pct:.1f}%)')

n = len(df)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ===========================================================================
# Helpers
# ===========================================================================
def sig_stars(p: float) -> str:
    """Return significance stars for a p-value."""
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    return ''


def build_corr_matrix(cols, method='pearson'):
    """Return (r_matrix, p_matrix) for given column list and method."""
    k = len(cols)
    r_mat = np.zeros((k, k))
    p_mat = np.ones((k, k))
    for i in range(k):
        for j in range(k):
            if i == j:
                r_mat[i, j] = 1.0
                p_mat[i, j] = 0.0
            else:
                xi, xj = df[cols[i]].values, df[cols[j]].values
                if method == 'pearson':
                    r, p = stats.pearsonr(xi, xj)
                else:
                    r, p = stats.spearmanr(xi, xj)
                r_mat[i, j] = r
                p_mat[i, j] = p
    return r_mat, p_mat


def draw_heatmap(ax, r_mat, p_mat, title, symbol='r', show_ylabel=True):
    """Render one correlation heatmap panel onto ax. Returns the AxesImage."""
    k = len(SHORT_LABELS)
    im = ax.imshow(r_mat, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    for i in range(k):
        for j in range(k):
            r     = r_mat[i, j]
            stars = '' if i == j else sig_stars(p_mat[i, j])
            tc    = 'white' if abs(r) > 0.5 else 'black'
            lbl   = (f'{symbol} = {r:+.2f}' if i != j
                     else f'{symbol} = 1.00')
            ax.text(j, i, f'{lbl}{stars}',
                    ha='center', va='center',
                    fontsize=11, color=tc, fontweight='bold')
    ax.set_xticks(range(k))
    ax.set_yticks(range(k))
    ax.set_xticklabels(SHORT_LABELS, fontsize=10)
    if show_ylabel:
        ax.set_yticklabels(SHORT_LABELS, fontsize=10)
    else:
        ax.set_yticklabels([])
    ax.set_title(title, fontsize=10, pad=8)
    return im


# ===========================================================================
# Figure 1 — Three-panel Correlation Heatmap
# ===========================================================================
pearson_pct_r, pearson_pct_p = build_corr_matrix(PCT_COLS, 'pearson')
pearson_log_r, pearson_log_p = build_corr_matrix(LOG_COLS, 'pearson')
spearman_r,    spearman_p    = build_corr_matrix(PCT_COLS, 'spearman')

fig1, axes1 = plt.subplots(1, 3, figsize=(15, 4.8))
fig1.suptitle(
    f'Correlation Matrix Comparison \u2014 Age-Group Growth Rates (2015\u21922020)'
    f'  |  n\u2009=\u2009{n:,} municipalities\n'
    f'*** p < 0.001  ** p < 0.01  * p < 0.05',
    fontsize=11, y=1.03,
)

im = draw_heatmap(
    axes1[0], pearson_pct_r, pearson_pct_p,
    'Pearson r\n(raw growth rates, %)',
    symbol='r', show_ylabel=True,
)
draw_heatmap(
    axes1[1], pearson_log_r, pearson_log_p,
    'Pearson r\n(log growth ratio  \u2113n(pop\u2082\u2080\u2082\u2080/pop\u2082\u2080\u2081\u2085))',
    symbol='r', show_ylabel=False,
)
draw_heatmap(
    axes1[2], spearman_r, spearman_p,
    'Spearman \u03c1\n(rank-based, outlier-robust)',
    symbol='\u03c1', show_ylabel=False,
)

cbar = fig1.colorbar(im, ax=axes1.tolist(),
                     fraction=0.018, pad=0.04, shrink=0.88)
cbar.set_label('Correlation coefficient', fontsize=9)
cbar.set_ticks([-1.0, -0.5, 0.0, 0.5, 1.0])

fig1.tight_layout()
out1 = os.path.join(OUTPUT_DIR, '01-06_correlation_heatmap.png')
fig1.savefig(out1, dpi=150, bbox_inches='tight', facecolor='white')
print(f'\nSaved \u2192 {out1}')
plt.close(fig1)


# ===========================================================================
# Figure 2 — Scatter Pair Plots (log growth ratio axes)
# ===========================================================================
fig2, axes2 = plt.subplots(1, 3, figsize=(16, 5.5))
fig2.suptitle(
    f'Scatter Pair Plots \u2014 Age-Group Log Growth Ratio (2015\u21922020)'
    f'  |  n\u2009=\u2009{n:,} municipalities',
    fontsize=12, y=1.01,
)

for ax, (ix, iy) in zip(axes2, PAIRS):
    cx, cy = LOG_COLS[ix], LOG_COLS[iy]

    # Scatter by region
    for region, color in REGION_COLORS.items():
        mask = df['region'] == region
        if not mask.any():
            continue
        ax.scatter(
            df.loc[mask, cx], df.loc[mask, cy],
            c=color, alpha=0.30, s=8, linewidths=0, rasterized=True,
        )

    # Zero reference lines
    ax.axhline(0, color='#aaaaaa', linewidth=0.8, linestyle='--', zorder=1)
    ax.axvline(0, color='#aaaaaa', linewidth=0.8, linestyle='--', zorder=1)

    # OLS regression line
    x_arr = df[cx].values
    y_arr = df[cy].values
    slope, intercept, r_val, p_val, _ = stats.linregress(x_arr, y_arr)
    x_fit = np.linspace(x_arr.min(), x_arr.max(), 200)
    ax.plot(x_fit, slope * x_fit + intercept,
            color='#222222', linewidth=1.5, zorder=5)

    # Annotation
    stars = sig_stars(p_val)
    p_str = 'p < 0.001' if p_val < 0.001 else f'p = {p_val:.3f}'
    ax.text(
        0.97, 0.97,
        f'r = {r_val:+.2f}{stars}\n{p_str}',
        transform=ax.transAxes,
        ha='right', va='top', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#cccccc', alpha=0.85),
    )

    ax.set_xlabel(AXIS_LABELS_LOG[ix], fontsize=9)
    ax.set_ylabel(AXIS_LABELS_LOG[iy], fontsize=9)
    ax.tick_params(labelsize=8)

# Shared region legend (last panel, lower-right)
region_patches = [
    mpatches.Patch(facecolor=c, alpha=0.85, label=r)
    for r, c in REGION_COLORS.items()
]
axes2[-1].legend(
    handles=region_patches,
    title='Region', fontsize=8, title_fontsize=9,
    loc='lower right', framealpha=0.9,
)

fig2.tight_layout()
out2 = os.path.join(OUTPUT_DIR, '01-06_scatter_pairs.png')
fig2.savefig(out2, dpi=150, bbox_inches='tight', facecolor='white')
print(f'Saved \u2192 {out2}')
plt.close(fig2)


# ===========================================================================
# Figure 3 — Octant Analysis
# ===========================================================================
# Count municipalities in each octant; sort by count descending
octant_counts_raw = df['octant'].value_counts()
# Preserve OCTANT_ORDER where present, then append any unexpected keys
all_keys = OCTANT_ORDER + [k for k in octant_counts_raw.index
                            if k not in OCTANT_ORDER]
counts   = [int(octant_counts_raw.get(k, 0)) for k in all_keys]
labels   = [OCTANT_LABELS.get(k, k)          for k in all_keys]
colors   = [OCTANT_COLORS.get(k, '#888888')  for k in all_keys]

# Sort by count descending
sort_idx = np.argsort(counts)[::-1]
all_keys = [all_keys[i] for i in sort_idx]
counts   = [counts[i]   for i in sort_idx]
labels   = [labels[i]   for i in sort_idx]
colors   = [colors[i]   for i in sort_idx]

fig3, ax3 = plt.subplots(figsize=(11, 5.5))
bars = ax3.bar(range(len(all_keys)), counts, color=colors,
               edgecolor='white', linewidth=0.6)

# Count + percentage annotation above each bar
for bar, cnt in zip(bars, counts):
    pct = cnt / n * 100
    ax3.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + max(counts) * 0.008,
        f'{cnt:,}\n({pct:.1f}%)',
        ha='center', va='bottom', fontsize=8.5,
    )

ax3.set_xticks(range(len(all_keys)))
ax3.set_xticklabels(labels, fontsize=10)

# Bold/colour key pattern tick labels
for ticklabel, key in zip(ax3.get_xticklabels(), all_keys):
    if key == '--+':
        ticklabel.set_color('#c05000')
        ticklabel.set_fontweight('bold')
    elif key == '---':
        ticklabel.set_color('#a00000')
        ticklabel.set_fontweight('bold')
    elif key == '+++':
        ticklabel.set_color('#0050a0')
        ticklabel.set_fontweight('bold')

ax3.set_xlabel(
    'Growth-rate sign pattern  (Under-15,  Ages 15\u201364,  Ages 65+)',
    fontsize=10,
)
ax3.set_ylabel('Number of municipalities', fontsize=10)
ax3.set_title(
    f'Octant Analysis \u2014 Municipality Count by Age-Group Growth Direction'
    f' (2015\u21922020)\n'
    f'n\u2009=\u2009{n:,}  |  + = positive growth  \u2212 = negative growth',
    fontsize=11, pad=10,
)
ax3.tick_params(axis='y', labelsize=9)
ax3.set_ylim(0, max(counts) * 1.20)

# Key-pattern legend (inside chart, top-right)
legend_text = (
    '\u25a0 (\u2212, \u2212, +)  Sequential depopulation: 65+ still growing\n'
    '\u25a0 (+, +, +)   All cohorts growing\n'
    '\u25a0 (\u2212, \u2212, \u2212)  Advanced depopulation: all cohorts declining'
)
ax3.text(
    0.97, 0.97, legend_text,
    transform=ax3.transAxes, ha='right', va='top', fontsize=8.5,
    bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='#cccccc', alpha=0.90),
    linespacing=1.6,
)

fig3.tight_layout()
out3 = os.path.join(OUTPUT_DIR, '01-06_octant_analysis.png')
fig3.savefig(out3, dpi=150, bbox_inches='tight', facecolor='white')
print(f'Saved \u2192 {out3}')
plt.close(fig3)


# ===========================================================================
# [NOTES]
# ===========================================================================
# Why three correlation measures?
# --------------------------------
# Raw Pearson r (left panel):
#   Sensitive to extreme outliers.  Fast-growing Tokyo wards (Q1: all very
#   high positive) and severely depopulated rural municipalities (Q3: all
#   very negative) both contribute large POSITIVE covariance between 65+
#   and the other cohorts, inflating r well above what the Q2 majority
#   (65+ positive, others negative) would imply alone.
#
# Log-ratio Pearson r (centre panel):
#   ln(pop_2020/pop_2015) compresses extreme positive outliers significantly:
#   +200% → ln(3) ≈ 1.10 (vs raw 200); +30% → ln(1.30) ≈ 0.26 (vs raw 30).
#   Reduces but does not eliminate Q1/Q3 leverage.  r(65+, others) should
#   decrease; may turn weakly positive or near-zero.
#
# Spearman ρ (right panel):
#   Rank-based; extreme outliers count only as rank-1 or rank-N regardless
#   of magnitude.  Most directly reflects the structural majority pattern
#   across all municipalities.  Expected: ρ(65+, others) clearly negative,
#   confirming Q2 dominance.
#
# Octant analysis (Figure 3):
#   Bypasses correlation entirely — simply counts municipalities in each of
#   the 8 sign-pattern groups.  No distributional assumption required.
#   Directly answers: "how many municipalities are in each trajectory type?"
#
# Expected results (informed by 01-05 3-D scatter):
#   Pearson raw  : r(U15, 15–64) ≈ +0.85  r(65+, others) ≈ +0.45–0.55
#   Pearson log  : r(U15, 15–64) still high; r(65+, others) ≈ +0.1–0.3
#   Spearman     : ρ(U15, 15–64) ≈ +0.80; ρ(65+, others) ≈ −0.1 to −0.3
#   Octant (−,−,+): expected plurality (~50–60% of all municipalities)

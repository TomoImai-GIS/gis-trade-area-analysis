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
#
#   city_code only — English names are fetched automatically from the DB
#   (admin_jp.municipalities_v2.city_name_en).
#
#   label_offset : (x, y) in display points from the 2020 bubble centre.
#                  Positive x → right,  positive y → up.
#                  Increase the magnitude to move the label further away.
#   label_ha     : horizontal alignment of the label text.
#                  'left'  → label extends rightward from the anchor point.
#                  'right' → label extends leftward  from the anchor point.
#                  Use 'right' when label_offset x is negative (label is to
#                  the left of the bubble).
# ===========================================================================
GROUP_CONFIG = [
    {
        'group': 'A',
        'label': 'Urban Core',
        'color': '#e74c3c',      # coral red
        'cities': [
            {'code': 13102, 'label_offset': ( 12, -20), 'label_ha': 'left'},   # 中央区
            {'code': 13103, 'label_offset': (-12,  12), 'label_ha': 'right'},  # 港区
        ],
    },
    {
        'group': 'B',
        'label': 'Urban Residential',
        'color': '#f39c12',      # amber
        'cities': [
            {'code': 13112, 'label_offset': (-12,  16), 'label_ha': 'right'},  # 世田谷区
            {'code': 13114, 'label_offset': ( 12, -18), 'label_ha': 'left'},   # 中野区
        ],
    },
    {
        'group': 'C',
        'label': 'Suburban',
        'color': '#1abc9c',      # teal green
        'cities': [
            {'code': 13201, 'label_offset': (-12,  10), 'label_ha': 'right'},  # 八王子市
            {'code': 13209, 'label_offset': ( 12,  10), 'label_ha': 'left'},   # 町田市
        ],
    },
    {
        'group': 'D',
        'label': 'Rural',
        'color': '#8e44ad',      # purple
        'cities': [
            {'code': 13307, 'label_offset': ( 10,   6), 'label_ha': 'left'},   # 檜原村
            {'code': 13361, 'label_offset': ( 10,   6), 'label_ha': 'left'},   # 大島町
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
    cp.city_name_en,
    cp.survey_year,
    cp.population,
    ROUND(cp.density::numeric, 1)                                 AS pop_density,
    ROUND(cp.gt_65::numeric / NULLIF(cp.population, 0) * 100, 1) AS elderly_rate,
    cp.lt_15,
    cp.mid_15_64,
    cp.gt_65,
    cp.lt_15_rate,
    cp.mid_15_64_rate,
    cp.gt_65_rate
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

# Build code → English name lookup from DB  (avoids hardcoding names in config)
# Use survey_year=2020 rows only; 2015 records have city_name_en = NULL
code_to_name = (
    df_cities[df_cities['survey_year'] == 2020][['city_code', 'city_name_en']]
    .drop_duplicates('city_code')
    .set_index('city_code')['city_name_en']
    .to_dict()
)

print(f"National 2020 : {len(df_nat):,} municipalities")
print(f"Cities loaded : {df_cities['city_code'].nunique()} cities  "
      f"({len(df_cities)} rows total)")
print("City name lookup from DB:")
for code, name in sorted(code_to_name.items()):
    print(f"  {code} → {name}")

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
        code = fmt_code(city['code'])               # always 5-digit string
        name = code_to_name.get(code, f'[{code}]')  # name from DB; fallback to code

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

        # City name label with thin leader line from 2020 bubble edge
        lbl_offset = city.get('label_offset', (10, 6))
        lbl_ha     = city.get('label_ha', 'left')
        ax.annotate(
            name,
            xy=(x20, y20),
            xytext=lbl_offset, textcoords='offset points',
            fontsize=10, color=color, fontweight='bold',
            ha=lbl_ha, va='center',
            arrowprops=dict(
                arrowstyle='-',
                color=color,
                lw=0.8,
                shrinkA=2,                               # gap at label end
                shrinkB=max(4.0, np.sqrt(s20 / np.pi) * 0.85),  # gap at bubble edge
            ),
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

# ===========================================================================
# Figure 2: Age Composition — stacked bars (2015 / 2020) + Δ pp bars
# ===========================================================================

# ── Constants ────────────────────────────────────────────────────────────
AGE_KEYS       = ['lt_15', 'mid_15_64', 'gt_65']
AGE_RATE_COLS  = ['lt_15_rate', 'mid_15_64_rate', 'gt_65_rate']
AGE_COLORS_MAP = {
    'lt_15':     '#66bb6a',   # green
    'mid_15_64': '#5c6bc0',   # indigo
    'gt_65':     '#ef5350',   # red
}
AGE_LABELS_MAP = {
    'lt_15':     'Under 15',
    'mid_15_64': 'Ages 15–64',
    'gt_65':     'Ages 65+',
}

CITY_SP  = 0.92   # x-spacing between cities within a group
GROUP_SP = 1.40   # extra gap between groups

# Build ordered list of (code, group_cfg) following GROUP_CONFIG order
city_order2 = [
    (fmt_code(c['code']), grp)
    for grp in GROUP_CONFIG
    for c in grp['cities']
]

# Assign x-positions
x_positions = {}
x = 0.0
for i, (code, grp) in enumerate(city_order2):
    x_positions[code] = x
    # Add a gap between groups (but not after the last city)
    if i < len(city_order2) - 1:
        next_grp = city_order2[i + 1][1]
        if next_grp is not grp:
            x += GROUP_SP
        else:
            x += CITY_SP

BAR_W = 0.38   # width of each year's bar
YEAR_OFF = {2015: -BAR_W / 2, 2020: BAR_W / 2}   # left / right of x centre

# ── Figure layout ─────────────────────────────────────────────────────────
fig2, (ax_top, ax_bot) = plt.subplots(
    2, 1, figsize=(18, 11),
    gridspec_kw={'height_ratios': [5, 4]},
    sharex=False,
)
fig2.patch.set_facecolor('white')

# ── Group background shading (both panels) ────────────────────────────────
for ax_panel in (ax_top, ax_bot):
    for grp in GROUP_CONFIG:
        codes_in_grp = [fmt_code(c['code']) for c in grp['cities']]
        xs = [x_positions[cd] for cd in codes_in_grp if cd in x_positions]
        if not xs:
            continue
        x_lo = min(xs) - CITY_SP * 0.55
        x_hi = max(xs) + CITY_SP * 0.55
        ax_panel.axvspan(x_lo, x_hi, color=grp['color'], alpha=0.14, zorder=0)

# ── Top panel: stacked composition bars ───────────────────────────────────
alpha_map = {2015: 0.58, 2020: 0.92}

for code, grp in city_order2:
    xc = x_positions[code]
    for yr in (2015, 2020):
        row = df_cities[(df_cities['city_code'] == code) &
                        (df_cities['survey_year'] == yr)]
        if row.empty:
            continue
        row = row.iloc[0]
        alpha = alpha_map[yr]
        xb = xc + YEAR_OFF[yr]
        bottom = 0.0
        for key, col in zip(AGE_KEYS, AGE_RATE_COLS):
            val = float(row[col]) if pd.notna(row[col]) else 0.0
            ax_top.bar(xb, val, width=BAR_W, bottom=bottom,
                       color=AGE_COLORS_MAP[key], alpha=alpha,
                       linewidth=0, zorder=3)
            bottom += val

# Year labels above each pair
for code, grp in city_order2:
    xc = x_positions[code]
    for yr in (2015, 2020):
        row = df_cities[(df_cities['city_code'] == code) &
                        (df_cities['survey_year'] == yr)]
        if row.empty:
            continue
        total = 100.0   # rates should sum to ~100
        ax_top.text(xc + YEAR_OFF[yr], total + 0.5,
                    str(yr), ha='center', va='bottom',
                    fontsize=7.5, color='#555555', rotation=0)

# City name x-tick labels for top panel
xtick_pos   = [x_positions[cd] for cd, _ in city_order2]
xtick_names = [code_to_name.get(cd, f'[{cd}]') for cd, _ in city_order2]
ax_top.set_xticks(xtick_pos)
ax_top.set_xticklabels(xtick_names, fontsize=10, rotation=20, ha='right')

ax_top.set_ylabel('Age Composition (%)', fontsize=11)
ax_top.set_ylim(0, 108)
ax_top.set_xlim(min(xtick_pos) - CITY_SP * 0.70,
                max(xtick_pos) + CITY_SP * 0.70)
ax_top.grid(axis='y', color='#dddddd', linewidth=0.8, zorder=0)
ax_top.set_axisbelow(True)
ax_top.set_title(
    'Age Composition & Change: 2015 vs 2020  —  8 Representative Municipalities (Tokyo)',
    fontsize=13, fontweight='bold', pad=10,
)

# Legend (top panel)
comp_patches = [
    mpatches.Patch(color=AGE_COLORS_MAP[k], label=AGE_LABELS_MAP[k])
    for k in AGE_KEYS
]
yr2015_patch = mpatches.Patch(facecolor='#aaaaaa', alpha=0.58, label='2015  (lighter)')
yr2020_patch = mpatches.Patch(facecolor='#aaaaaa', alpha=0.92, label='2020  (darker)')
grp_patches2 = [
    mpatches.Patch(color=grp['color'],
                   label=f"Group {grp['group']}: {grp['label']}")
    for grp in GROUP_CONFIG
]
ax_top.legend(
    handles=comp_patches + [yr2015_patch, yr2020_patch] + grp_patches2,
    fontsize=9, framealpha=0.95,
    loc='upper left', bbox_to_anchor=(1.02, 1.0),
    borderaxespad=0, ncol=1,
)

# ── Bottom panel: age-group population growth rate (%) ───────────────────
#   = (count_2020 − count_2015) / count_2015 × 100
#   Reveals "which layer drove the composition shift" rather than
#   simply restating the composition-share change shown in the top panel.
DELTA_W = 0.22    # width per age-group bar within one city slot
DELTA_OFFSETS = {
    'lt_15':     -DELTA_W,
    'mid_15_64':  0.0,
    'gt_65':      DELTA_W,
}
# Absolute-count columns (no '_rate' suffix)
AGE_COUNT_COLS = AGE_KEYS   # ['lt_15', 'mid_15_64', 'gt_65']

for code, grp in city_order2:
    xc = x_positions[code]
    r15 = df_cities[(df_cities['city_code'] == code) &
                    (df_cities['survey_year'] == 2015)]
    r20 = df_cities[(df_cities['city_code'] == code) &
                    (df_cities['survey_year'] == 2020)]
    if r15.empty or r20.empty:
        continue
    r15, r20 = r15.iloc[0], r20.iloc[0]

    for key in AGE_COUNT_COLS:
        v15 = float(r15[key]) if pd.notna(r15[key]) else None
        v20 = float(r20[key]) if pd.notna(r20[key]) else None
        if v15 is None or v20 is None or v15 == 0:
            continue
        growth_pct = (v20 - v15) / v15 * 100
        xb = xc + DELTA_OFFSETS[key]
        color = AGE_COLORS_MAP[key]
        ax_bot.bar(xb, growth_pct, width=DELTA_W * 0.88,
                   color=color, alpha=0.85,
                   linewidth=0, zorder=3)
        # Value annotation — skip if too small to read clearly
        va_pos = 'bottom' if growth_pct >= 0 else 'top'
        y_ann  = growth_pct + (0.4 if growth_pct >= 0 else -0.4)
        ax_bot.text(xb, y_ann, f'{growth_pct:+.1f}%',
                    ha='center', va=va_pos,
                    fontsize=7.0, color='#333333', zorder=4)

ax_bot.axhline(0, color='#888888', linewidth=1.0, zorder=2)
ax_bot.set_xticks(xtick_pos)
ax_bot.set_xticklabels(xtick_names, fontsize=10, rotation=20, ha='right')
ax_bot.set_ylabel('Population Growth by Age Group\n(2020 vs 2015, %)', fontsize=11)
ax_bot.set_xlim(ax_top.get_xlim())
ax_bot.grid(axis='y', color='#dddddd', linewidth=0.8, zorder=0)
ax_bot.set_axisbelow(True)

# Legend (bottom panel)
delta_patches = [
    mpatches.Patch(color=AGE_COLORS_MAP[k], alpha=0.85,
                   label=f'{AGE_LABELS_MAP[k]} growth rate')
    for k in AGE_KEYS
]
ax_bot.legend(handles=delta_patches, fontsize=9, framealpha=0.95,
              loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderaxespad=0)

# ── Group name labels: bottom panel only, watermark style ─────────────────
#   Placed behind bars (zorder=1) at vertical centre of the panel.
#   Group colour at low alpha → readable but non-intrusive.
ax_bot.set_ylim(-25, 48)   # ylim centre ≈ 11.5; use 10 as label y

for grp in GROUP_CONFIG:
    _codes = [fmt_code(c['code']) for c in grp['cities']]
    _xs    = [x_positions[cd] for cd in _codes if cd in x_positions]
    if not _xs:
        continue
    _x_right = max(_xs) + CITY_SP * 0.50   # close to right edge of group shading
    ax_bot.text(
        _x_right, 45,
        f'Group {grp["group"]}',
        ha='right', va='top',
        fontsize=25, fontweight='bold',
        color=grp['color'], alpha=0.30,
        zorder=1,
    )

# ── Source note ───────────────────────────────────────────────────────────
fig2.text(
    0.5, 0.01,
    'Source: e-Stat 2015 / 2020 Population Census  |  '
    'top: age composition shares (lt_15_rate / mid_15_64_rate / gt_65_rate)  |  '
    'bottom: (count_2020 − count_2015) / count_2015 × 100',
    ha='center', fontsize=8.5, color='#888888',
)

plt.tight_layout(rect=[0, 0.03, 0.82, 1])

out_fig2 = os.path.join(SCRIPT_DIR, '01-03_age_composition.png')
fig2.savefig(out_fig2, dpi=150, bbox_inches='tight', facecolor='white')
print(f"Saved → {out_fig2}")
plt.close()

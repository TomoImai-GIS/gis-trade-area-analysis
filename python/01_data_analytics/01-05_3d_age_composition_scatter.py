"""
01-05_3d_age_composition_scatter.py

3-D bubble scatter — 2015→2020 age-group population growth rate (%)
All Japanese municipalities with data in both census years (population >= 5,000)

Axes  (same formula as 01-03_age_composition.png bottom panel)
--------------------------------------------------------------
X : Under-15   growth rate  = (lt_15_2020  - lt_15_2015)  / lt_15_2015  × 100
Y : Ages 15-64 growth rate  = (mid_15_64_2020 - mid_15_64_2015) / mid_15_64_2015 × 100
Z : Ages 65+   growth rate  = (gt_65_2020  - gt_65_2015)  / gt_65_2015  × 100

Normalising by 2015 base removes the city-size effect: a small rural village
and a large metro can be compared on equal footing.

Expected cluster patterns (extending 01-03 to national scale)
--------------------------------------------------------------
  Urban Core   type  :  +X large, +Y, +Z modest  (youth grew fastest → rate fell)
  Urban Resid. type  :  small positive on all axes (gentle equilibrium)
  Suburban     type  :  −X or 0 (youth fell), +Z (elderly absolute increase)
  Rural        type  :  −X, −Y large (working-age exodus), +Z moderate

Bubbles : size = 2020 population (√-scaled), colour = 8-region scheme (01-01)

Outputs
-------
  01-05_3d_age_static.png        — 3 static views rotating around Z axis
  01-05_3d_age_interactive.html  — Plotly interactive: drag + azimuth slider

Requirements
------------
  pip install plotly   (matplotlib / psycopg2 assumed already present)
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import psycopg2

sys.path.append(r'C:\path\to\AccessKeys')   # ← edit before running
import my_access as ma

# ===========================================================================
# [PARAMETERS]  ← edit here
# ===========================================================================
TARGET_DB      = 'gis'
MIN_POPULATION = 5_000    # based on 2020 population
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))

# Prefecture code → 8-region  (Statistics Bureau of Japan standard)
# Derived from JIS X 0401 (first 2 digits of city_code).
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

# Identical colour scheme to 01-01
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

# Static PNG: three azimuth angles (elevation fixed at 25°)
STATIC_VIEWS = [
    ('View 1  (azim=  0°)',  25,   0),
    ('View 2  (azim=120°)', 25, 120),
    ('View 3  (azim=240°)', 25, 240),
]

# Plotly camera geometry for Z-axis rotation
CAM_R        = 2.0
CAM_ELEV_DEG = 25   # default elevation for initial view and auto-rotate frames
AZIM_STEP    = 5    # degrees per azimuth slider step
ELEV_STEP    = 5    # degrees per elevation slider step

# ===========================================================================
# [MAIN QUERY]  — 2015→2020 change in composition shares
# ===========================================================================
SQL = """
WITH y15 AS (
    SELECT
        city_code,
        lt_15,
        mid_15_64,
        gt_65
    FROM e_stat.census_population
    WHERE survey_year = 2015
      AND admin_type <> '1'     -- exclude 政令指定都市 city-level & 東京都区部 aggregates
      AND lt_15     >= 50        -- minimum count to avoid noise from tiny base
      AND mid_15_64 >= 500
      AND gt_65     >= 50
),
y20 AS (
    SELECT
        city_code,
        city_name_en,
        population,
        lt_15,
        mid_15_64,
        gt_65
    FROM e_stat.census_population
    WHERE survey_year    = 2020
      AND admin_type <> '1'     -- exclude 政令指定都市 city-level & 東京都区部 aggregates
      AND population    >= %(min_pop)s
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

# Clip extreme outliers (e.g. tiny 2015 base that slipped through) at ±200 %
CLIP_PCT = 200.0
pct_cols = ['d_lt_15_pct', 'd_mid_15_64_pct', 'd_gt_65_pct']
before = (df[pct_cols].abs() > CLIP_PCT).any(axis=1).sum()
df[pct_cols] = df[pct_cols].clip(lower=-CLIP_PCT, upper=CLIP_PCT)
print(f'Clipped {before} rows with |growth| > {CLIP_PCT}%')

# Sanity check: print range of each growth rate
for col in pct_cols:
    print(f'{col:20s}  min={df[col].min():+.1f}%  max={df[col].max():+.1f}%  '
          f'mean={df[col].mean():+.1f}%')

# ── Region assignment via prefecture code ──────────────────────────────────
df['pref_code'] = df['city_code'].str[:2].astype(int)
df['region'] = (
    df['pref_code']
    .map(PREF_CODE_TO_REGION)
    .map(REGION_MAP)
    .fillna('Other')
)
print(df['region'].value_counts().to_string())

# ── Bubble sizes ───────────────────────────────────────────────────────────
max_pop = df['population'].max()
_sqrt_ratio  = np.sqrt(df['population']) / np.sqrt(max_pop)
df['bsz_mpl']    = (_sqrt_ratio * 250).clip(lower=6)
df['bsz_plotly'] = (_sqrt_ratio * 18).clip(lower=2)

# ── Axis range for symmetric display ──────────────────────────────────────
_abs_max = max(
    df[['d_lt_15_pct', 'd_mid_15_64_pct', 'd_gt_65_pct']].abs().max().max(),
    1.0,
)
AX_LIM = np.ceil(_abs_max * 1.1)   # rounded up with 10 % margin

# ===========================================================================
# Figure 1 — Static 3-panel PNG  (3 angles around Z axis)
# ===========================================================================
fig = plt.figure(figsize=(21, 8))
fig.patch.set_facecolor('white')

for panel_i, (view_lbl, elev, azim) in enumerate(STATIC_VIEWS, 1):
    ax = fig.add_subplot(1, 3, panel_i, projection='3d')
    ax.set_facecolor('#f5f5f5')

    for region, color in REGION_COLORS.items():
        mask = df['region'] == region
        if not mask.any():
            continue
        ax.scatter(
            df.loc[mask, 'd_lt_15_pct'],
            df.loc[mask, 'd_mid_15_64_pct'],
            df.loc[mask, 'd_gt_65_pct'],
            s=df.loc[mask, 'bsz_mpl'],
            c=color,
            alpha=0.40,
            edgecolors='white',
            linewidths=0.2,
            depthshade=True,
        )

    # Reference lines through origin — darker solid lines + arrowhead on positive end
    _ref_style  = dict(color='#444444', linewidth=1.5, linestyle='-', zorder=2)
    _arrow_len  = AX_LIM * 0.12   # quiver arrow shaft length (tip cap only)
    _arrow_col  = '#444444'
    # Negative-to-positive lines (stop just short of tip so quiver cap looks clean)
    ax.plot([-AX_LIM, AX_LIM - _arrow_len], [0, 0], [0, 0], **_ref_style)
    ax.plot([0, 0], [-AX_LIM, AX_LIM - _arrow_len], [0, 0], **_ref_style)
    ax.plot([0, 0], [0, 0], [-AX_LIM, AX_LIM - _arrow_len], **_ref_style)
    # Arrowheads at positive ends
    _q = dict(color=_arrow_col, arrow_length_ratio=1.0, linewidth=1.5, zorder=3)
    ax.quiver(AX_LIM - _arrow_len, 0, 0, _arrow_len, 0, 0, **_q)
    ax.quiver(0, AX_LIM - _arrow_len, 0, 0, _arrow_len, 0, **_q)
    ax.quiver(0, 0, AX_LIM - _arrow_len, 0, 0, _arrow_len, **_q)

    ax.set_xlabel('Under 15 growth (% vs 2015)', fontsize=8, labelpad=6)
    ax.set_ylabel('Ages 15–64 growth (% vs 2015)', fontsize=8, labelpad=6)
    ax.set_zlabel('Ages 65+ growth (% vs 2015)', fontsize=8, labelpad=6)
    ax.set_xlim(-AX_LIM, AX_LIM)
    ax.set_ylim(-AX_LIM, AX_LIM)
    ax.set_zlim(-AX_LIM, AX_LIM)
    ax.tick_params(labelsize=7)
    ax.set_title(view_lbl, fontsize=10, pad=6)
    ax.view_init(elev=elev, azim=azim)

# Region colour legend — right of the third panel
region_patches = [
    mpatches.Patch(facecolor=c, alpha=0.75, label=r)
    for r, c in REGION_COLORS.items()
]
ax.legend(
    handles=region_patches,
    title='Region', fontsize=7.5, title_fontsize=8.5,
    loc='upper left', bbox_to_anchor=(1.15, 1.0),
    framealpha=0.9,
)

fig.text(
    0.99, 0.01,
    'Axes = (count_2020 − count_2015) / count_2015 × 100  (% growth vs 2015)  |  '
    'Bubble ∝ √pop (2020)  |  '
    f'Source: e-Stat 2015 & 2020 Population Census  |  n = {len(df):,}',
    ha='right', va='bottom', fontsize=7.5, color='#888888',
)

fig.suptitle(
    '3-D Age-Group Population Growth Rate  (2015→2020)  —  All Japanese Municipalities',
    fontsize=13, fontweight='bold', y=1.01,
)

plt.tight_layout()
out_static = os.path.join(SCRIPT_DIR, '01-05_3d_age_static.png')
fig.savefig(out_static, dpi=150, bbox_inches='tight', facecolor='white')
print(f'Saved → {out_static}')
plt.close()

# ===========================================================================
# Figure 2 — Plotly interactive HTML  (drag + azimuth slider + auto-rotate)
# ===========================================================================
try:
    import plotly.graph_objects as go
except ImportError:
    print('\n[WARN] plotly not installed — skipping HTML output.\n'
          '       Run:  pip install plotly\n')
    sys.exit(0)

# ── Build one Scatter3d trace per region ──────────────────────────────────
traces = []
for region, color in REGION_COLORS.items():
    mask = df['region'] == region
    if not mask.any():
        continue
    sub = df[mask]
    traces.append(go.Scatter3d(
        x=sub['d_lt_15_pct'],
        y=sub['d_mid_15_64_pct'],
        z=sub['d_gt_65_pct'],
        mode='markers',
        name=region,
        marker=dict(
            size=sub['bsz_plotly'],
            color=color,
            opacity=0.55,
            line=dict(color='white', width=0.3),
        ),
        text=sub['city_name_en'],
        hovertemplate=(
            '<b>%{text}</b><br>'
            'Under 15 growth: %{x:+.1f}%<br>'
            'Ages 15–64 growth: %{y:+.1f}%<br>'
            'Ages 65+ growth: %{z:+.1f}%'
            '<extra></extra>'
        ),
    ))

# Reference lines through origin — X/Y/Z axes as solid dark lines
_cone_size = AX_LIM * 0.10   # cone height proportional to axis range
for vec in ([1, 0, 0], [0, 1, 0], [0, 0, 1]):
    # Line from negative to positive end (stop slightly short so cone doesn't overlap)
    traces.append(go.Scatter3d(
        x=[-AX_LIM * vec[0], (AX_LIM - _cone_size) * vec[0]],
        y=[-AX_LIM * vec[1], (AX_LIM - _cone_size) * vec[1]],
        z=[-AX_LIM * vec[2], (AX_LIM - _cone_size) * vec[2]],
        mode='lines',
        line=dict(color='#444444', width=3),
        showlegend=False,
        hoverinfo='skip',
    ))
    # Arrowhead cone at the positive tip
    traces.append(go.Cone(
        x=[AX_LIM * vec[0]],
        y=[AX_LIM * vec[1]],
        z=[AX_LIM * vec[2]],
        u=[vec[0]], v=[vec[1]], w=[vec[2]],
        colorscale=[[0, '#444444'], [1, '#444444']],
        showscale=False,
        sizemode='absolute',
        sizeref=_cone_size,
        anchor='tip',
        showlegend=False,
        hoverinfo='skip',
    ))

# ── Camera helper (spherical coordinates) ─────────────────────────────────
def cam_eye(azim_deg: float, elev_deg: float = CAM_ELEV_DEG) -> dict:
    """Return plotly camera eye dict from azimuth and elevation (degrees)."""
    theta = np.radians(azim_deg)
    phi   = np.radians(elev_deg)
    r     = CAM_R * np.cos(phi)   # horizontal distance
    z     = CAM_R * np.sin(phi)   # vertical height
    return dict(x=r * np.cos(theta), y=r * np.sin(theta), z=z)

azimuths = list(range(0, 360, AZIM_STEP))

# Frames drive auto-rotate at fixed elevation
frames = [
    go.Frame(
        layout=go.Layout(scene_camera=dict(eye=cam_eye(a, CAM_ELEV_DEG))),
        name=str(a),
    )
    for a in azimuths
]

layout = go.Layout(
    title=dict(
        text=(
            '3-D Age-Group Population Growth Rate (2015→2020)  —  '
            f'Japanese Municipalities  (n = {len(df):,})<br>'
            '<sup>'
            'X = Under-15 growth (%)  |  '
            'Y = Ages 15–64 growth (%)  |  '
            'Z = Ages 65+ growth (%)  |  '
            'Formula: (count₂₀₂₀ − count₂₀₁₅) / count₂₀₁₅ × 100  |  '
            'Bubble ∝ √pop (2020)'
            '</sup>'
        ),
        x=0.5,
        font=dict(size=13),
    ),
    scene=dict(
        xaxis=dict(title='Under 15 growth (% vs 2015)', range=[-AX_LIM, AX_LIM]),
        yaxis=dict(title='Ages 15–64 growth (% vs 2015)', range=[-AX_LIM, AX_LIM]),
        zaxis=dict(title='Ages 65+ growth (% vs 2015)', range=[-AX_LIM, AX_LIM]),
        camera=dict(eye=cam_eye(0, CAM_ELEV_DEG)),
        aspectmode='cube',
    ),
    legend=dict(title=dict(text='Region'), x=0.01, y=0.95),
    updatemenus=[dict(
        type='buttons',
        showactive=False,
        y=0.02, x=0.5, xanchor='center', yanchor='bottom',
        buttons=[
            dict(
                label='▶  Auto-rotate',
                method='animate',
                args=[None, dict(
                    frame=dict(duration=80, redraw=True),
                    fromcurrent=True,
                    mode='immediate',
                )],
            ),
            dict(
                label='⏸  Pause',
                method='animate',
                args=[[None], dict(
                    frame=dict(duration=0, redraw=False),
                    mode='immediate',
                )],
            ),
        ],
    )],
    height=720,
    paper_bgcolor='white',
)

fig_plotly = go.Figure(data=traces, frames=frames, layout=layout)

out_html = os.path.join(SCRIPT_DIR, '01-05_3d_age_interactive.html')
fig_plotly.write_html(out_html, include_plotlyjs='cdn')

# ── Inject custom JS sliders for azimuth + elevation ──────────────────────
_slider_html = f"""
<div id="cam-sliders" style="
    text-align:center; font-family:sans-serif; font-size:12px;
    padding:6px 0 10px; background:#fff; border-top:1px solid #e8e8e8">
  <label>Azimuth:</label>
  <input type="range" id="azim-sl"
         min="0" max="355" step="{AZIM_STEP}" value="0"
         style="width:32%; vertical-align:middle; margin:0 4px">
  <span id="azim-lbl" style="display:inline-block; width:32px; text-align:left">0°</span>
  &nbsp;&nbsp;
  <label>Elevation:</label>
  <input type="range" id="elev-sl"
         min="-10" max="80" step="{ELEV_STEP}" value="{CAM_ELEV_DEG}"
         style="width:22%; vertical-align:middle; margin:0 4px">
  <span id="elev-lbl" style="display:inline-block; width:32px; text-align:left">{CAM_ELEV_DEG}°</span>
</div>
<script>
(function () {{
  var CAM_R = {CAM_R};
  var azim  = 0;
  var elev  = {CAM_ELEV_DEG};

  function camEye(a, e) {{
    var th = a * Math.PI / 180;
    var ph = e * Math.PI / 180;
    var r  = CAM_R * Math.cos(ph);
    return {{ x: r * Math.cos(th), y: r * Math.sin(th), z: CAM_R * Math.sin(ph) }};
  }}

  function relay() {{
    var gd = document.querySelector('.js-plotly-plot');
    if (gd) Plotly.relayout(gd, {{ 'scene.camera.eye': camEye(azim, elev) }});
  }}

  document.getElementById('azim-sl').addEventListener('input', function () {{
    azim = +this.value;
    document.getElementById('azim-lbl').textContent = azim + '°';
    relay();
  }});

  document.getElementById('elev-sl').addEventListener('input', function () {{
    elev = +this.value;
    document.getElementById('elev-lbl').textContent = elev + '°';
    relay();
  }});
}})();
</script>
"""

with open(out_html, 'r', encoding='utf-8') as _f:
    _html = _f.read()
_html = _html.replace('</body>', _slider_html + '</body>', 1)
with open(out_html, 'w', encoding='utf-8') as _f:
    _f.write(_html)

print(f'Saved → {out_html}')

# ===========================================================================
# [NOTES]
# ===========================================================================
# Outlier handling
# -----------------
# The y15 CTE requires minimum counts (lt_15>=50, mid_15_64>=500, gt_65>=50)
# to prevent division-by-tiny-base producing growth rates in the thousands of %.
# Growth rates are further clipped to ±200 % in Python after loading.
# Municipalities excluded by either filter are omitted from the plot.
#
# Normalisation rationale
# -----------------------
# Dividing by the 2015 base count eliminates the city-size effect:
# a mountain village losing 50 children out of 100 (-50 %) and a major
# city losing 50,000 out of 100,000 (-50 %) plot at the same point.
# This makes the 3-D space meaningful for comparing municipalities of
# vastly different scales — unlike raw absolute-count deltas.
#
# Expected cluster geometry
# -------------------------
#   (+X large, +Y, +Z modest) → youth in-migration led growth (Urban Core)
#   (all axes small positive)  → demographic stability (Urban Residential)
#   (−X or ≈0, ≈0 Y, +Z)     → standard suburban aging
#   (−X, −Y large, +Z)        → working-age exodus + aging (Rural)
#
# Offline HTML
# ------------
# For use without internet:  fig_plotly.write_html(out_html, include_plotlyjs=True)
# (produces ~3-4 MB file vs ~50 kB with CDN).

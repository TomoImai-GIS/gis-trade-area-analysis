"""
01-04_cluster_municipalities_by_density_aging.py
=================================================
Cluster ~1,900 Japanese municipalities into 6 urban-type groups using
2020 Census population density and elderly rate.

  Primary method  : GMM  (Gaussian Mixture Model, full covariance)
                    Both axes StandardScaler-normalised before fitting;
                    means & covariances back-transformed to original space
                    for visualisation.
  Comparison      : K-means  (features normalised with StandardScaler)
  Model selection : BIC curve for k = 2 .. 9

Cluster labels (ordered by population density, high → low):
  Ultra Urban       – ultra-high density / very low elderly  (power-couple tower condos)
  Urban Core        – high density / low elderly rate
  Urban Residential – moderate-high density / moderate elderly rate
  Inner Suburban    – moderate density / moderate elderly rate
  Outer Suburban    – low-moderate density / higher elderly rate
  Rural             – low density / highest elderly rate

Outputs (saved to the same folder as this script):
  01-04_cluster_municipalities_by_density_aging.png   3-panel figure
  01-04_cluster_assignments.csv                       cluster label per city

Execution   : PyCharm or any standard Python environment (not QGIS)
Requirements: pandas, numpy, matplotlib, scikit-learn, psycopg2,
              AccessKeys/my_access.py
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Ellipse
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
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
MIN_POPULATION = 5_000      # exclude municipalities below this threshold
N_CLUSTERS     = 6          # number of clusters (k)
BIC_K_RANGE    = range(2, 10)  # k values evaluated for BIC  (2 .. 9)
RANDOM_STATE   = 42

# Cluster labels ordered by density rank (highest density = index 0)
CLUSTER_LABELS = [
    'Ultra Urban',
    'Urban Core',
    'Urban Residential',
    'Inner Suburban',
    'Outer Suburban',
    'Rural',
]
CLUSTER_COLORS = {
    'Ultra Urban':        '#6c3483',   # purple
    'Urban Core':         '#c0392b',   # deep red
    'Urban Residential':  '#e67e22',   # orange
    'Inner Suburban':     '#16a085',   # teal
    'Outer Suburban':     '#2980b9',   # blue
    'Rural':              '#27ae60',   # green
}

# Scatter dot styling
DOT_SIZE  = 12
DOT_ALPHA = 0.35

# GMM ellipse: draw n_std-sigma contour on GMM panel
N_STD_ELLIPSE = 2.0

# Output: same folder as this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PNG    = os.path.join(SCRIPT_DIR,
                          '01-04_cluster_municipalities_by_density_aging.png')
OUT_CSV    = os.path.join(SCRIPT_DIR,
                          '01-04_cluster_assignments.csv')

# ---------------------------------------------------------------------------
# 1. Load data from PostgreSQL
# ---------------------------------------------------------------------------
SQL = """
SELECT
    cp.city_code,
    cp.city_name_en,
    m.pref_name,
    p.region,
    cp.population,
    ROUND(cp.density::numeric, 1)                                 AS pop_density,
    ROUND(cp.gt_65::numeric / NULLIF(cp.population, 0) * 100, 1) AS elderly_rate
FROM  e_stat.census_population   cp
JOIN  admin_jp.municipalities_v2 m  USING (city_code)
JOIN  admin_jp.prefectures       p  USING (pref_code)
WHERE cp.survey_year = 2020
  AND cp.population  >= %(min_pop)s
  AND cp.density      > 0
ORDER BY cp.city_code
"""

conn = psycopg2.connect(
    f'user={ma.pg_user()} dbname={TARGET_DB} password={ma.pg_pass()}'
)
df = pd.read_sql(SQL, conn, params={'min_pop': MIN_POPULATION})
conn.close()

df = df.dropna(subset=['pop_density', 'elderly_rate'])
df['log_density'] = np.log10(df['pop_density'])

print(f"Loaded {len(df):,} municipalities  (population >= {MIN_POPULATION:,})")

# ---------------------------------------------------------------------------
# 2. Feature matrix  X = [log10(density),  elderly_rate]
#    Normalise with StandardScaler (used for BOTH GMM and K-means)
# ---------------------------------------------------------------------------
X = df[['log_density', 'elderly_rate']].values   # shape (N, 2)

scaler_gmm = StandardScaler()
X_gmm = scaler_gmm.fit_transform(X)   # normalised for GMM

scaler_km = StandardScaler()
X_km = scaler_km.fit_transform(X)     # normalised for K-means (same result, kept separate for clarity)

# ---------------------------------------------------------------------------
# 3. BIC analysis — GMM for k = 2 .. 9  (fitted on normalised X_gmm)
# ---------------------------------------------------------------------------
bic_scores = []
for k in BIC_K_RANGE:
    g = GaussianMixture(
        n_components=k, covariance_type='full',
        random_state=RANDOM_STATE, n_init=10
    )
    g.fit(X_gmm)
    bic_scores.append(g.bic(X_gmm))

best_k_bic = list(BIC_K_RANGE)[int(np.argmin(bic_scores))]
print(f"BIC minimum at k={best_k_bic}  (using k={N_CLUSTERS})")

# ---------------------------------------------------------------------------
# 4. GMM clustering  (primary)
#    Fitted on normalised space; means & covariances back-transformed
#    to original [log_density, elderly_rate] space for visualisation.
# ---------------------------------------------------------------------------
gmm = GaussianMixture(
    n_components=N_CLUSTERS, covariance_type='full',
    random_state=RANDOM_STATE, n_init=30
)
gmm.fit(X_gmm)
raw_gmm = gmm.predict(X_gmm)

# Back-transform: mean_orig = scaler.inverse_transform(mean_scaled)
#                 cov_orig  = diag(scale) @ cov_scaled @ diag(scale)
scale_mat = np.diag(scaler_gmm.scale_)
gmm_means_orig = scaler_gmm.inverse_transform(gmm.means_)   # (k, 2)
gmm_covs_orig  = [scale_mat @ cov @ scale_mat
                  for cov in gmm.covariances_]               # list of (2, 2)

# Assign interpretable labels: rank by mean log_density (desc → Ultra Urban first)
density_order  = np.argsort(gmm_means_orig[:, 0])[::-1]
gmm_label_map  = {int(old): CLUSTER_LABELS[rank]
                  for rank, old in enumerate(density_order)}
df['cluster_gmm'] = [gmm_label_map[c] for c in raw_gmm]

print("\nGMM cluster sizes:")
print(df['cluster_gmm'].value_counts().reindex(CLUSTER_LABELS))

# ---------------------------------------------------------------------------
# 5. K-means clustering  (comparison / StandardScaler normalised)
# ---------------------------------------------------------------------------
km = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=30)
km.fit(X_km)
raw_km = km.labels_

km_centers_orig = scaler_km.inverse_transform(km.cluster_centers_)
km_order        = np.argsort(km_centers_orig[:, 0])[::-1]
km_label_map    = {int(old): CLUSTER_LABELS[rank]
                   for rank, old in enumerate(km_order)}
df['cluster_km'] = [km_label_map[c] for c in raw_km]

print("\nK-means cluster sizes:")
print(df['cluster_km'].value_counts().reindex(CLUSTER_LABELS))

# ---------------------------------------------------------------------------
# 6. Save CSV
# ---------------------------------------------------------------------------
df[[
    'city_code', 'city_name_en', 'pref_name', 'region',
    'population', 'pop_density', 'elderly_rate',
    'log_density', 'cluster_gmm', 'cluster_km',
]].to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
print(f"\nSaved CSV → {OUT_CSV}")

# ---------------------------------------------------------------------------
# 7. Helper: draw GMM confidence ellipse  (in original space)
# ---------------------------------------------------------------------------
def draw_gmm_ellipse(ax, mean, cov, color, n_std=2.0):
    """Draw an n_std-sigma confidence ellipse for one GMM component.
    mean and cov must be in the same space as the scatter plot axes.
    """
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]

    angle  = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
    width  = 2 * n_std * np.sqrt(vals[0])
    height = 2 * n_std * np.sqrt(vals[1])

    ax.add_patch(Ellipse(
        xy=mean, width=width, height=height, angle=angle,
        facecolor=color, alpha=0.10, linewidth=0, zorder=2
    ))
    ax.add_patch(Ellipse(
        xy=mean, width=width, height=height, angle=angle,
        facecolor='none', edgecolor=color,
        linewidth=1.8, linestyle='--', zorder=3
    ))

# ---------------------------------------------------------------------------
# 8. Shared axis setup
# ---------------------------------------------------------------------------
X_LIM         = (-0.2, 4.8)
Y_LIM         = (0, 58)
X_TICKS       = [0, 1, 2, 3, 4]
X_TICK_LABELS = ['1', '10', '100', '1k', '10k']

def style_scatter_ax(ax, title):
    ax.set_xlim(*X_LIM)
    ax.set_ylim(*Y_LIM)
    ax.set_xticks(X_TICKS)
    ax.set_xticklabels(X_TICK_LABELS)
    ax.set_xlabel('Population Density (persons/km²)', fontsize=11)
    ax.set_ylabel('Elderly Rate (%)', fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    ax.grid(True, which='major', color='#dddddd', linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

# ---------------------------------------------------------------------------
# 9. Figure  (3 panels)
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(20, 6))
fig.patch.set_facecolor('white')

legend_handles = [
    mpatches.Patch(color=CLUSTER_COLORS[l], label=l)
    for l in CLUSTER_LABELS
]

# ── Panel 1: K-means ──────────────────────────────────────────────────────
ax1 = axes[0]
style_scatter_ax(ax1, f'K-means  (k={N_CLUSTERS}, StandardScaler)')

for label in CLUSTER_LABELS:
    sub = df[df['cluster_km'] == label]
    ax1.scatter(
        sub['log_density'], sub['elderly_rate'],
        c=CLUSTER_COLORS[label], s=DOT_SIZE, alpha=DOT_ALPHA,
        linewidths=0, zorder=3
    )

for raw_idx in range(N_CLUSTERS):
    label = km_label_map[raw_idx]
    cx, cy = km_centers_orig[raw_idx]
    ax1.scatter(cx, cy,
                c=CLUSTER_COLORS[label], s=130,
                marker='D', edgecolors='white', linewidths=1.2, zorder=5)

ax1.legend(handles=legend_handles, fontsize=8.5,
           loc='upper right', framealpha=0.85)

# ── Panel 2: GMM ──────────────────────────────────────────────────────────
ax2 = axes[1]
style_scatter_ax(
    ax2,
    f'GMM  (k={N_CLUSTERS}, full covariance, StandardScaler, {N_STD_ELLIPSE:.0f}σ)'
)

for label in CLUSTER_LABELS:
    sub = df[df['cluster_gmm'] == label]
    ax2.scatter(
        sub['log_density'], sub['elderly_rate'],
        c=CLUSTER_COLORS[label], s=DOT_SIZE, alpha=DOT_ALPHA,
        linewidths=0, zorder=3
    )

for raw_idx in range(N_CLUSTERS):
    label = gmm_label_map[raw_idx]
    mean  = gmm_means_orig[raw_idx]
    cov   = gmm_covs_orig[raw_idx]
    draw_gmm_ellipse(ax2, mean, cov, CLUSTER_COLORS[label], n_std=N_STD_ELLIPSE)
    ax2.scatter(*mean,
                c=CLUSTER_COLORS[label], s=130,
                marker='D', edgecolors='white', linewidths=1.2, zorder=5)

ax2.legend(handles=legend_handles, fontsize=8.5,
           loc='upper right', framealpha=0.85)

# ── Panel 3: BIC curve ────────────────────────────────────────────────────
ax3 = axes[2]
ks = list(BIC_K_RANGE)

delta_bic = [b - min(bic_scores) for b in bic_scores]

ax3.plot(ks, delta_bic, 'o-', color='#555555', linewidth=2, markersize=7,
         zorder=3)

chosen_delta = delta_bic[ks.index(N_CLUSTERS)]
ax3.scatter([N_CLUSTERS], [chosen_delta],
            color='#c0392b', s=120, zorder=4,
            label=f'k={N_CLUSTERS} (chosen)')

if best_k_bic != N_CLUSTERS:
    ax3.scatter([best_k_bic], [0],
                color='#2980b9', s=120, marker='*', zorder=4,
                label=f'k={best_k_bic} (BIC min)')

ax3.axvline(N_CLUSTERS, color='#c0392b', linestyle='--',
            linewidth=1.5, alpha=0.6, zorder=2)

ax3.set_xlabel('Number of Clusters (k)', fontsize=11)
ax3.set_ylabel('ΔBIC  (relative to minimum)', fontsize=11)
ax3.set_title('GMM Model Selection — BIC', fontsize=12,
              fontweight='bold', pad=10)
ax3.set_xticks(ks)
ax3.legend(fontsize=9, framealpha=0.85)
ax3.grid(True, color='#dddddd', linewidth=0.8)
ax3.set_axisbelow(True)
ax3.set_ylim(bottom=-max(delta_bic) * 0.05)

# ── Overall title & source note ───────────────────────────────────────────
fig.suptitle(
    'Municipal Clustering by Population Density × Elderly Rate  (2020 Census, Japan)',
    fontsize=13, fontweight='bold', y=0.99
)
fig.text(
    0.5, -0.03,
    (f'Source: e-Stat 2020 Population Census  |  '
     f'municipalities with population ≥ {MIN_POPULATION:,}  (n={len(df):,})  |  '
     f'GMM & K-means: StandardScaler normalised, n_init=30, random_state={RANDOM_STATE}'),
    ha='center', fontsize=8.5, color='#888888'
)

plt.tight_layout(rect=[0, 0.02, 1, 0.96])
fig.savefig(OUT_PNG, dpi=150, bbox_inches='tight', facecolor='white')
print(f"Saved PNG → {OUT_PNG}")
plt.close()

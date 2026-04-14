# Nationwide Aging Dynamics: 3-D Age-Group Growth Rate Analysis (2015–2020)
**All Japanese Municipalities — Three-Dimensional Scatter by Age-Cohort Change**

---

## 1. Key Findings

| # | Observation | Analytical View | Implication |
|---|---|---|---|
| 1 | Under-15 and Ages 15–64 growth rates show strong positive correlation | Looking down Z+ axis (top view) | Children overwhelmingly co-reside with working-age parents; the two cohorts move together as a household unit |
| 2 | Ages 65+ growth is largely independent of the other two cohorts, and is positive for nearly all municipalities | Looking from +X / +Y diagonal (side view) | The elderly are structurally "last to leave": depopulation follows a sequential pattern — working-age → children → elderly |

---

## 2. Background

Japan's demographic transition is well-documented at the national level,
but the spatial heterogeneity *across* municipalities — and the *relative* dynamics
*between* age cohorts — remain underexplored.

Prior analyses (scripts `01-01` to `01-03`) examined population density,
elderly rate, and age-composition shifts for selected representative cities.
This analysis scales that lens to **all ~1,700 municipalities nationwide**,
plotting the 2015 → 2020 growth rate of each age group simultaneously in three dimensions.

The key shift from earlier work is normalisation:
instead of reporting absolute population or composition shares,
each axis records the **percentage change within each cohort**
((count₂₀₂₀ − count₂₀₁₅) / count₂₀₁₅ × 100).
This removes the size advantage of large cities and allows direct comparison
of demographic *velocity* across municipalities of all scales.

---

## 3. Data & Methodology

| Item | Detail |
|---|---|
| Data source | e-Stat 2015 & 2020 Population Census (`e_stat.census_population`) |
| Coverage | All municipalities with population ≥ 5,000 in 2020 (≈ 1,700 cities, towns, and villages) |
| Exclusions | Aggregate parent records excluded: 政令指定都市 city-level totals and 東京都区部 (identified via `admin_type = '1'`) — only ward/municipality-level records retained to avoid double-counting |
| X axis | Under-15 population growth rate 2015 → 2020 (%) |
| Y axis | Ages 15–64 population growth rate 2015 → 2020 (%) |
| Z axis | Ages 65+ population growth rate 2015 → 2020 (%) |
| Bubble size | Proportional to √population (2020); plotted with region colour |
| Region colour | 8-region scheme matching `01-01`: Hokkaido / Tohoku / Kanto / Chubu / Kinki / Chugoku / Shikoku / Kyushu·Okinawa |
| Outlier cap | Growth rates clipped at ±200% to suppress noise from municipalities with very small 2015 base counts |

**Scripts & Outputs:**

| File | Description |
|---|---|
| [`python/01_data_analytics/01-05_3d_age_composition_scatter.py`](../../python/01_data_analytics/01-05_3d_age_composition_scatter.py) | Main analysis script |
| [`output/python/01-05_3d_age_static.png`](../../output/python/01-05_3d_age_static.png) | Static 3-panel PNG (azimuth 0° / 120° / 240°, elevation 25°) |
| [`output/python/01-05_3d_age_interactive.html`](https://tomoimai-gis.github.io/gis-trade-area-analysis/output/python/01-05_3d_age_interactive.html) | Interactive HTML: azimuth & elevation sliders + auto-rotate button |

---

## 4. Visualisation

![3-D Age-Group Growth Rate — All Municipalities](../../output/python/01-05_3d_age_static.png)

*Three fixed viewpoints at azimuth 0° / 120° / 240° (elevation 25°).
Each bubble is one municipality; size ∝ √population; colour = region.
Axes show 2015 → 2020 growth rate within each age cohort.
Dark reference lines mark the X / Y / Z axes through the origin; positive ends marked with arrowheads.*

The [interactive HTML companion](https://tomoimai-gis.github.io/gis-trade-area-analysis/output/python/01-05_3d_age_interactive.html) allows free rotation via azimuth and elevation sliders,
enabling the viewpoint-dependent findings described below to be reproduced and explored.

---

## 5. Finding 1 — Under-15 and Ages 15–64 Growth Are Strongly Correlated

**Viewpoint:** Looking straight down the Z+ axis (elevation ≈ 80°, any azimuth).

![Finding 1 — Top-down view: Under-15 vs Ages 15–64 growth correlation](../../output/python/01-05_3d_age_composition_scatter_angle1.png)

*Top-down view along the Z+ axis. The point cloud elongates diagonally from lower-left to upper-right, revealing a strong positive correlation between Under-15 and Ages 15–64 growth rates.*

From this bird's-eye perspective, the cloud of municipalities collapses onto
the X–Y plane (Under-15 vs. Ages 15–64 growth).
The distribution is elongated along the positive diagonal,
indicating a **strong positive linear relationship** between the two cohorts:
municipalities where the working-age population grew also tend to see
Under-15 growth, and municipalities shedding working-age residents
tend to lose children at a similar rate.

### Mechanism

The most direct explanation is household co-residence:
in Japan, children under 15 overwhelmingly live with at least one parent.
Migration decisions — to move into or out of a municipality —
are made at the household level and simultaneously affect
both the working-age and child cohort counts.

Consequently, **the Under-15 cohort functions largely as a lagged echo
of working-age in-migration**, rather than an independent demographic variable.
This has direct implications for forecasting:
projecting future child population from working-age migration trends
(or vice versa) is methodologically sound at the municipality level.

### Practical significance

- **School infrastructure:** municipalities forecasting working-age growth
  can anticipate corresponding primary-school demand without separate modelling.
- **Housing type:** markets where working-age in-migration is strong
  will see demand for family-sized units, not just single-person or couple units.
- **Policy:** incentives targeting young families (childcare, housing subsidies)
  are likely to move both cohorts together; separating "children" from
  "working-age" in policy targeting overstates the independence of the two levers.

---

## 6. Finding 2 — Ages 65+ Growth Is Largely Independent and Mostly Positive

**Viewpoint:** Looking from the diagonal between the X+ and Y+ axes
(azimuth ≈ 45°, elevation ≈ 0–15°).

![Finding 2 — Side view: Ages 65+ growth independence and positive bias](../../output/python/01-05_3d_age_composition_scatter_angle2.png)

*Side view from the X+/Y+ diagonal. The point cloud forms a near-horizontal disk sitting above Z = 0, showing that Ages 65+ growth is largely independent of the other two cohorts and positive across nearly all municipalities.*

From this angle, the Z axis (Ages 65+ growth) is directly visible
against the combined X–Y movement.
Two features stand out:

1. **The cloud shows little systematic relationship between Z and the X–Y plane.**
   Municipalities where working-age and child populations grew substantially
   span a wide range of 65+ growth rates, and vice versa.

2. **Nearly all municipalities lie above Z = 0.**
   The cloud sits almost entirely in the upper half of the plot —
   the 65+ cohort grew in absolute numbers in the vast majority of municipalities
   between 2015 and 2020.

3. **A critical asymmetry:** no municipality shows 65+ growth negative
   while Under-15 / Ages 15–64 growth is positive.
   The reverse — 65+ positive while other cohorts decline — is common.

### Mechanism

This pattern is consistent with a **sequential depopulation model**:

| Stage | Working-age | Under-15 | Ages 65+ |
|---|---|---|---|
| Early out-migration | Declining | Declining (lag) | Still growing |
| Accelerating decline | Strongly negative | Negative | Near zero / slightly positive |
| Advanced depopulation | Strongly negative | Strongly negative | Negative |

The elderly population is structurally "last to leave" for two reasons:

- **Low mobility:** older residents have stronger ties to place (property, community,
  medical care networks) and face higher costs and risks of relocation.
- **In-situ aging:** even without new elderly in-migrants,
  the existing working-age cohort ages into the 65+ bracket over time,
  mechanically adding to the elderly count even as total population falls.

The asymmetry (no municipality with 65+ negative AND others positive) is striking:
it implies that **if the elderly cohort is shrinking, the rest of the population
is already in severe decline** — this combination represents
an advanced stage of demographic contraction that only the most depopulated rural
municipalities have reached.

### Practical significance

- **Elder-care demand forecasting:** a municipality does not need to grow overall
  to face rising 65+ absolute numbers and associated service demands.
  Even municipalities in mild overall decline will continue adding elderly residents
  for a decade or more.
- **Fiscal asymmetry:** tax-generating working-age population and
  service-consuming elderly population can move in opposite directions simultaneously —
  the most fiscally challenging scenario, and apparently the modal outcome
  for Japan's smaller municipalities.
- **Site selection for elder-care facilities:** the near-universal 65+ growth
  means the addressable market is nationwide, but bubble size (population)
  and growth *rate* together identify where demand is accelerating fastest.

---

## 7. Octant Analysis — Quantifying the Directional Pattern

The 3-D scatter provides a qualitative picture; the octant analysis converts it into hard counts.
Each municipality is classified by the **sign** of its three growth rates —
positive (+) or negative (−) — yielding eight possible combinations
(octants of the three-dimensional growth-rate space).

**Script & Output:**

| File | Description |
|---|---|
| [`python/01_data_analytics/01-06_age_growth_correlation.py`](../../python/01_data_analytics/01-06_age_growth_correlation.py) | Octant analysis script |
| [`output/python/01-06_octant_analysis.png`](../../output/python/01-06_octant_analysis.png) | Bar chart — municipality counts by octant |

![Octant Analysis — Municipality Count by Age-Group Growth Direction](../../output/python/01-06_octant_analysis.png)

*Each bar represents one of the eight possible (+/−) sign combinations of
Under-15, Ages 15–64, and Ages 65+ growth rates.
n = 1,603 municipalities; 2020 population ≥ 5,000.*

### Results

| Pattern (Under-15, 15–64, 65+) | Count | Share | Interpretation |
|---|---|---|---|
| **(−, −, +)** | **1,107** | **69.1 %** | Sequential depopulation — working-age and children declining, 65+ still growing |
| (−, +, +) | 165 | 10.3 % | 15–64 growing despite Under-15 decline — labour in-migration without family formation |
| (−, −, −) | 143 | 8.9 % | Advanced depopulation — all three cohorts declining |
| (+, +, +) | 136 | 8.5 % | All cohorts growing — urban cores and fast-growing suburbs |
| (+, −, +) | 51 | 3.2 % | Unusual mix; small counts |
| Other | 2 | < 0.1 % | Rare edge cases |

### Key Observations

**1. (−, −, +) is the modal outcome for Japan — 69.1 % of municipalities.**  
This directly quantifies Finding 2 with a plain count rather than a correlation coefficient.
The dominant trajectory nationwide is simultaneous loss of working-age residents and children
while the 65+ cohort still grows in absolute numbers.
It is not a regional exception — it describes the structural baseline for the country.

**2. The 65+ asymmetry is exact: (+, +, −) and (−, +, −) are empty (0 municipalities).**  
No municipality has a declining 65+ cohort while either of the other cohorts is positive.
The asymmetry identified visually in §6 is confirmed precisely:
the elderly cohort never turns negative first.

**3. Advanced depopulation (−, −, −) affects 8.9 % of municipalities.**  
These 143 municipalities have crossed the threshold where even the 65+ cohort shrinks —
the late stage of the sequential depopulation model described in §6.

**4. (−, +, +) at 10.3 % is the one notable deviation from strict cohort co-movement.**  
Working-age population grows while Under-15 declines.
A plausible mechanism: labour in-migration (single workers, couples without children) into
logistics hubs, industrial zones, or elder-care employers — without the family formation
that would generate Under-15 growth.
This sub-group departs from the household co-residence assumption underlying Finding 1
and merits further investigation.

---

## 8. Implications

### Cohort co-movement simplifies demographic modelling

Because Under-15 and Ages 15–64 move together,
a single indicator — net working-age migration — can serve as a sufficient
leading signal for family-oriented demand (schools, family housing, childcare).
This simplifies scenario modelling for municipalities and site-selection analyses.

### Elder-care demand is structurally decoupled from overall growth

The 65+ cohort's near-universal growth, independent of whether the municipality
is gaining or losing residents overall, has a direct bearing on
infrastructure investment strategy:
elder-care capacity must be planned even in municipalities experiencing
moderate population decline — the growth trajectory for that specific cohort
will not reverse until the municipality reaches an advanced depopulation stage.

### The sequential depopulation model as a diagnostic tool

The three-zone structure (working-age first, then children, then elderly)
provides a staging framework for policy intervention:

| Stage | Diagnostic signal | Policy window |
|---|---|---|
| Early | Working-age outflow; 65+ still growing fast | Largest — structural interventions still possible |
| Mid | Both working-age and child cohorts negative; 65+ slowing | Narrowing — focus shifts to service consolidation |
| Late | All three cohorts negative | Severely constrained — structural reversal extremely unlikely; managed decline planning becomes the realistic goal |

In practice, many Late-stage municipalities may not yet have transitioned to
managed-decline planning, creating a gap between the urgency of the situation
and the policy response actually in place.

Overlaying this staging with fiscal capacity data
(municipal tax revenue, social welfare expenditure)
would quantify the point at which each municipality crosses into structural fiscal stress.

---

## 9. Next Steps

The 3-D scatter and octant analysis establish the structural pattern;
the logical next steps move toward spatial and typological deepening:

### 9.1 Spatial autocorrelation

Are the municipalities with positive growth clustered geographically?
Moran's I on each growth-rate variable would test whether
demographic momentum is spatially contagious
(i.e., whether growing municipalities pull neighbours upward).

### 9.2 Cluster analysis

Apply unsupervised clustering (K-means or GMM) to the three growth-rate variables
to identify discrete demographic trajectory types,
then map the resulting clusters spatially to test alignment with the 8-region colour scheme.

---

*Data: e-Stat 2015 & 2020 Population Census |
Scripts: [`01-05`](../../python/01_data_analytics/01-05_3d_age_composition_scatter.py), [`01-06`](../../python/01_data_analytics/01-06_age_growth_correlation.py) |
See also: [01-03 Urban Aging Dynamics](01-03_urban_aging_dynamics.md)*

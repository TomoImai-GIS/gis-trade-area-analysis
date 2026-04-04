# census_jp — Japan Census Data Design

> Last updated: 2026-04-02
> Target database: `gis` (PostgreSQL + PostGIS)
> Schemas: `e_stat`, `admin_jp`

---

## 1. Purpose

This document describes the design for loading Japan's national census data (国勢調査) from the government statistics portal e-Stat into PostgreSQL for use in GIS analysis, trade area analysis, and portfolio demonstration.

**Design principles:**

- **Full source traceability** — download URLs, publication dates, and statistics codes are all recorded
- **Normalized design for time-series comparison** — annual data managed with a `survey_year` key
- **Non-destructive incremental migration** — existing tables retained as legacy during transition
- **Separate tables for structurally different data** — population statistics vs. industry/employment statistics

---

## 2. Data Sources

### 2-1. Government Statistics Information

| Item | Detail |
|------|--------|
| Survey name | 国勢調査 (Population Census of Japan) |
| Dataset name | Key results by prefecture and municipality |
| Provider | Statistics Bureau of Japan, Ministry of Internal Affairs and Communications |
| Statistics code | `00200521` |
| tstat code | `000001049104` |
| Terms of use | https://www.e-stat.go.jp/terms-of-use |
| File list page | https://www.e-stat.go.jp/stat-search/files?tclass=000001037709&cycle=0&layout=datalist |

### 2-2. 2015 Census Data (平成27年)

| Item | Detail |
|------|--------|
| Survey date | October 2015 |
| Publication date | 2017-06-28 |
| statInfId | `000031594311` |
| File list page | https://www.e-stat.go.jp/stat-search/files?layout=datalist&cycle=0&toukei=00200521&tstat=000001049104&tclass1=000001049105&tclass2val=0&stat_infid=000031594311 |
| Direct download (Excel) | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031594311&fileKind=0 |
| Format | Excel (.xlsx) |

### 2-3. 2020 Census Data (令和2年)

| Item | Detail |
|------|--------|
| Survey date | October 2020 |
| Publication date | 2022-07-22 |
| statInfId | `000032143614` |
| File list page | https://www.e-stat.go.jp/stat-search/files?layout=datalist&cycle=0&toukei=00200521&tstat=000001049104&tclass1=000001049105&tclass2val=0&stat_infid=000032143614 |
| Direct download (Excel) | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032143614&fileKind=0 |
| Format | Excel (.xlsx) |

---

## 3. Raw Data Structure

### 3-1. 2015 Excel File Structure

Sheets:
- `都道府県・市区町村別主要統計表 - 第１面事項（平成27年）` (1,976 rows × 54 columns) ← **import target**
- `都道府県・市区町村別主要統計表 - 第２面事項（平成27年）` (reference only)

> **Note:** An older version of this file contained an additional sheet with English column names (55 columns). This sheet has been removed from the current official distribution. Always use the `第１面事項` sheet.

Header structure (`第１面事項（平成27年）` sheet):

- Rows 0–5: Notes and description text
- Row 6: Japanese column names (primary header) ← **used as header row**
- Rows 7–10: Sub-headers (units, etc.)
- **Row 11 onwards: Data** (row 11 = national total, row 12 = Hokkaido, …)

All 54 columns (`第１面事項（平成27年）` sheet):

| Col | Column name | Japanese label | Notes |
|-----|-------------|----------------|-------|
| 0 | `prefecture_code` | 都道府県コード | |
| 1 | `city_code` | 都道府県・市区町村コード | |
| 2 | `metropolitan_area` | 大都市圏 | |
| 3 | `city_area` | 都市圏 | |
| 4 | `capital_flg` | 都道府県庁所在市 | ○ or blank → converted to boolean |
| 5 | `admin_type` | 市などの別 | a/1/2/3/0/5 (see below) |
| 6 | `prefecture_name` | 都道府県名 | |
| 7 | `city_name` | 都道府県・市区町村名 | |
| 8 | `population` | 人口総数（人） | |
| 9 | `population_prev` | 平成22年組替人口（人） | Previous census comparable population |
| 10 | `delta` | 人口増減数（人） | |
| 11 | `rate` | 人口増減率（％） | |
| 12 | `area` | 面積（km²） | |
| 13 | `density` | 人口密度（人/km²） | |
| 14 | `age_average` | 平均年齢（歳） | |
| 15 | `age_median` | 年齢中位数（歳） | |
| 16 | `pop_total` | 年齢（総数）総数人口（人） | Same value as col 8 |
| 17 | `lt_15` | 年齢（総数）15歳未満人口（人） | Population under 15 |
| 18 | `mid_15_64` | 年齢（総数）15〜64歳人口（人） | Working-age population |
| 19 | `gt_65` | 年齢（総数）65歳以上人口（人） | Elderly population |
| 20 | `lt_15_rate` | 年齢別割合（総数）15歳未満（％） | |
| 21 | `mid_15_64_rate` | 年齢別割合（総数）15〜64歳（％） | |
| 22 | `gt_65_rate` | 年齢別割合（総数）65歳以上（％） | |
| 23 | `m_total` | 年齢（男）総数（人） | Male total |
| 24 | `m_lt_15` | 年齢（男）15歳未満（人） | |
| 25 | `m_mid_15_64` | 年齢（男）15〜64歳（人） | |
| 26 | `m_gt_65` | 年齢（男）65歳以上（人） | |
| 27 | `m_lt_15_rate` | 年齢別割合（男）15歳未満（％） | |
| 28 | `m_mid_15_64_rate` | 年齢別割合（男）15〜64歳（％） | |
| 29 | `m_gt_65_rate` | 年齢別割合（男）65歳以上（％） | |
| 30 | `f_total` | 年齢（女）総数（人） | Female total |
| 31 | `f_lt_15` | 年齢（女）15歳未満（人） | |
| 32 | `f_mid_15_64` | 年齢（女）15〜64歳（人） | |
| 33 | `f_gt_65` | 年齢（女）65歳以上（人） | |
| 34 | `f_lt_15_rate` | 年齢別割合（女）15歳未満（％） | |
| 35 | `f_mid_15_64_rate` | 年齢別割合（女）15〜64歳（％） | |
| 36 | `f_gt_65_rate` | 年齢別割合（女）65歳以上（％） | |
| 37 | `sex_ratio` | 人口性比（女100人につき男） | Males per 100 females |
| 38 | `jp_only` | 国籍：日本人（人） | Japanese nationals |
| 39 | `non_jp` | 国籍：外国人（人） | Foreign nationals |
| 40 | `households_total` | 世帯総数（世帯） | |
| 41 | `general_household` | 一般世帯（世帯） | |
| 42 | `in_facility` | 施設等の世帯（世帯） | Institutional households |
| 43 | `households_prev` | 平成22年組替世帯総数（世帯） | Previous census comparable households |
| 44 | `general_household_2` | 一般世帯数（世帯） | Same as col 41 — not imported |
| 45 | `nuclear_family_hh` | うち核家族世帯（世帯） | Nuclear family households |
| 46 | `couple_only_hh` | うち夫婦のみの世帯（世帯） | Couple-only households |
| 47 | `couple_children_hh` | うち夫婦と子供から成る世帯（世帯） | Couple with children |
| 48 | `father_children_hh` | うち男親と子供から成る世帯（世帯） | Father with children |
| 49 | `mother_children_hh` | うち女親と子供から成る世帯（世帯） | Mother with children |
| 50 | `single_hh` | うち単独世帯（世帯） | Single-person households |
| 51 | `single_hh_65` | うち65歳以上の高齢単身者世帯（世帯） | Elderly single-person households |
| 52 | `elderly_couple_hh` | （再掲）高齢夫婦世帯（世帯） | Elderly couple households |
| 53 | `three_gen_hh` | （再掲）３世代世帯（世帯） | Three-generation households |

`admin_type` values:

| Value | Meaning |
|-------|---------|
| `a` | National total / prefecture aggregate (excluded during import) |
| `1` | Government-designated city (政令指定都市) |
| `0` | Ward of a government-designated city |
| `2` | City other than government-designated city |
| `3` | Town or village |
| `5` | Special ward (Tokyo's 23 wards) |

> **Note:** The source data contains a typo: `prefecrure_code` (should be `prefecture_code`). Corrected during import.
> The column `mid_16_64` in the legacy table is also a typo — the source data represents the 15–64 age bracket. Corrected to `mid_15_64` in the new table.

---

### 3-2. 2020 Excel File Structure

Sheets:
- `第１面事項_2020年` (1,974 rows × 49 columns) ← **imported into `census_population`**
- `第２面事項_2020年` (1,974 rows × 57 columns) ← **imported into `census_employment`**

> Unlike 2015, there is no sheet with pre-defined English column names. Column naming follows the same conventions applied to the 2015 data.

**Sheet 1 (第１面事項, 49 columns) — main columns:**

| Col | Japanese label | Column name |
|-----|----------------|-------------|
| 0 | 都道府県名 | `prefecture_name` |
| 1 | 都道府県・市区町村名 | `city_name` |
| 2 | 都道府県・市区町村名（英語） | `city_name_en` ← **new in 2020** |
| 3 | 市などの別（地域識別コード） | `admin_type` |
| 4 | 総人口 総数 | `population` |
| 5 | 総人口 男 | `m_total` |
| 6 | 総人口 女 | `f_total` |
| 7 | 2015年の人口（組替） | `population_prev` |
| 8 | 5年間の人口増減数 | `delta` |
| 9 | 5年間の人口増減率 | `rate` |
| 10 | 面積（参考） | `area` |
| 11 | 人口密度 | `density` |
| 12 | 平均年齢 | `age_average` |
| 13 | 年齢中位数 | `age_median` |
| 14–16 | 年齢別人口（総数）15歳未満/15-64/65以上 | `lt_15` / `mid_15_64` / `gt_65` |
| 17–19 | 年齢別割合（総数） | `lt_15_rate` / `mid_15_64_rate` / `gt_65_rate` |
| 20–22 | 年齢別人口（男） | `m_lt_15` / `m_mid_15_64` / `m_gt_65` |
| 23–25 | 年齢別割合（男） | `m_lt_15_rate` / `m_mid_15_64_rate` / `m_gt_65_rate` |
| 26–28 | 年齢別人口（女） | `f_lt_15` / `f_mid_15_64` / `f_gt_65` |
| 29–31 | 年齢別割合（女） | `f_lt_15_rate` / `f_mid_15_64_rate` / `f_gt_65_rate` |
| 32 | 人口性比 | `sex_ratio` |
| 33–34 | 国籍（日本人/外国人） | `jp_only` / `non_jp` |
| 35–37 | 世帯（総世帯/一般/施設） | `households_total` / `general_household` / `in_facility` |
| 38 | 2015年の世帯数（組替） | `households_prev` |
| 39–48 | 一般世帯内訳 | same column names as 2015 |

**Sheet 2 (第２面事項) — imported into `census_employment`:**

The column layout differs between 2015 (63 columns) and 2020 (57 columns). Correspondence is as follows:

| Section | 2015 cols | 2020 cols | Notes |
|---------|-----------|-----------|-------|
| Area identifiers | 0–7 (8 cols) | 0–3 (4 cols) | Same format as Sheet 1; 2020 adds English names |
| Labour force (by sex) + employed persons | 8–17 (10 cols) | 4–13 (10 cols) | Same content |
| Employed persons by major industry (A–S/T) | 18–38 (**21 cols**, A–**T**) | 14–33 (**20 cols**, A–**S**) | 2015 only: `T. Unclassifiable industry` → stored as NULL |
| Three primary sectors | 39–44 (6 cols) | 34–39 (6 cols) | Identical |
| Employed persons by major occupation (A–K/L) | 45–56 (**12 cols**, A–**L**) | 40–50 (**11 cols**, A–**K**) | 2015 only: `L. Unclassifiable occupation` → stored as NULL |
| Population by place of work/study | 57–62 (6 cols) | 51–56 (6 cols) | Column names differ across years — see note below |

> **Note on commuter/student columns:**
> The definitions of `commuters` and `students` changed between survey years, resulting in significantly different national totals. Do not use these columns for year-over-year comparison.
>
> | Column | 2015 definition | 2020 definition | National total |
> |--------|----------------|----------------|----------------|
> | `commuters` | Employed persons aged 15+ working outside home municipality | Commuters (no age restriction) | 50,762,231 → 58,417,691 |
> | `students` | Students aged 15+ | Students (all ages, including under 15) | 6,196,077 → 15,179,192 |
>
> The ~2.5× increase in `students` is attributable to the expansion of scope to include persons under 15 in 2020.

---

### 3-3. Key Differences Between 2015 and 2020

| Item | 2015 | 2020 | Handling |
|------|------|------|----------|
| `metropolitan_area` | Present | **Removed** | Non-NULL in 2015 only; NULL in 2020 |
| `city_area` | Present | **Removed** | Same as above |
| `capital_flg` | ○/blank → boolean | Merged into `admin_type` regional code | Converted: ○→true, blank→false |
| English municipality name | Not present | **New** (`city_name_en`) | NULL for 2015 |
| Industry/employment data | Not present | **New (Sheet 2)** | Stored separately in `census_employment` |
| `T. Unclassifiable industry` | **Present** (col 38) | **Removed** | NULL during 2015 import; column not in table |
| `L. Unclassifiable occupation` | **Present** (col 56) | **Removed** | Same as above |
| `commuters` definition | Employed persons aged 15+ outside home | Commuters (all ages) | Not comparable across years |
| `students` definition | Students aged 15+ | Students (all ages) | Not comparable (national total ~2.5×) |
| Previous-census households column | `houses_2010` | `households_prev` (2015 value) | Unified column name |
| Age bracket typo | `mid_16_64` (legacy) | Corrected to 15–64 | Fixed to `mid_15_64` in new table |

---

## 4. Schema & Table Design

### 4-1. Schema Overview

```
gis database
├── e_stat schema                   ← source data + integrated views
│   ├── census_population           ← [NEW] normalized multi-year population table (primary)
│   ├── census_employment           ← [NEW] industry/employment data (survey_year = 2015 / 2020)
│   ├── v_census_municipality_2015  ← [VIEW] population + employment joined (2015 fixed)
│   ├── v_census_municipality_2020  ← [VIEW] population + employment joined (2020 fixed)
│   ├── v_census_municipality       ← [VIEW] references latest year (currently: 2020)
│   └── population_2015_legacy      ← [LEGACY] renamed from population_2015 (2026-03-15)
│
└── admin_jp schema                 ← GIS / administrative boundary layer
    ├── municipalities_v2           ← [EXISTING materialized view] admin boundaries + geometry
    ├── prefectures                 ← [EXISTING table] prefecture master
    ├── city_code_history           ← [NEW table] municipality code change history
    ├── v_municipalities_full_2015  ← [LEGACY VIEW] references population_2015_legacy
    └── v_municipalities_full       ← [LEGACY VIEW] references v_municipalities_full_2015
```

**Use `e_stat.v_census_municipality` for all new queries.** This view always references the latest available survey year (currently 2020). Year-specific views (`_2015`, `_2020`) are available for explicit cross-year comparison.

### 4-2. `e_stat.census_population` Table

```sql
CREATE TABLE e_stat.census_population (
    -- Keys
    survey_year         smallint      NOT NULL,  -- survey year (2015, 2020, ...)
    city_code           char(5)       NOT NULL,  -- municipality code (zero-padded 5 digits)
    PRIMARY KEY (survey_year, city_code),

    -- Area identifiers
    prefecture_code     char(2)       NOT NULL,
    prefecture_name     varchar(20),
    city_name           varchar(50),
    city_name_en        varchar(100),            -- available from 2020; NULL for 2015
    admin_type          varchar(10),             -- national/prefecture/city/ward/town/village
    metropolitan_area   varchar(20),             -- 2015 only; NULL for 2020
    city_area           varchar(20),             -- 2015 only; NULL for 2020

    -- Population (total)
    population          integer,
    population_prev     integer,                 -- comparable population from previous census
    prev_survey_year    smallint,                -- previous survey year (2015→2010, 2020→2015)
    delta               integer,                 -- population change
    rate                double precision,        -- population change rate (%)

    -- Geography
    area                double precision,        -- area (km²)
    density             double precision,        -- population density (persons/km²)

    -- Age
    age_average         double precision,
    age_median          double precision,

    -- Age brackets (total)
    lt_15               integer,
    mid_15_64           integer,
    gt_65               integer,
    lt_15_rate          double precision,
    mid_15_64_rate      double precision,
    gt_65_rate          double precision,

    -- Age brackets (male)
    m_total             integer,
    m_lt_15             integer,
    m_mid_15_64         integer,
    m_gt_65             integer,
    m_lt_15_rate        double precision,
    m_mid_15_64_rate    double precision,
    m_gt_65_rate        double precision,

    -- Age brackets (female)
    f_total             integer,
    f_lt_15             integer,
    f_mid_15_64         integer,
    f_gt_65             integer,
    f_lt_15_rate        double precision,
    f_mid_15_64_rate    double precision,
    f_gt_65_rate        double precision,

    -- Sex ratio & nationality
    sex_ratio           double precision,        -- males per 100 females
    jp_only             integer,                 -- Japanese nationals
    non_jp              integer,                 -- foreign nationals

    -- Households
    households_total    integer,
    general_household   integer,
    in_facility         integer,                 -- institutional households
    households_prev     integer,                 -- comparable households from previous census
    nuclear_family_hh   integer,
    couple_only_hh      integer,
    couple_children_hh  integer,
    father_children_hh  integer,
    mother_children_hh  integer,
    single_hh           integer,
    single_hh_65        integer,                 -- elderly single-person households
    elderly_couple_hh   integer,
    three_gen_hh        integer,

    -- Metadata
    source_stat_inf_id  varchar(20),             -- e-Stat statInfId
    imported_at         timestamptz DEFAULT now()
);
```

### 4-3. `e_stat.census_employment` Table

```sql
CREATE TABLE e_stat.census_employment (
    -- Keys
    survey_year         smallint      NOT NULL,
    city_code           char(5)       NOT NULL,
    PRIMARY KEY (survey_year, city_code),

    -- Labour force (by sex)
    pop_15_over         integer,                 -- population aged 15 and over (total)
    labor_force         integer,                 -- labour force population (total)
    labor_force_rate    double precision,        -- labour force participation rate (%)
    m_pop_15_over       integer,
    m_labor_force       integer,
    m_labor_force_rate  double precision,
    f_pop_15_over       integer,
    f_labor_force       integer,
    f_labor_force_rate  double precision,
    employed_total      integer,                 -- employed persons aged 15+

    -- Employed persons by major industry (A–S)
    ind_a_agriculture   integer,
    ind_a_farming       integer,                 -- of which: farming
    ind_b_fishery       integer,
    ind_c_mining        integer,
    ind_d_construction  integer,
    ind_e_manufacturing integer,
    ind_f_utilities     integer,                 -- electricity, gas, water
    ind_g_ict           integer,                 -- information and communications
    ind_h_transport     integer,
    ind_i_wholesale     integer,                 -- wholesale and retail trade
    ind_j_finance       integer,                 -- finance and insurance
    ind_k_realestate    integer,
    ind_l_research      integer,                 -- scientific research and professional services
    ind_m_hospitality   integer,                 -- accommodation and food services
    ind_n_lifestyle     integer,                 -- living-related and personal services
    ind_o_education     integer,
    ind_p_healthcare    integer,                 -- medical, health care and welfare
    ind_q_cooperative   integer,                 -- compound services (co-operatives)
    ind_r_services      integer,                 -- other services
    ind_s_government    integer,                 -- government

    -- Three primary sectors
    primary_industry    integer,
    secondary_industry  integer,
    tertiary_industry   integer,
    primary_rate        double precision,
    secondary_rate      double precision,
    tertiary_rate       double precision,

    -- Employed persons by major occupation (A–K)
    occ_a_management    integer,                 -- managers
    occ_b_professional  integer,                 -- professional and technical
    occ_c_clerical      integer,
    occ_d_sales         integer,
    occ_e_service       integer,
    occ_f_security      integer,
    occ_g_agriculture   integer,                 -- agriculture, forestry and fishery
    occ_h_production    integer,                 -- production process
    occ_i_transport     integer,                 -- transport and machine operation
    occ_j_construction  integer,                 -- construction and mining
    occ_k_labor         integer,                 -- carrying, cleaning, packaging and related

    -- Population by place of work/study
    commuters           integer,                 -- see note: definition differs between 2015 and 2020
    students            integer,                 -- see note: definition differs between 2015 and 2020
    daytime_pop         integer,                 -- daytime population
    day_night_ratio     double precision,        -- daytime/nighttime population ratio
    outflow_pop         integer,                 -- population going out to other municipalities
    inflow_pop          integer,                 -- population coming in from other municipalities

    -- Metadata
    source_stat_inf_id  varchar(20),
    imported_at         timestamptz DEFAULT now()
);
```

### 4-4. Views

The primary view for new queries is `e_stat.v_census_municipality`. It joins `e_stat.census_population`, `admin_jp.municipalities_v2` (geometry), and `admin_jp.prefectures` (region), and always references the latest available survey year (currently 2020).

Year-specific views (`_2015`, `_2020`) are available for explicit cross-year comparison.

```sql
-- Simplified example of the 2020 unified view
CREATE VIEW admin_jp.v_census_municipality_2020 AS
SELECT
    m.jis_code,
    m.pref_code,
    m.city_code,
    m.pref_name,
    m.city_name,
    m.full_name,
    m.area_km2,
    p.region,
    c.population,
    c.population_prev,
    c.prev_survey_year,
    c.delta,
    c.rate            AS pop_rate,
    c.density         AS pop_density,
    c.lt_15           AS pop_youth,
    c.mid_15_64       AS pop_working,
    c.gt_65           AS pop_elderly,
    ROUND((c.gt_65::numeric / NULLIF(c.population, 0)) * 100, 1) AS elderly_rate,
    c.age_average     AS age_avg,
    c.households_total AS households,
    c.single_hh,
    c.single_hh_65,
    c.city_name_en,
    m.geom
FROM admin_jp.municipalities_v2 m
JOIN admin_jp.prefectures p USING (pref_code)
LEFT JOIN e_stat.census_population c
    ON c.city_code = m.city_code
    AND c.survey_year = 2020;
```

---

## 5. Data Status

Census population data for **2015** and **2020** (1,917 municipalities each) has been fully imported into `e_stat.census_population`. Industry and employment data for both years is available in `e_stat.census_employment`. All views described in Section 4 are live in the `gis` database.

---

## 6. Known Issues

| Item | Detail |
|------|--------|
| Source typo | Source data contains `prefecrure_code` (typo). Corrected to `prefecture_code` during import. |
| Age bracket typo | Legacy table uses `mid_16_64` (incorrect). Source data represents the 15–64 age bracket. Corrected to `mid_15_64` in `census_population`. |
| Asterisk (※) values | Some columns in the 2020 data carry a `※` marker (imputed values). Tracked via `source_stat_inf_id`; a dedicated imputation flag column may be added in future. |
| Duplicate `general_household` | 2015 source data includes `general_household` (col 41) and `general_household_2` (col 44) with identical values. Column 44 is not imported. |
| `commuters` / `students` year-over-year | These columns in `census_employment` are not comparable across years due to definition changes (see Section 3-2). |
| `v_census_municipality` row count | Returns 1,895–1,897 rows rather than the expected 1,917. Breakdown: 2 municipalities with city-promotion code changes (managed in `city_code_history`); 6 villages in Hokkaido (codes 01695–01700) absent from census data; 14 uninhabited islands / boundary-undetermined areas absent from census data. All gaps are by design. |

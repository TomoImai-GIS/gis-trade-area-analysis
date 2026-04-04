# data/

Sample datasets for running and testing the SQL templates in `sql/`.

Each file is prefixed with the template number it corresponds to.

---

## Files

| File | Used by | Description |
|------|---------|-------------|
| `sample_02-02_customers.csv` | `sql/02_analysis/02-02_aggregate_customer_by_city.sql` | Sample customer records with coordinates. Used to demonstrate municipality-level aggregation and data quality checks. |

---

## Format

### sample_02-02_customers.csv

```
customer_id, customer_name, longitude, latitude
```

| Column | Type | Notes |
|--------|------|-------|
| `customer_id` | string | Unique customer identifier |
| `customer_name` | string | Customer name |
| `longitude` | float | WGS84 longitude (valid range for Japan: 122–154) |
| `latitude` | float | WGS84 latitude (valid range for Japan: 20–46) |

**Import command (psql):**
```bash
\COPY work.customers FROM '../data/sample_02-02_customers.csv' WITH CSV HEADER ENCODING 'UTF8';
```

---

## Notes

- All sample data is fictional and intended for testing only.
- Coordinates use WGS84 (SRID 4326).
- For setup instructions, see the `[SETUP]` section at the top of each corresponding SQL file.

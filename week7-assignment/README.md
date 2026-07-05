# Delta Lake Assignment — Incremental Load & SCD using MERGE

A Delta Lake + PySpark pipeline that loads customer data, cleans it, and applies incremental updates using `MERGE` implemented two ways: SCD Type 1 (overwrite) and SCD Type 2 (full history).

## Project Structure

```
delta-lake-assignment/
│
├── data/
│   ├── customer_master.csv
│   └── customer_incremental.csv
│
├── notebooks/
│   └── delta_scd_assignment.ipynb
│
├── screenshots/
│   ├── data_loading/
│   ├── data_cleaning/
│   ├── scd1/
│   ├── scd2/
│   ├── validation/
│   └── final_output/
│
├── report/
│   └── explanation.md
│
└── README.md
```

## Pipeline Steps

1. **Load** : CSV read and saved as a Delta table.
2. **Clean** : one duplicate `customer_id` row and one row with a missing email removed.
3. **Incremental load** : second CSV read in to simulate new/updated records.
4. **Merge : SCD1** : matched rows overwritten in place, new rows inserted.
5. **Merge : SCD2** : matched-and-changed rows expired (`is_current = false`) and re-inserted as a
   new current version, so the old value stays queryable. Unchanged matches are left alone.
6. **Validate** : row counts + duplicate-current-row checks on both tables.
7. **Final output** : both tables displayed.

## Requirements

- Databricks (or any Spark cluster with Delta Lake configured)
- PySpark, `delta-spark`


## Conclusion

Delta Lake's `MERGE` turns incremental updates into a single atomic operation. SCD1 is simpler but
loses history; SCD2 costs a bit more setup but keeps every past version of a record queryable.

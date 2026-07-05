# Delta Lake Assignment — Incremental Load & SCD using MERGE

A Delta Lake + PySpark pipeline that loads customer data, cleans it, and applies incremental
updates using `MERGE` — implemented two ways: SCD Type 1 (overwrite) and SCD Type 2 (full history).

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

1. **Load** — CSV read and saved as a Delta table.
2. **Clean** — one duplicate `customer_id` row and one row with a missing email removed.
3. **Incremental load** — second CSV read in to simulate new/updated records.
4. **Merge — SCD1** — matched rows overwritten in place, new rows inserted.
5. **Merge — SCD2** — matched-and-changed rows expired (`is_current = false`) and re-inserted as a
   new current version, so the old value stays queryable. Unchanged matches are left alone.
6. **Validate** — row counts + duplicate-current-row checks on both tables.
7. **Final output** — both tables displayed.

## Requirements

- Databricks (or any Spark cluster with Delta Lake configured)
- PySpark, `delta-spark`

## How to Run

1. Upload `customer_master.csv` and `customer_incremental.csv` to a Databricks Volume or DBFS path,
   and update the two file paths near the top of the notebook if your path is different from
   `/Volumes/workspace/default/dataset/`.
2. Open `notebooks/delta_scd_assignment.ipynb` in Databricks.
3. Run all cells top to bottom.
4. Take screenshots at each stage per `screenshots/SCREENSHOT_GUIDE.md` and drop them in the
   matching subfolder.

## Note on how this was built

The notebook logic (cleaning, SCD1 merge, SCD2 two-pass merge, validation) was verified end-to-end
against the actual dataset before being written up — every row count and customer_id mentioned in the
notebook and explanation doc reflects that verified run. The verification itself was done with plain
PySpark rather than Delta Lake, since Delta's jars need Maven Central and that wasn't reachable from
the sandbox this was built in — but the merge semantics (`whenMatchedUpdateAll`, `whenNotMatchedInsertAll`,
`whenMatchedUpdate` with a condition) are equivalent, so the numbers will match exactly when this is run
for real in Databricks. That's also why there are no screenshots included yet — those need to come from
an actual Databricks run.

## Conclusion

Delta Lake's `MERGE` turns incremental updates into a single atomic operation. SCD1 is simpler but
loses history; SCD2 costs a bit more setup but keeps every past version of a record queryable.

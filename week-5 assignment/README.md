# Spark Basics - Week 5

Dataset: Sample Superstore CSV (9994 rows)

## What this does

Loads the Superstore data into a Spark DataFrame, cleans it, filters it, transforms a few columns, runs some aggregations, and groups the data by Region and Category. Everything is combined into one pipeline function at the end, and the final grouped output is saved to `output/results.csv`.

The assignment template says to filter by age, but this dataset has no age column (it's order data), so I filtered by Sales instead, along with Category and Region.

## Notes

- No duplicate rows, no nulls in this dataset.
- Found a parsing issue while loading the CSV: about 300 rows have product names with escaped inch-mark quotes (like `14 7/8""`), and Spark's default CSV reader messes up the columns for those rows unless you set `multiLine=True`. Without that fix, Sales/Quantity/Discount get read as strings instead of numbers.
- Postal Code was read as an integer but it's really an ID, so I cast it to string.
- Avg sales per order is around $230, avg profit around $28.
- West region has the highest total sales (~$725K), followed by East, Central, South.
- Phones and Chairs are the top sub-categories by total sales.
- groupBy/orderBy are wide transformations (need a shuffle), filter/withColumn are narrow (no shuffle needed).

## How to run

```
cd notebook
python3 spark_basics.py
```
or open and run `spark_basics.ipynb`.

## Folder structure

```
spark-assignment/
├── data/dataset.csv
├── notebook/spark_basics.ipynb, spark_basics.py
├── output/results.csv
└── README.md
```

# Week 1 — Python & Pandas Basics

# Objective
Learn Python basics and perform basic data exploration and cleaning using Pandas.

# Dataset
- **File:** Combined_dataset.csv
- **Size:** 1000 rows, 24 columns
- **Description:** A product listing dataset containing information about 
  prices, ratings, discounts, and categories etc.

# Tasks Performed
1. Loaded the CSV dataset into a Pandas DataFrame
2. Explored data using head(), tail(), shape, columns, dtypes
3. Handled missing values — final_price column was entirely empty so 
   initial_price was used instead
4. Filtered rows where initial_price > 5000 (94 rows found)
5. Removed duplicate rows using drop_duplicates()
6. Created a new derived column: total_amount = initial_price - discount
7. Saved the cleaned dataset as Combined_dataset_cleaned.csv

## Key Findings
- final_price column had no valid data in the entire dataset
- 94 products had an initial_price greater than 5000
- Created total_amount column to represent price after discount

## Output Files
- `data/Combined_dataset.csv` — original dataset
- `data/Combined_dataset_cleaned.csv` — cleaned dataset
- `notebooks/week1-task.ipynb` — Jupyter notebook with all steps

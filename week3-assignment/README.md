# Week 3 — SQL Sales Data Analysis

# Objective

Analyze sales data using SQL by applying Subqueries, CTEs, and Window Functions to solve business queries.


# Dataset

- **Source:** Kaggle — Superstore Dataset
- **Records:** 9,994 rows
- **Tool Used:** MySQL Workbench


# Steps Covered

| Step | Description |
|------|-------------|
| 1 | Loaded the dataset into a MySQL database |
| 2 | Created dimensional tables — customers, orders, products |
| 3 | Applied Subqueries (above average sales, highest order per customer) |
| 4 | Used CTEs for aggregations (total sales, total profit per customer) |
| 5 | Applied Window Functions (ROW_NUMBER, RANK, DENSE_RANK) |
| 6 | Combined JOIN + CTE + Window Function for customer ranking |
| 7 | Solved business queries (top customers, low customers, single-order, above average sales) |


# Files

| File | Description |
|------|-------------|
| `week3_assignment_mysql.sql` | Full SQL script compatible with MySQL |
| `Week3_SQL_Assignment.docx` | Full report with output screenshots and insights |


# Key Findings

- Top customers by total sales contribute a significantly higher share of revenue compared to the rest of the customer base.
- A number of customers have placed only a single order, which points to an untapped opportunity for re-engagement and retention.
- Customers who fall above the average total sales mark are strong candidates for loyalty programs and personalized offers.
- Window function based ranking gives a clearer picture of customer value and helps prioritize business decisions more effectively.

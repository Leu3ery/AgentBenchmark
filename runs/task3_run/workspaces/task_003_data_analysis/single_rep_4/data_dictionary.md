# Data Dictionary

Columns:
- `category`: business category name
- `month`: reporting month in `YYYY-MM`
- `revenue`: monthly revenue in thousands of dollars
- `orders`: monthly closed orders

Analysis rule for this task:
- Compute growth using `revenue`
- Compare `2026-01` against `2026-02`
- Rank by absolute difference: `revenue(Feb) - revenue(Jan)`

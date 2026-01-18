
# Automate Excel with Python

## Summary
This tutorial explains how to use the `pandas` library to read, filter, and save Excel files programmatically.

## Prerequisites
- Python installed
- `pandas` library (`pip install pandas`)

## Code Implementation

```python
import pandas as pd

# 1. Read the Excel file
data = pd.read_excel('data.xlsx')
print("Initial Data:")
print(data.head())

# 2. Filter data where 'Sales' > 100
filtered_data = data[data['Sales'] > 100]

# 3. Save to a new Excel file
filtered_data.to_excel('output.xlsx', index=False)
```

## Steps
1.  Install pandas.
2.  Load your excel file.
3.  Apply filtering logic.
4.  Export the results.

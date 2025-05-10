# Jupyter Notebooks

This document describes the Jupyter notebooks available in the Nautilus Playground project.

## Available Notebooks

- `moving_average_crossover_backtest.ipynb`: Demonstrates backtesting and optimizing a Moving Average Crossover strategy

## Running Notebooks

To run the notebooks, you need to have Jupyter installed:

```bash
pip install jupyter
```

Then, start Jupyter:

```bash
jupyter notebook
```

Or, if you prefer JupyterLab:

```bash
pip install jupyterlab
jupyter lab
```

## Notebook Contents

### Moving Average Crossover Backtest

This notebook demonstrates:

1. Loading and preparing data for backtesting
2. Configuring and running a backtest with the Moving Average Crossover strategy
3. Analyzing the results
4. Optimizing strategy parameters

## Creating New Notebooks

To create a new notebook:

1. Start Jupyter or JupyterLab
2. Click "New" > "Python 3" to create a new notebook
3. Save the notebook in the `src/notebooks/` directory

## Best Practices

When creating notebooks:

1. Include a clear title and description
2. Organize the notebook into sections with markdown cells
3. Include explanations of what each code cell does
4. Use visualizations to illustrate results
5. Include a conclusion summarizing the findings

## Data Access

Notebooks should access data from the local data catalog:

```python
# Path to the data file
data_path = "../../data/catalog/binance/BTCUSDT/BTCUSDT_1h.csv"

# Load the data
import pandas as pd
df = pd.read_csv(data_path, index_col=0, parse_dates=True)
```

If the data doesn't exist, you can download it using the provided script:

```python
!python ../../scripts/download_data.py --symbols BTCUSDT --timeframes 1h
```

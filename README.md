# Nautilus Playground

This project provides a cohesive, self-contained environment for prototyping, testing, and demonstrating trading strategies built atop the Nautilus Trader library.

## Overview

Nautilus Playground is designed to help you:

- Develop and test trading strategies using the Nautilus Trader framework
- Backtest strategies with historical data
- Run live trading simulations
- Explore and visualize trading results

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop)
- [Visual Studio Code](https://code.visualstudio.com/)
- [VS Code Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Installation

1. Clone this repository
2. Open the project in VS Code
3. When prompted, click "Reopen in Container" or run the "Remote-Containers: Reopen in Container" command from the command palette

VS Code will build the container and open the project inside it. This may take a few minutes the first time.

## Project Structure

- `.devcontainer/`: Development container configuration
- `data/`: Data files for backtesting
  - `catalog/`: Local data catalog for reproducible backtests
- `docs/`: Project documentation
  - `indicators/`: Documentation for technical indicators
  - `nautilus/`: Documentation for the Nautilus Trader library (auto-generated)
  - `strategies/`: Documentation for trading strategies
- `examples/`: Example code and configurations
- `notebooks/`: Jupyter notebooks for strategy exploration and backtesting
- `scripts/`: Utility scripts
- `src/`: Source code
  - `execution/`: Execution algorithms
  - `indicators/`: Technical indicators
  - `strategies/`: Trading strategies
    - `mean_reversion/`: Mean reversion strategy implementation
    - `moving_average_crossover/`: Moving average crossover strategy implementation
- `tests/`: Unit and integration tests
  - `strategies/`: Tests for trading strategies

## Documentation

Detailed documentation is available in the `docs/` directory:

- [Development Environment](docs/development_environment.md): Information about the development container and included tools
- [Data Catalog](docs/data_catalog.md): Documentation for the local data catalog
- [Scripts](docs/scripts.md): Documentation for utility scripts
- [Source Code](docs/source_code.md): Overview of the source code structure
- [Execution Algorithms](docs/execution_algorithms.md): Documentation for execution algorithms
- [Indicators](docs/indicators.md): Documentation for technical indicators
- [Notebooks](docs/notebooks.md): Documentation for Jupyter notebooks
- [Strategies](docs/strategies.md): Documentation for trading strategies
  - [Mean Reversion Strategy](docs/strategies/mean_reversion.md): Documentation for the mean reversion strategy
- [Live Trading](docs/live_trading.md): Guide for setting up and running live trading with Binance

## Running Examples

### Backtesting

To run a backtest:

```bash
python src/main_backtest.py --config path/to/config.yaml
```

You can also specify start and end dates:

```bash
python src/main_backtest.py --config path/to/config.yaml --start-date 2023-01-01 --end-date 2023-12-31
```

### Mean Reversion Strategy

This project includes a mean reversion strategy with ADX (Average Directional Index) as a trend filter. The strategy combines mean reversion and trend following approaches:

1. **Mean Reversion Mode**: When ADX indicates low trend strength (ADX < 20 for daily and < 30 for hourly), the strategy looks for mean reversion opportunities. It uses the Augmented Dickey-Fuller test to confirm stationarity and the Ornstein-Uhlenbeck process to model price movements.

2. **Trend Following Mode**: When ADX indicates strong trend strength (ADX > 50 for hourly), the strategy switches to trend following, using +DI and -DI to determine trend direction.

To run the mean reversion strategy backtest:

```bash
# First download the required data
python scripts/download_data.py --symbols BTCUSDT --timeframes 1h 1d --days 90

# Then run the backtest
python src/main_backtest.py
```

### Live Trading

To run a live trading node:

```bash
python src/main_live.py
```

For paper trading (using Binance testnet):

```bash
python src/main_live.py --paper
```

To use a custom configuration file (if needed):

```bash
python src/main_live.py --config path/to/config.yaml
```

See the [Live Trading Guide](docs/live_trading.md) for detailed setup instructions.

## Development Tools

### Neovim with NvChad

This dev container comes with Neovim installed and configured with NvChad, a modern Neovim configuration. Neovim is bound to the `vim` command, so you can simply type `vim` in the terminal to use it.

To learn more about NvChad, visit the [official documentation](https://nvchad.com/docs/quickstart/install).

## Included Libraries and Tools

The development container provides a rich environment with numerous libraries and tools for quantitative trading, data analysis, and general development. This includes tools from the base image (`quantconnect/lean:foundation`), the `Dockerfile`, the `.devcontainer/devcontainer.json`, and the `requirements.txt` file.

**VS Code Extensions:**
- ms-python.python
- ms-python.vscode-pylance
- ms-toolsai.jupyter
- ms-vscode.vscode-typescript-next
- augment.vscode-augment
- rooveterinaryinc.roo-cline
- github.copilot

**System Packages:**
- sudo
- zsh
- git
- nano
- less
- wget
- curl
- build-essential
- ninja-build
- gettext
- cmake
- unzip
- r-base
- pandoc
- nodejs

**Python Packages:**
- uv
- pytest
- black
- isort
- pylint
- jupyterlab
- nautilus_trader
- pandas-ta
- xgboost
- datafusion
- statsmodels
- numpy
- cython
- pandas
- scipy
- wrapt
- astropy
- beautifulsoup4
- dill
- jsonschema
- lxml
- msgpack
- numba
- xarray
- plotly
- ipywidgets
- jupyterlab-widgets
- tensorflow
- docutils
- gensim
- keras
- lightgbm
- nltk
- graphviz
- cmdstanpy
- copulae
- featuretools
- PuLP
- pymc
- rauth
- scikit-learn
- scikit-optimize
- aesara
- tsfresh
- tslearn
- tweepy
- PyWavelets
- umap-learn
- fastai
- arch
- copulas
- cufflinks
- gym
- deap
- pykalman
- cvxpy
- pyro-ppl
- sklearn-json
- dtw-python
- gluonts
- gplearn
- jax
- pennylane
- PennyLane-Lightning
- pennylane-qiskit
- mplfinance
- hmmlearn
- ta
- seaborn
- optuna
- findiff
- sktime
- hyperopt
- bayesian-optimization
- matplotlib
- sdeint
- pandas_market_calendars
- ruptures
- simpy
- scikit-learn-extra
- ray
- ray[tune]
- ray[rllib]
- ray[data]
- ray[train]
- fastText
- h2o
- prophet
- Riskfolio-Lib
- torch
- torchvision
- ax-platform
- alphalens-reloaded
- pyfolio-reloaded
- altair
- modin
- persim
- ripser
- pydmd
- EMD-signal
- spacy
- pytorch-ignite
- tensorly
- mlxtend
- shap
- lime
- mpmath
- polars
- stockstats
- QuantStats
- hurst
- numerapi
- pymdptoolbox
- panel
- hvplot
- py-heat
- py-heat-magic
- bokeh
- river
- stumpy
- pyvinecopulib
- ijson
- jupyter-resource-usage
- injector
- openpyxl
- xlrd
- mljar-supervised
- dm-tree
- lz4
- ortools
- py_vollib
- thundergbm
- yellowbrick
- livelossplot
- gymnasium
- interpret
- DoubleML
- jupyter-bokeh
- imbalanced-learn
- openai
- lazypredict
- darts
- fastparquet
- tables
- dimod
- dwave-samplers
- python-statemachine
- pymannkendall
- Pyomo
- gpflow
- pyarrow
- dwave-ocean-sdk
- chardet
- stable-baselines3
- Shimmy
- FixedEffectModel
- transformers
- langchain
- pomegranate
- MAPIE
- mlforecast
- x-transformers
- Werkzeug
- nolds
- feature-engine
- pytorch-tabnet
- opencv-contrib-python-headless
- POT
- alibi-detect
- datasets
- scikeras
- contourpy
- iisignature

**Other Tools/Libraries:**
- dotnet 9 sdk & runtime
- miniconda
- java runtime (jdk-17.0.12)
- dwave tool
- ipopt solver
- oh-my-zsh
- Tini
- ipykernel_launcher
- NLTK data (punkt, punkt_tab, vader_lexicon, stopwords, wordnet)
- Pyrb
- SSM
- uni2ts
- chronos-forecasting
- matplotlib fonts

## License

This project is licensed under the GNU Lesser General Public License v3.0 - see the LICENSE file for details.

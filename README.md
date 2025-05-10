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
  - `nautilus/`: Documentation for the Nautilus Trader library (auto-generated)
- `scripts/`: Utility scripts
- `src/`: Source code
  - `execution/`: Execution algorithms
  - `indicators/`: Technical indicators
  - `strategies/`: Trading strategies
  - `notebooks/`: Jupyter notebooks

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

### Live Trading

To run a live trading node:

```bash
python src/main_live.py --config path/to/config.yaml
```

For paper trading:

```bash
python src/main_live.py --config path/to/config.yaml --paper
```

## Development Tools

### Neovim with NvChad

This dev container comes with Neovim installed and configured with NvChad, a modern Neovim configuration. Neovim is bound to the `vim` command, so you can simply type `vim` in the terminal to use it.

To learn more about NvChad, visit the [official documentation](https://nvchad.com/docs/quickstart/install).

## License

This project is licensed under the GNU Lesser General Public License v3.0 - see the LICENSE file for details.

# Nautilus Playground Project Context

## 1. Nautilus Trader Overview

Nautilus Trader is an open-source, high-performance, production-grade algorithmic trading platform that enables:

- Backtesting portfolios of automated trading strategies on historical data with an event-driven engine
- Deploying those same strategies live with no code changes
- Supporting Python-native, mission-critical trading systems
- Trading across multiple asset classes and venues simultaneously

The platform is designed with an AI-first approach, prioritizing software correctness and safety at the highest level.

### Key Features

- **Fast**: Core written in Rust with asynchronous networking
- **Reliable**: Type safety and thread safety through Rust
- **Portable**: OS independent (Linux, macOS, Windows)
- **Flexible**: Modular adapters for any REST API or WebSocket stream
- **Advanced**: Supports various order types, time in force options, and execution instructions

### Core Concepts

1. **Environment Contexts**:
   - **Backtest**: Historical data with simulated venues
   - **Sandbox**: Real-time data with simulated venues
   - **Live**: Real-time data with live venues (paper trading or real accounts)

2. **Actors**: Base components for interacting with the trading system
   - Event subscription and handling
   - Market data reception
   - State management

3. **Strategies**: Inherit from Actors and add order management capabilities
   - Define trading logic
   - Manage orders and positions
   - Process market data

4. **Execution**: Components involved in order execution
   - Strategy → OrderEmulator → ExecAlgorithm → RiskEngine → ExecutionEngine → ExecutionClient
   - Support for execution algorithms like TWAP (Time-Weighted Average Price)

5. **Data Types**:
   - OrderBookDelta, QuoteTick, TradeTick, Bar, etc.
   - Custom data types can be created

## 2. Nautilus Playground Purpose

The Nautilus Playground project aims to create a cohesive, self-contained environment for:
- Prototyping trading strategies
- Testing implementations
- Demonstrating capabilities of the Nautilus Trader library

It serves as a standard scaffold for developers, architects, and quant researchers to build, extend, and evaluate algorithmic strategies.

## 3. Implementation Context

### Project Structure

The project follows a clear directory structure:
- `.ai/`: AI assistant artifacts and drafts
- `.roo/`: Orchestration and toolchain metadata
- `data/`: Local data catalog for reproducible datasets
- `nautilus/`: Core Nautilus Trader docs and examples
- `src/`: Sample implementations (execution, indicators, strategies, notebooks)
- `scripts/`: Utility scripts

### Key Components to Implement

1. **Sample Execution Algorithms** (`src/execution/`):
   - Implement algorithms like TWAP
   - Demonstrate order splitting and execution timing

2. **Sample Indicators** (`src/indicators/`):
   - Technical indicators (e.g., moving averages, RSI)
   - Custom indicators for specific trading strategies

3. **Sample Strategies** (`src/strategies/`):
   - Complete strategy implementations
   - Demonstrate different trading approaches (trend following, mean reversion, etc.)

4. **Jupyter Notebooks** (`src/notebooks/`):
   - Interactive exploration of strategies
   - Visualization of backtest results

5. **Entry Points**:
   - `main_live.py`: Live trading node with paper trading support
   - `main_backtest.py`: Backtesting node
   - `run_example.py`: Runner for Nautilus examples with mocks

6. **Data Management**:
   - Local catalog for reproducible datasets
   - Data download script for Binance sample data

### Development Environment

The project uses a VS Code Dev Container with:
- Python 3.12
- Docker
- Neovim with NvChad configuration

## 4. Technical Requirements

### Dependencies

- Python 3.8+ environment
- Git
- Docker (optional for sandbox)
- Jupyter Lab/Notebook

### Installation Options

1. **From PyPI**: Using pip to install the latest release
2. **From Source**:
   - Install Rust toolchain
   - Clone the repository
   - Build from source

### Testing Approach

- Scaffold directory structure validation
- Sample modules import and execution testing
- Data download and catalog load testing
- Entry point scripts error handling

## 5. Implementation Challenges

1. **Dependency Management**:
   - Upstream Nautilus Trader changes may break integration
   - Solution: Pin versions and automate upgrade tests

2. **Data Availability**:
   - External API rate limits
   - Solution: Cache data in local catalog

3. **Complexity Balance**:
   - Too many sample modules may confuse users
   - Solution: Curate examples and document purpose

## 6. Next Steps

1. Establish the directory structure
2. Clone and integrate Nautilus Trader docs and examples
3. Implement sample components (execution algorithms, indicators, strategies)
4. Create Jupyter notebooks for exploration
5. Develop entry point scripts
6. Set up data management and download scripts
7. Document workflows and configuration

This context document provides the foundation for understanding and implementing the Nautilus Playground project as specified in the draft.md file.

# Nautilus Playground Project Structure

# 1. Overview

**Project Name**  
Nautilus Playground

**Purpose**  
Provide a cohesive, self-contained environment for prototyping, testing, and demonstrating trading strategies built atop the Nautilus Trader library.

**Scope**  
• Houses core Nautilus Trader code (docs + examples) alongside project-specific sample implementations.  
• Offers entry points for both live and backtesting workflows.  
• Includes utilities for data ingestion, mocking, and example orchestration.  
• Serves as a standard scaffold for developers and architects to build, extend, and evaluate algorithmic strategies.

**Intended Audience**  
• Solution architects (task breakdown)  
• Development teams (implementation of modules)  
• Quant researchers (strategy prototyping)  

---

# 2. Objectives

## 2.1 Functional Objectives  
1. **Project Scaffold**  
   – Establish a clear directory layout (`.ai`, `.roo`, `data`, `nautilus`, `src`, `scripts`).  
2. **Nautilus Integration**  
   – Clone and surface the official Nautilus Trader repo under `nautilus/` (docs + examples).  
3. **Sample Components**  
   – Provide sample execution algorithms, indicators, and strategies in `src/`.  
   – Deliver Jupyter notebooks for exploration in `src/notebooks/`.  
4. **Entry Points**  
   – `main_live.py`: live (and paper) trading node.  
   – `main_backtest.py`: backtesting node.  
   – `run_example.py`: mock-enabled runner for Nautilus examples, leveraging the local data catalog.  
5. **Data Management**  
   – Local catalog under `data/catalog/` for reproducible datasets.  
   – `scripts/download_data.py` to fetch Binance sample data.  
6. **Orchestration & Metadata**  
   – `.roo/orchestrator.md` for high-level workflow instructions.  
   – `.roo/mcp.json` for tool-chain configuration.

## 2.2 Non-functional Objectives  
• **Modularity & Extensibility**: Ensure each component can be independently developed and tested.  
• **Reproducibility**: Use a local data catalog and mocks so examples run consistently.  
• **Onboarding**: Maintain clear docs and consistent naming to accelerate new-developer setup.  
• **Maintainability**: Enforce coding standards and directory conventions for long-term evolution.

/workspaces/nautilus-playground/
├── .ai
│   ├── docs
│   ├── prompt
│   └── spec
├── .roo
│   ├── orchestrator.md
│   └── mcp.json
├── data
│   └── catalog
├── nautilus // Clone the nautilus_trader repo from https://github.com/nautechsystems/nautilus_trader in /workspaces/nautilus_trader; Copy the docs and examples folders from /workspaces/nautilus_trader to /workspaces/nautilus-playground/nautilus.
│   ├── docs
│   └── examples
├── src                        
│   ├── execution               // Sample execution algorithms
│   ├── indicators              // Sample indicator implementations
│   ├── notebooks               // Sample Jupyter notebooks
│   ├── strategies              // Sample strategy implementations
│   ├── main_live.py            // Live TradingNode entry point. Should support also paper trading with param
│   ├── main_backtest.py        // BacktestNode entry point
│   └── run_example.py          // Example runner script for the examples in the nautilus/examples folder. Create mocks so the examples can their reqired data from the repo in the /workspaces/nautilus_trader/ folder. Use the local datacatalog in /workspaces/nautilus-playground/data/catalog when a Catalog is needed.
└── scripts
    └── download_data.py         // Data required data for the samplestrategies from Binance

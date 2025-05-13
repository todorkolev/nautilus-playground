# Mean Reversion Strategy Specification

## 1. Executive Summary

### 1.1 Problem Statement

Financial markets often exhibit mean-reverting behavior interspersed with strong trends.
Maintaining a robust automated strategy requires detecting stationary regimes, applying grid trading,
and shifting to trend following when appropriate.

### 1.2 Business Objectives and Success Criteria

- Identify mean-reverting price regimes reliably using statistical tests.
- Execute an Ornstein-Uhlenbeck based grid trading strategy during stationary markets.
- Deploy a machine learning model to predict trend continuation when extreme deviations occur.
- Seamlessly switch to trend following with trailing stops to capture emerging trends.
- Achieve target backtest Sharpe ratio > 1.0 and maximum drawdown < 10%.

### 1.3 Target Users and Key Use Cases

- Quantitative researchers configuring and tuning strategies.
- Algorithmic traders executing automated strategies via Nautilus Trader.
- Risk managers monitoring strategy performance and regime switches.

## 2. User Stories and Use Cases

### 2.1 User Stories

- As a quantitative researcher, I want to test for stationarity using the ADF test so that I can detect mean-reverting regimes.
- As a trader, I want an OU-based grid trading strategy so that I can profit from price deviations around the mean.
- As a data scientist, I want to train and use a trend prediction model when prices deviate significantly so that I can avoid adverse positions.
- As a risk manager, I want automatic regime switching to trend following with trailing stops so that risk is controlled during strong trends.

### 2.2 Use Case Scenarios

**Use Case 1: Backtesting Mean Reversion**
**Actor:** Quantitative researcher
**Preconditions:** Historical data loaded for specified symbols and timeframes.
**Success Path:**
1. Run `main_backtest.py` with strategy=mean_reversion.
2. Strategy performs ADF test and OU estimation.
3. Grid trades executed when price deviates within threshold.
4. Backtest results generated with performance metrics.
**Alternative Flow:** ADF test indicates non-stationarity → Strategy logs and skips grid entry.

**Use Case 2: Live Trading with Regime Switching**
**Actor:** Algorithmic trader
**Preconditions:** Strategy configured in Nautilus Trader, live market data stream connected.
**Success Path:**
1. Strategy monitors price and ADX filters.
2. Upon deviation > 2×σ, ML model predicts trend continuation.
3. If trend predicted, close losing grid positions and open trend position with trailing stop.
4. Continue monitoring and adjust stops.
**Exception Scenario:** ML model confidence below threshold → maintain grid positions.

## 3. Functional Requirements

### 3.1 Stationarity Detection

- Perform Augmented Dickey-Fuller (ADF) test on defined lookback window (configurable, default=168).
- Record p-value and test statistic; require p-value < 0.05 to confirm stationarity.

### 3.2 Ornstein-Uhlenbeck Model Estimation

- Estimate OU parameters θ (speed of mean reversion), μ (long-run mean), and σ (volatility).
- Use maximum likelihood estimation over the lookback period.

### 3.3 Grid Trading Execution

- Deploy grid orders at levels defined by μ ± n×σ for n=1..positions_per_side (default=3).
- Fixed take profit levels at μ ± k×σ × take_profit_std_dev_multiplier.
- Fixed stop loss levels at μ ± k×σ × stop_loss_std_dev_multiplier.
- Manage order placement and cancellation via Nautilus Trader API.

### 3.4 Machine Learning Trend Prediction

- Trigger model training when price deviation > 2×σ.
- Input features: OU parameters, statistical indicators (ADX, RSI, Bollinger Bands), recent returns.
- Model options: logistic regression or decision tree (configurable).
- Evaluate model probability; require confidence > threshold (configurable, default=0.6) to predict trend continuation.

### 3.5 Regime Switching Logic

- If ML predicts trend continuation:
  - Close all open grid positions.
  - Open new position in direction of predicted trend.
  - Use trailing stop loss based on trailing_stop_pct (default=0.5%).

### 3.6 Configuration and Integration

- Expose all parameters in `config.yaml` under `mean_reversion`.
- Integrate strategy into `main_backtest.py` and `main_live.py` entrypoints.
- Provide CLI flags: `--strategy mean_reversion`, `--start-date`, `--end-date`.

## 4. Non-Functional Requirements

### 4.1 Performance

- Backtest execution time per 1-year dataset < 30 seconds per symbol.
- Live trading latency from signal to order < 100 ms.

### 4.2 Scalability

- Support multiple symbols in parallel via multi-threading or async architecture.

### 4.3 Reliability

- Ensure idempotent order management; handle API failures with retries (max 3 attempts).

### 4.4 Logging and Monitoring

- Log key events: ADF results, OU parameters, ML predictions, trade executions.
- Expose metrics for dashboard (e.g., Prometheus).

### 4.5 Documentation

- Update `docs/strategies.md` with details.
- Provide examples in README and notebooks.

## 5. User Experience

### 5.1 Configuration Interface

- Structured YAML config with clear comments and defaults.
- Validate parameter ranges at startup.

### 5.2 Command Line Interface

- Provide `--strategy mean_reversion` flag.
- Clear help output for strategy-specific parameters.

### 5.3 Reporting

- Output backtest summary including Sharpe, MDD, total P&L.
- Generate performance plots (price vs equity, drawdown).

## 6. Implementation Guidelines

### 6.1 Phasing and Prioritization

- Phase 1: ADF and OU grid trading core functionality.
- Phase 2: ML model integration and regime switching.
- Phase 3: Performance optimizations and documentation.

### 6.2 Dependencies and Prerequisites

- Nautilus Trader SDK 1.x.
- Python 3.9+ with packages: pandas, numpy, statsmodels, scikit-learn.

### 6.3 Suggested Technical Approach

- Leverage existing `src/strategies/mean_reversion/strategy.py` as base.
- Modularize ML logic in `src/strategies/mean_reversion/ml_model.py`.
- Extend `position_management.py` with static grid and trailing stop classes.

### 6.4 Code Structure and Integration

- New directory `.ai/spec/mean_reversion_strategy` for spec.
- Ensure tests in `tests/strategies/test_mean_reversion.py`.

## 7. Testing and Validation

### 7.1 Unit Testing

- Test `run_adf_test` with synthetic AR(1) data generating known p-values.
- Test `estimate_ou_parameters` against simulated OU processes.
- Located in [`tests/strategies/test_mean_reversion.py`](../../tests/strategies/test_mean_reversion.py:1)

### 7.2 Integration Testing

- End-to-end backtest with deterministic sample data to verify outputs.

### 7.3 Backtesting Scenarios

- Range-bound market simulation.
- Trending market simulation.
- Choppy market simulation.

### 7.4 Regression and Performance Testing

- Ensure performance stays within SLAs after changes.
- Automate backtest in CI pipeline.

## 8. Risks and Challenges

### 8.1 Model Reliability

- Risk of false stationarity detection; mitigate with parameter tuning.

### 8.2 Market Regime Changes

- Sudden regime shifts may lead to losses; implement safe-exit logic.

### 8.3 Data Quality and Latency

- Incomplete or delayed data can affect decisions; include data validation.

### 8.4 Technical Limitations

- Python GIL may limit parallelism; consider async or multi-process.
# Live Trading with Binance

This document explains how to set up and run live trading with Binance using the Nautilus Playground.

## Prerequisites

1. A Binance account with API access
2. Python 3.8+ with the required dependencies
3. The `python-dotenv` package for loading environment variables

## Setup

### 1. Install Dependencies

Make sure you have the required dependencies installed:

```bash
pip install python-dotenv
```

### 2. Create API Keys

1. Log in to your Binance account
2. Navigate to API Management
3. Create a new API key
4. Set appropriate permissions (read info, spot & margin trading)
5. Save your API key and secret

### 3. Configure Environment Variables

Create a `.env` file in the project root directory based on the provided `.env.example`:

```bash
cp .env.example .env
```

Edit the `.env` file and set your Binance API credentials:

```
# Binance API credentials
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# Account type: spot, margin, usdt_future, coin_future
BINANCE_ACCOUNT_TYPE=spot

# Set to true to use Binance Testnet (for testing without real funds)
BINANCE_TESTNET=false

# Set to true if using Binance US instead of global Binance
BINANCE_US=false

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
```

## Running Live Trading

### Basic Usage

To run live trading with the default configuration:

```bash
python src/main_live.py
```

### Paper Trading

To run in paper trading mode (using the Binance testnet):

```bash
python src/main_live.py --paper
```

### Custom Configuration

To use a custom configuration file (if you create one):

```bash
python src/main_live.py --config path/to/config.yaml
```

Note: For most use cases, using environment variables via the `.env` file is sufficient.

### Setting Log Level

To change the logging level:

```bash
python src/main_live.py --log-level DEBUG
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BINANCE_API_KEY` | Your Binance API key | None |
| `BINANCE_API_SECRET` | Your Binance API secret | None |
| `BINANCE_ACCOUNT_TYPE` | Account type (spot, margin, usdt_future, coin_future) | spot |
| `BINANCE_TESTNET` | Use Binance testnet (true/false) | false |
| `BINANCE_US` | Use Binance US (true/false) | false |
| `BINANCE_BASE_URL_HTTP` | Custom HTTP endpoint | None |
| `BINANCE_BASE_URL_WS` | Custom WebSocket endpoint | None |
| `LOG_LEVEL` | Logging level | INFO |

### Advanced Configuration

For most use cases, configuring through environment variables in the `.env` file is sufficient.

If you need more advanced configuration options, you can create a custom YAML configuration file and pass it to the `--config` parameter. Refer to the [Nautilus Trader documentation](https://nautilustrader.io/docs/) for details on the configuration format.

## Troubleshooting

### API Key Issues

If you encounter API key errors:

1. Verify your API key and secret are correct
2. Check that your API key has the necessary permissions
3. Ensure your IP address is whitelisted in Binance API settings

### Connection Issues

If you have connection problems:

1. Check your internet connection
2. Verify that Binance services are operational
3. If using a VPN, try disabling it or changing servers

### Testnet Issues

If you're having trouble with the testnet:

1. Create separate API keys specifically for the testnet at https://testnet.binance.vision/
2. Set `BINANCE_TESTNET=true` in your `.env` file
3. Note that the testnet has limited functionality compared to the live environment

## Resources

- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Nautilus Trader Documentation](https://nautilustrader.io/docs/)

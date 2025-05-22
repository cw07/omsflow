# OMSFlow - Financial Order Management System Framework

A robust Python framework for managing financial orders with multi-source order consumption, FIX message construction, and comprehensive monitoring capabilities.

## Features

- **Multi-source Order Consumption**
  - SQL Server backend integration
  - Redis stream/queue support
  - Extensible architecture for new data sources

- **Order Processing**
  - FIX message generation with template patterns
  - Dynamic field mapping based on broker reference data
  - Comprehensive validation engine
    - Price/Volume checks
    - Portfolio-level risk limits
    - Customizable validation rules

- **Execution System Integration**
  - Abstract broker interface
  - Support for Phoenix Order System and Futu platform
  - Order submission, status checks, and bulk cancellation
  - Broker-specific configuration management

- **Monitoring & Lifecycle Management**
  - Adaptive status polling
  - Robust failure handling
  - Dead letter queue integration
  - Alert system integration

## Requirements

- Python 3.12 or higher
- SQL Server
- Redis
- QuickFIX
- Phoenix API access
- Futu API access

## Installation

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

## Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
black .
mypy .
```

## Project Structure

```
omsflow/
├── src/
│   └── omsflow/
│       ├── core/           # Core framework components
│       ├── sources/        # Order source implementations
│       ├── validation/     # Order validation engine
│       ├── execution/      # Broker execution systems
│       ├── monitoring/     # Monitoring and lifecycle
│       └── utils/          # Utility functions
├── tests/                  # Test suite
├── pyproject.toml         # Project configuration
└── README.md             # This file
```

## License

MIT License
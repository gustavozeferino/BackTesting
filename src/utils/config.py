from pathlib import Path

# Project Root (two levels up from src/utils/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / 'data'

# Database configuration
DB_NAME = 'backtesting.db'
DB_PATH = DATA_DIR / DB_NAME

# Default settings
DEFAULT_TABLE_NAME = 'trading_data'

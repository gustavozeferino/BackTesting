import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directories
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Database configuration
DB_NAME = 'backtesting.db'
DB_PATH = os.path.join(DATA_DIR, DB_NAME)

# Default settings
DEFAULT_TABLE_NAME = 'trading_data'

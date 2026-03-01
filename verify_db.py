import pandas as pd
import os
import config
from db_manager import upload_excel_to_sqlite, load_from_sqlite_to_pandas

# 1. Create Mock Data
mock_data = {
    'Data': ['05/01/2026 09:03', '05/01/2026 09:04'],
    'Opem': [163160, 163220],
    'Max': [163310, 163400],
    'Min': [163065, 163200],
    'Close': [163220, 163350],
    'MME52': [162825.61, 162830.00],
    'VWAP': [163178.92, 163200.00],
    'Contador': [1, 2],
    'StopATR3': [162803, 162810],
    'LinhaQuant': [162950.5, 162960.0],
    'OBV': [12427.18, 12500.00],
    'OBVMME52': [12344.98, 12350.00],
    'OBVMME200': [12325.95, 12330.00]
}

df_mock = pd.DataFrame(mock_data)
excel_path = os.path.join(config.DATA_DIR, 'test_data.xlsx')
db_path = config.DB_PATH

# Ensure data directory exists
if not os.path.exists(config.DATA_DIR):
    os.makedirs(config.DATA_DIR)

# Save mock to Excel
df_mock.to_excel(excel_path, index=False)
print(f"Mock Excel created at {excel_path}")

# 2. Test Upload Routine
try:
    upload_excel_to_sqlite(excel_path, db_path)
except Exception as e:
    print(f"Error during upload: {e}")

# 3. Test Load Routine
try:
    df_loaded = load_from_sqlite_to_pandas(db_path)
    print("\nLoaded DataFrame Head:")
    print(df_loaded.head())
    print("\nDataFrame Types:")
    print(df_loaded.dtypes)
    
    # Simple validation
    if len(df_loaded) == 2:
        print("\nVerification SUCCESS: Data correctly uploaded and loaded.")
    else:
        print("\nVerification FAILED: Row count mismatch.")
except Exception as e:
    print(f"Error during loading: {e}")

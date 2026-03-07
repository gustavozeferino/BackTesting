import pandas as pd
import sqlite3
import os
import config

def upload_excel_to_sqlite(excel_path, db_path=None, table_name=config.DEFAULT_TABLE_NAME):
    """
    Reads an Excel file and uploads its content to a SQLite database.
    
    Args:
        excel_path (str): Path to the Excel file.
        db_path (str, optional): Path to the SQLite database file. Defaults to config.DB_PATH.
        table_name (str): Name of the table to create/append to.
    """
    if db_path is None:
        db_path = config.DB_PATH

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found at: {excel_path}")
    
    # Read the Excel file
    df = pd.read_excel(excel_path)
    
    # Ensure date column is datetime objects
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    
    try:
        # Save to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Successfully uploaded {len(df)} rows to {table_name} in {db_path}")
    finally:
        conn.close()

def load_from_sqlite_to_pandas(db_path=None, table_name=config.DEFAULT_TABLE_NAME):
    """
    Loads data from a SQLite database table into a Pandas DataFrame.
    
    Args:
        db_path (str, optional): Path to the SQLite database file. Defaults to config.DB_PATH.
        table_name (str): Name of the table to read from.
        
    Returns:
        pd.DataFrame: The loaded data.
    """
    if db_path is None:
        db_path = config.DB_PATH

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    
    try:
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        
        # Ensure date column is datetime again if needed
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'])
            
        print(f"Successfully loaded {len(df)} rows from {table_name}")
        return df
    finally:
        conn.close()

def remover_duplicatas_sqlite(db_path=None, table_name=config.DEFAULT_TABLE_NAME):
    """
    Remove linhas duplicadas de uma tabela SQLite mantendo o registro original.
    Considera duplicatas linhas que possuem todos os valores iguais.
    """
    if db_path is None:
        db_path = config.DB_PATH

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Contar total antes
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_antes = cursor.fetchone()[0]

        # 2. Executar a remoção baseada no ROWID
        # Esta query deleta todas as linhas cujo ROWID não seja o MENOR 
        # para aquele grupo de valores idênticos.
        query_delete = f"""
            DELETE FROM {table_name}
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM {table_name}
                GROUP BY Data, Open, Max, Min, Close, MME52, VWAP, Contador, StopATR3, LinhaQuant, OBV, OBVMME52, OBVMME200
            )
        """
        
        cursor.execute(query_delete)
        linhas_removidas = cursor.rowcount
        
        # 3. Commitar e Otimizar o arquivo do banco (opcional mas recomendado)
        conn.commit()
        cursor.execute("VACUUM") 
        
        print(f"--- Limpeza Concluída ---")
        print(f"Registros processados: {total_antes}")
        print(f"Linhas duplicadas removidas: {linhas_removidas}")
        print(f"Registros restantes: {total_antes - linhas_removidas}")

        conn.close()
        return linhas_removidas

    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")
        return 0        


if __name__ == "__main__":
    # Example usage using the real file provided by the user previously
    excel_file = os.path.join(config.DATA_DIR, 'WIN_2026_TF1.xlsx')
    if os.path.exists(excel_file):
        upload_excel_to_sqlite(excel_file)
        df = load_from_sqlite_to_pandas()
        print(df.head())
        remover_duplicatas_sqlite(db_path=None, table_name=config.DEFAULT_TABLE_NAME)
    else:
        print(f"File not found for auto-execution: {excel_file}")


import pandas as pd
import sqlite3
import os
import config

def upload_excel_to_sqlite(excel_path, db_path=None, table_name=None):
    """
    Lê Excel, calcula sinais de Compra/Venda e salva no SQLite.
    """
    import config # Garantindo que o config seja acessado
    
    if db_path is None:
        db_path = config.DB_PATH
    if table_name is None:
        table_name = config.DEFAULT_TABLE_NAME

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Arquivo Excel não encontrado: {excel_path}")
    
    # 1. Carga dos dados
    df = pd.read_excel(excel_path)
    
    # 2. Tratamento de Data e Ordenação (Essencial para o shift de sinais)
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    
    df = df.sort_values('Data').reset_index(drop=True)

    # 3. Processamento de Sinais (Lógica que estava no seu main)
    # Criando o Status de Quadrante (SQD)
    df['SQD'] = '' 
    df.loc[df['Close'] > df['LinhaQuant'], 'SQD'] = 'C'
    df.loc[df['Close'] < df['LinhaQuant'], 'SQD'] = 'V'
    
    # Criando o Sinal de Cruzamento (Sinal)
    df['Sinal'] = 0
    # Cruzamento para Cima: Agora é C e antes era V
    df.loc[(df['SQD'] == 'C') & (df['SQD'].shift(1) == 'V'), 'Sinal'] = 1
    # Cruzamento para Baixo: Agora é V e antes era C
    df.loc[(df['SQD'] == 'V') & (df['SQD'].shift(1) == 'C'), 'Sinal'] = -1
    
    # 4. Persistência no SQLite
    conn = sqlite3.connect(db_path)
    try:
        # Usamos replace para garantir que a tabela tenha as novas colunas
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # 5. Otimização: Criar índice na coluna Data para acelerar o backtest
        cursor = conn.cursor()
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_data ON {table_name} (Data)")
        
        print(f"✅ Sucesso: {len(df)} linhas processadas e salvas em {table_name}.")
        print(f"📊 Colunas geradas: SQD e Sinal (Baseadas na LinhaQuant).")
        
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


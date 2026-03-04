import pandas as pd
import numpy as np

def analisar_stop_otimo(lista_trades, stops=range(50, 301, 25)):
    if not lista_trades: return pd.DataFrame(), None, {}
    df = pd.DataFrame([t.to_dict() for t in lista_trades])
    
    resultados = []
    
    for stop in stops:
        # Se o MAE absoluto for maior ou igual ao stop testado, saiu no stop.
        # df['mae'] é negativo (pontos contra). abs(df['mae']) > stop testa a violação
        atingiu_stop = df['mae'].abs() >= stop
        
        # O novo resultado é -stop_testado para os que bateram no stop, original pros outros
        pontos_simulados = np.where(atingiu_stop, -stop, df['pontos'])
        
        total_pontos = pontos_simulados.sum()
        vitorias = pontos_simulados[pontos_simulados > 0]
        derrotas = pontos_simulados[pontos_simulados <= 0]
        
        win_rate = (len(vitorias) / len(pontos_simulados)) * 100
        soma_ganhos = vitorias.sum()
        soma_perdas = abs(derrotas.sum())
        profit_factor = soma_ganhos / soma_perdas if soma_perdas > 0 else float('inf')
        expected_value = total_pontos / len(pontos_simulados)
        
        resultados.append({
            'stop': stop,
            'total_pontos': round(total_pontos, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else float('inf'),
            'win_rate': round(win_rate, 2),
            'expected_value': round(expected_value, 2)
        })
    
    res_df = pd.DataFrame(resultados)
    melhor_stop = res_df.loc[res_df['profit_factor'].idxmax(), 'stop'] if not res_df.empty else None
    
    mae_abs = df['mae'].abs()
    percentis = {
        'P25': round(mae_abs.quantile(0.25), 2),
        'P50': round(mae_abs.quantile(0.50), 2),
        'P75': round(mae_abs.quantile(0.75), 2),
        'P90': round(mae_abs.quantile(0.90), 2),
        'P95': round(mae_abs.quantile(0.95), 2)
    }
    
    return res_df, melhor_stop, percentis


def analisar_parcial_otima(lista_trades, niveis=range(50, 301, 25), pct_parcial=0.5):
    if not lista_trades: return pd.DataFrame(), None
    df = pd.DataFrame([t.to_dict() for t in lista_trades])
    
    resultados = []
    for nivel in niveis:
        # Se trade.mfe >= nivel, realiza parcial
        fez_parcial = df['mfe'] >= nivel
        
        # O novo resultado pesa o nivel com pct_parcial, mais o resultado_original 
        # para o resto dos contratos. Se o resultado_original bateu MFE mas voltou e 
        # fechou pior, ele ganha a parcial mas perde o resto (ou ganha o resto original).
        # A conta: (nivel * pct_parcial) + (resultado_original * (1 - pct_parcial))
        simulacao = np.where(fez_parcial, 
                             (nivel * pct_parcial) + (df['pontos'] * (1 - pct_parcial)),
                             df['pontos'])
        
        total_pontos = simulacao.sum()
        expected_value = total_pontos / len(simulacao)
        pct_trades = (fez_parcial.sum() / len(simulacao)) * 100
        
        resultados.append({
            'nivel': nivel,
            'expected_value': round(expected_value, 2),
            'total_pontos': round(total_pontos, 2),
            'pct_trades_com_parcial': round(pct_trades, 2)
        })
        
    res_df = pd.DataFrame(resultados)
    melhor_nivel = res_df.loc[res_df['expected_value'].idxmax(), 'nivel'] if not res_df.empty else None
    
    return res_df, melhor_nivel


def analisar_breakeven_otimo(lista_trades, valores=range(100, 500, 50)):
    if not lista_trades: return pd.DataFrame(), None
    df = pd.DataFrame([t.to_dict() for t in lista_trades])
    
    resultados = []
    for be in valores:
        # Se mfe >= be_testado, break-even atingido, ou seja, pior cenário é 0 pontos (ou mantém positivo)
        atingiu_be = df['mfe'] >= be
        
        # Max(resultado_original, 0) apenas se break-even for atingido
        pontos_simulados = np.where(atingiu_be, df['pontos'].clip(lower=0), df['pontos'])
        
        # Trades salvos = qtde de trades que atingiram BE mas o original era < 0
        salvos = (atingiu_be & (df['pontos'] < 0)).sum()
        
        total_pontos = pontos_simulados.sum()
        vitorias = pontos_simulados[pontos_simulados > 0]
        derrotas = pontos_simulados[pontos_simulados <= 0]
        soma_ganhos = vitorias.sum()
        soma_perdas = abs(derrotas.sum())
        profit_factor = soma_ganhos / soma_perdas if soma_perdas > 0 else float('inf')
        
        resultados.append({
            'breakeven_pts': be,
            'total_pontos': round(total_pontos, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else float('inf'),
            'trades_salvos': salvos
        })
        
    res_df = pd.DataFrame(resultados)
    melhor_breakeven = res_df.loc[res_df['profit_factor'].idxmax(), 'breakeven_pts'] if not res_df.empty else None
    
    return res_df, melhor_breakeven

def resumo_analises(lista_trades):
    if not lista_trades:
        print("Sem trades para analisar.")
        return
        
    print("\n" + "="*50)
    print("ANÁLISE DE PARÂMETROS".center(50))
    print("="*50)
    
    df_stop, melhor_stop, perc = analisar_stop_otimo(lista_trades)
    print(f"\n[Stop Ótimo]")
    print(f"Melhor Stop (por Profit Factor): {melhor_stop} pts")
    print(f"MAEs observados - P50: {perc['P50']}, P90: {perc['P90']}")
    
    df_parcial, melhor_parcial = analisar_parcial_otima(lista_trades, pct_parcial=0.5)
    print(f"\n[Parcial Ótima (50% do lote)]")
    print(f"Melhor Nível (por Execpted Value): {melhor_parcial} pts")
    
    df_be, melhor_be = analisar_breakeven_otimo(lista_trades)
    print(f"\n[Break-even Ótimo]")
    print(f"Melhor BE (por Profit Factor): {melhor_be} pts")
    print("="*50 + "\n")

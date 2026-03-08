import pandas as pd
import numpy as np
import math

def estatisticas_trades(lista_trades):
    """
    Função pura que recebe uma lista de objetos Trade e retorna um dicionário 
    com estatísticas completas.
    """
    if not lista_trades:
        return {
            'Total Trades': 0, 'Total Empates': 0, 'Win Rate (%)': 0, 'Profit Factor': 0,
            'Total Pontos': 0, 'Média por Trade': 0, 'Max Drawdown (Pts)': 0,
            'Maior Vitória (pts)': 0, 'Maior Derrota (pts)': 0, 'Média Vencedores (pts)': 0,
            'Média Perdedores (pts)': 0, 'Payoff Ratio': 0, 'Maior Sequência Ganhos': 0,
            'Maior Sequência Perdas': 0, 'Recovery Factor': 0, 'Sharpe Ratio': 0,
            'Sortino Ratio': 0, 'MAE mediano': 0, 'MFE mediano': 0,
            'MFE Efficiency (%)': 0, 'MAE Efficiency (%)': 0
        }

    df = pd.DataFrame([t.to_dict() for t in lista_trades])
    
    total_trades = len(df)
    vitorias = df[df['pontos'] > 0]
    derrotas = df[df['pontos'] < 0]
    empates = df[df['pontos'] == 0]
    derrotas_e_empates = df[df['pontos'] <= 0]

    win_rate = (len(vitorias) / total_trades) * 100 if total_trades > 0 else 0
    soma_ganhos = vitorias['pontos'].sum()
    soma_perdas = abs(derrotas_e_empates['pontos'].sum())
    profit_factor = soma_ganhos / soma_perdas if soma_perdas > 0 else float('inf')
    total_pontos = df['pontos'].sum()
    expectativa_matematica = total_pontos / total_trades if total_trades > 0 else 0
    
    # Drawdown
    df['saldo_acumulado'] = df['pontos'].cumsum()
    df['max_acumulado'] = df['saldo_acumulado'].cummax()
    df['drawdown'] = df['max_acumulado'] - df['saldo_acumulado']
    max_drawdown = df['drawdown'].max()

    # Mídias e Extremos
    maior_vitoria = vitorias['pontos'].max() if not vitorias.empty else 0
    maior_derrota = derrotas['pontos'].min() if not derrotas.empty else 0
    media_vencedores = vitorias['pontos'].mean() if not vitorias.empty else 0
    media_perdedores = derrotas_e_empates['pontos'].mean() if not derrotas_e_empates.empty else 0
    payoff_ratio = media_vencedores / abs(media_perdedores) if media_perdedores != 0 else float('inf')

    # Sequências
    sinais = np.sign(df['pontos']).replace(0, -1)
    blocos = (sinais != sinais.shift()).cumsum()
    contagens = df.groupby(blocos)['pontos'].apply(lambda x: (np.sign(x.iloc[0]), len(x)))
    
    maior_seq_ganhos = 0
    maior_seq_perdas = 0
    for sinal_seq, tamanho in contagens:
        if sinal_seq > 0: maior_seq_ganhos = max(maior_seq_ganhos, tamanho)
        else: maior_seq_perdas = max(maior_seq_perdas, tamanho)

    # Ratios
    recovery_factor = total_pontos / max_drawdown if max_drawdown > 0 else (float('inf') if total_pontos > 0 else 0)
    std_pontos = df['pontos'].std()
    sharpe_ratio = (df['pontos'].mean() / std_pontos * np.sqrt(252)) if std_pontos > 0 else 0
    
    std_negativos = derrotas_e_empates['pontos'].std()
    sortino_ratio = (df['pontos'].mean() / std_negativos * np.sqrt(252)) if std_negativos > 0 else 0

    # MAE/MFE
    mae_mediano = df['mae'].abs().median()
    mfe_mediano = df['mfe'].median()
    
    # Efficiency logic (from trade.py)
    vitorias_mfe_valido = vitorias[vitorias['mfe'] > 0]
    mfe_efficiency = ((vitorias_mfe_valido['pontos'] / (vitorias_mfe_valido['n_contratos'] * vitorias_mfe_valido['mfe'])) * 100).mean() if not vitorias_mfe_valido.empty else 0
    
    derrotas_mae_valido = derrotas_e_empates[derrotas_e_empates['risco'] > 0]
    mae_efficiency = (derrotas_mae_valido['mae'].abs() / (derrotas_mae_valido['n_contratos'] * derrotas_mae_valido['risco']) * 100).mean() if not derrotas_mae_valido.empty else 0

    return {
        'Total Trades': total_trades,
        'Total Empates': len(empates),
        'Win Rate (%)': win_rate,
        'Profit Factor': profit_factor,
        'Total Pontos': total_pontos,
        'Média por Trade': expectativa_matematica,
        'Max Drawdown (Pts)': max_drawdown,
        'Maior Vitória (pts)': maior_vitoria,
        'Maior Derrota (pts)': maior_derrota,
        'Média Vencedores (pts)': media_vencedores,
        'Média Perdedores (pts)': media_perdedores,
        'Payoff Ratio': payoff_ratio,
        'Maior Sequência Ganhos': maior_seq_ganhos,
        'Maior Sequência Perdas': maior_seq_perdas,
        'Recovery Factor': recovery_factor,
        'Sharpe Ratio': sharpe_ratio,
        'Sortino Ratio': sortino_ratio,
        'MAE mediano': mae_mediano,
        'MFE mediano': mfe_mediano,
        'MFE Efficiency (%)': mfe_efficiency,
        'MAE Efficiency (%)': mae_efficiency
    }

def segmentar_estatisticas(lista_trades, segmentos=None, min_trades=30, verbose=False, excel=None):
    """
    Gera estatísticas segmentadas (Lado, Mês, Dia da Semana, etc.)
    """
    if not lista_trades:
        return pd.DataFrame()

    df_base = pd.DataFrame([t.to_dict() for t in lista_trades])
    df_base['inicio'] = pd.to_datetime(df_base['inicio'])
    
    # Mapeamento de nomes de colunas e transformações
    mapping = {
        'lado': ('direcao', lambda x: x),
        'mes': ('inicio', lambda x: x.dt.month_name()),
        'dia_semana': ('inicio', lambda x: x.dt.day_name()),
        'semana_ano': ('inicio', lambda x: x.dt.isocalendar().week),
        'hora': ('inicio', lambda x: x.dt.hour.astype(str) + 'h')
    }

    if segmentos is None:
        segmentos = list(mapping.keys())

    resultados = []

    # 1. Geral
    stats_geral = estatisticas_trades(lista_trades)
    row_geral = {'Segmento': 'Geral', 'Categoria': 'Geral'}
    row_geral.update(stats_geral)
    resultados.append(row_geral)

    # 2. Segmentos
    for seg in segmentos:
        if seg not in mapping: continue
        
        col_origem, transform = mapping[seg]
        df_base[seg] = transform(df_base[col_origem])
        
        grupos = df_base.groupby(seg)
        for nome_cat, indices in grupos.groups.items():
            # Pegar os objetos Trade correspondentes
            subset_trades = [lista_trades[i] for i in indices]
            count = len(subset_trades)
            
            row = {'Segmento': seg.capitalize(), 'Categoria': str(nome_cat), 'Total Trades': count}
            
            if count >= min_trades:
                stats_seg = estatisticas_trades(subset_trades)
                row.update(stats_seg)
            else:
                # Preencher com NaN ou 0 conforme pedido (mostrar apenas n_trades)
                # Vou usar None para o resto
                for key in stats_geral.keys():
                    if key != 'Total Trades':
                        row[key] = None
            
            resultados.append(row)

    df_final = pd.DataFrame(resultados)
    
    # Arredondamento para exibição no verbose/excel se necessário
    # Mas a função pede para NÃO arredondar no núcleo, somente tratar erro.
    
    if verbose:
        print("\n" + "="*80)
        print("ESTATÍSTICAS SEGMENTADAS".center(80))
        print("="*80)
        print(df_final.to_string(index=False))
        print("="*80 + "\n")

    if excel:
        df_final.to_excel(excel, index=False)
        print(f"Relatório segmentado salvo em: {excel}")

    return df_final

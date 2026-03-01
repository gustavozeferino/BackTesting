import pandas as pd
import math
from datetime import time
from db_manager import load_from_sqlite_to_pandas
from trade import Trade, gerar_relatorio_estatistico, imprimir_stats, ajustar_preco_stop, detalhar_dia


def simular_operacional(timeframe_data, verbose=False, n_contratos=1, tipo_parcial=None, valores_parciais=None):
    """
    Simula o operacional clássico (opcionalmente com parciais).
    """
    timeframe_data['Data'] = pd.to_datetime(timeframe_data['Data'])
    horario_inicial, horario_final = time(9, 15), time(17, 30)
    preco_entrada, preco_stop = 0, 0
    timeframe_data['Dia'] = timeframe_data['Data'].dt.date
    
    operacoes, trade_atual = [], None
    dias = timeframe_data['Dia'].unique()
    
    for dia in dias:
        df_dia = timeframe_data[timeframe_data['Dia'] == dia].copy()
        operacao_aberta, ordem_aberta = 0, 0
        
        for i, candle in df_dia.iterrows():
            horario_atual = candle['Data'].time()
            if trade_atual: trade_atual.update_statistics(candle)
            
            if horario_inicial <= horario_atual <= horario_final:
                sinal = candle['Sinal']
                if operacao_aberta == 0:
                    if ordem_aberta == 0:
                        if sinal == 1:
                            preco_entrada = candle['Max'] + 5
                            preco_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                            ordem_aberta = 1
                        elif sinal == -1:
                            preco_entrada = candle['Min'] - 5
                            preco_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                            ordem_aberta = -1

                    if ordem_aberta == 1:
                        if candle['SQD'] == "C":
                            if candle['Max'] >= preco_entrada:
                                operacao_aberta, trade_atual = 1, Trade(direcao=1, ponto_entrada=preco_entrada, hora_entrada=candle['Data'], ponto_stop=preco_stop, n_contratos=n_contratos, tipo_parcial=tipo_parcial, valores_parciais=valores_parciais)
                                ordem_aberta = 0
                        else: ordem_aberta = 0

                    if ordem_aberta == -1:
                        if candle['SQD'] == "V":
                            if candle['Min'] <= preco_entrada:
                                operacao_aberta, trade_atual = -1, Trade(direcao=-1, ponto_entrada=preco_entrada, hora_entrada=candle['Data'], ponto_stop=preco_stop, n_contratos=n_contratos, tipo_parcial=tipo_parcial, valores_parciais=valores_parciais)
                                ordem_aberta = 0
                        else: ordem_aberta = 0

                else:
                    # Se houver configuração de parciais, checar
                    while trade_atual.check_partial_exit(candle):
                        if verbose: print(f"{'Compra' if trade_atual.direcao==1 else 'Venda'} Parcial atingida: {trade_atual.saidas[-1][0]}")
                    
                    if trade_atual.contratos_abertos == 0:
                        trade_atual.close_trade(candle['Close'], candle['Data'])
                        operacoes.append(trade_atual)
                        if verbose: print(f"Operação finalizada por parciais. Pontos: {trade_atual.pontos_totais:.2f}")
                        operacao_aberta, trade_atual = 0, None
                        continue

                    if operacao_aberta == 1:
                        if candle['Min'] < candle['LinhaQuant']:
                            trade_atual.close_trade(ponto_saida=candle['LinhaQuant'], hora_saida=candle['Data'])
                            operacoes.append(trade_atual)
                            if verbose: print(f"Compra Finalizada: {preco_entrada} -> {candle['LinhaQuant']} | Pontos: {trade_atual.pontos}")
                            operacao_aberta, trade_atual = 0, None
                    else:
                        if candle['Max'] > candle['LinhaQuant']:
                            trade_atual.close_trade(ponto_saida=candle['LinhaQuant'], hora_saida=candle['Data'])
                            operacoes.append(trade_atual)
                            if verbose: print(f"Venda Finalizada: {preco_entrada} -> {candle['LinhaQuant']} | Pontos: {trade_atual.pontos}")
                            operacao_aberta, trade_atual = 0, None
            else:
                if trade_atual:
                    trade_atual.close_trade(ponto_saida=candle['Close'], hora_saida=candle['Data'])
                    operacoes.append(trade_atual)
                    if verbose: print(f"Operação Finalizada devido ao horário.")
                    operacao_aberta, trade_atual = 0, None

    return operacoes


def operacional_parciais(timeframe_data, verbose=False, n_contratos=3, tipo_parcial='risco', valores_parciais=None):
    """
    Simula o operacional com parciais.
    """
    if valores_parciais is None and tipo_parcial == 'risco':
        valores_parciais = [1, 2, 3] # Default para o que era antes
    timeframe_data['Data'] = pd.to_datetime(timeframe_data['Data'])
    horario_inicial, horario_final = time(9, 15), time(17, 30)
    timeframe_data['Dia'] = timeframe_data['Data'].dt.date
    
    operacoes, trade_atual = [], None
    dias = timeframe_data['Dia'].unique()
    
    for dia in dias:
        df_dia = timeframe_data[timeframe_data['Dia'] == dia].copy()
        operacao_aberta, ordem_aberta = 0, 0
        p_entrada, p_stop = 0, 0
        
        for i, candle in df_dia.iterrows():
            horario_atual = candle['Data'].time()
            if trade_atual: trade_atual.update_statistics(candle)
            
            if horario_inicial <= horario_atual <= horario_final:
                sinal = candle['Sinal']
                if operacao_aberta == 0:
                    # Sem operação aberta, verificar ordens ou sinais
                    if ordem_aberta == 0:
                        if sinal == 1:
                            p_entrada = candle['Max'] + 5
                            p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                            ordem_aberta = 1
                        elif sinal == -1:
                            p_entrada = candle['Min'] - 5
                            p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                            ordem_aberta = -1

                    # Verificar se a ordem aberta foi atingida
                    if ordem_aberta == 1:
                        if candle['SQD'] == "C":
                            if candle['Max'] >= p_entrada:
                                operacao_aberta, trade_atual = 1, Trade(1, p_entrada, candle['Data'], p_stop, n_contratos, tipo_parcial, valores_parciais)
                                ordem_aberta = 0
                        else:
                            ordem_aberta = 0

                    if ordem_aberta == -1:
                        if candle['SQD'] == "V":
                            if candle['Min'] <= p_entrada:
                                operacao_aberta, trade_atual = -1, Trade(-1, p_entrada, candle['Data'], p_stop, n_contratos, tipo_parcial, valores_parciais)
                                ordem_aberta = 0
                        else:
                            ordem_aberta = 0

                else:
                    while trade_atual.check_partial_exit(candle):
                        if verbose: print(f"{'Compra' if trade_atual.direcao==1 else 'Venda'} Parcial atingida: {trade_atual.saidas[-1][0]}")
                    
                    if trade_atual.contratos_abertos == 0:
                        trade_atual.close_trade(candle['Close'], candle['Data'])
                        operacoes.append(trade_atual)
                        if verbose: print(f"Operação finalizada por parciais. Pontos: {trade_atual.pontos_totais:.2f}")
                        operacao_aberta, trade_atual = 0, None
                        continue

                    if operacao_aberta == 1:
                        if candle['Min'] < candle['LinhaQuant']:
                            trade_atual.close_trade(candle['LinhaQuant'], candle['Data'])
                            operacoes.append(trade_atual)
                            if verbose: print(f"Compra Finalizada (Stop/Linha): {trade_atual.ponto_entrada} -> {candle['LinhaQuant']} | Pontos: {trade_atual.pontos_totais:.2f}")
                            operacao_aberta, trade_atual = 0, None
                            if sinal == 1:
                                p_entrada = candle['Max'] + 5
                                p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                                ordem_aberta = 1
                                
                            if sinal == -1:
                                p_entrada = candle['Min'] - 5
                                p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                                ordem_aberta = -1
                                
                    else:
                        if candle['Max'] > candle['LinhaQuant']:
                            trade_atual.close_trade(candle['LinhaQuant'], candle['Data'])
                            operacoes.append(trade_atual)
                            if verbose: print(f"Venda Finalizada (Stop/Linha): {trade_atual.ponto_entrada} -> {candle['LinhaQuant']} | Pontos: {trade_atual.pontos_totais:.2f}")
                            operacao_aberta, trade_atual = 0, None
                            if sinal == 1:
                                p_entrada = candle['Max'] + 5
                                p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                                ordem_aberta = 1
                                
                            if sinal == -1:
                                p_entrada = candle['Min'] - 5
                                p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                                ordem_aberta = -1
            else:
                if trade_atual:
                    trade_atual.close_trade(candle['Close'], candle['Data'])
                    operacoes.append(trade_atual)
                    if verbose: print(f"Operação Finalizada devido ao horário.")
                    operacao_aberta, trade_atual = 0, None

    return operacoes


if __name__ == "__main__":
    df = load_from_sqlite_to_pandas().sort_values('Data').reset_index(drop=True)
    df['SQD'] = '' 
    df.loc[df['Close'] > df['LinhaQuant'], 'SQD'] = 'C'
    df.loc[df['Close'] < df['LinhaQuant'], 'SQD'] = 'V'
    df['Sinal'] = 0
    df.loc[(df['SQD'] == 'C') & (df['SQD'].shift(1) == 'V'), 'Sinal'] = 1
    df.loc[(df['SQD'] == 'V') & (df['SQD'].shift(1) == 'C'), 'Sinal'] = -1
    
    print("Executando Operacional Clássico (Simples)...")
    trades_simples = simular_operacional(df, n_contratos=3, verbose=False)
    if trades_simples:
        stats, resumo = gerar_relatorio_estatistico(trades_simples)
        imprimir_stats(stats)
        
    print("\nExecutando Operacional com Parciais fixas 300 e 600")
    trades_parciais = operacional_parciais(df, verbose=False, n_contratos=3, tipo_parcial='fixa', valores_parciais=[300, 600])
    if trades_parciais:
        stats, resumo = gerar_relatorio_estatistico(trades_parciais)
        imprimir_stats(stats)

    print("\nExecutando Operacional com Parciais fixas 300")
    trades_parciais = operacional_parciais(df, verbose=False, n_contratos=3, tipo_parcial='fixa', valores_parciais=[300])
    if trades_parciais:
        stats, resumo = gerar_relatorio_estatistico(trades_parciais)
        imprimir_stats(stats)

    print("\nExecutando Operacional com Parciais Por Risco 2 e 3")
    trades_parciais = operacional_parciais(df, verbose=False, n_contratos=3, tipo_parcial='risco', valores_parciais=[2, 3])
    if trades_parciais:
        stats, resumo = gerar_relatorio_estatistico(trades_parciais)
        print("Estatisticas por trade")
        print(resumo)
        print("\nResumo de Operações com Parciais Por Risco 2 e 3")
        imprimir_stats(stats)
        
        # Detalhar um dia específico (Exemplo: primeiro dia com trades)
        dia_exemplo = '2026-02-19'
        detalhar_dia(trades_parciais, dia_exemplo)

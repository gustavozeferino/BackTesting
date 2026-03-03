import pandas as pd
import math
from datetime import time
from db_manager import load_from_sqlite_to_pandas
from trade import Trade, gerar_relatorio_estatistico, imprimir_stats, ajustar_preco_stop, detalhar_dia, comparar_resultados, detalhar_trades
from trade import exportar_trades_para_excel
import json
import yaml
import os

def carregar_configuracoes(arquivo):
    ext = os.path.splitext(arquivo)[1].lower()

    if ext == ".json":
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)

    elif ext in (".yml", ".yaml"):
        with open(arquivo, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    else:
        raise ValueError("Formato não suportado. Use JSON ou YAML.")


def simular_operacional(timeframe_data,
                        verbose=False, 
                        n_contratos=3, 
                        tipo_parcial=None, 
                        valores_parciais=None,
                        breakeven_pontos=False):
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
    permissao_abrir = False
    
    for dia in dias:
        df_dia = timeframe_data[timeframe_data['Dia'] == dia].copy()
        operacao_aberta, ordem_aberta = 0, 0
        p_entrada, p_stop = 0, 0
        
        for i, candle in df_dia.iterrows():
            horario_atual = candle['Data'].time()
            permissao_abrir = horario_inicial <= horario_atual <= horario_final
            
            if trade_atual:
                trade_atual.update_statistics(candle)
                if breakeven_pontos and trade_atual.breakeven_acionado == False:
                    if trade_atual.direcao == 1:

                        if candle['Max'] > (trade_atual.ponto_entrada + breakeven_pontos) and candle['Min'] > trade_atual.ponto_entrada:
                            trade_atual.ponto_stop_atual = max(trade_atual.ponto_stop_atual, trade_atual.ponto_entrada+5)
                            trade_atual.breakeven_acionado = True
                            if verbose:
                                print(f"Breakeven acionado para compra: {trade_atual.ponto_stop_atual}")
                    else:
                        if candle['Min'] < (trade_atual.ponto_entrada - breakeven_pontos) and candle['Max'] < trade_atual.ponto_entrada:
                            trade_atual.ponto_stop_atual = min(trade_atual.ponto_stop_atual, trade_atual.ponto_entrada-5)
                            trade_atual.breakeven_acionado = True
                            if verbose:
                                print(f"Breakeven acionado para venda: {trade_atual.ponto_stop_atual}")


            if permissao_abrir:
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
                                # Abriu operação de compra
                                operacao_aberta = 1
                                trade_atual = Trade(1, p_entrada, candle['Data'], p_stop, n_contratos, tipo_parcial, valores_parciais)
                                ordem_aberta = 0
                                if verbose:
                                    print("-"*50)
                                    print(f"Compra aberta: Entrada: {p_entrada} | Stop: {p_stop} | Risco: {trade_atual.risco_pontos}")
                        else:
                            ordem_aberta = 0

                    if ordem_aberta == -1:
                        if candle['SQD'] == "V":
                            if candle['Min'] <= p_entrada:
                                    # Abriu operação de venda
                                operacao_aberta = -1
                                trade_atual = Trade(-1, p_entrada, candle['Data'], p_stop, n_contratos, tipo_parcial, valores_parciais)
                                ordem_aberta = 0
                                if verbose:
                                    print("-"*50)
                                    print(f"Venda aberta: Entrada: {p_entrada} | Stop: {p_stop} | Risco: {trade_atual.risco_pontos}")
                        else:
                            ordem_aberta = 0

                else:
                    # Tem operação aberta
                    while trade_atual.check_partial_exit(candle):
                        if verbose: print(f"{'Compra' if trade_atual.direcao==1 else 'Venda'} Parcial atingida: {trade_atual.saidas[-1][0]}")
                    
                    if trade_atual.contratos_abertos == 0:
                        trade_atual.close_trade(candle['Close'], candle['Data'])
                        operacoes.append(trade_atual)
                        if verbose: print(f"Operação finalizada por parciais. Pontos: {trade_atual.pontos_totais:.2f}")
                        operacao_aberta, trade_atual = 0, None
                        #continue
                    
                    if operacao_aberta == 1:
                        # Operação de compra aberta com contratos restantes
                        stop_indicador = ajustar_preco_stop(1, candle['LinhaQuant'])
                        trade_atual.ponto_stop_atual = max(trade_atual.ponto_stop_atual, stop_indicador)
                        if candle['Min'] < trade_atual.ponto_stop_atual:
                            trade_atual.close_trade(trade_atual.ponto_stop_atual, candle['Data'])
                            operacoes.append(trade_atual)
                            if verbose:
                                print(f"Compra Finalizada (Stop/Linha): {trade_atual.ponto_entrada} -> {trade_atual.ponto_stop_atual} | Pontos: {trade_atual.pontos_totais:.2f}")
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
                        # Operação de venda aberta com contratos restantes
                        stop_indicador = ajustar_preco_stop(-1, candle['LinhaQuant'])
                        trade_atual.ponto_stop_atual = min(trade_atual.ponto_stop_atual, stop_indicador)
                        if candle['Max'] > trade_atual.ponto_stop_atual:
                            trade_atual.close_trade(trade_atual.ponto_stop_atual, candle['Data'])
                            operacoes.append(trade_atual)
                            if verbose:
                                print(f"Venda Finalizada (Stop/Linha): {trade_atual.ponto_entrada} -> {trade_atual.ponto_stop_atual} | Pontos: {trade_atual.pontos_totais:.2f}")
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
                    if verbose:
                        print(f"Operação Finalizada devido ao horário.")
                    operacao_aberta, trade_atual = 0, None

    return operacoes

def executar_testes(df, arquivo_config):
    configuracoes = carregar_configuracoes(arquivo_config)

    resumos = []
    nomes_estrategias = []

    for cfg in configuracoes:
        nome = cfg["nome"]
        params = cfg["params"]

        print(f"Executando Operacional: {nome}")
        resultado = simular_operacional(df, **params)

        resumo, resumo_diario = gerar_relatorio_estatistico(resultado)

        resumos.append(resumo)
        nomes_estrategias.append(nome)

    comparar_resultados(resumos, nomes_estrategias)


if __name__ == "__main__":
    df = load_from_sqlite_to_pandas().sort_values('Data').reset_index(drop=True)
    df['SQD'] = '' 
    df.loc[df['Close'] > df['LinhaQuant'], 'SQD'] = 'C'
    df.loc[df['Close'] < df['LinhaQuant'], 'SQD'] = 'V'
    df['Sinal'] = 0
    df.loc[(df['SQD'] == 'C') & (df['SQD'].shift(1) == 'V'), 'Sinal'] = 1
    df.loc[(df['SQD'] == 'V') & (df['SQD'].shift(1) == 'C'), 'Sinal'] = -1
    
    # Executar vários testes
    #arquivo_config = "testes_risco.yml"
    #executar_testes(df, arquivo_config)

    resultado_base = simular_operacional(df, n_contratos=3, verbose=False, breakeven_pontos=200, tipo_parcial='risco', valores_parciais=[2,3])
    res_global, res_diario = gerar_relatorio_estatistico(resultado_base)
    imprimir_stats(res_global)
    #if resultado_base:
    #    exportar_trades_para_excel(resultado_base, "trades_base.xlsx")
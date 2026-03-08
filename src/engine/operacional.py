import pandas as pd
import math
from datetime import time
from src.database.db_manager import load_from_sqlite_to_pandas
from src.engine.trade import Trade, gerar_relatorio_estatistico, imprimir_stats, ajustar_preco_stop, detalhar_dia, comparar_resultados, detalhar_trades
from src.engine.trade import exportar_trades_para_excel
import json
import yaml
import os
from src.analysis.analise_parametros import analisar_stop_otimo, analisar_parcial_otima, analisar_breakeven_otimo, resumo_analises, analisar_distribuicao_mae_mfe
from src.reports.relatorio_html import gerar_relatorio
from src.engine.trade import gerar_estatisticas_completas, analisar_por_periodo

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
                        breakeven_pontos=False,
                        horario_inicial=time(9, 15),
                        horario_final=time(17, 30),
                        horario_encerramento=time(18, 00),
                        stop_max=None):
    """
    Simula o operacional com parciais.
    """
    if isinstance(horario_inicial, str): horario_inicial = pd.to_datetime(horario_inicial).time()
    if isinstance(horario_final, str): horario_final = pd.to_datetime(horario_final).time()
    if isinstance(horario_encerramento, str): horario_encerramento = pd.to_datetime(horario_encerramento).time()
    
    if valores_parciais is None and tipo_parcial == 'risco':
        valores_parciais = [1, 2, 3] # Default para o que era antes

    timeframe_data['Data'] = pd.to_datetime(timeframe_data['Data'])
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
                            trade_atual.ponto_stop_atual = max(trade_atual.ponto_stop_atual, trade_atual.ponto_entrada+0)
                            trade_atual.breakeven_acionado = True
                            if verbose:
                                print(f"Breakeven acionado para compra: {trade_atual.ponto_stop_atual}")
                    else:
                        if candle['Min'] < (trade_atual.ponto_entrada - breakeven_pontos) and candle['Max'] < trade_atual.ponto_entrada:
                            trade_atual.ponto_stop_atual = min(trade_atual.ponto_stop_atual, trade_atual.ponto_entrada-0)
                            trade_atual.breakeven_acionado = True
                            if verbose:
                                print(f"Breakeven acionado para venda: {trade_atual.ponto_stop_atual}")


            if trade_atual and horario_atual >= horario_encerramento:
                trade_atual.motivo_saida = 'HORARIO'
                trade_atual.close_trade(candle['Close'], candle['Data'])
                operacoes.append(trade_atual)
                if verbose:
                    print(f"Operação Finalizada devido ao horário de encerramento ({horario_encerramento}).")
                operacao_aberta, trade_atual = 0, None
                continue
            elif operacao_aberta == 0 and not permissao_abrir:
                ordem_aberta = 0
            
            sinal = candle['Sinal']

            if operacao_aberta != 0:
                # Tem operação aberta
                while trade_atual.check_partial_exit(candle):
                    if verbose: print(f"{'Compra' if trade_atual.direcao==1 else 'Venda'} Parcial atingida: {trade_atual.saidas[-1][0]}")
                
                if trade_atual.contratos_abertos == 0:
                    trade_atual.close_trade(candle['Close'], candle['Data'])
                    operacoes.append(trade_atual)
                    if verbose: print(f"Operação finalizada por parciais. Pontos: {trade_atual.pontos_totais:.2f}")
                    operacao_aberta, trade_atual = 0, None
                elif operacao_aberta == 1:
                    # Operação de compra aberta com contratos restantes
                    stop_indicador = ajustar_preco_stop(1, candle['LinhaQuant'])
                    trade_atual.ponto_stop_atual = max(trade_atual.ponto_stop_atual, stop_indicador)
                    if candle['Min'] < trade_atual.ponto_stop_atual:
                        trade_atual.motivo_saida = 'STOP_LINHA'
                        trade_atual.close_trade(trade_atual.ponto_stop_atual, candle['Data'])
                        operacoes.append(trade_atual)
                        if verbose:
                            print(f"Compra Finalizada (Stop/Linha): {trade_atual.ponto_entrada} -> {trade_atual.ponto_stop_atual} | Pontos: {trade_atual.pontos_totais:.2f}")
                        operacao_aberta, trade_atual = 0, None
                        if permissao_abrir:
                            if sinal == 1:
                                p_entrada = candle['Max'] + 5
                                p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                                ordem_aberta = 1
                            elif sinal == -1:
                                p_entrada = candle['Min'] - 5
                                p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                                ordem_aberta = -1
                elif operacao_aberta == -1:
                    # Operação de venda aberta com contratos restantes
                    stop_indicador = ajustar_preco_stop(-1, candle['LinhaQuant'])
                    trade_atual.ponto_stop_atual = min(trade_atual.ponto_stop_atual, stop_indicador)
                    if candle['Max'] > trade_atual.ponto_stop_atual:
                        trade_atual.motivo_saida = 'STOP_LINHA'
                        trade_atual.close_trade(trade_atual.ponto_stop_atual, candle['Data'])
                        operacoes.append(trade_atual)
                        if verbose:
                            print(f"Venda Finalizada (Stop/Linha): {trade_atual.ponto_entrada} -> {trade_atual.ponto_stop_atual} | Pontos: {trade_atual.pontos_totais:.2f}")
                        operacao_aberta, trade_atual = 0, None
                        if permissao_abrir:
                            if sinal == 1:
                                p_entrada = candle['Max'] + 5
                                p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                                ordem_aberta = 1
                            elif sinal == -1:
                                p_entrada = candle['Min'] - 5
                                p_stop = ajustar_preco_stop(sinal, candle['LinhaQuant'])
                                ordem_aberta = -1

            if operacao_aberta == 0 and permissao_abrir:
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

                # --- BLOCO DE ABERTURA DE COMPRA ---
                if ordem_aberta == 1:
                    if candle['SQD'] == "C":
                        if candle['Max'] >= p_entrada:
                            # Abriu operação de compra
                            # Cálculo do risco original
                            risco_original = abs(p_entrada - p_stop)
                            # Lógica stop_max
                            if stop_max is not None:
                                risco_final = min(risco_original, stop_max)
                                p_stop = p_entrada - risco_final # Ajusta o ponto de stop real

                            trade_atual = Trade(1, p_entrada, candle['Data'], p_stop, n_contratos, tipo_parcial, valores_parciais)

                            if trade_atual:
                                operacao_aberta = 1
                                ordem_aberta = 0
                                if verbose:
                                    print("-"*50)
                                    print(f"Compra aberta: Entrada: {p_entrada} | Stop: {p_stop} | Risco: {trade_atual.risco_pontos}")
                    else:
                        ordem_aberta = 0

                # --- BLOCO DE ABERTURA DE VENDA ---
                if ordem_aberta == -1:
                    if candle['SQD'] == "V":
                        if candle['Min'] <= p_entrada:
                            # Abriu operação de venda
                            # Cálculo do risco original
                            risco_original = abs(p_entrada - p_stop)
                            # Lógica stop_max
                            if stop_max is not None:
                                risco_final = min(risco_original, stop_max)
                                p_stop = p_entrada + risco_final # Ajusta o ponto de stop real

                            trade_atual = Trade(-1, p_entrada, candle['Data'], p_stop, n_contratos, tipo_parcial, valores_parciais)

                            if trade_atual:
                                operacao_aberta = -1
                                ordem_aberta = 0
                                if verbose:
                                    print("-"*50)
                                    print(f"Venda aberta: Entrada: {p_entrada} | Stop: {p_stop} | Risco: {trade_atual.risco_pontos}")
                    else:
                        ordem_aberta = 0

        # Fim do dia, fecha trade aberto
        if trade_atual:
            trade_atual.motivo_saida = 'HORARIO'
            trade_atual.close_trade(candle['Close'], candle['Data'])
            operacoes.append(trade_atual)
            if verbose:
                print(f"Operação Finalizada devido ao fim do dia.")
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


def executar_backtest_completo(df, params, titulo="Backtest Completo", output_html="relatorio.html"):
    """
    Executa o fluxo completo: simulação, estatísticas avançadas, 
    análise de parâmetros e geração de relatório HTML.
    """
    print(f"\n>>> Iniciando Backtest: {titulo}")
    
    # 1. Simulação
    resultado = simular_operacional(df, **params)
    
    if not resultado:
        print("Nenhuma operação realizada no período.")
        return
        
    # 2. Estatísticas e Console
    stats_c, resumo_d = gerar_estatisticas_completas(resultado)
    imprimir_stats(stats_c)
    
    # 3. Análise de Parâmetros
    resumo_analises(resultado)
    
    # 4. Relatório HTML
    gerar_relatorio(resultado, output_html, titulo)
    print(f"\n[OK] Relatório HTML gerado: {output_html}")
    
    return resultado


if __name__ == "__main__":
    df = load_from_sqlite_to_pandas().sort_values('Data').reset_index(drop=True)
    
    #resultado_base = executar_backtest_completo(
    #    df, 
    #    params={'n_contratos': 2, 'verbose': False}, 
    #    titulo="Estratégia Base - Backtest Completo"
    #)
    
    resultado_base = simular_operacional(
        df,
        n_contratos=2,
        verbose=False,
        breakeven_pontos=200,
        tipo_parcial=None,
        valores_parciais=None,
        stop_max=None,
        horario_inicial=time(11, 45),
        horario_final=time(17, 30),
        horario_encerramento=time(18, 00))

    stats_c, resumo_d = gerar_estatisticas_completas(resultado_base)
    imprimir_stats(stats_c) 
    analisar_distribuicao_mae_mfe(resultado_base)
    # if resultado_base:
    #    exportar_trades_para_excel(resultado_base, "trades_base.xlsx")

    output_html = 'output/relatorio_melhor_solucao.html'
    gerar_relatorio(resultado_base, output_html, titulo="Solução com melhor fator de lucro")
    print(f"\n[OK] Relatório HTML gerado: {output_html}")

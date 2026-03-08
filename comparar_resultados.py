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

from src.analysis.otimizador import comparar_resultados_otimizacao




if __name__ == "__main__":
    df = load_from_sqlite_to_pandas().sort_values('Data').reset_index(drop=True)
    comparar_resultados_otimizacao(df, config_file='output/optimization_result_best.json', top_n=10)
    
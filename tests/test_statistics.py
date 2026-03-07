from datetime import datetime, timedelta
from src.engine.trade import Trade, gerar_relatorio_estatistico, gerar_estatisticas_completas, analisar_por_periodo
import pandas as pd

def test_estatisticas():
    print("Iniciando teste de estatísticas...")
    
    trades = []
    
    # Dia 1: 3 trades (2 vitórias, 1 derrota)
    d1 = datetime(2023, 1, 1)
    
    t1 = Trade(1, 100, d1 + timedelta(hours=10))
    t1.close_trade(110, d1 + timedelta(hours=10, minutes=30)) # +10 pts
    t1.MFE, t1.MAE = 12, -2
    trades.append(t1)
    
    t2 = Trade(1, 100, d1 + timedelta(hours=11))
    t2.close_trade(105, d1 + timedelta(hours=11, minutes=20)) # +5 pts
    t2.MFE, t2.MAE = 8, -1
    trades.append(t2)
    
    t3 = Trade(-1, 100, d1 + timedelta(hours=14))
    t3.close_trade(105, d1 + timedelta(hours=14, minutes=15)) # -5 pts
    t3.MFE, t3.MAE = 2, -6
    trades.append(t3)
    
    # Dia 2: 2 trades (1 vitória, 1 derrota)
    d2 = datetime(2023, 1, 2)
    
    t4 = Trade(1, 200, d2 + timedelta(hours=10))
    t4.close_trade(220, d2 + timedelta(hours=10, minutes=40)) # +20 pts
    t4.MFE, t4.MAE = 25, -5
    trades.append(t4)
    
    t5 = Trade(-1, 200, d2 + timedelta(hours=15))
    t5.close_trade(210, d2 + timedelta(hours=15, minutes=10)) # -10 pts
    t5.MFE, t5.MAE = 0, -12
    trades.append(t5)
    
    # Gerar Relatório
    stats, resumo = gerar_relatorio_estatistico(trades)
    stats_c, resumo_c = gerar_estatisticas_completas(trades)
    df_periodos = analisar_por_periodo(trades)
    
    print("\nEstatísticas Completas:")
    print(stats_c)
    print("\nResumo por Período:")
    print(df_periodos)
    
    # Asserções Globais
    # Total pontos: 10 + 5 - 5 + 20 - 10 = 20
    # Ganhos: 10 + 5 + 20 = 35
    # Perdas: 5 + 10 = 15
    # Profit Factor: 35 / 15 = 2.33
    # Win Rate: 3 / 5 = 60%
    
    assert stats['Total Trades'] == 5
    assert stats['Total Pontos'] == 20
    assert stats['Win Rate (%)'] == 60.0
    assert stats['Profit Factor'] == 2.33
    
    # Completas
    assert stats_c['Total Vencedores'] == 3
    assert stats_c['Total Perdedores'] == 2
    assert stats_c['Maior Sequência Ganhos'] == 2 # 10, 5 positivos
    assert stats_c['Maior Vitória (pts)'] == 20
    assert stats_c['Maior Derrota (pts)'] == -10
    assert stats_c['Payoff Ratio'] == 1.56 # (35/3)/(15/2) = 11.66 / 7.5 = 1.555
    
    # Períodos
    assert len(df_periodos) > 0
    df_manha = df_periodos[df_periodos['periodo'] == 'MANHA']
    assert df_manha['total_trades'].values[0] == 3 # t1(10h), t2(11h), t4(10h)
    assert df_manha['total_pontos'].values[0] == 35 # 10 + 5 + 20
    
    # Asserções Diárias
    assert len(resumo) == 2
    assert resumo.loc[resumo['Data'] == d1.date(), 'saldo_pontos'].values[0] == 10 # 10+5-5
    assert resumo.loc[resumo['Data'] == d2.date(), 'saldo_pontos'].values[0] == 10 # 20-10
    
    print("\nTodos os testes de estatísticas passaram!")

if __name__ == "__main__":
    test_estatisticas()

import pandas as pd
import pandas as pd
from datetime import datetime
from trade import Trade
from analise_parametros import analisar_stop_otimo, analisar_parcial_otima, analisar_breakeven_otimo

def get_test_trades():
    trades = []
    
    # Trade 1: Vitória rápida, sem calor
    t1 = Trade(1, 1000, datetime(2023, 1, 1, 10, 0))
    t1.close_trade(1200, datetime(2023, 1, 1, 10, 30))
    t1.MFE, t1.MAE = 250, -10
    trades.append(t1)
    
    # Trade 2: Perda bruta, calor máximo e stop
    t2 = Trade(-1, 2000, datetime(2023, 1, 2, 11, 0))
    t2.close_trade(2150, datetime(2023, 1, 2, 11, 20)) # Vendeu e subiu 150 pontos
    t2.MFE, t2.MAE = 20, -150
    trades.append(t2)
    
    # Trade 3: Vitória que sofreu calor antes de ir
    t3 = Trade(1, 3000, datetime(2023, 1, 3, 14, 0))
    t3.close_trade(3100, datetime(2023, 1, 3, 15, 0))
    t3.MFE, t3.MAE = 120, -80
    trades.append(t3)
    
    # Trade 4: Falsa Vitória, foi muito a favor e voltou perdendo
    t4 = Trade(1, 4000, datetime(2023, 1, 4, 10, 0))
    t4.close_trade(3900, datetime(2023, 1, 4, 11, 0)) # Perdeu 100
    t4.MFE, t4.MAE = 180, -110
    trades.append(t4)
    
    return trades

def test_analisar_stop_otimo():
    trades = get_test_trades()
    # trades originais pontos: t1(200), t2(-150), t3(100), t4(-100)
    # MAE abs: t1(10), t2(150), t3(80), t4(110)
    
    df, melhor, perc = analisar_stop_otimo(trades, stops=[50, 100, 200])
    
    # stop = 50: 
    # t1 (mae 10) < 50 => 200
    # t2 (mae 150) >= 50 => -50
    # t3 (mae 80) >= 50 => -50  <- Essa vitória virou derrota no stop curto
    # t4 (mae 110) >= 50 => -50
    # Total pontos: 200 - 50 - 50 - 50 = 50
    res_50 = df[df['stop'] == 50].iloc[0]
    assert res_50['total_pontos'] == 50
    
    # stop = 100:
    # t1 (mae 10) < 100 => 200
    # t2 (mae 150) >= 100 => -100
    # t3 (mae 80) < 100 => 100
    # t4 (mae 110) >= 100 => -100
    # Total pontos: 200 - 100 + 100 - 100 = 100
    res_100 = df[df['stop'] == 100].iloc[0]
    assert res_100['total_pontos'] == 100

def test_analisar_parcial_otima():
    trades = get_test_trades()
    # MFE: t1(250), t2(20), t3(120), t4(180)
    # Pontos: t1(200), t2(-150), t3(100), t4(-100)
    
    df, melhor = analisar_parcial_otima(trades, niveis=[100, 200], pct_parcial=0.5)
    
    # nivel = 100
    # t1 (mfe 250) >= 100 => fez parcial. Novo pt = 100*0.5 + 200*0.5 = 50 + 100 = 150
    # t2 (mfe 20) < 100 => não fez parcial. Novo pt = -150
    # t3 (mfe 120) >= 100 => fez parcial. Novo pt = 100*0.5 + 100*0.5 = 50 + 50 = 100
    # t4 (mfe 180) >= 100 => fez parcial. Novo pt = 100*0.5 + (-100)*0.5 = 50 - 50 = 0
    # Total pontos = 150 - 150 + 100 + 0 = 100
    res_100 = df[df['nivel'] == 100].iloc[0]
    assert res_100['total_pontos'] == 100
    
    # nivel = 200
    # t1 (mfe 250) >= 200 => fez parcial. Novo pt = 200*0.5 + 200*0.5 = 200
    # t2 (mfe 20) < 200 => não fez
    # t3 (mfe 120) < 200 => não fez
    # t4 (mfe 180) < 200 => não fez
    # Total pontos: 200 - 150 + 100 - 100 = 50
    res_200 = df[df['nivel'] == 200].iloc[0]
    assert res_200['total_pontos'] == 50

def test_analisar_breakeven_otimo():
    trades = get_test_trades()
    # MFE: t1(250), t2(20), t3(120), t4(180)
    # Pontos: t1(200), t2(-150), t3(100), t4(-100)
    
    df, melhor = analisar_breakeven_otimo(trades, valores=[150, 200])
    
    # valor = 150
    # t1 (mfe 250) >= 150 => clip(0) -> 200
    # t2 (mfe 20) < 150 => mantem -> -150
    # t3 (mfe 120) < 150 => mantem -> 100
    # t4 (mfe 180) >= 150 => clip(-100, 0) -> 0
    # Total pontos: 200 - 150 + 100 + 0 = 150
    res_150 = df[df['breakeven_pts'] == 150].iloc[0]
    assert res_150['total_pontos'] == 150
    assert res_150['trades_salvos'] == 1 # Apenas t4 foi salvo
    
    # valor = 200
    # t1 (mfe 250) >= 200 => 200
    # t2 (mfe 20) < 200 => -150
    # t3 (mfe 120) < 200 => 100
    # t4 (mfe 180) < 200 => -100 (nao salvou)
    # Total pontos: 200 - 150 + 100 - 100 = 50
    res_200 = df[df['breakeven_pts'] == 200].iloc[0]
    assert res_200['total_pontos'] == 50
    assert res_200['trades_salvos'] == 0

if __name__ == "__main__":
    test_analisar_stop_otimo()
    test_analisar_parcial_otima()
    test_analisar_breakeven_otimo()
    print("All anaylsis tests passed!")

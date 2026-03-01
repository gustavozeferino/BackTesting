from trade import Trade
from datetime import datetime

def test_config_partials():
    # Teste 1: Parciais Fixas (pontos)
    # Compra 100, Stop 90, Parciais em 50 e 150 pontos
    t_fixa = Trade(direcao=1, ponto_entrada=100.0, hora_entrada=datetime(2026, 1, 1, 9, 0), 
                   ponto_stop=90.0, n_contratos=3, tipo_parcial='fixa', valores_parciais=[50, 150])
    print(f"Alvos fixa: {t_fixa.alvos}")
    assert t_fixa.alvos == [150.0, 250.0] # 100+50, 100+150
    
    # Teste 2: Parciais Risco (multiplicadores)
    # Compra 100, Stop 90 (Risco 10), Parciais em 1.5R e 3R
    t_risco = Trade(direcao=1, ponto_entrada=100.0, hora_entrada=datetime(2026, 1, 1, 9, 0), 
                    ponto_stop=90.0, n_contratos=3, tipo_parcial='risco', valores_parciais=[1.5, 3])
    print(f"Alvos risco: {t_risco.alvos}")
    assert t_risco.alvos == [115.0, 130.0] # 100 + 10*1.5, 100 + 10*3
    
    # Teste 3: Sem parciais
    t_none = Trade(direcao=-1, ponto_entrada=100.0, hora_entrada=datetime(2026, 1, 1, 9, 0), 
                   ponto_stop=110.0, n_contratos=3)
    print(f"Alvos none: {t_none.alvos}")
    assert t_none.alvos == []
    
    # Teste 4: Parcial atingida (Venda, fixa 50 pts)
    # Entrada 1000, Stop 1050, Parcial 50 pts (1000-50 = 950)
    t_venda = Trade(direcao=-1, ponto_entrada=1000.0, hora_entrada=datetime(2026, 1, 1, 9, 0), 
                    ponto_stop=1050.0, n_contratos=1, tipo_parcial='fixa', valores_parciais=[50])
    candle = {'Min': 940.0, 'Max': 1005.0, 'Data': datetime(2026, 1, 1, 9, 5)}
    hit = t_venda.check_partial_exit(candle)
    print(f"Hit venda fixa: {hit}")
    assert hit == True
    assert t_venda.saidas[0][0] == 950.0

    print("\nTestes de configuração de parciais passaram!")

if __name__ == "__main__":
    test_config_partials()

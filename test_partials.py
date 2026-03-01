from trade import Trade
from datetime import datetime

def test_partial_exits():
    # Setup trade: Compra, entrada 100, stop 90 (risco 10)
    # Alvos: 110 (1R), 120 (2R), 130 (3R)
    t = Trade(direcao=1, ponto_entrada=100.0, hora_entrada=datetime(2026, 1, 1, 9, 15), ponto_stop=90.0, n_contratos=3)
    
    print(f"Alvos calculados: {t.alvos}")
    assert t.alvos == [110.0, 120.0, 130.0]
    
    # Candle 1: Atinge o primeiro alvo
    candle1 = {'Max': 112.0, 'Min': 99.0, 'Data': datetime(2026, 1, 1, 9, 20)}
    hit1 = t.check_partial_exit(candle1)
    print(f"Hit 1R: {hit1}")
    assert hit1 == True
    assert t.contratos_abertos == 2
    assert len(t.saidas) == 1
    assert t.saidas[0][0] == 110.0
    
    # Candle 2: Não atinge o segundo alvo
    candle2 = {'Max': 118.0, 'Min': 105.0, 'Data': datetime(2026, 1, 1, 9, 25)}
    hit2 = t.check_partial_exit(candle2)
    print(f"Hit 2R (antes): {hit2}")
    assert hit2 == False
    
    # Candle 3: Atinge o segundo alvo
    candle3 = {'Max': 125.0, 'Min': 110.0, 'Data': datetime(2026, 1, 1, 9, 30)}
    hit3 = t.check_partial_exit(candle3)
    print(f"Hit 2R (depois): {hit3}")
    assert hit3 == True
    assert t.contratos_abertos == 1
    
    # Candle 4: Bate no stop (LinhaQuant fictícia)
    # Fecha o último contrato em 95
    t.close_trade(ponto_saida=95.0, hora_saida=datetime(2026, 1, 1, 10, 0))
    print(f"Contratos abertos: {t.contratos_abertos}")
    assert t.contratos_abertos == 0
    assert len(t.saidas) == 3
    
    # Cálculos:
    # Saída 1: 110 (1 contrato) -> +10 pontos
    # Saída 2: 120 (1 contrato) -> +20 pontos
    # Saída 3: 95 (1 contrato) -> -5 pontos
    # Total pontos: 10 + 20 - 5 = 25
    print(f"Pontos totais acumulados: {t.pontos_totais}")
    assert round(t.pontos_totais, 2) == 25.0
    
    print("\nTeste de parciais passou com sucesso!")

if __name__ == "__main__":
    test_partial_exits()

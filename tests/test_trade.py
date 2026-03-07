from datetime import datetime, timedelta
from src.engine.trade import Trade

def test_trade_compra():
    print("Testando Operação de Compra...")
    inicio = datetime(2023, 1, 1, 10, 0)
    trade = Trade(direcao=1, ponto_entrada=1000, hora_entrada=inicio)
    
    # Simular candles
    candles = [
        {'Max': 1010, 'Min': 995},  # Ganho: 10, Perda: -5
        {'Max': 1020, 'Min': 1005}, # Ganho: 20, Perda: -5
        {'Max': 1015, 'Min': 990},  # Ganho: 20, Perda: -10
    ]
    
    for c in candles:
        trade.update_statistics(c)
    
    # Saída
    fim = inicio + timedelta(minutes=15)
    trade.close_trade(ponto_saida=1015, hora_saida=fim)
    
    res = trade.to_dict()
    print(res)
    
    assert res['pontos'] == 15
    assert res['duracao_min'] == 15
    assert res['mfe'] == 20
    assert res['mae'] == -10
    print("Teste Compra: SUCESSO\n")

def test_trade_venda():
    print("Testando Operação de Venda...")
    inicio = datetime(2023, 1, 1, 14, 0)
    trade = Trade(direcao=-1, ponto_entrada=2000, hora_entrada=inicio)
    
    # Simular candles
    # Preço cai -> Lucro na venda
    # Preço sobe -> Prejuízo na venda
    candles = [
        {'Max': 2005, 'Min': 1990}, # Ganho: 10 (2000-1990), Perda: -5 (2000-2005)
        {'Max': 2010, 'Min': 1995}, # Ganho: 10, Perda: -10 (2000-2010)
        {'Max': 1990, 'Min': 1980}, # Ganho: 20 (2000-1980), Perda: -10
    ]
    
    for c in candles:
        trade.update_statistics(c)
        
    fim = inicio + timedelta(minutes=45)
    trade.close_trade(ponto_saida=1985, hora_saida=fim)
    
    res = trade.to_dict()
    print(res)
    
    assert res['pontos'] == 15  # 2000 - 1985
    assert res['duracao_min'] == 45
    assert res['mfe'] == 20     # 2000 - 1980
    assert res['mae'] == -10    # 2000 - 2010
    print("Teste Venda: SUCESSO\n")

if __name__ == "__main__":
    try:
        test_trade_compra()
        test_trade_venda()
        print("Todos os testes passaram!")
    except AssertionError as e:
        print(f"Falha no teste!")
        raise e

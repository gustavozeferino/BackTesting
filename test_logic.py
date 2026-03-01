import math

def ajustar_preco_stop(direcao, preco_stop):
    """
    Se direcao for 1 (compra), ajusta o preco_stop para o próximo múltiplo de 5 para baixo (floor).
    Se direcao for -1 (venda), ajusta o preco_stop para o próximo múltiplo de 5 para cima (ceil).
    """
    if direcao == 1:
        return math.floor(preco_stop / 5) * 5
    elif direcao == -1:
        return math.ceil(preco_stop / 5) * 5
    return preco_stop

def test_ajuste():
    # Test cases: (direcao, preco_stop, esperado)
    cases = [
        (1, 103, 100),    # Compra: 103 -> 100 (múltiplo de 5 para baixo)
        (1, 105, 105),    # Compra: 105 -> 105 (já é múltiplo)
        (1, 107.8, 105),  # Compra: 107.8 -> 105
        (-1, 102, 105),   # Venda: 102 -> 105 (múltiplo de 5 para cima)
        (-1, 105, 105),   # Venda: 105 -> 105 (já é múltiplo)
        (-1, 107.2, 110), # Venda: 107.2 -> 110
    ]
    
    for d, p, e in cases:
        res = ajustar_preco_stop(d, p)
        assert res == e, f"Erro: d={d}, p={p}, esperado={e}, obtido={res}"
        print(f"OK: d={d}, p={p} -> {res}")

if __name__ == "__main__":
    test_ajuste()
    print("\nTodos os testes lógicos passaram!")

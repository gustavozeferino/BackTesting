"""
test_logic.py — Testes unitários isolados (sem banco de dados).

Testa:
  - ajustar_preco_stop (existente)
  - Break-even stop (novo)
  - Trailing stop (novo)

Os testes criam objetos Trade diretamente e simulam candles como dicts,
sem depender do banco de dados ou do loop de operacional.py.
"""

import math
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from trade import Trade, ajustar_preco_stop


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_candle(data, open_, max_, min_, close, linha_quant=None):
    """Cria um candle como dict no formato esperado pela classe Trade."""
    return {
        'Data': data,
        'Open': open_,
        'Max': max_,
        'Min': min_,
        'Close': close,
        'LinhaQuant': linha_quant if linha_quant is not None else min_,
        'Sinal': 0,
        'SQD': 'C',
    }


def tick(minutes=1, base=None):
    base = base or datetime(2024, 1, 2, 9, 15)
    return base + timedelta(minutes=minutes)


def simular_stop_logica(trade, candles, breakeven_pontos=None, trailing_pontos=None, trailing_ativacao=None):
    """
    Reproduz a lógica de break-even + trailing do operacional.py,
    aplicada sequencialmente em uma lista de candles.
    Retorna (encerrado, motivo_saida, ponto_stop_atual final).
    """
    for candle in candles:
        trade.update_statistics(candle)

        if trade.direcao == 1:  # COMPRA
            # Break-even
            if breakeven_pontos and not trade.breakeven_acionado:
                if candle['Max'] >= trade.ponto_entrada + breakeven_pontos:
                    if trade.ponto_stop_atual is None or trade.ponto_stop_atual < trade.ponto_entrada:
                        trade.ponto_stop_atual = trade.ponto_entrada
                        trade.breakeven_acionado = True

            # Trailing
            if trailing_pontos:
                ativacao_ok = (trailing_ativacao is None) or (trade.MFE >= trailing_ativacao)
                if ativacao_ok:
                    stop_trail = trade.extrema_favor - trailing_pontos
                    if trade.ponto_stop_atual is None or stop_trail > trade.ponto_stop_atual:
                        trade.ponto_stop_atual = stop_trail
                        trade.trailing_acionado = True

            # Verificação do stop
            if trade.breakeven_acionado or trade.trailing_acionado:
                ponto_stop_efetivo = trade.ponto_stop_atual
            else:
                ponto_stop_efetivo = candle['LinhaQuant']

            if candle['Min'] < ponto_stop_efetivo:
                if trade.trailing_acionado:
                    trade.motivo_saida = 'TRAILING'
                elif trade.breakeven_acionado:
                    trade.motivo_saida = 'BREAKEVEN'
                else:
                    trade.motivo_saida = 'STOP_LINHA'
                trade.close_trade(ponto_stop_efetivo, candle['Data'])
                return True, trade.motivo_saida

        else:  # VENDA
            # Break-even
            if breakeven_pontos and not trade.breakeven_acionado:
                if candle['Min'] <= trade.ponto_entrada - breakeven_pontos:
                    if trade.ponto_stop_atual is None or trade.ponto_stop_atual > trade.ponto_entrada:
                        trade.ponto_stop_atual = trade.ponto_entrada
                        trade.breakeven_acionado = True

            # Trailing
            if trailing_pontos:
                ativacao_ok = (trailing_ativacao is None) or (trade.MFE >= trailing_ativacao)
                if ativacao_ok:
                    stop_trail = trade.extrema_favor + trailing_pontos
                    if trade.ponto_stop_atual is None or stop_trail < trade.ponto_stop_atual:
                        trade.ponto_stop_atual = stop_trail
                        trade.trailing_acionado = True

            # Verificação do stop
            if trade.breakeven_acionado or trade.trailing_acionado:
                ponto_stop_efetivo = trade.ponto_stop_atual
            else:
                ponto_stop_efetivo = candle['LinhaQuant']

            if candle['Max'] > ponto_stop_efetivo:
                if trade.trailing_acionado:
                    trade.motivo_saida = 'TRAILING'
                elif trade.breakeven_acionado:
                    trade.motivo_saida = 'BREAKEVEN'
                else:
                    trade.motivo_saida = 'STOP_LINHA'
                trade.close_trade(ponto_stop_efetivo, candle['Data'])
                return True, trade.motivo_saida

    return False, None


# ─── Testes preexistentes ────────────────────────────────────────────────────

def test_ajuste():
    cases = [
        (1,  103,   100),
        (1,  105,   105),
        (1,  107.8, 105),
        (-1, 102,   105),
        (-1, 105,   105),
        (-1, 107.2, 110),
    ]
    for d, p, e in cases:
        res = ajustar_preco_stop(d, p)
        assert res == e, f"Erro: d={d}, p={p}, esperado={e}, obtido={res}"
        print(f"OK ajuste: d={d}, p={p} -> {res}")


# ─── Testes de Break-Even ────────────────────────────────────────────────────

def test_breakeven_compra_acionado():
    """Break-even deve ser acionado quando Max >= entrada + breakeven_pontos (compra)."""
    entrada, stop = 100000, 99800  # risco = 200pts
    t = Trade(1, entrada, tick(0), stop)
    assert t.ponto_stop_atual == stop
    assert not t.breakeven_acionado

    candles = [
        # Max = 100100 aciona break-even; Min = 100010 > entrada → stop não é atingido
        make_candle(tick(1), 100000, 100100, 100010, 100050, linha_quant=99800),
    ]
    encerrado, _ = simular_stop_logica(t, candles, breakeven_pontos=100)

    assert not encerrado, "Não deveria ter encerrado — stop foi para entrada, Min ainda acima"
    assert t.breakeven_acionado, "Break-even deveria ter sido acionado"
    assert t.ponto_stop_atual == entrada, f"ponto_stop_atual deveria ser {entrada}, obtido {t.ponto_stop_atual}"
    print("OK test_breakeven_compra_acionado")


def test_breakeven_venda_acionado():
    """Break-even deve ser acionado quando Min <= entrada - breakeven_pontos (venda)."""
    entrada, stop = 100000, 100200  # risco = 200pts (venda)
    t = Trade(-1, entrada, tick(0), stop)
    assert t.ponto_stop_atual == stop

    candles = [
        # Min cai 100pts; Max = 99990 < entrada → stop de venda não é atingido
        make_candle(tick(1), 100000, 99990, 99900, 99950, linha_quant=100200),
    ]
    encerrado, _ = simular_stop_logica(t, candles, breakeven_pontos=100)

    assert not encerrado
    assert t.breakeven_acionado, "Break-even deveria ter sido acionado"
    assert t.ponto_stop_atual == entrada, f"ponto_stop_atual deveria ser {entrada}"
    print("OK test_breakeven_venda_acionado")


def test_breakeven_nao_acionado_quando_preco_nao_chega():
    """Break-even NÃO deve ser acionado quando o preço não atinge o nível."""
    entrada, stop = 100000, 99800
    t = Trade(1, entrada, tick(0), stop)

    candles = [
        # Max só avança 80pts — não atinge os 100 necessários
        make_candle(tick(1), 100000, 100080, 99850, 100020, linha_quant=99800),
    ]
    simular_stop_logica(t, candles, breakeven_pontos=100)

    assert not t.breakeven_acionado, "Break-even não deveria ter sido acionado"
    assert t.ponto_stop_atual == stop, "ponto_stop_atual não deveria ter mudado"
    print("OK test_breakeven_nao_acionado_quando_preco_nao_chega")


def test_breakeven_stop_nao_recua_compra():
    """Após break-even acionado, o stop não pode recuar abaixo do ponto de entrada."""
    entrada, stop = 100000, 99800
    t = Trade(1, entrada, tick(0), stop)

    candles = [
        # Candle 1: aciona break-even (Max = 100100)
        make_candle(tick(1), 100000, 100100, 99900, 100050, linha_quant=99800),
        # Candle 2: prova que o stop não voltou para 99800 (LinhaQuant abaixo da entrada)
        make_candle(tick(2), 100050, 100060, 99950, 100000, linha_quant=99750),
    ]
    encerrado, _ = simular_stop_logica(t, candles, breakeven_pontos=100)

    # Candle 2 tem Min=99950. Com stop em 100000 (entrada), 99950 < 100000 → deveria encerrar
    # por BREAKEVEN
    assert encerrado, "Trade deveria ter encerrado pelo stop de break-even"
    assert t.motivo_saida == 'BREAKEVEN', f"Motivo deveria ser BREAKEVEN, obtido: {t.motivo_saida}"
    assert t.ponto_saida == entrada, f"Saída deveria ser no ponto de entrada {entrada}"
    print("OK test_breakeven_stop_nao_recua_compra")


def test_breakeven_stop_nao_recua_venda():
    """Após break-even em venda, o stop não pode recuar acima do ponto de entrada."""
    entrada, stop = 100000, 100200
    t = Trade(-1, entrada, tick(0), stop)

    candles = [
        # Candle 1: aciona break-even em venda (Min <= 99900)
        make_candle(tick(1), 100000, 100010, 99900, 99950, linha_quant=100200),
        # Candle 2: Max sobe para 100050 — acima da entrada (100000) → encerra por BREAKEVEN
        make_candle(tick(2), 99950, 100050, 99940, 100000, linha_quant=100200),
    ]
    encerrado, _ = simular_stop_logica(t, candles, breakeven_pontos=100)

    assert encerrado
    assert t.motivo_saida == 'BREAKEVEN'
    assert t.ponto_saida == entrada
    print("OK test_breakeven_stop_nao_recua_venda")


# ─── Testes de Trailing Stop ─────────────────────────────────────────────────

def test_trailing_sobe_com_preco_compra():
    """Em compra, o stop do trailing deve subir conforme o Max aumenta."""
    entrada, stop_inicial = 100000, 99800
    t = Trade(1, entrada, tick(0), stop_inicial)
    trailing = 80

    candles = [
        # Candle 1: extrema_favor=100100; stop_trail=100020; Min=100030 → não fecha
        make_candle(tick(1), 100000, 100100, 100030, 100050, linha_quant=99800),
        # Candle 2: extrema_favor=100200; stop_trail=100120; Min=100130 → não fecha
        make_candle(tick(2), 100050, 100200, 100130, 100150, linha_quant=99800),
    ]
    encerrado, _ = simular_stop_logica(t, candles, trailing_pontos=trailing)

    assert not encerrado, "Trade não deveria ter encerrado nestes candles"
    assert t.trailing_acionado
    # Stop deve ser: extrema_favor - trailing = 100200 - 80 = 100120
    assert t.ponto_stop_atual == 100200 - trailing, \
        f"Stop esperado {100200 - trailing}, obtido {t.ponto_stop_atual}"
    print(f"OK test_trailing_sobe_com_preco_compra: stop={t.ponto_stop_atual}")


def test_trailing_nao_desce_compra():
    """Em compra, o trailing stop nunca deve recuar (só sobe)."""
    entrada, stop_inicial = 100000, 99800
    t = Trade(1, entrada, tick(0), stop_inicial)
    trailing = 80

    candles = [
        # Candle 1: pico=100200; stop_trail=100120; Min=100130 → não fecha
        make_candle(tick(1), 100000, 100200, 100130, 100100, linha_quant=99800),
        # Candle 2: Max=100150 < 100200. extrema_favor permanece 100200. Min=100125 > 100120 → não fecha
        make_candle(tick(2), 100100, 100150, 100125, 100050, linha_quant=99800),
    ]
    encerrado, _ = simular_stop_logica(t, candles, trailing_pontos=trailing)

    assert not encerrado, "Trade não deveria ter encerrado"
    # Após candle 2 (Max=100150 < 100200), stop deve permanecer 100120
    assert t.ponto_stop_atual == 100200 - trailing, \
        f"Stop não deveria ter recuado: {t.ponto_stop_atual}"
    print(f"OK test_trailing_nao_desce_compra: stop={t.ponto_stop_atual}")


def test_trailing_encerra_com_motivo_correto():
    """Trade encerrado pelo trailing deve ter motivo_saida == 'TRAILING'."""
    entrada, stop_inicial = 100000, 99800
    t = Trade(1, entrada, tick(0), stop_inicial)
    trailing = 80

    candles = [
        # Avança 200pts → stop sobe para 100120
        make_candle(tick(1), 100000, 100200, 99950, 100150, linha_quant=99800),
        # Recua: Min = 100100 < 100120 → encerra pelo trailing
        make_candle(tick(2), 100150, 100160, 100100, 100120, linha_quant=99800),
    ]
    encerrado, motivo = simular_stop_logica(t, candles, trailing_pontos=trailing)

    assert encerrado, "Trade deveria ter sido encerrado"
    assert motivo == 'TRAILING', f"Motivo esperado TRAILING, obtido: {motivo}"
    print("OK test_trailing_encerra_com_motivo_correto")


def test_trailing_ativacao_nao_ativa_antes():
    """Trailing com ativacao=150 não deve ativar se MFE < 150."""
    entrada, stop_inicial = 100000, 99800
    t = Trade(1, entrada, tick(0), stop_inicial)
    trailing = 80
    ativacao = 150

    candles = [
        # Avança 100pts — MFE=100, menor que ativação=150
        make_candle(tick(1), 100000, 100100, 99950, 100050, linha_quant=99800),
    ]
    simular_stop_logica(t, candles, trailing_pontos=trailing, trailing_ativacao=ativacao)

    assert not t.trailing_acionado, "Trailing não deveria ter ativado (MFE < ativação)"
    assert t.ponto_stop_atual == stop_inicial, "Stop não deveria ter mudado"
    print("OK test_trailing_ativacao_nao_ativa_antes")


def test_trailing_ativacao_ativa_apos_limiar():
    """Trailing com ativacao=150 deve ativar quando MFE >= 150."""
    entrada, stop_inicial = 100000, 99800
    t = Trade(1, entrada, tick(0), stop_inicial)
    trailing = 80
    ativacao = 150

    candles = [
        # Avança 200pts — MFE=200 >= ativação=150
        make_candle(tick(1), 100000, 100200, 99950, 100150, linha_quant=99800),
    ]
    simular_stop_logica(t, candles, trailing_pontos=trailing, trailing_ativacao=ativacao)

    assert t.trailing_acionado, "Trailing deveria ter ativado (MFE >= ativação)"
    assert t.ponto_stop_atual == 100200 - trailing
    print("OK test_trailing_ativacao_ativa_apos_limiar")


def test_breakeven_seguido_de_trailing():
    """Break-even é acionado primeiro, depois o trailing assume e melhora o stop."""
    entrada, stop_inicial = 100000, 99800
    t = Trade(1, entrada, tick(0), stop_inicial)
    breakeven = 100
    trailing = 80
    ativacao = 150

    candles = [
        # Candle 1: Max=100100 → aciona break-even (stop=100000); Min=100010 > entrada → não fecha
        make_candle(tick(1), 100000, 100100, 100010, 100050, linha_quant=99800),
        # Candle 2: Max=100200 → MFE=200 >= ativação=150, trailing=100120; Min=100130 > 100120 → não fecha
        make_candle(tick(2), 100050, 100200, 100130, 100150, linha_quant=99800),
    ]
    encerrado, _ = simular_stop_logica(t, candles, breakeven_pontos=breakeven,
                                       trailing_pontos=trailing, trailing_ativacao=ativacao)

    assert not encerrado
    assert t.breakeven_acionado
    assert t.trailing_acionado
    # Stop deve ser 100120 (trailing melhorou em relação ao break-even 100000)
    assert t.ponto_stop_atual == 100200 - trailing, \
        f"Stop deveria ser {100200 - trailing}, obtido {t.ponto_stop_atual}"
    print(f"OK test_breakeven_seguido_de_trailing: stop={t.ponto_stop_atual}")


# ─── Execução ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_ajuste()

    test_breakeven_compra_acionado()
    test_breakeven_venda_acionado()
    test_breakeven_nao_acionado_quando_preco_nao_chega()
    test_breakeven_stop_nao_recua_compra()
    test_breakeven_stop_nao_recua_venda()

    test_trailing_sobe_com_preco_compra()
    test_trailing_nao_desce_compra()
    test_trailing_encerra_com_motivo_correto()
    test_trailing_ativacao_nao_ativa_antes()
    test_trailing_ativacao_ativa_apos_limiar()
    test_breakeven_seguido_de_trailing()

    print("\n✅ Todos os testes lógicos passaram!")

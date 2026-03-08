import pandas as pd
import numpy as np
import math
from datetime import time

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

class Trade:
    def __init__(self, direcao, ponto_entrada, hora_entrada, ponto_stop=None, n_contratos=1, tipo_parcial=None, valores_parciais=None):
        """
        Inicializa uma nova operação.
        :param direcao: 1 para Compra, -1 para Venda.
        :param ponto_entrada: Preço de entrada.
        :param hora_entrada: datetime do início.
        :param ponto_stop: Preço de stop inicial (opcional).
        :param n_contratos: Quantidade total de contratos.
        :param tipo_parcial: 'fixa' ou 'risco'.
        :param valores_parciais: Lista de valores (pontos ou fatores RR).
        """
        self.direcao = direcao
        self.ponto_entrada = ponto_entrada
        self.hora_entrada = hora_entrada
        self.ponto_stop_inicial = ponto_stop
        self.n_contratos_total = n_contratos
        self.contratos_abertos = n_contratos
        
        # Alvos para as parciais
        self.alvos = []
        self.risco_pontos = abs(ponto_entrada - ponto_stop) if ponto_stop is not None else 0
        
        if tipo_parcial and valores_parciais:
            for val in valores_parciais:
                if tipo_parcial == 'fixa':
                    alvo = ponto_entrada + (val * direcao)
                elif tipo_parcial == 'risco' and self.risco_pontos > 0:
                    alvo = ponto_entrada + (self.risco_pontos * val * direcao)
                else:
                    continue
                self.alvos.append(alvo)
        
        # Registro de saídas: cada item é (ponto_saida, hora_saida, qtd_contratos)
        
        # Registro de saídas: cada item é (ponto_saida, hora_saida, qtd_contratos)
        self.saidas = []
        
        # Atributos finais (médias ponderadas)
        self.ponto_saida_medio = None # Alias para ponto_saida em trades simples
        self.hora_saida_final = None 
        self.duracao = 0
        self.pontos_totais = 0 # Alias para pontos em trades simples
        self.pontos = 0 # Para compatibilidade com código antigo
        
        # Estatísticas durante a operação
        self.extrema_favor = ponto_entrada
        self.extrema_contra = ponto_entrada
        self.MFE = 0
        self.MAE = 0

        # Stop dinâmico e flags de gestão
        self.ponto_stop_atual = ponto_stop   # Começa igual ao stop inicial; pode ser movido
        self.breakeven_acionado = False
        self.trailing_acionado = False
        self.motivo_saida = ''               # 'STOP_LINHA' | 'BREAKEVEN' | 'TRAILING' | 'HORARIO'

    def update_statistics(self, candle):
        if self.direcao == 1:
            if candle['Max'] > self.extrema_favor: self.extrema_favor = candle['Max']
            if candle['Min'] < self.extrema_contra: self.extrema_contra = candle['Min']
            self.MFE = self.extrema_favor - self.ponto_entrada
            self.MAE = self.extrema_contra - self.ponto_entrada
        else:
            if candle['Min'] < self.extrema_favor: self.extrema_favor = candle['Min']
            if candle['Max'] > self.extrema_contra: self.extrema_contra = candle['Max']
            self.MFE = self.ponto_entrada - self.extrema_favor
            self.MAE = self.ponto_entrada - self.extrema_contra

    def check_partial_exit(self, candle):
        """Checks if any target was hit and registers partial exit."""
        if self.contratos_abertos <= 0:
            return False

        # Verifica se o alvo correspondente ao próximo contrato foi atingido
        idx_alvo = self.n_contratos_total - self.contratos_abertos
        if idx_alvo >= len(self.alvos):
            return False
            
        alvo_atual = self.alvos[idx_alvo]
        hit = False
        
        if self.direcao == 1:
            if candle['Max'] >= alvo_atual:
                hit = True
        else:
            if candle['Min'] <= alvo_atual:
                hit = True
                
        if hit:
            exit_price = alvo_atual
            self.saidas.append((exit_price, candle['Data'], 1))
            self.contratos_abertos -= 1
            return True
        return False

    def close_trade(self, ponto_saida, hora_saida):
        """Finalizes any remaining contracts."""
        if self.contratos_abertos > 0:
            self.saidas.append((ponto_saida, hora_saida, self.contratos_abertos))
            self.contratos_abertos = 0
            
        self.hora_saida_final = hora_saida
        
        # Calcular média ponderada de saída e pontos totais
        soma_produtos = sum(p * q for p, h, q in self.saidas)
        self.ponto_saida_medio = soma_produtos / self.n_contratos_total
        
        soma_pontos = 0
        for p, h, q in self.saidas:
            if self.direcao == 1:
                soma_pontos += (p - self.ponto_entrada) * q
            else:
                soma_pontos += (self.ponto_entrada - p) * q
        
        # Pontos totais acumulados de todos os contratos
        self.pontos_totais = soma_pontos
        self.pontos = self.pontos_totais
        self.ponto_saida = self.ponto_saida_medio # Manteve o alias para o médio
        
        delta = self.hora_saida_final - self.hora_entrada
        self.duracao = delta.total_seconds() / 60

    def to_dict(self):
        hora_eq = self.hora_entrada.time()
        if hora_eq < time(12, 0):
            periodo = 'MANHA'
        elif hora_eq < time(14, 0):
            periodo = 'ALMOCO'
        else:
            periodo = 'TARDE'
            
        return {
            'direcao': 'Compra' if self.direcao == 1 else 'Venda',
            'risco': self.risco_pontos,
            'n_contratos': self.n_contratos_total,
            'periodo': periodo,
            'entrada': self.ponto_entrada,
            'saida': self.ponto_saida,
            'saida_media': self.ponto_saida_medio,
            'inicio': self.hora_entrada,
            'fim': self.hora_saida_final,
            'duracao_min': self.duracao,
            'pontos': self.pontos_totais,
            'mfe': self.MFE,
            'mae': self.MAE,
            'breakeven_acionado': self.breakeven_acionado,
            'trailing_acionado': self.trailing_acionado,
            'motivo_saida': self.motivo_saida,
            'stop_final': self.ponto_stop_atual,
        }

def gerar_relatorio_estatistico(lista_trades):
    if not lista_trades:
        print("Nenhum trade para analisar.")
        return None, None

    df = pd.DataFrame([t.to_dict() for t in lista_trades])
    df['inicio'] = pd.to_datetime(df['inicio'])
    df['Data'] = df['inicio'].dt.date

    total_trades = len(df)
    vitorias = df[df['pontos'] > 0]
    derrotas = df[df['pontos'] <= 0]
    
    win_rate = (len(vitorias) / total_trades) * 100 if total_trades > 0 else 0
    soma_ganhos = vitorias['pontos'].sum()
    soma_perdas = abs(derrotas['pontos'].sum())
    profit_factor = soma_ganhos / soma_perdas if soma_perdas > 0 else float('inf')
    total_pontos = df['pontos'].sum()
    expectativa_matematica = total_pontos / total_trades if total_trades > 0 else 0
    
    df['saldo_acumulado'] = df['pontos'].cumsum()
    df['max_acumulado'] = df['saldo_acumulado'].cummax()
    df['drawdown'] = df['max_acumulado'] - df['saldo_acumulado']
    max_drawdown = df['drawdown'].max()

    stats_globais = {
        'Total Trades': total_trades,
        'Win Rate (%)': round(win_rate, 2),
        'Profit Factor': round(profit_factor, 2),
        'Total Pontos': round(total_pontos, 2),
        'Média por Trade': round(expectativa_matematica, 2),
        'Max Drawdown (Pts)': round(max_drawdown, 2)
    }

    resumo_diario = df.groupby('Data').agg(
        qtd_trades=('pontos', 'count'),
        saldo_pontos=('pontos', 'sum'),
        mfe_medio=('mfe', 'mean'),
        mae_medio=('mae', 'mean')
    ).round(2).reset_index()

    return stats_globais, resumo_diario

from src.engine.stats import estatisticas_trades, segmentar_estatisticas

def gerar_estatisticas_completas(lista_trades):
    """Bridge for backward compatibility."""
    stats = estatisticas_trades(lista_trades)
    # The old function returned (stats_dict, resumo_diario)
    # We can generate a simple daily summary here or just return empty df if not needed
    df = pd.DataFrame([t.to_dict() for t in lista_trades])
    if not df.empty:
        df['inicio'] = pd.to_datetime(df['inicio'])
        df['Data'] = df['inicio'].dt.date
        resumo_diario = df.groupby('Data').agg(
            qtd_trades=('pontos', 'count'),
            saldo_pontos=('pontos', 'sum'),
            mfe_medio=('mfe', 'mean'),
            mae_medio=('mae', 'mean')
        ).round(2).reset_index()
    else:
        resumo_diario = pd.DataFrame()
    return stats, resumo_diario

def analisar_por_periodo(lista_trades):
    """Bridge for backward compatibility using segmentar_estatisticas."""
    df_seg = segmentar_estatisticas(lista_trades, segmentos=['hora'], min_trades=1)
    return df_seg
# funções 'gerar_estatisticas_completas' e 'analisar_por_periodo' agora são wrappers
# definidos no início do arquivo para manter compatibilidade e evitar redundância.


def comparar_resultados(lista_stats, nomes=None, verbose=True):
    """
    Gera uma tabela comparativa a partir de uma lista de dicionários de estatísticas
    (retornados por gerar_estatisticas_completas).
    """
    if not lista_stats:
        return pd.DataFrame()

    if nomes is None:
        nomes = [f"Simulação {i+1}" for i in range(len(lista_stats))]

    colunas_desejadas = [
        "Rank", "Total Trades", "Total Empates", "Win Rate (%)", "Profit Factor",
        "Total Pontos", "Média por Trade", "Max Drawdown (Pts)", "Maior Vitória (pts)",
        "Maior Derrota (pts)", "Média Vencedores (pts)", "Média Perdedores (pts)",
        "Payoff Ratio", "Maior Sequência Ganhos", "Maior Sequência Perdas",
        "Recovery Factor", "Sortino Ratio"
    ]

    linhas = []
    for i, stats in enumerate(lista_stats):
        # Filtra apenas as colunas desejadas que existirem no dict
        dados = {col: stats.get(col, 0) for col in colunas_desejadas}
        # Se Rank não estiver no dict, usa o índice
        if "Rank" not in stats:
            dados["Rank"] = i + 1
        
        # Adiciona o nome/identificador
        dados["Setup"] = nomes[i]
        linhas.append(dados)

    df_comparativo = pd.DataFrame(linhas)
    
    # Reordenar para colocar Setup e Rank primeiro
    cols = ["Setup", "Rank"] + [c for c in colunas_desejadas if c not in ["Rank"]]
    df_comparativo = df_comparativo[cols]

    if verbose:
        print("\n" + "="*120)
        print(f"{' '*45}TABELA COMPARATIVA DE RESULTADOS")
        print("="*120)
        print(df_comparativo.to_string(index=False, justify='right'))
        print("="*120 + "\n")

    return df_comparativo

def imprimir_stats(stats):
    if not stats: return
    print("\n" + "="*45)
    print("         ESTATÍSTICAS GLOBAIS DA ESTRATÉGIA")
    print("="*45)
    for label, valor in stats.items():
        print(f" {label:.<30} {valor}")
    print("="*45 + "\n")

def detalhar_dia(lista_trades, data_alvo):
    """
    Mostra detalhes de todos os trades de um dia específico em formato de tabela.
    """
    trades_do_dia = [t for t in lista_trades if t.hora_entrada.strftime('%Y-%m-%d') == data_alvo]
    
    if not trades_do_dia:
        print(f"\nNenhum trade encontrado para a data {data_alvo}.")
        return

    print(f"\n" + "="*150)
    print(f"{' '*55}RELATÓRIO DE TRADES - DIA {data_alvo}")
    print("="*150)
    
    # Cabeçalho da Tabela
    headers = f"{'#':>3} | {'Dir':<4} | {'Risco':>8} | {'Início':<8} | {'Entrada':>8} | {'Saída F':>8} | {'Dur':>6} | {'P1':>8} | {'P2':>8} | {'P3':>8} | {'Total':>10} | {'MFE':>8} | {'MAE':>8}"
    print(headers)
    print("-" * 150)

    for i, t in enumerate(trades_do_dia, 1):
        dir_str = "C" if t.direcao == 1 else "V"
        risco   = f"{t.risco_pontos:.0f}"
        inicio  = t.hora_entrada.strftime('%H:%M')
        entrada = f"{t.ponto_entrada:.0f}"
        saida_f = f"{t.ponto_saida_medio:.0f}"
        duracao = f"{t.duracao:.1f}"
        
        # Calcular pontos individuais das parciais para exibir nas colunas
        parciais_pts = []
        for p_saida, h_saida, q in t.saidas:
            if t.direcao == 1:
                pts_unit = (p_saida - t.ponto_entrada)
            else:
                pts_unit = (t.ponto_entrada - p_saida)
            
            # Se saiu mais de um contrato no mesmo ponto (ex: stop final), 
            # distribuímos o valor nas colunas de parciais restantes
            for _ in range(q):
                parciais_pts.append(f"{pts_unit:.1f}")

        # Preencher colunas vazias se houver menos de 3 contratos
        while len(parciais_pts) < 3:
            parciais_pts.append("-")
            
        p1    = parciais_pts[0]
        p2    = parciais_pts[1]
        p3    = parciais_pts[2]
        total = f"{t.pontos_totais:.1f}"
        mfe   = f"{t.MFE:.1f}"
        mae   = f"{t.MAE:.1f}"

        row = f"{i:>3} | {dir_str:<4} | {risco:<8} | {inicio:<8} | {entrada:>8} | {saida_f:>8} | {duracao:>6} | {p1:>8} | {p2:>8} | {p3:>8} | {total:>10} | {mfe:>8} | {mae:>8}"
        print(row)

    print("="*150 + "\n")

def detalhar_trades(lista_trades):
    """
    Mostra detalhes de todos os trades de um dia específico em formato de tabela.
    """
    if not lista_trades:
        print("\nNenhum trade encontrado.")
        return

    print("\n" + "="*150)
    print(" " * 65 + "RELATÓRIO DE TRADES")
    print("="*150)
    
    # Cabeçalho da Tabela
    headers = f"{'#':>3} | {'Data':<10} | {'Hora':<8} | {'Dir':<4} | {'Risco':>8} | {'Entrada':>8} | {'Saída F':>8} | {'Dur':>6} | {'P1':>8} | {'P2':>8} | {'P3':>8} | {'Total':>10} | {'MFE':>8} | {'MAE':>8}"
    print(headers)
    print("-" * 150)

    for i, t in enumerate(lista_trades, 1):
        dir_str = "C" if t.direcao == 1 else "V"
        risco   = f"{t.risco_pontos:.0f}"
        data    = t.hora_entrada.strftime('%Y-%m-%d')
        hora_inicio  = t.hora_entrada.strftime('%H:%M')
        entrada = f"{t.ponto_entrada:.0f}"
        saida_f = f"{t.ponto_saida_medio:.0f}"
        duracao = f"{t.duracao:.1f}"
        
        # Calcular pontos individuais das parciais para exibir nas colunas
        parciais_pts = []
        for p_saida, h_saida, q in t.saidas:
            if t.direcao == 1:
                pts_unit = (p_saida - t.ponto_entrada)
            else:
                pts_unit = (t.ponto_entrada - p_saida)
            
            # Se saiu mais de um contrato no mesmo ponto (ex: stop final), 
            # distribuímos o valor nas colunas de parciais restantes
            for _ in range(q):
                parciais_pts.append(f"{pts_unit:.1f}")

        # Preencher colunas vazias se houver menos de 3 contratos
        while len(parciais_pts) < 3:
            parciais_pts.append("-")
            
        p1    = parciais_pts[0]
        p2    = parciais_pts[1]
        p3    = parciais_pts[2]
        total = f"{t.pontos_totais:.1f}"
        mfe   = f"{t.MFE:.1f}"
        mae   = f"{t.MAE:.1f}"

        row = f"{i:>3} | {data:<10} | {hora_inicio:<8} | {dir_str:<4} | {risco:>8} | {entrada:>8} | {saida_f:>8} | {duracao:>6} | {p1:>8} | {p2:>8} | {p3:>8} | {total:>10} | {mfe:>8} | {mae:>8}"
        print(row)

    print("="*150 + "\n")


def exportar_trades_para_excel(lista_trades, arquivo_excel):
    """
    Converte a lista de trades em uma planilha Excel organizada.
    """

    if not lista_trades:
        print("Nenhum trade encontrado.")
        return

    linhas = []

    for i, t in enumerate(lista_trades, 1):
        dir_str = "C" if t.direcao == 1 else "V"
        risco   = t.risco_pontos
        data    = t.hora_entrada.strftime('%Y-%m-%d')
        hora    = t.hora_entrada.strftime('%H:%M')
        entrada = t.ponto_entrada
        saida_f = t.ponto_saida_medio
        duracao = t.duracao
        
        # Calcular pontos individuais das parciais
        parciais_pts = []
        for p_saida, h_saida, q in t.saidas:
            if t.direcao == 1:
                pts_unit = (p_saida - t.ponto_entrada)
            else:
                pts_unit = (t.ponto_entrada - p_saida)

            for _ in range(q):
                parciais_pts.append(pts_unit)

        # Garantir 3 colunas de parciais
        while len(parciais_pts) < 3:
            parciais_pts.append(None)

        linha = {
            "Nº": i,
            "Data": data,
            "Hora": hora,
            "Direção": dir_str,
            "Risco (pts)": risco,
            "Entrada": entrada,
            "Saída Final": saida_f,
            "Duração (min)": duracao,
            "P1 (pts)": parciais_pts[0],
            "P2 (pts)": parciais_pts[1],
            "P3 (pts)": parciais_pts[2],
            "Total (pts)": t.pontos_totais,
            "MFE": t.MFE,
            "MAE": t.MAE,
            "Motivo Saída": t.motivo_saida,
            "Break-even": "Sim" if t.breakeven_acionado else "Não",
            "Trailing": "Sim" if t.trailing_acionado else "Não",
        }

        linhas.append(linha)

    # Criar DataFrame
    df = pd.DataFrame(linhas)

    # Exportar para Excel
    df.to_excel(arquivo_excel, index=False)

    print(f"Arquivo Excel gerado com sucesso: {arquivo_excel}")

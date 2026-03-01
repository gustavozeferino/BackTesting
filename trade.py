from datetime import datetime
import pandas as pd
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
        return {
            'direcao': 'Compra' if self.direcao == 1 else 'Venda',
            'entrada': self.ponto_entrada,
            'saida': self.ponto_saida,
            'saida_media': self.ponto_saida_medio,
            'inicio': self.hora_entrada,
            'fim': self.hora_saida_final,
            'duracao_min': self.duracao,
            'pontos': self.pontos_totais,
            'mfe': self.MFE,
            'mae': self.MAE
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
    headers = f"{'#':>3} | {'Dir':<4} | {'Início':<8} | {'Entrada':>8} | {'Saída F':>8} | {'Dur':>6} | {'P1':>8} | {'P2':>8} | {'P3':>8} | {'Total':>10} | {'MFE':>8} | {'MAE':>8}"
    print(headers)
    print("-" * 150)

    for i, t in enumerate(trades_do_dia, 1):
        dir_str = "C" if t.direcao == 1 else "V"
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

        row = f"{i:>3} | {dir_str:<4} | {inicio:<8} | {entrada:>8} | {saida_f:>8} | {duracao:>6} | {p1:>8} | {p2:>8} | {p3:>8} | {total:>10} | {mfe:>8} | {mae:>8}"
        print(row)

    print("="*150 + "\n")

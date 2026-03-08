import pandas as pd
import numpy as np
import base64
import io
import matplotlib.pyplot as plt
from src.engine.trade import gerar_estatisticas_completas, analisar_por_periodo

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    # Encode em string base64
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_str

def gerar_grafico_curva_patrimonio(df):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df.index, df['saldo_acumulado'], color='blue', label='Saldo Acumulado')
    
    # Sombreado em Drawdown
    if 'max_acumulado' in df.columns:
        ax.fill_between(df.index, df['saldo_acumulado'], df['max_acumulado'], color='red', alpha=0.3, label='Drawdown')
        
    ax.axhline(0, color='black', linewidth=1)
    ax.set_title('Curva de Patrimônio')
    ax.set_xlabel('Trade #')
    ax.set_ylabel('Pontos')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.5)
    return fig_to_base64(fig)

def gerar_grafico_periodos(df_periodos):
    df_p = df_periodos[df_periodos['periodo'] != 'TOTAL']
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # Gráfico 1: Total de Pontos por Período
    colors1 = ['green' if x > 0 else 'red' for x in df_p['total_pontos']]
    ax1.bar(df_p['periodo'], df_p['total_pontos'], color=colors1)
    ax1.set_title('Resultado por Período')
    ax1.axhline(0, color='black')
    
    # Gráfico 2: Win Rate por Período
    ax2.bar(df_p['periodo'], df_p['win_rate'], color='royalblue')
    ax2.axhline(50, color='red', linestyle='--', label='50%')
    ax2.set_title('Win Rate (%) por Período')
    ax2.set_ylim(0, 100)
    ax2.legend()
    
    return fig_to_base64(fig)

def gerar_grafico_distribuicao_mae_mfe(df):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # MAE Histograma
    ax1.hist(df['mae'], bins=20, color='salmon', edgecolor='black')
    mae_medio = df['mae'].mean()
    ax1.axvline(mae_medio, color='red', linestyle='dashed', linewidth=2, label=f'Média: {mae_medio:.1f}')
    ax1.set_title('Distribuição de MAE')
    ax1.legend()
    
    # MFE Histograma
    ax2.hist(df['mfe'], bins=20, color='lightgreen', edgecolor='black')
    mfe_medio = df['mfe'].mean()
    ax2.axvline(mfe_medio, color='green', linestyle='dashed', linewidth=2, label=f'Média: {mfe_medio:.1f}')
    ax2.set_title('Distribuição de MFE')
    ax2.legend()
    
    return fig_to_base64(fig)

def gerar_grafico_scatter_mae_mfe(df):
    fig, ax = plt.subplots(figsize=(8, 6))
    
    vencedores = df[df['pontos'] > 0]
    perdedores = df[df['pontos'] <= 0]
    
    ax.scatter(vencedores['mae'], vencedores['mfe'], color='green', alpha=0.6, label='Vencedor')
    ax.scatter(perdedores['mae'], perdedores['mfe'], color='red', alpha=0.6, label='Perdedor')
    
    ax.set_title('Dispersão MAE x MFE')
    ax.set_xlabel('MAE (Risco Assumido)')
    ax.set_ylabel('MFE (Excursão a Favor)')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.5)
    
    return fig_to_base64(fig)

def gerar_relatorio(lista_trades, output_path='relatorio.html', titulo='Relatório de Backtesting', df_comparativo=None):
    if not lista_trades:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("<html><body><h1>Nenhum trade para relatar</h1></body></html>")
        return output_path
        
    df_trades = pd.DataFrame([t.to_dict() for t in lista_trades])
    # Calcula coluna de acumulado necessária pros gráficos gerais
    df_trades['saldo_acumulado'] = df_trades['pontos'].cumsum()
    df_trades['max_acumulado'] = df_trades['saldo_acumulado'].cummax()
    
    stats_c, _ = gerar_estatisticas_completas(lista_trades)
    df_periodos = analisar_por_periodo(lista_trades)
    
    # Gerando os gráficos em base64
    img_curva = gerar_grafico_curva_patrimonio(df_trades)
    img_periodos = gerar_grafico_periodos(df_periodos)
    img_dist_mae_mfe = gerar_grafico_distribuicao_mae_mfe(df_trades)
    img_scatter = gerar_grafico_scatter_mae_mfe(df_trades)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{titulo}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #fdfdfd; margin: 0; padding: 20px; color: #333; }}
            .container {{ max-width: 1200px; margin: auto; }}
            h1, h2, h3 {{ border-bottom: 2px solid #eaeaea; padding-bottom: 10px; margin-top: 40px; }}
            .nav {{ display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 20px; background: #fff; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: sticky; top: 0; z-index: 100; }}
            .nav a {{ text-decoration: none; color: #007bff; font-weight: bold; font-size: 14px; }}
            .cards {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 30px; }}
            .card {{ background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex: 1; min-width: 150px; text-align: center; border-top: 4px solid #007bff; }}
            .card h4 {{ margin: 0 0 10px 0; color: #666; font-size: 12px; text-transform: uppercase; }}
            .card .value {{ font-size: 24px; font-weight: bold; color: #333; }}
            .section {{ background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow-x: auto; }}
            img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; display: block; margin: 10px auto; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; min-width: 600px; }}
            th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 13px; }}
            th {{ background-color: #f8f9fa; color: #333; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
            tr:hover {{ background-color: #fcfcfc; }}
            .positivo {{ color: #28a745; font-weight: bold; }}
            .negativo {{ color: #dc3545; font-weight: bold; }}
            .comparativo-container table {{ font-size: 11px; }}
            .comparativo-container th {{ background: #e9ecef; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{titulo}</h1>
            
            <div class="nav">
                <a href="#resumo">Painel</a>
                {('<a href="#comparativo">Comparativo</a>' if df_comparativo is not None else '')}
                <a href="#curva">Gráfico</a>
                <a href="#estatisticas">Estatísticas</a>
                <a href="#periodos">Períodos</a>
                <a href="#maemfe">MAE/MFE</a>
                <a href="#trades">Trades</a>
            </div>
    """

    if df_comparativo is not None:
        html += f"""
            <div id="comparativo" class="section comparativo-container">
                <h2>Tabela Comparativa de Estratégias</h2>
                {df_comparativo.to_html(index=False)}
            </div>
        """

    html += f"""
            <div id="resumo" class="cards">
                <div class="card">
                    <h4>Win Rate</h4>
                    <div class="value">{stats_c.get('Win Rate (%)', 0)}%</div>
                </div>
                <div class="card">
                    <h4>Profit Factor</h4>
                    <div class="value">{stats_c.get('Profit Factor', 0)}</div>
                </div>
                <div class="card">
                    <h4>Total Pontos</h4>
                    <div class="value {('positivo' if stats_c.get('Total Pontos', 0) >= 0 else 'negativo')}">{stats_c.get('Total Pontos', 0)}</div>
                </div>
                <div class="card">
                    <h4>Max Drawdown</h4>
                    <div class="value">{stats_c.get('Max Drawdown (Pts)', 0)}</div>
                </div>
                <div class="card">
                    <h4>Média/Trade</h4>
                    <div class="value">{stats_c.get('Média por Trade', 0)}</div>
                </div>
            </div>
            
            <div id="curva" class="section">
                <h2>Curva de Patrimônio</h2>
                <img src="data:image/png;base64,{img_curva}" alt="Curva de Patrimônio">
            </div>
            
            <div id="estatisticas" class="section">
                <h2>Estatísticas Completas</h2>
                <table>
                    <tr><th>Métrica</th><th>Valor</th><th>Métrica</th><th>Valor</th></tr>
                    <tr>
                        <td>Total Trades</td><td>{stats_c.get('Total Trades')}</td>
                        <td>Sharpe Ratio</td><td>{stats_c.get('Sharpe Ratio')}</td>
                    </tr>
                    <tr>
                        <td>Vencedores / Perdedores</td><td>{stats_c.get('Total Vencedores')} / {stats_c.get('Total Perdedores')}</td>
                        <td>Sortino Ratio</td><td>{stats_c.get('Sortino Ratio')}</td>
                    </tr>
                    <tr>
                        <td>Média Vencedores</td><td>{stats_c.get('Média Vencedores (pts)')}</td>
                        <td>Calmar Ratio</td><td>{stats_c.get('Calmar Ratio')}</td>
                    </tr>
                    <tr>
                        <td>Média Perdedores</td><td>{stats_c.get('Média Perdedores (pts)')}</td>
                        <td>Recovery Factor</td><td>{stats_c.get('Recovery Factor')}</td>
                    </tr>
                    <tr>
                        <td>Payoff Ratio</td><td>{stats_c.get('Payoff Ratio')}</td>
                        <td>Maior Sequência de Ganhos / Perdas</td><td>{stats_c.get('Maior Sequência Ganhos')} / {stats_c.get('Maior Sequência Perdas')}</td>
                    </tr>
                    <tr>
                        <td>MAE Médio / MFE Médio</td><td>{stats_c.get('MAE Médio')} / {stats_c.get('MFE Médio')}</td>
                        <td>MAE Efficiency / MFE Efficiency</td><td>{stats_c.get('MAE Efficiency (%)')}% / {stats_c.get('MFE Efficiency (%)')}%</td>
                    </tr>
                </table>
            </div>
            
            <div id="periodos" class="section">
                <h2>Análise por Períodos</h2>
                <img src="data:image/png;base64,{img_periodos}" alt="Períodos">
                <table>
                    <tr>
                        <th>Período</th>
                        <th>Trades</th>
                        <th>Win Rate</th>
                        <th>Total Pontos</th>
                        <th>Profit Factor</th>
                        <th>Max DD</th>
                    </tr>
                    {"".join(f"<tr><td>{row['periodo']}</td><td>{row['total_trades']}</td><td>{row['win_rate']}</td><td class='{('positivo' if row['total_pontos'] >= 0 else 'negativo')}'>{row['total_pontos']}</td><td>{row['profit_factor']}</td><td>{row['max_drawdown']}</td></tr>" for idx, row in df_periodos.iterrows())}
                </table>
            </div>
            
            <div id="maemfe" class="section">
                <h2>Distribuição MAE e MFE</h2>
                <img src="data:image/png;base64,{img_dist_mae_mfe}" alt="Histogramas">
                <br><br>
                <img src="data:image/png;base64,{img_scatter}" alt="Scatter Plot">
            </div>
            
            <div id="trades" class="section">
                <h2>Lista de Trades</h2>
                <table>
                    <tr>
                        <th>Início</th><th>Direção</th><th>Risco</th><th>Entrada</th><th>Saída</th><th>Pontos</th><th>MAE</th><th>MFE</th><th>Motivo Saída</th>
                    </tr>
                    {"".join(f"<tr><td>{row['inicio']}</td><td>{row['direcao']}</td><td>{row['risco']}</td><td>{row['entrada']}</td><td>{row['saida_media']:.1f}</td><td class='{('positivo' if row['pontos'] > 0 else 'negativo')}'>{row['pontos']:.1f}</td><td>{row['mae']}</td><td>{row['mfe']}</td><td>{row['motivo_saida']}</td></tr>" for idx, row in df_trades.iterrows())}
                </table>
            </div>

        </div>
    </body>
    </html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
        
    return output_path

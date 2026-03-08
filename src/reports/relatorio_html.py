import pandas as pd
import numpy as np
import base64
import io
import matplotlib.pyplot as plt
from src.engine.stats import estatisticas_trades, segmentar_estatisticas

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_str

def gerar_grafico_curva_patrimonio(df):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df.index, df['saldo_acumulado'], color='#0d6efd', linewidth=2, label='Saldo Acumulado')
    
    if 'max_acumulado' in df.columns:
        ax.fill_between(df.index, df['saldo_acumulado'], df['max_acumulado'], color='#dc3545', alpha=0.2, label='Drawdown')
        
    ax.axhline(0, color='#212529', linewidth=1, alpha=0.5)
    ax.set_title('Curva de Patrimônio', fontsize=14, fontweight='bold')
    ax.set_xlabel('Trade #')
    ax.set_ylabel('Pontos')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3)
    return fig_to_base64(fig)

def gerar_grafico_mae_mfe_scatter(df):
    fig, ax = plt.subplots(figsize=(10, 7))
    vencedores = df[df['pontos'] > 0]
    perdedores = df[df['pontos'] <= 0]
    
    ax.scatter(vencedores['mae'].abs(), vencedores['mfe'], color='#198754', alpha=0.5, label='Vencedores', s=50)
    ax.scatter(perdedores['mae'].abs(), perdedores['mfe'], color='#dc3545', alpha=0.5, label='Perdedores', s=50)
    
    ax.set_title('MAE vs MFE (Maximum Adverse/Favorable Excursion)', fontsize=14, fontweight='bold')
    ax.set_xlabel('MAE (Risco Máximo Durante o Trade)')
    ax.set_ylabel('MFE (Ganho Máximo Durante o Trade)')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3)
    return fig_to_base64(fig)

def gerar_relatorio(lista_trades, output_path='relatorio.html', titulo='Relatório de Backtesting Avançado'):
    if not lista_trades:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("<html><body class='p-5'><h1>Nenhum trade para relatar</h1></body></html>")
        return output_path
        
    df_trades = pd.DataFrame([t.to_dict() for t in lista_trades])
    df_trades['saldo_acumulado'] = df_trades['pontos'].cumsum()
    df_trades['max_acumulado'] = df_trades['saldo_acumulado'].cummax()
    
    stats_c = estatisticas_trades(lista_trades)
    df_segmentado = segmentar_estatisticas(lista_trades, min_trades=1) # Usamos 1 para mostrar tudo no relatório
    
    img_curva = gerar_grafico_curva_patrimonio(df_trades)
    img_scatter = gerar_grafico_mae_mfe_scatter(df_trades)
    
    # Helper to check if value is numeric and positive/negative
    def get_color_class(val):
        try:
            val = float(val)
            if val > 0: return 'text-success fw-bold'
            if val < 0: return 'text-danger fw-bold'
        except: pass
        return ''

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{titulo}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f8f9fa; color: #212529; }}
            .card {{ border: none; box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075); margin-bottom: 1.5rem; }}
            .card-header {{ background-color: #fff; border-bottom: 1px solid rgba(0,0,0,.125); font-weight: bold; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 700; }}
            .stat-label {{ font-size: 0.875rem; color: #6c757d; text-transform: uppercase; }}
            .nav-pills .nav-link.active {{ background-color: #0d6efd; }}
            .table-sm td, .table-sm th {{ font-size: 0.85rem; }}
            .sticky-top-nav {{ position: sticky; top: 0; z-index: 1020; background: white; padding: 10px 0; border-bottom: 1px solid #dee2e6; }}
        </style>
    </head>
    <body class="bg-light">
        <nav class="sticky-top-nav shadow-sm mb-4">
            <div class="container d-flex justify-content-between align-items-center">
                <h4 class="mb-0">{titulo}</h4>
                <div class="nav nav-pills small">
                    <a class="nav-link" href="#dashboard">Dashboard</a>
                    <a class="nav-link" href="#curva">Gráficos</a>
                    <a class="nav-link" href="#segmentos">Segmentos</a>
                    <a class="nav-link" href="#trades">Lista de Trades</a>
                </div>
            </div>
        </nav>

        <div class="container pb-5">
            <!-- DASHBOARD -->
            <div id="dashboard" class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center p-3">
                        <div class="stat-label">Win Rate</div>
                        <div class="stat-value">{stats_c['Win Rate (%)']:.2f}%</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center p-3">
                        <div class="stat-label">Profit Factor</div>
                        <div class="stat-value text-primary">{stats_c['Profit Factor']:.2f}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center p-3">
                        <div class="stat-label">Total Pontos</div>
                        <div class="stat-value {get_color_class(stats_c['Total Pontos'])}">{stats_c['Total Pontos']:.2f}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center p-3">
                        <div class="stat-label">Max Drawdown</div>
                        <div class="stat-value text-danger">{stats_c['Max Drawdown (Pts)']:.2f}</div>
                    </div>
                </div>
            </div>

            <div class="row">
                <!-- ESTATISTICAS COMPLETAS -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">Métricas de Performance</div>
                        <div class="card-body p-0">
                            <table class="table table-hover mb-0 small">
                                <tbody>
                                    <tr><td>Total de Trades</td><td class="text-end fw-bold">{stats_c['Total Trades']}</td></tr>
                                    <tr><td>Sharpe Ratio (Anualizado)</td><td class="text-end fw-bold">{stats_c['Sharpe Ratio']:.2f}</td></tr>
                                    <tr><td>Sortino Ratio</td><td class="text-end fw-bold">{stats_c['Sortino Ratio']:.2f}</td></tr>
                                    <tr><td>Recovery Factor</td><td class="text-end fw-bold">{stats_c['Recovery Factor']:.2f}</td></tr>
                                    <tr><td>Payoff Ratio</td><td class="text-end fw-bold">{stats_c['Payoff Ratio']:.2f}</td></tr>
                                    <tr><td>Média Vitória / Derrota</td><td class="text-end">{stats_c['Média Vencedores (pts)']:.1f} / {stats_c['Média Perdedores (pts)']:.1f}</td></tr>
                                    <tr><td>Sequência Ganhos / Perdas</td><td class="text-end">{stats_c['Maior Sequência Ganhos']} / {stats_c['Maior Sequência Perdas']}</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                <!-- EFICIENCIA -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">Métricas de Execução (MAE/MFE)</div>
                        <div class="card-body p-0">
                            <table class="table table-hover mb-0 small">
                                <tbody>
                                    <tr><td>MAE Mediano (Calor)</td><td class="text-end fw-bold">{stats_c['MAE mediano']:.1f}</td></tr>
                                    <tr><td>MFE Mediano (Excursão)</td><td class="text-end fw-bold">{stats_c['MFE mediano']:.1f}</td></tr>
                                    <tr><td>MFE Efficiency (%)</td><td class="text-end fw-bold">{stats_c['MFE Efficiency (%)']:.1f}%</td></tr>
                                    <tr><td>MAE Efficiency (%)</td><td class="text-end fw-bold">{stats_c['MAE Efficiency (%)']:.1f}%</td></tr>
                                    <tr><td>Maior Vitória</td><td class="text-end text-success fw-bold">{stats_c['Maior Vitória (pts)']:.1f}</td></tr>
                                    <tr><td>Maior Derrota</td><td class="text-end text-danger fw-bold">{stats_c['Maior Derrota (pts)']:.1f}</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- GRAFICOS -->
            <div id="curva" class="card">
                <div class="card-header">Análise Gráfica</div>
                <div class="card-body text-center">
                    <h6 class="text-muted mb-3">Evolução do Saldo Acumulado</h6>
                    <img src="data:image/png;base64,{img_curva}" class="img-fluid rounded border mb-5" alt="Curva de Patrimônio">
                    <h6 class="text-muted mb-3">Dispersão MAE x MFE (Eficiência)</h6>
                    <img src="data:image/png;base64,{img_scatter}" class="img-fluid rounded border" alt="Scatter Plot MAE/MFE">
                </div>
            </div>

            <!-- SEGMENTACAO -->
            <div id="segmentos" class="card">
                <div class="card-header">Análise Segmentada</div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm table-striped table-hover mb-0">
                            <thead class="table-dark">
                                <tr>
                                    <th>Segmento</th>
                                    <th>Categoria</th>
                                    <th class="text-center">Trades</th>
                                    <th class="text-center">Win Rate</th>
                                    <th class="text-center">Profit Factor</th>
                                    <th class="text-center">Total Pontos</th>
                                    <th class="text-center">Média/Trade</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join(f"<tr><td>{row['Segmento']}</td><td>{row['Categoria']}</td><td class='text-center'>{row['Total Trades']}</td><td class='text-center'>{row['Win Rate (%)']:.2f}%</td><td class='text-center'>{row['Profit Factor']:.2f}</td><td class='text-center {get_color_class(row['Total Pontos'])}'>{row['Total Pontos']:.1f}</td><td class='text-center'>{row['Média por Trade']:.1f}</td></tr>" if row['Total Trades'] > 0 else f"<tr><td>{row['Segmento']}</td><td>{row['Categoria']}</td><td class='text-center'>{row['Total Trades']}</td><td colspan='4' class='text-center text-muted'>NS</td></tr>" for idx, row in df_segmentado.iterrows())}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- LISTA DE TRADES -->
            <div id="trades" class="card">
                <div class="card-header">Detalhamento das Operações</div>
                <div class="card-body p-0">
                    <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                        <table class="table table-sm table-hover mb-0">
                            <thead class="table-light sticky-top">
                                <tr>
                                    <th>Data/Hora</th>
                                    <th>Lado</th>
                                    <th>Entrada</th>
                                    <th>Saída</th>
                                    <th class="text-center">Pontos</th>
                                    <th class="text-center">MAE</th>
                                    <th class="text-center">MFE</th>
                                    <th>Motivo</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join(f"<tr><td>{str(row['inicio'])[:16]}</td><td>{row['direcao']}</td><td>{row['entrada']:.0f}</td><td>{row['saida_media']:.0f}</td><td class='text-center {get_color_class(row['pontos'])}'>{row['pontos']:.1f}</td><td class='text-center text-danger'>{row['mae']:.0f}</td><td class='text-center text-success'>{row['mfe']:.0f}</td><td><small>{row['motivo_saida']}</small></td></tr>" for idx, row in df_trades.iterrows())}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
        
    return output_path

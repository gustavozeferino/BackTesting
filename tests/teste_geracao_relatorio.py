from src.reports.relatorio_html import gerar_relatorio
from tests.test_analise_parametros import get_test_trades

trades = get_test_trades()
output = gerar_relatorio(trades, "teste_relatorio.html")
print(f"Relatorio gerado em {output}")

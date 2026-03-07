import argparse
import sys
import pandas as pd
from datetime import datetime
from src.database.db_manager import load_from_sqlite_to_pandas, upload_excel_to_sqlite
from src.engine.operacional import simular_operacional, executar_backtest_completo
from src.analysis.analise_parametros import resumo_analises, analisar_distribuicao_mae_mfe
from src.reports.relatorio_html import gerar_relatorio
from src.engine.trade import gerar_estatisticas_completas, imprimir_stats

def main():
    parser = argparse.ArgumentParser(description="BackTesting Framework - Professional CLI")
    
    # Core Actions
    parser.add_argument("--upload", type=str, help="Upload Excel file to database (provide file path)")
    parser.add_argument("--run", action="store_true", help="Run the backtest simulation")
    parser.add_argument("--report", action="store_true", help="Generate HTML report from simulation results")
    parser.add_argument("--optimize", action="store_true", help="Run parameter optimization analysis")
    parser.add_argument("--all", action="store_true", help="Run full workflow (run, optimize, report)")
    
    # Parameters
    parser.add_argument("--contracts", type=int, default=2, help="Number of contracts (default: 2)")
    parser.add_argument("--be", type=int, help="Break-even points")
    parser.add_argument("--stop-max", type=int, help="Maximum stop points")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--title", type=str, default="Backtest results", help="Title for the report")
    parser.add_argument("--output", type=str, default="output/relatorio.html", help="Output path for HTML report")

    args = parser.parse_args()

    # Load data
    try:
        df = load_from_sqlite_to_pandas().sort_values('Data').reset_index(drop=True)
    except Exception as e:
        print(f"Error loading database: {e}")
        if not args.upload:
            print("Try running with --upload <file.xlsx> first.")
            return

    if args.upload:
        print(f"Uploading {args.upload} to database...")
        upload_excel_to_sqlite(args.upload)
        print("Upload complete.")
        if not (args.run or args.all or args.optimize or args.report):
            return
        # Reload DF after upload
        df = load_from_sqlite_to_pandas().sort_values('Data').reset_index(drop=True)

    params = {
        'n_contratos': args.contracts,
        'verbose': args.verbose,
        'breakeven_pontos': args.be,
        'stop_max': args.stop_max
    }

    results = []

    if args.run or args.all:
        print(f"Running simulation with {args.contracts} contracts...")
        results = simular_operacional(df, **params)
        stats_c, resumo_d = gerar_estatisticas_completas(results)
        imprimir_stats(stats_c) 
        print(f"Simulation finished. {len(results)} trades executed.")

    if (args.optimize or args.all) and results:
        resumo_analises(results)
        analisar_distribuicao_mae_mfe(results)

    if (args.report or args.all) and results:
        print(f"Generating HTML report: {args.output}")
        # Ensure output directory exists
        import os
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        gerar_relatorio(results, args.output, args.title)
        print("Report ready.")

    if not any([args.upload, args.run, args.report, args.optimize, args.all]):
        parser.print_help()

if __name__ == "__main__":
    main()

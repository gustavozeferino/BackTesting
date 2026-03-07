import json
import os
import random
import multiprocessing
import numpy as np
import pandas as pd
from datetime import time, datetime, timedelta
import matplotlib.pyplot as plt

from deap import base, creator, tools, algorithms
from src.engine.operacional import simular_operacional
from src.engine.trade import gerar_estatisticas_completas, imprimir_stats
from src.analysis.analise_parametros import analisar_distribuicao_mae_mfe
from src.reports.relatorio_html import gerar_relatorio

# Configuracoes Globais do Otimizador
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'optimization_config.json')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_otimizador = json.load(f)

# Funcoes de conversao
def decode_time(base_time_str, steps, step_minutes):
    """Converte hora minima + N passos em objeto datetime.time"""
    base_time = datetime.strptime(base_time_str, "%H:%M")
    delta = timedelta(minutes=steps * step_minutes)
    final_time = (base_time + delta).time()
    return final_time

def decodificar_individuo(individuo):
    params = config_otimizador['parametros']
    
    # 0: n_contratos -> FIXED TO 2
    n_contratos = 2
    
    # 1: tipo_parcial
    tipo_parcial_idx = int(individuo[0]) % len(params['tipo_parcial']['opcoes'])
    tipo_parcial = params['tipo_parcial']['opcoes'][tipo_parcial_idx]
    
    # 2: Valor Parcial (UNICA PARCIAL)
    if tipo_parcial == 'fixa':
        val1 = int(params['valores_parciais_f1']['min'] + individuo[1] * params['valores_parciais_f1']['step'])
    else: # risco
        val1 = params['valores_parciais_r1']['min'] + individuo[1] * params['valores_parciais_r1']['step']
        val1 = round(val1, 1)

    valores_parciais = [val1] # Apenas uma parcial
    
    # 3: breakeven
    breakeven = int(params['breakeven_pontos']['min'] + individuo[2] * params['breakeven_pontos']['step'])
    
    # 4: stop_max
    stop_max = int(params['stop_max']['min'] + individuo[3] * params['stop_max']['step'])
    
    # 5: horario_inicial
    horario_inicial = decode_time(params['horario_inicial']['min'], individuo[4], params['horario_inicial']['step_minutos'])
    
    # 6: horario_final
    horario_final = decode_time(params['horario_final']['min'], individuo[5], params['horario_final']['step_minutos']) 

    return {
        'n_contratos': n_contratos,
        'tipo_parcial': tipo_parcial,
        'valores_parciais': valores_parciais,
        'breakeven_pontos': breakeven,
        'stop_max': stop_max,
        'horario_inicial': horario_inicial,
        'horario_final': horario_final,
        'verbose': False
    }

def fitness_function(individuo, df):
    """
    Funcao objetivo hibrida (Fitness) top-level para pickling no multiprocessing.
    """
    params = decodificar_individuo(individuo)
    
    try:
        trades = simular_operacional(df, **params)
        
        min_trades = config_otimizador['restricoes'].get('min_trades', 50)
        if len(trades) < min_trades:
            return (0.0,)
            
        stats_c, _ = gerar_estatisticas_completas(trades)
        
        rec_factor = stats_c.get('Recovery Factor', 0)
        if isinstance(rec_factor, str) and rec_factor == 'inf':
            rec_factor = 100 # cap to avoid breaking algorithms
            
        pf = stats_c.get('Profit Factor', 0)
        if isinstance(pf, str) and pf == 'inf':
            pf = 100
            
        score = pf
        #score = rec_factor * pf
        
        # Penalidades por SQN baixo ou negativo
        #sqn = stats_c.get('SQN', 0)
        #if sqn < 0:
        #    score *= 0.1
            
        return (score,)
    except Exception as e:
        print(f"Erro na simulacao: {e}")
        return (0.0,)

# Configuracao DEAP
def configurar_deap():
    if hasattr(creator, "FitnessMax"):
        del creator.FitnessMax
    if hasattr(creator, "Individual"):
        del creator.Individual
        
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)

    toolbox = base.Toolbox()
    params = config_otimizador['parametros']
    
    def gen_int_range(min_v, max_v, step):
        if step == 0: return 0
        return int((max_v - min_v) / step)

    def gen_horario_range(min_str, max_str, step_min):
        t1 = datetime.strptime(min_str, "%H:%M")
        t2 = datetime.strptime(max_str, "%H:%M")
        diff = (t2 - t1).seconds / 60
        return int(diff / step_min)

    # Genes:
    # 0: tipo_parcial index
    # 1: valor_parcial index (max entre fixa e risco)
    # 2: breakeven index
    # 3: stop_max index
    # 4: horario_inicial index
    # 5: horario_final-offset index
    
    max_idx = {
        0: len(params['tipo_parcial']['opcoes']) - 1,
        1: max(gen_int_range(params['valores_parciais_f1']['min'], params['valores_parciais_f1']['max'], params['valores_parciais_f1']['step']), 
               gen_int_range(params['valores_parciais_r1']['min'], params['valores_parciais_r1']['max'], params['valores_parciais_r1']['step'])),
        2: gen_int_range(params['breakeven_pontos']['min'], params['breakeven_pontos']['max'], params['breakeven_pontos']['step']),
        3: gen_int_range(params['stop_max']['min'], params['stop_max']['max'], params['stop_max']['step']),
        4: gen_horario_range(params['horario_inicial']['min'], params['horario_inicial']['max'], params['horario_inicial']['step_minutos']),
        5: gen_horario_range(params['horario_final']['min'], params['horario_final']['max'], params['horario_final']['step_minutos']),
    }

    # Calculo do espaco combinatorial total
    total_combinacoes = 1
    for i in range(len(max_idx)):
        total_combinacoes *= (max_idx[i] + 1)
    
    print(f"\n====================================================")
    print(f"Espaço Amostral de Parâmetros: {total_combinacoes:,} combinações")
    print(f"====================================================\n")

    toolbox.register("attr_0", random.randint, 0, max_idx[0])
    toolbox.register("attr_1", random.randint, 0, max_idx[1])
    toolbox.register("attr_2", random.randint, 0, max_idx[2])
    toolbox.register("attr_3", random.randint, 0, max_idx[3])
    toolbox.register("attr_4", random.randint, 0, max_idx[4])
    toolbox.register("attr_5", random.randint, 0, max_idx[5])

    toolbox.register("individual", tools.initCycle, creator.Individual,
                     (toolbox.attr_0, toolbox.attr_1, toolbox.attr_2, 
                      toolbox.attr_3, toolbox.attr_4, toolbox.attr_5), n=1)
                      
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    def mutUniformIntBound(individual, low, up, indpb):
        for i, (l, u) in enumerate(zip(low, up)):
            if random.random() < indpb:
                individual[i] = random.randint(l, u)
        return individual,

    low_bounds = [0] * 6
    up_bounds = [max_idx[i] for i in range(6)]
    
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", mutUniformIntBound, low=low_bounds, up=up_bounds, indpb=0.2)
    toolbox.register("select", tools.selTournament, tournsize=3)
    
    return toolbox

# Wrapper class para pular a serializacao da df
class Evaluator:
    def __init__(self, df):
        self.df = df
    def __call__(self, individual):
        return fitness_function(individual, self.df)

# --- RELATÓRIO E EXPORTAÇÃO ---
def gerar_relatorio_otimizacao(results, logbook, top_n=20):
    """Gera o HTML e o gráfico de convergência."""
    os.makedirs('output', exist_ok=True)
    
    # 1. Gráfico
    try:
        gen = logbook.select("gen")
        plt.figure(figsize=(10, 5))
        plt.plot(gen, logbook.select("max"), 'b-', label='Máximo Score', linewidth=2)
        plt.plot(gen, logbook.select("avg"), 'r--', label='Média População')
        plt.title('Convergência do Algoritmo Genético')
        plt.xlabel('Geração')
        plt.ylabel('Fitness Score (Híbrido)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig('output/convergence_plot.png')
        plt.close()
    except Exception as e:
        print(f"Erro ao gerar gráfico: {e}")

    # 2. HTML
    html = """<html><head><meta charset="utf-8"><style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; color: #e0e0e0; padding: 30px; }
        h1 { color: #00ff88; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin: 25px 0; background: #1e1e1e; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        th, td { padding: 15px; border: 1px solid #333; text-align: left; }
        th { background: #252525; color: #00ff88; text-transform: uppercase; font-size: 0.9em; letter-spacing: 1px; }
        tr:hover { background: #2a2a2a; }
        .fitness { font-weight: bold; color: #00ff88; font-family: monospace; font-size: 1.1em; }
        .rank-1 { background: rgba(0, 255, 136, 0.1) !important; }
        img { display: block; margin: 20px auto; max-width: 90%; border: 1px solid #333; border-radius: 5px; }
    </style></head><body>
    <h1>Otimização GA - Top Configurações</h1>
    <table><tr><th>Rank</th><th>Fitness</th><th>Contratos</th><th>Parcial</th><th>Valores</th><th>BE</th><th>StopMax</th><th>Horário Operacional</th></tr>"""
    
    for i, r in enumerate(results[:top_n]):
        p = r['params']
        rank_class = "rank-1" if r['rank'] == 1 else ""
        html += f"<tr class='{rank_class}'><td>{r['rank']}</td><td class='fitness'>{r['fitness']:.2f}</td><td>{p['n_contratos']}</td>"
        html += f"<td>{p['tipo_parcial']}</td><td>{p['valores_parciais']}</td><td>{p['breakeven_pontos']}</td>"
        html += f"<td>{p['stop_max']}</td><td>{p['horario_inicial']} - {p['horario_final']}</td></tr>"
    
    html += '</table><h2>Evolução da Convergência</h2><img src="convergence_plot.png"></body></html>'
    
    with open('output/optimization_report.html', 'w', encoding='utf-8') as f:
        f.write(html)

def otimizar(df, n_workers=None, pop_size=None, ngen=None):
    if pop_size is None: pop_size = config_otimizador.get("populacao", 20)
    if ngen is None: ngen = config_otimizador.get("geracoes", 10)
    
    print(f"\nIniciando Algoritmo Genético (DEAP)")
    print(f"Populacao: {pop_size} | Geracoes: {ngen} | Workers: {n_workers or multiprocessing.cpu_count()}")
    
    toolbox = configurar_deap()
    pool = multiprocessing.Pool(processes=n_workers)
    
    evaluator = Evaluator(df)
    toolbox.register("map", pool.map)
    toolbox.register("evaluate", evaluator)

    pop = toolbox.population(n=pop_size)
    hof = tools.HallOfFame(20) # Aumentado para o relatório HTML top 20
    
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("std", np.std)
    stats.register("min", np.min)
    stats.register("max", np.max)

    logbook = tools.Logbook()
    logbook.header = "gen", "evals", "std", "min", "avg", "max"

    try:
        print("\nEvoluindo gerações...")
        # Evaluate initialization
        invalid_ind = [ind for ind in pop if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
            
        hof.update(pop)
        record = stats.compile(pop)
        logbook.record(gen=0, evals=len(invalid_ind), **record)
        print(logbook.stream)
        
        for gen in range(1, ngen + 1):
            offspring = toolbox.select(pop, len(pop))
            offspring = list(map(toolbox.clone, offspring))
    
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < 0.5:
                    toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values
    
            for mutant in offspring:
                if random.random() < 0.2:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values
    
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
    
            pop[:] = offspring
            hof.update(pop)
            record = stats.compile(pop)
            logbook.record(gen=gen, evals=len(invalid_ind), **record)
            print(logbook.stream)
            
    finally:
        pool.close()
        pool.join()
        
    print("\nOtimizacao finalizada!")
    
    # Preparar resultados
    results = []
    for i, ind in enumerate(hof):
        params = decodificar_individuo(ind)
        params_serializable = params.copy()
        params_serializable['horario_inicial'] = params['horario_inicial'].strftime("%H:%M")
        params_serializable['horario_final'] = params['horario_final'].strftime("%H:%M")
        
        results.append({
            "rank": i + 1,
            "fitness": ind.fitness.values[0],
            "params": params_serializable
        })
        
    # Exportar JSON
    with open('output/optimization_result.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
        
    # Gerar Relatorio e Grafico
    gerar_relatorio_otimizacao(results, logbook, top_n=20)
    
    # EXIBIR ESTATISTICAS COMPLETAS DO MELHOR RESULTADO
    print("\n" + "="*50)
    print("MELHOR SOLUÇÃO ENCONTRADA - ESTATÍSTICAS DETALHADAS")
    print("="*50)
    best_params = decodificar_individuo(hof[0])
    best_trades = simular_operacional(df, **best_params)
    stats_c, _ = gerar_estatisticas_completas(best_trades)
    imprimir_stats(stats_c)
    analisar_distribuicao_mae_mfe(best_trades)
    imprimir_parametros_trading(results[0]['params'])

    output_html = '/output/relatorio_melhor_solucao.html'
    gerar_relatorio(best_trades, output_html, titulo="Solução com melhor fator de lucro")
    print(f"\n[OK] Relatório HTML gerado: {output_html}")

    return results


def imprimir_parametros_trading(params):
    """
    Imprime os parâmetros de otimização de forma formatada e organizada.
    """
    # Cores/Estilos básicos (ANSI)
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    print(f"\n{BOLD}{'='*40}{RESET}")
    print(f"{BOLD}{CYAN}      CONFIGURAÇÃO DO SETUP{RESET}")
    print(f"{BOLD}{'='*40}{RESET}")

    # Grupo: Operacional
    print(f"{BOLD}[OPERACIONAL]{RESET}")
    print(f"  • Contratos: {GREEN}{params['n_contratos']}{RESET}")
    print(f"  • Stop Máximo: {GREEN}{params['stop_max']} pts{RESET}")
    print(f"  • Breakeven: {GREEN}{params['breakeven_pontos']} pts{RESET}")

    # Grupo: Alvos/Parciais
    print(f"\n{BOLD}[ALVOS]{RESET}")
    print(f"  • Tipo Parcial: {params['tipo_parcial'].capitalize()}")
    parciais = " | ".join([f"{v} pts" for v in params['valores_parciais']])
    print(f"  • Valores: {GREEN}{parciais}{RESET}")

    # Grupo: Horários
    print(f"\n{BOLD}[JANELA DE TEMPO]{RESET}")
    print(f"  • Início: {params['horario_inicial']}")
    print(f"  • Fim:    {params['horario_final']}")
    
    print(f"{BOLD}{'='*40}{RESET}\n")    
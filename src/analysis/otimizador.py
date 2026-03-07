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
from src.engine.trade import gerar_estatisticas_completas

# Configuracoes Globais do Otimizador
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'optimization_config.json')

with open(CONFIG_PATH, 'r') as f:
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
    
    # 0: n_contratos
    n_contratos = int(params['n_contratos']['min'] + individuo[0] * params['n_contratos']['step'])
    
    # 1: tipo_parcial
    tipo_parcial_idx = int(individuo[1]) % len(params['tipo_parcial']['opcoes'])
    tipo_parcial = params['tipo_parcial']['opcoes'][tipo_parcial_idx]
    
    # Valores Parciais (baseado no tipo)
    if tipo_parcial == 'fixa':
        val1 = int(params['valores_parciais_f1']['min'] + individuo[2] * params['valores_parciais_f1']['step'])
        val2 = int(params['valores_parciais_f2']['min'] + (individuo[2] + individuo[3]) * params['valores_parciais_f2']['step']) # Garantir que val2 > val1
    else: # risco
        val1 = params['valores_parciais_r1']['min'] + individuo[2] * params['valores_parciais_r1']['step']
        val2 = params['valores_parciais_r2']['min'] + (individuo[2] + individuo[3]) * params['valores_parciais_r2']['step']
        val1 = round(val1, 1)
        val2 = round(val2, 1)

    valores_parciais = [val1, val2]
    
    # 4: breakeven
    breakeven = int(params['breakeven_pontos']['min'] + individuo[4] * params['breakeven_pontos']['step'])
    
    # 5: stop_max
    stop_max = int(params['stop_max']['min'] + individuo[5] * params['stop_max']['step'])
    
    # 6: horario_inicial
    horario_inicial = decode_time(params['horario_inicial']['min'], individuo[6], params['horario_inicial']['step_minutos'])
    
    # 7: horario_final
    horario_final = decode_time(params['horario_final']['min'], (individuo[6] + 1 + individuo[7]), params['horario_final']['step_minutos']) # garantir final > inicial

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
        
        min_trades = config_otimizador['restricoes'].get('min_trades', 30)
        if len(trades) < min_trades:
            return (0.0,)
            
        stats_c, _ = gerar_estatisticas_completas(trades)
        
        rec_factor = stats_c.get('Recovery Factor', 0)
        if isinstance(rec_factor, str) and rec_factor == 'inf':
            rec_factor = 100 # cap to avoid breaking algorithms
            
        pf = stats_c.get('Profit Factor', 0)
        if isinstance(pf, str) and pf == 'inf':
            pf = 100
            
        score = rec_factor * pf
        
        # Penalidades por SQN baixo ou negativo
        sqn = stats_c.get('SQN', 0)
        if sqn < 0:
            score *= 0.1
            
        return (score,)
    except Exception as e:
        print(f"Erro na simulacao: {e}")
        return (0.0,)

# Configuracao DEAP (chamada apenas durante a otimizacao para evitar recriacoes globais conflitantes)
def configurar_deap():
    if hasattr(creator, "FitnessMax"):
        del creator.FitnessMax
    if hasattr(creator, "Individual"):
        del creator.Individual
        
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)

    toolbox = base.Toolbox()

    params = config_otimizador['parametros']
    
    # Limites para geracao de aleatorios (indices inteiros que multiplicam o step)
    
    def gen_int_range(min_v, max_v, step):
        if hasattr(min_v, 'time') or ':' in str(min_v): return 0 # time is handled separately
        return int((max_v - min_v) / step)

    def gen_horario_range(min_str, max_str, step_min):
        t1 = datetime.strptime(min_str, "%H:%M")
        t2 = datetime.strptime(max_str, "%H:%M")
        diff = (t2 - t1).seconds / 60
        return int(diff / step_min)

    max_idx = {
        0: gen_int_range(params['n_contratos']['min'], params['n_contratos']['max'], params['n_contratos']['step']),
        1: len(params['tipo_parcial']['opcoes']) - 1,
        2: max(gen_int_range(params['valores_parciais_f1']['min'], params['valores_parciais_f1']['max'], params['valores_parciais_f1']['step']), 
               int((params['valores_parciais_r1']['max'] - params['valores_parciais_r1']['min']) / params['valores_parciais_r1']['step'])),
        3: max(gen_int_range(params['valores_parciais_f2']['min'], params['valores_parciais_f2']['max'], params['valores_parciais_f2']['step']),
               int((params['valores_parciais_r2']['max'] - params['valores_parciais_r2']['min']) / params['valores_parciais_r2']['step'])),
        4: gen_int_range(params['breakeven_pontos']['min'], params['breakeven_pontos']['max'], params['breakeven_pontos']['step']),
        5: gen_int_range(params['stop_max']['min'], params['stop_max']['max'], params['stop_max']['step']),
        6: gen_horario_range(params['horario_inicial']['min'], params['horario_inicial']['max'], params['horario_inicial']['step_minutos']),
        7: gen_horario_range(params['horario_final']['min'], params['horario_final']['max'], params['horario_final']['step_minutos']),
    }

    toolbox.register("attr_0", random.randint, 0, max_idx[0])
    toolbox.register("attr_1", random.randint, 0, max_idx[1])
    toolbox.register("attr_2", random.randint, 0, max_idx[2])
    toolbox.register("attr_3", random.randint, 0, max_idx[3])
    toolbox.register("attr_4", random.randint, 0, max_idx[4])
    toolbox.register("attr_5", random.randint, 0, max_idx[5])
    toolbox.register("attr_6", random.randint, 0, max_idx[6])
    toolbox.register("attr_7", random.randint, 0, max_idx[7])

    toolbox.register("individual", tools.initCycle, creator.Individual,
                     (toolbox.attr_0, toolbox.attr_1, toolbox.attr_2, toolbox.attr_3,
                      toolbox.attr_4, toolbox.attr_5, toolbox.attr_6, toolbox.attr_7), n=1)
                      
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    # Mutation bounds
    def mutUniformIntBound(individual, low, up, indpb):
        for i, (l, u) in enumerate(zip(low, up)):
            if random.random() < indpb:
                individual[i] = random.randint(l, u)
        return individual,

    low_bounds = [0] * 8
    up_bounds = [max_idx[i] for i in range(8)]
    
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

def otimizar(df, n_workers=None):
    from functools import partial
    
    pop_size = config_otimizador.get("populacao", 20)
    ngen = config_otimizador.get("geracoes", 10)
    
    print(f"\nIniciando Algoritmo Genético (DEAP)")
    print(f"Populacao: {pop_size} | Geracoes: {ngen} | Workers: {n_workers or multiprocessing.cpu_count()}")
    
    toolbox = configurar_deap()
    
    # Multiprocessing pool
    pool = multiprocessing.Pool(processes=n_workers)
    
    # map parallel
    evaluator = Evaluator(df)
    toolbox.register("map", pool.map)
    toolbox.register("evaluate", evaluator)

    pop = toolbox.population(n=pop_size)
    hof = tools.HallOfFame(10) # Guarda os top 10
    
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("std", np.std)
    stats.register("min", np.min)
    stats.register("max", np.max)

    logbook = tools.Logbook()
    logbook.header = "gen", "evals", "std", "min", "avg", "max"

    try:
        # Loop manual para adicionar TQDM progress bar
        print("\nProgresso da Otimizacao:")
        
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
            # Select the next generation individuals
            offspring = toolbox.select(pop, len(pop))
            offspring = list(map(toolbox.clone, offspring))
    
            # Apply crossover and mutation
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < 0.5:
                    toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values
    
            for mutant in offspring:
                if random.random() < 0.2:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values
    
            # Evaluate the individuals with an invalid fitness
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
    
            # Update population
            pop[:] = offspring
            hof.update(pop)
            
            record = stats.compile(pop)
            logbook.record(gen=gen, evals=len(invalid_ind), **record)
            print(logbook.stream)
            
    finally:
        pool.close()
        pool.join()
        
    print("\nOtimizacao finalizada!")
    
    # Save results
    results = []
    for i, ind in enumerate(hof):
        params = decodificar_individuo(ind)
        # Convert times to string for JSON serialization
        params['horario_inicial'] = params['horario_inicial'].strftime("%H:%M")
        params['horario_final'] = params['horario_final'].strftime("%H:%M")
        
        results.append({
            "rank": i + 1,
            "fitness": ind.fitness.values[0],
            "params": params
        })
        
    os.makedirs('output', exist_ok=True)
    with open('output/optimization_result.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    # Plot Convergence Graph
    gen = logbook.select("gen")
    fit_max = logbook.select("max")
    fit_avg = logbook.select("avg")
    
    plt.figure(figsize=(10, 6))
    plt.plot(gen, fit_max, 'b-', label='Maximum Fitness', linewidth=2)
    plt.plot(gen, fit_avg, 'r--', label='Average Fitness')
    plt.title('Genetic Algorithm Convergence')
    plt.xlabel('Generation')
    plt.ylabel('Fitness (Hybrid Score)')
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('output/convergence_plot.png')
    
    # HTML Report
    html_content = f"""
    <html>
    <head>
        <title>Optimization Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #1a1a1a; color: #ffffff; padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #444; padding: 10px; text-align: left; }}
            th {{ background-color: #333; }}
            tr:nth-child(even) {{ background-color: #222; }}
            img {{ max-width: 100%; height: auto; margin-top: 20px; border: 1px solid #444; }}
        </style>
    </head>
    <body>
        <h1>Optimization Results - Top 10 Configurations</h1>
        <p>Sorted by Hybrid Score (Recovery Factor * Profit Factor * SQN penalty)</p>
        <table>
            <tr>
                <th>Rank</th>
                <th>Fitness</th>
                <th>Contratos</th>
                <th>Tipo Parcial</th>
                <th>Valores Parciais</th>
                <th>Breakeven</th>
                <th>Stop Max</th>
                <th>Horarios</th>
            </tr>
    """
    for res in results:
        p = res['params']
        html_content += f"""
            <tr>
                <td>{res['rank']}</td>
                <td>{res['fitness']:.2f}</td>
                <td>{p['n_contratos']}</td>
                <td>{p['tipo_parcial']}</td>
                <td>{p['valores_parciais']}</td>
                <td>{p['breakeven_pontos']}</td>
                <td>{p['stop_max']}</td>
                <td>{p['horario_inicial']} - {p['horario_final']}</td>
            </tr>
        """
    html_content += """
        </table>
        <h2>Convergence</h2>
        <img src="convergence_plot.png" alt="Convergence Graph">
    </body>
    </html>
    """
    with open('output/optimization_report.html', 'w') as f:
        f.write(html_content)
        
    print("\n================== TOP RESULT ==================")
    best = results[0]
    print(f"Fitness: {best['fitness']:.2f}")
    print(f"Parameters: {best['params']}")
    print("================================================")
    print("Salvo em: output/optimization_result.json e optimization_report.html")
    
    return results




# --- RELATÓRIO E EXPORTAÇÃO ---

def gerar_relatorio_otimizacao(results, logbook):
    """Gera o HTML e o gráfico de convergência."""
    os.makedirs('output', exist_ok=True)
    
    # 1. Gráfico
    gen = logbook.select("gen")
    plt.figure(figsize=(10, 5))
    plt.plot(gen, logbook.select("max"), 'b-', label='Máximo Score', linewidth=2)
    plt.plot(gen, logbook.select("avg"), 'r--', label='Média População')
    plt.title('Convergência do Algoritmo Genético')
    plt.xlabel('Geração')
    plt.ylabel('Fitness Score')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('output/convergence_plot.png')
    plt.close()

    # 2. HTML
    html = """<html><head><style>
        body { font-family: sans-serif; background: #121212; color: white; padding: 20px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; background: #1e1e1e; }
        th, td { padding: 12px; border: 1px solid #333; text-align: left; }
        th { background: #252525; color: #00ff88; }
        tr:hover { background: #2a2a2a; }
        .fitness { font-weight: bold; color: #00ff88; }
    </style></head><body>
    <h1>Top 10 Configurações Encontradas</h1>
    <table><tr><th>Rank</th><th>Fitness</th><th>Contratos</th><th>Parcial</th><th>Valores</th><th>BE</th><th>StopMax</th><th>Horário</th></tr>"""
    
    for r in results:
        p = r['params']
        html += f"<tr><td>{r['rank']}</td><td class='fitness'>{r['fitness']:.2f}</td><td>{p['n_contratos']}</td>"
        html += f"<td>{p['tipo_parcial']}</td><td>{p['valores_parciais']}</td><td>{p['breakeven_pontos']}</td>"
        html += f"<td>{p['stop_max']}</td><td>{p['horario_inicial']} - {p['horario_final']}</td></tr>"
    
    html += '</table><h2>Gráfico de Evolução</h2><img src="convergence_plot.png"></body></html>'
    
    with open('output/optimization_report.html', 'w', encoding='utf-8') as f:
        f.write(html)
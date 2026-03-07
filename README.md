# BackTesting Framework

Um framewok completo de simulação e otimização de estratégias de trading (Backtesting) com análise avançada de performance e Algoritmos Genéticos.

## 📁 Estrutura do Projeto

A arquitetura foi modularizada para escalabilidade e clareza:

```
BackTesting/
├── config/                  # Arquivos JSON e YML (testes_risco.yml, optimization_config.json)
├── data/                    # Banco de dados SQLite e planilhas de entrada
├── output/                  # Relatórios HTML gerados e gráficos da otimização
├── src/                     # Código Fonte
│   ├── analysis/            # Módulo de otimização (GA) e análises estatísticas (SQN, MAE/MFE)
│   ├── database/            # Gerenciador de conexão com o SQLite (db_manager.py)
│   ├── engine/              # Core do backtesting (trade.py e operacional.py)
│   ├── reports/             # Scripts para geração de PDF/HTML
│   └── utils/               # Configurações de sistema e gerenciamento de pastas
├── tests/                   # Suite de Testes Automatizados (Pytest)
├── main.py                  # Entry Point único por CLI (Comandos de Terminal)
└── README.md                # Esta documentação
```

## 🚀 Como Utilizar (CLI via `main.py`)

A interação principal ocorre através do terminal com suporte a argumentos detalhados.

### 1. Ingestão de Dados
Carrega dados históricos de Excel (OHLC + Indicadores) e popula o SQLite.
```bash
python main.py --upload "C:\caminho\para\arquivo.xlsx"
```

### 2. Rodar apenas o Backtest (Simulação Base)
Roda os parâmetros defalt e exibe estatísticas vitais no console.
```bash
python main.py --run --contracts 3 --be 150 --stop-max 400
```
> Parâmetros adicionais: `--verbose` (prints detalhados)

### 3. Geração de Relatórios
Gera as matrizes de distribuição MAE/MFE e um arquivo `relatorio.html` riquíssimo visualmente na pasta `/output`.
```bash
python main.py --run --report --title "Meu Setup"
```

### 4. Otimização por Algoritmo Genético (DEAP)
Explora o espaço de parâmetros definido em `config/optimization_config.json` buscando o melhor Score Híbrido (Recovery Factor * Profit Factor). Usa *Multiprocessing* por padrão em todas as CPUs disponíveis.
```bash
python main.py --ga
```
> Você pode limitar as CPUs: `python main.py --ga --workers 4`
> **Saídas:** `output/optimization_result.json`, `output/optimization_report.html` e um gráfico `convergence_plot.png`.

### 5. Executar Toda a Pipeline (Analise Simples)
```bash
python main.py --all
```

## 🧪 Como Rodar os Testes

O projeto utiliza `pytest` para assegurar que modificações no core não quebrem as funções existentes (TDD-friendly).
Estando no terminal (dentro da pasta do projeto), basta digitar:

```bash
python -m pytest tests/
```
Ou, com maior nível de detalhes de execução:
```bash
python -m pytest tests/ -v
```

---
*Este projeto está alinhado com as fases 1-6 do roadmap. Mais detalhes podem ser visualizados na pasta `.agent/`.*

# 📊 Estatísticas de Backtesting: Guia de Referência

Este documento define as métricas estatísticas utilizadas no motor de backtesting, suas fórmulas e interpretações para Day Trading.

---

## 🟢 Métricas de Assertividade e Lucratividade

### Win Rate (Taxa de Acerto)

* **Explicação:** Percentual de operações que resultaram em lucro em relação ao total de operações.
* **Cálculo:** `(Número de Trades Lucrativos / Total de Trades) * 100`
* **Referência:** * **< 40%:** Exige um Payoff muito alto.
* **40% - 60%:** Comum para seguidores de tendência.
* **> 70%:** Comum para scalpers (geralmente com Payoff baixo).



### Profit Factor (Fator de Lucro)

* **Explicação:** Relação entre o total bruto ganho e o total bruto perdido.
* **Cálculo:** `Soma dos Lucros / Soma das Perdas (absoluto)`
* **Referência:** * **1.0:** Break-even (estagnado).
* **1.5 - 2.0:** Estratégia sólida.
* **> 2.5:** Excelente (verificar se não há overfiting).



### Payoff Ratio

* **Explicação:** A relação entre o valor médio dos ganhos e o valor médio das perdas.
* **Cálculo:** `Média de Ganhos / Média de Perdas`
* **Referência:** * **1.0:** Ganha e perde a mesma quantia em média.
* **> 2.0:** Muito bom para estratégias de tendência.
* **< 1.0:** Aceitável apenas se o Win Rate for muito alto (Scalping).



---

## 🔵 Médias de Execução

### Média Vencedores

* **Explicação:** Valor médio de lucro em cada operação ganhadora.
* **Cálculo:** `Soma dos Lucros Brutos / Quantidade de Trades Vencedores`

### Média Perdedores

* **Explicação:** Valor médio de prejuízo em cada operação perdedora.
* **Cálculo:** `Soma das Perdas Brutas / Quantidade de Trades Perdedores`

---

## 🟡 Métricas de Risco e Recuperação

### Recovery Factor (Fator de Recuperação)

* **Explicação:** Indica quão rápido a estratégia recupera o capital após um Drawdown (queda).
* **Cálculo:** `Lucro Líquido Total / Máximo Drawdown`
* **Referência:** * **< 3.0:** Recuperação lenta.
* **> 5.0:** Recuperação robusta.



### Sharpe Ratio

* **Explicação:** Mede o retorno excedente por unidade de risco (volatilidade).
* **Cálculo:** $(R_p - R_f) / \sigma_p$ (Onde $R_p$ é o retorno, $R_f$ a taxa livre de risco e $\sigma_p$ o desvio padrão).
* **Referência:** * **> 1.0:** Bom.
* **> 2.0:** Excelente para day trading intraday.



### Sortino Ratio

* **Explicação:** Similar ao Sharpe, mas considera apenas a volatilidade "negativa" (perdas), ignorando a volatilidade de lucros.
* **Referência:** Geralmente maior que o Sharpe em estratégias lucrativas.

### Calmar Ratio

* **Explicação:** Relação entre o retorno anualizado e o Máximo Drawdown.
* **Cálculo:** `Retorno Anual / Max Drawdown`
* **Referência:** * **> 2.0:** Indica uma excelente relação risco/retorno histórica.

---

## 🔴 Métricas de Eficiência (MAE/MFE)

### MAE Médio (Maximum Adverse Excursion)

* **Explicação:** A média do maior "calor" (prejuízo latente) que cada trade passou.
* **Cálculo:** `Média dos piores preços atingidos durante a vida do trade (em relação à entrada)`.

### MFE Médio (Maximum Favorable Excursion)

* **Explicação:** A média do maior lucro latente que cada trade atingiu antes de ser fechado.

### MAE/MFE Médio — Vencedores vs Perdedores

* **Uso:** * **MAE Perdedores:** Ajuda a definir o **Stop Loss** (se o MAE de perdedores é muito maior que o de vencedores, seu stop está longe demais).
* **MFE Vencedores:** Ajuda a definir o **Alvo** (se o MFE é muito maior que o lucro final, você está deixando dinheiro na mesa).



### MFE Efficiency (%)

* **Explicação:** Quanto do lucro máximo disponível você realmente capturou.
* **Cálculo:** `(Preço de Saída - Preço de Entrada) / (MFE - Preço de Entrada)`
* **Referência:** Quanto mais próximo de 100%, melhor é o seu "timing" de saída no lucro.

### MAE Efficiency (%)

* **Explicação:** Mede o quão próximo o seu stop esteve de ser atingido desnecessariamente.
* **Cálculo:** `(Preço de Entrada - Preço de Saída) / (Preço de Entrada - MAE)`

---

# Funções Objetivo para Algoritmo Genético

Escolher a **função objetivo** (ou *fitness function*) é a parte mais crítica de um Algoritmo Genético. Se você otimizar apenas pelo **Lucro Líquido**, o algoritmo encontrará um setup "sortudo" que acertou uma grande variação, mas que provavelmente quebraria sua conta na vida real devido ao risco excessivo.

Para o seu projeto em Python, aqui estão as principais funções objetivo, organizadas para facilitar sua implementação no `roadmap.md`.

---

### 1. Sharpe Ratio (ou Sortino Ratio)

É o padrão da indústria. Mede o retorno ajustado ao risco.

* **Fórmula:** $\frac{\text{Retorno Médio} - \text{Taxa Livre}}{\text{Desvio Padrão dos Retornos}}$
* **Prós:** Penaliza estratégias com resultados muito voláteis (instáveis).
* **Contras:** Trata volatilidade positiva (lucros grandes) como risco. O **Sortino** resolve isso focando apenas na volatilidade negativa.

### 2. Profit Factor (Fator de Lucro)

A relação direta entre o que ganha e o que perde.

* **Fórmula:** $\sum \text{Ganhos} / \sum |\text{Perdas}|$
* **Prós:** Muito simples de entender e foca na eficiência bruta da estratégia.
* **Contras:** Pode ser enganoso se houver poucos trades. Um único trade gigante pode inflar o Profit Factor artificialmente.

### 3. Recovery Factor (Fator de Recuperação)

Foca na resiliência da estratégia após perdas.

* **Fórmula:** $\text{Lucro Líquido} / \text{Máximo Drawdown}$
* **Prós:** Garante que a estratégia não precise de um "milagre" para recuperar uma sequência de perdas. É excelente para evitar estratégias que dão lucro, mas têm quedas de 50% no capital.
* **Contras:** Ignora o tempo. Uma estratégia pode levar 2 anos para recuperar um drawdown e ainda ter um Recovery Factor aceitável.

### 4. Expectância Matemática (Valor Esperado)

O quanto você espera ganhar, em média, por trade.

* **Fórmula:** $(\text{Win Rate} \times \text{Média Ganho}) - (\text{Loss Rate} \times \text{Média Perda})$
* **Prós:** É a métrica mais pura para saber se o seu "edge" (vantagem) é real.
* **Contras:** Não considera o risco de ruína ou a sequência de perdas (drawdown).

### 5. SQN (System Quality Number)

Desenvolvido por Van Tharp para avaliar a "facilidade" de operar um sistema.

* **Fórmula:** $\frac{\text{Expectância}}{\text{Desvio Padrão dos Resultados}} \times \sqrt{\text{Número de Trades}}$
* **Prós:** Premia estratégias que fazem muitos trades com resultados constantes. É ideal para Day Trading.
* **Contras:** Tende a favorecer sistemas com muitos trades curtos (scalping), o que pode aumentar muito o custo de corretagem real.

---

### Comparativo para Algoritmo Genético

| Função Objetivo | Melhor Uso | Risco de Overfitting |
| --- | --- | --- |
| **Lucro Líquido** | Jamais usar sozinha | **Altíssimo** |
| **Sharpe Ratio** | Portfólios de médio/longo prazo | Médio |
| **Recovery Factor** | Estratégias de tendência | Baixo |
| **SQN** | Day Trading de alta frequência | Médio |

---

### Minha Recomendação: Função Objetivo Composta (Híbrida)

Para o seu algoritmo em multithread, recomendo não usar uma métrica única, mas sim um **Score Composto**. Isso evita que o robô encontre um "ponto fora da curva".

**Exemplo de lógica para sua função fitness:**

```python
def fitness_function(resultado_backtest):
    # Penaliza se houver menos de 30 trades para evitar amostragem baixa
    if resultado_backtest['total_trades'] < 30:
        return 0
    
    
    # Peso 1: Fator de Recuperação (Estabilidade)
    rec_factor = resultado_backtest['recovery_factor']
    
    # Peso 2: Profit Factor (Eficiência)
    pf = resultado_backtest['profit_factor']
    
    # Score final combina os dois. Se o Drawdown for Zero, tratamos para não dividir por zero.
    score = rec_factor * pf
    
    return score

```

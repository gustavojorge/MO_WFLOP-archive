# Relatório de Sensibilidade: StandardScaler vs. RobustScaler no Agrupamento de Instâncias MO-WFLOP

Este documento descreve o experimento de sensibilidade realizado na etapa de normalização dos dados das 516 instâncias de parques eólicos para o pipeline de clustering.

---

## 1. Motivação e Configuração do Experimento
O objetivo principal deste teste foi analisar o impacto da troca da técnica de normalização dos dados. Avaliou-se se a substituição do `StandardScaler` (que utiliza média e desvio padrão) pelo `RobustScaler` (que utiliza mediana e Intervalo Interquartil - IQR) seria capaz de "abrir" o aglomerado central de instâncias e revelar novas subdivisões para a amostragem estratificada do Meta-Learning.

O teste foi executado de forma isolada no diretório `/temp` sem alterar a branch `feature/clustering-pipeline`.

---

## 2. Tabela Comparativa de Resultados

A tabela abaixo contrasta as métricas e a distribuição das duas técnicas de normalização:

| Métrica | StandardScaler (Original) | RobustScaler (Teste) | Análise Técnica |
| :--- | :---: | :---: | :--- |
| **PC1 (PCA)** | 24.76% | 38.28% | O RobustScaler aumenta significativamente a variância explicada pela primeira componente. |
| **PC2 (PCA)** | 8.15% | 16.93% | O ganho de variância explicada se mantém expressivo na segunda componente. |
| **PC3 (PCA)** | 7.78% | 6.79% | A terceira componente apresenta comportamento similar em termos de peso. |
| **Variância Acumulada (3 PCs)** | **40.69%** | **62.00%** | **RobustScaler é matematicamente superior** na etapa de projeção linear, capturando +21.31% de variância total com as mesmas 3 componentes. |
| **Distribuição dos Clusters (516)** | <ul><li>Cluster 0: 42 (8.1%)</li><li>Cluster 1: 169 (32.8%)</li><li>Cluster 2: 33 (6.4%)</li><li>Cluster 3: 1 (0.2%)</li><li>Cluster 4: 271 (52.5%)</li></ul> | <ul><li>Cluster 0: 440 (85.3%)</li><li>Cluster 1: 1 (0.2%)</li><li>Cluster 2: 25 (4.8%)</li><li>Cluster 3: 1 (0.2%)</li><li>Cluster 4: 49 (9.5%)</li></ul> | **StandardScaler é superior para fins práticos de agrupamento**. O RobustScaler concentrou 85.3% de todo o dataset (440 instâncias) em um único cluster massivo (Cluster 0), além de isolar dois clusters com apenas 1 instância cada. |
| **Distribuição Amostrada (300)** | <ul><li>Cluster 0: 42 (14.0%)</li><li>Cluster 1: 86 (28.7%)</li><li>Cluster 2: 33 (11.0%)</li><li>Cluster 3: 1 (0.3%)</li><li>Cluster 4: 138 (46.0%)</li></ul> | <ul><li>Cluster 0: 224 (74.7%)</li><li>Cluster 1: 1 (0.3%)</li><li>Cluster 2: 25 (8.3%)</li><li>Cluster 3: 1 (0.3%)</li><li>Cluster 4: 49 (16.3%)</li></ul> | O RobustScaler gera uma amostra final muito homogênea, onde **74.7% das instâncias são do mesmo cluster**, prejudicando severamente a diversidade almejada. |

---

## 3. Diagnóstico e Conclusões

### 3.1. Projeção de Variância (PCA)
O `RobustScaler` é, por definição, resiliente à presença de outliers porque centraliza e dimensiona os dados usando a mediana e o IQR ($75\% - 25\%$). Uma vez que os dados do MO-WFLOP possuem instâncias com comportamentos extremos (ex: a instância 501), o `StandardScaler` foi muito influenciado por esses extremos, fazendo com que a projeção do PCA inicial "desperdiçasse" variância com as direções de maior dispersão desses outliers. 

Ao neutralizar essa influência, o `RobustScaler` permitiu que as 3 primeiras componentes principais representassem muito melhor a estrutura de correlação da maioria dos dados centrais, subindo a variância explicada para **62.00%**.

### 3.2. Agrupamento e Separabilidade (K-Means)
Apesar do ganho matemático no PCA, o efeito colateral no agrupamento foi negativo. Ao trazer os outliers estatisticamente mais próximos do centro e homogeneizar as escalas das features com base no IQR:
1. O aglomerado central tornou-se uma densa "nuvem de gravidade".
2. O algoritmo K-Means não conseguiu encontrar limites de separação dentro dessa massa de 440 instâncias, alocando todas elas no mesmo Cluster 0.
3. Os outros clusters formados foram apenas fiapos remanescentes das margens extremas e outliers estritos isolados.

### 3.3. Recomendação
**Recomenda-se descartar a alteração para o RobustScaler e manter a implementação baseada no StandardScaler**. 

Embora o `StandardScaler` possua uma variância explicada menor no PCA ($40.69\%$), ele deforma a distribuição dos dados de tal forma que o K-Means consegue subdividir o aglomerado central de maneira mais uniforme (distribuído principalmente entre os Clusters 1 e 4). Isso é crucial para que a nossa **amostragem estratificada proporcional** colete instâncias de perfis variados dentro do espaço de busca, garantindo a diversidade necessária para a modelagem de Meta-Learning (essencial para artigos de Journal Qualis A1).

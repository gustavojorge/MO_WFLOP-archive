"""
process_clustering.py
=====================
Pipeline de clustering para seleção de 300 instâncias representativas
do problema MO-WFLOP, usando PCA (3 componentes) + K-Means (K=5).

Etapas:
  1. Carregamento e preparação dos dados
  2. Normalização (StandardScaler)
  3. Redução de dimensionalidade (PCA, n_components=3)
  4. Agrupamento (K-Means, K=5)
  5. Amostragem estratificada (60 instâncias por cluster → 300 total)
  6. Exportação de CSVs, gráfico e relatório de metadados
"""

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend sem display (compatível com servidor)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------

PIPELINE_DIR = Path(__file__).resolve().parent
INPUT_CSV    = PIPELINE_DIR / "consolidated_features.csv"
OUTPUT_DIR   = PIPELINE_DIR / "output_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Parâmetros
N_COMPONENTS   = 3    # componentes principais do PCA
N_CLUSTERS     = 5    # número de clusters K-Means
SAMPLES_PER_CLUSTER = 60   # 60 × 5 = 300 instâncias
RANDOM_STATE   = 42

# Paleta de cores para os clusters
CLUSTER_COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]


# ===========================================================================
# PASSO 1 – Carregamento e Preparação
# ===========================================================================
print("=" * 60)
print("  MO-WFLOP — Pipeline de Clustering")
print("=" * 60)

print("\n[1/6] Carregando e preparando os dados...")

df_original = pd.read_csv(INPUT_CSV)
print(f"  Shape do dataset: {df_original.shape}")

# Isola o rótulo Instance_ID
instance_ids = df_original["Instance_ID"]
df_features  = df_original.drop(columns=["Instance_ID"])

# Tratamento de dados ausentes: preenche com mediana de cada coluna
imputer = SimpleImputer(strategy="median")
X_imputed = imputer.fit_transform(df_features)

# Normalização: StandardScaler (média 0, desvio padrão 1)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

print(f"  Features numéricas: {X_scaled.shape[1]}")
print(f"  NaNs após imputação: {np.isnan(X_scaled).sum()}")


# ===========================================================================
# PASSO 2 – Redução de Dimensionalidade (PCA)
# ===========================================================================
print(f"\n[2/6] Aplicando PCA (n_components={N_COMPONENTS})...")

pca = PCA(n_components=N_COMPONENTS, random_state=RANDOM_STATE)
X_pca = pca.fit_transform(X_scaled)

explained_variance   = pca.explained_variance_ratio_ * 100   # em %
cumulative_variance  = explained_variance.cumsum()

for i, (ev, cv) in enumerate(zip(explained_variance, cumulative_variance), 1):
    print(f"  PC{i}: {ev:.2f}%  |  Acumulado: {cv:.2f}%")

print(f"\n  Variância explicada acumulada (3 PCs): {cumulative_variance[-1]:.2f}%")


# ===========================================================================
# PASSO 3 – Agrupamento (K-Means sobre as 3 PCs)
# ===========================================================================
print(f"\n[3/6] Executando K-Means (K={N_CLUSTERS}, random_state={RANDOM_STATE})...")

kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
cluster_labels = kmeans.fit_predict(X_pca)   # SOMENTE a matriz PCA como entrada

# Contagem por cluster
cluster_counts = pd.Series(cluster_labels).value_counts().sort_index()
print("  Instâncias por cluster (antes da amostragem):")
for cluster_id, count in cluster_counts.items():
    print(f"    Cluster {cluster_id}: {count} instâncias")


# ===========================================================================
# PASSO 4 – Montagem Final dos Dados
# ===========================================================================
print("\n[4/6] Montando DataFrame analítico completo...")

# Parte com os dados originais + colunas derivadas do PCA e K-Means
df_master = df_original.copy()
df_master["PC1"]           = X_pca[:, 0]
df_master["PC2"]           = X_pca[:, 1]
df_master["PC3"]           = X_pca[:, 2]
df_master["Cluster_Label"] = cluster_labels

print(f"  Shape do master DataFrame: {df_master.shape}")


# ===========================================================================
# SAÍDAS — CSVs
# ===========================================================================
print("\n[5/6] Salvando arquivos de saída...")

# 5a. Tabela analítica completa
master_path = OUTPUT_DIR / "master_instances_clustered.csv"
df_master.to_csv(master_path, index=False)
print(f"  ✓ {master_path.name}")

# 5b. Um CSV por cluster
for cluster_id in range(N_CLUSTERS):
    cluster_df   = df_master[df_master["Cluster_Label"] == cluster_id]
    cluster_path = OUTPUT_DIR / f"cluster_{cluster_id}_instances.csv"
    cluster_df.to_csv(cluster_path, index=False)
    print(f"  ✓ {cluster_path.name}  ({len(cluster_df)} instâncias)")

# 5c. Amostragem estratificada com fallback proporcional → exatamente 300 instâncias
#
# Regra:
#  1. Meta inicial: 60 por cluster.
#  2. Clusters com N_i <= 60: seleciona TUDO (contribui menos que 60).
#  3. Calcula o déficit total D = soma das instâncias que faltaram nos clusters pequenos.
#  4. Distribui D proporcionalmente entre os clusters grandes (N_i > 60),
#     de forma que o total final seja exatamente 300.

TOTAL_SAMPLE = N_CLUSTERS * SAMPLES_PER_CLUSTER   # 300

cluster_sizes = {
    cid: len(df_master[df_master["Cluster_Label"] == cid])
    for cid in range(N_CLUSTERS)
}

# Passo 1: separa clusters pequenos (fixos) e grandes (ajustáveis)
small_clusters = {cid: sz for cid, sz in cluster_sizes.items() if sz <= SAMPLES_PER_CLUSTER}
large_clusters = {cid: sz for cid, sz in cluster_sizes.items() if sz >  SAMPLES_PER_CLUSTER}

# Passo 2: conta quantas instâncias os clusters pequenos entregam
small_total = sum(small_clusters.values())
deficit     = SAMPLES_PER_CLUSTER * len(small_clusters) - small_total  # faltou nos pequenos

# Passo 3: distribui o déficit proporcionalmente nos clusters grandes
large_total_available = sum(large_clusters.values())
large_quota: dict[int, int] = {}
remaining = TOTAL_SAMPLE - small_total
quotas_float = {
    cid: sz / large_total_available * remaining
    for cid, sz in large_clusters.items()
}

# Arredondamento por maior resto (garante soma exata = remaining)
quotas_floor = {cid: int(q) for cid, q in quotas_float.items()}
remainder_needed = remaining - sum(quotas_floor.values())
remainders = sorted(
    large_clusters.keys(),
    key=lambda cid: -(quotas_float[cid] - quotas_floor[cid])
)
for cid in remainders[:remainder_needed]:
    quotas_floor[cid] += 1
large_quota = quotas_floor

# Passo 4: realiza o sorteio em cada cluster
sampled_frames = []
print("  Distribuição da amostragem proporcional:")

for cluster_id in range(N_CLUSTERS):
    cluster_df = df_master[df_master["Cluster_Label"] == cluster_id]
    n_available = len(cluster_df)

    if cluster_id in small_clusters:
        n_sample = n_available   # usa todas
        tag = "(todas — cluster pequeno)"
    else:
        n_sample = large_quota[cluster_id]
        tag = f"(cota proporcional)"

    sampled = cluster_df.sample(n=n_sample, random_state=RANDOM_STATE)
    sampled_frames.append(sampled)
    print(f"    Cluster {cluster_id}: {n_available} disponíveis → {n_sample} amostradas {tag}")

df_sampled = pd.concat(sampled_frames).sort_values("Instance_ID").reset_index(drop=True)
assert len(df_sampled) == TOTAL_SAMPLE, (
    f"Erro de amostragem: esperado {TOTAL_SAMPLE}, obtido {len(df_sampled)}"
)
sampled_path = OUTPUT_DIR / "sampled_instances_300.csv"
df_sampled.to_csv(sampled_path, index=False)
print(f"  ✓ {sampled_path.name}  ({len(df_sampled)} instâncias amostradas)")


# ===========================================================================
# SAÍDA — Visualização Gráfica (PC1 × PC2, colorido por Cluster_Label)
# ===========================================================================
print("\n[6/6] Gerando visualização gráfica...")

fig, ax = plt.subplots(figsize=(10, 7))

for cluster_id in range(N_CLUSTERS):
    mask = df_master["Cluster_Label"] == cluster_id
    ax.scatter(
        df_master.loc[mask, "PC1"],
        df_master.loc[mask, "PC2"],
        c=CLUSTER_COLORS[cluster_id],
        label=f"Cluster {cluster_id}  (n={mask.sum()})",
        alpha=0.75,
        edgecolors="white",
        linewidths=0.4,
        s=60,
    )

ax.set_xlabel(f"PC1  ({explained_variance[0]:.1f}% variância explicada)", fontsize=12)
ax.set_ylabel(f"PC2  ({explained_variance[1]:.1f}% variância explicada)", fontsize=12)
ax.set_title(
    "Agrupamento K-Means (K=5) sobre Componentes Principais\n"
    "516 Instâncias MO-WFLOP — PCA (3 PCs)",
    fontsize=13,
    fontweight="bold",
)
ax.legend(title="Clusters", fontsize=10, title_fontsize=10, framealpha=0.9)
ax.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()

plot_path = OUTPUT_DIR / "cluster_visualization.png"
plt.savefig(plot_path, dpi=150, bbox_inches="tight")
print(f"  ✓ {plot_path.name} salvo")

plt.show()


# ===========================================================================
# SAÍDA — Relatório de Metadados (clustering_summary.txt)
# ===========================================================================
summary_path = OUTPUT_DIR / "clustering_summary.txt"

with open(summary_path, "w", encoding="utf-8") as f:
    f.write("=" * 60 + "\n")
    f.write("  RELATÓRIO DO PIPELINE DE CLUSTERING — MO-WFLOP\n")
    f.write("=" * 60 + "\n\n")

    f.write("--- Análise de Componentes Principais (PCA) ---\n\n")
    for i, (ev, cv) in enumerate(zip(explained_variance, cumulative_variance), 1):
        f.write(f"  PC{i}  :  {ev:.4f}%  de variância explicada\n")
    f.write(f"\n  Variância Acumulada (PC1+PC2+PC3): {cumulative_variance[-1]:.4f}%\n")

    f.write("\n--- Distribuição dos Clusters (516 instâncias) ---\n\n")
    for cluster_id, count in cluster_counts.items():
        pct = count / len(df_master) * 100
        f.write(f"  Cluster {cluster_id}: {count:>3} instâncias  ({pct:.1f}%)\n")

    f.write(f"\n  Total: {len(df_master)} instâncias\n")

    f.write("\n--- Amostragem Estratificada (Fallback Proporcional) ---\n\n")
    f.write(f"  Meta inicial por cluster          : {SAMPLES_PER_CLUSTER}\n")
    f.write(f"  Clusters pequenos (N<=60)         : usadas todas as instâncias disponíveis\n")
    f.write(f"  Clusters grandes  (N>60)          : cota ajustada proporcionalmente\n")
    f.write(f"  Total amostrado                   : {len(df_sampled)} (exato)\n")
    f.write("\n  Distribuição da amostra por cluster:\n")
    sample_dist = df_sampled["Cluster_Label"].value_counts().sort_index()
    for cid, cnt in sample_dist.items():
        f.write(f"    Cluster {cid}: {cnt} instâncias\n")

    f.write("\n--- Parâmetros do Pipeline ---\n\n")
    f.write(f"  PCA n_components : {N_COMPONENTS}\n")
    f.write(f"  K-Means K        : {N_CLUSTERS}\n")
    f.write(f"  random_state     : {RANDOM_STATE}\n")
    f.write(f"  Scaler           : StandardScaler\n")
    f.write(f"  Imputer          : SimpleImputer (strategy=median)\n")

print(f"  ✓ {summary_path.name}")

print("\n" + "=" * 60)
print("  Pipeline concluído com sucesso!")
print(f"  Arquivos salvos em: {OUTPUT_DIR}")
print("=" * 60)

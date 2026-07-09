import os
import pandas as pd
import numpy as np

def main():
    # Caminhos dos arquivos
    input_file = "clustering_pipeline/output_data/master_instances_clustered.csv"
    output_dir = "clustering_analysis/output_data"
    output_file = os.path.join(output_dir, "cluster_profiles.txt")

    # Garante que o diretório de saída exista
    os.makedirs(output_dir, exist_ok=True)

    # Carrega os dados
    if not os.path.exists(input_file):
        print(f"Erro: O arquivo {input_file} nao foi encontrado.")
        return

    df = pd.read_csv(input_file)

    # Identifica colunas a serem analisadas (exclui colunas de ID, PCs e labels)
    exclude_cols = ["Instance_ID", "PC1", "PC2", "PC3", "Cluster_Label"]
    feature_cols = [col for col in df.columns if col not in exclude_cols]

    # Calcula a média global de cada feature
    global_means = df[feature_cols].mean()

    # Identifica os clusters únicos
    clusters = sorted(df["Cluster_Label"].unique())

    # Prepara o conteúdo do relatório
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("RELATORIO DE PERFIS DOS CLUSTERS (EXPLICABILIDADE)")
    report_lines.append("=" * 80)
    report_lines.append(f"Total de Instancias: {len(df)}")
    report_lines.append(f"Total de Features Analisadas: {len(feature_cols)}\n")

    for cluster in clusters:
        cluster_df = df[df["Cluster_Label"] == cluster]
        cluster_means = cluster_df[feature_cols].mean()

        # Calcula o desvio relativo em relação à média global
        # Evita divisão por zero se a média global for muito próxima de zero
        relative_deviations = []
        for feature in feature_cols:
            g_mean = global_means[feature]
            c_mean = cluster_means[feature]

            if abs(g_mean) < 1e-9:
                # Se a média global for praticamente zero, usamos a diferença absoluta normalizada pelo desvio padrão global
                g_std = df[feature].std()
                if g_std < 1e-9:
                    dev = 0.0
                else:
                    dev = (c_mean - g_mean) / g_std
            else:
                dev = (c_mean - g_mean) / abs(g_mean)

            relative_deviations.append((feature, dev, c_mean, g_mean))

        # Filtra apenas desvios positivos e ordena de forma decrescente
        positive_devs = [item for item in relative_deviations if item[1] > 0]
        positive_devs.sort(key=lambda x: x[1], reverse=True)

        # Seleciona as 5 principais features com maior desvio positivo
        top_5 = positive_devs[:5]

        report_lines.append("-" * 80)
        report_lines.append(f"Cluster {cluster} (n = {len(cluster_df)} instancias)")
        report_lines.append("-" * 80)
        report_lines.append("Top 5 características marcantes (maior desvio positivo em relacao a media global):")

        for idx, (feature, dev, c_mean, g_mean) in enumerate(top_5, 1):
            percentage_increase = dev * 100
            report_lines.append(
                f"  {idx}. Feature: {feature}\n"
                f"     Media no Cluster: {c_mean:.6f} | Media Global: {g_mean:.6f}\n"
                f"     Desvio Positivo: +{percentage_increase:.2f}%\n"
            )
        report_lines.append("")

    # Escreve o relatório no arquivo
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"Relatorio de perfis dos clusters gerado com sucesso em: {output_file}")

if __name__ == "__main__":
    main()

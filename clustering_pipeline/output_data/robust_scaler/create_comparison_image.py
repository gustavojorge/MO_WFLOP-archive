import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os

def main():
    img_orig_path = 'clustering_pipeline/output_data/cluster_visualization.png'
    img_test_path = 'temp/cluster_visualization.png'
    output_path = 'temp/comparison_visualization.png'

    if not os.path.exists(img_orig_path):
        print(f"Erro: {img_orig_path} nao existe.")
        return
    if not os.path.exists(img_test_path):
        print(f"Erro: {img_test_path} nao existe.")
        return

    # Lê as imagens salvas
    img_orig = mpimg.imread(img_orig_path)
    img_test = mpimg.imread(img_test_path)

    # Cria a figura lado a lado
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))
    
    axes[0].imshow(img_orig)
    axes[0].set_title("StandardScaler (Original)\nVariancia Acumulada (3 PCs): 40.69%", fontsize=14, fontweight='bold')
    axes[0].axis('off')

    axes[1].imshow(img_test)
    axes[1].set_title("RobustScaler (Teste)\nVariancia Acumulada (3 PCs): 62.00%", fontsize=14, fontweight='bold')
    axes[1].axis('off')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Imagem de comparacao gerada com sucesso em: {output_path}")

if __name__ == "__main__":
    main()

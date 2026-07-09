"""
build_dataset.py
================
Extrai features físicas (raw) e meta-features de 516 instâncias de otimização
de parques eólicos e consolida em um único arquivo CSV tabular.

Autor: gerado por Antigravity (Google DeepMind)
Branch: feature/clustering-pipeline
"""

import json
import glob
import warnings
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Polygon

# ---------------------------------------------------------------------------
# Configuração de caminhos
# ---------------------------------------------------------------------------

# Raiz do repositório (pasta pai deste script)
REPO_ROOT = Path(__file__).resolve().parent.parent

RAW_INSTANCES_DIR = REPO_ROOT / "instances" / "sites"
METAFEATURES_DIR = Path(
    "/home/gustavojorge/Documentos/GitClone/IC/MO-WFLOP/MO_WFLOP-archive"
    "/raw_results/metafeatures_raw"
)

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = OUTPUT_DIR / "consolidated_features.csv"

# ---------------------------------------------------------------------------
# Lista de instâncias: "0" até "505" + "A" até "J"
# ---------------------------------------------------------------------------

NUMERIC_INSTANCES = [str(i) for i in range(506)]   # "0", "1", ..., "505"
LETTER_INSTANCES = [chr(c) for c in range(ord("A"), ord("J") + 1)]  # A..J
ALL_INSTANCES = NUMERIC_INSTANCES + LETTER_INSTANCES  # 516 instâncias


# ===========================================================================
# PARTE 1 – Raw Features (Físicas)
# ===========================================================================

def _polygon_area_km2(coords: list[tuple[float, float]]) -> float:
    """Calcula área de um polígono (coords em metros) em km²."""
    if len(coords) < 3:
        return 0.0
    poly = Polygon(coords)
    return poly.area / 1_000_000.0  # m² → km²


def _parse_geometry_numeric(geometry_path: Path) -> list[float]:
    """
    Lê geometry.txt de instâncias NUMÉRICAS.

    Formato: polígonos separados por linhas em branco.
    Cada linha de coordenadas: "x y"
    Retorna uma lista de áreas em km² (uma por polígono/zona).
    """
    areas = []
    current_coords = []

    with open(geometry_path, "r") as f:
        for raw_line in f:
            line = raw_line.strip()
            if line == "":
                # Separador de polígono
                if current_coords:
                    areas.append(_polygon_area_km2(current_coords))
                    current_coords = []
            else:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        current_coords.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        pass  # ignora linhas não numéricas

    # Último polígono (sem linha em branco final)
    if current_coords:
        areas.append(_polygon_area_km2(current_coords))

    return areas


def extract_raw_features_from_info_json(info_json_path: Path) -> dict:
    """
    Extrai raw features para instâncias que possuem info.json (A-J).

    Colunas produzidas:
      total_area_km2, total_holes, total_available_points,
      total_fixed_turbines, density
    """
    with open(info_json_path, "r") as f:
        data = json.load(f)

    zones = data.get("Zones", {})

    total_area_km2 = 0.0
    total_holes = 0
    total_available_points = 0
    total_fixed_turbines = 0

    for zone_info in zones.values():
        zone_type = zone_info.get("Type", "").lower()
        if zone_type == "available":
            total_area_km2 += zone_info.get("Area km2", 0.0)
            total_holes += zone_info.get("Holes", 0)
            total_available_points += zone_info.get("Points", 0)
        elif zone_type == "fixed":
            total_fixed_turbines += zone_info.get("Points", 0)

    density = (
        total_available_points / total_area_km2 if total_area_km2 > 0 else float("nan")
    )

    return {
        "total_area_km2": total_area_km2,
        "total_holes": total_holes,
        "total_available_points": total_available_points,
        "total_fixed_turbines": total_fixed_turbines,
        "density": density,
    }


def extract_raw_features_from_txt(instance_dir: Path) -> dict:
    """
    Extrai raw features para instâncias NUMÉRICAS (0-505) a partir de .txt.

    - total_area_km2      : soma das áreas dos polígonos em geometry.txt (Shapely)
    - total_holes         : 0 (não existe informação de buracos em instâncias sintéticas)
    - total_available_points : total de linhas em availablePositions.txt
    - total_fixed_turbines   : total de linhas em fixed_wf.txt
    - density             : total_available_points / total_area_km2
    """
    geometry_path = instance_dir / "geometry.txt"
    avail_path = instance_dir / "availablePositions.txt"
    fixed_path = instance_dir / "fixed_wf.txt"

    # Área
    if geometry_path.exists():
        areas = _parse_geometry_numeric(geometry_path)
        total_area_km2 = sum(areas)
    else:
        warnings.warn(f"[WARN] geometry.txt não encontrado: {geometry_path}")
        total_area_km2 = float("nan")

    # Pontos disponíveis
    if avail_path.exists():
        with open(avail_path, "r") as f:
            total_available_points = sum(1 for line in f if line.strip())
    else:
        warnings.warn(f"[WARN] availablePositions.txt não encontrado: {avail_path}")
        total_available_points = float("nan")

    # Turbinas fixas
    if fixed_path.exists():
        with open(fixed_path, "r") as f:
            total_fixed_turbines = sum(1 for line in f if line.strip())
    else:
        total_fixed_turbines = 0

    # Buracos: não disponível para instâncias sintéticas
    total_holes = 0

    density = (
        total_available_points / total_area_km2
        if (total_area_km2 and total_area_km2 > 0)
        else float("nan")
    )

    return {
        "total_area_km2": total_area_km2,
        "total_holes": total_holes,
        "total_available_points": total_available_points,
        "total_fixed_turbines": total_fixed_turbines,
        "density": density,
    }


def extract_raw_features(instance: str) -> dict:
    """Despacha para a função correta conforme o tipo de instância."""
    instance_dir = RAW_INSTANCES_DIR / instance
    info_json = instance_dir / "info.json"

    if info_json.exists():
        return extract_raw_features_from_info_json(info_json)
    elif instance_dir.exists():
        return extract_raw_features_from_txt(instance_dir)
    else:
        warnings.warn(f"[WARN] Diretório da instância não encontrado: {instance_dir}")
        return {
            "total_area_km2": float("nan"),
            "total_holes": float("nan"),
            "total_available_points": float("nan"),
            "total_fixed_turbines": float("nan"),
            "density": float("nan"),
        }


# ===========================================================================
# PARTE 2 – Meta-features dos CSVs
# ===========================================================================

# Definição dos 4 grupos de meta-features
METAFEATURE_SOURCES = [
    {
        "name": "pareto_rw",
        "glob_template": "{mf_dir}/{inst}/pareto_based/random_walk/l100_r1.0/*.csv",
        "prefix": "pareto_rw_",
    },
    {
        "name": "pareto_aw",
        "glob_template": "{mf_dir}/{inst}/pareto_based/adaptative_walk/r1.0/*.csv",
        "prefix": "pareto_aw_",
    },
    {
        "name": "decomp_rw",
        "glob_template": "{mf_dir}/{inst}/decomposition_based/random_walk/l100_r1.0/*.csv",
        "prefix": "decomp_rw_",
    },
    {
        "name": "decomp_aw",
        "glob_template": "{mf_dir}/{inst}/decomposition_based/adaptative_walk/r1.0/*.csv",
        "prefix": "decomp_aw_",
    },
]

# Coluna que identifica a instância (chave de junção — NÃO recebe prefixo)
INSTANCE_ID_COLUMN = "Instance"


def read_metafeature_csv(glob_pattern: str, prefix: str, instance: str) -> pd.Series | None:
    """
    Localiza o CSV via glob, lê, renomeia colunas com prefixo (exceto Instance)
    e retorna a linha correspondente à instância como pd.Series.
    Retorna None se o arquivo não for encontrado ou se a instância não estiver no CSV.
    """
    files = glob.glob(glob_pattern)
    if not files:
        warnings.warn(
            f"[WARN] Nenhum CSV encontrado com padrão: {glob_pattern}"
        )
        return None

    csv_path = files[0]  # Esperamos exatamente 1 arquivo por diretório

    try:
        df = pd.read_csv(csv_path, dtype=str)
    except Exception as exc:
        warnings.warn(f"[WARN] Erro ao ler CSV '{csv_path}': {exc}")
        return None

    # Renomeia colunas: todas exceto Instance recebem o prefixo
    rename_map = {
        col: f"{prefix}{col}"
        for col in df.columns
        if col != INSTANCE_ID_COLUMN
    }
    df = df.rename(columns=rename_map)

    # Converte valores para numérico (exceto Instance)
    for col in df.columns:
        if col != INSTANCE_ID_COLUMN:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Filtra pela instância
    instance_str = str(instance)
    row = df[df[INSTANCE_ID_COLUMN].astype(str) == instance_str]

    if row.empty:
        warnings.warn(
            f"[WARN] Instância '{instance}' não encontrada no CSV: {csv_path}"
        )
        return None

    # Retorna apenas a primeira linha como Series (sem a coluna Instance)
    series = row.iloc[0].drop(labels=[INSTANCE_ID_COLUMN])
    return series


def extract_all_metafeatures(instance: str) -> pd.Series:
    """
    Extrai e concatena as meta-features dos 4 grupos para uma instância.
    """
    all_series = []
    for source in METAFEATURE_SOURCES:
        pattern = source["glob_template"].format(
            mf_dir=METAFEATURES_DIR, inst=instance
        )
        series = read_metafeature_csv(pattern, source["prefix"], instance)
        if series is not None:
            all_series.append(series)
        else:
            # Adicionar NaNs com prefixo correto (colunas desconhecidas neste ponto)
            # Serão tratados no merge final como NaN
            pass

    if all_series:
        return pd.concat(all_series)
    else:
        return pd.Series(dtype=float)


# ===========================================================================
# MAIN – Loop principal + consolidação
# ===========================================================================

def main():
    print("=" * 60)
    print("  MO-WFLOP – Pipeline de Extração de Features")
    print(f"  Total de instâncias: {len(ALL_INSTANCES)}")
    print("=" * 60)

    rows = []

    for idx, instance in enumerate(ALL_INSTANCES):
        print(f"[{idx+1:03d}/{len(ALL_INSTANCES)}] Processando instância: {instance}")

        row = {"Instance_ID": instance}

        # --- Parte 1: Raw Features ---
        try:
            raw = extract_raw_features(instance)
            row.update(raw)
        except Exception as exc:
            warnings.warn(f"[WARN] Falha ao extrair raw features da instância '{instance}': {exc}")
            row.update({
                "total_area_km2": float("nan"),
                "total_holes": float("nan"),
                "total_available_points": float("nan"),
                "total_fixed_turbines": float("nan"),
                "density": float("nan"),
            })

        # --- Parte 2: Meta-features ---
        try:
            meta = extract_all_metafeatures(instance)
            for col, val in meta.items():
                row[col] = val
        except Exception as exc:
            warnings.warn(f"[WARN] Falha ao extrair meta-features da instância '{instance}': {exc}")

        rows.append(row)

    # ---------------------------------------------------------------------------
    # Consolidação final
    # ---------------------------------------------------------------------------
    print("\nConsolidando DataFrame final...")
    df = pd.DataFrame(rows)

    # Garante que Instance_ID é a primeira coluna
    cols = ["Instance_ID"] + [c for c in df.columns if c != "Instance_ID"]
    df = df[cols]

    # Relatório dimensional
    n_rows, n_cols = df.shape
    print(f"\nDataFrame final: {n_rows} linhas × {n_cols} colunas")
    if n_rows != 516:
        warnings.warn(f"[WARN] Número de linhas esperado: 516, obtido: {n_rows}")
    if n_cols != 106:
        warnings.warn(
            f"[WARN] Número de colunas esperado: 106, obtido: {n_cols}\n"
            f"  Colunas presentes: {list(df.columns)}"
        )

    # Salva o resultado
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✓ Dataset salvo em: {OUTPUT_FILE}")
    print("\nPrimeiras colunas do dataset:")
    print(df.iloc[:5, :10].to_string())

    return df


if __name__ == "__main__":
    main()

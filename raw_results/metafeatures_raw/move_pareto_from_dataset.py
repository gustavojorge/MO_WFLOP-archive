#!/usr/bin/env python3
"""
move_pareto_from_dataset.py

Move os diretórios `pareto_based` do diretório `/dataset` para os diretórios
correspondentes na raiz. Para cada diretório X na raiz, verifica se existe
`/dataset/X/pareto_based` e move para `/raiz/X/pareto_based`.

Uso:
  python move_pareto_from_dataset.py                    # executa movimentação real
  python move_pareto_from_dataset.py --dry-run          # apenas mostra o que seria movido
  python move_pareto_from_dataset.py --verbose          # mostra cada ação detalhadamente
  python move_pareto_from_dataset.py --dataset /outro/dataset --root /outro/root

Segurança:
  - Verifica se os diretórios de origem e destino existem
  - Não sobrescreve diretórios de destino existentes (reporta erro)
  - Trata exceções de permissão ou E/S sem interromper o fluxo geral
"""
from __future__ import annotations
import os
import sys
import argparse
import shutil
from typing import List

# Caminhos padrão baseados na estrutura do projeto
DEFAULT_ROOT = "/home/gustavojorge/Documentos/GitClone/IC/MO_WFLOP-archive/raw_results/metafeatures_raw"
DEFAULT_DATASET = "/home/gustavojorge/Documentos/GitClone/IC/MO_WFLOP-archive/raw_results/metafeatures_raw/dataset"


def get_directory_names(base_path: str) -> List[str]:
    """Obtém lista de nomes de diretórios válidos no caminho base."""
    try:
        with os.scandir(base_path) as it:
            return [entry.name for entry in it if entry.is_dir() and entry.name != "remove_pareto_based.py"]
    except FileNotFoundError:
        return []


def move_pareto_directories(root_path: str, dataset_path: str, dry_run: bool = False, verbose: bool = False) -> dict:
    """Move diretórios pareto_based do dataset para a raiz."""
    processed = 0
    found_in_dataset = 0
    moved = 0
    skipped = 0
    errors: List[str] = []

    # Obter lista de diretórios da raiz
    root_dirs = get_directory_names(root_path)
    if not root_dirs:
        errors.append(f"Nenhum diretório encontrado na raiz: {root_path}")
        return {"processed": 0, "found_in_dataset": 0, "moved": 0, "skipped": 0, "errors": errors}

    if verbose:
        print(f"Encontrados {len(root_dirs)} diretórios na raiz")

    for dir_name in root_dirs:
        processed += 1
        
        # Caminhos de origem e destino
        source_pareto = os.path.join(dataset_path, dir_name, "pareto_based")
        dest_dir = os.path.join(root_path, dir_name)
        dest_pareto = os.path.join(dest_dir, "pareto_based")

        # Verifica se o diretório de origem existe
        if not os.path.isdir(source_pareto):
            if verbose:
                print(f"[IGNORADO] Não encontrado: {source_pareto}")
            continue

        found_in_dataset += 1

        # Verifica se o diretório de destino já existe
        if os.path.exists(dest_pareto):
            skipped += 1
            msg = f"Destino já existe: {dest_pareto}"
            errors.append(msg)
            if verbose:
                print(f"[PULADO] {msg}")
            continue

        # Verifica se o diretório pai do destino existe
        if not os.path.isdir(dest_dir):
            msg = f"Diretório de destino não existe: {dest_dir}"
            errors.append(msg)
            if verbose:
                print(f"[ERRO] {msg}")
            continue

        # Executa ou simula a movimentação
        if dry_run:
            if verbose:
                print(f"[DRY-RUN] Moveria: {source_pareto} -> {dest_pareto}")
        else:
            try:
                shutil.move(source_pareto, dest_pareto)
                moved += 1
                if verbose:
                    print(f"[MOVIDO] {source_pareto} -> {dest_pareto}")
            except Exception as e:
                msg = f"Falha ao mover {source_pareto} -> {dest_pareto}: {e}"
                errors.append(msg)
                if verbose:
                    print(f"[ERRO] {msg}")

    return {
        "processed": processed,
        "found_in_dataset": found_in_dataset,
        "moved": moved,
        "skipped": skipped,
        "errors": errors
    }


def parse_args(argv: List[str]):
    p = argparse.ArgumentParser(description="Move diretórios 'pareto_based' do dataset para os diretórios correspondentes na raiz.")
    p.add_argument("--root", default=DEFAULT_ROOT, help="Caminho raiz de destino (default: caminho configurado no script)")
    p.add_argument("--dataset", default=DEFAULT_DATASET, help="Caminho do dataset de origem (default: caminho configurado no script)")
    p.add_argument("--dry-run", action="store_true", help="Não move nada, apenas informa o que faria")
    p.add_argument("--verbose", action="store_true", help="Mostra cada ação/diretório processado")
    return p.parse_args(argv)


def main(argv: List[str]):
    args = parse_args(argv)
    
    root_path = os.path.abspath(args.root)
    dataset_path = os.path.abspath(args.dataset)
    
    # Validações iniciais
    if not os.path.isdir(root_path):
        print(f"Erro: caminho raiz não é diretório: {root_path}", file=sys.stderr)
        return 2
    
    if not os.path.isdir(dataset_path):
        print(f"Erro: caminho dataset não é diretório: {dataset_path}", file=sys.stderr)
        return 2

    mode = "DRY-RUN" if args.dry_run else "EXECUÇÃO"
    print(f"Iniciando {mode}:")
    print(f"  Raiz: {root_path}")
    print(f"  Dataset: {dataset_path}")
    
    summary = move_pareto_directories(root_path, dataset_path, dry_run=args.dry_run, verbose=args.verbose)

    print("\nResumo:")
    print(f"Diretórios processados na raiz: {summary['processed']}")
    print(f"Diretórios pareto_based encontrados no dataset: {summary['found_in_dataset']}")
    if args.dry_run:
        would_move = summary['found_in_dataset'] - summary['skipped']
        print(f"Diretórios que seriam movidos: {would_move}")
    else:
        print(f"Diretórios movidos com sucesso: {summary['moved']}")
    
    if summary['skipped'] > 0:
        print(f"Diretórios pulados (destino já existe): {summary['skipped']}")
    
    if summary['errors']:
        print(f"Erros encontrados ({len(summary['errors'])}):")
        for i, error in enumerate(summary['errors'][:10]):  # limita saída
            print(f"  {i+1}. {error}")
        if len(summary['errors']) > 10:
            print(f"  ... e mais {len(summary['errors']) - 10} erros")

    return 0 if not summary['errors'] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
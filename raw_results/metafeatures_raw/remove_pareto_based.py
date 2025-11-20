#!/usr/bin/env python3
"""
remove_pareto_based.py

Percorre os subdiretórios imediatos do caminho base e remove o subdiretório
`pareto_based` quando existir. Suporta modo dry-run para apenas relatar.

Uso:
  python remove_pareto_based.py                # executa remoção real
  python remove_pareto_based.py --dry-run      # apenas mostra o que seria removido
  python remove_pareto_based.py -p /outro/caminho
  python remove_pareto_based.py --verbose      # lista cada ação

Saídas:
  Summary final com quantos diretórios tinham `pareto_based` e quantos foram removidos.

Segurança:
  - Ignora entradas que não sejam diretórios.
  - Trata exceções de permissão ou E/S sem interromper o fluxo geral.
"""
from __future__ import annotations
import os
import sys
import argparse
import shutil
from typing import List

DEFAULT_BASE = "/home/gustavojorge/Documentos/GitClone/IC/MO_WFLOP-archive/raw_results/metafeatures_raw"


def should_process(entry: os.DirEntry) -> bool:
    """Define se o diretório deve ser processado. Aqui aceitamos todos os diretórios imediatos.
    Se quiser restringir a nomes 0-500 e A-J, isso pode ser ajustado.
    """
    if not entry.is_dir():
        return False
    name = entry.name
    # Checagem opcional (comentada). Descomente se quiser limitar.
    # if name.isdigit():
    #     return True
    # if len(name) == 1 and name.isalpha() and name.upper() in [chr(c) for c in range(ord('A'), ord('J') + 1)]:
    #     return True
    # return False
    return True  # processa todos os diretórios imediatos


def remove_pareto(base_path: str, dry_run: bool = False, verbose: bool = False) -> dict:
    processed = 0
    existed = 0
    removed = 0
    errors: List[str] = []

    try:
        with os.scandir(base_path) as it:
            for entry in it:
                if not should_process(entry):
                    continue
                processed += 1
                pareto_path = os.path.join(entry.path, "pareto_based")
                if os.path.isdir(pareto_path):
                    existed += 1
                    if dry_run:
                        if verbose:
                            print(f"[DRY-RUN] Encontrado (seria removido): {pareto_path}")
                    else:
                        try:
                            shutil.rmtree(pareto_path)
                            removed += 1
                            if verbose:
                                print(f"[REMOVIDO] {pareto_path}")
                        except Exception as e:  # noqa: BLE001
                            errors.append(f"Falha ao remover {pareto_path}: {e}")
                            if verbose:
                                print(f"[ERRO] {pareto_path}: {e}")
                else:
                    if verbose:
                        print(f"[IGNORADO] Sem 'pareto_based': {entry.path}")
    except FileNotFoundError:
        print(f"Caminho base não encontrado: {base_path}", file=sys.stderr)
        return {"processed": processed, "existed": existed, "removed": removed, "errors": ["Base path not found"]}

    return {"processed": processed, "existed": existed, "removed": removed, "errors": errors}


def parse_args(argv: List[str]):
    p = argparse.ArgumentParser(description="Remove subdiretórios 'pareto_based' dos diretórios filhos do caminho base.")
    p.add_argument("-p", "--path", default=DEFAULT_BASE, help="Caminho base (default: caminho configurado no script)")
    p.add_argument("--dry-run", action="store_true", help="Não remove nada, apenas informa o que faria")
    p.add_argument("--verbose", action="store_true", help="Mostra cada ação/diretório processado")
    return p.parse_args(argv)


def main(argv: List[str]):
    args = parse_args(argv)
    base = os.path.abspath(args.path)
    if not os.path.isdir(base):
        print(f"Erro: caminho base não é diretório: {base}", file=sys.stderr)
        return 2

    mode = "DRY-RUN" if args.dry_run else "EXECUÇÃO"
    print(f"Iniciando {mode} em: {base}")
    summary = remove_pareto(base, dry_run=args.dry_run, verbose=args.verbose)

    print("\nResumo:")
    print(f"Diretórios processados: {summary['processed']}")
    print(f"Diretórios com 'pareto_based': {summary['existed']}")
    if args.dry_run:
        print(f"Diretórios que seriam removidos: {summary['existed']}")
    else:
        print(f"Diretórios removidos: {summary['removed']}")
    if summary['errors']:
        print(f"Erros ({len(summary['errors'])}):")
        for e in summary['errors'][:10]:  # limita saída se muitos erros
            print(f"  - {e}")
        if len(summary['errors']) > 10:
            print("  (mais erros omitidos)")

    return 0 if not summary['errors'] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))

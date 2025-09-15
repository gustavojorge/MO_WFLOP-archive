#!/bin/bash

# Caminho base
BASE_DIR="./dataset/comolsd"

# Procurar e remover apenas arquivos que terminam com "_comolsd_layout.txt"
find "$BASE_DIR" -type f -name "*_comolsd_layout.txt" -exec rm -f {} \;

echo "Arquivos '*_comolsd_layout.txt' removidos dentro de $BASE_DIR"

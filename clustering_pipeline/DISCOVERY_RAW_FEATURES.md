# Descoberta: Assimetria Estrutural entre Instâncias Numéricas e Letra

> **Contexto:** Durante o desenvolvimento do pipeline de extração de features
> (`build_dataset.py`), foi identificada uma diferença fundamental na forma como
> os metadados das instâncias são armazenados, dependendo do seu tipo.

---

## O Problema

O pipeline precisava extrair 5 colunas de features físicas ("raw features") para
as 516 instâncias do problema MO-WFLOP:

| Coluna | Descrição |
|---|---|
| `total_area_km2` | Área total disponível em km² |
| `total_holes` | Número de buracos/exclusões dentro das zonas disponíveis |
| `total_available_points` | Total de posições candidatas para turbinas |
| `total_fixed_turbines` | Total de turbinas de posição fixa |
| `density` | Razão pontos disponíveis / área disponível |

A especificação original assumia a existência de um arquivo `info.json` em cada
instância. Ao inspecionar o repositório, foi descoberta uma **assimetria
estrutural** entre os dois grupos de instâncias:

```
instances/sites/A/  →  info.json  ✓  (instâncias reais, A–J)
instances/sites/0/  →  *.txt      ✗  (instâncias sintéticas, 0–505)
```

```bash
# Verificação: apenas 10 arquivos info.json existem — todos em letras
$ find instances/sites -name "info.json" | wc -l
10

$ find instances/sites -name "info.json" | sort
instances/sites/A/info.json
instances/sites/B/info.json
...
instances/sites/J/info.json
```

---

## Estrutura de Cada Grupo

### Instâncias Letra (A–J) — `info.json`

As 10 instâncias baseadas em parques reais possuem um arquivo JSON com todos os
metadados pré-calculados por zona:

```json
{
  "Fixed turbines": true,
  "Points": 3238,
  "Zones": {
    "1": {
      "Area km2": 50.423129875116345,
      "Holes": 2,
      "Points": 2187,
      "Type": "available"
    },
    "2": {
      "Area km2": 26.761054557621,
      "Holes": 4,
      "Points": 1009,
      "Type": "available"
    },
    "3": {
      "Points": 42,
      "Type": "fixed"
    }
  }
}
```

A extração é direta: iterar sobre `Zones`, filtrar por `Type`, somar os campos.

---

### Instâncias Numéricas (0–505) — Arquivos `.txt`

As 506 instâncias sintéticas (geradas por script Python com NumPy e Shapely,
conforme `instances/sites/5/README.md`) contêm apenas arquivos brutos:

```
instances/sites/0/
├── availablePositions.txt   # posições candidatas (x y z AEF zone_id)
├── fixed_wf.txt             # turbinas fixas     (x y z col4 col5)
├── geometry.txt             # vértices dos polígonos de cada zona
├── turbines_per_zone.txt    # min/max turbinas por zona
└── plot.png
```

Não há cálculo de área, não há tipagem de zonas, não há contagem de buracos.

---

## Solução: Equivalência Reversa

Para cada coluna, foi identificado o arquivo `.txt` equivalente e aplicada a
transformação necessária.

---

### `total_area_km2` — Calculado via Shapely

**Arquivo:** `geometry.txt`

O arquivo contém os vértices dos polígonos de cada zona em coordenadas UTM
(metros), separados por **linhas em branco**:

```
145806.32  110136.04   ← vértice 1 da zona 1
180180.72  106501.51   ← vértice 2
179933.58  133304.01   ← vértice 3
145806.32  110136.04   ← fecha o polígono (igual ao vértice 1)
                       ← linha em branco = separador entre zonas
110938.09  119753.31   ← vértice 1 da zona 2
...
```

**Solução:** parsear os polígonos, calcular área via fórmula de Gauss (Shoelace)
usando a biblioteca Shapely e converter de m² para km²:

```python
from shapely.geometry import Polygon

def _polygon_area_km2(coords):
    poly = Polygon(coords)        # coords em metros
    return poly.area / 1_000_000  # m² → km²
```

**Validação cruzada:** Para a instância **A**, o `info.json` registra
`50.423 + 26.761 = 77.184 km²`. Rodando o parser no `geometry.txt` da
instância A (que também possui esse arquivo), o resultado obtido foi
**77.184 km²** — confirmando a equivalência ✓.

---

### `total_holes` — Fixado em 0

**Por que não há buracos?**

As instâncias sintéticas foram geradas por um script Python que cria polígonos
simples (convexos ou côncavos, mas sem exclusões internas). O `geometry.txt`
dessas instâncias contém apenas os **contornos externos** de cada zona, sem
representação de obstáculos interiores (recifes, cabos, áreas protegidas).

Nas instâncias reais (A–J), os buracos representam zonas de exclusão dentro da
área disponível e estão explicitamente modelados no `info.json`.

**Decisão:** `total_holes = 0` para todas as instâncias numéricas.

> **Possível melhoria:** Os buracos poderiam ser aproximados contando regiões
> do bounding box da zona que estão *dentro* do polígono mas *ausentes* do grid
> de `availablePositions.txt`. Essa heurística não foi implementada pois
> dependeria de suposições sobre o espaçamento do grid.

---

### `total_available_points` — Contagem de linhas

**Arquivo:** `availablePositions.txt`

Cada linha representa uma posição candidata para instalação de turbina.
Estrutura das 5 colunas: `x  y  z  AEF  zone_id`

```
179621.14  133064.71  -27.66  2668697.70  1
179781.02  133064.71  -27.34  2645012.90  1
...
```

**Solução:** contar linhas não-vazias.

```python
with open(avail_path) as f:
    total_available_points = sum(1 for line in f if line.strip())
```

**Validação:** Para a instância 0, `availablePositions.txt` tem **42.616 linhas**.
Cruzando com a coluna `zone_id`, zonas 1+2+3 somam 17.400+18.853+6.363 = **42.616** ✓.

Para a instância A, o `info.json` diz `Points: 2187 + 1009 = 3.196`.
O `availablePositions.txt` da instância A tem **3.196 linhas** ✓.

---

### `total_fixed_turbines` — Contagem de linhas

**Arquivo:** `fixed_wf.txt`

Cada linha representa uma turbina cuja posição é pré-definida (não otimizável).
Estrutura das 5 colunas: `x  y  z  col4  col5`

```
181567.79  112249.12  0.0  4  4
183007.73  112262.40  0.0  4  4
...
```

**Solução:** contar linhas não-vazias.

**Validação:** Para a instância A, o `info.json` registra a zona 3 com
`"Points": 42` e `"Type": "fixed"`. O `fixed_wf.txt` da instância A tem
**42 linhas** ✓.

---

### `density` — Derivado

```python
density = total_available_points / total_area_km2
```

Calculado a partir das duas colunas acima. Retorna `NaN` se `total_area_km2` for
zero ou indisponível.

---

## Tabela Resumo da Equivalência

| Coluna | Instâncias A–J (`info.json`) | Instâncias 0–505 (`.txt`) |
|---|---|---|
| `total_area_km2` | `sum(Area km2)` onde `Type == "available"` | Shapely sobre polígonos de `geometry.txt` |
| `total_holes` | `sum(Holes)` onde `Type == "available"` | **0** (instâncias sintéticas) |
| `total_available_points` | `sum(Points)` onde `Type == "available"` | `wc -l availablePositions.txt` |
| `total_fixed_turbines` | `sum(Points)` onde `Type == "fixed"` | `wc -l fixed_wf.txt` |
| `density` | calculado | calculado |

---

## Validação Final

Após rodar o pipeline completo sobre as 516 instâncias:

```
DataFrame final: 516 linhas × 106 colunas
NaNs em Raw features (5 colunas): 0
```

Amostra das instâncias letra para conferência visual:

| Instance_ID | total_area_km2 | total_holes | total_available_points | total_fixed_turbines | density |
|---|---|---|---|---|---|
| A | 77.18 | 6 | 3196 | 42 | 41.41 |
| B | 186.56 | 2 | 6974 | 15 | 37.38 |
| C | 170.51 | 4 | 7090 | 8 | 41.58 |
| D | 319.24 | 2 | 10398 | 45 | 32.57 |
| E | 259.42 | 12 | 11478 | 40 | 44.24 |
| F | 299.27 | 5 | 11536 | 12 | 38.55 |
| G | 263.13 | 3 | 14602 | 35 | 55.49 |
| H | 353.71 | 7 | 19458 | 40 | 55.01 |
| I | 588.63 | 4 | 20211 | 36 | 34.34 |
| J | 442.09 | 8 | 21634 | 75 | 48.94 |

# CCKP (Python + Gurobi)

Cutting-plane methods for the Cardinality-Constrained Knapsack Problem (CCKP):

- **`violation_max_cp`** — max-violation cut generation (MIP separation subproblem)
- **`greedy_cp`** — greedy cut generation heuristic

Requires [Gurobi](https://www.gurobi.com/) (`pip install gurobipy`) and a valid license.

## Layout

```
CCKP_python/
├── data/                 # test instances (CSV)
├── src/
│   ├── cckp.py           # solvers
│   ├── readdata.py       # CSV loader
│   ├── main.py           # single-run entry point
│   └── run_all.py        # batch runner
├── requirements.txt
└── README.md
```

## Install

```bash
pip install -r requirements.txt
```

## Run one experiment

```bash
python src/main.py [csv_file] [n] [method]
```

Defaults: `data/cckp_test_set_50.csv`, `n=50`, `method=violation_max_cp`.

```bash
python src/main.py data/cckp_test_set_50.csv 50 violation_max_cp
python src/main.py data/cckp_test_set_50.csv 50 greedy_cp
```

## Batch run

Default size grid: `10..100` (step 10), `200..1000` (step 200), `2000, 4000, …, 10000`.

```bash
python src/run_all.py
python src/run_all.py --method greedy_cp
python src/run_all.py --method all --max-n 100
python src/run_all.py --sizes 50 100 200 --method violation_max_cp
```

Large `n` with `violation_max_cp` uses a 3600s per-instance limit.

## Outputs

Each run appends one object to a JSON array under the repo root:

| Method | File |
|--------|------|
| `greedy_cp` | `result_greedy_cp.json` |
| `violation_max_cp` | `result_violation_max.json` |

Fields include `reduced_gap_avg`, `time_avg_sec`, `iteration_avg`, and for max-violation also `sub_solve_time_avg_sec`.

## CSV format

Each row:

`c_1…c_n, a_1…a_n, b, K, z*, z^L, time_z*, time_z^L`

- `n ≤ 100`: 100 instances per file  
- `n > 100`: 10 instances per file  

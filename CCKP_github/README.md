# CCKP (Cutting Plane for CCKP)

This repository contains a Java implementation for solving CCKP instances with two cut-generation methods:

- `violation_max_cp`
- `greedy_cp`

Running the code will generate result files as JSON arrays (they are **not** intended to be committed).

## Project structure

- `src/main.java`: entry point
- `src/CCKP.java`: solver implementation
- `src/readdata.java`: CSV loader
- `data/`: input instances (CSV)

## How to run

### Defaults (no CLI args)

`src/main.java` contains default values:

- default file: `data/cckp_test_set_50.csv`
- default n: `50`
- default method: `violation_max_cp`

So you can run without any arguments.

### Run a single file with parameters

Run one CSV file with explicit `n` and method:

```bash
java main <csv_file> <n> <method>
```

Examples:

```bash
java main data/cckp_test_set_50.csv 50 violation_max_cp
java main data/cckp_test_set_50.csv 50 greedy_cp
```

## Outputs

The solver appends one JSON object per run into these files (JSON array format):

- `result_heur_maximal.json` (from `greedy_cp`)
- `result_exact_park_maximal.json` (from `violation_max_cp`)

## Notes

- `.lp` model dump files are not generated anymore, and are ignored via `.gitignore`.
- This project requires IBM ILOG CPLEX (Java) available on the classpath.


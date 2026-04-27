# ============================================================
# Purpose
# - Generate random CCKP test instances.
# - Keep only instances satisfying zstar != zL (within tolerance).
# - Save CSV files in a format directly readable by the Java code.
#
# Output CSV row format
# - Each row:
#   c_1, ..., c_n, a_1, ..., a_n, b, K, zstar, zL, time_zstar, time_zL
#
# Notes
# - time_zstar: elapsed wall-clock time for solving zstar model
# - time_zL   : elapsed wall-clock time for solving zL model
# ============================================================

import os
import csv
import math
import time
import random
import gurobipy as gp
from gurobipy import GRB


def solve_zL(c, a, b, K, time_limit=None):
    n = len(c)

    model = gp.Model("zL_model")
    model.Params.OutputFlag = 0
    if time_limit is not None:
        model.Params.TimeLimit = time_limit

    x = model.addVars(n, lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name="x")

    model.setObjective(gp.quicksum(c[i] * x[i] for i in range(n)), GRB.MAXIMIZE)
    model.addConstr(gp.quicksum(a[i] * x[i] for i in range(n)) <= b, name="capacity")
    model.addConstr(gp.quicksum(x[i] for i in range(n)) <= K, name="cardinality")

    start_time = time.time()
    model.optimize()
    elapsed_time = time.time() - start_time

    if model.Status == GRB.OPTIMAL:
        return model.ObjVal, elapsed_time
    elif model.Status == GRB.TIME_LIMIT and model.SolCount > 0:
        return model.ObjVal, elapsed_time
    else:
        raise RuntimeError(f"zL solve failed. Status = {model.Status}")


def solve_zstar(c, a, b, K, time_limit=None):
    n = len(c)

    model = gp.Model("zstar_model")
    model.Params.OutputFlag = 0
    if time_limit is not None:
        model.Params.TimeLimit = time_limit

    x = model.addVars(n, lb=0.0, vtype=GRB.CONTINUOUS, name="x")
    z = model.addVars(n, vtype=GRB.BINARY, name="z")

    model.setObjective(gp.quicksum(c[i] * x[i] for i in range(n)), GRB.MAXIMIZE)
    model.addConstr(gp.quicksum(a[i] * x[i] for i in range(n)) <= b, name="capacity")
    model.addConstrs((x[i] <= z[i] for i in range(n)), name="link")
    model.addConstr(gp.quicksum(z[i] for i in range(n)) <= K, name="cardinality_z")

    start_time = time.time()
    model.optimize()
    elapsed_time = time.time() - start_time

    if model.Status == GRB.OPTIMAL:
        return model.ObjVal, elapsed_time
    elif model.Status == GRB.TIME_LIMIT and model.SolCount > 0:
        return model.ObjVal, elapsed_time
    else:
        raise RuntimeError(f"zstar solve failed. Status = {model.Status}")


def generate_one_instance(n, rng):
    K = max(n // 5, 3)
    r = K / n

    c = [rng.randint(0, 99) for _ in range(n)]
    a = [rng.randint(5, 99) for _ in range(n)]
    b = max(math.floor(r * sum(a)), max(a) + 1)

    # Original behavior: solve to optimality (no time limit)
    zL, time_zL = solve_zL(c, a, b, K, time_limit=None)
    zstar, time_zstar = solve_zstar(c, a, b, K, time_limit=None)

    return c, a, b, K, zstar, zL, time_zstar, time_zL


def is_good_instance(zstar, zL, tol=1e-6):
    return abs(zstar - zL) > tol


def get_output_filename(n):
    if n >= 100:
        return f"data/cckp_test_set_{n}.csv"
    return f"data/cckp_test_set_0{n}.csv"


def generate_csv_for_n(
    n,
    target_num_instances=100,
    max_attempts=20000,
    seed=42,
    tol=1e-6
):
    rng = random.Random(seed + n)
    os.makedirs("data", exist_ok=True)

    output_file = get_output_filename(n)
    accepted_rows = []
    attempts = 0

    while len(accepted_rows) < target_num_instances and attempts < max_attempts:
        attempts += 1

        c, a, b, K, zstar, zL, time_zstar, time_zL = generate_one_instance(n, rng)

        if is_good_instance(zstar, zL, tol=tol):
            row = []
            row.extend(c)
            row.extend(a)
            row.append(b)
            row.append(K)
            row.append(zstar)
            row.append(zL)
            row.append(time_zstar)
            row.append(time_zL)

            accepted_rows.append(row)

            print(
                f"[ACCEPT] n={n:3d}, accepted={len(accepted_rows):3d}/{target_num_instances}, "
                f"attempt={attempts:5d}, diff={zstar - zL:.6f}, "
                f"zstar={zstar:.6f}, zL={zL:.6f}, "
                f"time_zstar={time_zstar:.4f}, time_zL={time_zL:.4f}"
            )
        else:
            print(
                f"[REJECT] n={n:3d}, accepted={len(accepted_rows):3d}/{target_num_instances}, "
                f"attempt={attempts:5d}, diff={zstar - zL:.6f}, "
                f"time_zstar={time_zstar:.4f}, time_zL={time_zL:.4f}"
            )

    if len(accepted_rows) < target_num_instances:
        raise RuntimeError(
            f"Could not generate enough instances for n={n}. "
            f"Accepted {len(accepted_rows)} out of {target_num_instances} "
            f"within {max_attempts} attempts."
        )

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(accepted_rows)

    print(f"Saved: {output_file}")
    print(f"Accepted {len(accepted_rows)} instances out of {attempts} attempts for n={n}.")


def generate_all_data():
    for k in range(2, 11):
        n = 10 * k
        generate_csv_for_n(
            n=n,
            target_num_instances=100,
            max_attempts=20000,
            seed=42,
            tol=1e-6
        )


if __name__ == "__main__":
    generate_all_data()
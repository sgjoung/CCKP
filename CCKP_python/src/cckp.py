"""CCKP cutting-plane solvers (Python / Gurobi).

Methods:
  - greedy_cp
  - violation_max_cp (max-violation separation)
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import List, Optional, Sequence

import gurobipy as gp
from gurobipy import GRB


def argsort_desc(values: Sequence[float]) -> List[int]:
    """Return indices sorted by values descending."""
    h = len(values)
    index = list(range(h))
    for i in range(h - 1, 0, -1):
        min_pos = 0
        for j in range(1, i + 1):
            if values[index[j]] < values[index[min_pos]]:
                min_pos = j
        index[i], index[min_pos] = index[min_pos], index[i]
    return index


def average_prefix(arr: Optional[Sequence[float]], length: int) -> float:
    if arr is None or length <= 0:
        return 0.0
    k = min(length, len(arr))
    if k == 0:
        return 0.0
    return sum(arr[i] for i in range(k)) / k


def time_limit_seconds_for_n(n: int) -> float:
    return 300.0 if n <= 100 else 3600.0


def remaining_time(inst_start: float, limit_sec: float) -> float:
    return max(0.0, limit_sec - (time.time() - inst_start))


def set_remaining_time(model: gp.Model, inst_start: float, limit_sec: float) -> None:
    model.Params.TimeLimit = remaining_time(inst_start, limit_sec)


_RESULT_DIR = Path(__file__).resolve().parent.parent


def append_json_array(filename: str, obj: dict) -> None:
    path = Path(filename)
    if not path.is_absolute():
        path = _RESULT_DIR / path
    json_object = json.dumps(obj, ensure_ascii=False)
    if not path.exists() or path.read_text(encoding="utf-8").strip() == "":
        path.write_text("[\n" + json_object + "\n]\n", encoding="utf-8")
        return

    existing = path.read_text(encoding="utf-8").strip()
    idx = existing.rfind("]")
    if idx < 0:
        path.write_text("[\n" + json_object + "\n]\n", encoding="utf-8")
        return

    before = existing[:idx].rstrip()
    after = existing[idx:]
    if before.endswith("["):
        out = before + "\n" + json_object + "\n" + after + "\n"
    else:
        out = before + ",\n" + json_object + "\n" + after + "\n"
    path.write_text(out, encoding="utf-8")


class CCKP:
    def __init__(
        self,
        n: int,
        K: List[float],
        b: List[float],
        c: List[List[float]],
        a: List[List[float]],
        zstar: List[float],
        zL: List[float],
        time_zstar: Optional[List[float]] = None,
        time_zL: Optional[List[float]] = None,
    ):
        self.n = n
        self.K = list(K)
        self.b = list(b)
        self.c = [list(row) for row in c]
        self.a = [list(row) for row in a]
        self.zstar = list(zstar)
        self.zL = list(zL)
        self.time_zstar = list(time_zstar) if time_zstar is not None else None
        self.time_zL = list(time_zL) if time_zL is not None else None
        self.num = 100 if n <= 100 else 10
        self.gap = [0.0] * self.num
        self.avggap = 0.0
        self.avggap2 = 0.0
        self.avgiter = 0.0

    def _build_base_model(self, index: int):
        model = gp.Model(f"cckp_{index}")
        model.Params.OutputFlag = 0
        x = model.addVars(self.n, lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name="x")
        model.setObjective(
            gp.quicksum(self.c[index][i] * x[i] for i in range(self.n)),
            GRB.MAXIMIZE,
        )
        model.addConstr(
            gp.quicksum(self.a[index][i] * x[i] for i in range(self.n)) <= self.b[index],
            name="capacity",
        )
        model.addConstr(
            gp.quicksum(x[i] for i in range(self.n)) <= self.K[index],
            name="cardinality",
        )
        return model, x

    def greedy_cp(self) -> float:
        """Greedy cutting-plane heuristic."""
        start = time.time()
        limit_sec = time_limit_seconds_for_n(self.n)
        timeouts = 0
        avg_rel_gap = 0.0
        self.avggap = 0.0
        self.avggap2 = 0.0
        self.avgiter = 0.0

        for index in range(self.num):
            inst_start = time.time()
            model, x = self._build_base_model(index)
            count = 0

            set_remaining_time(model, inst_start, limit_sec)
            model.optimize()

            while count < 100:
                count += 1
                xval = [x[i].X for i in range(self.n)]
                value = [xval[i] + 0.0001 * self.a[index][i] for i in range(self.n)]
                sorted_index = argsort_desc(value)

                alpha = [0] * self.n
                beta = [0] * self.n
                minf = float("inf")
                delta = self.b[index]
                added = 0

                for i in range(self.n):
                    if added == self.K[index]:
                        break
                    si = sorted_index[i]
                    if delta - self.a[index][si] > 0:
                        alpha[si] = 1
                        delta = delta - self.a[index][si]
                        if minf > self.a[index][si]:
                            minf = self.a[index][si]
                        added += 1

                for i in range(self.n):
                    if alpha[i] < 0.5 and self.a[index][i] <= minf:
                        beta[i] = 1

                equal = all(
                    self.a[index][i] == self.a[index][i + 1] for i in range(self.n - 1)
                )

                if added == self.K[index] and delta > 0 and not equal:
                    coeffs = []
                    for i in range(self.n):
                        if alpha[i] + beta[i] > 0.5:
                            coeffs.append(self.a[index][i] + delta)
                            self.a[index][i] = self.a[index][i] + delta
                        else:
                            coeffs.append(self.a[index][i])
                    rhsval = self.b[index] + (self.K[index] - 1) * delta
                    self.b[index] = self.b[index] + (self.K[index] - 1) * delta
                    model.addConstr(
                        gp.quicksum(coeffs[i] * x[i] for i in range(self.n)) <= rhsval
                    )
                    set_remaining_time(model, inst_start, limit_sec)
                    model.optimize()
                else:
                    break

            obj = model.ObjVal
            self.gap[index] = 1 - (obj - self.zstar[index]) / (
                self.zL[index] - self.zstar[index]
            )
            avg_rel_gap += (self.zL[index] - obj) / self.zL[index]
            red = 1 - (obj - self.zstar[index]) / (self.zL[index] - self.zstar[index])
            self.avggap += red
            self.avggap2 += red * red
            self.avgiter += count

            if (time.time() - inst_start) >= limit_sec:
                timeouts += 1
            model.dispose()

        end = time.time()
        self.avggap /= self.num
        self.avggap2 /= self.num
        avg_rel_gap /= self.num
        stdv = math.sqrt(max(0.0, self.avggap2 - self.avggap * self.avggap))

        record = {
            "method": "greedy_cp",
            "n": self.n,
            "reduced_gap_avg": self.avggap,
            "reduced_gap_stdv": stdv,
            "time_avg_sec": ((end - start) / self.num),
            "iteration_avg": self.avgiter / self.num,
            "timeouts": timeouts,
            "rel_gap_avg": avg_rel_gap,
            "avg_zstar": average_prefix(self.zstar, self.num),
            "avg_zl": average_prefix(self.zL, self.num),
            "avg_time_zstar": average_prefix(self.time_zstar, self.num),
            "avg_time_zl": average_prefix(self.time_zL, self.num),
        }
        append_json_array("result_greedy_cp.json", record)
        return self.avggap

    def violation_max_cp(self) -> float:
        """Max-violation cutting plane (MIP separation subproblem)."""
        start = time.time()
        # Enforce 3600s overall per instance regardless of n.
        limit_sec = 3600.0
        timeouts = 0
        avg_rel_gap = 0.0
        sub_solve_time_per_instance = [0.0] * self.num
        self.avggap = 0.0
        self.avggap2 = 0.0
        self.avgiter = 0.0

        for index in range(self.num):
            instance_sub_solve_sec = 0.0
            inner_start = time.time()
            model, x = self._build_base_model(index)
            count = 0

            set_remaining_time(model, inner_start, limit_sec)
            model.optimize()

            while count < 1000:
                count += 1
                xval = [x[i].X for i in range(self.n)]
                alpha = [0.0] * self.n
                beta = [0.0] * self.n
                delta = self.b[index]

                sub = gp.Model(f"sub_{index}_{count}")
                sub.Params.OutputFlag = 0

                var_alpha = sub.addVars(self.n, vtype=GRB.BINARY, name="alpha")
                var_beta = sub.addVars(self.n, vtype=GRB.BINARY, name="beta")
                var_delta = sub.addVar(
                    lb=0.0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name="delta"
                )
                var_u = sub.addVars(
                    self.n, lb=0.0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name="u"
                )
                var_v = sub.addVars(
                    self.n, lb=0.0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name="v"
                )

                sub.setObjective(
                    gp.quicksum(
                        xval[i] * var_u[i] + xval[i] * var_v[i] for i in range(self.n)
                    )
                    - (self.K[index] - 1) * var_delta
                    + gp.quicksum(
                        0.00001 * self.a[index][i] * var_alpha[i] for i in range(self.n)
                    ),
                    GRB.MAXIMIZE,
                )

                a_for_sort = list(self.a[index])
                sorted_index = argsort_desc(a_for_sort)

                sub.addConstr(
                    gp.quicksum(var_alpha[i] for i in range(self.n)) == self.K[index],
                    name="subconst1",
                )
                for i in range(self.n):
                    sub.addConstr(var_alpha[i] + var_beta[i] <= 1, name=f"subconst2_{i}")

                for i in range(self.n):
                    expr = var_beta[sorted_index[i]] - gp.quicksum(
                        var_alpha[sorted_index[j]] for j in range(i)
                    )
                    sub.addConstr(expr >= -self.K[index] + 1, name=f"subconst3_1_{i}")

                for i in range(self.n):
                    expr = self.K[index] * var_beta[sorted_index[i]] - gp.quicksum(
                        var_alpha[sorted_index[j]] for j in range(i)
                    )
                    sub.addConstr(expr <= 0, name=f"subconst3_2_{i}")

                sub.addConstr(
                    var_delta
                    + gp.quicksum(self.a[index][i] * var_alpha[i] for i in range(self.n))
                    == self.b[index],
                    name="subconst4",
                )

                b_idx = self.b[index]
                for i in range(self.n):
                    sub.addConstr(var_u[i] - b_idx * var_alpha[i] <= 0)
                    sub.addConstr(var_u[i] - var_delta - b_idx * var_alpha[i] >= -b_idx)
                    sub.addConstr(var_v[i] - b_idx * var_beta[i] <= 0)
                    sub.addConstr(var_v[i] - var_delta - b_idx * var_beta[i] >= -b_idx)

                    sub.addConstr(var_u[i] + b_idx * var_alpha[i] >= 0)
                    sub.addConstr(var_u[i] - var_delta + b_idx * var_alpha[i] <= b_idx)
                    sub.addConstr(var_v[i] + b_idx * var_beta[i] >= 0)
                    sub.addConstr(var_v[i] - var_delta + b_idx * var_beta[i] <= b_idx)

                set_remaining_time(sub, inner_start, limit_sec)
                sub_solve_start = time.perf_counter()
                sub.optimize()
                instance_sub_solve_sec += time.perf_counter() - sub_solve_start

                if sub.SolCount > 0:
                    alpha = [var_alpha[i].X for i in range(self.n)]
                    beta = [var_beta[i].X for i in range(self.n)]
                    delta = var_delta.X

                minf = float("inf")
                for i in range(self.n):
                    if alpha[i] > 0.5 and minf > self.a[index][i]:
                        minf = self.a[index][i]
                for i in range(self.n):
                    if alpha[i] < 0.5 and self.a[index][i] <= minf:
                        beta[i] = 1

                sub.dispose()

                equal = all(
                    self.a[index][i] == self.a[index][i + 1] for i in range(self.n - 1)
                )

                if delta > 0 and not equal:
                    coeffs = []
                    for i in range(self.n):
                        if alpha[i] + beta[i] > 0.5:
                            coeffs.append(self.a[index][i] + delta)
                            self.a[index][i] = self.a[index][i] + delta
                        else:
                            coeffs.append(self.a[index][i])
                    rhsval = self.b[index] + (self.K[index] - 1) * delta
                    self.b[index] = self.b[index] + (self.K[index] - 1) * delta
                    model.addConstr(
                        gp.quicksum(coeffs[i] * x[i] for i in range(self.n)) <= rhsval
                    )
                    set_remaining_time(model, inner_start, limit_sec)
                    model.optimize()
                else:
                    break

            obj = model.ObjVal
            self.gap[index] = 1 - (obj - self.zstar[index]) / (
                self.zL[index] - self.zstar[index]
            )
            avg_rel_gap += (self.zL[index] - obj) / self.zL[index]
            red = 1 - (obj - self.zstar[index]) / (self.zL[index] - self.zstar[index])
            self.avggap += red
            self.avggap2 += red * red
            self.avgiter += count

            if (time.time() - inner_start) >= limit_sec:
                timeouts += 1
            sub_solve_time_per_instance[index] = instance_sub_solve_sec
            model.dispose()

        end = time.time()
        self.avggap /= self.num
        self.avggap2 /= self.num
        avg_rel_gap /= self.num
        stdv = math.sqrt(max(0.0, self.avggap2 - self.avggap * self.avggap))
        sub_solve_time_avg = average_prefix(sub_solve_time_per_instance, self.num)

        record = {
            "method": "violation_max_cp",
            "n": self.n,
            "reduced_gap_avg": self.avggap,
            "reduced_gap_stdv": stdv,
            "time_avg_sec": ((end - start) / self.num),
            "iteration_avg": self.avgiter / self.num,
            "timeouts": timeouts,
            "rel_gap_avg": avg_rel_gap,
            "sub_solve_time_avg_sec": sub_solve_time_avg,
            "avg_zstar": average_prefix(self.zstar, self.num),
            "avg_zl": average_prefix(self.zL, self.num),
            "avg_time_zstar": average_prefix(self.time_zstar, self.num),
            "avg_time_zl": average_prefix(self.time_zL, self.num),
        }
        append_json_array("result_violation_max.json", record)
        return self.avggap

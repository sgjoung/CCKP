"""CSV loader for CCKP instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class CCKPData:
    n: int
    K: List[float]
    b: List[float]
    c: List[List[float]]
    a: List[List[float]]
    zstar: List[float]
    zL: List[float]
    time_zstar: List[float]
    time_zL: List[float]


def readdata(file: str | None, n: int) -> CCKPData:
    csv_file = file if file and file.strip() else f"data/cckp_test_set_{n}.csv"
    num_rows = 100 if n <= 100 else 10
    expected_cols = 2 * n + 6  # c[n], a[n], b, K, zstar, zL, timeZstar, timeZL

    c: List[List[float]] = []
    a: List[List[float]] = []
    b: List[float] = []
    K: List[float] = []
    zstar: List[float] = []
    zL: List[float] = []
    time_zstar: List[float] = []
    time_zL: List[float] = []

    with open(csv_file, "r", encoding="utf-8") as f:
        for row_index, line in enumerate(f):
            if row_index >= num_rows:
                break
            fields = line.strip().split(",")
            if len(fields) < expected_cols:
                raise ValueError(
                    f"Invalid CSV format in {csv_file} at row {row_index + 1}: "
                    f"expected at least {expected_cols} columns, got {len(fields)}"
                )

            loc = 0
            c_row = [float(int(fields[loc + i])) for i in range(n)]
            loc += n
            a_row = [float(int(fields[loc + i])) for i in range(n)]
            loc += n

            c.append(c_row)
            a.append(a_row)
            b.append(float(fields[loc]))
            loc += 1
            K.append(float(fields[loc]))
            loc += 1
            zstar.append(float(fields[loc]))
            loc += 1
            zL.append(float(fields[loc]))
            loc += 1
            time_zstar.append(float(fields[loc]))
            loc += 1
            time_zL.append(float(fields[loc]))

    return CCKPData(
        n=n,
        K=K,
        b=b,
        c=c,
        a=a,
        zstar=zstar,
        zL=zL,
        time_zstar=time_zstar,
        time_zL=time_zL,
    )

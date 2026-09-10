"""Entry point for CCKP Python / Gurobi solver.

Usage:
    python main.py [csv_file] [n] [method]

method is ``violation_max_cp`` or ``greedy_cp``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _SRC_DIR.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from cckp import CCKP
from readdata import readdata

METHODS = ("violation_max_cp", "greedy_cp")


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    default_n = 50
    default_file = str(_ROOT_DIR / "data" / f"cckp_test_set_{default_n}.csv")
    default_method = "violation_max_cp"

    file = default_file
    n = default_n
    method = default_method

    if len(argv) >= 1 and argv[0].strip():
        file = argv[0].strip()
    if len(argv) >= 2 and argv[1].strip():
        n = int(argv[1].strip())
    if len(argv) >= 3 and argv[2].strip():
        method = argv[2].strip()

    if not os.path.isabs(file) and not Path(file).exists():
        candidate = _ROOT_DIR / file
        if candidate.exists():
            file = str(candidate)

    data = readdata(file, n)
    prob = CCKP(
        data.n,
        data.K,
        data.b,
        data.c,
        data.a,
        data.zstar,
        data.zL,
        data.time_zstar,
        data.time_zL,
    )

    if method == "violation_max_cp":
        prob.violation_max_cp()
    elif method == "greedy_cp":
        prob.greedy_cp()
    else:
        raise ValueError(
            f"Unknown method: {method} (expected: {', '.join(METHODS)})"
        )


if __name__ == "__main__":
    main()

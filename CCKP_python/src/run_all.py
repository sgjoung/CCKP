"""Run CCKP experiments for the standard size grid.

Default sizes:
    10, 20, ..., 100
    200, 400, ..., 1000
    2000, 4000, 6000, 8000, 10000

Usage:
    python src/run_all.py
    python src/run_all.py --method greedy_cp
    python src/run_all.py --method all
    python src/run_all.py --max-n 100
    python src/run_all.py --sizes 50 100 200 --method violation_max_cp
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import traceback
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _SRC_DIR.parent
_DATA_DIR = _ROOT_DIR / "data"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

ALL_METHODS = ("greedy_cp", "violation_max_cp")

DEFAULT_SIZES = (
    list(range(10, 101, 10))
    + list(range(200, 1001, 200))
    + [2000, 4000, 6000, 8000, 10000]
)


def discover_sizes(data_dir: Path) -> list[int]:
    sizes = []
    pattern = re.compile(r"^cckp_test_set_(\d+)\.csv$")
    for path in data_dir.iterdir():
        match = pattern.match(path.name)
        if match:
            sizes.append(int(match.group(1)))
    return sorted(sizes)


def run_one(n: int, method: str) -> None:
    from cckp import CCKP
    from readdata import readdata

    csv_file = str(_DATA_DIR / f"cckp_test_set_{n}.csv")
    data = readdata(csv_file, n)
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
        raise ValueError(f"Unknown method: {method}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CCKP experiments for all sizes.")
    parser.add_argument(
        "--method",
        choices=[*ALL_METHODS, "both", "all"],
        default="all",
        help="Which method(s) to run (default: all)",
    )
    parser.add_argument("--min-n", type=int, default=None, help="Skip sizes smaller than this")
    parser.add_argument("--max-n", type=int, default=None, help="Skip sizes larger than this")
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=None,
        help="Explicit list of sizes (overrides the default size grid)",
    )
    parser.add_argument(
        "--all-data",
        action="store_true",
        help="Use every cckp_test_set_*.csv under data/ instead of the default grid",
    )
    args = parser.parse_args()

    if args.sizes is not None:
        sizes = sorted(args.sizes)
    elif args.all_data:
        sizes = discover_sizes(_DATA_DIR)
    else:
        sizes = list(DEFAULT_SIZES)

    if args.min_n is not None:
        sizes = [n for n in sizes if n >= args.min_n]
    if args.max_n is not None:
        sizes = [n for n in sizes if n <= args.max_n]

    missing = [n for n in sizes if not (_DATA_DIR / f"cckp_test_set_{n}.csv").exists()]
    if missing:
        raise SystemExit(f"Missing CSV files for sizes: {missing}")

    if not sizes:
        raise SystemExit("No sizes selected after filtering")

    if args.method in ("all", "both"):
        methods = list(ALL_METHODS)
    else:
        methods = [args.method]

    print(f"Sizes ({len(sizes)}): {sizes}")
    print(f"Methods: {methods}")
    print(f"Results directory: {_ROOT_DIR}")
    print("-" * 60)

    total_start = time.time()
    failures: list[tuple[int, str, str]] = []

    for n in sizes:
        for method in methods:
            label = f"n={n}, method={method}"
            print(f"[{time.strftime('%H:%M:%S')}] START {label}", flush=True)
            t0 = time.time()
            try:
                run_one(n, method)
                elapsed = time.time() - t0
                print(
                    f"[{time.strftime('%H:%M:%S')}] DONE  {label} "
                    f"({elapsed:.1f}s)",
                    flush=True,
                )
            except Exception as exc:
                elapsed = time.time() - t0
                failures.append((n, method, str(exc)))
                print(
                    f"[{time.strftime('%H:%M:%S')}] FAIL  {label} "
                    f"({elapsed:.1f}s): {exc}",
                    flush=True,
                )
                traceback.print_exc()

    total_elapsed = time.time() - total_start
    print("-" * 60)
    print(f"Finished in {total_elapsed:.1f}s")
    if failures:
        print(f"Failures ({len(failures)}):")
        for n, method, msg in failures:
            print(f"  n={n}, method={method}: {msg}")
        raise SystemExit(1)
    print("All runs completed successfully.")


if __name__ == "__main__":
    main()

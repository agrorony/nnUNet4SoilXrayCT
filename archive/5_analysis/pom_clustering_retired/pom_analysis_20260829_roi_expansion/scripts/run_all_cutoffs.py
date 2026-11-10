"""Part 3 + Part 4 driver -- run the pinned clustering methodology at
cutoffs 15, 20, and 25 voxels-across-diameter (Part 3 = the 20-voxel run;
Part 4 = the sensitivity sweep, which per the prompt needs full archetype
clustering at 15 and 25 too, not just object counts).

Each cutoff is run in its own subprocess (matching this project's existing
convention of processing one thing at a time to avoid memory leaks across
big-array runs).

Usage:
    python run_all_cutoffs.py --datasets-json datasets_this_run.json
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CUTOFFS = [15, 20, 25]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets-json", required=True)
    args = parser.parse_args()

    for cutoff in CUTOFFS:
        run_name = f"roi_expansion_cutoff{cutoff}"
        print(f"\n{'='*80}\nRunning cutoff={cutoff}  run_name={run_name}\n{'='*80}", flush=True)
        cmd = [
            sys.executable, str(HERE / "run_pom_shape_clustering_generalized.py"),
            "--run-name", run_name,
            "--datasets-json", args.datasets_json,
            "--cutoff-voxels", str(cutoff),
        ]
        # Only the pinned cutoff=20 run needs diagnostic plots for the report.
        if cutoff != 20:
            cmd.append("--no-plots")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"cutoff={cutoff} run failed (exit {result.returncode})")

    print("\nAll cutoff runs complete.")


if __name__ == "__main__":
    main()

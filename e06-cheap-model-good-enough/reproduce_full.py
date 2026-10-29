"""Reproduce full saved-result analysis, bootstrap, evidence and optional chart. No inference."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(*args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures", action="store_true", help="requires optional Matplotlib dependencies")
    args = parser.parse_args()
    run("freeze.py", "--check")
    run("pilot_health.py", "--items", "items.jsonl", "--run-tag", "frozen_20261029", "--evaluation")
    for cohort in ["all", "heldout", "development"]:
        run("analyse.py", "--items", "items.jsonl", "--run-tag", "frozen_20261029", "--cohort", cohort)
        run("analyse_uncertainty.py", "--cohort", cohort)
    run("export_results.py")
    if args.figures:
        run("make_final_chart.py")


if __name__ == "__main__":
    main()

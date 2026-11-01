"""Analyse a complete E02 replay ledger. No model judge and no API calls."""

import argparse
from pathlib import Path

from analysis_e2 import analyse
from e2core import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "development/pilot-run")
    parser.add_argument("--out", type=Path, default=ROOT / "development/pilot-analysis")
    args = parser.parse_args()
    analyse(args.run.resolve(), args.out.resolve())


if __name__ == "__main__":
    main()

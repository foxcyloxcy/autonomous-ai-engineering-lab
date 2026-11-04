"""Run tiny controlled fixtures. Results are NOT SWE-bench/MLE-bench scores."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ael.agents import MutationProposer
from ael.workflow import run_workflow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("runs/benchmark"))
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 10:
        parser.error("repetitions must be 1..10")
    root = Path(__file__).resolve().parent.parent
    results = []
    for repetition in range(args.repetitions):
        for name in ("addition", "product", "affine"):
            fixture = root / "fixtures" / name
            result = run_workflow(fixture / "repo", fixture / "oracle.json", args.output, MutationProposer())
            results.append({**result, "repetition": repetition})
    report = {"schema_version": 1, "benchmark": "ael-controlled-arithmetic-v1",
              "at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "platform": platform.platform(), "provider": "deterministic-ast-baseline", "live_model": False,
              "runs": len(results), "verified": sum(r["status"] == "verified" for r in results),
              "median_seconds": statistics.median(r["duration_seconds"] for r in results),
              "results": results}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["runs"] == report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import json
from pathlib import Path

from .agents import MutationProposer, OllamaProposer
from .memory import Memory
from .sandbox import Sandbox
from .workflow import replay, run_workflow


def main(argv=None):
    parser = argparse.ArgumentParser(description="AEL controlled repair and independent replay")
    subs = parser.add_subparsers(dest="command", required=True)
    run = subs.add_parser("run")
    run.add_argument("--repo", type=Path, required=True)
    run.add_argument("--oracle", type=Path, required=True)
    run.add_argument("--output", type=Path, default=Path("runs"))
    run.add_argument("--provider", choices=("baseline", "ollama"), default="baseline")
    run.add_argument("--model")
    run.add_argument("--max-attempts", type=int, default=24)
    run.add_argument("--retry-of")
    verify = subs.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--oracle", type=Path, required=True)
    subs.add_parser("doctor")
    recover = subs.add_parser("recover")
    recover.add_argument("--memory", type=Path, required=True)
    recover.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = Sandbox().preflight()
        elif args.command == "run":
            if args.provider == "ollama" and not args.model:
                parser.error("--model is required with --provider ollama")
            proposer = OllamaProposer(args.model) if args.provider == "ollama" else MutationProposer()
            result = run_workflow(args.repo, args.oracle, args.output, proposer,
                                  args.max_attempts, args.retry_of)
        elif args.command == "verify":
            result = replay(args.bundle, args.oracle)
        else:
            Memory(args.memory).recover(args.run_id)
            result = {"status": "aborted", "run_id": args.run_id}
        print(json.dumps(result, indent=2))
        status = result.get("status", result.get("verification", {}).get("status"))
        return 1 if status in {"failed", "rejected"} else 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": f"{type(exc).__name__}: {exc}"}))
        return 1

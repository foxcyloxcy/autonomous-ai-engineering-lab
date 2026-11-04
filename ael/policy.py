"""Small, deliberately restrictive language accepted by milestone 1."""

import ast
import hashlib
import json
import math
from pathlib import Path


class PolicyError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and abs(value) <= 10**12


def validate_source(source: str, function: str) -> ast.Module:
    """No imports, calls, attributes, decorators, defaults, globals or loops.

    This is a task admission policy in addition to OS confinement, not a
    general-purpose Python sandbox. Never loosen it without adversarial tests.
    """
    if len(source.encode()) > 8192 or not function.isidentifier() or function.startswith("_"):
        raise PolicyError("source/function outside controlled task limits")
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise PolicyError("invalid Python source") from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise PolicyError("exactly one pure function required")
    fn = tree.body[0]
    args = fn.args
    if (fn.name != function or fn.decorator_list or fn.returns or fn.type_comment
            or getattr(fn, "type_params", []) or args.defaults or args.kw_defaults
            or args.kwarg or args.vararg or args.kwonlyargs or args.posonlyargs
            or not 1 <= len(args.args) <= 4 or len(fn.body) != 1
            or not isinstance(fn.body[0], ast.Return)):
        raise PolicyError("only positional arguments and one return expression allowed")
    names = {arg.arg for arg in args.args}
    if any(arg.annotation or arg.arg.startswith("_") for arg in args.args):
        raise PolicyError("annotations/private arguments denied")
    allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
               ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd)
    nodes = list(ast.walk(tree))
    if len(nodes) > 100:
        raise PolicyError("AST budget exceeded")
    for node in nodes:
        if not isinstance(node, allowed):
            raise PolicyError(f"AST node denied: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in names:
            raise PolicyError("only function arguments may be referenced")
        if isinstance(node, ast.Constant) and not number(node.value):
            raise PolicyError("only finite bounded numeric constants allowed")
    return tree


def load_task(repo: Path) -> tuple[dict, dict[str, str]]:
    """Accept only three bounded regular files; reject links/special files."""
    repo = repo.absolute()
    if repo.is_symlink() or not repo.is_dir():
        raise PolicyError("repository must be a real directory")
    expected = {"task.json", "math_ops.py", "test_math_ops.py"}
    entries = list(repo.iterdir())
    if {p.name for p in entries} != expected:
        raise PolicyError("controlled repository must contain exactly task.json, math_ops.py, test_math_ops.py")
    files = {}
    for path in entries:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
            raise PolicyError("links, special files, and oversized files denied")
        files[path.name] = path.read_text(encoding="utf-8")
    spec = json.loads(files["task.json"])
    if (set(spec) != {"schema_version", "task_id", "function", "description"}
            or spec["schema_version"] != 1 or not isinstance(spec["description"], str)
            or not isinstance(spec["task_id"], str) or not isinstance(spec["function"], str)):
        raise PolicyError("invalid task contract")
    validate_source(files["math_ops.py"], spec["function"])
    return spec, files


def validate_cases(cases: list, arity: int) -> None:
    if not isinstance(cases, list) or not 1 <= len(cases) <= 100:
        raise PolicyError("oracle must have 1..100 cases")
    for case in cases:
        if (not isinstance(case, dict) or set(case) != {"args", "expected"}
                or not isinstance(case["args"], list) or len(case["args"]) != arity
                or not all(number(x) for x in case["args"]) or not number(case["expected"])):
            raise PolicyError("oracle accepts bounded numeric input/output only")


def authorize(action: str) -> None:
    """Milestone 1 has no execution capability for consequential actions."""
    if action not in {"read_controlled_repo", "sandbox_test", "write_run_artifact", "patch_run_copy"}:
        raise PolicyError(f"{action}: explicit human approval and a future capability adapter required")

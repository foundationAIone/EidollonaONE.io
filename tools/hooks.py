#!/usr/bin/env python
from __future__ import annotations
import argparse
import os
import subprocess
import sys
from typing import List


def run_first_existing_script(paths: List[str], script_args: List[str]) -> int:
    for p in paths:
        if os.path.exists(p):
            cmd = [sys.executable, p] + script_args
            return subprocess.call(cmd)
    # Nothing to run; succeed silently
    return 0


def pytest_if_exists(paths: List[str]) -> int:
    existing = [p for p in paths if os.path.exists(p)]
    if not existing:
        return 0
    cmd = [sys.executable, "-m", "pytest", "-q"] + existing
    return subprocess.call(cmd)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("run-first-existing-script")
    s1.add_argument("paths", nargs="+")
    s1.add_argument("--", dest="dashdash", action="store_true")
    s1.add_argument("script_args", nargs=argparse.REMAINDER)

    s2 = sub.add_parser("pytest-if-exists")
    s2.add_argument("paths", nargs="+")

    args = parser.parse_args(argv)

    if args.cmd == "run-first-existing-script":
        # argparse will include "--" in script_args if present; drop it
        script_args = [a for a in getattr(args, "script_args", []) if a != "--"]
        return run_first_existing_script(args.paths, script_args)
    if args.cmd == "pytest-if-exists":
        return pytest_if_exists(args.paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())

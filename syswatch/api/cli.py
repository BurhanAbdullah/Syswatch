#!/usr/bin/env python3
"""Small, dependency-free command helpers used by the SYSWATCH launcher."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_scan() -> int:
    engine = ROOT / "core" / "engine.sh"
    if not engine.exists():
        print(json.dumps({"ok": False, "error": "Security engine not found"}, indent=2))
        return 1
    try:
        proc = subprocess.run(
            ["bash", str(engine)], cwd=str(ROOT), text=True,
            capture_output=True, timeout=60, check=False,
        )
    except subprocess.TimeoutExpired:
        print(json.dumps({"ok": False, "error": "Scan timed out after 60 seconds"}, indent=2))
        return 1
    output = (proc.stdout + proc.stderr).strip()
    print(json.dumps({"ok": proc.returncode == 0, "exit_code": proc.returncode, "output": output[-12000:]}, indent=2))
    return proc.returncode


def main(argv: list[str]) -> int:
    command = argv[0] if argv else "help"
    if command == "scan":
        return run_scan()
    if command in {"help", "-h", "--help"}:
        print("Usage: syswatch <start|stop|restart|status|health|dashboard|open|logs|scan|demo|signal|version|doctor|uninstall>")
        return 0
    print(f"Unknown internal command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

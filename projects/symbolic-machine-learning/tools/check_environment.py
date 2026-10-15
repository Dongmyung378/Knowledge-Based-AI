"""Diagnose the Python/SWI-Prolog bridge without publishing machine-local paths."""

from __future__ import annotations

import argparse
import ctypes.util
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


PACKAGES = ("pyswip", "pytest", "scipy", "click", "networkx", "tabulate", "numpy")
BRIDGE_PROBE = """
import json
from pyswip import Prolog
p = Prolog()
values = [row['Y'] for row in p.query('member(X,[1,2,3]), Y is X*X')]
version = list(p.query('current_prolog_flag(version,V)'))[0]['V']
print(json.dumps({'squares': values, 'version_code': version}))
"""


def probe(*, timeout: float = 20.0) -> dict:
    """Return only versions, checks and actionable hints; omit stdout/stderr paths."""
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None

    try:
        library_found = bool(ctypes.util.find_library("swipl"))
    except OSError:
        library_found = False
    report = {
        "schema_version": 1,
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "packages": versions,
        "runtime_discovery": {
            "swipl_on_path": shutil.which("swipl") is not None,
            "shared_library_discoverable": library_found,
            "swi_home_dir_set": bool(os.environ.get("SWI_HOME_DIR")),
            "libswipl_path_set": bool(os.environ.get("LIBSWIPL_PATH")),
        },
        "checks": {},
        "hints": [],
    }
    checks = report["checks"]
    checks["python_supported"] = sys.version_info >= (3, 10)
    checks["dependencies_installed"] = all(versions.values())
    if not checks["dependencies_installed"]:
        report["hints"].append("Activate the project environment, then install requirements.lock.txt.")

    swipl = shutil.which("swipl")
    checks["swipl_cli"] = False
    if swipl:
        try:
            result = subprocess.run(
                [swipl, "--version"], capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace", check=False,
            )
            match = re.search(r"SWI-Prolog version ([0-9]+\.[0-9]+\.[0-9]+)", result.stdout)
            if result.returncode == 0 and match:
                report["swi_prolog_version"] = match.group(1)
                checks["swipl_cli"] = True
        except (OSError, subprocess.TimeoutExpired):
            pass
    if not checks["swipl_cli"]:
        report["hints"].append("Install SWI-Prolog and add its executable directory to this process's PATH.")
        if platform.system() == "Windows":
            report["hints"].append("The tested Windows runtime is SWI-Prolog 9.2.9 x64; see docs/reproduce.md for the exact installer.")

    checks["pyswip_query"] = False
    try:
        result = subprocess.run(
            [sys.executable, "-c", BRIDGE_PROBE], capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace", check=False,
        )
        if result.returncode == 0:
            # Foreign runtimes can print banners; accept only the final JSON line.
            data = json.loads(result.stdout.strip().splitlines()[-1])
            checks["pyswip_query"] = data.get("squares") == [1, 4, 9]
            if checks["pyswip_query"]:
                report["bridge_query"] = data
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
        pass
    if not checks["pyswip_query"]:
        report["hints"].append(
            "PySwip could not execute the isolated query. Use Python and SWI-Prolog of matching architecture. "
            "For an unregistered Windows runtime, set SWI_HOME_DIR and LIBSWIPL_PATH locally and add bin to PATH."
        )
        if platform.system() == "Windows":
            report["hints"].append(
                "Use the complete tested SWI-Prolog 9.2.9 x64 installation, including its bin directory. "
                "Copying only libswipl.dll is insufficient. A newer runtime is not part of the verified Windows version set."
            )
    report["passed"] = all(checks.values())
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON report; machine-local paths are omitted.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Maximum seconds per subprocess probe.")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    report = probe(timeout=args.timeout)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

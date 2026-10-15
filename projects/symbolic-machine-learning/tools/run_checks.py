"""Run release, environment, regression, and smoke checks in isolated processes.

Use a new output directory for each run. Source paths in the summary are
project-relative; {output_dir} in command templates denotes the selected folder.
The orchestrator imports only the Python standard library, never PySwip.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


PROJECT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "learning/attr_learner.py", "learning/rule_learner.py", "evaluate_attributes.py",
    "evaluate_rules.py", "tools/run_checks.py", "tools/check_environment.py",
    "tools/verify_release.py", "requirements.lock.txt", "setup.cfg",
)
PACKAGES = ("pyswip", "pytest", "numpy", "scipy", "click", "networkx", "tabulate")
FATAL_PATTERNS = {
    "atexit_exception": r"Exception ignored in[^\n]*atexit callback",
    "access_violation": r"access violation",
    "fatal_exception": r"fatal (?:Python error|exception)",
    "segmentation_fault": r"segmentation fault|\bSIGSEGV\b",
}


def _json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def native_failures(stdout, stderr):
    text = stdout + "\n" + stderr
    found = [name for name, pattern in FATAL_PATTERNS.items() if re.search(pattern, text, re.I)]
    if "PL_initialise" in text and re.search(
            r"Traceback|OSError|PrologError|error|exception|invalid handle|could not initialize|returned\s+0", text, re.I):
        found.append("prolog_initialise_error")
    return found


def _source_hashes():
    return {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def _versions():
    packages = {}
    for name in PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    # platform.uname() can spawn an unbounded Windows ``ver`` subprocess.
    # Read these fields directly so every child belongs to a declared stage.
    system = "Windows" if sys.platform == "win32" else "Linux" if sys.platform.startswith("linux") else sys.platform
    machine = (os.environ.get("PROCESSOR_ARCHITECTURE", "unknown") if os.name == "nt"
               else os.uname().machine if hasattr(os, "uname") else "unknown")
    return {"python": ".".join(map(str, sys.version_info[:3])), "system": system,
            "machine": machine, "packages": packages}


def _prepare_output(value):
    requested = Path(value)
    output = (requested if requested.is_absolute() else PROJECT / requested).resolve()
    project = PROJECT.resolve()
    if output.is_relative_to(project) and not output.is_relative_to(project / "outputs"):
        raise ValueError("Project-local output must stay under the outputs directory.")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Choose a new or empty output directory; existing evidence is never overwritten.")
    output.mkdir(parents=True, exist_ok=True)
    return output


def _stage_plan(output):
    return [
        ("release", ["tools/verify_release.py", "--project", "."], 30),
        ("environment", ["tools/check_environment.py", "--output", str(output / "environment.json")], 30),
        ("pytest", ["-m", "pytest", "tests/public", "-q", "--capture=sys",
                    "--basetemp", str(output / "pytest-tmp"),
                    "-o", "cache_dir=" + str(output / "pytest-cache"),
                    "--junitxml", str(output / "pytest-junit.xml"), "-o", "junit_logging=all"], 120),
        ("dtl_smoke", ["evaluate_attributes.py", "eval-size", "-a", "dtl", "-a", "my-dtl",
                       "-s", "4", "-d", "2", "-t", "0.75", "-r", "42"], 30),
        ("foil_smoke", ["evaluate_rules.py", "-a", "foil", "-d", "tests/graph_small.json",
                        "-k", "tests/graph_small.pl", "-t", "reachable(X,Y)", "-r", "-e", "0.8",
                        "-s", "42", "--max-seconds", "20", "--output-json", str(output / "foil-smoke.json")], 30),
    ]


def _check_stage_report(name, output, stdout):
    if name == "release":
        report = json.loads(stdout)
        if report.get("passed") is not True:
            raise ValueError("Release verification did not report success.")
        return report
    if name == "environment":
        report = json.loads((output / "environment.json").read_text(encoding="utf-8"))
        if report.get("passed") is not True:
            raise ValueError("The environment probe did not report success.")
        return {"passed": True, "checks": report.get("checks", {}),
                "swi_prolog_version": report.get("swi_prolog_version")}
    if name == "pytest":
        root = ET.parse(output / "pytest-junit.xml").getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        counts = {key: sum(int(suite.get(key, "0")) for suite in suites)
                  for key in ("tests", "failures", "errors", "skipped")}
        counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
        if counts["tests"] < 1 or counts["failures"] or counts["errors"]:
            raise ValueError("JUnit must contain nonempty tests with zero failures and errors.")
        return counts
    if name == "dtl_smoke":
        baseline = re.search(r"dtl\(baseline\) accuracy:\s*(\d+)/(\d+)", stdout)
        variant = re.search(r"Accuracy of my-dtl\s+(\d+)/(\d+)", stdout)
        if baseline is None or variant is None or any(match.groups() != ("4", "4") for match in (baseline, variant)):
            raise ValueError("The fixed DTL smoke examples did not each produce 4/4 correct predictions.")
        return {"dtl": {"correct": 4, "examples": 4}, "my-dtl": {"correct": 4, "examples": 4}}
    report = json.loads((output / "foil-smoke.json").read_text(encoding="utf-8"))
    algorithms = report.get("algorithms", [])
    rows = algorithms[0].get("predictions", []) if len(algorithms) == 1 else []
    positives = sum(row.get("expected") is True for row in rows)
    negatives = sum(row.get("expected") is False for row in rows)
    correct = sum(row.get("prediction") == row.get("expected") for row in rows)
    if report.get("status") != "passed" or (positives, negatives, correct) != (12, 59, 71):
        raise ValueError("The fixed FOIL hold-out examples did not produce 71/71 correct predictions.")
    return {"positive_examples": positives, "negative_examples": negatives, "correct": correct,
            "swi_prolog_version_number": report.get("environment", {}).get("swi_prolog_version_number")}


def _execute_stage(name, arguments, timeout, output):
    command = [sys.executable, "-B", *arguments]
    displayed = ["python", "-B", *[argument.replace(str(output), "{output_dir}").replace("\\", "/")
                                  for argument in arguments]]
    started = time.perf_counter()
    code, stdout, stderr, timed_out, spawn_error = None, "", "", False, None
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    try:
        completed = subprocess.run(command, cwd=PROJECT, env=environment, stdin=subprocess.DEVNULL,
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, timed_out = _text(exc.stdout), _text(exc.stderr), True
    except OSError as exc:
        spawn_error, stderr = type(exc).__name__, str(exc)
    (output / f"{name}.stdout.log").write_text(stdout, encoding="utf-8")
    (output / f"{name}.stderr.log").write_text(stderr, encoding="utf-8")
    fatal = native_failures(stdout, stderr)
    passed = code == 0 and not timed_out and not spawn_error and not fatal
    result = {"name": name, "status": "passed" if passed else "failed", "command": displayed,
              "timeout_seconds": timeout, "duration_seconds": time.perf_counter() - started,
              "exit_code": code, "timed_out": timed_out, "spawn_error": spawn_error,
              "native_failure_patterns": fatal, "stdout": f"{name}.stdout.log", "stderr": f"{name}.stderr.log",
              "stdout_bytes": len(stdout.encode("utf-8")), "stderr_bytes": len(stderr.encode("utf-8"))}
    if passed:
        try:
            result["checks"] = _check_stage_report(name, output, stdout)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, ET.ParseError) as exc:
            result["status"] = "failed"
            result["report_error"] = (str(exc) if isinstance(exc, ValueError)
                                      and not isinstance(exc, json.JSONDecodeError) else type(exc).__name__)
    _json(output / f"{name}.json", result)
    return result


def run_checks(output_dir="outputs/verification"):
    """Execute guarded stages and return their complete, path-neutral summary."""
    output = _prepare_output(output_dir)
    before = _source_hashes()
    stages, blocked = [], False
    for name, arguments, timeout in _stage_plan(output):
        if blocked:
            stages.append({"name": name, "status": "not_run", "reason": "An earlier stage failed."})
            continue
        stage = _execute_stage(name, arguments, timeout, output)
        stages.append(stage)
        blocked = stage["status"] != "passed"
    after = _source_hashes()
    changed = [name for name in before if before[name] != after[name]]
    summary = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
               "passed": not blocked and not changed, "environment": _versions(),
               "source_sha256": before, "source_changed_files": changed, "stages": stages,
               "command_path_scope": "Project-relative source paths; {output_dir} is the selected evidence folder.",
               "scope": "Checks the current environment and fixed smoke examples; not every input or independent hardware."}
    _json(output / "summary.json", summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="outputs/verification", help="New or empty evidence directory.")
    args = parser.parse_args(argv)
    try:
        report = run_checks(args.output_dir)
    except (OSError, ValueError) as exc:
        print(json.dumps({"passed": False, "error": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}))
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

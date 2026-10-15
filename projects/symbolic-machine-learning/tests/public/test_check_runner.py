"""Subprocess contract tests; these never launch a nested verification suite."""

import json
from pathlib import Path
import subprocess

import pytest

from tools import run_checks as runner


def mock_processes(monkeypatch, *, fatal="", nonzero=None, timeout=None, invalid_report=None):
    calls = []

    def fake_run(command, **kwargs):
        arguments = command[2:]
        name = ("pytest" if arguments[0] == "-m" else {
            "tools/verify_release.py": "release", "tools/check_environment.py": "environment",
            "evaluate_attributes.py": "dtl_smoke", "evaluate_rules.py": "foil_smoke",
        }[arguments[0]])
        calls.append((name, command, kwargs))
        if name == timeout:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=b"partial stdout", stderr=b"partial stderr")
        stdout, stderr = "", ""
        if name == "release":
            stdout = json.dumps({"passed": True, "payload_files": 12})
            stderr = fatal
        elif name == "environment":
            if invalid_report != "missing_environment":
                Path(arguments[arguments.index("--output") + 1]).write_text(
                    json.dumps({"passed": True, "checks": {"bridge": True}, "swi_prolog_version": "9.2.9"}),
                    encoding="utf-8")
            stderr = "Warning: optional diagnostic message.\n"
        elif name == "pytest":
            count = 0 if invalid_report == "empty_junit" else 3
            Path(arguments[arguments.index("--junitxml") + 1]).write_text(
                f'<testsuites><testsuite tests="{count}" failures="0" errors="0" skipped="0" /></testsuites>',
                encoding="utf-8")
            stdout = f"{count} passed"
        elif name == "dtl_smoke":
            score = 3 if invalid_report == "wrong_dtl" else 4
            stdout = f"dtl(baseline) accuracy: 4/4 (1.000))\nAccuracy of my-dtl \t {score}/4 (1.000))"
        else:
            rows = [{"expected": True, "prediction": True} for _ in range(12)]
            rows += [{"expected": False, "prediction": False} for _ in range(59)]
            Path(arguments[arguments.index("--output-json") + 1]).write_text(
                json.dumps({"status": "passed", "algorithms": [{"predictions": rows}]}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 7 if name == nonzero else 0, stdout, stderr)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    return calls


def test_success_requires_all_stages_and_keeps_benign_stderr_as_evidence(tmp_path, monkeypatch):
    calls = mock_processes(monkeypatch)
    output = tmp_path / "evidence"
    report = runner.run_checks(output)
    assert report["passed"]
    assert [name for name, _, _ in calls] == ["release", "environment", "pytest", "dtl_smoke", "foil_smoke"]
    assert [kwargs["timeout"] for _, _, kwargs in calls] == [30, 30, 120, 30, 30]
    assert all(kwargs["stdin"] == subprocess.DEVNULL for _, _, kwargs in calls)
    assert all(kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1" for _, _, kwargs in calls)
    pytest_arguments = calls[2][1]
    assert "--capture=sys" in pytest_arguments
    assert str(output / "pytest-tmp") in pytest_arguments
    assert "cache_dir=" + str(output / "pytest-cache") in pytest_arguments
    assert report["stages"][1]["stderr_bytes"] > 0
    assert report["stages"][2]["checks"]["tests"] == 3
    assert report["stages"][4]["checks"]["correct"] == 71
    assert set(report["source_sha256"]) >= {"learning/rule_learner.py", "learning/attr_learner.py"}
    assert report["source_changed_files"] == []
    assert str(output) not in json.dumps(report)
    assert json.loads((output / "summary.json").read_text(encoding="utf-8"))["passed"]


def test_native_fatal_stderr_fails_even_with_exit_zero_and_stops_later_stages(tmp_path, monkeypatch):
    diagnostics = [
        "Exception ignored in atexit callback: <function cleanupProlog>",
        "Windows fatal exception: access violation",
        "Fatal Python error: Segmentation fault",
        "Traceback\n result = PL_initialise(...)\nOSError: [WinError 6] Invalid handle",
    ]
    for index, text in enumerate(diagnostics):
        calls = mock_processes(monkeypatch, fatal=text)
        output = tmp_path / f"fatal-{index}"
        report = runner.run_checks(output)
        assert not report["passed"]
        assert len(calls) == 1
        assert report["stages"][0]["exit_code"] == 0
        assert report["stages"][0]["native_failure_patterns"]
        assert all(stage["status"] == "not_run" for stage in report["stages"][1:])
        assert (output / "release.stderr.log").read_text(encoding="utf-8") == text


def test_timeout_preserves_partial_output_and_prevents_smoke_execution(tmp_path, monkeypatch):
    calls = mock_processes(monkeypatch, timeout="pytest")
    output = tmp_path / "timeout"
    report = runner.run_checks(output)
    assert not report["passed"]
    assert len(calls) == 3
    stage = report["stages"][2]
    assert stage["timed_out"] and stage["exit_code"] is None
    assert (output / "pytest.stdout.log").read_text(encoding="utf-8") == "partial stdout"
    assert (output / "pytest.stderr.log").read_text(encoding="utf-8") == "partial stderr"
    assert all(stage["status"] == "not_run" for stage in report["stages"][3:])


def test_nonzero_exit_is_not_overridden_by_a_successful_json_payload(tmp_path, monkeypatch):
    calls = mock_processes(monkeypatch, nonzero="environment")
    report = runner.run_checks(tmp_path / "nonzero")
    assert not report["passed"] and len(calls) == 2
    assert report["stages"][1]["exit_code"] == 7
    assert report["stages"][1]["status"] == "failed"


def test_exit_zero_without_valid_report_or_expected_predictions_is_rejected(tmp_path, monkeypatch):
    for failure, count in (("missing_environment", 2), ("empty_junit", 3), ("wrong_dtl", 4)):
        calls = mock_processes(monkeypatch, invalid_report=failure)
        report = runner.run_checks(tmp_path / failure)
        assert not report["passed"]
        assert len(calls) == count
        assert "report_error" in report["stages"][count - 1]


def test_output_guards_preserve_source_directories_and_existing_evidence(tmp_path, monkeypatch):
    calls = mock_processes(monkeypatch)
    with pytest.raises(ValueError, match="under the outputs"):
        runner.run_checks(runner.PROJECT / "learning" / "check-evidence")
    old = tmp_path / "existing"
    old.mkdir()
    (old / "summary.json").write_text("preserved", encoding="utf-8")
    with pytest.raises(ValueError, match="never overwritten"):
        runner.run_checks(old)
    assert (old / "summary.json").read_text(encoding="utf-8") == "preserved"
    assert not calls

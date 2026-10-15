"""Bounded FOIL evaluation on finite graphs with an independent BFS oracle.

This holds out relation pairs within a known graph. It does not test transfer to
an unseen graph or hide the graph's background connected/2 facts from learning.
Each case runs in its own process so a Prolog failure cannot poison later cases.
"""

import argparse
from collections import Counter, deque
import hashlib
from importlib import metadata
import json
import math
from pathlib import Path
import platform
import random
import subprocess
import sys
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
TOPOLOGIES = ("chain", "cyclic", "disconnected", "dense", "self_loop")
SEEDS = (100, 101, 102)


def make_graph(topology, nodes, seed):
    """Create fixed-size graph families; every node has an explicit self-loop."""
    if topology not in TOPOLOGIES or nodes not in (8, 16):
        raise ValueError("Supported cases use the five declared topologies and 8 or 16 nodes.")
    rng = random.Random(seed)
    order = list(range(nodes))
    rng.shuffle(order)
    edges = {(node, node) for node in range(nodes)}
    if topology == "chain":
        edges.update(zip(order, order[1:]))
    elif topology == "cyclic":
        # Two disjoint directed cycles leave both reachable/unreachable pairs.
        for group in (order[:nodes // 2], order[nodes // 2:]):
            edges.update(zip(group, group[1:] + group[:1]))
    elif topology == "disconnected":
        for group in (order[:nodes // 2], order[nodes // 2:]):
            edges.update(zip(group, group[1:]))
    elif topology == "dense":
        # A random dense DAG (plus explicit self-loops) prevents an all-positive
        # strongly connected task, so every predeclared case remains evaluable.
        for index, source in enumerate(order):
            for target in order[index + 1:]:
                if rng.random() < 0.45:
                    edges.add((source, target))
    return sorted(edges)


def bfs_labels(nodes, edges):
    """Independent queue-based oracle; no Prolog and no NetworkX reachability."""
    adjacency = {node: [] for node in range(nodes)}
    for source, target in edges:
        adjacency[source].append(target)
    positives, negatives = [], []
    for source in range(nodes):
        visited = {source}
        pending = deque([source])
        while pending:
            node = pending.popleft()
            for target in adjacency[node]:
                if target not in visited:
                    visited.add(target)
                    pending.append(target)
        for target in range(nodes):
            example = {"X": f"n{source}", "Y": f"n{target}"}
            (positives if target in visited else negatives).append(example)
    return positives, negatives


def shared_split(positive, negative, seed):
    rng = random.Random(seed)
    result = {}
    for name, examples in (("positive", positive), ("negative", negative)):
        count = math.ceil(0.6 * len(examples))
        if not 0 < count < len(examples):
            raise ValueError("A predeclared case must contain training and hold-out examples of both classes.")
        indices = set(rng.sample(range(len(examples)), count))
        result[f"train_{name}"] = [example for index, example in enumerate(examples) if index in indices]
        result[f"holdout_{name}"] = [example for index, example in enumerate(examples) if index not in indices]
    return result


def classification_metrics(rows):
    tp = sum(row["expected"] and row["prediction"] for row in rows)
    tn = sum(not row["expected"] and not row["prediction"] for row in rows)
    fp = sum(not row["expected"] and row["prediction"] for row in rows)
    fn = sum(row["expected"] and not row["prediction"] for row in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return {"examples": len(rows), "true_positive": tp, "true_negative": tn,
            "false_positive": fp, "false_negative": fn,
            "accuracy": (tp + tn) / len(rows) if rows else None,
            "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "balanced_accuracy": (recall + specificity) / 2,
            "exact_match": bool(rows) and fp == 0 and fn == 0}


def environment():
    versions = {}
    for package in ("pyswip", "click", "numpy", "scipy", "networkx"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    return {"python": platform.python_version(), "system": platform.system(),
            "machine": platform.machine(), "dependencies": versions}


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_case(case, max_seconds=12.0, lookahead=0):
    # Import here so orchestrator startup cannot load or corrupt a Prolog engine.
    from learning.rule_learner import FOIL, FOILBudgetExceeded, FOILLearningError, FOILQueryError
    from learning.util import Dataset

    topology, nodes, seed = case["topology"], case["nodes"], case["seed"]
    edges = make_graph(topology, nodes, seed)
    positive, negative = bfs_labels(nodes, edges)
    split = shared_split(positive, negative, seed)
    canonical_data = json.dumps({"pos": positive, "neg": negative}, sort_keys=True, separators=(",", ":"))
    source = "\n".join(f"connected(n{left},n{right})." for left, right in edges) + "\n"
    result = dict(case, status="running", background_edges=[list(edge) for edge in edges],
                  split=split, dataset_sha256=hashlib.sha256(canonical_data.encode()).hexdigest(),
                  kb_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  scope="Unseen relation pairs within the same known graph; not unseen-graph transfer.")
    learner = None
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="foil-case-") as temporary:
        kb = Path(temporary) / "graph.pl"
        kb.write_text(source, encoding="utf-8", newline="\n")
        dataset = Dataset(positive_examples=split["train_positive"], negative_examples=split["train_negative"],
                          kb=str(kb), target="reachable(X,Y)")
        try:
            with FOIL(dataset, recursive=True, max_seconds=max_seconds, query_timeout_seconds=1.0,
                      max_candidate_evaluations=20000, max_prolog_queries=1000000,
                      max_clauses=32, max_literals_per_clause=8, lookahead=lookahead) as learner:
                learner.fit()
                result["fit_stats"] = dict(learner.stats_)
                result["rules"] = [repr(clause) for clause in learner.hypothesis.expressions]
                result["search_trace"] = list(learner.search_trace_)
                rows = []
                for expected, examples in ((True, split["holdout_positive"]), (False, split["holdout_negative"])):
                    for example in examples:
                        rows.append({"example": example, "expected": expected,
                                     "prediction": bool(learner.predict(example))})
                result["predictions"] = rows
                result["metrics"] = classification_metrics(rows)
                result["trace"] = learner.predict_with_trace(split["holdout_positive"][0])
                result["total_stats"] = dict(learner.stats_)
                result["swi_prolog_version_number"] = list(
                    learner.prolog.query("current_prolog_flag(version, Version)"))[0]["Version"]
            result["status"] = "completed"
        except (FOILLearningError, ValueError, OSError) as exc:
            result["status"] = ("budget_exceeded" if isinstance(exc, FOILBudgetExceeded) else
                                "query_error" if isinstance(exc, FOILQueryError) else
                                "search_failed" if isinstance(exc, FOILLearningError) else "runtime_error")
            result["error"] = {"type": type(exc).__name__, "message": str(exc).replace(str(kb), "graph.pl")}
            if learner is not None:
                result["fit_stats"] = dict(learner.stats_)
    result["wall_seconds"] = time.perf_counter() - start
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="JSON report path; parent directories are created.")
    parser.add_argument("--quick", action="store_true", help="Run six fixed cases instead of the full 30-case matrix.")
    parser.add_argument("--max-seconds", type=float, default=12.0, help="Per-case fit time budget (default: 12).")
    parser.add_argument("--lookahead", type=int, choices=(0, 2), default=0,
                        help="0 preserves greedy FOIL; 2 enables bounded zero-gain bridge search.")
    parser.add_argument("--seed-start", type=int, default=100,
                        help="Start of three consecutive seeds; 100 is development and 200 is final evaluation.")
    parser.add_argument("--worker", type=str, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not math.isfinite(args.max_seconds) or args.max_seconds <= 0:
        parser.error("--max-seconds must be a positive finite number.")
    if args.worker:
        case = json.loads(args.worker)
        try:
            result = run_case(case, args.max_seconds, args.lookahead)
        except BaseException as exc:
            result = dict(case, status="runtime_error", error={"type": type(exc).__name__, "message": str(exc)})
        _save(args.output, result)
        return
    cases = [{"case_id": f"{topology}-{nodes}-s{seed}", "topology": topology, "nodes": nodes, "seed": seed}
             for topology in TOPOLOGIES for nodes in (8, 16) for seed in range(args.seed_start, args.seed_start + 3)]
    if args.quick:
        wanted = {f"{topology}-8-s{args.seed_start}" for topology in TOPOLOGIES}
        wanted.add(f"chain-16-s{args.seed_start}")
        cases = [case for case in cases if case["case_id"] in wanted]
    report = {"schema_version": 1, "benchmark": "foil-finite-graph-reachability", "status": "running",
              "source_sha256": {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
                                for name in ("learning/rule_learner.py", "tools/benchmark_foil.py")},
              "environment": environment(), "protocol": {
                  "scope": "Relation-pair holdout within known graphs; not unseen-graph transfer.",
                  "oracle": "Independent Python queue-based BFS with explicit self-loops.",
                  "train_fraction": 0.6, "split": "Seeded, separately stratified positive/negative split.",
                  "topologies": list(TOPOLOGIES), "nodes": [8, 16],
                  "seeds": list(range(args.seed_start, args.seed_start + 3)), "lookahead": args.lookahead,
                  "partition": "development" if args.seed_start == 100 else "final" if args.seed_start == 200 else "custom",
                  "dense_family": "Random DAG with edge probability 0.45 plus explicit self-loops.",
                  "cyclic_family": "Two disjoint directed cycles plus explicit self-loops.",
                  "quick": args.quick, "max_fit_seconds": args.max_seconds,
                  "hard_subprocess_timeout_seconds": args.max_seconds + 13.0,
                  "failure_policy": "Preserve every predeclared case, including errors and budget exhaustion."},
              "cases": []}
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="foil-workers-") as temporary:
        for case in cases:
            destination = Path(temporary) / f"{case['case_id']}.json"
            command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", json.dumps(case),
                       "--output", str(destination), "--max-seconds", str(args.max_seconds),
                       "--lookahead", str(args.lookahead)]
            try:
                process = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True,
                                         encoding="utf-8", errors="replace", timeout=args.max_seconds + 13.0)
                if destination.exists():
                    result = json.loads(destination.read_text(encoding="utf-8"))
                    result["worker_returncode"] = process.returncode
                    if process.stderr.strip():
                        result["worker_stderr"] = process.stderr[-2500:].replace(str(PROJECT), "<project>")
                    fatal_stderr = any(marker in process.stderr for marker in
                                       ("Exception ignored in atexit", "Windows fatal exception", "Fatal Python error", "access violation"))
                    if process.returncode != 0 or fatal_stderr:
                        result["status_before_worker_failure"] = result["status"]
                        result["status"] = "runtime_error"
                else:
                    result = dict(case, status="runtime_error", error={"type": "WorkerFailure",
                                  "returncode": process.returncode, "stderr": process.stderr[-1500:]})
            except subprocess.TimeoutExpired:
                result = dict(case, status="hard_timeout", error={"type": "SubprocessTimeout"})
            report["cases"].append(result)
            print(f"{case['case_id']}: {result['status']}", flush=True)
            _save(args.output, report)
    completed = [case for case in report["cases"] if case["status"] == "completed"]
    rows = [row for case in completed for row in case["predictions"]]
    report["summary"] = {"planned_cases": len(cases), "completed_cases": len(completed),
                         "status_counts": dict(Counter(case["status"] for case in report["cases"])),
                         "exact_match_cases": sum(case["metrics"]["exact_match"] for case in completed),
                         "completed_case_micro_metrics": classification_metrics(rows),
                         "wall_seconds": time.perf_counter() - start}
    report["status"] = "completed"
    _save(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

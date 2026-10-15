"""Boundary regressions for actual Prolog learning, cleanup, and evaluation."""

import json
import math
from pathlib import Path
import subprocess
import sys

import pytest
from click.testing import CliRunner

from evaluate_rules import main
from learning.rule_learner import (FOIL, FOILBudgetExceeded, FOILCleanupError, FOILLearningError, FOILQueryError,
                                   HornClause, Conjunction, Literal, Predicate)
from learning.util import Dataset


def relation_dataset(tmp_path, source="linked(a,b).\nlinked(b,c).", *, positive=None, negative=None):
    kb = tmp_path / "facts.pl"
    kb.write_text(source, encoding="utf-8")
    return Dataset(positive_examples=positive or [{"X": "a", "Y": "b"}],
                   negative_examples=negative or [{"X": "c", "Y": "a"}],
                   kb=str(kb), target="reachable(X,Y)")


def test_unseparable_examples_raise_instead_of_returning_a_positive_clause(tmp_path):
    dataset = relation_dataset(tmp_path, "linked(a,b).\nlinked(c,d).",
                               negative=[{"X": "c", "Y": "d"}])
    with FOIL(dataset) as learner:
        with pytest.raises(FOILLearningError, match="No positive-gain candidate"):
            learner.fit()
        assert not hasattr(learner, "hypothesis")
        assert not list(learner.prolog.query("reachable(a,b)"))
    assert not list(learner.prolog.query("current_predicate(reachable/2)"))


def test_contradictory_labels_are_rejected_before_consult(tmp_path):
    dataset = relation_dataset(tmp_path, negative=[{"X": "a", "Y": "b"}])
    with pytest.raises(ValueError, match="contradictory"):
        with FOIL(dataset):
            pytest.fail("A contradictory dataset must not open a learner.")


@pytest.mark.parametrize("example", [
    {"X": "a"}, {"X": "a", "Y": "b", "Extra": "c"},
    {"X": "a),halt", "Y": "b"}, {"X": "Unbound", "Y": "b"},
    {"X": math.nan, "Y": "b"}, {"X": True, "Y": "b"},
])
def test_unsupported_binding_schema_is_rejected(tmp_path, example):
    dataset = relation_dataset(tmp_path, positive=[example])
    with pytest.raises(ValueError):
        with FOIL(dataset):
            pytest.fail("Unsupported input must be rejected before consult.")


@pytest.mark.parametrize("target", ["reachable(X,X)", "reachable(a,Y)", "reachable(f(X),Y)", "reachable(X,Y),halt"])
def test_target_requires_distinct_named_variables(tmp_path, target):
    dataset = relation_dataset(tmp_path)
    dataset.target = target
    with pytest.raises(ValueError):
        with FOIL(dataset):
            pytest.fail("Unsupported target must be rejected.")


def test_ternary_candidates_cover_mixed_existing_variable_positions(tmp_path):
    dataset = relation_dataset(tmp_path)
    with FOIL(dataset) as learner:
        candidates = list(learner.generate_candidates(
            HornClause(Literal.from_str("reachable(X,Y)")), [Predicate("triple", 3)]))
    representations = {repr(literal) for literal in candidates}
    assert len(candidates) == len(representations) == 20
    assert {"triple(X,V_0,Y)", "triple(Y,X,V_0)", "triple(V_0,Y,X)"} <= representations


def test_prolog_errors_propagate_and_exact_temporary_clause_is_removed(tmp_path):
    dataset = relation_dataset(tmp_path)
    clause = HornClause(Literal.from_str("reachable(X,Y)"),
                        Conjunction([Literal.from_str("missing_relation(X,Y)")]))
    with FOIL(dataset) as learner:
        with pytest.raises(FOILQueryError, match="missing_relation"):
            learner.covers(clause, {"X": "a", "Y": "b"})
        assert not list(learner.prolog.query("reachable(a,b)"))
        learner.fit()
        assert learner.predict({"X": "a", "Y": "b"})


def test_nonterminating_background_query_times_out_and_unloads_knowledge(tmp_path):
    dataset = relation_dataset(tmp_path, "linked(X,Y) :- linked(X,Y).")
    with FOIL(dataset, query_timeout_seconds=0.05, max_seconds=2) as learner:
        with pytest.raises(FOILBudgetExceeded):
            learner.fit()
        assert not hasattr(learner, "hypothesis")
    assert not list(learner.prolog.query("current_predicate(reachable/2)"))
    assert not list(learner.prolog.query("predicate_property(linked(_,_), file(_))"))


def test_candidate_budget_exhaustion_preserves_stats_and_cleanup(tmp_path):
    dataset = relation_dataset(tmp_path)
    with FOIL(dataset, max_candidate_evaluations=1) as learner:
        with pytest.raises(FOILBudgetExceeded, match="max_candidate_evaluations"):
            learner.fit()
        assert learner.stats_["candidate_evaluations"] == 1
        assert learner.stats_["fit_seconds"] > 0
        assert not hasattr(learner, "hypothesis")
    assert not list(learner.prolog.query("current_predicate(reachable/2)"))


def test_query_budget_is_finite_and_cleanup_bypasses_exhausted_budget(tmp_path):
    dataset = relation_dataset(tmp_path)
    with FOIL(dataset, max_prolog_queries=3) as learner:
        with pytest.raises(FOILBudgetExceeded, match="max_prolog_queries"):
            learner.fit()
        assert learner.stats_["prolog_queries"] == 3
    assert not list(learner.prolog.query("predicate_property(linked(_,_), file(_))"))


def test_clause_budget_rejects_partial_disjunction(tmp_path):
    dataset = relation_dataset(tmp_path, "left(a,b).\nright(c,d).",
                               positive=[{"X": "a", "Y": "b"}, {"X": "c", "Y": "d"}],
                               negative=[{"X": "a", "Y": "d"}])
    with FOIL(dataset, max_clauses=1) as learner:
        with pytest.raises(FOILBudgetExceeded, match="max_clauses"):
            learner.fit()
        assert learner.stats_["clauses"] == 1
        assert not list(learner.prolog.query("reachable(a,b)"))


def test_literal_budget_rejects_an_unfinished_specialization(tmp_path):
    dataset = relation_dataset(tmp_path, "parent(a,b).\nparent(b,c).\nparent(d,e).\nparent(e,f).",
                               positive=[{"X": "a", "Y": "c"}, {"X": "d", "Y": "f"}],
                               negative=[{"X": "a", "Y": "x"}, {"X": "a", "Y": "b"}])
    with FOIL(dataset, max_literals_per_clause=1) as learner:
        with pytest.raises(FOILBudgetExceeded, match="max_literals_per_clause"):
            learner.fit()
        assert not hasattr(learner, "hypothesis")


def test_trace_identifies_a_matching_rule_without_claiming_a_proof_tree(tmp_path):
    dataset = relation_dataset(tmp_path)
    with FOIL(dataset) as learner:
        learner.fit()
        trace = learner.predict_with_trace({"X": "a", "Y": "b"})
        assert trace["prediction"] is True
        assert trace["matching_clauses"][0]["bindings"] == {"X": "a", "Y": "b"}
        assert "linked" in trace["matching_clauses"][0]["clause"]
        assert "not a complete" in trace["scope"]
        assert learner.stats_["clauses"] == 1
        assert learner.stats_["literals"] == 1


@pytest.mark.parametrize("ratio", ["0", "1", "-0.1", "nan"])
def test_cli_rejects_invalid_training_fraction(ratio):
    result = CliRunner().invoke(main, ["-a", "foil", "-d", "tests/graph_small.json", "-k", "tests/graph_small.pl",
                                       "-t", "reachable(X,Y)", "-r", "-e", ratio])
    assert result.exit_code != 0
    assert "training fraction" in result.output.lower()


def test_cli_repeated_algorithms_use_identical_split_and_save_predictions(tmp_path):
    output = tmp_path / "evidence.json"
    result = CliRunner().invoke(main, ["-a", "foil", "-a", "foil", "-d", "tests/graph_small.json",
                                       "-k", "tests/graph_small.pl", "-t", "reachable(X,Y)", "-r", "-e", "0.8",
                                       "--output-json", str(output)])
    assert result.exit_code == 0, result.output
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["status"] == "passed"
    first, second = evidence["algorithms"]
    assert first["predictions"] == second["predictions"]
    assert first["rules"] == second["rules"]
    assert len(first["predictions"]) == 71
    assert len(evidence["inputs"]["dataset_sha256"]) == 64
    assert evidence["environment"]["swi_prolog_version_number"] > 0


def test_cli_records_failed_budget_without_successful_classifier(tmp_path):
    output = tmp_path / "failed.json"
    result = CliRunner().invoke(main, ["-a", "foil", "-d", "tests/graph_small.json", "-k", "tests/graph_small.pl",
                                       "-t", "reachable(X,Y)", "-r", "-e", "0.8", "--max-candidates", "1",
                                       "--output-json", str(output)])
    assert result.exit_code != 0
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["status"] == "failed"
    assert evidence["error"]["type"] == "FOILBudgetExceeded"
    assert evidence["algorithms"] == []


@pytest.mark.parametrize("topology,positive_count", [
    ("chain", 36), ("cyclic", 32), ("disconnected", 20), ("self_loop", 8),
])
def test_bfs_oracle_matches_closed_form_reachability_counts(topology, positive_count):
    from tools.benchmark_foil import make_graph, bfs_labels
    edges = make_graph(topology, 8, 100)
    positive, negative = bfs_labels(8, edges)
    assert len(positive) == positive_count
    assert len(positive) + len(negative) == 64
    assert not {tuple(example.values()) for example in positive} & {tuple(example.values()) for example in negative}
    assert all({"X": f"n{node}", "Y": f"n{node}"} in positive for node in range(8))


def cyclic_training_dataset(tmp_path):
    from tools.benchmark_foil import make_graph, bfs_labels, shared_split
    edges = make_graph("cyclic", 8, 100)
    positive, negative = bfs_labels(8, edges)
    split = shared_split(positive, negative, 100)
    source = "\n".join(f"connected(n{left},n{right})." for left, right in edges)
    return relation_dataset(tmp_path, source, positive=split["train_positive"],
                            negative=split["train_negative"]), split


def test_opt_in_lookahead_crosses_zero_gain_bridge_without_changing_default(tmp_path):
    dataset, split = cyclic_training_dataset(tmp_path)
    with FOIL(dataset, recursive=True) as learner:
        with pytest.raises(FOILLearningError, match="No positive-gain candidate"):
            learner.fit()
    with FOIL(dataset, recursive=True, lookahead=2) as learner:
        learner.fit()
        assert learner.search_trace_
        assert learner.search_trace_[0]["event"] == "zero_gain_bridge"
        assert len(learner.search_trace_[0]["literals"]) == 2
        assert all(learner.predict(example) for example in split["holdout_positive"])
        assert not any(learner.predict(example) for example in split["holdout_negative"])


def test_lookahead_uses_the_same_candidate_budget(tmp_path):
    dataset, _ = cyclic_training_dataset(tmp_path)
    with FOIL(dataset, recursive=True, lookahead=2, max_candidate_evaluations=10) as learner:
        with pytest.raises(FOILBudgetExceeded, match="max_candidate_evaluations"):
            learner.fit()
        assert learner.stats_["candidate_evaluations"] == 10
        assert not hasattr(learner, "hypothesis")


def test_lookahead_does_not_run_when_one_literal_already_has_positive_gain(tmp_path):
    dataset = relation_dataset(tmp_path)
    with FOIL(dataset, lookahead=2) as learner:
        learner.fit()
        assert learner.search_trace_ == []
        assert learner.stats_["clauses"] == learner.stats_["literals"] == 1


def test_cleanup_attempts_remaining_operations_and_reports_failures(tmp_path, monkeypatch):
    dataset = relation_dataset(tmp_path)
    calls = []
    with pytest.raises(FOILCleanupError, match="injected cleanup failure"):
        with FOIL(dataset) as learner:
            query = learner.prolog.query

            def fail_one_operation(goal, *args, **kwargs):
                calls.append(goal)
                if "abolish(linked/2)" in goal:
                    raise RuntimeError("injected cleanup failure")
                return query(goal, *args, **kwargs)

            monkeypatch.setattr(learner.prolog, "query", fail_one_operation)
    assert any("unload_file" in goal for goal in calls)
    assert not list(query("predicate_property(linked(_,_), file(_))"))


def test_answer_budget_rejects_excessive_substitutions_instead_of_truncating(tmp_path):
    dataset = relation_dataset(tmp_path, "linked(a,b) :- between(1,100001,_).")
    with FOIL(dataset) as learner:
        with pytest.raises(FOILBudgetExceeded, match="100000-answer"):
            list(learner.extend_example({"X": "a", "Y": "b"}, Literal.from_str("linked(X,Y)")))


def test_empty_recursive_context_then_repeated_full_learning_has_clean_native_exit():
    script = '''
import json
from learning.rule_learner import FOIL
from learning.util import Dataset
with open("tests/graph_small.json", encoding="utf-8") as stream:
    data = json.load(stream)
dataset = Dataset(positive_examples=data["pos"], negative_examples=data["neg"],
                  kb="tests/graph_small.pl", target="reachable(X,Y)")
with FOIL(dataset, recursive=True):
    pass
for _ in range(2):
    with FOIL(dataset, recursive=True) as learner:
        learner.fit()
        assert all(learner.predict(example) for example in data["pos"])
        assert not any(learner.predict(example) for example in data["neg"])
'''
    process = subprocess.run([sys.executable, "-B", "-c", script],
                             cwd=Path(__file__).resolve().parents[2], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=20)
    assert process.returncode == 0, process.stderr
    assert process.stderr == "", process.stderr


@pytest.mark.parametrize("flag,value", [("--max-seconds", "nan"), ("--max-seconds", "inf"),
                                        ("--query-timeout", "nan"), ("--query-timeout", "0")])
def test_cli_rejects_nonfinite_or_zero_time_budgets(flag, value):
    result = CliRunner().invoke(main, ["-a", "foil", "-d", "tests/graph_small.json", "-k", "tests/graph_small.pl",
                                       "-t", "reachable(X,Y)", flag, value])
    assert result.exit_code != 0
    assert "positive finite" in result.output


def test_cli_rejects_contradiction_before_train_holdout_split(tmp_path):
    dataset = relation_dataset(tmp_path)
    source = tmp_path / "contradictory.json"
    output = tmp_path / "failed.json"
    source.write_text(json.dumps({"pos": [{"X": "a", "Y": "b"}, {"X": "b", "Y": "c"}],
                                  "neg": [{"X": "a", "Y": "b"}, {"X": "c", "Y": "a"}]}), encoding="utf-8")
    result = CliRunner().invoke(main, ["-a", "foil", "-d", str(source), "-k", str(dataset.kb),
                                       "-t", "reachable(X,Y)", "-e", "0.5", "--output-json", str(output)])
    assert result.exit_code != 0
    assert "contradictory" in result.output
    assert json.loads(output.read_text())["status"] == "failed"


def test_cli_nonfinite_dataset_value_has_a_valid_failure_report(tmp_path):
    dataset = relation_dataset(tmp_path)
    source = tmp_path / "nonfinite.json"
    output = tmp_path / "failed.json"
    source.write_text('{"pos":[{"X":NaN,"Y":"b"}],"neg":[{"X":"c","Y":"a"}]}', encoding="utf-8")
    result = CliRunner().invoke(main, ["-a", "foil", "-d", str(source), "-k", str(dataset.kb),
                                       "-t", "reachable(X,Y)", "--output-json", str(output)])
    assert result.exit_code != 0
    evidence = json.loads(output.read_text())
    assert evidence["status"] == "failed"
    assert "finite" in evidence["error"]["message"]

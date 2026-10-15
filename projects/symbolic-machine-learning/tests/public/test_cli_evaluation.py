"""Regression checks for the supported, held-out attribute-evaluation commands."""

from copy import deepcopy
from collections import defaultdict
import math
import random

from click.testing import CliRunner
import pytest

import evaluate_attributes as evaluation
from learning.attr_learner import Conjunction, Disjunction
from learning.util import AlgorithmRegistry


def recording_factory(monkeypatch):
    """Record actual rows passed to each learner and predict a known clean rule."""
    training, predicted, order = defaultdict(list), defaultdict(list), []

    class RecordingLearner:
        def __init__(self, name, dataset):
            self.name, self.dataset = name, dataset
            training[name].append(deepcopy(dataset.examples))
            order.append(name)

        def fit(self):
            pass

        def predict_all(self, dataset):
            predicted[self.name].append(deepcopy(dataset.examples))
            return [row["A0"] for row in dataset]

    monkeypatch.setattr(AlgorithmRegistry, "create_algorithm",
                        lambda name, **kwargs: RecordingLearner(name, kwargs["dataset"]))
    monkeypatch.setattr(evaluation, "generate_random_hypothesis",
                        lambda *args, **kwargs: Disjunction([Conjunction({"A0": True})]))
    return training, predicted, order


def feature_rows(rows):
    return {tuple(sorted((name, value) for name, value in row.items() if name != "target")) for row in rows}


def test_noisy_cli_corrupts_training_only_and_reuses_one_disjoint_clean_test_set(monkeypatch):
    training, predicted, _ = recording_factory(monkeypatch)
    result = CliRunner().invoke(evaluation.eval_noisy, [
        "-a", "dtl", "-a", "my-dtl", "-s", "3", "-d", "1", "-c", "1", "--train_split", "0.5",
    ])
    assert result.exit_code == 0, result.output
    assert training["dtl"] == training["my-dtl"]
    assert predicted["dtl"] == predicted["my-dtl"]
    train, test = training["dtl"][0], predicted["dtl"][0]
    assert not feature_rows(train) & feature_rows(test)
    assert len(train) + len(test) == 8
    assert all(row["target"] != row["A0"] for row in train)
    assert all(row["target"] == row["A0"] for row in test)
    assert "4/4 (1.000)" in result.output
    assert "clean held-out test" in result.output
    assert "exact McNemar" in result.output
    assert "Statistically significant" not in result.output


def test_noise_levels_share_the_clean_concept_split_and_nested_training_flips(monkeypatch):
    training, predicted, _ = recording_factory(monkeypatch)
    result = CliRunner().invoke(evaluation.eval_noisy, [
        "-a", "dtl", "-s", "3", "-d", "1", "-c", "0", "-c", "0.5", "-c", "1", "--train_split", "0.5",
    ])
    assert result.exit_code == 0, result.output
    clean, half, full = training["dtl"]
    assert feature_rows(clean) == feature_rows(half) == feature_rows(full)
    assert predicted["dtl"][0] == predicted["dtl"][1] == predicted["dtl"][2]
    half_flips = {i for i, (left, right) in enumerate(zip(clean, half)) if left["target"] != right["target"]}
    full_flips = {i for i, (left, right) in enumerate(zip(clean, full)) if left["target"] != right["target"]}
    assert len(half_flips) == 2
    assert half_flips < full_flips == set(range(4))


def test_cli_case_data_is_independent_of_requested_algorithm_order(monkeypatch):
    training, predicted, order = recording_factory(monkeypatch)
    first = CliRunner().invoke(evaluation.eval_noisy, [
        "-a", "dtl", "-a", "my-dtl", "-s", "3", "-d", "1", "-c", "0.3", "-r", "17",
    ])
    assert first.exit_code == 0, first.output
    expected_training, expected_test = deepcopy(training), deepcopy(predicted)
    training.clear()
    predicted.clear()
    order.clear()
    second = CliRunner().invoke(evaluation.eval_noisy, [
        "-a", "my-dtl", "-a", "dtl", "-s", "3", "-d", "1", "-c", "0.3", "-r", "17",
    ])
    assert second.exit_code == 0, second.output
    assert dict(training) == dict(expected_training)
    assert dict(predicted) == dict(expected_test)


def test_timing_pregenerates_common_data_and_rotates_execution_order(monkeypatch):
    training, _, order = recording_factory(monkeypatch)
    arguments = ["-a", "dtl", "-a", "my-dtl", "-s", "3", "-r", "17", "--runs", "2", "--repeats", "1"]
    result = CliRunner().invoke(evaluation.eval_time, arguments)
    assert result.exit_code == 0, result.output
    assert training["dtl"] == training["my-dtl"]
    assert order[:2] == list(reversed(order[2:]))
    expected_training, expected_order = deepcopy(training), list(order)
    training.clear()
    order.clear()
    reversed_result = CliRunner().invoke(evaluation.eval_time, [
        "-a", "my-dtl", "-a", "dtl", *arguments[4:],
    ])
    assert reversed_result.exit_code == 0, reversed_result.output
    assert dict(training) == dict(expected_training)
    assert order == expected_order
    assert "running 2 iterations" in result.output
    assert "ms +/-" in result.output


@pytest.mark.parametrize("command, arguments", [
    (evaluation.eval_size, ["-s", "3", "-d", "2", "-t", "0.5"]),
    (evaluation.eval_noisy, ["-s", "3", "-d", "2", "-c", "0.3"]),
])
def test_existing_accuracy_command_options_still_execute_real_learners(command, arguments):
    result = CliRunner().invoke(command, ["-a", "dtl", "-a", "my-dtl", *arguments])
    assert result.exit_code == 0, result.output
    assert "dtl(baseline) accuracy:" in result.output
    assert "Accuracy of my-dtl" in result.output
    assert "exact McNemar p=" in result.output


@pytest.mark.parametrize("command, arguments, message", [
    (evaluation.eval_size, ["-a", "dtl", "-s", "3", "-t", "0"], "0"),
    (evaluation.eval_size, ["-a", "dtl", "-s", "3", "-t", "0.99"], "nonempty"),
    (evaluation.eval_noisy, ["-a", "dtl", "-s", "3", "-d", "1", "-c", "1.1"], "1.1"),
    (evaluation.eval_noisy, ["-a", "dtl", "-s", "3", "-d", "4"], "relevant attributes"),
    (evaluation.eval_time, ["-a", "dtl", "--runs", "0"], "0"),
    (evaluation.eval_size, [], "at least one"),
    (evaluation.eval_size, ["-a", "pruned-dtl"], "separate validation"),
])
def test_invalid_cli_inputs_fail_clearly_without_tracebacks(command, arguments, message):
    result = CliRunner().invoke(command, arguments)
    assert result.exit_code != 0
    assert message in result.output
    assert "Traceback" not in result.output


def test_impossible_minterm_request_fails_and_saturated_request_finishes():
    with pytest.raises(ValueError, match="exceeds the 2 distinct"):
        evaluation.generate_random_hypothesis({"A": [False, True]}, max_relevant=1, max_conj=3)
    expression = evaluation.generate_random_hypothesis(
        {"A": [False, True]}, max_relevant=1, max_conj=2, rng=random.Random(2))
    assert expression({"A": False}) and expression({"A": True})


def test_exact_mcnemar_uses_paired_disagreements_instead_of_independent_counts():
    rows = [{"target": True} for _ in range(6)]
    comparison = evaluation.paired_comparison([True] * 5 + [False], [False] * 5 + [True], rows)
    assert comparison == {"baseline_only": 5, "candidate_only": 1,
                          "discordant": 6, "exact_mcnemar_p": 0.21875}
    assert evaluation.paired_comparison([True] * 6, [True] * 6, rows)["exact_mcnemar_p"] == 1


def test_timing_interval_uses_sample_variance_and_reports_missing_replication():
    mean, variance, interval = evaluation.get_mean_var_ci([1, 3])
    assert mean == 2
    assert variance == 2
    assert interval > 1
    assert math.isnan(evaluation.get_mean_var_ci([1])[2])

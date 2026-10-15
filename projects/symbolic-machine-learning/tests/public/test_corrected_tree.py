"""Behavioural contracts for the separate, corrected categorical tree variants."""

from copy import deepcopy
from itertools import product

import pytest

from learning.attr_learner import (
    DecisionTreeLearner,
    DepthLimitedTreeLearner,
    GainDepthTreeLearner,
    GainRatioTreeLearner,
    Leaf,
    MyDecisionTreeLearner,
    Node,
    PrunedDecisionTreeLearner,
    to_logic_expression,
)
from learning.util import AlgorithmRegistry, Dataset


def parity_rows(size):
    return [dict(zip([f"A{i}" for i in range(size)], values), target=bool(sum(values) % 2))
            for values in product((False, True), repeat=size)]


@pytest.mark.parametrize("learner", [DepthLimitedTreeLearner, GainDepthTreeLearner])
@pytest.mark.parametrize("depth", [0, 1, 2])
def test_each_path_obeys_explicit_depth_even_when_immediate_gain_is_zero(learner, depth):
    algorithm = learner(Dataset(parity_rows(4)), max_depth=depth)
    algorithm.fit()
    assert algorithm.tree_metrics()["depth"] == depth
    assert all(len(algorithm.trace(example)["path"]) <= depth for example in parity_rows(4))


@pytest.mark.parametrize("learner", [GainRatioTreeLearner, DepthLimitedTreeLearner, GainDepthTreeLearner])
def test_zero_gain_root_can_still_learn_xor(learner):
    rows = parity_rows(2)
    algorithm = learner(Dataset(rows))
    algorithm.fit()
    assert algorithm.predict_all(Dataset(rows)) == [example["target"] for example in rows]
    assert algorithm.tree_metrics()["depth"] == 2


def test_gain_ratio_and_information_gain_are_separate_ablation_conditions():
    rows = [{"ID": f"person-{i}", "Signal": (i < 4) != (i == 0), "target": i < 4}
            for i in range(8)]
    information_gain = DepthLimitedTreeLearner(Dataset(rows), max_depth=1)
    gain_ratio = GainRatioTreeLearner(Dataset(rows), max_depth=1)
    information_gain.fit()
    gain_ratio.fit()
    assert information_gain.tree_.attr_name == "ID"
    assert gain_ratio.tree_.attr_name == "Signal"


def test_ties_and_rule_order_do_not_depend_on_row_or_dictionary_insertion_order():
    rows = parity_rows(3)
    reordered = [dict(reversed(list(example.items()))) for example in reversed(rows)]
    first = GainDepthTreeLearner(Dataset(rows), max_depth=3)
    second = GainDepthTreeLearner(Dataset(reordered), max_depth=3)
    first.fit()
    second.fit()
    assert repr(first.hypothesis) == repr(second.hypothesis)
    assert first.tree_metrics() == second.tree_metrics()
    assert [first.trace(example) for example in rows] == [second.trace(example) for example in rows]


def test_known_category_missing_from_a_node_has_an_explicit_majority_branch():
    rows = [
        {"A": "red", "B": "small", "target": False},
        {"A": "red", "B": "medium", "target": True},
        {"A": "blue", "B": "large", "target": True},
        {"A": "blue", "B": "small", "target": True},
    ]
    algorithm = GainRatioTreeLearner(Dataset(rows))
    algorithm.fit()
    # red/large was never observed, but both categories were present in training.
    # The red node has a tie, whose documented training majority is True.
    assert algorithm.predict({"A": "red", "B": "large"}) is True
    assert isinstance(algorithm.tree_.branches["red"].branches["large"], Leaf)
    expression = to_logic_expression(algorithm.tree_)
    for a, b in product(("red", "blue"), ("small", "medium", "large")):
        example = {"A": a, "B": b}
        expected = not (a == "red" and b == "small")
        assert algorithm.predict(example) is expected
        assert algorithm.predict_tree(example) is expected
        assert expression(example) is expected
        assert algorithm.trace(example)["prediction"] is expected


@pytest.mark.parametrize("invalid", [
    {},
    {"A": True},
    {"A": True, "B": "unseen"},
    {"A": 1, "B": "left"},
])
def test_prediction_tree_dnf_and_trace_share_the_strict_input_policy(invalid):
    rows = [{"A": a, "B": b, "target": a}
            for a, b in product((False, True), ("left", "right"))]
    algorithm = GainRatioTreeLearner(Dataset(rows))
    algorithm.fit()
    for predict in (algorithm.predict, algorithm.predict_tree, algorithm.hypothesis, algorithm.trace):
        with pytest.raises(ValueError, match="Missing required|Unseen category"):
            predict(invalid)


def test_validation_pruning_removes_a_memorised_exception_without_relabelling_leaves():
    validation = [dict(zip(("A", "B", "C"), values), target=values[0])
                  for values in product((False, True), repeat=3)]
    training = deepcopy(validation)
    training[0]["target"] = True
    snapshots = deepcopy((training, validation))
    algorithm = PrunedDecisionTreeLearner(Dataset(training), validation_dataset=Dataset(validation))
    algorithm.fit()
    assert algorithm.tree_metrics() == {
        "depth": 1, "nodes": 3, "leaves": 2, "positive_rules": 1, "literals": 1,
    }
    assert algorithm.pruning_summary_["validation_correct_before"] == 7
    assert algorithm.pruning_summary_["validation_correct_after"] == 8
    assert algorithm.pruning_summary_["nodes_removed"] > 0
    assert algorithm.predict_all(Dataset(validation)) == [example["target"] for example in validation]
    assert (training, validation) == snapshots
    expression = to_logic_expression(algorithm.tree_)
    assert all(expression(example) == algorithm.predict_tree(example) for example in validation)


def test_validation_labels_do_not_supply_training_majorities():
    training = [{"A": False, "target": True}, {"A": True, "target": True}]
    validation = [{"A": False, "target": False}, {"A": True, "target": False}]
    algorithm = PrunedDecisionTreeLearner(Dataset(training), validation_dataset=Dataset(validation))
    algorithm.fit()
    assert algorithm.tree_.target is True
    assert algorithm.pruning_summary_["validation_correct_after"] == 0


@pytest.mark.parametrize("target", [False, True])
def test_constant_functions_have_readable_rules_and_consistent_metrics(target):
    rows = [{"A": False, "target": target}, {"A": True, "target": target}]
    algorithm = GainRatioTreeLearner(Dataset(rows))
    algorithm.fit()
    assert repr(algorithm.hypothesis) == ("TRUE" if target else "FALSE")
    assert algorithm.tree_metrics() == {
        "depth": 0, "nodes": 1, "leaves": 1,
        "positive_rules": int(target), "literals": 0,
    }
    assert all(algorithm.predict(example) is target and algorithm.predict_tree(example) is target
               for example in rows)


@pytest.mark.parametrize("rows, message", [
    ([{"A": False, "target": 0}], "targets must be booleans"),
    ([{"A": False, "target": True}, {"A": 0, "target": False}], "Ambiguous"),
    ([{"A": float("nan"), "target": True}], "must be finite"),
    ([{"A": False, "target": True}, {"B": True, "target": False}], "identical attributes"),
])
def test_invalid_training_schema_fails_before_exposing_a_fitted_model(rows, message):
    algorithm = GainRatioTreeLearner(Dataset(rows))
    with pytest.raises(ValueError, match=message):
        algorithm.fit()
    assert not hasattr(algorithm, "tree_")
    assert not hasattr(algorithm, "hypothesis")


def test_minimum_leaf_size_prevents_singleton_identifier_memorisation():
    rows = [{"ID": f"id-{i}", "Signal": (i < 4) != (i == 0), "target": i < 4}
            for i in range(8)]
    algorithm = DepthLimitedTreeLearner(Dataset(rows), max_depth=4, min_samples_leaf=2)
    algorithm.fit()
    assert isinstance(algorithm.tree_, Node)
    assert algorithm.tree_.attr_name == "Signal"
    assert algorithm.tree_metrics()["depth"] == 1


def test_separate_models_and_repeated_fits_do_not_share_depth_or_hypothesis_state():
    rows = parity_rows(3)
    first = GainDepthTreeLearner(Dataset(rows), max_depth=3)
    second = GainDepthTreeLearner(Dataset([dict(example, target=False) for example in rows]), max_depth=1)
    first.fit()
    second.fit()
    assert first.tree_metrics()["depth"] == 3
    assert second.tree_metrics()["depth"] == 0
    assert first.predict_all(Dataset(rows)) == [example["target"] for example in rows]
    for example in rows:
        example["target"] = False
    first.fit()
    assert first.tree_metrics()["depth"] == 0
    assert first.predict_all(Dataset(rows)) == [False] * len(rows)


@pytest.mark.parametrize("kwargs", [
    {"max_depth": -1}, {"max_depth": True}, {"max_depth": 1.5},
    {"min_samples_leaf": 0}, {"min_samples_leaf": True},
])
def test_invalid_regularisation_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        GainDepthTreeLearner(Dataset(parity_rows(2)), **kwargs)


def test_pruning_requires_validation_and_a_failed_refit_exposes_no_stale_model():
    rows = parity_rows(2)
    algorithm = PrunedDecisionTreeLearner(Dataset(rows), validation_dataset=Dataset(deepcopy(rows)))
    algorithm.fit()
    algorithm.validation_dataset = None
    with pytest.raises(ValueError, match="requires nonempty"):
        algorithm.fit()
    assert not hasattr(algorithm, "hypothesis")
    assert not hasattr(algorithm, "tree_")
    with pytest.raises(ValueError, match="Call fit"):
        algorithm.predict(rows[0])


def test_registry_preserves_initial_learners_and_exposes_separate_variants():
    assert AlgorithmRegistry.registry["dtl"] is DecisionTreeLearner
    assert AlgorithmRegistry.registry["my-dtl"] is MyDecisionTreeLearner
    for name, learner in (
        ("gain-ratio", GainRatioTreeLearner), ("depth-limited", DepthLimitedTreeLearner),
        ("gain-depth", GainDepthTreeLearner), ("pruned-dtl", PrunedDecisionTreeLearner),
    ):
        assert AlgorithmRegistry.registry[name] is learner

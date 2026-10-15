"""Independent regression checks for the controlled benchmark's data protocol."""

from copy import deepcopy
from itertools import product
import json
import random

import pytest

from tools import benchmark_attributes as benchmark


def feature_key(row):
    return tuple((name, row[name]) for name in sorted(row) if name != "target")


@pytest.mark.parametrize("family", ["conjunction", "sparse_dnf", "xor", "random_truth"])
def test_three_splits_are_disjoint_and_noise_changes_training_labels_only(family):
    clean = benchmark.make_case(family, 6, 0.0, 7)
    noisy = benchmark.make_case(family, 6, 0.3, 7)
    noisier = benchmark.make_case(family, 6, 0.6, 7)
    assert clean["split_indices"] == noisy["split_indices"] == noisier["split_indices"]
    groups = [set(clean["split_indices"][name]) for name in ("train", "validation", "test")]
    assert not groups[0] & groups[1]
    assert not groups[0] & groups[2]
    assert not groups[1] & groups[2]
    assert set.union(*groups) == set(range(64))
    actual_rows = [{feature_key(row) for row in clean[name]} for name in ("train", "validation", "test")]
    assert not actual_rows[0] & actual_rows[1]
    assert not actual_rows[0] & actual_rows[2]
    assert not actual_rows[1] & actual_rows[2]
    assert len(set.union(*actual_rows)) == 64
    assert all({row["target"] for row in clean[name]} == {False, True}
               for name in ("train", "validation", "test"))
    assert clean["validation"] == noisy["validation"] == noisier["validation"]
    assert clean["test"] == noisy["test"] == noisier["test"]
    assert [feature_key(row) for row in clean["train"]] == [feature_key(row) for row in noisy["train"]]
    changed = [index for index, left, right in zip(clean["split_indices"]["train"], clean["train"], noisy["train"])
               if left["target"] != right["target"]]
    assert changed == noisy["flipped_training_indices"]
    assert len(changed) == round(0.3 * len(clean["train"]))
    assert set(changed) <= set(noisier["flipped_training_indices"])
    assert set(changed) <= groups[0]


def test_case_rng_is_independent_of_global_rng_and_algorithm_execution_order():
    case = benchmark.make_case("sparse_dnf", 6, 0.3, 17)
    original_hash = case["data_sha256"]
    models = ("my-dtl", "gain-depth", "pruned-dtl", "majority")
    first = {name: benchmark.run_model(name, case, [1, 3, "unlimited"], 1) for name in models}
    random.seed(12345)
    for _ in range(100):
        random.random()
    recreated = benchmark.make_case("sparse_dnf", 6, 0.3, 17)
    second = {name: benchmark.run_model(name, recreated, [1, 3, "unlimited"], 1)
              for name in reversed(models)}
    assert recreated["data_sha256"] == original_hash
    assert benchmark.digest({name: case[name] for name in ("train", "validation", "test")}) == original_hash
    for name in models:
        for field in ("validation", "test", "test_predictions", "complexity", "selected_depth", "rules"):
            assert first[name][field] == second[name][field]


def test_depth_tuning_uses_validation_and_cannot_follow_test_labels():
    rows = [dict(zip(("A0", "A1"), values), target=values[0])
            for values in product((False, True), repeat=2)]
    case = {"attributes": 2, "domains": {"A0": [False, True], "A1": [False, True]},
            "train": deepcopy(rows), "validation": deepcopy(rows),
            "test": [dict(row, target=not row["target"]) for row in rows]}
    contrary_test = benchmark.run_model("gain-depth-tuned", case, [0, 1], 1)
    case["test"] = deepcopy(rows)
    matching_test = benchmark.run_model("gain-depth-tuned", case, [0, 1], 1)
    # The deeper candidate is perfect on validation and wrong on contrary test.
    # A regression selecting by test accuracy would instead choose depth zero.
    assert contrary_test["selected_depth"] == matching_test["selected_depth"] == 1
    assert contrary_test["rules"] == matching_test["rules"]
    assert contrary_test["validation_search"] == matching_test["validation_search"]
    assert contrary_test["test"]["accuracy"] == 0
    assert matching_test["test"]["accuracy"] == 1


def test_model_construction_and_pruning_never_read_the_test_rows():
    case = benchmark.make_case("xor", 6, 0.15, 3)

    class ForbiddenRows(list):
        def __iter__(self):
            raise AssertionError("Fitting or pruning read held-out test rows")

    case["test"] = ForbiddenRows(case["test"])
    model = benchmark.create_model("pruned-dtl", case)
    model.fit()
    assert model.pruning_summary_["validation_samples"] == len(case["validation"])


def test_each_constructed_model_owns_copies_of_training_and_validation_rows():
    case = benchmark.make_case("xor", 6, 0.15, 3)
    before = deepcopy(case)
    model = benchmark.create_model("pruned-dtl", case)
    model.dataset.examples[0]["target"] = not model.dataset.examples[0]["target"]
    model.validation_dataset.examples[0]["target"] = not model.validation_dataset.examples[0]["target"]
    assert case == before


def test_balanced_accuracy_does_not_reward_majority_only_predictions():
    rows = [{"target": False} for _ in range(9)] + [{"target": True}]
    result = benchmark.metrics([False] * 10, rows)
    assert result["accuracy"] == 0.9
    assert result["balanced_accuracy"] == 0.5


def test_evaluation_requires_the_frozen_adoption_record(tmp_path, monkeypatch):
    plan = json.loads((benchmark.PROJECT / "configs/benchmark-plan.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(benchmark, "PROJECT", tmp_path)
    with pytest.raises(ValueError, match="Freeze configs/adoption.json"):
        benchmark.execute(plan, "evaluation", tmp_path / "result.json", limit=1)
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/adoption.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        benchmark.execute(plan, "evaluation", tmp_path / "result.json", limit=1)
    assert not (tmp_path / "result.json").exists()

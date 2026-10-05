from click.testing import CliRunner
import pytest

from evaluate_rules import main
from learning.rule_learner import FOIL, _FOIL, Conjunction, HornClause, Literal
from learning.util import Dataset


def test_rule_cli_evaluates_before_unloading_its_knowledge_base(monkeypatch):
    events = []
    predict = _FOIL.predict
    abolish = _FOIL.abolish

    def record_predict(learner, example):
        assert "cleanup" not in events
        assert list(learner.prolog.query("predicate_property(connected(_,_), file(_))."))
        events.append("predict")
        return predict(learner, example)

    def record_abolish(learner):
        result = abolish(learner)
        events.append("cleanup")
        return result

    monkeypatch.setattr(_FOIL, "predict", record_predict)
    monkeypatch.setattr(_FOIL, "abolish", record_abolish)
    result = CliRunner().invoke(main, [
        "-a", "foil", "-d", "tests/graph_small.json", "-k", "tests/graph_small.pl",
        "-t", "reachable(X,Y)", "-r", "-e", "0.8",
    ])
    assert result.exit_code == 0, result.output
    assert "Accuracy on positive examples:" in result.output
    assert "Accuracy on negative examples:" in result.output
    assert "12/12 (1.00)" in result.output
    assert "59/59 (1.00)" in result.output
    assert events.count("predict") == 71
    assert events[-1] == "cleanup"
    assert events.count("cleanup") == 1


@pytest.mark.parametrize("recursive", [False, True])
def test_sequential_learners_do_not_reuse_a_previous_knowledge_base(tmp_path, recursive):
    examples = [
        ([('a', 'b'), ('b', 'c')], [('a', 'a'), ('c', 'a')]),
        ([('d', 'e'), ('e', 'f')], [('a', 'b'), ('d', 'd')]),
    ]
    for index, (positive, negative) in enumerate(examples):
        kb = tmp_path / f"knowledge_{index}.pl"
        kb.write_text("\n".join(f"linked({x},{y})." for x, y in positive), encoding="utf-8")
        dataset = Dataset(
            positive_examples=[{"X": x, "Y": y} for x, y in positive],
            negative_examples=[{"X": x, "Y": y} for x, y in negative],
            kb=str(kb), target="reachable(X,Y)",
        )
        with FOIL(dataset, recursive=recursive) as learner:
            learner.fit()
            assert all(learner.predict(example) for example in dataset.positive_examples)
            assert not any(learner.predict(example) for example in dataset.negative_examples)
        assert not list(learner.prolog.query("current_predicate(reachable/2)."))
        assert not list(learner.prolog.query("predicate_property(linked(_,_), file(_))."))


def test_recursive_temporary_clause_does_not_leave_stale_tabled_answers(tmp_path):
    kb = tmp_path / "cyclic.pl"
    kb.write_text("linked(a,a).\nlinked(a,b).\nlinked(b,b).", encoding="utf-8")
    dataset = Dataset(
        positive_examples=[{"X": "a", "Y": "b"}],
        negative_examples=[{"X": "b", "Y": "a"}],
        kb=str(kb), target="reachable(X,Y)",
    )
    clause = HornClause(
        head=Literal.from_str("reachable(X,Y)"),
        body=Conjunction([Literal.from_str("linked(X,Y)")]),
    )
    with FOIL(dataset, recursive=True) as learner:
        assert learner.covers(clause, {"X": "a", "Y": "b"})
        # covers retracts its temporary rule: its cached True must disappear.
        assert not list(learner.prolog.query("reachable(a,b)."))
        learner.fit()
        assert learner.predict({"X": "a", "Y": "b"})
        assert not learner.predict({"X": "b", "Y": "a"})

# Evaluation and Dataset Tools

[English](evaluation-guide.md) | [한국어](evaluation-guide.ko.md) | [Project README](../README.md)

This guide covers the three command-line tools included with the symbolic machine learning project. Run every command from `projects/symbolic-machine-learning`.

## Algorithm registration

Evaluation scripts discover implementations through `AlgorithmRegistry`. Register a new attribute learner with a unique name:

```python
@AlgorithmRegistry.register("my-dtl")
class MyDecisionTreeLearner(DecisionTreeLearner):
    ...
```

A FOIL variant also needs the context-manager wrapper used by the base implementation so that temporary Prolog clauses are cleaned up after use.

## Attribute learner evaluation

View the available subcommands:

```bash
python evaluate_attributes.py --help
```

### Label-noise robustness

```bash
python evaluate_attributes.py eval-noisy \
  -a dtl -a my-dtl \
  -c 0.2 -c 0.5 \
  -s 10 \
  -d 10
```

- `-a` selects registered algorithms; the first is the comparison baseline.
- `-c` is the fraction of target labels to flip during training.
- `-s` is the number of Boolean attributes, producing `2^s` examples.
- `-d` is the maximum number of attributes used by the generated target concept.

The script restores the original labels before evaluation. It does not use a separate hold-out set for this command.

### Performance with less training data

```bash
python evaluate_attributes.py eval-size \
  -a dtl -a my-dtl \
  -t 0.5 -t 0.7 \
  -s 10 \
  -d 10
```

`-t` controls the training fraction. The remaining examples form the evaluation split.

### Training duration

```bash
python evaluate_attributes.py eval-time \
  -a dtl -a my-dtl \
  -s 5 -s 7 -s 10
```

The command reports repeated timing measurements. Compare differences against the reported variation and rerun on a quiet machine for more reliable results.

## Rule learner evaluation

Learn graph reachability with recursive clauses:

```bash
python evaluate_rules.py \
  -a foil \
  -d tests/graph_small.json \
  -k tests/graph_small.pl \
  -t "reachable(X,Y)" \
  -r \
  -e 0.8
```

- `-d` points to positive and negative examples in JSON.
- `-k` points to the Prolog knowledge base.
- `-t` supplies the target literal.
- `-r` allows recursive use of the target predicate.
- `-e` is the training fraction; omit it to train without a hold-out evaluation.

PySwip and SWI-Prolog can retain state or become unstable across repeated runs. Run algorithms or failing tests in separate processes when necessary.

## Graph dataset generation

Generate a random directed graph, a Prolog knowledge base, and labelled reachability examples:

```bash
python generate_graphs.py outputs/graph -n 15 -p 0.046 -r 42
```

This writes `outputs/graph.pl` and `outputs/graph.json`. Create the destination directory before running the command.

The JSON schema is:

```json
{
  "pos": [{"X": "n0", "Y": "n1"}],
  "neg": [{"X": "n1", "Y": "n0"}]
}
```

Keys in each example must match the variables in the target literal.

## Reproducibility checklist

1. Record Python, dependency, and SWI-Prolog versions.
2. Keep the random seed fixed for direct comparisons.
3. Run each algorithm on the same generated dataset.
4. Repeat experiments across several seeds before making general claims.
5. Keep generated outputs outside `tests/` unless they are intentional fixtures.
6. Report failures and regressions alongside improvements.

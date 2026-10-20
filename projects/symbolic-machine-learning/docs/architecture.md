# Architecture and supported workflows

[English](architecture.md) | [한국어](architecture.ko.md) | [Project README](../README.md)

## Two learning paths

The project learns inspectable symbolic hypotheses rather than neural-network weights.

```text
Attribute examples                    Relational examples + Prolog facts
        |                                           |
Python decision-tree learner          FOIL covering and specialisation
        |                                           |
Tree with categorical branches        Horn clauses over allowed predicates
        |                                           |
Disjunction of positive paths         SWI-Prolog query through PySwip
        |                                           |
Boolean prediction                    Relation coverage prediction
```

`learning/util.py` defines datasets, the common learner lifecycle and the algorithm registry. `learning/generate.py` generates Boolean attribute concepts. `learning/attr_learner.py` implements the trees and logical expressions. `learning/rule_learner.py` contains the rule representation, FOIL search and Prolog bridge.

## Decision trees and readable logic

A tree asks a sequence of questions about input features. Each **node** is a question or final **leaf**, and the path from the root to a leaf explains one prediction. **Entropy** measures uncertainty about the labels. **Information gain** measures the reduction in that uncertainty after a split, while **gain ratio** adjusts for how the split distributes examples. The resulting **DNF** expression joins conditions along each positive path with AND, then joins those alternative paths with OR.

`dtl` chooses an attribute by information gain. A unanimous partition becomes a leaf; an exhausted partition falls back to the majority class. Positive root-to-leaf paths are converted into conjunctions, then joined into a disjunction. This conversion makes the learned classification rule inspectable without a separate explanation model.

The initial `my-dtl` combines gain ratio with one shared, post-order growth counter. That counter is preserved in the initial snapshot and explicitly identified as a historical implementation. A path-depth limit instead passes the current depth into each recursive call, so one sibling cannot consume another sibling's depth budget. These are different controls and their results must not be conflated.

Gain ratio and depth control address different questions. Gain ratio changes the selected split; a depth limit changes the capacity of the tree. Their separate experimental conditions help attribute a result to the actual change. An inner validation split selects capacity for a candidate learner. Separate development hold-outs compare the candidate policies. Evaluation uses different, previously untouched seeds, and its final test examples do not choose the policy.

| Registered name | Attribute selection | Capacity control |
| --- | --- | --- |
| `dtl` | Information gain | Initial implementation, unchanged |
| `my-dtl` | Gain ratio | Initial shared growth counter, unchanged |
| `corrected-dtl` | Information gain | Maintained schema checks and deterministic splits, unlimited by default |
| `gain-ratio` | Gain ratio | No depth limit by default |
| `depth-limited` | Information gain | Actual per-path maximum depth |
| `gain-depth` | Gain ratio | Actual per-path maximum depth |
| `pruned-dtl` | Information gain | Bottom-up reduced-error pruning on validation examples |

The maintained variants expose `tree_`, `tree_metrics()` and `trace(example)`. Depth counts root-to-leaf edges, with a root leaf at depth zero. Metrics include depth, nodes, leaves, positive rules and literals. An explicit validation dataset is required for `pruned-dtl`; on equal validation accuracy, pruning keeps the smaller tree. The final test set must never be supplied for pruning.

The controlled benchmark adds a majority-class baseline and a validation-tuned `gain-depth-tuned` condition. These are experimental policies rather than two more registry implementations, giving nine comparison conditions in total.

The maintained variants require every training feature at prediction time and reject unseen feature categories. They accept explicit `None` as a categorical value, Boolean labels and finite scalar categories. A category observed somewhere in training but absent from a particular partition uses that node's learned majority fallback. These contracts belong to the maintained variants; the initial learners remain available for historical comparisons.

## FOIL and Prolog ownership

**FOIL** learns a target relation from examples and known facts. A **predicate** names a relation, such as an edge between graph nodes; a **literal** is a condition using such a relation. A learned **Horn clause** connects those conditions to a conclusion. **Bindings** assign actual input objects to the rule's variables. The learner adds conditions that keep positive examples covered while excluding negative ones; the Prolog runtime checks whether those conditions hold.

FOIL starts with an uncovered positive example set, adds candidate literals to specialise a clause, and repeats the covering loop to learn additional clauses. The Prolog knowledge base supplies the allowed background relations. Learned hypotheses remain ordinary Horn clauses that can be printed and queried.

Prediction belongs inside the learner's context manager:

```python
with FOIL(dataset=dataset, recursive=True) as learner:
    learner.fit()
    result = learner.predict(example)
    print(learner.hypothesis)
```

Leaving the context removes learned target clauses and unloads the consulted knowledge base. Recursive finite-graph targets use SWI-Prolog tabling; cached answers must be invalidated when the learned target changes. A finite relational fixture does not establish termination for arbitrary Prolog programs with unbounded terms.

Target declarations are created lazily before actual coverage queries. Queries collect their bounded answers under SWI-Prolog's standard time limit before yielding bindings to Python, so no open alarm spans a Python generator yield. Temporary clause references stay inside a private Prolog helper and are erased precisely. Cleanup is attempted even after the learning budget is exhausted and has its own query timeout. Verification covers sequential contexts and separate benchmark worker processes, not isolation between concurrently active FOIL contexts.

FOIL search and queries have explicit time, candidate, query, clause and literal budgets. Failure to find an admissible improving condition raises a learning error rather than silently accepting a clause that still covers negative examples. Budget exhaustion, query errors and cleanup errors are distinct failures. The API validates flat target signatures, example keys, supported atoms and numbers, and contradictory labels. It does not sandbox arbitrary Prolog source files.

Default `lookahead=0` preserves greedy search. Optional `lookahead=2` can pair a positive-binding-preserving zero-gain first literal with a second literal yielding positive combined gain when no positive-gain single literal exists. Candidate and query budgets still apply to this bounded search. Both relational CLIs expose it as `--lookahead 2`.

`predict_with_trace(example)` reports the matching learned clauses and input bindings. This is an explanation of which learned rules matched, not a complete internal Prolog proof tree.

## Evaluation boundaries

The historical [`experiment-report.md`](experiment-report.md) and [`evaluation-guide.md`](evaluation-guide.md) are preserved records of the initial commands. In particular, the initial label-noise command restores clean labels and evaluates on examples that were also used during fitting. It cannot establish generalisation to unseen examples. The maintained `eval-noisy` instead defaults to 80% training and 20% clean hold-out, with corruption restricted to training labels. Reproducing the historical protocol requires the initial snapshot.

The maintained experiment separates training, validation and final test examples. Algorithms in the same condition receive the same underlying concept, examples, partition and corrupted training-label positions. Raw predictions, seeds, fitted rules and timings are needed alongside aggregate charts so a reader can inspect an unexpected result.

Runtime measurements describe the executing machine and process. Accuracy on generated Boolean concepts or finite graph relations does not establish accuracy on external tabular datasets, natural language or production data.

## Supported inputs and scope

- Generated categorical attribute examples with Boolean labels.
- Explicit positive and negative relational examples paired with finite Prolog facts.
- Local Python execution with a compatible SWI-Prolog runtime for relational learning.
- Printed logical rules and repeatable command-line experiments.

The coursework `Dataset.from_csv()` and `Dataset.to_csv()` placeholders are outside the supported executable workflow. The repository is not a deployed prediction service, a neural-symbolic model or an integrated language-model agent. Vampire and the separate spacecraft-design Prolog project are not required to run this project's learning workflows.

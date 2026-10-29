# Symbolic Machine Learning

[English](README.md) | [한국어](README.ko.md) | [Portfolio home](../../README.md)

Two learning systems implemented from first principles: a decision-tree learner that turns attribute-value examples into readable logical expressions, and a FOIL-style learner that induces relational Horn clauses from examples and a Prolog knowledge base.

The original development period was **February–May 2025**. The maintained release preserves the initial algorithms and experiments, adds exact path-depth and validation-pruned tree variants, separates model selection from final testing, and gives relational search explicit failure and runtime budgets.

## Understand the task

**Symbolic learning** produces explicit rules that can be read and executed. In the attribute path, each example contains feature values and a true/false label. **DTL**, or decision-tree learning, chooses questions about those features and ends at a predicted label. The same decision can also be written as a logical expression: a conjunction joins conditions with AND, while a disjunction joins alternatives with OR.

The relational path uses examples of whether a relationship holds, together with known background facts. **FOIL** (First Order Inductive Learner) learns rules connecting those facts to the target relationship. For example, graph edges are known facts and reachability is the relationship to learn. **Prolog** executes logical queries, **SWI-Prolog** is its runtime, and **PySwip** connects that runtime to Python. A learned **Horn clause** says that a conclusion holds when its listed conditions hold.

The outputs are a learned tree or rules, predictions for examples, and traces showing which decisions or rules were used. The experiments ask whether the learned rules generalise to examples withheld from training, how complex those rules become, and whether learning finishes within its resource limits.

## What this project demonstrates

- Entropy, information gain, gain ratio and symbolic tree-to-logic conversion.
- Capacity control through exact root-to-leaf depth and reduced-error pruning.
- FOIL candidate generation, relational example extension, rule induction and recursive finite-graph inference.
- Paired experimental inputs, held-out evaluation and inspectable prediction traces.
- Runtime discovery, source integrity checks and preserved initial evidence.

The original coursework supplied the code skeleton, dataset generation utilities, evaluation scaffolding and public tests. The implemented learning logic and subsequent maintenance are distinguished from those supplied materials. Original assignment and lecture PDFs remain under [`references/`](references/).

## Learning approaches

**Information gain** measures how much a split reduces uncertainty about the label; **gain ratio** adjusts it by how broadly the attribute partitions the data. A **depth limit** caps the number of steps from the root to a final leaf. **Pruning** removes branches after training when validation data supports a simpler tree. These are separate choices about how to split data and how much detail the tree may retain.

| Name | Split criterion | Growth control | Purpose |
| --- | --- | --- | --- |
| `dtl` | Information gain | Initial implementation | Preserved comparison baseline |
| `my-dtl` | Gain ratio | Initial shared post-order counter | Preserved historical variant |
| `corrected-dtl` | Information gain | Unlimited by default | Maintained deterministic, schema-validated baseline |
| `gain-ratio` | Gain ratio | Unlimited by default | Isolate split-criterion effects |
| `depth-limited` | Information gain | Exact path depth | Isolate depth-control effects |
| `gain-depth` | Gain ratio | Exact path depth | Combine the two changes |
| `pruned-dtl` | Information gain | Validation-based reduced-error pruning | Test complexity reduction after fitting |
| `foil` | FOIL information gain | Explicit search and query budgets | Learn relational Horn clauses |

`my-dtl` retains the initial shared-counter behaviour. It is not silently relabelled as a correct per-path depth limiter. The corrected variants are separately registered so readers can compare the actual mechanisms. The initial [`experiment-report.md`](docs/experiment-report.md) is an unchanged historical record; phrases such as "current implementation" in that report refer to its initial snapshot.

## Quick start

Use Python 3.12 with **SWI-Prolog 9.2.9 x64 on Windows** or the **9.0.4 system package on Ubuntu 24.04**. SWI-Prolog must be discoverable by PySwip; it is not installed by `pip`. The source ZIP includes a pinned PySwip package with a native argument-lifetime fix; Git is not required to install it. The [reproduction guide](docs/reproduce.md) links the exact Windows installer and its hash.

```bash
cd projects/symbolic-machine-learning
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/WSL or `.\.venv\Scripts\Activate.ps1` on Windows PowerShell, then run:

```bash
python -m pip install -r requirements.lock.txt
python tools/run_checks.py --output-dir outputs/verification
```

The lock file installs local PySwip **0.3.3+argv1**, based on commit `c07e8083c6a58eb7de99bb26c8dc89a0c215f52c`, and records the resolved Python dependency versions. The [documented patch](vendor/pyswip/PATCH.md) keeps initialization arguments alive until normal native shutdown; the learning algorithms and recorded benchmark values are unchanged. The environment checker executes an actual isolated Prolog query and returns a nonzero status with hints if the native runtime cannot load. See [installation and reproduction](docs/reproduce.md) for Linux and Windows discovery details.

The guarded check command verifies the release, diagnoses the environment, runs pytest and both fixed learning smoke workflows, and checks native process shutdown. Choose a new or empty output directory; existing evidence is not overwritten.

## Run the workflows

The original command interfaces remain available:

```bash
python evaluate_attributes.py eval-size -a dtl -a my-dtl -s 4 -d 2 -t 0.75
python evaluate_rules.py -a foil -d tests/graph_small.json -k tests/graph_small.pl -t "reachable(X,Y)" -r -e 0.8
```

The maintained attribute CLI corrects the initial evaluation protocol: `eval-noisy` now uses a clean independent hold-out, training-only label flips and a shared concept/split across algorithms and noise levels. `eval-time` shares pre-generated inputs and rotates execution order. The initial report's commands reproduce the old protocol only from the preserved snapshot, not from this maintained CLI. `pruned-dtl` requires a separate validation set and is supported by the controlled benchmark rather than these simple attribute commands.

A **seed** is the starting value used to reproduce random data generation and splitting. Repeating the comparison with different seeds checks whether a result depends on one favourable draw. **Training** examples fit the rules; **validation** examples select settings such as depth; **held-out** examples are kept aside from that fitting. Development hold-outs select the candidate policy, then distinct final evaluation cases measure that fixed choice without selecting it again.

The maintained comparison has a checked-in plan and separate development and evaluation phases:

```bash
python tools/benchmark_attributes.py --plan configs/benchmark-plan.json --phase development --output outputs/attribute-development.json
python tools/benchmark_attributes.py --plan configs/benchmark-plan.json --phase evaluation --output outputs/attribute-evaluation.json
python tools/benchmark_foil.py --lookahead 2 --seed-start 200 --output outputs/foil-final-lookahead.json
```

Algorithms receive the same generated concept, examples, split and training-label corruption within a condition. Validation selects capacity before final test predictions are inspected. Reports retain seeds, predictions, model complexity and timings; aggregate accuracy alone is insufficient to explain a trade-off.

The benchmark compares nine conditions: the seven registered tree learners plus a majority-class predictor and `gain-depth-tuned`, which chooses a depth on the inner validation split. Candidate policies are selected on separate outer development hold-outs and frozen before running the distinct evaluation seeds.

## Inspect predictions

**DNF** (disjunctive normal form) writes the positive decision paths as OR-connected groups of AND conditions. A **node** is a decision point or final leaf; counting nodes and path depth helps compare model complexity. A prediction trace follows the conditions used for one input, making the reported rule inspectable.

Open [`demo/index.html`](demo/index.html) directly in a browser for the offline interactive explanation. Change A, B and C, follow the exported learned tree and compare its result with the exported DNF. The model was trained on all eight inputs for explanation; the demo is not a held-out score. Rebuild both language versions with `python tools/build_demo.py`.

Maintained tree variants expose `tree_`, `tree_metrics()` and `trace(example)`. Depth counts edges, so a root leaf has depth zero. Metrics include nodes, leaves, positive rules and literals. The path trace identifies the conditions used for one prediction. Features missing at prediction time and categories never observed during training raise explicit errors in these variants.

FOIL prediction belongs inside its context manager, before its knowledge base and target are removed:

```python
with FOIL(dataset=dataset, recursive=True) as learner:
    learner.fit()
    print(learner.hypothesis)
    print(learner.predict_with_trace(example))
```

The trace identifies matching learned clauses and input bindings; it is not a complete Prolog proof tree. Candidate exhaustion, budget exhaustion, query failures and cleanup failures are distinguishable. See [architecture and supported scope](docs/architecture.md).

## Results and initial records

**Balanced accuracy** gives equal weight to correctly recognising positive and negative examples, so a more common label does not dominate the result. **pp** means percentage points, the arithmetic difference between two percentages. The **frozen representative** is the policy selected before the final test, not a claim that it has the highest score in every later comparison.

Tree/DNF agreement checks whether two ways of executing the same learned rule return identical predictions; it does not measure correctness against unseen labels. **FOIL completion** counts whole cases that finish within the search budget and should be read separately from the prediction accuracy of completed cases. Regression-test counts check software behavior rather than model accuracy.

<span id="verified-smoke-experiments-2026-10-05"></span>

| Maintained evaluation | Result |
| --- | --- |
| Frozen representative balanced accuracy | **76.25%**, initial `my-dtl` **64.08%**, **+12.17 pp** |
| Nine comparison conditions | **240 cases**, **2,160 model evaluations**, zero model failures |
| Highest final balanced accuracy | `pruned-dtl` **77.81%**; kept available without changing the frozen representative |
| Equivalent DNF/tree prediction | **12,288/12,288 identical**, median case-level batch-time reduction **68.31%** |
| FOIL learning completed | Greedy **20/30** cases, optional two-literal look-ahead **26/30** |
| Source ZIP verification | **5/5 stages** on Windows and Linux; Windows **151 passed, two skipped**, Linux **153 passed** |

Read the [complete maintained results](docs/results.md) for all nine conditions, complexity and tuning costs, seed-level intervals and FOIL budget failures. The representative was fixed from development data before final evaluation. The initial experiment's lower training time is not reused as a speed claim for the new model.

![All nine held-out balanced-accuracy comparison conditions](figures/en/symbolic-accuracy.svg)

The historical coursework reported **44–80% lower training time** in three configurations and **+19.1 percentage points** in one extreme-noise setting, with substantial accuracy regressions elsewhere. Those measurements used the initial shared-counter variant. The noise evaluation included examples used for training, so these figures are not presented as new held-out generalisation results.

The initial public smoke verification on **2026-10-05** passed 30 tests with Python 3.12.7 and SWI-Prolog 9.2.9. It also completed a 4/4 attribute hold-out example and a graph hold-out with 12/12 positive and 59/59 negative predictions. This is preserved prior verification, separate from the maintained release's new experiments.

The original code, tests, recorded experiments and data are preserved as 27 byte-identical files in [`legacy/initial-aa947038.zip`](legacy/initial-aa947038.zip), pinned to Git commit `aa947038f923e98ec0bf16457745d538284ef45c`. The three original reference PDFs remain unchanged under [`references/`](references/) instead of being duplicated in that snapshot. [`legacy/initial-provenance.json`](legacy/initial-provenance.json) inventories all 30 initial files and identifies the shared reference hashes. The release manifest checks the snapshot and the shared PDFs. Historical reports and reference files also remain unchanged in the maintained tree.

## Repository map

```text
symbolic-machine-learning/
├── learning/               # Initial learners and maintained variants
├── tests/                  # Regression checks and graph fixtures
├── configs/                # Checked-in experimental plan
├── tools/                  # Benchmarks, environment and release checks
├── docs/                   # English-first documentation and Korean counterparts
├── legacy/                 # Pinned initial project snapshot
├── references/             # Original assignment and lecture material
├── requirements.lock.txt   # Resolved Python package versions
└── release-manifest.json   # Declared payload hashes and source provenance
```

## Documentation and limits

- [Architecture and supported workflows](docs/architecture.md)
- [Maintained results and all comparison conditions](docs/results.md)
- [Executed environments and native lifecycle verification](docs/validation.md)
- [Installation, experiments and release verification](docs/reproduce.md)
- [Initial experiment report](docs/experiment-report.md)
- [Initial evaluation guide](docs/evaluation-guide.md)

The executable scope is generated categorical examples and finite relational datasets with Prolog facts. The unused coursework CSV import/export placeholders remain outside that scope. Synthetic results do not establish performance on external or production datasets. Timings depend on the execution environment. Tabling and budgets support controlled finite-graph experiments; they do not sandbox arbitrary Prolog source or prove termination of every program.

The Ubuntu GitHub Actions workflow provides an execution path for the environment diagnostic, release verifier and regression suite. Its presence alone does not establish that a remote CI run passed. The repository does not declare a new licence for the code or supplied course materials.

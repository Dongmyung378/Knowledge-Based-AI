# Symbolic Machine Learning

[English](README.md) | [한국어](README.ko.md) | [Portfolio home](../../README.md)

## Overview

This project implements two explainable learning systems from first principles:

1. A decision-tree learner for attribute-value data, including conversion from a tree to a disjunction of logical conjunctions.
2. A FOIL-style inductive logic programming learner that induces Horn clauses from positive examples, negative examples, and a Prolog knowledge base.

It also includes dataset generators, command-line evaluation tools, graph fixtures, and public tests.

## Technical highlights

### Decision-tree learning

- Handles unanimous targets, plurality fallbacks, empty partitions, and exhausted attributes.
- Computes binary entropy and information gain for attribute selection.
- Converts positive root-to-leaf paths into human-readable logical expressions.
- Registers algorithms by name so evaluation scripts can compare implementations consistently.

### Improved `my-dtl` variant

- Uses gain ratio to normalise information gain by split information.
- Limits tree depth using the size of the training set.
- Trades some predictive accuracy for lower training time and improved behaviour in selected high-noise settings.
- Documents both successful and unsuccessful experimental outcomes in the [experiment report](docs/experiment-report.md).

### FOIL-style rule learning

- Extracts usable predicates from a Prolog knowledge base.
- Generates candidate literals with consistent variable naming.
- Extends examples through Prolog substitutions and scores candidates with FOIL information gain.
- Learns Horn clauses through separate covering and specialisation loops.
- Supports recursive target relations such as graph reachability.
- Unloads the consulted knowledge base and learned target predicates when a learner closes, preventing Prolog state from leaking across runs.

## Architecture

```text
symbolic-machine-learning/
├── learning/
│   ├── attr_learner.py   # DTL, my-dtl, entropy, and logic conversion
│   ├── rule_learner.py   # FOIL, Horn-clause types, and Prolog bridge
│   ├── generate.py       # Synthetic attribute dataset generator
│   └── util.py           # Dataset, algorithm interface, and registry
├── tests/
│   ├── public/           # Attribute and rule learner tests
│   └── graph*            # Reachability datasets and Prolog facts
├── evaluate_attributes.py
├── evaluate_rules.py
├── generate_graphs.py
├── docs/
│   ├── experiment-report.md
│   └── evaluation-guide.md
└── references/           # Original brief and lecture material
```

## Setup

### Prerequisites

- Python 3.12 recommended (the validation environment used 3.12.7)
- SWI-Prolog available on `PATH`
- Git, needed by the pinned PySwip source dependency
- A C/C++ toolchain only if required by your local dependency installation

```bash
cd projects/symbolic-machine-learning
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

PySwip must be able to locate the installed SWI-Prolog runtime. For an extracted
Windows runtime without installer registration, set `SWI_HOME_DIR` to its root and
`LIBSWIPL_PATH` to the absolute path of `bin/libswipl.dll`, and add its `bin` directory
to the current process's `PATH` before running Python. These paths are machine-local;
do not commit them.

### Ubuntu or Debian system runtime

Install SWI-Prolog and Python's environment support, then run the standard `venv`
setup above from `projects/symbolic-machine-learning`:

```bash
sudo apt-get update
sudo apt-get install -y swi-prolog python3-venv
python3 --version
swipl --version
```

Use a Python 3.12 environment for the validated version set below; older system
Python versions may resolve different dependency releases. The Conda option supplies
the specific Python and SWI-Prolog versions together.

### Self-contained Conda setup for Linux or WSL

This alternative keeps Python and SWI-Prolog together in the ignored `.venv` directory:

```bash
conda create -p .venv -c conda-forge python=3.12 swi-prolog=9.2.9 pip -y
conda activate ./.venv
python -m pip install -r requirements.txt
```

## Tests

```bash
python -m pytest
```

Run only the decision-tree tests:

```bash
python -m pytest tests/public/test_attr_learner.py
```

Run only the rule-learning tests:

```bash
python -m pytest tests/public/test_rule_learner.py
```

The regression suite checks learning and prediction before FOIL cleanup, and loading
different knowledge bases in the same process. Keep prediction inside `with FOIL(...)`
when using the learner directly; leaving the context removes its learned target and
unloads the knowledge base. Record Python, PySwip and SWI-Prolog versions if a runtime
problem occurs.

## Reproduce the evaluations

Start from this directory after installing the dependencies. A small decision-tree
experiment generates 16 Boolean examples, trains both learners on 75%, and reports
accuracy on the remaining examples:

```bash
python evaluate_attributes.py eval-size -a dtl -a my-dtl -s 4 -d 2 -t 0.75
```

The seed defaults to 42. Inputs are generated in memory, so no private dataset or
download is required. The rule-learning command below uses the tracked JSON examples
and Prolog facts, prints its learned clauses, then reports positive and negative
hold-out accuracy before cleaning up the Prolog state. These commands write results
to the terminal; they do not save a model or alter the input fixtures.

Compare decision-tree variants on noisy data:

```bash
python evaluate_attributes.py eval-noisy -a dtl -a my-dtl -c 0.3 -c 0.5 -c 0.7 -s 10 -d 10
```

Compare training time:

```bash
python evaluate_attributes.py eval-time -a dtl -a my-dtl -s 5 -s 7 -s 10
```

Learn a recursive reachability relation:

```bash
python evaluate_rules.py -a foil -d tests/graph_small.json -k tests/graph_small.pl -t "reachable(X,Y)" -r -e 0.8
```

See the [evaluation guide](docs/evaluation-guide.md) for all workflows.

### Verified smoke experiments (2026-10-05)

The full public suite passed **30 tests** on Windows with Python 3.12.7, SWI-Prolog
9.2.9 and PySwip 0.3.3 at commit
`c07e8083c6a58eb7de99bb26c8dc89a0c215f52c`. The installed dependency versions were
pytest 9.1.1, SciPy 1.18.1, Click 8.5.0, NetworkX 3.7, tabulate 0.10.0 and NumPy 2.5.3.

- The small attribute command above finished with `dtl` and `my-dtl` each correctly
  classifying 4/4 hold-out examples.
- The recursive graph command above finished with 12/12 positive and 59/59 negative
  hold-out examples classified correctly, using its default seed of 42.
- Regressions cover constant positive/negative trees, mixed tree branches, FOIL
  evaluation before cleanup, sequential knowledge bases and stale table removal.

Recursive targets use [SWI-Prolog tabling](https://www.swi-prolog.org/pldoc/man?section=tabling)
to avoid revisiting graph cycles. Target tables are cleared when learned clauses
change and removed during cleanup. This covers the finite relational graph fixtures;
it does not promise termination for arbitrary Prolog programs with unbounded terms.
The Linux/WSL installation instructions are provided as alternatives and were not
executed in this Windows validation. Vampire is a separate optional reasoning workflow
and was not part of these tests. Historical performance experiments were not rerun.

The supported dataset paths are generated attribute examples and JSON graph examples
paired with Prolog facts. `Dataset.from_csv()` and `Dataset.to_csv()` remain unused
coursework placeholders; CSV import/export is outside the runnable evaluation scope.

## Results and limitations

The recorded experiments show that `my-dtl` trains substantially faster than the baseline and is more robust in one extreme-noise configuration. It also performs worse in several low-noise and limited-data settings. These are historical coursework measurements and were not rerun as part of the portfolio reorganisation. Full tables, commands, interpretation, and threats to validity are in the [experiment report](docs/experiment-report.md).

`requirements.txt` pins PySwip to the tested commit. Other dependencies remain
unversioned; use the version set recorded above when comparing this smoke result,
and record your resolved versions for new experiments.

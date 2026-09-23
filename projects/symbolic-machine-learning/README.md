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

- Python 3
- SWI-Prolog available on `PATH`
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

PySwip must be able to locate the installed SWI-Prolog runtime.

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

The PySwip bridge can retain Prolog state between tests on some systems. If a rule-learning test is unstable, run it in isolation.

## Reproduce the evaluations

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

## Results and limitations

The recorded experiments show that `my-dtl` trains substantially faster than the baseline and is more robust in one extreme-noise configuration. It also performs worse in several low-noise and limited-data settings. These are historical coursework measurements and were not rerun as part of the portfolio reorganisation. Full tables, commands, interpretation, and threats to validity are in the [experiment report](docs/experiment-report.md).

The current `requirements.txt` installs PySwip from its upstream default branch. For a fully reproducible archival environment, replace that reference with a vetted release or commit and record the SWI-Prolog version.

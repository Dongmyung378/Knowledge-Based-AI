# COMP24412 - Knowledge-Based Artificial Intelligence

Coursework for COMP24412 (2024-25). The repository contains three labs covering first-order reasoning, Prolog programming, and symbolic machine learning.

## Contents

| Directory | Topic | Main work |
| --- | --- | --- |
| `comp24412_h18609dp-lab1` | Automated reasoning | TPTP problem files and proof/model configurations for Vampire |
| `comp24412_h18609dp-lab2` | Logic programming | Prolog knowledge bases and a constraint-based spacecraft component design checker |
| `comp24412_h18609dp-lab3` | Symbolic machine learning | Decision-tree and FOIL-style rule learners, tests, and evaluation scripts |

## Lab 1 - Automated reasoning

`comp24412_h18609dp-lab1` contains first-order logic encodings in TPTP format. The main examples are:

- `maps.p` - relations and proofs concerning maps
- `sets.p` and `sets.cnf` - set-theory encodings and their clausified form
- `pets.p` - a logic-puzzle encoding

The accompanying `.json`, `.tex`, `.pdf`, and `.tff` files record proof specifications, derivations, and model-finding variants.

The `run_vampire` wrapper starts Vampire with presets for given-clause, discount, or Otter-style saturation. It expects the executable at `/opt/vampire/vampire`, so adjust `VAMPIRE_BIN` in the script if Vampire is installed elsewhere.

```bash
cd comp24412_h18609dp-lab1
./run_vampire --preset gc maps.p
```

## Lab 2 - Logic programming

`comp24412_h18609dp-lab2` is designed to be loaded in SWI-Prolog.

- `database.pl` defines spacecraft components and compatible component pairs.
- `electrical.pl` builds on that database with predicates for checking nested shield designs, counting shields, and ensuring each required component is used once.
- `warmup.pl` and `backup.pl` are smaller supporting exercises.

For example:

```prolog
?- [electrical].
?- safe_design([part(radar), part(cpu)]).
true.
```

## Lab 3 - Symbolic machine learning

The third lab provides two learning approaches in `comp24412_h18609dp-lab3/learning`:

- `attr_learner.py` implements a decision-tree learner (`dtl`) and an alternative `my-dtl` learner using gain ratio and a depth limit.
- `rule_learner.py` implements a FOIL-style inductive logic programming learner (`foil`) over a Prolog knowledge base.
- `generate.py` creates attribute-based datasets.

`Exercise3.md` documents the `my-dtl` design and its measured trade-offs: substantially shorter training times and improved performance on one high-noise setting, with weaker results for some low-noise and limited-training-data cases.

### Setup

Lab 3 requires Python and SWI-Prolog. Create an environment, install the Python dependencies, then run commands from the lab directory.

```bash
cd comp24412_h18609dp-lab3
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

`pyswip` also needs a working SWI-Prolog installation that Python can locate.

### Tests and experiments

Run the public tests:

```bash
cd comp24412_h18609dp-lab3
pytest
```

Compare the supplied decision-tree learners on noisy synthetic data:

```bash
python evaluate_attributes.py eval-noisy -a dtl -a my-dtl -c 0.3 -c 0.5 -c 0.7 -s 10 -d 10
```

Evaluate the rule learner against the included graph knowledge base:

```bash
python evaluate_rules.py -a foil -d tests/graph_small.json -k tests/graph_small.pl -t "reachable(X,Y)" -r -e 0.8
```

Use `--help` with `evaluate_attributes.py`, `evaluate_rules.py`, or `generate_graphs.py` to view the available options.

## Notes

The original per-lab READMEs retain the course submission guidance supplied with the lab materials. This top-level document is intended as a quick map of the completed repository and how to run its code.

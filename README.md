# Knowledge-Based Artificial Intelligence Portfolio

[English](README.md) | [한국어](README.ko.md)

A curated portfolio of three projects from COMP24412, covering automated theorem proving, logic programming, and symbolic machine learning. The repository is organised around the work itself: each project explains the problem, implementation, reproducible workflow, and technical trade-offs.

## Portfolio at a glance

| Project | Focus | What it demonstrates | Core technologies |
| --- | --- | --- | --- |
| [Automated Reasoning](projects/automated-reasoning/README.md) | First-order logic and proof search | TPTP modelling, proof generation, model finding, and proof artefact inspection | Vampire, TPTP, Python, LaTeX |
| [Logic Programming](projects/logic-programming/README.md) | Declarative constraint modelling | Recursive Prolog predicates for validating nested spacecraft component designs | SWI-Prolog |
| [Symbolic Machine Learning](projects/symbolic-machine-learning/README.md) | Explainable concept learning | Decision trees, gain ratio, FOIL-style rule induction, recursive relations, and evaluation tooling | Python, PySwip, SWI-Prolog, pytest |

## Selected highlights

- Encoded first-order problems and inspected both proofs and finite-model variants.
- Built recursive Prolog predicates that validate compatibility, nested shields, component use, and structural constraints.
- Implemented a decision-tree learner and converted learned trees into readable logical expressions.
- Implemented a FOIL-style inductive logic programming learner backed by a Prolog knowledge base.
- Developed `my-dtl`, a gain-ratio and depth-limited decision-tree variant. Recorded coursework experiments report 44-80% lower training time and a 19.1 percentage-point gain in one high-noise setting, alongside documented regressions in lower-noise and limited-data cases.

## Repository map

```text
.
├── README.md / README.ko.md
└── projects/
    ├── automated-reasoning/
    │   ├── problems/       # TPTP and clausified problem definitions
    │   ├── artifacts/      # Proof specifications and rendered derivations
    │   ├── tools/          # Vampire wrapper and proof-to-LaTeX helper
    │   └── references/     # Original coursework briefs
    ├── logic-programming/
    │   ├── src/            # Prolog knowledge bases and predicates
    │   └── references/     # Original coursework brief
    └── symbolic-machine-learning/
        ├── learning/       # Decision-tree and FOIL implementations
        ├── tests/          # Public tests and graph fixtures
        ├── docs/           # Experiment report and evaluation guide
        └── references/     # Coursework and lecture material
```

## Quick start

### 1. Automated reasoning

Install [Vampire](https://vprover.github.io/) and update `VAMPIRE_BIN` in `tools/run_vampire` if the executable is not located at `/opt/vampire/vampire`.

```bash
cd projects/automated-reasoning
./tools/run_vampire --preset gc problems/maps.p
```

### 2. Logic programming

Install SWI-Prolog, then load the completed design checker.

```bash
cd projects/logic-programming
swipl -s src/electrical.pl
```

```prolog
?- safe_design([part(radar), part(cpu)]).
true.
```

### 3. Symbolic machine learning

Python 3 and SWI-Prolog are required. The following Conda workflow installs both in one local environment:

```bash
cd projects/symbolic-machine-learning
conda create -p .venv -c conda-forge python=3.12 swi-prolog=9.2.9 pip -y
conda activate ./.venv
python -m pip install -r requirements.txt
python -m pytest
```

See the project README for a standard Python `venv` setup when SWI-Prolog is already installed on the system.

## Documentation

Every Markdown document is written in English by default and links to a Korean counterpart. Start with an individual project README for technical details, or read the symbolic learning [experiment report](projects/symbolic-machine-learning/docs/experiment-report.md) for measured results and limitations.

## Context

This repository began as coursework for the University of Manchester's COMP24412 Knowledge-Based Artificial Intelligence unit (2024-25). Original assignment and lecture PDFs are retained under each project's `references/` directory for provenance. Generated caches, LaTeX auxiliary files, obsolete course synchronisation/submission scripts, and an incomplete backup were removed from the portfolio view.

The repository does not currently declare a licence. Please treat the code and supplied course material accordingly.

# Knowledge-Based Artificial Intelligence Portfolio

[English](README.md) | [한국어](README.ko.md)

A curated portfolio of three projects from COMP24412, covering automated theorem proving, logic programming, and symbolic machine learning. The repository is organised around the work itself: each project explains the problem, implementation, reproducible workflow, and technical trade-offs.

Here, **knowledge-based AI** represents facts and rules explicitly so a reader can inspect the reasoning. Automated reasoning asks whether a conclusion follows from given facts. Logic programming uses rules to check a proposed design. Symbolic machine learning reverses that direction: it starts from labelled examples and learns a decision tree or rules that can explain new predictions.

For the portfolio's learning project, start with **Symbolic Machine Learning** below. It accepts generated attribute examples or known graph relationships and produces readable classification rules, prediction traces and evaluation reports. The other two projects provide related logic background and have their own execution paths.

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
- Preserved the initial `dtl` and shared-counter `my-dtl`, then added independently comparable gain-ratio, exact-depth and validation-pruned variants with held-out evaluation and inspectable prediction traces. The historical experiment tables remain separate from the maintained measurements.

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
        ├── tools/          # Paired benchmarks and environment/release checks
        ├── docs/           # Maintained results and preserved initial reports
        ├── legacy/         # Pinned initial source and experiment snapshot
        └── references/     # Coursework and lecture material
```

## Quick start

### 1. Automated reasoning

Install [Vampire](https://vprover.github.io/) and update `VAMPIRE_BIN` in `tools/run_vampire` if the executable is not located at `/opt/vampire/vampire`.

```bash
cd projects/automated-reasoning
sh ./tools/run_vampire --preset gc problems/maps.p
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

Use Python 3.12 and the documented native runtime: SWI-Prolog 9.2.9 x64 on Windows or the 9.0.4 system package on Ubuntu 24.04. Install SWI-Prolog separately, create a Python environment and run the symbolic-learning checks:

```bash
cd projects/symbolic-machine-learning
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python tools/run_checks.py --output-dir outputs/verification
```

On Windows PowerShell activate with `.\.venv\Scripts\Activate.ps1`. See the [project README](projects/symbolic-machine-learning/README.md) for native runtime discovery and [reproduction guide](projects/symbolic-machine-learning/docs/reproduce.md) for experiments and source integrity checks.

The initial 2026-10-05 smoke verification passed 30 tests and remains a historical record. The maintained release was verified from an actual extracted source ZIP in fresh environments on the same PC: Windows passed 151 tests with two permission-related symlink skips, and Linux/WSL passed all 153 tests. Both environments passed all five guarded stages, including the actual Prolog query and native process shutdown. See the [executed environments and evidence](projects/symbolic-machine-learning/docs/validation.md). Vampire is needed only for the separate automated-reasoning workflow.

## Documentation

Every Markdown document is written in English by default and links to a Korean counterpart. Start with an individual project README for technical details. The symbolic-learning [architecture](projects/symbolic-machine-learning/docs/architecture.md) and [reproduction guide](projects/symbolic-machine-learning/docs/reproduce.md) explain the maintained workflow; the [initial experiment report](projects/symbolic-machine-learning/docs/experiment-report.md) is preserved as a historical record.

## Context

This repository began as coursework for the University of Manchester's COMP24412 Knowledge-Based Artificial Intelligence unit (2024-25). Original assignment and lecture PDFs are retained under each project's `references/` directory for provenance. Generated caches, LaTeX auxiliary files, obsolete course synchronisation/submission scripts, and an incomplete backup were removed from the portfolio view.

The repository does not currently declare a licence. Please treat the code and supplied course material accordingly.

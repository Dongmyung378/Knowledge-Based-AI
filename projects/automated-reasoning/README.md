# Automated Reasoning with First-Order Logic

[English](README.md) | [한국어](README.ko.md) | [Portfolio home](../../README.md)

## Overview

This project models small reasoning problems in the TPTP language and uses the Vampire theorem prover to explore proof search, saturation strategies, clausification, and finite-model variants.

## What I built

- First-order encodings for map-colouring relations, set theory, syntax, and a pets logic puzzle.
- Alternative typed formulations of the pets problem for satisfiable and unsatisfiable cases.
- Proof-search experiments using given-clause, discount, and Otter-style saturation presets.
- A workflow that converts proof specifications into LaTeX and retains rendered PDFs for inspection.

## Representative work

| Area | Source | Evidence |
| --- | --- | --- |
| Map reasoning | [`problems/maps.p`](problems/maps.p) | Three proof variants in `artifacts/maps-{a,b,c}.*` |
| Set reasoning | [`problems/sets.p`](problems/sets.p), [`problems/sets.cnf`](problems/sets.cnf) | Rendered derivation in [`artifacts/sets.pdf`](artifacts/sets.pdf) |
| Syntax reasoning | [`problems/syntax.p`](problems/syntax.p) | Rendered derivation in [`artifacts/syntax.pdf`](artifacts/syntax.pdf) |
| Model variants | `problems/pets-{a,b,c}.tff` | Typed variants for model-finding experiments |

## Run a proof

### Prerequisites

- A Unix-like shell
- [Vampire](https://vprover.github.io/)

The wrapper currently expects Vampire at `/opt/vampire/vampire`. If needed, edit `VAMPIRE_BIN` in `tools/run_vampire`.

```bash
cd projects/automated-reasoning
./tools/run_vampire --preset gc problems/maps.p
```

Other available presets are `discount` and `otter`; use `--verbose gc` or `--verbose all` to inspect the search process.

```bash
./tools/run_vampire --preset discount --verbose gc problems/sets.p
```

## Design notes

The project keeps three kinds of material separate:

- `problems/` contains executable logical specifications and reference problems.
- `artifacts/` contains proof metadata, generated LaTeX, and rendered results.
- `tools/` contains the prover wrapper and conversion helper.

This separation makes the authored logical models easy to review without mixing them with generated output.

## Limitations

- The Vampire path is hard-coded in the supplied wrapper and may require local configuration.
- The checked-in proof artefacts document prior runs; they are not regenerated automatically.
- Original coursework PDFs are preserved in `references/` and are not part of the executable workflow.

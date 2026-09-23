# Constraint Modelling in Prolog

[English](README.md) | [한국어](README.ko.md) | [Portfolio home](../../README.md)

## Overview

This project uses declarative Prolog rules to validate spacecraft component layouts. A design can contain individual parts and recursively nested shields; valid designs must satisfy compatibility and component-use constraints.

## Problem model

The knowledge base defines eight components and a symmetric `safe_with/2` relation. The completed solver adds predicates for four concerns:

| Predicate | Responsibility |
| --- | --- |
| `safe_list/1` | Verifies that every component in a flat list is compatible with every other component |
| `safe_design/1` | Recursively validates parts and nested shields |
| `count_shields/2` | Counts shields at every nesting level using an accumulator |
| `design_uses/2` | Checks that a design consumes the requested components exactly once |

## Implementation approach

- Pattern matching distinguishes `part(Component)` from `shield(InnerDesign)`.
- Recursion handles both the outer design and arbitrarily nested shield contents.
- `select/3` removes a component from the remaining allowed set, preventing reuse.
- `subtract/3` and `append/3` combine component usage across nested structures.
- Pairwise safety is enforced through the explicit `safe_with/2` knowledge base.

## Run the project

Install [SWI-Prolog](https://www.swi-prolog.org/), then run commands from this directory.

```bash
cd projects/logic-programming
swipl -s src/electrical.pl
```

Example queries:

```prolog
?- safe_list([radar, cpu, imu]).
true.

?- safe_design([part(radar), shield([part(cpu), part(imu)])]).
true.

?- count_shields([part(radar), shield([part(cpu), shield([part(imu)])])], Count).
Count = 2.
```

Use `halt.` to leave the interpreter.

## Project structure

```text
logic-programming/
├── src/
│   ├── database.pl    # Component facts and compatibility relation
│   ├── electrical.pl  # Completed recursive design checker
│   └── warmup.pl      # Minimal introductory facts
└── references/
    └── prolog_lab_assessed.pdf
```

`electrical.pl` includes the component facts directly, so it can be loaded on its own. `database.pl` retains the standalone source knowledge base used during development.

## Limitations

- The compatibility data is fixed rather than loaded dynamically.
- Validation is expressed for the assignment's `part/1` and `shield/1` term structure.
- The original project provides no automated test suite; the documented queries are useful smoke tests.

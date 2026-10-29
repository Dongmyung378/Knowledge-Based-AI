# Local PySwip compatibility patch

[English](PATCH.md) | [한국어](PATCH.ko.md)

This directory contains PySwip from upstream commit
`c07e8083c6a58eb7de99bb26c8dc89a0c215f52c`, with its MIT licence and authorship
notices. `UPSTREAM.json` records the original file hashes. Only `core.py` and the
package version in `pyproject.toml` differ from those upstream files.

The local version is **0.3.3+argv1**. Upstream's generic string conversion wrapper
creates a temporary ctypes argument vector for `PL_initialise`. SWI-Prolog retains
that vector after the call. Its documented contract requires the vector to stay
valid for the lifetime of the engine. A native pointer probe found stale slots
immediately after initialization in the unpatched package.

The patch retains the vector and its byte strings, appends a terminal NULL, and
declares the native function signature. Normal `PL_cleanup` remains enabled.
It does not change query handling, rule learning, predictions, or recorded
benchmark results. Install it through the project's requirements file from the
project directory; no Git checkout of an external package is needed.

`tests/public/test_prolog_argv_lifetime.py` starts four independent interpreters,
checks the actual native argument addresses before and after allocations, runs
a real Prolog query, and waits for normal shutdown with empty stderr.

Reference: [SWI-Prolog's PL_initialise lifetime contract](https://www.swi-prolog.org/pldoc/man?CAPI=PL_initialise).

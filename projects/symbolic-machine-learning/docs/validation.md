# Execution and release verification

[English](validation.md) | [한국어](validation.ko.md) | [Project README](../README.md)

## Downloaded ZIP recheck and native binding fix

The 2026-10-29 clean-environment recheck found an intermittent `PL_cleanup` access violation after an otherwise passing test run. Earlier successful runs below remain valid records of those executions; they did not exclude this intermittent defect. A direct native probe found that upstream PySwip had already released the argument vector retained by SWI-Prolog. The local **0.3.3+argv1** package retains that vector and its strings, supplies its terminal NULL and leaves normal cleanup enabled. See the [patch and upstream provenance](../vendor/pyswip/PATCH.md).

The new regression checks inspect the actual native pointers before and after memory allocation, execute a real query and wait for normal interpreter exit. They supplement the existing algorithm tests rather than changing evaluation data or scores. The new [execution receipt](../reports/clean-room-20261029.json) records the current ZIP-based Windows and Linux checks and their limits.

Windows completed **five full guarded runs**, each with **155 passed and two permission-related skips**. Linux completed **one full run with 157 passed and no skips**. All stages exited with code zero and empty stderr, including 24 isolated argument-lifetime probes across these runs.

## Earlier environment verification

| Executed environment | Runtime | Confirmed scope |
| --- | --- | --- |
| Windows on the development PC | Python 3.12.7, SWI-Prolog 9.2.9 x64, pinned PySwip 0.3.3 | Source ZIP extraction, all five guarded stages, 151 passed and two skipped tests |
| WSL Ubuntu 24.04 on the same PC, Linux filesystem | Python 3.12.3, SWI-Prolog 9.0.4, pinned PySwip 0.3.3 | Source ZIP extraction, all five guarded stages, 153 regression checks with normal exit |
| Offline browser | Actual Chrome, English and Korean, desktop and mobile | Embedded model, input changes, trace highlights and logical equivalence |

The Linux run extracted a release-candidate ZIP to a native Linux filesystem and executed `python tools/run_checks.py --output-dir outputs/verification`. All five stages completed in **25.22 seconds**, including **153/153 tests with no skips**, process exit code zero and empty native stderr. The source hashes stayed unchanged during execution. Its `graph_small` hold-out predicted 12/12 positive and 59/59 negative examples correctly, and each initial tree learner predicted 4/4 examples correctly. A separate cyclic look-ahead smoke command also predicted 12/12 positive and 12/12 negative examples correctly. These are explicit fixtures, separate from the 30-case final graph benchmark.

Windows extracted the same source ZIP and passed **5/5 guarded stages**. Pytest collected 153 tests: **151 passed, two skipped, zero failures and zero errors**. The two symlink checks were skipped for Windows permission requirements. Both initial tree smoke checks were 4/4 and the relational hold-out was 71/71. Every stage exited with code zero and empty stderr.

The [Windows receipt](../reports/verification-windows.json), [Linux receipt](../reports/verification-linux.json) and [combined verification](../reports/verification.json) identify the tested candidate archive and executable source hashes. Documentation and evidence were added to the final distribution afterwards, so its archive hash differs from the tested candidate while the tested executable source hashes remain identical. The included manifest checks the final declared payloads; no self-referential final ZIP hash is embedded in these documents.

The environments share one physical computer. WSL is a separate Linux userspace and filesystem, not independently owned hardware or an independent-machine certificate. The checked-in Ubuntu CI workflow is an execution path; a remote GitHub Actions pass is not asserted without its actual completed run.

## Native lifecycle verification

Earlier diagnostic runs printed a passing pytest summary but subsequently failed during native process shutdown. A test summary alone was therefore insufficient. The maintained implementation reorganises bounded queries and target-table lifetimes, keeps temporary clause references inside Prolog, and attempts cleanup independently of exhausted learning budgets. It does not disable native shutdown to conceal the failure.

The final Windows [lifecycle stress report](../reports/foil-native-lifecycle.json) records **eight fresh Python processes**. Each closes an unused recursive context, then learns and predicts with two full graph contexts. Every process exited normally with code zero and empty stderr.

Both final graph modes were then rerun from the maintained source: **60 benchmark workers** all exited with code zero and empty stderr. The [comparison receipt](../reports/foil-comparison-validation.json) independently checks graph labels with NetworkX transitive closure, confirms identical paired inputs and splits, and confirms identical predictions for the 20 cases completed in both modes.

Default pytest uses `--capture=sys` through `setup.cfg` to preserve native standard-stream handles on Windows. That capture configuration is separate from the query and table-lifetime repair. Verification concerns sequential FOIL contexts and isolated benchmark processes; concurrently active contexts are outside the isolation claim.

## Interactive explanation checks

The offline demo embeds [`examples/explanation.json`](../examples/explanation.json) and computes predictions from its exported tree and DNF terms. It does not hard-code the target concept into a separate prediction formula.

Actual Chrome exercised English and Korean pages at desktop 1440×1000 and mobile 390×844 viewports. In each combination, all eight table selections and all eight checkbox inputs were checked: **64 input transitions**. Tree predictions, DNF predictions, stored example traces and highlighted paths matched. There were no JavaScript errors, external asset dependencies or body overflow. The pages were opened through `file://` without a server.

This demonstrates an eight-input model fitted to the complete truth table, not an unseen-data performance result. The [maintained results](results.md) describe the separate held-out measurements.

## Preserved source and distribution

The initial 27 code, data and document files remain byte-identical in the pinned snapshot, and three initial PDFs remain byte-identical under `references/`. The provenance file inventories all 30 initial payloads. The release builder checks these against their initial hashes and checks the preserved DTL source prefix and unchanged historical experiment reports.

The project manifest includes the verification tools, source, supported fixtures, documentation, reports, figures, demo and initial evidence. The verifier checks declared paths, sizes and SHA-256 values in a checkout or directly in the downloadable repository ZIP, along with the initial ZIP's integrity. Companion repository projects are retained but their optional runtimes are outside this project's validation claim.

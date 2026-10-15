# Reproduce and verify a release

[English](reproduce.md) | [한국어](reproduce.ko.md) | [Project README](../README.md)

Run commands from `projects/symbolic-machine-learning` unless stated otherwise. Python and SWI-Prolog are separate runtimes; installing Python packages alone does not install the Prolog shared library.

## Install the local environment

Use Python 3.12. The tested Windows native runtime is **SWI-Prolog 9.2.9 x64**; the Ubuntu 24.04 system package is **SWI-Prolog 9.0.4**. Python 3.10 or later is required by the release tools. Activate a clean environment rather than reusing an unrelated project's packages.

Install Git as well: `pip` uses it to fetch the pinned PySwip source commit, including when you started from the downloadable ZIP. The generated attribute examples and graph fixtures require no separate dataset download.

```bash
python -m venv .venv
```

Linux or WSL:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

```bash
python -m pip install -r requirements.lock.txt
python tools/check_environment.py --output outputs/environment.json
```

On Ubuntu 24.04, install the system runtime with `sudo apt-get install swi-prolog-nox`. On Windows, use the [official 9.2.9 x64 installer](https://www.swi-prolog.org/download/stable/bin/swipl-9.2.9-1.x64.exe.envelope) and make `swipl` available on `PATH`. Its official installer SHA-256 is `0e6dbf5f4bb245344a257f2715f5d793d17870dee9eea1735ccb67b35f1e037c`.

Keep the complete native installation, including its runtime root and `bin` contents; copying only `libswipl.dll` is insufficient. For an extracted installation without installer registration, set `SWI_HOME_DIR` to its installation root and `LIBSWIPL_PATH` to the `bin/libswipl.dll` file, then prepend that `bin` directory to the current process's `PATH`. Keep these machine-local paths out of commits and published reports. A separate Windows 10.0.2 runtime comparison failed during initialisation with this pinned bridge and was not adopted. The release does not recommend substituting the latest SWI-Prolog version for the tested Windows runtime.

The environment checker records package versions, discovery checks and an actual isolated PySwip query whose expected output is `[1, 4, 9]`. It omits executable locations, home directories and raw exception traces. Exit status zero means every listed check passed; a nonzero status includes corrective hints. A discovery check alone is not a substitute for the executed query.

## Check payload integrity

```bash
python tools/verify_release.py
```

The manifest declares each maintained project payload's relative path, byte count and SHA-256. It excludes its own file because a file cannot contain its own final hash. It includes the verifier itself and the preserved initial snapshot. File hashes provide consistency checking rather than third-party authenticity or a digital signature.

Verify the downloadable repository ZIP without extracting it:

```bash
python tools/verify_release.py --zip /path/to/knowledge-based-ai-source.zip
```

The verifier automatically finds the unique project manifest inside the archive. If a larger archive has more than one matching manifest, supply `--prefix` with the project directory inside that archive. Unsafe ZIP member paths, symlinks, duplicate names, CRC failures and declared payload mismatches fail verification. Extra files outside the declared payload list are not certified by this command.

## Run executable checks

Run the complete guarded sequence:

```bash
python tools/run_checks.py --output-dir outputs/verification
```

This checks payload integrity, the actual Python-to-Prolog query, pytest, the fixed 4/4 predictions for each initial tree learner, and the 71/71 relational hold-out predictions. It requires normal subprocess exits and checks native failure text after the test summary. Detailed reports and logs are retained under the selected new or empty output directory. A failed stage stops dependent checks. Use a different output directory for a repeat run.

Individual regression tests remain available:

```bash
python -m pytest
```

`setup.cfg` selects `--capture=sys` so the default command preserves native standard-stream handles on Windows. This compatibility setting does not replace checking process exit.

Keep the complete pytest summary and environment report with any reproduced result. The test suite uses generated attribute data and tracked relational fixtures. A passing suite establishes those specified cases, not correctness for all possible inputs or Prolog knowledge bases.

The original smoke workflows remain available:

```bash
python evaluate_attributes.py eval-size -a dtl -a my-dtl -s 4 -d 2 -t 0.75
python evaluate_rules.py -a foil -d tests/graph_small.json -k tests/graph_small.pl -t "reachable(X,Y)" -r -e 0.8
```

## Run the maintained experiments

```bash
python tools/benchmark_attributes.py --plan configs/benchmark-plan.json --phase development --output outputs/attribute-development.json
python tools/benchmark_attributes.py --plan configs/benchmark-plan.json --phase evaluation --output outputs/attribute-evaluation.json
python tools/benchmark_inference.py --phase evaluation --output outputs/inference-evaluation.json
python tools/benchmark_foil.py --seed-start 200 --output outputs/foil-final-greedy.json
python tools/benchmark_foil.py --lookahead 2 --seed-start 200 --output outputs/foil-final-lookahead.json
```

The development and evaluation phases are separate commands. Keep the checked-in plan unchanged when reproducing the published comparison, and inspect the plan and result metadata before interpreting the output. `--quick` on the FOIL benchmark requests its smaller smoke workload; a quick run must not be reported as the full benchmark. Store your own outputs under ignored `outputs/` rather than overwriting the published reports.

To retain the original relational CLI's clauses, example-level predictions and failure diagnostics in JSON:

```bash
python evaluate_rules.py -a foil -d tests/graph_small.json -k tests/graph_small.pl -t "reachable(X,Y)" -r -e 0.8 --output-json outputs/graph-small.json
```

The CLI accepts `--max-seconds`, `--query-timeout`, `--max-candidates`, `--max-prolog-queries`, `--max-clauses` and `--max-literals`. Defaults are 60 seconds for fitting, 2 seconds per query, 20,000 candidate evaluations, 1,000,000 Prolog queries, 128 clauses and 16 literals per clause. `--lookahead 2` opts into the bounded two-literal extension; default `--lookahead 0` retains greedy search. These are controlled search budgets, not a security boundary for arbitrary knowledge bases. The report's `status` and per-algorithm status must be inspected; failure diagnostics are not a successfully learned model.

The graph benchmark holds out relation pairs within each known graph. Background edge facts remain available during learning, so this is relational completion within the graph, not transfer to an unseen graph. Its labels are checked against an independent queue-based breadth-first search oracle.

The historical noise and timing commands and their limitations are retained in the [initial evaluation guide](evaluation-guide.md). Those command names still exist, but the maintained implementation corrects their comparison protocol. Use the initial snapshot to reproduce the original procedures and the maintained result report for the new comparison. Do not reinterpret the historical tables as new held-out measurements.

The maintained `eval-noisy` defaults to 80% training and 20% clean hold-out and accepts `--train_split`. Only training labels are flipped, with shared concepts and splits across algorithms and noise levels. `eval-size` reports a paired exact McNemar p-value for disagreement in correctness; it is descriptive and has no adjustment for multiple comparisons. `eval-time` accepts `--random_seed`/`-r`, `--runs` and `--repeats`, shares pre-generated inputs and rotates algorithm order. Use the dedicated benchmark for `pruned-dtl`, which needs an independent validation set.

## Inspect the initial version

`legacy/initial-aa947038.zip` preserves 27 initial code, test, experiment and data files from commit `aa947038f923e98ec0bf16457745d538284ef45c`. The three initial reference PDFs remain byte-identical in `references/` and are not duplicated in the snapshot. `legacy/initial-provenance.json` inventories all 30 initial files and records those shared reference hashes. The release manifest checks both the snapshot and the maintained reference files. Extract the snapshot to a separate directory for inspection or a historical run; it is not an overlay to copy over the maintained implementation. If inspecting the initial reference material from that directory, copy the unchanged `references/` directory alongside it.

The surrounding repository contains two other coursework projects. They are preserved context rather than dependencies of this symbolic-learning release. The original PDFs are retained for provenance; the repository does not declare a new licence for them.

## Interpreting verification evidence

An independently created Python environment on the same computer still shares the hardware and operating system. WSL provides a separate Linux userspace and filesystem, while sharing the host hardware. Neither is a certificate that every other machine will behave identically. Published measurements identify which environment and commands were actually executed; a GitHub Actions workflow is only a proposed remote execution path until a visible remote run completes.

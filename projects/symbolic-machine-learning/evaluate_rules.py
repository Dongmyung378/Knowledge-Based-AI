"""Train and evaluate FOIL with shared splits and optional machine-readable evidence."""

import hashlib
import json
import math
import platform
import random
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace

import click

from learning.rule_learner import FOIL, FOILLearningError, validate_foil_dataset
from learning.util import AlgorithmRegistry, Dataset


def split(examples, split=0.8, *, rng=None):
    if not 0 < split < 1:
        raise ValueError("The training fraction must be strictly between 0 and 1.")
    count = math.ceil(split * len(examples))
    if not 0 < count < len(examples):
        raise ValueError("Each positive/negative class must leave at least one training and one hold-out example.")
    indices = set((rng or random).sample(range(len(examples)), count))
    return ([example for index, example in enumerate(examples) if index in indices],
            [example for index, example in enumerate(examples) if index not in indices])


def _environment():
    versions = {}
    for name in ("pyswip", "click", "numpy", "scipy", "networkx"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return {"python": platform.python_version(), "system": platform.system(),
            "machine": platform.machine(), "dependencies": versions}


def _write_json(path, result):
    if path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _finite_positive(ctx, parameter, value):
    if not math.isfinite(value) or value <= 0:
        raise click.BadParameter("must be a positive finite number", ctx=ctx, param=parameter)
    return value


def _training_fraction(ctx, parameter, value):
    if value is not None and (not math.isfinite(value) or not 0 < value < 1):
        raise click.BadParameter("The training fraction must be strictly between 0 and 1.", ctx=ctx, param=parameter)
    return value


@click.command()
@click.option('algos', '--algo', '-a', type=str, multiple=True, required=True,
              help='Registered algorithms. All algorithms receive the same precomputed split.')
@click.option('--dataset', '-d', type=click.Path(exists=True, dir_okay=False), required=True,
              help='JSON object containing nonempty pos and neg example arrays.')
@click.option('--kb', '-k', type=click.Path(exists=True, dir_okay=False), required=True,
              help='Trusted Prolog knowledge-base source file.')
@click.option('--eval', '-e', type=float, default=None, callback=_training_fraction,
              help='Training fraction strictly between 0 and 1. Omit to train without hold-out evaluation.')
@click.option('--target', '-t', type=str, required=True, help='Target such as reachable(X,Y).')
@click.option('--recursive', '-r', is_flag=True, help='Allow recursive learned target clauses.')
@click.option('--random_seed', '-s', type=int, default=42, show_default=True)
@click.option('--output-json', type=click.Path(dir_okay=False), default=None,
              help='Save shared split, predictions, rules, budgets, versions, and failure status as JSON.')
@click.option('--max-seconds', type=float, default=60.0, callback=_finite_positive, show_default=True)
@click.option('--query-timeout', type=float, default=2.0, callback=_finite_positive, show_default=True)
@click.option('--max-candidates', type=click.IntRange(min=1), default=20000, show_default=True)
@click.option('--max-prolog-queries', type=click.IntRange(min=1), default=1000000, show_default=True)
@click.option('--max-clauses', type=click.IntRange(min=1), default=128, show_default=True)
@click.option('--max-literals', type=click.IntRange(min=1), default=16, show_default=True)
@click.option('--lookahead', type=click.Choice(['0', '2']), default='0', show_default=True,
              help='Optional two-literal zero-gain bridge search, used only when greedy search stalls.')
def main(algos, dataset, kb, eval, target, recursive, random_seed, output_json,
         max_seconds, query_timeout, max_candidates, max_prolog_queries, max_clauses, max_literals, lookahead):
    budgets = {"max_seconds": max_seconds, "query_timeout_seconds": query_timeout,
               "max_candidate_evaluations": max_candidates, "max_prolog_queries": max_prolog_queries,
               "max_clauses": max_clauses, "max_literals_per_clause": max_literals, "lookahead": int(lookahead)}
    result = {"schema_version": 1, "status": "running", "seed": random_seed,
              "train_fraction": eval, "target": target, "recursive": recursive,
              "budgets": budgets, "environment": _environment(), "algorithms": []}
    learner = None
    try:
        data_path = Path(dataset)
        kb_path = Path(kb)
        data = json.loads(data_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"pos", "neg"}:
            raise ValueError("Dataset JSON must have exactly the keys pos and neg.")
        if any(not isinstance(data[key], list) or not data[key] for key in ("pos", "neg")):
            raise ValueError("pos and neg must each be nonempty example arrays.")
        # Validate every label and binding before splitting. A contradiction
        # must not disappear merely because its two copies land in different
        # train/hold-out partitions. Invalid values never enter the JSON report.
        validate_foil_dataset(SimpleNamespace(target=target, kb=kb, examples=data["pos"] + data["neg"],
                                              positive_examples=data["pos"], negative_examples=data["neg"]))
        result["inputs"] = {"dataset_name": data_path.name, "kb_name": kb_path.name,
                            "dataset_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
                            "kb_sha256": hashlib.sha256(kb_path.read_bytes()).hexdigest()}
        rng = random.Random(random_seed)
        if eval is not None:
            train_pos, eval_pos = split(data["pos"], eval, rng=rng)
            train_neg, eval_neg = split(data["neg"], eval, rng=rng)
        else:
            train_pos, train_neg = data["pos"], data["neg"]
            eval_pos, eval_neg = [], []
        result["split"] = {"train_positive": train_pos, "train_negative": train_neg,
                           "holdout_positive": eval_pos, "holdout_negative": eval_neg}
        for algo_name in algos:
            learner = None
            ds = Dataset(positive_examples=train_pos, negative_examples=train_neg, kb=kb, target=target)
            with AlgorithmRegistry.create_algorithm(algo_name, dataset=ds, recursive=recursive, **budgets) as learner:
                learner.fit()
                click.echo(f"Algorithm {click.style(algo_name, fg='green')} learned")
                click.echo(learner.hypothesis)
                rows = []
                for expected, examples in ((True, eval_pos), (False, eval_neg)):
                    for example in examples:
                        rows.append({"example": example, "expected": expected,
                                     "prediction": bool(learner.predict(example))})
                positives = [row for row in rows if row["expected"]]
                negatives = [row for row in rows if not row["expected"]]
                if eval is not None:
                    acc_pos = sum(row["prediction"] for row in positives)
                    acc_neg = sum(not row["prediction"] for row in negatives)
                    click.echo(f"Accuracy on positive examples: {acc_pos}/{len(eval_pos)} ({acc_pos / len(eval_pos):.2f})")
                    click.echo(f"Accuracy on negative examples: {acc_neg}/{len(eval_neg)} ({acc_neg / len(eval_neg):.2f})")
                result["algorithms"].append({"algorithm": algo_name, "status": "passed",
                                             "rules": [repr(clause) for clause in learner.hypothesis.expressions],
                                             "search_trace": list(learner.search_trace_),
                                             "stats": dict(learner.stats_), "predictions": rows})
                version = list(learner.prolog.query("current_prolog_flag(version, Version)"))[0]["Version"]
                result["environment"]["swi_prolog_version_number"] = version
        result["status"] = "passed"
    except (ValueError, OSError, FOILLearningError) as exc:
        result["status"] = "failed"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        if learner is not None:
            result["failed_fit_stats"] = dict(learner.stats_)
        _write_json(output_json, result)
        raise click.ClickException(str(exc)) from exc
    _write_json(output_json, result)


if __name__ == '__main__':
    main()

"""Command-line experiments for categorical attribute learners.

Historical measurements are preserved separately. Supported accuracy commands
now use clean held-out examples, and timing commands share generated datasets.
"""

import math
import random
import time
from typing import Dict, List, Tuple

import click
import numpy as np
from scipy.stats import binomtest, t

from learning.attr_learner import Conjunction, Disjunction
from learning.generate import AttributeDatasetGenerator
from learning.util import Algorithm, AlgorithmRegistry, Dataset, Examples


def evaluate(algo: Algorithm, eval: Dataset) -> float:
    """Return the number of correctly classified examples."""
    if not eval:
        raise ValueError("Evaluation data must not be empty.")
    predictions = algo.predict_all(eval)
    if len(predictions) != len(eval):
        raise ValueError("Prediction count must match the evaluation set.")
    return sum(prediction == example["target"] for prediction, example in zip(predictions, eval))


def generate_random_hypothesis(attr_values: Dict[str, List[bool]], max_relevant=None, max_conj=4, rng=None):
    """Uniformly sample distinct complete minterms without a rejection loop."""
    rng = rng or random
    max_relevant = len(attr_values) if max_relevant is None else max_relevant
    if type(max_relevant) is not int or not 0 <= max_relevant <= len(attr_values):
        raise ValueError("max_relevant must be between zero and the number of attributes.")
    if type(max_conj) is not int or max_conj < 0:
        raise ValueError("max_conj must be a nonnegative integer.")
    relevant = rng.sample(list(attr_values), max_relevant)
    domains = []
    for name in relevant:
        try:
            values = list(dict.fromkeys(attr_values[name]))
        except TypeError as exc:
            raise ValueError("Attribute categories must be hashable.") from exc
        if not values:
            raise ValueError("Every relevant attribute needs at least one category.")
        domains.append(values)
    possibilities = math.prod(len(values) for values in domains)
    if max_conj > possibilities:
        raise ValueError(f"max_conj={max_conj} exceeds the {possibilities} distinct possible minterms.")
    conjunctions = []
    for encoded in rng.sample(range(possibilities), max_conj):
        assignments = {}
        for name, values in zip(reversed(relevant), reversed(domains)):
            encoded, index = divmod(encoded, len(values))
            assignments[name] = values[index]
        conjunctions.append(Conjunction(assignments))
    return Disjunction(conjunctions)


def split(dataset: Dataset, split=0.8, rng=None) -> Tuple[Examples, Examples]:
    """Create disjoint train/test rows; callers reuse them across algorithms."""
    if not math.isfinite(split) or not 0 < split < 1:
        raise ValueError("The training fraction must be strictly between zero and one.")
    examples = list(dataset)
    count = math.ceil(split * len(examples))
    if not examples or count >= len(examples):
        raise ValueError("The requested split must leave nonempty training and evaluation sets.")
    order = list(range(len(examples)))
    (rng or random).shuffle(order)
    indices = set(order[:count])
    return ([dict(example) for index, example in enumerate(examples) if index in indices],
            [dict(example) for index, example in enumerate(examples) if index not in indices])


def paired_comparison(baseline_predictions, candidate_predictions, rows):
    """Exact McNemar comparison of paired correctness, without a significance claim."""
    if not rows or len(baseline_predictions) != len(rows) or len(candidate_predictions) != len(rows):
        raise ValueError("Paired predictions must match the same nonempty evaluation set.")
    baseline_only = candidate_only = 0
    for baseline, candidate, example in zip(baseline_predictions, candidate_predictions, rows):
        baseline_correct = baseline == example["target"]
        candidate_correct = candidate == example["target"]
        baseline_only += baseline_correct and not candidate_correct
        candidate_only += candidate_correct and not baseline_correct
    discordant = baseline_only + candidate_only
    p_value = float(binomtest(baseline_only, discordant, 0.5).pvalue) if discordant else 1.0
    return {"baseline_only": baseline_only, "candidate_only": candidate_only,
            "discordant": discordant, "exact_mcnemar_p": p_value}


def _validate_algorithms(algos):
    if not algos:
        raise ValueError("Specify at least one learner with --algo.")
    if len(set(algos)) != len(algos):
        raise ValueError("Specify each learner only once.")
    for name in algos:
        if name not in AlgorithmRegistry.registry:
            raise ValueError(f"Unknown attribute learner: {name!r}.")
        registered = AlgorithmRegistry.registry[name]
        if not isinstance(registered, type) or not issubclass(registered, Algorithm):
            raise ValueError(f"Unknown attribute learner: {name!r}.")
        if name == "pruned-dtl":
            raise ValueError("Use tools/benchmark_attributes.py for pruned-dtl with a separate validation set.")


def _dataset(size, relevant, rng):
    if relevant < 1 or relevant > size:
        raise ValueError("The number of relevant attributes must be between one and the dataset size.")
    domains = {f"A{i}": [True, False] for i in range(size)}
    hypothesis = generate_random_hypothesis(domains, relevant, 2 ** (relevant - 1), rng=rng)
    return Dataset(AttributeDatasetGenerator(domains, hypothesis).generate_all())


def _predictions(algos, train, test):
    results = []
    for name in algos:
        # Each model receives its own dictionaries with identical row content.
        model = AlgorithmRegistry.create_algorithm(name, dataset=Dataset([dict(row) for row in train]))
        model.fit()
        predictions = model.predict_all(Dataset([dict(row) for row in test]))
        if len(predictions) != len(test):
            raise ValueError("Prediction count must match the held-out test set.")
        results.append((name, predictions))
    return results


def _report_accuracy(algos, predictions, test):
    baseline_name, baseline_predictions = predictions[0]
    baseline_score = sum(prediction == row["target"] for prediction, row in zip(baseline_predictions, test))
    click.echo(20 * "----")
    click.echo(f"{click.style(baseline_name, fg='green')}(baseline) accuracy: "
               f"{baseline_score}/{len(test)} ({baseline_score / len(test):.3f}))")
    for name, candidate in predictions[1:]:
        score = sum(prediction == row["target"] for prediction, row in zip(candidate, test))
        paired = paired_comparison(baseline_predictions, candidate, test)
        click.echo(f"Accuracy of {click.style(name, fg='green')} \t {score}/{len(test)} "
                   f"({score / len(test):.3f})) | Paired disagreement: "
                   f"baseline-only {paired['baseline_only']}, candidate-only {paired['candidate_only']}; "
                   f"exact McNemar p={paired['exact_mcnemar_p']:.6g}")
    if len(algos) > 1:
        click.echo("Paired p-values are descriptive and have no multiple-comparison adjustment.")


@click.command(help="Train on noisy labels and evaluate on independent, clean held-out examples.")
@click.option("algos", "--algo", "-a", type=str, multiple=True)
@click.option("sizes", "--size", "-s", type=click.IntRange(min=1), multiple=True, default=[5, 7, 10])
@click.option("max_dets", "--max-det", "-d", type=click.IntRange(min=1), multiple=True, default=[3])
@click.option("corrupts", "--corrupt_ratio", "-c", type=click.FloatRange(0, 1), multiple=True, default=[0.1, 0.3, 0.5])
@click.option("--random_seed", "-r", type=int, default=42)
@click.option("--train_split", type=click.FloatRange(0, 1, min_open=True, max_open=True), default=0.8,
              help="Training fraction; remaining clean rows are held out.")
def eval_noisy(algos, max_dets, corrupts, sizes, random_seed=42, train_split=0.8):
    try:
        _validate_algorithms(algos)
        for size in sizes:
            for corrupt in corrupts:
                for relevant in max_dets:
                    if not math.isfinite(corrupt) or not 0 <= corrupt <= 1:
                        raise ValueError("The corruption ratio must be between zero and one.")
                    rng = random.Random(f"{random_seed}:size={size}:relevant={relevant}")
                    dataset = _dataset(size, relevant, rng)
                    train, test = split(dataset, train_split, rng=rng)
                    corruption_order = list(range(len(train)))
                    rng.shuffle(corruption_order)
                    corrupted = set(corruption_order[:math.ceil(corrupt * len(train))])
                    for index in corrupted:
                        train[index]["target"] = not train[index]["target"]
                    click.echo(20 * "====")
                    click.echo(f"Number of attributes: {size}. of which {relevant} are used to generate a random "
                               f"hypothesis. Dataset size: {2 ** size}, number of corrupted examples {len(corrupted)} ")
                    click.echo(f"Independent split: {len(train)} training examples, {len(test)} clean held-out test "
                               "examples; label corruption applies to training only.")
                    _report_accuracy(algos, _predictions(algos, train, test), test)
    except (ValueError, TypeError) as exc:
        raise click.ClickException(str(exc)) from exc


@click.command(help="Train from fewer examples and evaluate all learners on the same held-out rows.")
@click.option("algos", "--algo", "-a", type=str, multiple=True)
@click.option("sizes", "--size", "-s", type=click.IntRange(min=1), multiple=True, default=[5, 7, 10])
@click.option("max_dets", "--max-det", "-d", type=click.IntRange(min=1), multiple=True, default=[10])
@click.option("train_splits", "--train_split", "-t", type=click.FloatRange(0, 1, min_open=True, max_open=True),
              multiple=True, default=[0.1, 0.3, 0.5])
@click.option("--random_seed", "-r", type=int, default=42)
def eval_size(algos, max_dets, train_splits, sizes, random_seed=42):
    try:
        _validate_algorithms(algos)
        for size in sizes:
            for ratio in train_splits:
                for requested_relevant in max_dets:
                    # Preserve the original limited-data command's clamping.
                    relevant = min(requested_relevant, size)
                    rng = random.Random(f"{random_seed}:size={size}:relevant={relevant}")
                    dataset = _dataset(size, relevant, rng)
                    train, test = split(dataset, ratio, rng=rng)
                    click.echo(20 * "====")
                    click.echo(f"Number of attributes: {size}. of which {relevant} are used to generate a random "
                               f"hypothesis. Dataset size: {2 ** size}, size of training set {len(train)}. ")
                    click.echo(f"{sum(row['target'] for row in dataset)} of which are True.")
                    _report_accuracy(algos, _predictions(algos, train, test), test)
    except (ValueError, TypeError) as exc:
        raise click.ClickException(str(exc)) from exc


def get_mean_var_ci(sample, alpha=0.025):
    values = np.asarray(sample, dtype=float)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError("Timing samples must be nonempty and finite.")
    if len(values) == 1:
        return float(values[0]), 0.0, float("nan")
    variance = float(values.var(ddof=1))
    half_width = float(t.ppf(1 - alpha, df=len(values) - 1)) * math.sqrt(variance / len(values))
    return float(values.mean()), variance, half_width


@click.command(help="Time all learners on identical pregenerated datasets with balanced execution order.")
@click.option("algos", "--algo", "-a", type=str, multiple=True)
@click.option("sizes", "--size", "-s", type=click.IntRange(min=1), multiple=True, default=[5, 7, 10])
@click.option("--random_seed", "-r", type=int, default=42)
@click.option("--runs", type=click.IntRange(min=1), default=None, help="Override the original size-dependent run count.")
@click.option("--repeats", type=click.IntRange(min=1), default=5, help="Timed fits per dataset after one untimed fit.")
def eval_time(algos, sizes, random_seed=42, runs=None, repeats=5):
    try:
        _validate_algorithms(algos)
        for size in sizes:
            rng = random.Random(f"{random_seed}:size={size}")
            count = runs if runs is not None else max(1, int((2 ** 15) / (size ** 3)))
            datasets = [_dataset(size, size, rng).examples for _ in range(count)]
            # Sorting and rotating ensures requested algorithm order cannot
            # change datasets or systematically assign the first timing slot.
            base_order = sorted(algos)
            rng.shuffle(base_order)
            results = {name: [] for name in algos}
            click.echo(20 * "====")
            click.echo(f"Number of attributes: {size}. all of which are used to generate a random hypothesis. "
                       f"Dataset size: {2 ** size}. running {count} iterations.")
            click.echo(20 * "----")
            for index, rows in enumerate(datasets):
                offset = index % len(base_order)
                for name in base_order[offset:] + base_order[:offset]:
                    model = AlgorithmRegistry.create_algorithm(name, dataset=Dataset([dict(row) for row in rows]))
                    model.fit()
                    started = time.perf_counter()
                    for _ in range(repeats):
                        model.fit()
                    results[name].append((time.perf_counter() - started) / repeats)
            for name in algos:
                mean, _, interval = get_mean_var_ci(results[name])
                if math.isfinite(interval):
                    click.echo(f"{click.style(name, fg='green')} \t {mean * 1000:.5f}ms +/- {interval * 1000:.3f} ms")
                else:
                    click.echo(f"{click.style(name, fg='green')} \t {mean * 1000:.5f}ms "
                               "(one run; 95% interval unavailable)")
    except (ValueError, TypeError) as exc:
        raise click.ClickException(str(exc)) from exc


cli = click.Group(help="Attribute-learning accuracy and paired CPU timing experiments.")
cli.add_command(eval_size)
cli.add_command(eval_noisy)
cli.add_command(eval_time)


if __name__ == "__main__":
    cli()

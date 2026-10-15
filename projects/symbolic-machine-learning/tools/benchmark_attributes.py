"""Controlled, paired Boolean-learning benchmark. No external dataset is required."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import platform
import random
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from learning.attr_learner import Leaf, Node, to_logic_expression  # noqa: E402
from learning.util import AlgorithmRegistry, Dataset  # noqa: E402


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_plan(plan):
    allowed = {'majority', 'dtl', 'my-dtl', 'corrected-dtl', 'gain-ratio', 'depth-limited', 'gain-depth', 'gain-depth-tuned', 'pruned-dtl'}
    if not plan.get('algorithms') or len(plan['algorithms']) != len(set(plan['algorithms'])) or not set(plan['algorithms']) <= allowed:
        raise ValueError('Provide unique supported algorithms')
    if 'my-dtl' not in plan['algorithms']:
        raise ValueError('The paired report requires the preserved my-dtl reference')
    train, validation = plan['train_fraction'], plan['validation_fraction']
    if not (0 < train < 1 and 0 < validation < 1 and train + validation < 1):
        raise ValueError('Train and validation fractions must leave a nonempty test split')
    if type(plan['timing_repeats']) is not int or not 1 <= plan['timing_repeats'] <= 100:
        raise ValueError('timing_repeats must be an integer between 1 and 100')
    if set(plan['development']['seeds']) & set(plan['evaluation']['seeds']):
        raise ValueError('Development and evaluation seeds must be disjoint')
    for phase in ['development', 'evaluation']:
        values = plan[phase]
        if not values['seeds'] or len(values['seeds']) != len(set(values['seeds'])):
            raise ValueError('Each phase requires nonempty unique seeds')
        if any(type(value) is not int or not 4 <= value <= 12 for value in values['attributes']):
            raise ValueError('The bounded full-truth-table benchmark supports 4 to 12 attributes')
        if not values['noise'] or any(not 0 <= value <= 1 for value in values['noise']):
            raise ValueError('Training label noise must be between zero and one')
    if not plan['depth_candidates'] or any(value != 'unlimited' and (type(value) is not int or value < 0) for value in plan['depth_candidates']):
        raise ValueError('Depth candidates must be nonnegative integers or unlimited')


def make_case(family, attributes, noise, seed, train_fraction=0.6, validation_fraction=0.2):
    """A case RNG does not depend on model order or the outer experiment loop."""
    case_key = f'{family}:{attributes}:{seed}'
    rng = random.Random(int(hashlib.sha256(case_key.encode()).hexdigest()[:16], 16))
    rows = [dict(zip((f'A{i}' for i in range(attributes)), values))
            for values in itertools.product([False, True], repeat=attributes)]
    relevant = rng.sample(range(attributes), min(6, attributes))
    if family == 'conjunction':
        terms = [[(a, bool(rng.randrange(2))) for a in relevant[:3]]]
    elif family == 'sparse_dnf':
        terms = [[(a, bool(rng.randrange(2))) for a in rng.sample(relevant, 3)] for _ in range(3)]
    elif family == 'xor':
        terms = None
    elif family == 'random_truth':
        terms = None
    else:
        raise ValueError(f'Unknown concept family: {family}')
    if family == 'random_truth':
        labels = [False] * (len(rows) // 2) + [True] * (len(rows) // 2)
        rng.shuffle(labels)
    elif family == 'xor':
        labels = [sum(row[f'A{a}'] for a in relevant[:3]) % 2 == 1 for row in rows]
    else:
        labels = [any(all(row[f'A{a}'] == val for a, val in term) for term in terms) for row in rows]
    for row, target in zip(rows, labels):
        row['target'] = target
    # Stratification gives each split both classes when each class has >=3 rows.
    groups = [[i for i, target in enumerate(labels) if target == label] for label in [False, True]]
    train_indices, validation_indices, test_indices = [], [], []
    for indices in groups:
        rng.shuffle(indices)
        nt = max(1, math.floor(len(indices) * train_fraction))
        nv = max(1, math.floor(len(indices) * validation_fraction))
        if nt + nv >= len(indices):
            raise ValueError('Insufficient class support for three independent splits')
        train_indices.extend(indices[:nt])
        validation_indices.extend(indices[nt:nt + nv])
        test_indices.extend(indices[nt + nv:])
    for indices in [train_indices, validation_indices, test_indices]:
        indices.sort()
    flip_rng = random.Random(int(hashlib.sha256(f'{case_key}:noise'.encode()).hexdigest()[:16], 16))
    ordered_train = list(train_indices)
    flip_rng.shuffle(ordered_train)
    flips = set(ordered_train[:round(noise * len(ordered_train))])
    train = [dict(row, target=not row['target']) if i in flips else dict(row)
             for i, row in enumerate(rows) if i in set(train_indices)]
    validation = [dict(rows[i]) for i in validation_indices]
    test = [dict(rows[i]) for i in test_indices]
    domains = {f'A{i}': [False, True] for i in range(attributes)}
    return {
        'id': f'{case_key}:noise={noise}', 'family': family, 'attributes': attributes,
        'noise': noise, 'seed': seed, 'concept': {'relevant': relevant, 'terms': terms},
        'train': train, 'validation': validation, 'test': test, 'domains': domains,
        'data_sha256': digest({'train': train, 'validation': validation, 'test': test}),
        'split_indices': {'train': train_indices, 'validation': validation_indices, 'test': test_indices},
        'flipped_training_indices': sorted(flips),
    }


def metrics(predictions, rows):
    if len(predictions) != len(rows) or not rows:
        raise ValueError('Predictions must match a nonempty evaluation set')
    tp = sum(bool(p) and row['target'] for p, row in zip(predictions, rows))
    tn = sum(not p and not row['target'] for p, row in zip(predictions, rows))
    fp = sum(bool(p) and not row['target'] for p, row in zip(predictions, rows))
    fn = sum(not p and row['target'] for p, row in zip(predictions, rows))
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return {'accuracy': (tp + tn) / len(rows), 'balanced_accuracy': (recall + specificity) / 2,
            'precision': tp / (tp + fp) if tp + fp else 0.0, 'recall': recall,
            'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn, 'examples': len(rows)}


def tree_metrics(tree):
    if isinstance(tree, Leaf):
        return {'depth': 0, 'nodes': 1, 'leaves': 1}
    children = [tree_metrics(child) for child in tree.branches.values()]
    return {'depth': 1 + max(child['depth'] for child in children),
            'nodes': 1 + sum(child['nodes'] for child in children),
            'leaves': sum(child['leaves'] for child in children)}


def create_model(name, case, depth=None):
    dataset = Dataset([dict(row) for row in case['train']], attr_values=case['domains'])
    actual = 'gain-depth' if name == 'gain-depth-tuned' else name
    kwargs = {}
    if name not in ['dtl', 'my-dtl']:
        kwargs['max_depth'] = depth
    if name == 'pruned-dtl':
        kwargs['validation_dataset'] = Dataset([dict(row) for row in case['validation']], attr_values=case['domains'])
    return AlgorithmRegistry.create_algorithm(actual, dataset=dataset, **kwargs)


def inspect_model(model):
    if hasattr(model, 'tree_metrics'):
        return model.tree_metrics()
    # Historical classes are unchanged. Reconstruct the identical tree outside
    # the timed fit call, resetting the historical shared counter when present.
    if hasattr(model, 'depth'):
        model.depth = 0
    tree = model.decision_tree_learning(model.dataset.examples, model.dataset.attributes, [])
    if repr(to_logic_expression(tree)) != repr(model.hypothesis):
        raise RuntimeError('Historical tree reconstruction changed the learned hypothesis')
    result = tree_metrics(tree)
    result.update(positive_rules=len(model.hypothesis.conjunctions),
                  literals=sum(len(c.attribute_confs) for c in model.hypothesis.conjunctions))
    return result


def run_model(name, case, depth_candidates, repeats):
    if name == 'majority':
        positive = sum(row['target'] for row in case['train']) >= len(case['train']) / 2
        return {'status': 'passed', 'validation': metrics([positive] * len(case['validation']), case['validation']),
                'test': metrics([positive] * len(case['test']), case['test']),
                'test_predictions': [int(positive)] * len(case['test']),
                'complexity': {'depth': 0, 'nodes': 1, 'leaves': 1, 'positive_rules': int(positive), 'literals': 0},
                'fit_ms': 0.0, 'fit_repeats_ms': [], 'tuning_ms': 0.0, 'selected_depth': 0,
                'prediction_ms': 0.0, 'rules': str(positive)}
    depth = None
    search = []
    tuning_start = time.perf_counter()
    if name == 'gain-depth-tuned':
        for value in depth_candidates:
            current_depth = case['attributes'] if value == 'unlimited' else value
            model = create_model(name, case, current_depth)
            model.fit()
            score = metrics(model.predict_all(Dataset(case['validation'], attr_values=case['domains'])), case['validation'])
            complexity = inspect_model(model)
            search.append({'max_depth': current_depth, 'balanced_accuracy': score['balanced_accuracy'],
                           'nodes': complexity['nodes'], 'depth': complexity['depth']})
        chosen = max(search, key=lambda item: (item['balanced_accuracy'], -item['nodes'], -item['depth']))
        depth = chosen['max_depth']
    tuning_ms = (time.perf_counter() - tuning_start) * 1000 if search else 0.0
    times = []
    for _ in range(repeats):
        model = create_model(name, case, depth)
        started = time.perf_counter()
        model.fit()
        times.append((time.perf_counter() - started) * 1000)
    val = model.predict_all(Dataset(case['validation'], attr_values=case['domains']))
    started = time.perf_counter()
    predictions = model.predict_all(Dataset(case['test'], attr_values=case['domains']))
    prediction_ms = (time.perf_counter() - started) * 1000
    return {'status': 'passed', 'validation': metrics(val, case['validation']),
            'test': metrics(predictions, case['test']), 'test_predictions': [int(p) for p in predictions],
            'complexity': inspect_model(model), 'fit_ms': statistics.median(times),
            'fit_repeats_ms': times, 'tuning_ms': tuning_ms, 'prediction_ms': prediction_ms,
            'selected_depth': depth, 'validation_search': search, 'rules': repr(model.hypothesis)}


def summarize(records, algorithms):
    result = {}
    for name in algorithms:
        rows = [(record, record['models'][name]) for record in records if record['models'][name]['status'] == 'passed']
        if not rows:
            result[name] = {'completed_cases': 0}
            continue
        summary = {'completed_cases': len(rows), 'failed_cases': len(records) - len(rows)}
        for split in ['validation', 'test']:
            summary[split] = {key: statistics.mean(row[split][key] for _, row in rows)
                              for key in ['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1']}
        summary['mean_nodes'] = statistics.mean(row['complexity']['nodes'] for _, row in rows)
        summary['mean_depth'] = statistics.mean(row['complexity']['depth'] for _, row in rows)
        summary['median_fit_ms'] = statistics.median(row['fit_ms'] for _, row in rows)
        summary['median_prediction_ms'] = statistics.median(row['prediction_ms'] for _, row in rows)
        summary['mean_tuning_ms'] = statistics.mean(row['tuning_ms'] for _, row in rows)
        by_family = {}
        for family in sorted(set(record['family'] for record, _ in rows)):
            values = [row for record, row in rows if record['family'] == family]
            by_family[family] = {key: statistics.mean(row['test'][key] for row in values)
                                 for key in ['accuracy', 'balanced_accuracy', 'f1']}
        summary['test_by_family'] = by_family
        paired = defaultdict(list)
        for record, row in rows:
            baseline = record['models']['my-dtl']
            if baseline['status'] == 'passed':
                paired[record['seed']].append(row['test']['balanced_accuracy'] - baseline['test']['balanced_accuracy'])
        seed_differences = [statistics.mean(values) for _, values in sorted(paired.items())]
        if len(seed_differences) >= 2:
            from scipy.stats import t
            mean = statistics.mean(seed_differences)
            half_width = float(t.ppf(0.975, len(seed_differences) - 1)) * statistics.stdev(seed_differences) / math.sqrt(len(seed_differences))
            summary['paired_test_difference_vs_initial_my_dtl'] = {
                'unit': 'seed-level mean balanced-accuracy difference across all fixed conditions',
                'seeds': len(seed_differences), 'mean': mean, 'ci95': [mean - half_width, mean + half_width],
                'seed_differences': seed_differences}
        result[name] = summary
    return result


def execute(plan, phase, output, limit=None):
    validate_plan(plan)
    if limit is not None and limit < 1:
        raise ValueError('limit must be positive')
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing to overwrite an existing result; choose a new output path')
    dimensions = plan[phase]
    specifications = list(itertools.product(dimensions['seeds'], dimensions['attributes'], plan['families'], dimensions['noise']))
    if limit is not None:
        specifications = specifications[:limit]
    records = []
    adoption = None
    adoption_path = PROJECT / 'configs/adoption.json'
    if phase == 'evaluation':
        if not adoption_path.is_file():
            raise ValueError('Freeze configs/adoption.json from development results before evaluation')
        adoption = json.loads(adoption_path.read_text(encoding='utf-8'))
        if adoption.get('plan_sha256') != digest(plan):
            raise ValueError('Frozen adoption record does not match the benchmark plan')
        if adoption.get('attribute_source_sha256') != hashlib.sha256((PROJECT / 'learning/attr_learner.py').read_bytes()).hexdigest():
            raise ValueError('Attribute implementation changed after the adoption record was frozen')
    started = time.perf_counter()
    for index, (seed, attributes, family, noise) in enumerate(specifications):
        case = make_case(family, attributes, noise, seed, plan['train_fraction'], plan['validation_fraction'])
        record = {key: value for key, value in case.items() if key not in ['train', 'validation', 'test', 'domains']}
        record['counts'] = {key: len(case[key]) for key in ['train', 'validation', 'test']}
        record['test_labels'] = [int(row['target']) for row in case['test']]
        order = list(plan['algorithms'])
        random.Random(seed * 1009 + index).shuffle(order)
        record['timing_order'] = order
        record['models'] = {}
        for name in order:
            try:
                record['models'][name] = run_model(name, case, plan['depth_candidates'], plan['timing_repeats'])
            except Exception as exc:
                record['models'][name] = {'status': 'failed', 'error_type': type(exc).__name__, 'message': str(exc)}
        if case['data_sha256'] != digest({key: case[key] for key in ['train', 'validation', 'test']}):
            raise RuntimeError('An algorithm mutated shared benchmark data')
        records.append(record)
        print(f'{phase}: {index + 1}/{len(specifications)} {case["id"]}', flush=True)
    failures = sum(row['status'] != 'passed' for record in records for row in record['models'].values())
    result = {'schema_version': 1, 'plan_id': plan['plan_id'], 'phase': phase,
              'status': 'passed' if not failures else 'completed_with_failures',
              'plan_sha256': digest(plan), 'partial_run': limit is not None,
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'environment': {'python': platform.python_version(), 'os': platform.system(), 'machine': platform.machine()},
              'source_sha256': {str(path.relative_to(PROJECT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in [PROJECT / 'learning/attr_learner.py', Path(__file__)]},
              'case_count': len(records), 'model_runs': len(records) * len(plan['algorithms']),
              'adoption_sha256': hashlib.sha256(adoption_path.read_bytes()).hexdigest() if adoption else None,
              'model_failures': failures, 'elapsed_seconds': time.perf_counter() - started,
              'metric_scope': 'Unweighted mean across fixed concept/noise/size cases. Timing is local Python CPU fit time; validation search is reported separately. Intervals use seed-level paired differences, not individual predictions as independent runs.',
              'summary': summarize(records, plan['algorithms']), 'cases': records}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'cases': len(records), 'model_failures': failures,
                      'elapsed_seconds': result['elapsed_seconds']}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=PROJECT / 'configs/benchmark-plan.json')
    parser.add_argument('--phase', choices=['development', 'evaluation'], default='development')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, help='Small diagnostic run, explicitly marked partial in the output')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    try:
        result = execute(plan, args.phase, args.output, args.limit)
    except ValueError as exc:
        parser.error(str(exc))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())

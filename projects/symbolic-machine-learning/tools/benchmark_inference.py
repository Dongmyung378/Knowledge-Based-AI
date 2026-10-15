"""Compare two equivalent execution paths of the same learned decision tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'tools'))
from benchmark_attributes import make_case, create_model, metrics  # noqa: E402


def run(output, phase):
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new result path; existing reports are not overwritten')
    seeds = [0, 1, 2] if phase == 'development' else [100, 101, 102]
    records = []
    for seed in seeds:
        for family in ['conjunction', 'sparse_dnf', 'xor', 'random_truth']:
            case = make_case(family, 10, 0.15, seed)
            candidates = []
            for depth in [2, 4, 6, 10]:
                model = create_model('gain-depth-tuned', case, depth)
                model.fit()
                score = metrics([model.predict(row) for row in case['validation']], case['validation'])
                candidates.append((score['balanced_accuracy'], -model.tree_metrics()['nodes'], -model.tree_metrics()['depth'], model))
            model = max(candidates, key=lambda item: item[:3])[3]
            # Include every valid Boolean input, not only the held-out test split.
            rows = case['train'] + case['validation'] + case['test']
            dnfs = [bool(model.hypothesis(row)) for row in rows]
            tree_predictions = [bool(model.predict_tree(row)) for row in rows]
            if dnfs != tree_predictions:
                raise RuntimeError('The tree traversal changed at least one prediction')
            timings = {'dnf': [], 'tree': []}
            functions = {'dnf': model.hypothesis, 'tree': model.predict_tree}
            for repetition in range(8):
                order = ['dnf', 'tree'] if repetition % 2 == 0 else ['tree', 'dnf']
                for mode in order:
                    start = time.perf_counter()
                    result = [bool(functions[mode](row)) for row in rows]
                    elapsed = (time.perf_counter() - start) * 1000
                    if result != dnfs:
                        raise RuntimeError('Repeated inference changed predictions')
                    if repetition:
                        timings[mode].append(elapsed)
            dnf_ms, tree_ms = (statistics.median(timings[key]) for key in ['dnf', 'tree'])
            records.append({'id': case['id'], 'data_sha256': case['data_sha256'],
                            'predictions_checked': len(rows), 'all_predictions_equal': True,
                            'complexity': model.tree_metrics(), 'timings_ms': timings,
                            'dnf_median_ms': dnf_ms, 'tree_median_ms': tree_ms,
                            'speedup': dnf_ms / tree_ms, 'time_reduction': 1 - tree_ms / dnf_ms})
            print(f'{phase}: inference {len(records)}/12 {family} seed={seed}', flush=True)
    result = {'schema_version': 1, 'status': 'passed', 'phase': phase,
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'configuration': {'attributes': 10, 'noise': 0.15, 'seeds': seeds,
                                'warmup_passes': 1, 'measured_passes': 7, 'model': 'gain-depth-tuned',
                                'depth_candidates': [2, 4, 6, 10]},
              'scope': 'Same learned model and complete valid Boolean input space. Both paths validate input schema. Timing is local Python CPU batch inference, not model-training acceleration.',
              'case_count': len(records), 'equivalence_checks': sum(row['predictions_checked'] for row in records),
              'median_case_speedup': statistics.median(row['speedup'] for row in records),
              'median_case_time_reduction': statistics.median(row['time_reduction'] for row in records),
              'source_sha256': {str(path.relative_to(PROJECT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in [PROJECT / 'learning/attr_learner.py', Path(__file__)]},
              'cases': records}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ['status', 'case_count', 'equivalence_checks', 'median_case_speedup', 'median_case_time_reduction']}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['development', 'evaluation'], default='development')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output, args.phase)

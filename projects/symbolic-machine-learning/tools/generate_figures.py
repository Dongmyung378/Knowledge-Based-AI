"""Render bilingual portfolio figures directly from the published raw reports."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

INK, AMBER, SLATE, RED, CREAM = '#29283F', '#A66A13', '#6B7C91', '#A74648', '#F7F3EA'
COLORS = ['#B7AF9C', SLATE, RED, '#A39CAF', '#827995', '#6D637F', '#5B516E', AMBER, '#3F6374']
LABELS = {
    'en': ['Majority', 'Initial DTL', 'Initial my-dtl', 'Corrected DTL', 'Gain ratio', 'Depth limit', 'Gain + depth', 'Selected depth policy', 'Validation pruning'],
    'ko': ['다수결', '초기 DTL', '초기 my-dtl', '수정 DTL', '이득비', '깊이 제한', '이득비와 깊이 제한', '검증셋으로 깊이 선택', '검증 기반 가지치기'],
}


def configure(language):
    names = {font.name for font in font_manager.fontManager.ttflist}
    candidates = ['Malgun Gothic', 'Noto Sans CJK KR', 'NanumGothic', 'Arial Unicode MS'] if language == 'ko' else ['DejaVu Sans']
    font = next((name for name in candidates if name in names), None)
    if font is None:
        raise RuntimeError('Install a Korean font such as Noto Sans CJK KR before rendering Korean figures')
    plt.rcParams.update({'font.family': font, 'font.size': 10, 'axes.labelcolor': INK,
                         'text.color': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'axes.edgecolor': '#B3AB9C', 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.facecolor': CREAM,
                         'figure.facecolor': CREAM, 'svg.fonttype': 'path',
                         'svg.hashsalt': 'symbolic-learning-controlled-v1', 'axes.unicode_minus': False})


def save(figure, language, name):
    folder = PROJECT / 'figures' / language
    folder.mkdir(parents=True, exist_ok=True)
    svg = folder / f'{name}.svg'
    figure.savefig(svg, bbox_inches='tight', metadata={'Date': None, 'Creator': 'Symbolic learning report renderer'})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n',
                   encoding='utf-8', newline='\n')
    figure.savefig(folder / f'{name}.png', bbox_inches='tight', dpi=160, metadata={'Software': 'Symbolic learning report renderer'})
    plt.close(figure)


def explanation():
    from learning.attr_learner import GainDepthTreeLearner, Leaf
    from learning.util import Dataset
    rows = [dict(zip(['A', 'B', 'C'], values)) for values in itertools.product([False, True], repeat=3)]
    for row in rows:
        row['target'] = (row['A'] and row['B']) or row['C']
    model = GainDepthTreeLearner(Dataset(rows), max_depth=3)
    model.fit()

    def encode(tree):
        if isinstance(tree, Leaf):
            return {'prediction': tree.target}
        return {'attribute': tree.attr_name, 'branches': {str(value).lower(): encode(child) for value, child in tree.branches.items()}}

    value = {'schema_version': 1, 'purpose': 'Explanatory demonstration fitted to all eight Boolean inputs; not a held-out performance measurement.',
             'concept': '(A AND B) OR C', 'algorithm': 'gain-depth', 'max_depth': 3,
             'training_rows': rows, 'tree': encode(model.tree_), 'dnf': repr(model.hypothesis),
             'logic_terms': [dict(conjunction.attribute_confs) for conjunction in model.hypothesis.conjunctions],
             'complexity': model.tree_metrics(),
             'examples': [{'input': {key: row[key] for key in ['A', 'B', 'C']}, **model.trace(row)} for row in rows]}
    folder = PROJECT / 'examples'
    folder.mkdir(exist_ok=True)
    (folder / 'explanation.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    return value


def render_accuracy(report, language):
    names = list(report['summary'])
    values = [report['summary'][name]['test']['balanced_accuracy'] * 100 for name in names]
    fig, ax = plt.subplots(figsize=(10, 5.6), layout='constrained')
    bars = ax.barh(LABELS[language], values, color=COLORS, height=0.65)
    ax.invert_yaxis()
    ax.set_xlim(0, 103)
    ax.set_xlabel('평균 균형 정확도 (%)' if language == 'ko' else 'Mean balanced accuracy (%)')
    ax.set_title('동일한 240개 조건에서 비교한 9개 정책' if language == 'ko' else 'Nine policies on the same 240 held-out conditions', loc='left', fontweight='bold', pad=14)
    ax.grid(axis='x', alpha=0.18)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, values):
        ax.text(value + 1, bar.get_y() + bar.get_height() / 2, f'{value:.2f}', va='center', fontsize=10)
    note = '4개 개념 유형과 잡음 3수준, 속성 2규모, 평가 시드 10개. 대표 정책은 개발 데이터로 사전 선정했습니다.' if language == 'ko' else '4 concept families x 3 noise levels x 2 sizes x 10 evaluation seeds. Policy selected before final evaluation.'
    fig.supxlabel(note, fontsize=8)
    save(fig, language, 'symbolic-accuracy')


def render_complexity(report, inference, language):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7), layout='constrained')
    selected = [('my-dtl', RED, '초기 my-dtl', 'Initial my-dtl'), ('dtl', SLATE, '초기 DTL', 'Initial DTL'),
                ('gain-depth-tuned', AMBER, '깊이 선택', 'Depth selection'), ('pruned-dtl', '#3F6374', '가지치기', 'Pruning')]
    for name, color, ko, en in selected:
        item = report['summary'][name]
        x, y = item['mean_nodes'], item['test']['balanced_accuracy'] * 100
        axes[0].scatter(x, y, s=105, color=color, zorder=3)
        axes[0].annotate(ko if language == 'ko' else en, (x, y), xytext=(7, 4), textcoords='offset points', fontsize=9)
    axes[0].set(xlabel='평균 전체 노드 수' if language == 'ko' else 'Mean total tree nodes',
                ylabel='평균 균형 정확도 (%)' if language == 'ko' else 'Mean balanced accuracy (%)',
                xlim=(0, 380), ylim=(60, 83))
    axes[0].set_title('정확도와 트리 크기의 절충' if language == 'ko' else 'Accuracy and tree size', loc='left', fontweight='bold')
    axes[0].grid(alpha=0.16)
    dnf = [row['dnf_median_ms'] for row in inference['cases']]
    tree = [row['tree_median_ms'] for row in inference['cases']]
    for first, second in zip(dnf, tree):
        axes[1].plot([0, 1], [first, second], color=SLATE, alpha=0.35, linewidth=1)
    axes[1].scatter([0] * len(dnf), dnf, color=SLATE, s=35)
    axes[1].scatter([1] * len(tree), tree, color=AMBER, s=35)
    axes[1].set_xticks([0, 1], ['논리식 실행', '트리 경로 실행'] if language == 'ko' else ['DNF evaluation', 'Tree traversal'])
    axes[1].set_xlim(-0.25, 1.25)
    axes[1].set_ylabel('1,024개 입력의 배치 시간 (ms)' if language == 'ko' else 'Batch time for 1,024 inputs (ms)')
    axes[1].set_title('동일한 모델의 두 실행 경로' if language == 'ko' else 'Two paths of the same learned model', loc='left', fontweight='bold')
    reduction = inference['median_case_time_reduction'] * 100
    fig.supxlabel((f'12개 모델의 전체 입력 12,288개 예측 일치. 조건별 배치 시간 감소율 중앙값 {reduction:.2f}%.' if language == 'ko'
                   else f'12,288 predictions agree across 12 models. Median per-case batch-time reduction: {reduction:.2f}%.'), fontsize=8)
    save(fig, language, 'symbolic-complexity')


def render_foil(greedy, lookahead, language):
    fig, ax = plt.subplots(figsize=(10, 4.8), layout='constrained')
    labels = ['기본 탐색', '제한된 2단계 탐색'] if language == 'ko' else ['Greedy search', 'Bounded two-literal lookahead']
    descriptions = {'completed': ('학습 완료', 'Completed', AMBER), 'search_failed': ('탐색 실패', 'Search failed', RED), 'budget_exceeded': ('예산 초과', 'Budget exceeded', SLATE)}
    for row_index, report in enumerate([greedy, lookahead]):
        left = 0
        for status, (ko, en, color) in descriptions.items():
            count = report['summary']['status_counts'].get(status, 0)
            if count:
                ax.barh(row_index, count, left=left, color=color, height=0.55,
                        label=(ko if language == 'ko' else en) if row_index == 0 else None)
                ax.text(left + count / 2, row_index, str(count), ha='center', va='center', color='white', fontweight='bold')
                left += count
    ax.set_yticks([0, 1], labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 30)
    ax.set_xticks(range(0, 31, 5))
    ax.set_xlabel('사전에 정한 그래프 조건 수' if language == 'ko' else 'Number of predeclared graph cases')
    ax.set_title('실패와 시간 제한을 포함한 전체 30개 조건' if language == 'ko' else 'All 30 cases, including search failures and time limits', loc='left', fontweight='bold', pad=15)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
    fig.supxlabel('알려진 그래프의 관계 쌍 홀드아웃. 새로운 그래프로의 전이 성능을 뜻하지 않습니다.' if language == 'ko'
                  else 'Relation-pair holdout within known graphs; this does not measure transfer to unseen graphs.', fontsize=8)
    save(fig, language, 'symbolic-foil')


def render_rules(demo, language):
    fig, ax = plt.subplots(figsize=(10, 4.6), layout='constrained')
    ax.axis('off')
    positions = {}
    edges = []
    leaves = []

    def place(node, depth, low, high, key='root'):
        if 'prediction' in node:
            x = (low + high) / 2
            leaves.append((key, node, x, depth))
        else:
            middle = (low + high) / 2
            place(node['branches']['false'], depth + 1, low, middle, key + 'f')
            place(node['branches']['true'], depth + 1, middle, high, key + 't')
            x = middle
            edges.extend([(key, key + 'f', 'False'), (key, key + 't', 'True')])
        positions[key] = (x, depth, node)

    place(demo['tree'], 0, 0, 1)
    for parent, child, label in edges:
        x1, y1, _ = positions[parent]
        x2, y2, _ = positions[child]
        ax.plot([x1, x2], [-y1, -y2], color=SLATE, linewidth=1.4)
        display_label = {'False': '거짓', 'True': '참'}[label] if language == 'ko' else label
        ax.text((x1 + x2) / 2, -(y1 + y2) / 2 + 0.03, display_label, ha='center', fontsize=8,
                bbox={'facecolor': CREAM, 'edgecolor': 'none', 'pad': 1.5})
    for _, (x, depth, node) in positions.items():
        leaf = 'prediction' in node
        text = ('참' if node['prediction'] else '거짓') if leaf and language == 'ko' else str(node['prediction']).upper() if leaf else node['attribute']
        ax.text(x, -depth, text, ha='center', va='center', color='white' if leaf else INK,
                bbox={'boxstyle': 'round,pad=0.55', 'facecolor': AMBER if leaf else '#E5DFD1', 'edgecolor': 'none'}, zorder=4)
    ax.set_xlim(-0.04, 1.04)
    ax.set_ylim(-3.6, 0.8)
    ax.set_title('학습한 트리와 논리식으로 같은 판단 설명' if language == 'ko' else 'One learned decision expressed as a tree and a rule', loc='left', fontweight='bold')
    fig.supxlabel('(A AND B) OR C: 8개 전체 입력으로 학습한 설명용 예제이며 성능 평가가 아닙니다.' if language == 'ko'
                  else '(A AND B) OR C: explanatory fit on all 8 inputs, not a held-out performance result.', fontsize=8)
    save(fig, language, 'symbolic-rules')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', choices=['en', 'ko', 'both'], default='both')
    parser.add_argument('--only-rules', action='store_true',
                        help='Render the saved explanatory model only; leave raw reports and the saved model unchanged.')
    args = parser.parse_args()
    languages = ['en', 'ko'] if args.language == 'both' else [args.language]
    if args.only_rules:
        source = PROJECT / 'examples/explanation.json'
        demo = json.loads(source.read_text(encoding='utf-8'))
        for language in languages:
            configure(language)
            render_rules(demo, language)
        provenance = {'scope': 'Localized rule labels from the unchanged saved explanatory model; no training or benchmark rerun.',
                      'source_model_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                      'renderer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'files': {f'figures/{language}/symbolic-rules.{suffix}': hashlib.sha256((PROJECT / f'figures/{language}/symbolic-rules.{suffix}').read_bytes()).hexdigest()
                                for language in languages for suffix in ['svg', 'png']}}
        (PROJECT / 'figures/rules-localization.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps({'status': 'passed', 'languages': languages, 'only_rules': True}))
        return
    filenames = ['attribute-evaluation.json', 'inference-evaluation.json', 'foil-final-greedy.json', 'foil-final-lookahead.json']
    reports = [json.loads((PROJECT / 'reports' / name).read_text(encoding='utf-8')) for name in filenames]
    demo = explanation()
    for language in languages:
        configure(language)
        render_accuracy(reports[0], language)
        render_complexity(reports[0], reports[1], language)
        render_foil(reports[2], reports[3], language)
        render_rules(demo, language)
    provenance = {'schema_version': 1,
                  'inputs': {f'reports/{name}': hashlib.sha256((PROJECT / 'reports' / name).read_bytes()).hexdigest() for name in filenames},
                  'renderer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'scope': 'Every numerical chart is generated from raw reports. The small rule illustration uses an actual fitted explanatory model and is not a held-out result.'}
    (PROJECT / 'figures/provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'passed', 'languages': len(languages),
                      'svg_figures': 4 * len(languages), 'png_figures': 4 * len(languages)}))


if __name__ == '__main__':
    main()

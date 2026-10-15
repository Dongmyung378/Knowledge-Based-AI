# 기호 머신러닝

[English](README.md) | [한국어](README.ko.md) | [포트폴리오 홈](../../README.ko.md)

속성 예제를 읽을 수 있는 논리식으로 바꾸는 결정 트리 학습기와, 양성 및 음성 예제와 Prolog 배경 지식에서 관계 규칙을 찾는 FOIL 학습기를 구현한 프로젝트입니다.

최초 개발 기간은 **2025년 2월~5월**입니다. 개선 배포본은 초기 알고리즘과 실험을 보존하면서 정확한 경로별 깊이 제한과 검증 기반 가지치기를 추가했습니다. 모델 선택과 최종 평가를 분리하고 관계 학습의 탐색 및 질의 실패도 명시적으로 처리합니다.

## 보여 주는 역량

- 엔트로피와 정보 이득, 이득비 및 트리의 논리식 변환 구현
- 실제 경로 깊이와 검증 기반 가지치기를 통한 모델 복잡도 조절
- FOIL 후보 생성과 관계 예제 확장, 규칙 귀납 및 유한 그래프의 재귀 추론
- 동일 입력을 적용한 비교와 홀드아웃 평가, 개별 예측 경로 분석
- 런타임 진단과 소스 무결성 검사, 초기 근거 보존

초기 과제에서 코드 골격과 데이터 생성 도구, 평가 도구 및 공개 테스트를 제공했습니다. 직접 구현한 학습 로직과 이후 보완을 제공 자료와 구분하며, 원본 과제 및 강의 PDF는 [`references/`](references/)에 보존합니다.

## 학습 방식

| 등록명 | 분기 기준 | 성장 제어 | 비교 목적 |
| --- | --- | --- | --- |
| `dtl` | 정보 이득 | 초기 구현 | 초기 비교 기준 보존 |
| `my-dtl` | 이득비 | 초기 공유 후위 순회 카운터 | 초기 변형 보존 |
| `corrected-dtl` | 정보 이득 | 기본값은 제한 없음 | 입력 검사와 결정적 분기를 적용한 개선 기준 |
| `gain-ratio` | 이득비 | 기본값은 제한 없음 | 분기 기준의 효과 분리 |
| `depth-limited` | 정보 이득 | 실제 경로 깊이 | 깊이 제어의 효과 분리 |
| `gain-depth` | 이득비 | 실제 경로 깊이 | 두 변경의 결합 |
| `pruned-dtl` | 정보 이득 | 검증 기반 가지치기 | 학습 후 복잡도 축소 비교 |
| `foil` | FOIL 정보 이득 | 탐색 및 질의 예산 | 관계를 설명하는 Horn 절 학습 |

`my-dtl`은 초기 공유 카운터의 동작을 유지합니다. 이를 실제 경로별 깊이 제한으로 이름만 바꾸지 않고 수정한 변형을 별도로 등록했습니다. [`experiment-report.ko.md`](docs/experiment-report.ko.md)는 수정하지 않은 과거 기록이며, 그 문서의 ‘현재 구현’이라는 표현은 당시 스냅샷을 가리킵니다.

## 빠른 시작

Python 3.12와 함께 **Windows에서는 SWI-Prolog 9.2.9 x64**, **Ubuntu 24.04에서는 시스템 패키지 9.0.4**를 사용합니다. PySwip이 SWI-Prolog를 찾을 수 있어야 하며 `pip`만으로 Prolog 런타임이 설치되지는 않습니다. 고정한 PySwip 소스 의존성 설치에는 Git이 필요합니다. [재현 문서](docs/reproduce.ko.md)에 정확한 Windows 설치 파일과 해시를 안내합니다.

```bash
cd projects/symbolic-machine-learning
python -m venv .venv
```

Linux와 WSL에서는 `source .venv/bin/activate`, Windows PowerShell에서는 `.\.venv\Scripts\Activate.ps1`로 활성화한 뒤 실행합니다.

```bash
python -m pip install -r requirements.lock.txt
python tools/run_checks.py --output-dir outputs/verification
```

고정 목록은 PySwip 커밋 `c07e8083c6a58eb7de99bb26c8dc89a0c215f52c`과 설치한 Python 의존성 버전을 지정합니다. 환경 진단은 별도 프로세스에서 실제 Prolog 질의를 수행하고, 런타임을 불러오지 못하면 원인에 맞는 안내와 함께 실패 코드를 반환합니다. Linux와 Windows의 런타임 연결은 [설치와 재현](docs/reproduce.ko.md)을 참고하세요.

통합 검증 명령은 배포 파일과 환경을 확인하고 pytest 및 두 학습 경로의 고정 예제를 실행하며 네이티브 프로세스 종료도 검사합니다. 출력은 새 폴더 또는 빈 폴더로 지정하며 기존 근거를 덮어쓰지 않습니다.

## 실행 경로

초기 명령행 인터페이스를 유지합니다.

```bash
python evaluate_attributes.py eval-size -a dtl -a my-dtl -s 4 -d 2 -t 0.75
python evaluate_rules.py -a foil -d tests/graph_small.json -k tests/graph_small.pl -t "reachable(X,Y)" -r -e 0.8
```

개선한 속성 CLI는 평가 절차를 바로잡았습니다. `eval-noisy`는 독립적인 깨끗한 평가셋을 두고 학습 정답에만 잡음을 적용하며, 알고리즘과 잡음 수준 사이에서 개념 및 분할을 공유합니다. `eval-time`은 미리 생성한 동일 입력을 사용하고 실행 순서를 순환합니다. 초기 보고서의 절차를 재현하려면 현재 CLI 대신 보존한 스냅샷을 사용합니다. `pruned-dtl`은 별도 검증셋이 필요하므로 간단한 속성 명령 대신 통제 벤치마크에서 지원합니다.

개선 비교는 저장한 계획과 개발 및 최종 평가 단계로 구성합니다.

```bash
python tools/benchmark_attributes.py --plan configs/benchmark-plan.json --phase development --output outputs/attribute-development.json
python tools/benchmark_attributes.py --plan configs/benchmark-plan.json --phase evaluation --output outputs/attribute-evaluation.json
python tools/benchmark_foil.py --lookahead 2 --seed-start 200 --output outputs/foil-final-lookahead.json
```

같은 조건의 알고리즘에는 동일한 개념과 예제, 데이터 분할과 학습 정답의 잡음 위치를 적용합니다. 최종 평가 예측을 살펴보기 전에 검증 데이터에서 복잡도를 선택합니다. 시드와 예측값, 모델 크기와 측정 시간을 남겨 집계 정확도만으로는 설명하기 어려운 차이도 확인합니다.

벤치마크는 등록한 트리 학습기 일곱 개에 다수 클래스 기준과 `gain-depth-tuned`를 추가해 아홉 조건을 비교합니다. `gain-depth-tuned`는 내부 검증으로 깊이를 선택하는 실험 정책입니다. 후보 정책은 별도의 개발 홀드아웃에서 비교하고, 서로 다른 최종 평가 시드를 실행하기 전에 고정합니다.

## 예측 근거 확인

[`demo/index.ko.html`](demo/index.ko.html)을 브라우저에서 직접 열면 오프라인으로 입력을 바꿔 볼 수 있습니다. A와 B 및 C를 선택하면 내보낸 학습 트리의 경로와 논리식의 계산 결과를 비교합니다. 이 모델은 설명을 위해 입력 여덟 개 전체를 학습했으며 홀드아웃 점수가 아닙니다. `python tools/build_demo.py`로 두 언어의 페이지를 다시 생성합니다.

개선한 트리 변형은 `tree_`, `tree_metrics()` 및 `trace(example)`를 제공합니다. 깊이는 간선 수이며 루트가 리프면 0입니다. 노드와 리프 수, 양성 규칙 수와 조건 수도 측정합니다. 분기 경로는 개별 입력의 판단 과정을 보여줍니다. 개선한 변형에서 예측에 필요한 특성이 빠졌거나 학습에서 보지 못한 범주를 받으면 명확한 오류로 안내합니다.

FOIL은 지식 베이스와 목표 규칙을 정리하기 전, 문맥 관리자 내부에서 예측합니다.

```python
with FOIL(dataset=dataset, recursive=True) as learner:
    learner.fit()
    print(learner.hypothesis)
    print(learner.predict_with_trace(example))
```

예측 설명은 일치한 학습 규칙과 입력 바인딩을 제공하며 Prolog의 완전한 증명 트리는 아닙니다. 후보 소진과 예산 초과, 질의 오류 및 정리 오류를 구분합니다. 세부 사항은 [구조와 지원 범위](docs/architecture.ko.md)에 정리했습니다.

## 결과와 초기 기록

<span id="실제-기본-실험-검증-2026-10-05"></span>

| 개선 평가 | 결과 |
| --- | --- |
| 사전 대표의 균형 정확도 | **76.25%**, 초기 `my-dtl` **64.08%**, **12.17%p 상승** |
| 아홉 비교 조건 | **240개 조건**, **모델 평가 2,160회**, 모델 실패 0회 |
| 최종 균형 정확도 최고 | `pruned-dtl` **77.81%**, 사전 대표를 변경하지 않고 선택 구현으로 유지 |
| 논리식과 트리의 같은 예측 | **12,288/12,288개 일치**, 조건별 배치 시간 감소율 중앙값 **68.31%** |
| FOIL 학습 완료 | 기본 탐색 **20/30개**, 선택 가능한 두 단계 탐색 **26/30개** |
| 소스 ZIP 검증 | Windows와 Linux **5/5단계**, Windows **151개 통과와 2개 건너뜀**, Linux **153개 통과** |

아홉 조건 전체와 복잡도 및 깊이 선택 비용, 시드별 구간과 FOIL의 예산 초과는 [개선 실험 전체 결과](docs/results.ko.md)에서 공개합니다. 대표는 최종 평가 전에 개발 데이터로 고정했습니다. 초기 실험의 시간 단축을 새 모델의 속도 개선으로 재사용하지 않습니다.

![아홉 조건의 홀드아웃 균형 정확도 비교](figures/ko/symbolic-accuracy.svg)

초기 과제는 세 조건에서 **학습 시간 44~80% 감소**, 한 극단적 잡음 조건에서 **정확도 19.1%p 상승**을 기록했으나 다른 조건에서는 정확도가 크게 낮아졌습니다. 당시에는 공유 카운터 변형을 사용했고 잡음 평가에 학습한 예제가 포함됐으므로 이 수치를 새로운 홀드아웃 일반화 성능으로 제시하지 않습니다.

**2026-10-05의 초기 기본 검증**에서는 Python 3.12.7과 SWI-Prolog 9.2.9로 테스트 30개가 통과했습니다. 속성 홀드아웃 4/4개와 그래프 양성 12/12개 및 음성 59/59개 예측도 완료했습니다. 이는 과거의 검증이며 이번 배포본에서 새로 수행한 실험과 구분합니다.

초기 코드와 테스트, 실험 문서 및 데이터 27개 파일은 [`legacy/initial-aa947038.zip`](legacy/initial-aa947038.zip)에 바이트 단위로 그대로 보존합니다. 기준 커밋은 `aa947038f923e98ec0bf16457745d538284ef45c`입니다. 원본 참고 PDF 세 개는 [`references/`](references/)에서 변경 없이 유지하고 스냅샷에 중복해서 담지 않았습니다. [`legacy/initial-provenance.json`](legacy/initial-provenance.json)에 초기 전체 30개 파일 목록과 공유 참고 자료의 해시를 기록합니다. 배포 매니페스트로 스냅샷과 PDF도 확인합니다. 현재 트리의 초기 실험 보고서와 원본 참고 파일도 변경하지 않습니다.

## 폴더 구조

```text
symbolic-machine-learning/
├── learning/               # 초기 학습기와 개선 변형
├── tests/                  # 회귀 검사와 그래프 예제
├── configs/                # 실험 계획
├── tools/                  # 벤치마크, 환경 진단과 배포 검사
├── docs/                   # 영어 기본 문서와 한국어 대응 문서
├── legacy/                 # 초기 프로젝트 스냅샷
├── references/             # 원본 과제와 강의 자료
├── requirements.lock.txt   # 고정한 Python 패키지 버전
└── release-manifest.json   # 배포 파일 해시와 초기 출처
```

## 문서와 한계

- [구조와 지원 범위](docs/architecture.ko.md)
- [개선 결과와 모든 비교 조건](docs/results.ko.md)
- [실행 환경과 네이티브 수명 검증](docs/validation.ko.md)
- [설치, 실험 실행과 배포 검증](docs/reproduce.ko.md)
- [초기 실험 보고서](docs/experiment-report.ko.md)
- [초기 평가 가이드](docs/evaluation-guide.ko.md)

지원하는 실행 범위는 생성 범주형 예제와 Prolog 사실을 사용하는 유한 관계 데이터입니다. 사용하지 않는 과제의 CSV 입출력 틀은 이 범위에 포함하지 않습니다. 합성 결과는 외부 실무 데이터에서의 성능을 입증하지 않으며 시간은 실행 환경에 영향을 받습니다. 테이블링과 예산은 통제한 유한 그래프 실험을 지원하지만 임의 Prolog 소스를 격리하거나 모든 프로그램의 종료를 보장하지는 않습니다.

Ubuntu GitHub Actions 설정에는 환경 진단과 배포 검사, 회귀 테스트 실행 경로를 제공합니다. 설정이 존재한다는 사실만으로 원격 CI가 통과했다고 설명하지 않습니다. 코드와 제공된 수업 자료에 새로운 라이선스를 부여하지 않습니다.

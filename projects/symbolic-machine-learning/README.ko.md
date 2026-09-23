# 기호 머신러닝

[English](README.md) | [한국어](README.ko.md) | [포트폴리오 홈](../../README.ko.md)

## 개요

설명 가능한 두 학습 시스템을 기초부터 구현한 프로젝트입니다.

1. 속성-값 데이터를 위한 결정 트리 학습기와 트리를 논리곱의 논리합으로 변환하는 기능
2. 양성·음성 예제와 Prolog 지식 베이스로부터 Horn 절을 귀납하는 FOIL 방식 학습기

데이터셋 생성기, 명령줄 평가 도구, 그래프 픽스처, 공개 테스트도 포함합니다.

## 기술적 핵심

### 결정 트리 학습

- 모든 타깃이 같은 경우, 다수결 대체, 빈 분할, 속성 소진을 처리합니다.
- 이진 엔트로피와 정보 이득을 계산해 분할 속성을 선택합니다.
- 양성 리프에 도달하는 루트 경로를 읽기 쉬운 논리식으로 변환합니다.
- 알고리즘을 이름으로 등록해 평가 스크립트가 구현을 일관되게 비교할 수 있습니다.

### 개선형 `my-dtl`

- 정보 이득을 분할 정보로 정규화하는 이득비를 사용합니다.
- 학습 데이터 크기에 따라 트리 깊이를 제한합니다.
- 일부 예측 정확도를 희생하는 대신 학습 시간을 줄이고 특정 고잡음 조건의 동작을 개선합니다.
- 성공한 결과와 실패한 결과를 모두 [실험 보고서](docs/experiment-report.ko.md)에 기록했습니다.

### FOIL 방식 규칙 학습

- Prolog 지식 베이스에서 사용할 수 있는 술어를 추출합니다.
- 일관된 변수 이름으로 후보 리터럴을 생성합니다.
- Prolog 치환으로 예제를 확장하고 FOIL 정보 이득으로 후보를 평가합니다.
- 별도의 covering·specialisation 루프로 Horn 절을 학습합니다.
- 그래프 도달 가능성과 같은 재귀 타깃 관계를 지원합니다.
- 학습기 종료 시 불러온 지식 베이스와 동적으로 학습한 타깃 술어를 해제해 Prolog 상태가 다음 실행으로 누수되지 않도록 합니다.

## 구조

```text
symbolic-machine-learning/
├── learning/
│   ├── attr_learner.py   # DTL, my-dtl, 엔트로피, 논리식 변환
│   ├── rule_learner.py   # FOIL, Horn 절 타입, Prolog 연동
│   ├── generate.py       # 합성 속성 데이터셋 생성기
│   └── util.py           # 데이터셋, 알고리즘 인터페이스, 레지스트리
├── tests/
│   ├── public/           # 속성 및 규칙 학습기 테스트
│   └── graph*            # 도달 가능성 데이터셋과 Prolog 사실
├── evaluate_attributes.py
├── evaluate_rules.py
├── generate_graphs.py
├── docs/
│   ├── experiment-report.md
│   └── evaluation-guide.md
└── references/           # 원본 명세와 강의 자료
```

## 설치

### 준비 사항

- Python 3
- `PATH`에서 실행할 수 있는 SWI-Prolog
- 로컬 의존성 설치에서 요구하는 경우 C/C++ 도구 체인

```bash
cd projects/symbolic-machine-learning
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell에서는 다음 명령으로 환경을 활성화합니다.

```powershell
.\.venv\Scripts\Activate.ps1
```

PySwip에서 설치된 SWI-Prolog 런타임을 찾을 수 있어야 합니다.

### Linux 또는 WSL용 독립 Conda 환경

다음 방법은 Python과 SWI-Prolog를 Git에서 제외되는 `.venv` 디렉터리에 함께 설치합니다.

```bash
conda create -p .venv -c conda-forge python=3.12 swi-prolog=9.2.9 pip -y
conda activate ./.venv
python -m pip install -r requirements.txt
```

## 테스트

```bash
python -m pytest
```

결정 트리 테스트만 실행:

```bash
python -m pytest tests/public/test_attr_learner.py
```

규칙 학습 테스트만 실행:

```bash
python -m pytest tests/public/test_rule_learner.py
```

일부 시스템에서는 PySwip 연동이 테스트 사이에 Prolog 상태를 유지할 수 있습니다. 규칙 학습 테스트가 불안정하면 개별 실행하세요.

## 평가 재현

잡음 데이터에서 결정 트리 변형 비교:

```bash
python evaluate_attributes.py eval-noisy -a dtl -a my-dtl -c 0.3 -c 0.5 -c 0.7 -s 10 -d 10
```

학습 시간 비교:

```bash
python evaluate_attributes.py eval-time -a dtl -a my-dtl -s 5 -s 7 -s 10
```

재귀 도달 가능성 관계 학습:

```bash
python evaluate_rules.py -a foil -d tests/graph_small.json -k tests/graph_small.pl -t "reachable(X,Y)" -r -e 0.8
```

전체 워크플로는 [평가 가이드](docs/evaluation-guide.ko.md)를 참고하세요.

## 결과와 한계

기록된 실험에서 `my-dtl`은 기준 구현보다 훨씬 빠르게 학습했고 한 극단적 잡음 조건에서 더 강건했습니다. 반면 여러 저잡음 및 제한된 데이터 조건에서는 성능이 낮았습니다. 이는 과제 당시 측정값이며 이번 포트폴리오 재구성 과정에서 다시 실행한 결과가 아닙니다. 전체 표, 명령, 해석, 타당성의 한계는 [실험 보고서](docs/experiment-report.ko.md)에 정리했습니다.

현재 `requirements.txt`는 PySwip의 업스트림 기본 브랜치에서 설치합니다. 완전히 재현 가능한 보관 환경이 필요하다면 검증한 릴리스 또는 커밋으로 고정하고 SWI-Prolog 버전도 기록해야 합니다.

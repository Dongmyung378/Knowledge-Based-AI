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

- Python 3.12 권장 (검증 환경은 3.12.7 사용)
- `PATH`에서 실행할 수 있는 SWI-Prolog
- 고정한 PySwip 소스 의존성을 설치하는 데 필요한 Git
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

PySwip에서 설치된 SWI-Prolog 런타임을 찾을 수 있어야 합니다. Windows에서 설치 등록
없이 압축 해제한 런타임을 사용한다면 `SWI_HOME_DIR`은 런타임 루트로, `LIBSWIPL_PATH`는
`bin/libswipl.dll`의 절대 경로로 설정하고 Python을 실행할 프로세스의 `PATH`에 `bin`
디렉터리를 추가합니다. 이 경로는 각 컴퓨터에만 적용하며 저장소에 커밋하지 않습니다.

### Ubuntu 또는 Debian 시스템 런타임

SWI-Prolog와 Python 가상환경 지원을 설치한 뒤 `projects/symbolic-machine-learning`에서
위의 표준 `venv` 설정을 실행합니다.

```bash
sudo apt-get update
sudo apt-get install -y swi-prolog python3-venv
python3 --version
swipl --version
```

아래 검증 버전 조합에는 Python 3.12 환경을 사용하세요. 이전 시스템 Python에서는
다른 의존성 버전이 설치될 수 있습니다. Conda 대안은 명시한 Python과 SWI-Prolog
버전을 함께 준비합니다.

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

회귀 테스트는 FOIL 정리 전에 학습·예측을 수행하는지와 같은 프로세스에서 서로 다른
지식 베이스를 순서대로 불러오는지 확인합니다. 학습기를 직접 사용할 때는 예측도
`with FOIL(...)` 안에서 수행합니다. 이 문맥을 벗어나면 학습한 target과 지식 베이스가
정리됩니다. 런타임 문제가 발생하면 Python·PySwip·SWI-Prolog 버전을 기록하세요.

## 평가 재현

의존성을 설치한 뒤 이 디렉터리에서 실행합니다. 작은 결정 트리 실험은 Boolean 예제
16개를 생성하고 75%로 두 학습기를 학습한 뒤 나머지 예제의 정확도를 출력합니다.

```bash
python evaluate_attributes.py eval-size -a dtl -a my-dtl -s 4 -d 2 -t 0.75
```

기본 seed는 42입니다. 입력을 메모리에서 생성하므로 개인 데이터셋이나 다운로드가
필요하지 않습니다. 아래 규칙 학습 명령은 추적된 JSON 예제와 Prolog 사실을 사용하고,
학습한 절과 양성·음성 hold-out 정확도를 출력한 뒤 Prolog 상태를 정리합니다. 이 명령은
터미널에 결과를 출력하며 모델을 저장하거나 입력 fixture를 변경하지 않습니다.

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

### 실제 기본 실험 검증 (2026-10-05)

Windows에서 Python 3.12.7, SWI-Prolog 9.2.9, 커밋
`c07e8083c6a58eb7de99bb26c8dc89a0c215f52c`의 PySwip 0.3.3을 사용하여 전체 공개
테스트 **30개가 통과**했습니다. 설치된 의존성은 pytest 9.1.1, SciPy 1.18.1,
Click 8.5.0, NetworkX 3.7, tabulate 0.10.0, NumPy 2.5.3입니다.

- 위의 작은 속성 학습 명령은 종료했으며 `dtl`과 `my-dtl` 모두 홀드아웃 예제 4/4개를
  올바르게 분류했습니다.
- 위의 재귀 그래프 명령은 기본 seed 42로 종료했으며 양성 12/12개와 음성 59/59개를
  올바르게 분류했습니다.
- 회귀 테스트는 양성·음성 상수 트리, 혼합 분기 트리, FOIL 정리 전 평가, 연속 지식
  베이스, 오래된 테이블 응답 제거를 확인합니다.

재귀 target은 [SWI-Prolog tabling](https://www.swi-prolog.org/pldoc/man?section=tabling)으로
그래프 순환의 반복 탐색을 막습니다. 학습한 절이 변경되면 target 테이블을 비우고
정리 시 제거합니다. 이는 유한 관계 그래프 fixture에 적용하며, 무한히 증가하는 term을
사용하는 임의의 Prolog 프로그램까지 종료를 보장하지는 않습니다. Linux/WSL 설치
명령은 대안으로 제공하며 이번 Windows 검증에서는 실행하지 않았습니다. Vampire는
별도의 선택적 추론 경로이며 이번 테스트에 포함하지 않았고 과거 성능 실험도 재실행하지
않았습니다.

지원하는 데이터 경로는 생성한 속성 예제와 Prolog 사실에 연결한 JSON 그래프 예제입니다.
`Dataset.from_csv()`와 `Dataset.to_csv()`는 사용하지 않는 과제 placeholder로 남아 있으며,
CSV 입출력은 실행 가능한 평가 범위에 포함하지 않습니다.

## 결과와 한계

기록된 실험에서 `my-dtl`은 기준 구현보다 훨씬 빠르게 학습했고 한 극단적 잡음 조건에서 더 강건했습니다. 반면 여러 저잡음 및 제한된 데이터 조건에서는 성능이 낮았습니다. 이는 과제 당시 측정값이며 이번 포트폴리오 재구성 과정에서 다시 실행한 결과가 아닙니다. 전체 표, 명령, 해석, 타당성의 한계는 [실험 보고서](docs/experiment-report.ko.md)에 정리했습니다.

`requirements.txt`는 PySwip을 검증한 커밋으로 고정합니다. 다른 의존성은 버전이 고정되지
않았으므로 이번 기본 실험 결과와 비교할 때는 위의 버전 조합을 사용하고, 새 실험에서는
실제로 설치된 버전을 기록하세요.

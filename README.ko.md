# 지식 기반 인공지능 포트폴리오

[English](README.md) | [한국어](README.ko.md)

COMP24412에서 수행한 세 프로젝트를 자동 정리 증명, 논리 프로그래밍, 기호 머신러닝이라는 흐름으로 정리한 포트폴리오입니다. 각 프로젝트는 문제, 구현 방법, 재현 절차, 기술적 트레이드오프를 중심으로 설명합니다.

## 한눈에 보기

| 프로젝트 | 주제 | 보여 주는 역량 | 핵심 기술 |
| --- | --- | --- | --- |
| [자동 추론](projects/automated-reasoning/README.ko.md) | 일차 논리와 증명 탐색 | TPTP 모델링, 증명 생성, 모델 탐색, 증명 산출물 분석 | Vampire, TPTP, Python, LaTeX |
| [논리 프로그래밍](projects/logic-programming/README.ko.md) | 선언적 제약 모델링 | 중첩된 우주선 부품 설계를 검증하는 재귀 Prolog 술어 | SWI-Prolog |
| [기호 머신러닝](projects/symbolic-machine-learning/README.ko.md) | 설명 가능한 개념 학습 | 결정 트리, 이득비, FOIL 규칙 귀납, 재귀 관계, 평가 도구 | Python, PySwip, SWI-Prolog, pytest |

## 주요 내용

- 일차 논리 문제를 정의하고 증명 결과와 유한 모델 변형을 분석했습니다.
- 호환성, 중첩 실드, 부품 사용 여부, 구조 제약을 검사하는 재귀 Prolog 술어를 구현했습니다.
- 결정 트리 학습기를 구현하고 학습한 트리를 읽을 수 있는 논리식으로 변환했습니다.
- Prolog 지식 베이스를 활용하는 FOIL 방식의 귀납 논리 프로그래밍 학습기를 구현했습니다.
- 이득비와 깊이 제한을 사용하는 `my-dtl`을 개발했습니다. 기존 과제 실험 기록에서는 학습 시간이 44-80% 감소했고 특정 고잡음 조건에서 정확도가 19.1%p 향상되었습니다. 저잡음 및 소규모 학습 데이터에서 발생한 성능 저하도 함께 기록했습니다.

## 저장소 구조

```text
.
├── README.md / README.ko.md
└── projects/
    ├── automated-reasoning/
    │   ├── problems/       # TPTP 및 절 형식 문제 정의
    │   ├── artifacts/      # 증명 명세와 렌더링된 유도 과정
    │   ├── tools/          # Vampire 래퍼와 proof-to-LaTeX 도구
    │   └── references/     # 원본 과제 명세
    ├── logic-programming/
    │   ├── src/            # Prolog 지식 베이스와 술어
    │   └── references/     # 원본 과제 명세
    └── symbolic-machine-learning/
        ├── learning/       # 결정 트리와 FOIL 구현
        ├── tests/          # 공개 테스트와 그래프 픽스처
        ├── docs/           # 실험 보고서와 평가 가이드
        └── references/     # 과제 및 강의 자료
```

## 빠른 시작

### 1. 자동 추론

[Vampire](https://vprover.github.io/)를 설치합니다. 실행 파일이 `/opt/vampire/vampire`에 없다면 `tools/run_vampire`의 `VAMPIRE_BIN`을 수정하세요.

```bash
cd projects/automated-reasoning
./tools/run_vampire --preset gc problems/maps.p
```

### 2. 논리 프로그래밍

SWI-Prolog를 설치한 뒤 설계 검사기를 불러옵니다.

```bash
cd projects/logic-programming
swipl -s src/electrical.pl
```

```prolog
?- safe_design([part(radar), part(cpu)]).
true.
```

### 3. 기호 머신러닝

Python 3와 SWI-Prolog가 필요합니다. 다음 Conda 워크플로는 두 런타임을 하나의 로컬 환경에 설치합니다.

```bash
cd projects/symbolic-machine-learning
conda create -p .venv -c conda-forge python=3.12 swi-prolog=9.2.9 pip -y
conda activate ./.venv
python -m pip install -r requirements.txt
python -m pytest
```

SWI-Prolog가 이미 시스템에 설치되어 있다면 프로젝트 README의 일반 Python `venv` 설치 방법을 사용할 수 있습니다.

## 문서

모든 Markdown 문서는 영어를 기본으로 하며 한국어 대응 문서로 이동할 수 있습니다. 세부 구현은 각 프로젝트 README에서, 측정 결과와 한계는 기호 학습 프로젝트의 [실험 보고서](projects/symbolic-machine-learning/docs/experiment-report.ko.md)에서 확인할 수 있습니다.

## 배경

이 저장소는 맨체스터 대학교 COMP24412 Knowledge-Based Artificial Intelligence 과목(2024-25)의 과제로 시작되었습니다. 출처와 맥락을 보존하기 위해 원본 과제 및 강의 PDF를 각 프로젝트의 `references/`에 유지했습니다. 포트폴리오에 불필요한 캐시, LaTeX 보조 파일, 오래된 수업 동기화·제출 스크립트, 미완성 백업 파일은 제거했습니다.

현재 별도 라이선스가 선언되어 있지 않습니다. 코드와 제공된 수업 자료를 사용할 때 이 점을 고려해 주세요.

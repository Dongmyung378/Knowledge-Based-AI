# 지식 기반 인공지능 포트폴리오

[English](README.md) | [한국어](README.ko.md)

COMP24412에서 수행한 세 프로젝트를 자동 정리 증명, 논리 프로그래밍, 기호 머신러닝이라는 흐름으로 정리한 포트폴리오입니다. 각 프로젝트는 문제, 구현 방법, 재현 절차, 기술적 트레이드오프를 중심으로 설명합니다.

여기서 **지식 기반 인공지능**은 사실과 규칙을 명시적으로 표현해 판단 과정을 살펴볼 수 있는 방식을 뜻합니다. 자동 추론은 주어진 사실에서 결론이 따라오는지 확인하고, 논리 프로그래밍은 규칙으로 제안한 설계가 조건에 맞는지 검사합니다. 기호 머신러닝은 반대로 정답이 붙은 예제에서 출발해 새로운 입력을 판단할 결정 트리나 규칙을 학습합니다.

포트폴리오의 학습 프로젝트를 보려면 아래 **기호 머신러닝**부터 읽으면 됩니다. 생성한 속성 예제나 알려진 그래프 관계를 입력받아 읽을 수 있는 분류 규칙, 개별 예측의 판단 경로와 평가 보고서를 만듭니다. 나머지 두 프로젝트는 관련 논리 배경을 다루며 별도의 실행 경로를 제공합니다.

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
- 초기 `dtl`과 공유 카운터 방식의 `my-dtl`을 보존하고, 이득비와 정확한 경로 깊이 및 검증 기반 가지치기 변형을 별도로 추가했습니다. 홀드아웃 평가와 예측 경로를 제공하며 초기 실험 표는 새로운 측정과 구분합니다.

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
        ├── tools/          # 동일 조건 벤치마크와 환경 및 배포 검사
        ├── docs/           # 개선 결과와 보존한 초기 보고서
        ├── legacy/         # 초기 소스와 실험의 고정 스냅샷
        └── references/     # 과제 및 강의 자료
```

## 빠른 시작

### 1. 자동 추론

[Vampire](https://vprover.github.io/)를 설치합니다. 실행 파일이 `/opt/vampire/vampire`에 없다면 `tools/run_vampire`의 `VAMPIRE_BIN`을 수정하세요.

```bash
cd projects/automated-reasoning
sh ./tools/run_vampire --preset gc problems/maps.p
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

Python 3.12와 함께 Windows에서는 SWI-Prolog 9.2.9 x64, Ubuntu 24.04에서는 시스템 패키지 9.0.4를 사용합니다. SWI-Prolog를 별도로 설치하고 새 Python 환경에서 기호 학습 검사를 실행합니다.

```bash
cd projects/symbolic-machine-learning
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python tools/run_checks.py --output-dir outputs/verification
```

Windows PowerShell에서는 `.\.venv\Scripts\Activate.ps1`로 활성화합니다. 런타임 연결은 [프로젝트 README](projects/symbolic-machine-learning/README.ko.md), 실험 실행과 파일 무결성 확인은 [재현 문서](projects/symbolic-machine-learning/docs/reproduce.ko.md)를 참고하세요.

2026-10-05의 초기 기본 검증 30개 통과는 과거 기록으로 유지합니다. 개선 배포본은 실제 소스 ZIP을 풀어 같은 PC의 새 환경에서 확인했습니다. Windows는 151개 통과와 권한 관련 심볼릭 링크 2개 건너뜀, WSL의 Linux 환경은 153개 모두 통과했습니다. 두 환경에서 실제 Prolog 질의와 네이티브 프로세스 종료를 포함한 통합 다섯 단계가 모두 통과했습니다. [실행 환경과 검증 근거](projects/symbolic-machine-learning/docs/validation.ko.md)를 참고하세요. Vampire는 별도의 자동 추론 경로에만 필요합니다.

## 문서

모든 Markdown 문서는 영어를 기본으로 하며 한국어 대응 문서로 이동할 수 있습니다. 세부 구현은 각 프로젝트 README에서 확인할 수 있습니다. 기호 학습의 [구조](projects/symbolic-machine-learning/docs/architecture.ko.md)와 [재현 문서](projects/symbolic-machine-learning/docs/reproduce.ko.md)는 개선한 실행 경로를 설명하며 [초기 실험 보고서](projects/symbolic-machine-learning/docs/experiment-report.ko.md)는 과거 기록으로 보존합니다.

## 배경

이 저장소는 맨체스터 대학교 COMP24412 Knowledge-Based Artificial Intelligence 과목(2024-25)의 과제로 시작되었습니다. 출처와 맥락을 보존하기 위해 원본 과제 및 강의 PDF를 각 프로젝트의 `references/`에 유지했습니다. 포트폴리오에 불필요한 캐시, LaTeX 보조 파일, 오래된 수업 동기화 및 제출 스크립트, 미완성 백업 파일은 제거했습니다.

현재 별도 라이선스가 선언되어 있지 않습니다. 코드와 제공된 수업 자료를 사용할 때 이 점을 고려해 주세요.

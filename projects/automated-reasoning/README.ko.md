# 일차 논리를 이용한 자동 추론

[English](README.md) | [한국어](README.ko.md) | [포트폴리오 홈](../../README.ko.md)

## 개요

작은 추론 문제를 TPTP 언어로 모델링하고 Vampire 정리 증명기를 이용해 증명 탐색, 포화 전략, 절 형식 변환, 유한 모델 변형을 탐구한 프로젝트입니다.

## 구현 내용

- 지도 관계, 집합론, 구문, 반려동물 논리 퍼즐에 대한 일차 논리 인코딩
- 만족 가능·불가능 사례를 비교하기 위한 반려동물 문제의 타입 기반 변형
- given-clause, discount, Otter 방식 포화 프리셋을 사용한 증명 탐색
- 증명 명세를 LaTeX로 변환하고 검토용 PDF를 보존하는 워크플로

## 대표 결과물

| 영역 | 소스 | 결과물 |
| --- | --- | --- |
| 지도 추론 | [`problems/maps.p`](problems/maps.p) | `artifacts/maps-{a,b,c}.*`의 세 가지 증명 변형 |
| 집합 추론 | [`problems/sets.p`](problems/sets.p), [`problems/sets.cnf`](problems/sets.cnf) | [`artifacts/sets.pdf`](artifacts/sets.pdf)의 렌더링된 유도 과정 |
| 구문 추론 | [`problems/syntax.p`](problems/syntax.p) | [`artifacts/syntax.pdf`](artifacts/syntax.pdf)의 렌더링된 유도 과정 |
| 모델 변형 | `problems/pets-{a,b,c}.tff` | 모델 탐색용 타입 기반 변형 |

## 증명 실행

### 준비 사항

- Unix 계열 셸
- [Vampire](https://vprover.github.io/)

현재 래퍼는 Vampire가 `/opt/vampire/vampire`에 있다고 가정합니다. 다른 위치에 설치했다면 `tools/run_vampire`의 `VAMPIRE_BIN`을 수정하세요.

```bash
cd projects/automated-reasoning
./tools/run_vampire --preset gc problems/maps.p
```

`discount`, `otter` 프리셋도 사용할 수 있으며 `--verbose gc` 또는 `--verbose all`로 탐색 과정을 확인할 수 있습니다.

```bash
./tools/run_vampire --preset discount --verbose gc problems/sets.p
```

## 설계 메모

자료를 다음 세 종류로 분리했습니다.

- `problems/`: 실행 가능한 논리 명세와 참고 문제
- `artifacts/`: 증명 메타데이터, 생성된 LaTeX, 렌더링 결과
- `tools/`: 정리 증명기 래퍼와 변환 도구

작성한 논리 모델과 생성 결과가 섞이지 않아 핵심 작업을 쉽게 검토할 수 있습니다.

## 한계

- 제공된 래퍼의 Vampire 경로는 하드코딩되어 있어 로컬 설정이 필요할 수 있습니다.
- 저장된 증명 산출물은 이전 실행 결과를 기록한 것이며 자동으로 재생성되지 않습니다.
- 원본 과제 PDF는 `references/`에 보존되어 있으며 실행 워크플로에는 포함되지 않습니다.

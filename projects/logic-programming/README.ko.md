# Prolog을 이용한 제약 모델링

[English](README.md) | [한국어](README.ko.md) | [포트폴리오 홈](../../README.ko.md)

## 개요

선언적 Prolog 규칙으로 우주선 부품 배치를 검증하는 프로젝트입니다. 설계는 개별 부품과 재귀적으로 중첩된 실드를 포함할 수 있으며, 올바른 설계는 호환성과 부품 사용 제약을 만족해야 합니다.

## 문제 모델

지식 베이스는 8개 부품과 대칭 관계인 `safe_with/2`를 정의합니다. 완성된 해결기는 네 가지 관심사를 처리합니다.

| 술어 | 역할 |
| --- | --- |
| `safe_list/1` | 평면 목록의 모든 부품 쌍이 서로 호환되는지 검사 |
| `safe_design/1` | 부품과 중첩 실드를 재귀적으로 검증 |
| `count_shields/2` | 누산기를 사용해 모든 중첩 수준의 실드 수 계산 |
| `design_uses/2` | 요청한 부품을 설계가 정확히 한 번씩 사용하는지 검사 |

## 구현 방식

- 패턴 매칭으로 `part(Component)`와 `shield(InnerDesign)`을 구분합니다.
- 재귀로 외부 설계와 임의 깊이의 실드 내부를 처리합니다.
- `select/3`으로 남은 허용 부품 집합에서 사용한 부품을 제거해 재사용을 막습니다.
- `subtract/3`와 `append/3`으로 중첩 구조의 부품 사용 결과를 결합합니다.
- 명시적인 `safe_with/2` 지식 베이스로 부품 쌍의 안전성을 검사합니다.

## 실행 방법

[SWI-Prolog](https://www.swi-prolog.org/)를 설치하고 이 디렉터리에서 실행합니다.

```bash
cd projects/logic-programming
swipl -s src/electrical.pl
```

예시 질의:

```prolog
?- safe_list([radar, cpu, imu]).
true.

?- safe_design([part(radar), shield([part(cpu), part(imu)])]).
true.

?- count_shields([part(radar), shield([part(cpu), shield([part(imu)])])], Count).
Count = 2.
```

인터프리터를 종료하려면 `halt.`를 사용합니다.

## 프로젝트 구조

```text
logic-programming/
├── src/
│   ├── database.pl    # 부품 사실과 호환 관계
│   ├── electrical.pl  # 완성된 재귀 설계 검사기
│   └── warmup.pl      # 최소 입문 예제
└── references/
    └── prolog_lab_assessed.pdf
```

`electrical.pl`은 부품 사실을 직접 포함하므로 단독으로 불러올 수 있습니다. `database.pl`에는 개발 과정에서 사용한 독립 지식 베이스를 보존했습니다.

## 한계

- 호환성 데이터는 동적으로 불러오지 않고 고정되어 있습니다.
- 검증기는 과제에서 정의한 `part/1`, `shield/1` 항 구조를 대상으로 합니다.
- 원본 프로젝트에는 자동 테스트 모음이 없으므로 위 질의를 스모크 테스트로 사용할 수 있습니다.

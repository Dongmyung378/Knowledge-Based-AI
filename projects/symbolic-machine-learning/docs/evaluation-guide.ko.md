# 평가 및 데이터셋 도구

[English](evaluation-guide.md) | [한국어](evaluation-guide.ko.md) | [프로젝트 README](../README.ko.md)

기호 머신러닝 프로젝트에 포함된 세 명령줄 도구의 사용법입니다. 모든 명령은 `projects/symbolic-machine-learning`에서 실행하세요.

## 알고리즘 등록

평가 스크립트는 `AlgorithmRegistry`를 통해 구현을 찾습니다. 새 속성 학습기를 고유 이름으로 등록합니다.

```python
@AlgorithmRegistry.register("my-dtl")
class MyDecisionTreeLearner(DecisionTreeLearner):
    ...
```

FOIL 변형은 실행 후 임시 Prolog 절을 정리할 수 있도록 기준 구현과 같은 컨텍스트 관리자 래퍼도 필요합니다.

## 속성 학습기 평가

사용 가능한 하위 명령 확인:

```bash
python evaluate_attributes.py --help
```

### 레이블 잡음 강건성

```bash
python evaluate_attributes.py eval-noisy \
  -a dtl -a my-dtl \
  -c 0.2 -c 0.5 \
  -s 10 \
  -d 10
```

- `-a`: 등록된 알고리즘 선택. 첫 번째 알고리즘이 비교 기준입니다.
- `-c`: 학습 중 반전할 타깃 레이블 비율입니다.
- `-s`: Boolean 속성 수이며 `2^s`개의 예제를 생성합니다.
- `-d`: 생성된 타깃 개념이 사용하는 최대 속성 수입니다.

평가 전에 원래 레이블을 복원합니다. 이 명령은 별도의 홀드아웃 데이터셋을 사용하지 않습니다.

### 학습 데이터가 적을 때의 성능

```bash
python evaluate_attributes.py eval-size \
  -a dtl -a my-dtl \
  -t 0.5 -t 0.7 \
  -s 10 \
  -d 10
```

`-t`는 학습 데이터 비율이며 나머지 예제가 평가 분할이 됩니다.

### 학습 시간

```bash
python evaluate_attributes.py eval-time \
  -a dtl -a my-dtl \
  -s 5 -s 7 -s 10
```

반복 측정한 실행 시간을 보고합니다. 보고된 변동 폭과 성능 차이를 함께 비교하고, 더 신뢰할 수 있는 결과를 위해 시스템 부하가 적을 때 다시 실행하세요.

## 규칙 학습기 평가

재귀 절로 그래프 도달 가능성을 학습합니다.

```bash
python evaluate_rules.py \
  -a foil \
  -d tests/graph_small.json \
  -k tests/graph_small.pl \
  -t "reachable(X,Y)" \
  -r \
  -e 0.8
```

- `-d`: 양성·음성 예제를 담은 JSON 경로
- `-k`: Prolog 지식 베이스 경로
- `-t`: 타깃 리터럴
- `-r`: 타깃 술어의 재귀적 사용 허용
- `-e`: 학습 데이터 비율. 홀드아웃 평가 없이 학습하려면 생략

PySwip과 SWI-Prolog는 반복 실행 사이에 상태를 유지하거나 불안정해질 수 있습니다. 필요한 경우 알고리즘이나 실패 테스트를 별도 프로세스에서 실행하세요.

## 그래프 데이터셋 생성

임의 방향 그래프, Prolog 지식 베이스, 레이블이 있는 도달 가능성 예제를 생성합니다.

```bash
python generate_graphs.py outputs/graph -n 15 -p 0.046 -r 42
```

`outputs/graph.pl`과 `outputs/graph.json`이 생성됩니다. 실행 전에 대상 디렉터리를 만들어야 합니다.

JSON 스키마:

```json
{
  "pos": [{"X": "n0", "Y": "n1"}],
  "neg": [{"X": "n1", "Y": "n0"}]
}
```

각 예제의 키는 타깃 리터럴의 변수와 일치해야 합니다.

## 재현성 체크리스트

1. Python, 의존성, SWI-Prolog 버전을 기록합니다.
2. 직접 비교할 때는 난수 시드를 고정합니다.
3. 모든 알고리즘을 같은 생성 데이터셋에서 실행합니다.
4. 일반적인 결론을 내리기 전에 여러 시드로 실험을 반복합니다.
5. 의도적인 테스트 픽스처가 아니라면 생성 결과를 `tests/` 밖에 저장합니다.
6. 개선점과 함께 실패 및 성능 저하도 보고합니다.

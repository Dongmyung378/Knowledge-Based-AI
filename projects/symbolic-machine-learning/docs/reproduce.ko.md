# 배포본 재현과 검증

[English](reproduce.md) | [한국어](reproduce.ko.md) | [프로젝트 README](../README.ko.md)

별도 안내가 없으면 `projects/symbolic-machine-learning`에서 명령을 실행합니다. Python과 SWI-Prolog는 별도 런타임이므로 Python 패키지 설치만으로 Prolog 공유 라이브러리가 설치되지는 않습니다.

## 로컬 환경 설치

Python 3.12를 사용합니다. 검증한 Windows 런타임은 **SWI-Prolog 9.2.9 x64**이며 Ubuntu 24.04의 시스템 패키지는 **SWI-Prolog 9.0.4**입니다. 배포 도구는 Python 3.10 이상을 사용합니다. 다른 프로젝트의 패키지를 재사용하기보다 새 환경을 활성화합니다.

고정한 PySwip 소스 커밋을 `pip`으로 가져오려면 Git도 필요합니다. 다운로드 ZIP에서 시작하는 경우에도 의존성 설치에는 Git을 사용합니다. 속성 예제는 생성하고 그래프 예제는 저장소에 포함하므로 별도 데이터셋 다운로드는 필요하지 않습니다.

```bash
python -m venv .venv
```

Linux 또는 WSL:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

```bash
python -m pip install -r requirements.lock.txt
python tools/check_environment.py --output outputs/environment.json
```

Ubuntu 24.04에서는 `sudo apt-get install swi-prolog-nox`로 시스템 런타임을 설치합니다. Windows에서는 [공식 9.2.9 x64 설치 파일](https://www.swi-prolog.org/download/stable/bin/swipl-9.2.9-1.x64.exe.envelope)을 사용하고 `PATH`에서 `swipl`을 실행할 수 있게 합니다. 공식 설치 파일의 SHA-256은 `0e6dbf5f4bb245344a257f2715f5d793d17870dee9eea1735ccb67b35f1e037c`입니다.

설치 루트와 `bin`의 파일을 포함한 전체 런타임을 유지합니다. `libswipl.dll` 하나만 복사해서는 충분하지 않습니다. 설치 프로그램에 등록되지 않은 압축 해제형 런타임은 `SWI_HOME_DIR`에 설치 루트를, `LIBSWIPL_PATH`에 `bin/libswipl.dll`을 지정하고 현재 프로세스의 `PATH` 앞에 `bin` 디렉터리를 추가합니다. 이 경로는 각 컴퓨터에서만 설정하며 커밋이나 공개 보고서에 넣지 않습니다. 별도로 비교한 Windows 10.0.2 런타임은 고정한 연결 패키지와의 초기화에서 실패해 채택하지 않았습니다. Windows의 검증 버전 대신 무조건 최신 SWI-Prolog를 설치하도록 안내하지 않습니다.

환경 진단은 패키지 버전과 발견 여부를 확인하고, 별도 PySwip 프로세스에서 실제 질의를 실행해 `[1, 4, 9]`가 나오는지 확인합니다. 실행 파일 위치와 사용자 디렉터리, 원시 오류 추적은 기록하지 않습니다. 종료 코드가 0이면 명시한 검사를 모두 통과한 것입니다. 실패하면 수정 안내와 함께 0이 아닌 코드를 반환합니다. 라이브러리를 발견했다는 사실만으로 실제 질의 검증을 대신하지 않습니다.

## 파일 무결성 확인

```bash
python tools/verify_release.py
```

매니페스트에는 프로젝트 배포 파일의 상대 경로와 바이트 수, SHA-256을 기록합니다. 파일 자체의 최종 해시를 자기 안에 넣을 수 없으므로 매니페스트 자신은 제외합니다. 검증 도구와 초기 스냅샷도 확인 대상입니다. 이 해시는 파일의 일치 여부를 확인하며 제3자 인증이나 전자서명을 뜻하지 않습니다.

저장소 다운로드 ZIP을 압축 해제하지 않고 검사할 수도 있습니다.

```bash
python tools/verify_release.py --zip /path/to/knowledge-based-ai-source.zip
```

검증 도구는 ZIP 내부의 프로젝트 매니페스트를 자동으로 찾습니다. 같은 이름의 매니페스트가 여러 개라면 `--prefix`로 해당 프로젝트의 ZIP 내부 디렉터리를 지정합니다. 안전하지 않은 경로와 심볼릭 링크, 중복 이름, CRC 오류, 선언한 파일의 해시 또는 크기 불일치는 검증 실패로 처리합니다. 목록에 선언하지 않은 추가 파일까지 인증하는 명령은 아닙니다.

## 실행 검사

전체 검증을 한 명령으로 실행합니다.

```bash
python tools/run_checks.py --output-dir outputs/verification
```

파일 무결성과 실제 Python 및 Prolog 연결, pytest, 두 초기 트리의 고정 예제 각각 4/4개 및 관계 홀드아웃 71/71개를 확인합니다. 테스트 요약 뒤에도 개별 프로세스의 정상 종료와 네이티브 실패 문자열을 검사합니다. 새 폴더 또는 빈 폴더 안에 세부 보고서와 로그를 보관하고, 앞 단계가 실패하면 후속 검사를 중단합니다. 다시 실행할 때는 다른 출력 폴더를 지정합니다.

회귀 테스트만 실행할 수도 있습니다.

```bash
python -m pytest
```

`setup.cfg`는 `--capture=sys`를 선택해 Windows의 네이티브 표준 스트림 핸들을 유지합니다. 이 호환성 설정이 프로세스 종료 확인을 대신하지는 않습니다.

재현한 결과와 함께 pytest의 전체 요약과 환경 보고서를 보관합니다. 테스트는 생성 속성 데이터와 저장된 관계 예제를 사용합니다. 통과 결과는 명시한 사례의 검증이며 가능한 모든 입력이나 Prolog 지식 베이스의 정답을 보장하지 않습니다.

초기 기본 실행 경로도 사용할 수 있습니다.

```bash
python evaluate_attributes.py eval-size -a dtl -a my-dtl -s 4 -d 2 -t 0.75
python evaluate_rules.py -a foil -d tests/graph_small.json -k tests/graph_small.pl -t "reachable(X,Y)" -r -e 0.8
```

## 개선 실험 실행

```bash
python tools/benchmark_attributes.py --plan configs/benchmark-plan.json --phase development --output outputs/attribute-development.json
python tools/benchmark_attributes.py --plan configs/benchmark-plan.json --phase evaluation --output outputs/attribute-evaluation.json
python tools/benchmark_inference.py --phase evaluation --output outputs/inference-evaluation.json
python tools/benchmark_foil.py --seed-start 200 --output outputs/foil-final-greedy.json
python tools/benchmark_foil.py --lookahead 2 --seed-start 200 --output outputs/foil-final-lookahead.json
```

개발 단계와 최종 평가 단계는 명령을 나누어 실행합니다. 공개 결과를 재현할 때는 저장된 계획을 바꾸지 않고, 출력 해석 전에 계획과 결과의 메타데이터를 확인합니다. FOIL 벤치마크의 `--quick`은 축소한 기본 실행이며 전체 벤치마크를 수행한 것으로 설명하지 않습니다. 사용자가 만든 출력은 공개 보고서를 덮어쓰지 않도록 무시되는 `outputs/` 아래에 저장합니다.

초기 관계 학습 명령의 규칙과 개별 예측 및 실패 진단도 JSON으로 저장할 수 있습니다.

```bash
python evaluate_rules.py -a foil -d tests/graph_small.json -k tests/graph_small.pl -t "reachable(X,Y)" -r -e 0.8 --output-json outputs/graph-small.json
```

CLI는 `--max-seconds`, `--query-timeout`, `--max-candidates`, `--max-prolog-queries`, `--max-clauses` 및 `--max-literals`를 받습니다. 기본값은 학습 60초와 질의당 2초, 후보 평가 20,000회, Prolog 질의 1,000,000회, 규칙 128개와 규칙별 조건 16개입니다. `--lookahead 2`는 제한된 두 조건 탐색을 선택하며 기본값 `--lookahead 0`은 탐욕 탐색을 유지합니다. 이는 통제된 탐색 예산이며 임의의 지식 베이스를 격리하는 보안 경계가 아닙니다. 보고서와 알고리즘별 `status`를 확인하며, 실패 진단을 정상 학습 모델로 해석하지 않습니다.

그래프 벤치마크는 알고 있는 그래프 안에서 관계 쌍을 홀드아웃으로 남깁니다. 학습 중에도 연결 사실을 제공하므로 새로운 그래프로의 전이 성능이 아닌 동일 그래프의 관계 완성 평가입니다. 정답은 독립적인 큐 기반 너비 우선 탐색과 대조합니다.

초기 잡음 및 시간 측정 명령과 한계는 [초기 평가 가이드](evaluation-guide.ko.md)에 남겨 두었습니다. 명령 이름은 유지하지만 현재 구현은 비교 절차를 수정했습니다. 당시 절차는 초기 스냅샷에서 재현하고 새로운 비교에는 개선 결과 보고서를 사용합니다. 초기 표를 새로운 홀드아웃 평가 결과로 해석하지 않습니다.

현재 `eval-noisy`는 기본 학습 80%와 깨끗한 홀드아웃 20%를 사용하며 `--train_split`을 받습니다. 학습 정답에만 잡음을 적용하고 알고리즘과 잡음 수준 사이에서 개념 및 분할을 공유합니다. `eval-size`는 같은 평가 예제에서 정답 여부의 차이에 대한 정확 McNemar 검정값을 표시하며 다중 비교를 보정하지 않은 기술적 비교입니다. `eval-time`에는 `--random_seed`/`-r`, `--runs`와 `--repeats`를 추가하고 동일한 선생성 입력과 순환 실행 순서를 사용합니다. 독립 검증셋이 필요한 `pruned-dtl`은 전용 벤치마크에서 실행합니다.

## 초기 버전 확인

`legacy/initial-aa947038.zip`에는 `aa947038f923e98ec0bf16457745d538284ef45c` 커밋의 초기 코드와 실험 문서, 테스트 및 데이터 27개 파일을 보존합니다. 원본 참고 PDF 세 개는 `references/`에서 바이트 단위로 그대로 유지하고 스냅샷에는 중복 저장하지 않습니다. `legacy/initial-provenance.json`에 초기 전체 30개 목록과 공유 참고 자료의 해시를 기록하며 배포 매니페스트로 스냅샷과 현재 참고 파일을 확인합니다. 초기 구현을 살펴보거나 실행할 때는 별도 디렉터리에 압축을 풉니다. 개선한 구현 위에 덮어쓰는 파일이 아닙니다. 별도 폴더에서 초기 참고 자료도 열려면 변경하지 않은 `references/`를 함께 복사합니다.

같은 저장소의 다른 두 과제 프로젝트는 배경 자료로 보존하며 이 기호 학습 실행에 필요한 의존성은 아닙니다. 원본 PDF는 출처를 확인하기 위한 자료이며 새로운 라이선스를 부여하지 않습니다.

## 검증 근거의 해석

같은 컴퓨터에 새로 만든 Python 환경은 하드웨어와 운영체제를 공유합니다. WSL은 Linux 사용자 공간과 파일 시스템을 분리하지만 호스트 하드웨어는 공유합니다. 어느 경우에도 모든 다른 컴퓨터에서 동일하게 실행된다는 인증은 아닙니다. 공개 결과에는 실제로 실행한 환경과 명령을 구분해 기록하며, GitHub Actions 설정이 있다는 사실만으로 원격 실행이 통과했다고 설명하지 않습니다.

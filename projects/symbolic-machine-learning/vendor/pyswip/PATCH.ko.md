# PySwip 호환성 수정

[English](PATCH.md) | [한국어](PATCH.ko.md)

이 폴더는 PySwip의 `c07e8083c6a58eb7de99bb26c8dc89a0c215f52c` 커밋을
MIT 라이선스와 저작자 표시와 함께 포함합니다. `UPSTREAM.json`은 원본 파일의
해시를 기록합니다. 원본 파일 중 `core.py`와 `pyproject.toml`의 패키지 버전만 수정했습니다.

프로젝트에서 사용하는 버전은 **0.3.3+argv1**입니다. 원본 연결 코드는
`PL_initialise`에 임시 ctypes 인자 배열을 전달하지만, SWI-Prolog는 호출이
끝난 뒤에도 그 배열을 참조합니다. 공식 API 계약에 따르면 엔진이 사용되는
동안 배열이 유효해야 합니다. 수정 전 패키지에서 네이티브 포인터를 검사한 결과,
초기화 직후 이미 배열의 주소 값이 손상된 것을 확인했습니다.

인자 배열과 문자열의 메모리를 유지하고 마지막에 NULL을 추가했으며 네이티브 함수의
인자 형식을 명시했습니다. 정상 `PL_cleanup` 종료 처리는 그대로 수행합니다.
질의 처리와 규칙 학습, 예측 및 기존 벤치마크 수치는 바꾸지 않았습니다.
프로젝트 폴더에서 requirements 파일을 설치하면 이 패키지가 함께 설치됩니다.
외부 패키지를 가져오기 위한 Git 설치는 필요하지 않습니다.

`tests/public/test_prolog_argv_lifetime.py`는 독립 Python 프로세스 네 개에서
메모리 할당 전후의 실제 네이티브 인자 주소와 Prolog 질의를 확인하고,
표준 오류 없이 정상 종료하는지 검사합니다.

근거: [SWI-Prolog의 PL_initialise 메모리 수명 계약](https://www.swi-prolog.org/pldoc/man?CAPI=PL_initialise).

# UnivManager Project Memory

## 아키텍처 핵심 전제
- **구조**: 본 프로그램(UnivManager)은 단독 봇이 아니라, 이미 구축된 메인 대화형 챗봇인 **OpenClaw가 사용할 수 있는 백엔드 도구(모듈/서버)**입니다.
- **텔레그램 알림**: 대화 인터페이스는 OpenClaw가 전담하므로, UnivManager 내의 텔레그램 알림 로직은 제거하거나 OpenClaw와의 통신용으로 축소될 수 있습니다.

## 과거 및 현재 작업사항 (구현 완료/진행 중)
- **Blackboard 스크래퍼 기반 (수집 및 아키텍처 개편)**: Playwright, Stealth를 이용한 브라우저 구동 및 SSO 자동 로그인 템플릿 구현 (`scraper/blackboard_scraper.py`).
  - **[완료]** 한국어 로케일 환경에서 공지사항 상세 패널의 닫기 버튼 클릭 실패 버그 완벽 해결. 다중 라인 개행 나열 시 파이썬 콤마(`,`)에 의해 의도치 않은 튜플(Tuple) 구조가 생성되어 잘못된 문자열 인자가 전달되던 치명적인 구문 결함을 박멸했습니다. 사용자가 명시한 고유 마크업에 정확히 매칭되는 단일 CSS 셀렉터 `'button.bb-close[data-close="bb-offcanvas"]'`로 전면 일치화하여 원래의 네이티브 클릭 방식(`await close_btn.click()`)으로 오류 없이 패널이 안전하게 닫히도록 완벽 복구 완료. (2026-05-28)
  - **[완료]** 영어 및 한글 다국어 로케일 대응 퀴즈/시험 탐색 및 저장 안정화. 영문명 `Quiz`, `Test`, `Assessment`, `평가` 등의 라벨을 가진 퀴즈들이 `get_handler` 분기에서 누락되어 일반 기타 문서로 유도되어 빈 파일로 생성되던 인지 필터의 키워드 범위를 완벽하게 확장 완료. 또한 퀴즈 메타데이터(`timeLimit`, `attempts`)를 텍스트 파일 헤더에 정교하게 포맷팅하여 부모 폴더 경로 내에 이쁘게 기록되도록 익스포트 함수를 대폭 고도화함. (2026-05-28)
  - **[완료]** 실행 위치(cwd) 종속성 제거 및 Docker용 환경 변수 기반 절대 경로 고정. 메인 스크립트 실행 디렉토리가 바뀔 때 다운로드 폴더나 캐시 파일이 흩어지던 현상을 방지하고자, `config.py` 내의 `DOWNLOAD_PATH`, `CHROMA_DB_PATH`, `DATA_FILE` 경로를 프로젝트 물리 루트(`BASE_DIR`) 절대 경로 기준으로 완전히 통일 완료. 또한 환경 변수(`DOWNLOAD_PATH` 등) 연동을 지원하여 Docker 컨테이너 볼륨 마운트 매칭을 100% 보장하도록 설정함. (2026-05-28)
  - **[완료]** 가상환경(.venv) 재설치 후 IDE의 샌드박스 정책 충돌에 따른 Python 3.14 인터프리터 인식 불가 현상 대응. 기존 .venv를 제거한 뒤 `--copies` 옵션을 강제하여 물리 파일 복사 형태의 새로운 가상환경으로 재구축 완료. pip 패키지 및 Playwright 브라우저 드라이버 재설치를 완벽히 마쳐 정상화 달성. (2026-05-28)
  - **[완료]** `Cannot find module playwright.async_api` 에러 발생 건 조치. `.vscode/settings.json` 내의 `python.defaultInterpreterPath`가 잘못된 경로(`~/.venv/bin/python`)로 설정되어 있어 시스템 전역 파이썬으로 분석기가 폴백되던 현상을 로컬 가상환경 경로(`${workspaceFolder}/.venv/bin/python`)로 수정하여 해결함. (2026-05-28)
  - **[완료]** 실행 버튼 클릭 시 가상환경이 자동 활성화되지 않는 현상 조치. `.vscode/settings.json` 파일에 `"python.terminal.activateEnvironment": true` 설정을 명시하여 VS Code 터미널 구동 및 실행 시 로컬 가상환경을 우선적으로 로드하도록 환경을 복구함. (2026-05-28)
  - **[최근 작업]** 메인 루프에서 조건문을 제거하고 `handlers/` 하위 모듈(`assignment_handler`, `exam_handler` 등)로 파싱 책임을 분리하는 전략 패턴 적용.
  - **[완료]** `announcement_handler.py` 공지 사항 추출 로직 고도화 및 첨부파일(data-bbfile JSON 파싱) 대응 완료. (2026-04-19)
  - **[최근 작업]** `discussion_handler.py` 토론 게시판 파싱 로직 전면 고도화.
    - **DOM 클리닝 및 필터링**: `cloneNode`를 활용하여 원본 훼손 없이 불필요한 메타데이터 제거.
    - **작성자 인식 및 정제**: `aria-label`, `bdi` 속성을 통한 순수 이름 추출.
    - **인라인 미디어 치환**: 이미지와 파일 링크를 본문 내 위치에서 `[이미지 첨부: ...]` 형식으로 치환.
  - **[이슈 및 개선 필요]** `assignment_handler.py`: 과제 상세 본문 추출 시, 현재 열린 과제가 아닌 다른 과제의 안내문이 섞여 나오는 현상 (DOM 캐싱 또는 셀렉터 중복 문제 추정).
- **Google Drive 연동 (보존)**: OAuth2.0 기반 토큰 발급 및 파이썬 API 연동 기초 마련 (`storage/google_drive.py`).
- **메인 스케줄러 (통합 뼈대)**: 1시간 단위 반복 실행을 위한 Python 스케줄러 세팅 (`main.py`).

## 수정 완료된 버그 목록 (2026-06-10)

- **[완료]** 파일 여러 개일 때 첫 번째 파일만 반복 다운로드되는 버그 수정. `filter(has=...).first`가 리스트 전체 래퍼를 잡아 항상 첫 번째 파일 버튼을 눌렀던 것을, `filter(has=overflow_selector).last`로 정확히 해당 파일의 행을 잡도록 수정. 다운로드 전후 Escape로 잔여 메뉴 정리도 추가. (`base_handler.py`)
- **[완료]** `container` null 참조 크래시. JS evaluate 내 `if (container)` 가드 밖에서 `container.querySelector()`를 호출해 TypeError 발생 시 과목 전체 수집이 0개로 실패하던 심각한 버그. `!!(container && container.querySelector(...))` 로 수정. (`blackboard_scraper.py`)
- **[완료]** 다운로드 재시도/영구누락 판별 오류. `not_downloadable`(파일 아님)과 `failed`(일시 오류) 반환이 반대로 되어 있어 파일 아닌 항목을 무한 재시도하고 진짜 파일은 조용히 누락되었음. 판별 기준을 "더보기 메뉴에 다운로드 항목 존재 여부"로 교정. expect_download 타임아웃 5s → 15s로 확대. (`base_handler.py`)
- **[완료]** 파일 다운로드 aria-label 미제공 시 FileHandler 누락. 폴백으로 title/href 확장자 검사 추가. aria-label(`"PDF, 파일명.pdf"`) 1순위는 유지 — 확장자 방식으로 대체하지 말 것. (`handlers/__init__.py`)
- **[완료]** 공지 사항 stale 핸들 및 evaluate_handle 누수. 패널 열고 닫을 때 리스트 re-render로 핸들 무효화 가능. 매 반복 목록 재조회 + `row_handle.dispose()` 추가. (`announcement_handler.py`)
- **[완료]** `processed_items.json` 항목마다 전체 재기록(O(n²) I/O). 저장 시점을 과목 단위(finally 블록)로 이동. 과목 중간 크래시 시 해당 과목만 재수집(dedup 멱등). (`blackboard_scraper.py`)
- **[완료]** 오디오 타입 문자열 필터링 조건 강화. '오디오'와 정확히 일치하지 않고 포함만 하는 경우(예: '오디오 파일') 개별 폴더가 생성되던 버그를 방지하기 위해 `in` 연산자 기반의 서브스트링 검사로 수정. (`blackboard_scraper.py`)
- **[완료]** 하드코딩된 도메인 주소 제거. 오디오 파일 소스 URL 파싱 중 사용된 하드코딩 도메인(`https://eclass2.ajou.ac.kr`)을 제거하고 `urllib.parse.urljoin`을 활용하여 현재 페이지 URL 기준으로 동적 절대 경로를 생성하도록 수정. (`scraper/handlers/audio_handler.py`)
- **[완료]** 과제 첨부파일 다운로드 시 stale 요소 클릭 방지. `assignment_handler.py`에서 다운로드 버튼 탐색 시 화면에 보이지 않는 이전 패널이나 메뉴의 찌꺼기가 남은 상태에서 잘못된 요소를 클릭하는 현상을 막기 위해, `filter(state="visible")` 및 `last`를 사용하도록 개선. (`scraper/handlers/assignment_handler.py`)
- **[완료]** 무한 스크롤 성능 최적화. `announcement_handler.py` 및 `discussion_handler.py` 내의 무한 스크롤 트리거 스크립트에서 레이아웃 스래싱을 유발하는 `window.getComputedStyle(c)` 호출을 제거하여 불필요한 성능 저하 및 렌더링 지연을 완벽히 해결함.
- **[완료]** 환경 변수 절대 경로 파싱 로직 개선. `config.py`에서 `CHROMA_DB_PATH` 및 `DOWNLOAD_PATH`에 상대 경로가 입력될 경우, 현재 작업 디렉토리 기준이 아닌 프로젝트 루트(`BASE_DIR`) 기준으로 정확하게 절대 경로를 생성하도록 `os.path.isabs` 기반 검증 로직 추가.
- **[완료]** 바이너리 항목 다운로드 실패 시 오작동 방지. `blackboard_scraper.py`에서 파일/오디오/비디오 등 바이너리 항목이 다운로드 불가 상태(`not_downloadable`)일 때 껍데기 텍스트 파일로 저장되고 처리 완료로 간주되는 버그를 수정. 이진 항목은 성공 시에만 처리 완료 목록에 포함되며, 실패 시 `.txt` 생성을 스킵하고 다음 실행 때 재시도 하도록 조건 로직 강화.
- **[완료]** 큰따옴표 포함 문자열 파싱 오류 방지. `base_handler.py`에서 폴백용 제목 기반 노드 탐색 시, `has-text` 텍스트 선택자에 큰따옴표 등의 특수문자가 직접 삽입되어 Playwright 문법 에러가 발생하는 문제를 막기 위해 안전한 `filter(has_text=...)` API로 교체.
- **[완료]** 설문조사(opinion-scale) 문항에서 질문 본문이 수집되지 않던 버그 수정. `exam_handler.py`의 `querySelector`가 DOM 순서상 먼저 등장하는 `legend.question-label`("문제 N")을 질문 본문으로 잡아버려 실제 질문 텍스트(예: "나는 아주대학교에 소속감을 느낀다")가 누락되던 현상을 해결. `legend`을 질문 본문 셀렉터에서 제거하고 헤더(문항 번호) 파싱으로 이동. 리커트 척도의 양 끝 라벨("전혀 그렇지 않다" ↔ "매우 그렇다")도 함께 수집하도록 개선. (2026-06-16)

## 추후 진행할 작업 (미구현 항목 및 계획)
1. **[직전 작업 예정] AssignmentHandler 안정화**: 과제 본문 혼선 문제 해결.
2. **[Phase 1] Google Drive 계층형 업로드 시스템**: 
   - 다운로드 완료된 자료를 `blackboard/{과목명}/{자료유형}/{파일명}` 구조로 업로드.
   - 업로드 후 로컬 임시 파일 삭제 로직 추가.
3. **[Phase 2] Gemini 3 Pro 전사 API 적용 (Text-First)**: 
   - Gemini File API를 통해 '완벽 강의록(md)' 생성.
4. **[Phase 2] ChromaDB 텍스트 기반 RAG 엔진 연동**: 
   - 생성된 완벽 강의록을 Text Chunking하여 `ChromaDB`에 벡터 임베딩 저장.
5. **[Phase 3] OpenClaw 연동 인터페이스 완성**: 
   - OpenClaw가 ChromaDB를 쿼리하거나 UnivManager를 툴로 호출할 수 있는 인터페이스 구성.


# UnivManager Project Memory

## 아키텍처 핵심 전제
- **구조**: 본 프로그램(UnivManager)은 단독 봇이 아니라, 이미 구축된 메인 대화형 챗봇인 **OpenClaw가 사용할 수 있는 백엔드 도구(모듈/서버)**입니다.
- **텔레그램 알림**: 대화 인터페이스는 OpenClaw가 전담하므로, UnivManager 내의 텔레그램 알림 로직은 제거하거나 OpenClaw와의 통신용으로 축소될 수 있습니다.

## 과거 및 현재 작업사항 (구현 완료/진행 중)
- **Blackboard 스크래퍼 기반 (수집 및 아키텍처 개편)**: Playwright, Stealth를 이용한 브라우저 구동 및 SSO 자동 로그인 템플릿 구현 (`scraper/blackboard_scraper.py`).
  - **[최근 작업]** 메인 루프에서 조건문을 제거하고 `handlers/` 하위 모듈(`assignment_handler`, `exam_handler` 등)로 파싱 책임을 분리하는 전략 패턴 적용.
  - **[완료]** `announcement_handler.py` 공지 사항 추출 로직 고도화 및 첨부파일(data-bbfile JSON 파싱) 대응 완료. (2026-04-19)
  - **[최근 작업]** `discussion_handler.py` 토론 게시판 파싱 로직 전면 고도화.
    - **DOM 클리닝 및 필터링**: `cloneNode`를 활용하여 원본 훼손 없이 불필요한 메타데이터 제거.
    - **작성자 인식 및 정제**: `aria-label`, `bdi` 속성을 통한 순수 이름 추출.
    - **인라인 미디어 치환**: 이미지와 파일 링크를 본문 내 위치에서 `[이미지 첨부: ...]` 형식으로 치환.
  - **[이슈 및 개선 필요]** `assignment_handler.py`: 과제 상세 본문 추출 시, 현재 열린 과제가 아닌 다른 과제의 안내문이 섞여 나오는 현상 (DOM 캐싱 또는 셀렉터 중복 문제 추정).
- **Google Drive 연동 (보존)**: OAuth2.0 기반 토큰 발급 및 파이썬 API 연동 기초 마련 (`storage/google_drive.py`).
- **메인 스케줄러 (통합 뼈대)**: 1시간 단위 반복 실행을 위한 Python 스케줄러 세팅 (`main.py`).

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


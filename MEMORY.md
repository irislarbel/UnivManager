# UnivManager Project Memory

## 아키텍처 핵심 전제
- **구조**: 본 프로그램(UnivManager)은 단독 봇이 아니라, 이미 구축된 메인 대화형 챗봇인 **OpenClaw가 사용할 수 있는 백엔드 도구(모듈/서버)**입니다.
- **텔레그램 알림**: 대화 인터페이스는 OpenClaw가 전담하므로, UnivManager 내의 텔레그램 알림 로직은 제거하거나 OpenClaw와의 통신용으로 축소될 수 있습니다.

## 과거 및 현재 작업사항 (구현 완료/진행 중)
- **Blackboard 스크래퍼 기반 (수집)**: Playwright, Stealth를 이용한 브라우저 구동 및 SSO 자동 로그인 템플릿 구현 (`scraper/blackboard_scraper.py`).
- **Google Drive 연동 (보존)**: OAuth2.0 기반 토큰 발급 및 파이썬 API 연동 기초 마련 (`storage/google_drive.py`).
- **메인 스케줄러 (통합 뼈대)**: 1시간 단위 반복 실행을 위한 Python 스케줄러 세팅 (`main.py`).
- *주의*: `multimedia_analyzer.py`의 로컬 Whisper 로직은 더 이상 사용하지 않는 **레거시 데이터**입니다.

## 추후 진행할 작업 (미구현 항목 및 계획)
1. **[Phase 1] 스크래퍼 고도화 및 데이터 정제**: 
   - Blackboard 로그인 이후 과목을 순회하며 게시물 파싱 및 영상/자료 다운로드 자동화.
2. **[Phase 1] Google Drive 계층형 업로드 시스템**: 
   - 다운로드 완료된 자료를 `blackboard/{과목명}/{자료유형}/{파일명}`의 디렉토리 구조를 생성(또는 탐색)하여 업로드하는 로직 구현. 
   - (예: `blackboard/수학1/수업 녹화 영상/1주차 - 3월 9일 월요일 수업(2장9절).mp4`)
   - 업로드 직후 로컬 용량 확보를 위해 임시 파일 삭제.
3. **[Phase 2] Gemini 3 Pro 전사 API 적용 (Text-First)**: 
   - 레거시 Whisper 대신, 영상을 Google Drive에 올림과 동시에 Gemini File API를 통해 **Gemini 3 Pro**에 넘겨 '완벽 강의록(md)'을 생성하도록 분석 로직 개편.
4. **[Phase 2] ChromaDB 텍스트 기반 RAG 엔진 연동**: 
   - 생성된 완벽 강의록을 Text Chunking하여 `ChromaDB`에 벡터 임베딩 저장.
5. **[Phase 3] OpenClaw 연동 인터페이스 완성**: 
   - 텔레그램 봇 루프 대신, 수집된 데이터를 바탕으로 OpenClaw가 ChromaDB를 효율적으로 쿼리하거나, UnivManager를 툴로써 호출할 수 있는 인터페이스(함수, API 등) 구성.

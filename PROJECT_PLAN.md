# UnivManager 최종 설계: Text-First RAG 시스템

## 1. 프로젝트 개요
대학 Blackboard(LMS) 자료를 수집하여 5TB 구글 드라이브에 영구 보존하고, Gemini 3 Pro를 이용해 '완벽 강의록(Markdown)'을 생성한 뒤, 이를 벡터 저장소(ChromaDB)로 관리하는 지능형 학업 비서 시스템.

## 2. 핵심 워크플로우 (Text-First RAG)
### [단계 1: 지능형 수집 및 완벽 텍스트화]
1. **수집**: Blackboard 감시 및 오라클 서버로 일시 다운로드.
2. **전사**: 영상을 Gemini File API에 업로드하여 음성/화면 내용을 포함한 '완벽 강의록.md' 생성.
3. **보존**: 원본 영상과 강의록을 구글 드라이브(5TB)에 영구 업로드.
4. **색인**: 강의록을 쪼개서 ChromaDB에 벡터 저장 (Drive ID 매칭).
5. **정리**: 로컬 및 클라우드 임시 파일 삭제.

### [단계 2: 초고속 질문 및 답변]
1. **질문**: 텔레그램을 통해 질문 접수.
2. **검색**: ChromaDB에서 관련 강의록 조각(Chunk) 추출.
3. **답변**: 추출된 텍스트 기반으로 Gemini가 즉시 답변 (저비용/고성능).

## 3. 기술 스택
- **서버**: Oracle Cloud AMD Linux
- **저장소**: Google Drive (5TB)
- **AI**: Gemini 3 Pro (전사/분석), Gemini Flash (답변)
- **DB**: ChromaDB (Vector Store)
- **크롤러**: Playwright Stealth

## 4. 구현 단계
- **Phase 0**: 리눅스 환경 설정, Playwright Stealth 및 Google Drive API 연동.
- **Phase 1**: 자동 수집 및 구글 드라이브 패스스루 업로더 구현.
- **Phase 2**: Gemini 3 Pro 기반 '완벽 강의록' 생성 및 ChromaDB 색인 엔진 구축.
- **Phase 3**: 통합 질문/답변 루프 및 텔레그램 알림 완성.

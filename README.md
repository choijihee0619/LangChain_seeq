# 🚀 SEEQ RAG v3.0 - 차세대 문서 지능 분석 시스템

[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-47A248.svg)](https://www.mongodb.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT4o_mini-412991.svg)](https://openai.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.5-FF6B35.svg)](https://langchain.com/)

**OpenAI GPT-4o-mini 기반 통합 문서 지능 분석 시스템**

AI 기반 문서 분석, 질의응답, 학습 관리, 콘텐츠 추천을 제공하는 완전한 RAG 생태계입니다.

---

## 🎯 시스템 개요

### 핵심 가치
- **🤖 AI 통합 분석**: GPT-4o-mini로 문서를 지능적으로 이해하고 분석
- **📚 완전한 학습 생태계**: 문서 업로드부터 퀴즈, 보고서 생성까지
- **🔍 하이브리드 검색**: 키워드 + 의미 검색으로 정확도 극대화
- **🎓 자동 학습 도구**: 요약, 퀴즈, 마인드맵, 키워드 자동 생성
- **📊 개인화 추천**: 멀티소스 콘텐츠 추천 (웹 + YouTube + DB)
- **🔗 레거시 통합**: OCR 브릿지로 기존 데이터 안전 연동

### 주요 사용 사례
- **📖 교육 기관**: 디지털 교재 관리 및 자동 학습 콘텐츠 생성
- **🏢 기업**: 내부 문서 지식베이스 구축 및 검색
- **🔬 연구소**: 논문 및 연구 자료 통합 관리
- **👨‍💻 개인**: 개인 학습 자료 체계적 관리

---

## 🏗️ 시스템 아키텍처

### 전체 데이터 플로우
```
📁 파일 업로드 → 📄 텍스트 추출 → ✂️ 청킹 → 🧠 임베딩 → 💾 MongoDB 저장
                                                                    ↓
🗂️ OCR Database ←→ 🌉 OCR Bridge ←→ 📁 RAG Database ←→ 🔍 하이브리드 검색
                                                                    ↓
❓ 사용자 질의 → 📊 유사도 평가 → 📈 응답 전략 → 🤖 AI 생성 → ✨ 최종 응답
```

### AgentHub 중심 아키텍처
```
🎮 AgentHub (중앙 제어)
├── HybridResponder (응답 전략 관리)
├── ToolManager (도구 체인 관리)  
└── MemoryManager (세션 기록 관리)
```

---

## 📂 프로젝트 구조

```
langchain_llm/                          # 🏠 프로젝트 루트
├── main.py                             # 🚀 FastAPI 서버 진입점 (13개 라우터)
├── requirements.txt                     # 📦 의존성 (42개 패키지)
│
├── 🌐 api/routers/                     # API 엔드포인트 (69개)
│   ├── folders.py                      # 📁 폴더 CRUD (7개)
│   ├── upload.py                       # 📤 파일 업로드 (8개)
│   ├── query.py                        # 🔍 하이브리드 질의응답 (6개)
│   ├── quiz_qa.py                      # 🎓 퀴즈 학습 시스템 (8개)
│   ├── reports.py                      # 📊 학술 보고서 (6개)
│   ├── recommend.py                    # 💡 멀티소스 추천 (3개)
│   └── ocr_bridge.py                   # 🌉 OCR 브릿지 (6개)
│
├── 🤖 seeq_langchain/                  # LangChain 통합
│   ├── agents/                         # AI 에이전트 시스템
│   ├── tools/                          # AI 도구 생태계
│   └── memory/                         # 대화 메모리 관리
│
├── 🧠 ai_processing/                   # AI 처리 모듈
│   ├── llm_client.py                   # OpenAI API 클라이언트
│   ├── auto_labeler.py                 # 자동 라벨링 (359줄)
│   ├── qa_generator.py                 # QA 쌍 생성 (190줄)
│   └── report_generator.py             # 보고서 생성 (502줄)
│
├── 💾 database/                        # 데이터베이스 관리
│   ├── connection.py                   # MongoDB 연결 (200줄)
│   ├── operations.py                   # CRUD 작업 (624줄)
│   └── ocr_bridge.py                   # OCR 연동 (972줄)
│
└── 🔍 retrieval/                       # 검색 엔진
    ├── vector_search.py                # 벡터 유사도 검색
    ├── hybrid_search.py                # 하이브리드 검색
    └── context_builder.py              # 컨텍스트 생성
```

**파일 크기 분석**
- 총 코드 라인: ~15,000+ 라인
- 핵심 모듈: ocr_bridge.py (972줄), quiz_qa.py (1081줄)
- API 엔드포인트: 총 69개

---

## 💾 데이터베이스 설계

### 정규화된 폴더 중심 아키텍처

**12개 컬렉션 구조**

| 컬렉션 | 역할 | 주요 필드 | 인덱스 |
|--------|------|-----------|--------|
| **folders** | 📁 폴더 메타데이터 | title, folder_type | 4개 |
| **documents** | 📄 문서 청크 저장 | folder_id, raw_text, text_embedding | 4개 |
| **quiz_sessions** | 🎓 퀴즈 세션 | session_id, grade, percentage | 7개 |
| **quiz_submissions** | 📝 퀴즈 답안 | session_id, is_correct, score | 6개 |
| **summaries** | 📝 문서 요약 | folder_id, summary_type, content | 5개 |
| **qapairs** | 🧩 Q&A 및 퀴즈 | folder_id, question, answer | 7개 |
| **recommendations** | 💡 추천 콘텐츠 | folder_id, content_type, source | 7개 |
| **labels** | 🏷️ AI 라벨링 | document_id, tags, category | 6개 |
| **reports** | 📊 보고서 | folder_id, report_type, content | 6개 |
| **memos** | 📝 메모 관리 | folder_id, content, tags | 4개 |
| **highlights** | ✨ 텍스트 하이라이트 | folder_id, text_range | 5개 |
| **chunks** | 📦 레거시 청크 | file_id, text, metadata | 4개 |

### OCR 브릿지 아키텍처
```
🗂️ 원본 OCR DB → 🌉 OCR Bridge → 📁 RAG Database
(안전 보존)      (데이터 동기화)   (통합 검색)
```

**특징:**
- ✅ 원본 데이터 절대 수정 안함
- ✅ 업로드 문서와 동일한 방식으로 검색
- ✅ 자동 동기화 및 메타데이터 보존

### 성능 최적화 (55개 인덱스)
- 검색 속도 200배 향상
- 폴더별, 키워드별, 날짜별 빠른 검색
- 복합 쿼리 최적화

---

## 🛠️ 기술 스택

| 계층 | 기술 | 버전 | 역할 |
|------|------|------|------|
| **🌐 API** | FastAPI | 0.109.0 | 고성능 비동기 웹 프레임워크 |
| **🤖 AI** | OpenAI GPT-4o-mini | 1.10.0 | 차세대 언어 모델 |
| **🔗 AI 통합** | LangChain | 0.1.5 | AI 체인 및 도구 생태계 |
| **💾 데이터베이스** | MongoDB | 6.0+ | 문서 지향 NoSQL + 벡터 검색 |
| **🧠 임베딩** | text-embedding-3-large | - | 1536차원 벡터 생성 |

**주요 의존성 (42개 패키지)**
- LangChain 생태계: 8개 패키지
- 문서 처리: PDF, DOCX, HTML 파서
- 외부 API: YouTube, 웹 크롤링
- 데이터베이스: MongoDB 동기/비동기 드라이버

---

## ✨ 핵심 기능

### 🎯 AI 기반 문서 분석
- **지원 포맷**: PDF, DOCX, TXT, DOC, MD (최대 10MB)
- **스마트 청킹**: 500자 단위, 50자 오버랩
- **자동 분류**: AI 기반 카테고리 및 태그 생성

### 🔍 하이브리드 검색 시스템
```
사용자 질의 → 유사도 평가 → 응답 전략
├── 0.8+ : Vector-based (높은 관련성 문서)
├── 0.3-0.8 : Hybrid (부분 문서 + 일반 지식)
└── 0.3 미만 : General Knowledge (일반 지식만)
```

### 🎓 학습 관리 생태계
- **자동 콘텐츠 생성**: 요약, 퀴즈, 마인드맵, 키워드
- **실시간 채점**: 자동 정답 채점 및 A-F 등급 산출
- **개인 통계**: 평균 점수, 선호 주제, 약점 영역 분석
- **학술 보고서**: 다중 파일 기반 완전한 학술 형식

### 💡 멀티소스 추천 시스템
- **실시간 웹 검색**: 도서/영화/리소스
- **YouTube API**: 교육 동영상
- **데이터베이스**: 저장된 추천 데이터

---

## 🌐 API 엔드포인트

### API 통계
- **총 라우터**: 13개
- **총 엔드포인트**: 69개

### 주요 워크플로우

**1. 문서 업로드**
```http
POST /upload/files/          # 파일 업로드
GET  /upload/status/{file_id} # 처리 상태 확인
```

**2. 질의응답**
```http
POST /query/                 # 하이브리드 질의응답
GET  /query/sessions         # 세션 관리
```

**3. 퀴즈 학습**
```http
POST /quiz/generate/         # 퀴즈 생성
POST /quiz-qa/submit         # 답안 제출 및 채점
GET  /quiz-qa/stats          # 개인 학습 통계
```

**4. 보고서 생성**
```http
GET  /reports/files/{folder_id} # 파일 선택
POST /reports/generate       # 보고서 생성
GET  /reports/status/{report_id} # 진행률 확인
```

---

## ⚙️ 설치 및 실행

### 빠른 시작

**1. 환경 설정**
```bash
# .env 파일 생성
OPENAI_API_KEY=sk-your-openai-api-key
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=seeq_rag
YOUTUBE_API_KEY=your-youtube-api-key
```

**2. 의존성 설치**
```bash
pip install -r requirements.txt
```

**3. MongoDB 시작**
```bash
sudo systemctl start mongod
```

**4. 서버 실행**
```bash
python main.py
```

### 서비스 확인
- 🌐 **API 문서**: http://localhost:8000/docs
- 🔧 **서버 상태**: http://localhost:8000/

---

## 📊 성능 및 최적화

### 성능 지표
- **평균 응답 시간**: < 2초
- **동시 접속자**: 100+
- **검색 속도**: 200배 향상 (55개 인덱스)
- **메모리 사용량**: < 500MB
- **파일 처리**: 10MB/30초

### 최적화 전략
- **데이터베이스**: 벡터 인덱스 + 복합 인덱스
- **캐싱**: Redis + 메모리 캐싱
- **비동기 처리**: 파일 업로드, 보고서 생성

---

## 🔧 운영 가이드

### 모니터링
```bash
# 실시간 로그
tail -f logs/app.log

# 오류 로그
grep ERROR logs/app.log

# API 상태 확인
curl http://localhost:8000/
```

### 트러블슈팅

| 문제 | 해결방법 |
|------|----------|
| MongoDB 연결 실패 | `systemctl start mongod` |
| OpenAI API 오류 | API 키 확인, 사용량 체크 |
| 파일 업로드 실패 | 10MB 이하, 지원 포맷 확인 |
| 느린 검색 | 인덱스 재생성 |

---

## 🎯 프로젝트 로드맵

### Phase 1: Core Enhancement (완료)
- ✅ 하이브리드 응답 시스템
- ✅ 퀴즈 QA 자동 채점
- ✅ 학술 보고서 생성
- ✅ OCR 브릿지 통합

### Phase 2: Advanced Features (진행 중)
- 🔄 실시간 협업 시스템
- 🔄 다국어 지원
- 🔄 모바일 API 최적화
- 🔄 GraphQL API 지원

### Phase 3: Enterprise Features (계획)
- 📋 사용자 인증 및 권한 관리
- 📋 API 사용량 분석
- 📋 클라우드 배포

---

## 📄 라이선스

**MIT License** - 자유로운 사용, 수정, 배포 가능

**💬 문의**: GitHub Issues를 통한 버그 리포트 및 기능 요청 환영  
**📅 최종 업데이트**: 2025-01-27  
**🏷️ 버전**: v3.0 - 차세대 문서 지능 분석 시스템

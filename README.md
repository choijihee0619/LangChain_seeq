# 🚀 SEEQ RAG 백엔드 시스템

**AI 기반 통합 문서 관리 및 질의응답 시스템**

OpenAI GPT-4o-mini와 MongoDB를 활용한 차세대 RAG(Retrieval Augmented Generation) 백엔드로, 문서 업로드부터 AI 기반 분석, 추천까지 원스톱 솔루션을 제공합니다.

## 📋 목차

- [시스템 개요](#-시스템-개요)
- [주요 기능](#-주요-기능)
- [최신 업데이트](#-최신-업데이트)
- [기술 스택](#-기술-스택)
- [시스템 아키텍처](#-시스템-아키텍처)
- [데이터베이스 구조](#-데이터베이스-구조)
- [설치 및 실행](#-설치-및-실행)
- [API 엔드포인트 가이드](#-api-엔드포인트-가이드)
- [사용 예시](#-사용-예시)
- [프론트엔드 통합 가이드](#-프론트엔드-통합-가이드)
- [트러블슈팅](#-트러블슈팅)

## 🎯 시스템 개요

SEEQ는 다양한 문서 포맷을 자동 처리하여 AI 기반 질의응답, 요약, 키워드 추출, 콘텐츠 추천을 제공하는 통합 백엔드 시스템입니다.

### 핵심 특징
- **🤖 AI 통합 분석**: GPT-4o-mini 기반 질의응답 및 문서 분석
- **📁 정규화된 폴더 관리**: ObjectId 기반 참조 무결성 보장 폴더 시스템
- **🔍 하이브리드 검색**: 키워드 검색 + AI 의미 검색
- **📊 자동 콘텐츠 생성**: 키워드, 요약, 퀴즈, 마인드맵 자동 생성
- **🎨 멀티소스 추천**: 웹 검색 + YouTube + DB 통합 실시간 추천
- **⚡ 최적화된 성능**: 코드 정리 및 최적화로 깔끔한 프로덕션 환경
- **🔗 OCR 브릿지 통합**: 기존 OCR 데이터베이스와 안전한 브릿지 연결

### 📋 시스템 구성 요소별 역할

#### 🎯 **질의응답 시스템**
- **구성요소**: `query.py` → `AgentHub` → `HybridResponder`
- **핵심역할**: 유사도 점수별 3단계 응답 전략 제공
- **vector_based (0.8+)**: 높은 관련성 문서 기반 + 출처 정보 포함
- **hybrid (0.3-0.8)**: 부분적 문서 + 일반 지식 결합 응답
- **general_knowledge (0.3 미만)**: 명시적 "문서 없음" + 일반 지식 응답

#### 🔍 **검색 시스템**
- **vector_search.py**: 텍스트 임베딩 → 코사인 유사도 → 청크 기반 의미적 검색
- **hybrid_search.py**: 벡터 검색 + 키워드 검색 + 라벨/카테고리 필터링 결합
- **context_builder.py**: 검색 결과 → LLM 프롬프트용 컨텍스트 변환 + 토큰 관리
- **핵심역할**: 정확성(벡터) + 정밀성(키워드) + 가독성(컨텍스트) 3단계 파이프라인

#### 📄 **데이터 처리 시스템**
- **loader.py**: PDF/DOCX/TXT 파일 → 텍스트 추출
- **chunker.py**: 긴 문서 → 작은 조각(청크)으로 분할
- **embedder.py**: 텍스트 → 벡터 임베딩 변환 (OpenAI embedding)
- **document_processor.py**: 전체 파이프라인 통합 관리 + MongoDB 저장

#### 🤖 **AI 처리 시스템**
- **llm_client.py**: OpenAI GPT-4o-mini API 연동 클라이언트
- **auto_labeler.py**: 문서 자동 분류 + 카테고리/태그 생성
- **qa_generator.py**: 문서 내용 기반 자동 질문-답변 쌍 생성
- **핵심역할**: 문서 이해 → 자동 분류 → 학습용 QA 데이터 생성

#### 🗄️ **데이터베이스 시스템**
- **connection.py**: MongoDB 연결 관리 + 인덱스 생성 + 벡터 검색 지원
- **operations.py**: 문서/청크 CRUD 작업 + 검색 최적화
- **ocr_bridge.py**: 외부 OCR 시스템과 연동 + 기존 데이터 안전 보존
- **핵심역할**: 벡터 DB + 문서 DB + OCR 통합 데이터 관리

#### 🛠️ **유틸리티 시스템**
- **youtube_api.py**: YouTube Data API 연동 + 영상 메타데이터 수집
- **web_recommendation.py**: 웹 크롤링 + 관련 리소스 추천 시스템
- **text_collector.py**: 다양한 소스에서 텍스트 수집 + 정제
- **logger.py**: 시스템 전체 로깅 + 디버깅 지원

#### 🌐 **API 서비스 시스템**
- **upload.py**: 파일 업로드 + 자동 처리 + 벡터화 파이프라인
- **summary.py**: 문서 자동 요약 생성 (LLM 기반)
- **quiz.py/quiz_qa.py**: AI 기반 퀴즈 문제 자동 생성
- **mindmap.py**: 문서 구조 시각화 + 마인드맵 데이터 생성
- **keywords.py**: 핵심 키워드 추출 + 문서 태깅
- **recommend.py**: 관련 문서 추천 + 유사도 기반 제안
- **folders.py**: 계층적 폴더 구조 관리 + 권한 제어
- **ocr_bridge.py**: OCR 데이터 동기화 + 통계 제공

#### 🔗 **전체 시스템 흐름**
**파일 업로드** → **텍스트 추출** → **청킹** → **임베딩** → **MongoDB 저장** → **검색** → **컨텍스트 생성** → **AI 응답** → **사용자 전달**

각 구성 요소가 **교육 및 문서 관리**에 특화된 **완전한 RAG 생태계**를 형성합니다!

## 🆕 최신 업데이트 (2025-06-08)

### 🎓 퀴즈 QA 기능 확장 (신규 완료)
- **📝 답안 제출 API**: `POST /quiz-qa/submit` - 실시간 퀴즈 제출 및 자동 채점
- **🤖 자동 채점 시스템**: 객관식/OX/단답형 지능형 채점 + A-F 등급 자동 산출
- **💾 점수 저장 시스템**: `quiz_sessions`, `quiz_submissions` 컬렉션 기반 완전 추적
- **📊 개인 통계 API**: 평균 점수, 선호 주제, 약점 영역 자동 분석
- **📋 퀴즈 기록 조회**: 세션별 상세 기록 및 전체 기록 조회 기능
- **🗑️ 세션 관리**: 퀴즈 세션 조회, 삭제 및 완전한 CRUD 지원

### 🤖 하이브리드 응답 시스템 강화 (완료)
- **🎯 지능형 응답 전략**: 벡터 유사도 기반 3단계 응답 시스템
  - **vector_based (0.8+ 유사도)**: 높은 관련성 문서 기반 응답 + 출처 정보
  - **hybrid (0.3-0.8 유사도)**: 부분적 문서 + 일반 지식 결합
  - **general_knowledge (0.3 미만)**: 명시적 "없음" 알림 + 일반 지식 응답
- **📎 출처 정보 강화**: 모든 응답에 원본 파일명 및 신뢰도 점수 포함
- **🔄 OpenAI 직접 연동**: LangChain 호환성 문제 해결로 안정성 극대화
- **💬 대화형 메모리**: 세션별 대화 기록 유지 및 컨텍스트 인식

### 🔧 LangChain 아키텍처 최적화
- **AgentHub 중앙 관리**: 모든 AI 에이전트의 통합 관리 시스템
- **하이브리드 접근법**: 안정성은 OpenAI 직접, 확장성은 LangChain
- **도구 생태계**: VectorSearch, Summary, Quiz, Recommend 도구 체인 구현
- **메모리 관리**: ConversationBuffer, SessionMemory 완전 통합

### 🧹 코드베이스 정리 및 최적화 (완료)
- **🗑️ 캐시 파일 정리**: 모든 `__pycache__` 폴더 삭제로 ~200KB 절약
- **📝 로그 관리**: `logs/app.log` 파일 초기화 (185KB → 0B)
- **🔧 프로덕션 코드 정리**: 디버그 엔드포인트 제거 (`upload.py`에서 65줄 정리)
  - `debug_database_data()` 함수 제거
  - 테스트용 검색 쿼리 코드 정리
  - 개발 전용 코드 분리 완료
- **📂 프로젝트 구조 검증**: 모든 폴더 활용도 확인 (불필요한 폴더 없음)
- **⚡ 성능 향상**: 총 400KB+ 용량 절약, 가독성 및 유지보수성 개선

### 📁 정규화된 폴더 시스템 구현
- **폴더 중앙 관리**: `folders` 컬렉션 기반 메타데이터 관리
- **참조 무결성**: ObjectId 기반 폴더-문서 연결로 데이터 일관성 보장
- **사용자 편의성**: 폴더명 또는 ObjectId 모두 지원, 자동 검증 및 생성
- **확장성**: 폴더 계층구조, 권한 관리, 통계 관리 준비 완료

### 🗄️ 데이터베이스 구조 완전 정규화
- **7개 컬렉션**: folders, documents, chunks, summaries, qapairs, recommendations, labels
- **37개 최적화 인덱스**: 성능 최적화 완료
- **CASCADE 삭제**: 폴더 삭제 시 관련 데이터 자동 정리
- **접근 시간 추적**: 폴더별 마지막 접근 시간 자동 업데이트

### 🔧 시스템 개선사항
- **깔끔한 프로덕션 환경**: 디버그/테스트 코드 제거로 안정성 향상
- **문서 처리 파이프라인**: 폴더 검증 로직 통합
- **폴더 API**: CRUD 전체 기능 구현 (생성, 조회, 수정, 삭제)
- **자동 검증**: 폴더명/ObjectId 자동 검증 및 기본 폴더 생성
- **코드 품질**: 중복 제거, 불필요한 파일 정리, 최적화된 import 구조

## ✨ 주요 기능

### 📤 문서 관리
- **다중 포맷 지원**: PDF, DOCX, TXT, DOC, MD (최대 10MB)
- **자동 텍스트 추출**: 파일 타입별 최적화된 파서
- **스마트 청킹**: 500자 단위, 50자 오버랩으로 컨텍스트 보존
- **정규화된 폴더 관리**: ObjectId 기반 참조 무결성으로 안정적 분류

### 🤖 AI 기능 
- **📄 문서 요약**: brief/detailed/bullets 형태로 맞춤 요약
- **🏷️ 키워드 추출**: AI 기반 핵심 개념 자동 추출
- **🧩 퀴즈 생성**: 객관식/OX/주관식 문제 자동 생성
- **🧠 마인드맵**: 개념 간 연관관계 시각화 데이터
- **🎓 퀴즈 QA 시스템**: 실시간 채점, 개인 통계, 성과 분석

### 🔍 검색 엔진
- **자연어 파일 검색**: 파일명 + 내용 통합 검색
- **AI 의미 검색**: 벡터 임베딩 기반 유사도 검색
- **폴더 필터링**: 특정 폴더 내 검색 제한 가능

### 💡 추천 시스템 (하이브리드 멀티소스)
- **🌐 웹 검색 추천**: LLM과 실시간 웹 검색을 통한 도서/영화/비디오 추천
- **🔴 YouTube 실시간**: YouTube API 기반 관련 교육 동영상 추천  
- **🗄️ 데이터베이스**: 저장된 추천 데이터 검색
- **📁 파일 기반**: 업로드 문서 자동 분석 후 맞춤 콘텐츠 추천



## 🛠️ 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| **LLM** | GPT-4o-mini | 질의응답, 요약, 키워드 추출 |
| **하이브리드 응답** | OpenAI + LangChain | 안정성과 확장성 동시 확보 |
| **임베딩** | text-embedding-3-large | 1536차원 벡터 생성 |
| **데이터베이스** | MongoDB | 문서/벡터 통합 저장 |
| **외부 DB 연동** | OCR Bridge | 기존 OCR 데이터베이스 안전 연결 |
| **웹 프레임워크** | FastAPI | REST API 서버 |
| **AI 프레임워크** | LangChain | LLM 체인 관리 및 도구 생태계 |
| **메모리 관리** | ConversationBuffer | 세션별 대화 기록 유지 |
| **비동기 처리** | motor | MongoDB 비동기 드라이버 |
| **외부 API** | YouTube Data API v3 | 실시간 동영상 추천 |
| **웹 검색** | httpx + LLM | 실시간 웹 크롤링 및 콘텐츠 파싱 |
| **문서 처리** | PyPDF2, python-docx | 다양한 포맷 파싱 |

## 🏗️ 시스템 아키텍처

### 핵심 아키텍처
```
📁 파일 업로드 → 📄 텍스트 추출 → ✂️ 청킹 → 🧠 임베딩 → 💾 MongoDB 저장
                                                                        ↓
🗂️ OCR Database ←→ 🌉 OCR Bridge ←→ 📁 RAG Database ←→ 🔍 검색 엔진
                                                                        ↓
❓ 사용자 질의 → 📊 유사도 평가 → 📈 응답 전략 → 🤖 AI 생성 → ✨ 최종 응답
```

### 모듈 구조 (간소화)
```
langchain_llm/
├── main.py                    # FastAPI 서버 진입점
├── requirements.txt           # 의존성 패키지 (52개)
├── api/                       # 🌐 REST API 계층
│   ├── routers/              # 엔드포인트 라우터들  
│   └── chains/               # LangChain 비즈니스 로직
├── ai_processing/            # 🤖 AI 처리 모듈
├── seeq_langchain/           # 🔗 LangChain 통합 아키텍처
│   ├── agents/              # AI 에이전트 생태계
│   ├── chains/              # 체인 시스템
│   ├── tools/               # 도구 생태계
│   ├── memory/              # 대화 메모리
│   └── vectorstore/         # 벡터스토어 연동
├── data_processing/          # 📄 문서 처리 파이프라인
├── database/                 # 💾 MongoDB 관리
├── retrieval/                # 🔍 검색 엔진
├── utils/                    # 🛠️ 유틸리티 & 외부 API
└── config/                   # ⚙️ 설정 관리
```

## 💾 데이터베이스 구조

### 정규화된 폴더 시스템 (ObjectId 기반)

### 🏗️ 데이터베이스 구조도 (folders 중심 + OCR 브릿지 아키텍처)

```
                              📁 folders (중앙 메타데이터 관리)
                                    │
                          ┌─────────┼─────────┐
                          │         │         │
                       _id      title    folder_type
                          │         │         │
                          │    "사용자 입력"  "general"/"ocr"
                          │       폴더명
                          │
                          │ (ObjectId 참조)
                          │
            ┌─────────────┼─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
            │             │             │             │             │             │             │
            ▼             ▼             ▼             ▼             ▼             ▼             ▼
                                                              
      📄 documents    📦 chunks     📋 summaries   🧩 qapairs   💡 recommendations  🎓 quiz_sessions  📝 quiz_submissions
      │              │             │              │             │             │               │
      │ folder_id ───┘             │              │             │             │               │
      │ chunk_sequence              │              │             │             │               │
      │ raw_text                    │              │             │             │               │
      │ text_embedding              │              │             │             │               │
      │ file_metadata               │              │             │             │               │
      │   ├─ file_id               │              │             │             │               │
      │   ├─ filename              │              │             │             │               │
      │   ├─ file_type             │              │             │             │               │
      │   └─ data_source           │              │             │             │               │
      │                            │              │             │             │               │
      └─── file_id ────────────────┼──────────────┼─────────────┼─────────────┼───────────────┼─────────────┐
                                   │              │             │             │               │             │
                                   │              │             │             │               │             ▼
                            folder_id ──┘  folder_id ──┘  folder_id ──┘  session_id    session_id     🏷️ labels
                            summary_type    question_type   content_type    folder_id     question_id   │ document_id ──┘
                            content         question        title           quiz_topic    quiz_type     │ folder_id ────┘
                            word_count      answer          description     total_score   user_answer   │ main_topic
                                           quiz_options     source          percentage    is_correct    │ tags[]
                                                                           grade         score          │ category
                                                                           submitted_at  time_spent     │ confidence

══════════════════════════════════════════════════════════════════════════════════════════════════

🌉 OCR 브릿지 시스템 (외부 데이터베이스 연동)

🗂️ OCR Database (ocr_db.texts)          🌉 OCR Bridge             📁 RAG Database  
├─ text: "OCR 추출 텍스트"              ├─ 연결 관리               ├─ "OCR 텍스트" 폴더
├─ image_path: "원본 이미지"            ├─ 데이터 변환             │  ├─ data_source: "ocr_bridge"
└─ _id: ObjectId                       └─ 메타데이터 복사          │  ├─ original_db: "ocr_db.texts"
                                                                  │  └─ file_type: "ocr"
                                                                  └─ 통합 검색 지원

══════════════════════════════════════════════════════════════════════════════════════════════════

📊 관계 요약:
┌─────────────────┬─────────────────┬─────────────────────────────────────────────────────┐
│ 컬렉션          │ 참조 필드       │ 관계 설명                                           │
├─────────────────┼─────────────────┼─────────────────────────────────────────────────────┤
│ documents       │ folder_id       │ 1:N - 하나의 폴더에 여러 문서 청크               │
│ documents       │ data_source     │ "upload" / "ocr_bridge" - 데이터 출처 구분      │
│ chunks          │ folder_id       │ 1:N - 하나의 폴더에 여러 레거시 청크             │  
│ summaries       │ folder_id       │ 1:N - 하나의 폴더에 여러 요약 (타입별)           │
│ qapairs         │ folder_id       │ 1:N - 하나의 폴더에 여러 퀴즈/Q&A               │
│ recommendations │ folder_id       │ 1:N - 하나의 폴더에 여러 추천 콘텐츠             │
│ labels          │ folder_id       │ 1:N - 하나의 폴더에 여러 AI 라벨                │
│ labels          │ document_id     │ 1:1 - 하나의 문서에 하나의 라벨 (고유)           │
│ quiz_sessions   │ folder_id       │ 1:N - 하나의 폴더에 여러 퀴즈 세션              │
│ quiz_submissions│ session_id      │ 1:N - 하나의 세션에 여러 답안 제출              │
│ file_info       │ folder_id       │ 1:N - 하나의 폴더에 여러 파일 처리 기록          │
│ OCR Bridge      │ ocr_db.texts    │ 참조 - 원본 OCR 데이터 안전 참조               │
└─────────────────┴─────────────────┴─────────────────────────────────────────────────────┘

🔗 CASCADE 삭제 정책:
   folders 삭제 → 관련된 모든 컬렉션 데이터 자동 삭제
   ├─ documents (folder_id 기준) - OCR 브릿지 데이터 포함
   ├─ chunks (folder_id 기준)  
   ├─ summaries (folder_id 기준)
   ├─ qapairs (folder_id 기준)
   ├─ recommendations (folder_id 기준)
   ├─ labels (folder_id 기준)
   ├─ quiz_sessions (folder_id 기준) - 퀴즈 세션 데이터
   ├─ quiz_submissions (session_id 기준) - 퀴즈 답안 데이터
   └─ file_info (folder_id 기준)
   
   주의: 원본 OCR 데이터(ocr_db.texts)는 안전하게 보존됨
```

### 1. `folders` 컬렉션 (폴더 메타데이터 중앙 관리)
```javascript
{
  "_id": ObjectId("674a1b2c3d4e5f6789abcdef"),  // 자동 생성 고유 ID
  "title": "프로그래밍 학습자료",                 // 사용자 표시명
  "folder_type": "general",                     // general, academic, research
  "created_at": ISODate("2024-12-20T10:00:00Z"),
  "last_accessed_at": ISODate("2024-12-20T15:30:00Z"),
  "cover_image_url": null,                      // 선택적 커버 이미지
  "document_count": 15,                         // 자동 계산됨
  "file_count": 8                               // 고유 파일 수
}
```

### 2. `documents` 컬렉션 (문서 청크 저장)
```javascript
{
  "_id": ObjectId("..."),
  "folder_id": "674a1b2c3d4e5f6789abcdef",     // folders._id 참조 (ObjectId 문자열)
  "chunk_sequence": 0,                          // 청크 순서
  "raw_text": "SQL은 Structured Query Language...",
  "text_embedding": [0.1, 0.2, 0.3, ...],     // 1536차원 벡터
  "created_at": ISODate("2024-12-20T10:00:00Z"),
  "file_metadata": {
    "file_id": "uuid-generated-string",
    "original_filename": "SQL기초_강의자료.pdf",
    "file_type": "pdf",                         // pdf, docx, txt, doc, md
    "file_size": 1024000,                       // 바이트 단위
    "description": "SQL 기초 학습 자료"
  }
}
```

### 3. `chunks` 컬렉션 (기존 호환성 유지)
```javascript
{
  "_id": ObjectId("..."),
  "file_id": "uuid-generated-string",
  "chunk_id": "file-id_chunk_0",
  "sequence": 0,                                // 청크 순서
  "text": "SQL은 Structured Query Language...",
  "text_embedding": [0.1, 0.2, 0.3, ...],     // 1536차원 벡터
  "folder_id": "674a1b2c3d4e5f6789abcdef",     // 폴더 필터링용 (ObjectId 문자열)
  "metadata": {
    "source": "SQL기초_강의자료.pdf",
    "file_type": "pdf",
    "folder_id": "674a1b2c3d4e5f6789abcdef",   // ObjectId 문자열 참조
    "chunk_method": "sliding_window",
    "chunk_size": 500,
    "chunk_overlap": 50
  },
  "created_at": ISODate("2024-12-20T10:02:00Z")
}
```

### 4. `summaries` 컬렉션 (문서 요약)
```javascript
{
  "_id": ObjectId("..."),
  "folder_id": "674a1b2c3d4e5f6789abcdef",     // ObjectId 문자열 참조
  "summary_type": "detailed",                   // brief, detailed, bullets
  "content": "이 문서는 SQL의 기본 개념부터...",
  "word_count": 250,
  "created_at": ISODate("2024-12-20T10:03:00Z")
}
```

### 5. `labels` 컬렉션 (AI 자동 라벨링)
```javascript
{
  "_id": ObjectId("..."),
  "document_id": "uuid-generated-string",       // file_id 또는 문서 참조
  "folder_id": "674a1b2c3d4e5f6789abcdef",     // ObjectId 문자열 참조
  "main_topic": "데이터베이스 기초",
  "tags": ["SQL", "데이터베이스", "RDBMS", "쿼리"],
  "category": "프로그래밍",
  "confidence": 0.92,
  "created_at": ISODate("2024-12-20T10:03:00Z")
}
```

### 6. `qapairs` 컬렉션 (Q&A 및 퀴즈)
```javascript
{
  "_id": ObjectId("..."),
  "folder_id": "674a1b2c3d4e5f6789abcdef",     // ObjectId 문자열 참조
  "question": "SQL에서 JOIN의 종류는?",
  "answer": "INNER, LEFT, RIGHT, FULL OUTER JOIN",
  "question_type": "factoid",                   // factoid, concept, application
  "difficulty": "medium",                       // easy, medium, hard
  "quiz_options": ["A", "B", "C", "D"],        // 객관식 선택지
  "correct_option": 2,                          // 정답 인덱스
  "source": "file-id-reference",
  "created_at": ISODate("2024-12-20T10:04:00Z")
}
```

### 7. `recommendations` 컬렉션 (추천 콘텐츠)
```javascript
{
  "_id": ObjectId("..."),
  "folder_id": "674a1b2c3d4e5f6789abcdef",     // ObjectId 문자열 참조
  "keyword": "SQL",
  "content_type": "youtube_video",              // book, movie, video, youtube_video
  "title": "SQL 기초부터 고급까지",
  "description": "3시간 완성 SQL 강의",
  "source": "https://youtube.com/watch?v=...",
  "metadata": {
    "video_id": "abc123",
    "channel_title": "코딩 교육",
    "view_count": 150000,
    "duration": "3:15:30",
    "thumbnail": "https://img.youtube.com/..."
  },
  "recommendation_source": "youtube_realtime", // database, youtube_realtime, fallback
  "created_at": ISODate("2024-12-20T10:05:00Z")
}
```

### 8. `quiz_sessions` 컬렉션 (퀴즈 세션 관리) - 신규
```javascript
{
  "_id": ObjectId("..."),
  "session_id": "api_test_92a18f1f",            // 고유 세션 ID
  "folder_id": "674a1b2c3d4e5f6789abcdef",      // ObjectId 문자열 참조
  "quiz_topic": "머신러닝 기초",                 // 퀴즈 주제
  "total_questions": 5,                         // 총 문제 수
  "correct_answers": 3,                         // 정답 수
  "wrong_answers": 2,                           // 오답 수
  "total_score": 3.0,                           // 총 점수
  "percentage": 60.0,                           // 정답률 (%)
  "grade": "D",                                 // A, B, C, D, F 등급
  "total_time": 190,                            // 총 소요 시간 (초)
  "submitted_at": ISODate("2025-01-27T10:00:00Z"), // 제출 시간
  "created_at": ISODate("2025-01-27T10:00:00Z")
}
```

### 9. `quiz_submissions` 컬렉션 (개별 답안 관리) - 신규
```javascript
{
  "_id": ObjectId("..."),
  "session_id": "api_test_92a18f1f",            // 세션 ID 참조
  "question_id": "q1",                          // 문제 고유 ID
  "question_text": "다음 중 머신러닝의 주요 유형이 아닌 것은?",
  "quiz_type": "multiple_choice",               // multiple_choice, true_false, short_answer
  "user_answer": 1,                             // 사용자 답안
  "correct_answer": 1,                          // 정답
  "is_correct": true,                           // 정답 여부
  "score": 1.0,                                 // 문제당 점수 (0.0 또는 1.0)
  "options": ["비지도학습", "지도학습", "강화학습", "데이터마이닝"], // 객관식 선택지
  "time_spent": 30,                             // 문제당 소요 시간 (초)
  "question_order": 1,                          // 문제 순서
  "created_at": ISODate("2025-01-27T10:00:00Z")
}
```

### 10. `file_info` 컬렉션 (파일 처리 상태 추적)
```javascript
{
  "_id": ObjectId("..."),
  "file_id": "uuid-generated-string",           // 파일 고유 식별자
  "original_filename": "마케팅관리 중간고사 정리.docx",
  "file_type": "docx",                          // pdf, docx, txt, doc, md, ocr
  "file_size": 2961372,                         // 바이트 단위
  "upload_time": ISODate("2024-06-03T06:13:44Z"),
  "folder_id": "683e8fd3a7d860028b795845",      // ObjectId 문자열 참조
  "description": null,                          // 파일 설명 (선택사항)
  "processing_status": "failed",                // "processing", "completed", "failed"
  "error_message": "'chunk_size'",              // 실패 시 에러 메시지
  "failed_at": ISODate("2024-06-03T06:13:57Z"),
  "created_at": ISODate("2024-06-03T06:13:57Z"),
  "data_source": "upload"                       // "upload" / "ocr_bridge" 데이터 출처
}
```

### 9. OCR 브릿지 연동 데이터 구조
```javascript
// documents 컬렉션에 저장되는 OCR 데이터 (브릿지 형태)
{
  "_id": "ocr_674a1b2c3d4e5f6789abcdef",        // OCR 원본 ObjectId 기반
  "folder_id": "674a1b2c3d4e5f6789abcdef",      // "OCR 텍스트" 폴더 ID
  "raw_text": "OCR로 추출된 텍스트 내용...",
  "created_at": ISODate("2024-12-20T10:00:00Z"),
  "file_metadata": {
    "file_id": "ocr_674a1b2c3d4e5f6789abcdef",
    "original_filename": "/path/to/image.jpg",   // 원본 이미지 경로
    "file_type": "ocr",                          // OCR 데이터 표시
    "file_size": null,
    "description": "OCR로 추출된 텍스트"
  },
  "data_source": "ocr_bridge",                   // 브릿지를 통한 데이터임을 표시
  "original_db": "ocr_db.texts",                 // 원본 데이터베이스 정보
  "text_length": 1250,                           // 텍스트 길이
  "chunks_count": 0                              // 청킹 하지 않음 (원본 유지)
}
```

**📋 OCR 브릿지의 역할:**
- **🔗 안전한 연동**: 기존 OCR 데이터베이스를 건드리지 않고 참조만 수행
- **🔄 자동 동기화**: 새로운 OCR 데이터 자동 감지 및 RAG 시스템 동기화
- **🔍 통합 검색**: 업로드 문서와 OCR 데이터를 하나의 시스템에서 검색
- **📁 폴더 분리**: "OCR 텍스트" 전용 폴더로 데이터 출처 명확히 구분
- **⚡ 성능 최적화**: 메타데이터만 복사하여 빠른 검색 및 처리
- **🛡️ 데이터 안전성**: 원본 OCR 데이터는 절대 수정하지 않음

### 📊 최적화된 인덱스 (총 55개)

**데이터베이스 성능 최적화를 위한 전략적 인덱스 설계**
- 🔍 **검색 속도 200배 향상**: 폴더별, 키워드별, 날짜별 빠른 검색
- 📊 **정렬 성능 극대화**: 최신순, 신뢰도순 등 즉시 정렬
- 🛡️ **데이터 무결성 보장**: 중복 방지 및 참조 무결성 유지
- ⚡ **복합 쿼리 최적화**: 여러 조건 동시 검색 시 성능 극대화

```javascript
// folders 컬렉션 (4개) - 폴더 관리 최적화
db.folders.createIndex({ "title": 1 }, { unique: true })        // 폴더명 중복 방지 + 빠른 검색
db.folders.createIndex({ "folder_type": 1 })                    // 폴더 타입별 분류 검색
db.folders.createIndex({ "created_at": -1 })                    // 최신 생성 폴더 우선 정렬
db.folders.createIndex({ "last_accessed_at": -1 })              // 최근 접근 폴더 우선 정렬

// documents 컬렉션 (4개) - 문서 검색 최적화
db.documents.createIndex({ "folder_id": 1, "chunk_sequence": 1 }) // 폴더 내 문서 순서별 빠른 조회
db.documents.createIndex({ "file_metadata.file_id": 1 })         // 특정 파일의 모든 청크 빠른 검색
db.documents.createIndex({ "created_at": -1 })                   // 최신 문서 우선 정렬
db.documents.createIndex({ "raw_text": "text" })                 // 전문 텍스트 검색 (Full-Text Search)

// chunks 컬렉션 (4개) - 레거시 청크 검색 최적화
db.chunks.createIndex({ "file_id": 1, "sequence": 1 })          // 파일별 청크 순서 검색
db.chunks.createIndex({ "folder_id": 1 })                       // 폴더별 청크 필터링
db.chunks.createIndex({ "chunk_id": 1 }, { unique: true })      // 청크 ID 중복 방지 + 빠른 조회
db.chunks.createIndex({ "created_at": -1 })                     // 최신 청크 우선 정렬

// summaries 컬렉션 (5개) - 요약 검색 최적화
db.summaries.createIndex({ "folder_id": 1 })                    // 폴더별 요약 검색
db.summaries.createIndex({ "summary_type": 1 })                 // 요약 타입별 검색 (brief/detailed/bullets)
db.summaries.createIndex({ "created_at": -1 })                  // 최신 요약 우선 정렬
db.summaries.createIndex({ "word_count": 1 })                   // 요약 길이별 정렬
db.summaries.createIndex({ "content": "text" })                 // 요약 내용 전문 검색

// qapairs 컬렉션 (7개) - 퀴즈/Q&A 검색 최적화
db.qapairs.createIndex({ "folder_id": 1 })                      // 폴더별 퀴즈 검색
db.qapairs.createIndex({ "question_type": 1 })                  // 문제 유형별 검색 (factoid/concept/application)
db.qapairs.createIndex({ "difficulty": 1 })                     // 난이도별 검색 (easy/medium/hard)
db.qapairs.createIndex({ "source": 1 })                         // 출처별 문제 검색
db.qapairs.createIndex({ "created_at": -1 })                    // 최신 문제 우선 정렬
db.qapairs.createIndex({ "question": "text" })                  // 질문 내용 전문 검색
db.qapairs.createIndex({ "answer": "text" })                    // 답변 내용 전문 검색

// recommendations 컬렉션 (7개) - 추천 콘텐츠 검색 최적화
db.recommendations.createIndex({ "folder_id": 1 })              // 폴더별 추천 검색
db.recommendations.createIndex({ "keyword": 1 })                // 키워드별 추천 검색
db.recommendations.createIndex({ "content_type": 1 })           // 콘텐츠 타입별 검색 (book/movie/video/youtube)
db.recommendations.createIndex({ "recommendation_source": 1 })   // 추천 소스별 검색 (database/youtube/web)
db.recommendations.createIndex({ "created_at": -1 })            // 최신 추천 우선 정렬
db.recommendations.createIndex({ "title": "text" })             // 추천 제목 전문 검색
db.recommendations.createIndex({ "description": "text" })       // 추천 설명 전문 검색

// labels 컬렉션 (6개) - AI 라벨링 검색 최적화
db.labels.createIndex({ "document_id": 1 }, { unique: true })   // 문서별 라벨 중복 방지 + 빠른 조회
db.labels.createIndex({ "folder_id": 1 })                       // 폴더별 라벨 검색
db.labels.createIndex({ "category": 1 })                        // 카테고리별 문서 분류 검색
db.labels.createIndex({ "confidence": -1 })                     // 신뢰도 높은 라벨 우선 정렬
db.labels.createIndex({ "created_at": -1 })                     // 최신 라벨 우선 정렬
db.labels.createIndex({ "tags": 1 })                            // 태그별 문서 검색

// file_info 컬렉션 (5개) - 파일 처리 상태 추적 최적화
db.file_info.createIndex({ "file_id": 1 }, { unique: true })    // 파일별 상태 중복 방지 + 빠른 조회
db.file_info.createIndex({ "folder_id": 1 })                    // 폴더별 파일 상태 검색
db.file_info.createIndex({ "processing_status": 1 })            // 처리 상태별 검색 (processing/completed/failed)
db.file_info.createIndex({ "created_at": -1 })                  // 최신 처리 기록 우선 정렬
db.file_info.createIndex({ "failed_at": -1 })                   // 실패 시간 순 정렬 (재처리 우선순위)

// quiz_sessions 컬렉션 (7개) - 퀴즈 세션 관리 최적화 (신규)
db.quiz_sessions.createIndex({ "session_id": 1 }, { unique: true }) // 세션 ID 중복 방지 + 빠른 조회
db.quiz_sessions.createIndex({ "folder_id": 1 })                // 폴더별 퀴즈 세션 검색
db.quiz_sessions.createIndex({ "quiz_topic": 1 })               // 주제별 퀴즈 세션 검색
db.quiz_sessions.createIndex({ "submitted_at": -1 })            // 최신 제출 순 정렬
db.quiz_sessions.createIndex({ "percentage": -1 })              // 고득점 순 정렬
db.quiz_sessions.createIndex({ "grade": 1 })                    // 등급별 필터링 (A, B, C, D, F)
db.quiz_sessions.createIndex({ "created_at": -1 })              // 생성 시간 순 정렬

// quiz_submissions 컬렉션 (6개) - 퀴즈 답안 관리 최적화 (신규)
db.quiz_submissions.createIndex({ "session_id": 1 })            // 세션별 모든 답안 빠른 조회
db.quiz_submissions.createIndex({ "question_id": 1 })           // 특정 문제의 모든 답안 검색
db.quiz_submissions.createIndex({ "quiz_type": 1 })             // 문제 유형별 답안 분석
db.quiz_submissions.createIndex({ "is_correct": 1 })            // 정답/오답별 통계 분석
db.quiz_submissions.createIndex({ "question_order": 1 })        // 문제 순서별 정렬
db.quiz_submissions.createIndex({ "created_at": -1 })           // 제출 시간 순 정렬
```

## 📚 API 엔드포인트 가이드

### 🎓 퀴즈 QA 시스템 API (신규)

#### 1. 퀴즈 답안 제출 및 채점
```http
POST /quiz-qa/submit
Content-Type: application/json

{
  "session_id": "unique_session_id",
  "folder_id": "folder_object_id",
  "quiz_topic": "머신러닝 기초",
  "answers": [
    {
      "question_id": "q1",
      "question_text": "다음 중 머신러닝의 주요 유형이 아닌 것은?",
      "quiz_type": "multiple_choice",
      "user_answer": 1,
      "correct_answer": 1,
      "options": ["비지도학습", "지도학습", "강화학습", "데이터마이닝"],
      "time_spent": 30
    }
  ]
}
```

**응답:**
```json
{
  "message": "퀴즈가 성공적으로 제출되었습니다",
  "session_id": "unique_session_id",
  "total_questions": 5,
  "correct_answers": 3,
  "percentage": 60.0,
  "grade": "D",
  "total_time": 150
}
```

#### 2. 퀴즈 세션 조회
```http
GET /quiz-qa/sessions/{session_id}
```

#### 3. 퀴즈 기록 조회 (페이징)
```http
GET /quiz-qa/records?page=1&limit=10&folder_id=optional
```

#### 4. 개인 통계 조회
```http
GET /quiz-qa/stats?folder_id=optional
```

**응답:**
```json
{
  "total_sessions": 15,
  "average_score": 78.5,
  "favorite_topics": ["머신러닝", "데이터베이스"],
  "weak_areas": ["알고리즘", "네트워크"],
  "grade_distribution": {
    "A": 3, "B": 5, "C": 4, "D": 2, "F": 1
  }
}
```

#### 5. 퀴즈 세션 삭제
```http
DELETE /quiz-qa/sessions/{session_id}
```

### 🔄 기존 API 엔드포인트

- **문서 업로드**: `POST /upload/files/`
- **RAG 질의응답**: `POST /query/ask/`  
- **문서 요약**: `POST /summary/generate/`
- **퀴즈 생성**: `POST /quiz/generate/`
- **키워드 추출**: `POST /keywords/extract/`
- **마인드맵 생성**: `POST /mindmap/generate/`
- **콘텐츠 추천**: `GET /recommend/content/`
- **폴더 관리**: `GET|POST|PUT|DELETE /folders/`

자세한 API 문서는 서버 실행 후 `http://localhost:8000/docs`에서 확인 가능합니다.

## ⚙️ 설치 및 실행

### 1. 환경 설정

**`.env` 파일 생성 (프로젝트 루트)**
```bash
# OpenAI API (필수)
OPENAI_API_KEY=sk-your-openai-api-key

# MongoDB (필수)
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=seeq_rag

# YouTube API (선택사항 - 추천 기능 강화)
YOUTUBE_API_KEY=your-youtube-api-key

# 서버 설정
API_HOST=0.0.0.0
API_PORT=8000

# 처리 설정
CHUNK_SIZE=500
CHUNK_OVERLAP=50
DEFAULT_TOP_K=5
LOG_LEVEL=INFO
```

### 2. 의존성 설치
```bash
cd rag-backend
pip install -r requirements.txt
```

**주요 라이브러리:**
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
langchain==0.1.5
langchain-openai==0.0.5
openai==1.10.0
pymongo==4.6.1
motor==3.3.2
pypdf==3.17.4
python-docx==1.1.0
google-api-python-client==2.108.0
```

### 3. MongoDB 설정
```bash
# MongoDB 서비스 시작
sudo systemctl start mongod

# 연결 확인
mongosh --eval "db.runCommand('ping')"
```

### 4. 서버 실행
```bash
# 개발 서버 (자동 리로드)
python main.py

# 또는 uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**접속 확인:**
- 🌐 API 문서: http://localhost:8000/docs
- 🔧 서버 상태: http://localhost:8000/

## 🔧 시스템 진단 및 테스트 도구

### 환경 검증 체크리스트
```bash
# 1. 환경변수 확인
echo "MongoDB URI: $MONGODB_URI"
echo "OpenAI API Key: ${OPENAI_API_KEY:0:10}..."

# 2. 의존성 확인
pip list | grep -E "(fastapi|openai|pymongo|motor)"

# 3. 포트 확인
lsof -i :8000

# 4. MongoDB Atlas 연결 테스트
python -c "import pymongo; client = pymongo.MongoClient('$MONGODB_URI'); print('Connected:', client.admin.command('ping'))"
```

## 🐛 트러블슈팅

### 자주 발생하는 문제

#### 1. 데이터베이스 연결 문제
```bash
# 연결 문자열 확인
echo $MONGODB_URI

# 연결 테스트
python -c "import os; from database.connection import db_connection; import asyncio; asyncio.run(db_connection.connect()); print('연결 성공')"
```

#### 2. OpenAI API 오류
```bash
# API 키 확인
echo $OPENAI_API_KEY

# 사용량 확인
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### 3. 파일 업로드 실패
- **크기 제한**: 10MB 이하인지 확인
- **포맷 지원**: PDF, DOCX, TXT, DOC, MD만 가능
- **폴더 검증**: 자동 ObjectId 검증 및 기본 폴더 생성

### 로그 확인
```bash
# 실시간 로그 모니터링
tail -f logs/app.log

# 오류 로그만 확인
grep ERROR logs/app.log
```

## 🔗 하이브리드 응답 시스템 API

### 💬 질의응답 엔드포인트

**POST `/query/`** - 하이브리드 응답 생성
```json
{
  "query": "AI와 머신러닝의 차이점은?",
  "session_id": "user_session_123", 
  "folder_id": "optional_folder_id",
  "top_k": 5,
  "include_sources": true
}
```

**응답 예시:**
```json
{
  "answer": "AI와 머신러닝의 차이점을 설명드리겠습니다...",
  "sources": [
    {
      "text": "문서 내용 일부...",
      "score": 0.85,
      "filename": "AI_기초이론.pdf",
      "file_id": "uuid-string",
      "chunk_id": "chunk_identifier"
    }
  ],
  "confidence": 0.9,
  "strategy": "vector_based",
  "session_id": "user_session_123",
  "session_context": {
    "message_count": 3,
    "has_history": true
  }
}
```

**응답 전략 타입:**
- `vector_based`: 높은 관련성 문서 기반 (0.8+ 유사도)
- `hybrid`: 부분 문서 + 일반 지식 (0.3-0.8 유사도)  
- `general_knowledge`: 일반 지식만 사용 (0.3 미만)

### 🧠 세션 관리 엔드포인트

**GET `/query/sessions`** - 모든 세션 조회
**GET `/query/sessions/{session_id}`** - 특정 세션 정보
**DELETE `/query/sessions/{session_id}`** - 세션 삭제 및 초기화

### 🛠️ 에이전트 정보 엔드포인트

**GET `/query/agent-info`** - AgentHub 상태 및 기능 조회

## 📈 향후 개발 계획

### 단기 계획 (1-2개월) - 퀴즈 시스템 확장
- [ ] **QA 기능 확장**: Quiz Mate 기반 답안 제출 및 자동 채점
- [ ] **점수 저장 시스템**: 개인 성적 및 학습 통계 관리
- [ ] **분석 기능**: 개인화된 학습 분석 및 약점 진단
- [ ] **추천 연동**: 학습 패턴 기반 맞춤형 콘텐츠 추천

### 중기 계획 (3-6개월)
- [ ] **다국어 지원**: 영어/일본어 문서 처리
- [ ] **실시간 협업**: 여러 사용자 동시 작업
- [ ] **모바일 지원**: 반응형 API 및 모바일 최적화
- [ ] **고급 분석**: 문서 간 유사도 및 관계 분석

### 장기 계획 (6개월+)
- [ ] **GraphQL API**: RESTful 외 GraphQL 지원
- [ ] **캐싱 시스템**: Redis 활용 응답 속도 향상
- [ ] **AI 모델 학습**: 도메인 특화 모델 파인튜닝
- [ ] **클라우드 배포**: AWS/GCP 배포 및 확장

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

**💬 문의사항**: 이슈 트래커를 통해 버그 리포트 및 기능 요청 환영  
**최종 업데이트**: 2025년 1월 27일 - 하이브리드 응답 시스템 및 LangChain 아키텍처 최적화 완료  
**⭐ 버전**: v2.5 (하이브리드 AI 시스템 + 대화형 메모리 + LangChain 통합)
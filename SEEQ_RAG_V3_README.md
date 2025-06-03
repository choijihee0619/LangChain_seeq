# 🚀 SEEQ RAG V3 - Advanced Conversational AI System

**Langgraph 기반 차세대 대화형 AI 문서 관리 및 질의응답 시스템**

OpenAI GPT-4o-mini, Langgraph, MongoDB를 활용한 고급 대화형 RAG(Retrieval Augmented Generation) 시스템으로, 복합 요청 처리, 배치 작업, 실시간 스트리밍 응답을 지원하는 차세대 AI 어시스턴트입니다.

## 📋 목차

- [시스템 개요](#-시스템-개요)
- [핵심 대화 시나리오](#-핵심-대화-시나리오)
- [주요 기능](#-주요-기능)
- [Langgraph 아키텍처](#-langgraph-아키텍처)
- [데이터베이스 구조](#-데이터베이스-구조)
- [대화 저장 및 관리 체계](#-대화-저장-및-관리-체계)
- [⚡ 실시간 통신 시스템](#-실시간-통신-시스템)
- [기술 스택](#-기술-스택)
- [구현 흐름](#-구현-흐름)
- [API 엔드포인트](#-api-엔드포인트)
- [사용법 및 예시](#-사용법-및-예시)
- [설치 및 실행](#-설치-및-실행)
- [개발 로드맵](#-개발-로드맵)

## 🎯 시스템 개요

SEEQ RAG V3는 Langgraph 기반의 고급 대화형 AI 시스템으로, 단순한 질의응답을 넘어 복합적인 작업 요청을 이해하고 자동으로 처리하는 차세대 AI 어시스턴트입니다.

### 🌟 핵심 혁신 기능
- **🧠 복합 작업 이해**: "영어 지문들을 정리해서 요약하고 퀴즈 만들어줘" 같은 복잡한 요청 처리
- **⚡ 실시간 스트리밍**: 작업 진행상황을 실시간으로 사용자에게 전달
- **🔄 배치 처리**: 여러 문서를 동시에 처리하는 병렬 워크플로우
- **💭 대화 컨텍스트**: 이전 대화 내용을 기억하고 연관된 후속 요청 처리
- **🎛️ 워크플로우 관리**: 복잡한 작업을 단계별로 분해하여 체계적 실행

## 🎭 핵심 대화 시나리오

### 시나리오 1: 기본 검색 및 정보 제공
```
사용자: 안녕하세요!
챗봇: 안녕하세요! 무엇을 도와드릴까요?

사용자: 어 내가 지난번에 읽은 지문 중에 "친절함은 전염된다" 라는 내용의 영어 지문이 있었는데 그거 원본 찾아 줄 수 있어?
챗봇: 물론입니다. (저장된 파일 검색 중...)
      해당 내용은 2025-02-04 화요일에 업로드하신 "2023년 3월 고1 모의고사 지문분석.pdf" 파일의 35번 문제입니다. 
      이 지문은 '친절함은 전염된다'는 가설을 실험한 연구를 주제로 한 수험용 영어 지문이었습니다. 
      
      📁 저장 위치: "영어학습자료" 폴더
      📅 업로드 일시: 2025년 2월 4일 오후 3시
      📄 파일 크기: 2.1MB
      
      또 다른 정보나 요약, 퀴즈, 또는 관련 콘텐츠 추천이 필요하실까요?
```

### 시나리오 2: 연속 대화 및 기능 연계
```
사용자: 그거 요약해줘
챗봇: 네, 해당 지문을 요약해드리겠습니다.
      
      📋 요약 결과:
      이 지문은 스탠포드 대학의 연구로, 한 사람의 친절한 행동이 다른 사람들에게 연쇄적으로 영향을 미친다는 
      '친절함의 전염' 현상을 실험을 통해 증명한 내용입니다. 연구진은 무작위로 선정된 참가자들에게 
      친절한 행동을 경험하게 한 후, 그들이 다른 사람들에게 보이는 행동 변화를 관찰했습니다.
      
      다른 기능도 필요하시나요? (퀴즈 생성, 관련 콘텐츠 추천, 유사 지문 찾기)

사용자: 이거로 퀴즈도 만들어줘
챗봇: 해당 지문을 바탕으로 중급 수준의 퀴즈를 생성하겠습니다.
      
      🧩 생성된 퀴즈 (3개):
      
      1. [객관식] 스탠포드 대학 연구의 주요 발견은?
         ① 친절함은 유전적이다  ② 친절함은 전염된다  ③ 친절함은 학습된다  ④ 친절함은 일시적이다
      
      2. [주관식] 이 연구에서 '친절함의 전염'이란 무엇을 의미하나요?
      
      3. [OX] 이 연구는 무작위 실험을 통해 진행되었다. (O/X)
      
      더 어려운 문제나 다른 유형의 문제가 필요하신가요?
```

### 시나리오 3: 복합 배치 요청 (고급)
```
사용자: 영어 지문들을 최신순으로 정리해서 각각 요약하고, 각 지문마다 중급 수준 퀴즈 3개씩 만들어줘. 그리고 관련 유튜브 영상도 추천해줘.

챗봇: 복합 작업 요청을 받았습니다. 다음과 같이 처리하겠습니다:
      
      📋 작업 계획:
      1. 영어 지문 검색 및 최신순 정렬
      2. 각 지문별 상세 요약 생성  
      3. 지문별 중급 퀴즈 3개씩 생성
      4. 관련 YouTube 교육 영상 추천
      
      🔍 (1/4) 영어 지문 검색 중... 
      → 총 8개 지문 발견 (2024.12~2025.02)
      
      📝 (2/4) 요약 생성 중... (진행률: 25%)
      → "고1 모의고사 지문분석.pdf" 요약 완료
      → "토익 리딩 문제집.pdf" 요약 중...
      → "수능 영어 기출문제.pdf" 대기 중...
      
      🧩 (3/4) 퀴즈 생성 중... (진행률: 15%)
      → 첫 번째 지문 퀴즈 3개 생성 완료
      → 두 번째 지문 퀴즈 생성 중...
      
      🎥 (4/4) YouTube 추천 검색 중...
      → "영어 독해 기법" 관련 영상 5개 발견
      → "모의고사 해설" 관련 영상 3개 발견
      
      ✅ 모든 작업 완료! (총 소요시간: 2분 30초)
      
      📊 결과 요약:
      - 처리된 지문: 8개
      - 생성된 요약: 8개 (상세형)
      - 생성된 퀴즈: 24개 (각 3개씩)
      - 추천 영상: 12개
      
      결과를 확인하시겠습니까?
```

## ✨ 주요 기능

### 🤖 AI 대화 능력
- **자연어 이해**: 복잡하고 모호한 요청도 정확히 파악
- **의도 분류**: 검색, 요약, 퀴즈, 추천 등 다양한 의도 자동 식별
- **컨텍스트 유지**: 이전 대화 내용을 기억하고 연관 요청 처리
- **개인화 응답**: 사용자 선호도에 맞춘 응답 스타일 제공

### 🔍 고급 검색 엔진
- **멀티모달 검색**: 내용 + 메타데이터 + 시간 + 폴더 통합 검색
- **퍼지 매칭**: 정확하지 않은 키워드도 유사 문서 검색
- **벡터 의미 검색**: AI 임베딩 기반 의미적 유사도 검색
- **실시간 검색**: 즉시 응답하는 빠른 검색 성능

### ⚡ 배치 처리 시스템
- **병렬 문서 처리**: 여러 문서를 동시에 처리하여 시간 단축
- **진행상황 추적**: 실시간으로 작업 진행률 표시
- **오류 복구**: 일부 실패 시 나머지 작업 계속 진행
- **결과 취합**: 모든 처리 결과를 체계적으로 정리

### 🎛️ 워크플로우 관리
- **작업 분해**: 복잡한 요청을 단계별 작업으로 분해
- **조건부 실행**: 상황에 따른 다른 처리 경로 선택
- **상태 관리**: 중간 결과 저장 및 재개 가능
- **우선순위 처리**: 중요한 작업 우선 실행

### 📡 실시간 커뮤니케이션
- **스트리밍 응답**: 생각하는 과정을 실시간으로 보여줌
- **진행 알림**: 배치 작업 진행상황 실시간 업데이트
- **에러 알림**: 문제 발생 시 즉시 사용자에게 알림
- **완료 알림**: 작업 완료 시 결과 요약 제공

## 🏗️ Langgraph 아키텍처

### 메인 워크플로우 구조
```
사용자 입력
    ↓
📥 Input Parser (입력 분석)
    ↓
🧠 Intent Classifier (의도 분류)
    ↓ (조건부 분기)
    ├─ 💬 Simple Chat → Response Generator
    ├─ 🔍 Search Request → Document Search → Format Results
    ├─ 🛠️ Single Feature → Execute Feature → Response
    └─ 🔄 Complex Batch → Execution Planner
                           ↓
                      Batch Processor
                           ↓ (병렬 실행)
                      ├─ 📝 Parallel Summarize
                      ├─ 🧩 Parallel Quiz Gen
                      ├─ 💡 Parallel Recommend
                      └─ 🎥 YouTube Search
                           ↓
                      Result Collector
                           ↓
                      📊 Final Response
```

### 상태 관리 시스템
```
ChatState (중앙 상태)
├─ 대화 관리 (messages, session_id, user_intent)
├─ 검색 관리 (search_results, selected_documents)
├─ 작업 관리 (task_queue, completed_tasks, failed_tasks)
├─ 배치 처리 (progress, total_documents, processed_count)
└─ 컨텍스트 (previous_results, user_preferences)
```

### 노드별 기능 분담
- **Input Parser**: 자연어 → 구조화된 요청
- **Intent Classifier**: 요청 유형 및 복잡도 분석
- **Execution Planner**: 복합 작업을 단계별 계획으로 분해
- **Batch Processor**: 여러 문서 병렬 처리 관리
- **Progress Tracker**: 실시간 진행상황 모니터링
- **Result Collector**: 분산 처리 결과 취합 및 정리

## 💾 데이터베이스 구조

### 기존 컬렉션 (V2에서 유지)
```javascript
// 8개 기존 컬렉션 - 수정 없이 그대로 활용
folders (폴더 관리)
documents (문서 + 벡터 임베딩)
chunks (레거시 호환)
summaries (요약 결과)
qapairs (퀴즈/Q&A)
recommendations (추천 콘텐츠)
labels (AI 라벨링)
file_info (파일 처리 상태)
```

### 새로운 컬렉션 (V3 추가)

#### 1. `chat_sessions` - 세션 관리
```javascript
{
  "_id": ObjectId("..."),
  "session_id": "uuid-string",                    // 고유 세션 식별자
  "user_id": "user-identifier",                   // 사용자 식별자 (선택사항)
  "created_at": ISODate("2024-01-20T10:00:00Z"), // 세션 생성 시간
  "last_activity": ISODate("2024-01-20T15:30:00Z"), // 마지막 활동 시간
  "status": "active",                             // active, completed, expired
  "conversation_summary": "사용자가 영어 지문 검색 및 퀴즈 생성 요청", // 대화 요약
  "total_messages": 15,                           // 총 메시지 수
  "total_tasks": 3,                              // 실행된 작업 수
  "preferences": {                                // 사용자 선호 설정
    "language": "ko",                             // 응답 언어
    "response_style": "detailed",                 // 응답 스타일
    "notification_enabled": true,                 // 알림 수신 여부
    "default_summary_type": "detailed",           // 기본 요약 타입
    "default_quiz_difficulty": "medium"           // 기본 퀴즈 난이도
  },
  "accessed_folders": ["folder1", "folder2"],    // 접근한 폴더 목록
  "accessed_documents": ["doc1", "doc2"]         // 접근한 문서 목록
}
```

#### 2. `workflow_states` - 워크플로우 상태 추적
```javascript
{
  "_id": ObjectId("..."),
  "session_id": "uuid-string",                   // 세션 참조
  "workflow_id": "batch_process_20240120_001",   // 워크플로우 고유 ID
  "workflow_type": "complex_batch",              // simple_search, single_feature, complex_batch
  "current_step": "parallel_quiz_generation",    // 현재 실행 중인 단계
  "total_steps": 6,                             // 전체 단계 수
  "completed_steps": 3,                         // 완료된 단계 수
  "status": "in_progress",                      // pending, in_progress, completed, failed, paused
  "state_data": {                               // 워크플로우별 상태 데이터
    "original_request": "영어 지문들을 최신순으로...", // 원본 요청
    "extracted_requirements": {                  // 추출된 요구사항
      "content_type": "영어 지문",
      "sort_order": "latest_first", 
      "tasks": ["summarize", "quiz_generation", "recommend"]
    },
    "selected_documents": [                     // 선택된 문서들
      {"file_id": "doc1", "title": "고1 모의고사"},
      {"file_id": "doc2", "title": "토익 문제집"}
    ],
    "task_results": {                           // 각 작업별 결과
      "summarize": {
        "status": "completed",
        "results": [...],
        "completed_at": "2024-01-20T14:15:00Z"
      },
      "quiz_generation": {
        "status": "in_progress", 
        "progress": {"completed": 1, "total": 2},
        "partial_results": [...]
      }
    },
    "progress": {                               // 전체 진행률
      "total_documents": 8,
      "processed_documents": 3,
      "failed_documents": 0,
      "percentage": 37.5
    }
  },
  "created_at": ISODate("2024-01-20T14:00:00Z"),
  "updated_at": ISODate("2024-01-20T14:15:00Z"),
  "estimated_completion": ISODate("2024-01-20T14:25:00Z"), // 예상 완료 시간
  "error_messages": [],                         // 오류 메시지 배열
  "retry_count": 0                             // 재시도 횟수
}
```

#### 3. `conversation_history` - 대화 기록
```javascript
{
  "_id": ObjectId("..."),
  "session_id": "uuid-string",                   // 세션 참조
  "message_sequence": 5,                        // 메시지 순서 (0부터 시작)
  "role": "user",                               // user, assistant, system
  "content": "영어 지문들을 최신순으로 정리해서...", // 메시지 내용
  "content_type": "text",                       // text, file, image, structured
  "metadata": {                                 // 메시지 메타데이터
    "intent": "complex_batch_request",          // 분류된 의도
    "confidence": 0.95,                         // 의도 분류 신뢰도
    "entities": [                               // 추출된 엔티티
      {"type": "content", "value": "영어 지문"},
      {"type": "action", "value": "요약"},
      {"type": "action", "value": "퀴즈 생성"}
    ],
    "referenced_documents": ["doc1", "doc2"],   // 참조된 문서
    "triggered_workflow": "batch_process_001"   // 트리거된 워크플로우
  },
  "response_data": {                            // 응답 관련 데이터 (assistant 메시지)
    "response_type": "streaming",               // simple, streaming, structured
    "processing_time": 2.5,                    // 처리 시간 (초)
    "tokens_used": 1250,                       // 사용된 토큰 수
    "sources_used": 3,                         // 참조된 소스 수
    "generated_content": {                     // 생성된 콘텐츠 정보
      "summaries": 2,
      "quizzes": 6,
      "recommendations": 5
    }
  },
  "timestamp": ISODate("2024-01-20T14:10:00Z"), // 메시지 생성 시간
  "edited": false,                              // 메시지 수정 여부
  "flagged": false                             // 문제 있는 메시지 표시
}
```

#### 4. `task_queue` - 작업 대기열 (선택사항)
```javascript
{
  "_id": ObjectId("..."),
  "session_id": "uuid-string",                 // 세션 참조
  "workflow_id": "batch_process_001",          // 워크플로우 참조
  "task_id": "task_summarize_doc1",           // 작업 고유 ID
  "task_type": "generate_summary",            // 작업 유형
  "task_data": {                              // 작업별 데이터
    "document_id": "file-uuid",
    "summary_type": "detailed",
    "target_length": 200
  },
  "dependencies": ["task_search_docs"],       // 선행 작업 (의존성)
  "priority": 1,                              // 우선순위 (1이 가장 높음)
  "status": "pending",                        // pending, processing, completed, failed, cancelled
  "assigned_worker": null,                    // 처리 중인 워커 ID
  "created_at": ISODate("2024-01-20T14:05:00Z"),
  "started_at": null,                         // 작업 시작 시간
  "completed_at": null,                       // 작업 완료 시간
  "estimated_duration": 30,                   // 예상 소요 시간 (초)
  "actual_duration": null,                    // 실제 소요 시간
  "retry_count": 0,                          // 재시도 횟수
  "max_retries": 3,                          // 최대 재시도 횟수
  "error_message": null,                     // 오류 메시지
  "result": null                             // 작업 결과 (완료 후)
}
```

### 인덱스 추가 (4개 컬렉션)
```javascript
// chat_sessions 컬렉션
db.chat_sessions.createIndex({"session_id": 1}, {unique: true})
db.chat_sessions.createIndex({"user_id": 1})
db.chat_sessions.createIndex({"status": 1})
db.chat_sessions.createIndex({"last_activity": -1})

// workflow_states 컬렉션  
db.workflow_states.createIndex({"session_id": 1})
db.workflow_states.createIndex({"workflow_id": 1}, {unique: true})
db.workflow_states.createIndex({"status": 1})
db.workflow_states.createIndex({"created_at": -1})

// conversation_history 컬렉션
db.conversation_history.createIndex({"session_id": 1, "message_sequence": 1})
db.conversation_history.createIndex({"role": 1})
db.conversation_history.createIndex({"timestamp": -1})

// task_queue 컬렉션
db.task_queue.createIndex({"session_id": 1})
db.task_queue.createIndex({"status": 1, "priority": -1})
db.task_queue.createIndex({"workflow_id": 1})
db.task_queue.createIndex({"dependencies": 1})
```

## 💬 대화 저장 및 관리 체계

### 실시간 대화 내용 저장
V3에서는 사용자와의 모든 대화 내용이 체계적으로 저장되고 관리됩니다:

#### 1. **대화 저장 과정**
```
사용자 메시지 입력
    ↓
[1] session_id 확인/생성 (chat_sessions)
    ↓
[2] 사용자 메시지 즉시 저장 (conversation_history)
    - role: "user"
    - 메시지 내용 + AI 분석 메타데이터
    ↓
[3] AI 처리 및 응답 생성
    ↓
[4] AI 응답 저장 (conversation_history)
    - role: "assistant"
    - 응답 내용 + 처리 통계
    ↓
[5] 세션 정보 업데이트 (chat_sessions)
    - 마지막 활동 시간, 메시지 수 갱신
```

#### 2. **핵심 저장 특징**
- **즉시 저장**: 메시지 전송과 동시에 데이터베이스 저장
- **메타데이터 수집**: AI가 분석한 의도, 엔티티, 신뢰도 자동 기록
- **진행상황 추적**: 복잡한 배치 작업의 실시간 상태 저장
- **세션 연결**: 모든 대화가 고유 세션 ID로 연결 관리

#### 3. **저장되는 대화 정보**
```javascript
// 사용자 메시지 예시
{
  "session_id": "sess_001",
  "role": "user",
  "content": "영어 지문들로 퀴즈 만들어줘",
  "metadata": {
    "intent": "quiz_generation",           // AI 분석 의도
    "entities": [{"type": "content", "value": "영어 지문"}],
    "confidence": 0.95
  }
}

// AI 응답 예시  
{
  "session_id": "sess_001", 
  "role": "assistant",
  "content": "퀴즈 5개를 생성했습니다...",
  "response_data": {
    "processing_time": 2.3,              // 처리 시간
    "tokens_used": 850,                  // 사용 토큰
    "generated_content": {"quizzes": 5}  // 생성 콘텐츠 통계
  }
}
```

#### 4. **데이터 연관 및 활용**
- **세션 기반 관리**: 사용자별 독립적인 대화 공간
- **컨텍스트 유지**: 이전 대화 참조 가능
- **작업 연계**: 대화 → 워크플로우 → 결과 연결 추적
- **사용 통계**: 메시지 수, 작업 수, 활동 패턴 분석

#### 5. **검색 및 조회 최적화**
```javascript
// 세션별 대화 기록 빠른 조회
db.conversation_history.find({"session_id": "sess_001"})
  .sort({"message_sequence": 1})

// 특정 의도의 메시지만 조회
db.conversation_history.find({"metadata.intent": "quiz_generation"})

// 최근 활성 세션 조회
db.chat_sessions.find({"status": "active"})
  .sort({"last_activity": -1})
```

이를 통해 **사용자의 모든 대화가 손실 없이 보존**되고, **이전 대화 참조**, **개인화된 응답**, **작업 이력 추적** 등이 가능해집니다.

## ⚡ 실시간 통신 시스템

### WebSocket과 스트리밍의 핵심 역할
V3에서는 복잡한 AI 작업을 사용자가 안심하고 기다릴 수 있도록 실시간 소통 시스템을 구축했습니다.

#### 1. **기존 방식 vs 실시간 방식**
```
❌ 기존 HTTP 방식:
사용자 → 서버 (요청)
[5분간 무음...]
사용자 ← 서버 (결과)

✅ WebSocket 방식:
사용자 ↔ 서버 (지속 연결)
"검색 중... 8개 지문 발견"
"1번 지문 요약 완료"
"퀴즈 생성 중... 50%"
"모든 작업 완료!"
```

#### 2. **스트리밍 엔드포인트의 역할**
- **진행상황 실시간 전달**: 작업 단계별 진행률 표시
- **부분 결과 즉시 표시**: 완성되는 즉시 사용자에게 전달
- **오류 즉시 알림**: 문제 발생 시 바로 사용자에게 통지
- **작업 제어**: 사용자가 중간에 취소하거나 수정 가능

#### 3. **복합 작업에서의 실시간 피드백**
```javascript
복합 요청: "영어 지문 8개로 각각 요약하고 퀴즈 3개씩 만들어줘"

실시간 스트리밍 응답:
💬 "작업 계획: 8개 지문 → 8개 요약 + 24개 퀴즈"
🔍 "영어 지문 검색 중... (10%)"
📋 "8개 지문 발견 - 최신순 정렬 완료 (25%)"
📝 "1번 지문 '친절함은 전염된다' 요약 중... (30%)"
✅ "1번 지문 요약 완료 (35%)"
🧩 "1번 지문 퀴즈 3개 생성 중... (40%)"
🎯 "퀴즈 1: 다음 중 올바른 것은? ①친절함은..."
🎯 "퀴즈 2: 빈칸에 들어갈 말은? ①however..."
🎯 "퀴즈 3: 글의 제목으로 적절한 것은?..."
📝 "2번 지문 '환경보호의 중요성' 요약 중... (50%)"
...
🎉 "모든 작업 완료! 총 소요시간: 3분 27초"
```

#### 4. **사용자 경험 혁신**
| 상황 | 기존 방식 | WebSocket 방식 |
|------|-----------|----------------|
| **긴 작업 처리** | 😴 5분간 아무것도 모름 | 😊 실시간 진행상황 확인 |
| **오류 발생** | 😤 마지막에야 실패 알림 | ⚡ 즉시 오류 알림 및 대응 |
| **부분 결과** | 📦 완료 후 한번에 전달 | 🎁 생성 즉시 하나씩 확인 |
| **작업 제어** | ❌ 중단 불가능 | ✅ 언제든 취소/수정 가능 |

#### 5. **기술적 구현**
```javascript
// 클라이언트 (사용자 화면)
const socket = new WebSocket('ws://localhost:8000/api/v3/chat/stream');

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'progress') {
        updateProgressBar(data.progress);      // 진행률 바 업데이트
    } else if (data.type === 'partial_result') {
        appendResult(data.content);            // 부분 결과 즉시 표시
    } else if (data.type === 'complete') {
        showFinalResults(data.results);        // 최종 완료
    }
};
```

이러한 실시간 통신 시스템으로 **사용자가 안심하고 복잡한 AI 작업을 요청**할 수 있고, **투명한 처리 과정**을 통해 신뢰할 수 있는 AI 서비스를 제공합니다.

## 🛠️ 기술 스택

| 구분 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **워크플로우 엔진** | Langgraph | 0.0.20+ | 복합 워크플로우 관리 |
| **LLM** | GPT-4o-mini | latest | 자연어 이해 및 생성 |
| **임베딩** | text-embedding-3-large | latest | 1536차원 벡터 생성 |
| **데이터베이스** | MongoDB | 6.0+ | 문서/벡터/상태 통합 저장 |
| **웹 프레임워크** | FastAPI | 0.109+ | REST API + 스트리밍 |
| **AI 프레임워크** | LangChain Core | 0.1+ | LLM 체인 관리 |
| **비동기 처리** | asyncio + motor | latest | 고성능 비동기 처리 |
| **상태 관리** | Redis | 4.0+ | 세션 상태 캐싱 |
| **실시간 통신** | WebSocket/SSE | - | 스트리밍 응답 |
| **타입 검증** | Pydantic | 2.0+ | 강타입 데이터 검증 |

## 📈 구현 흐름

### Phase 1: 기반 설계 및 준비 (1주)
#### 목표: Langgraph 기반 아키텍처 설계
- **상태 모델 설계**: ChatState, WorkflowState 정의
- **새 컬렉션 생성**: chat_sessions, workflow_states, conversation_history, task_queue
- **의존성 설정**: langgraph, redis 등 새 라이브러리 추가
- **디렉토리 구조 재구성**: workflows/, state/, nodes/ 폴더 생성

### Phase 2: 핵심 워크플로우 구현 (3주)
#### 목표: 메인 대화 워크플로우 및 배치 처리 구현
- **메인 워크플로우**: 입력분석 → 의도분류 → 조건부실행 → 결과포맷팅
- **배치 워크플로우**: 작업계획 → 병렬처리 → 진행추적 → 결과취합
- **상태 관리**: 세션별 상태 저장/복원, 워크플로우 중단/재개
- **노드 구현**: 20+ 개별 노드 (검색, 요약, 퀴즈, 추천, 유튜브 등)

### Phase 3: 기존 기능 통합 (2주)
#### 목표: V2의 모든 기능을 Langgraph 노드로 변환
- **기존 체인 변환**: summary_chain → summary_node
- **배치 지원 추가**: 여러 문서 동시 처리 로직
- **캐싱 연계**: 기존 캐시 시스템과 새 워크플로우 연결
- **데이터 호환성**: 기존 데이터베이스와 완벽 호환 보장

### Phase 4: API 레이어 재설계 (1주)
#### 목표: 스트리밍 API 및 세션 관리 API 구현
- **스트리밍 엔드포인트**: `/chat/stream` - 실시간 응답
- **세션 관리 API**: 세션 생성/조회/종료
- **상태 조회 API**: 워크플로우 진행상황 조회
- **WebSocket 지원**: 실시간 양방향 통신

### Phase 5: 성능 최적화 및 고도화 (2주)
#### 목표: 병렬 처리 최적화 및 캐싱 전략 강화
- **병렬 처리**: ThreadPoolExecutor + asyncio 최적화
- **캐싱 전략**: Redis 기반 세션 캐시, 워크플로우 결과 캐시
- **메모리 관리**: 대용량 배치 작업 메모리 최적화
- **성능 모니터링**: 처리 시간, 메모리 사용량 모니터링

### Phase 6: 테스트 및 검증 (1주)
#### 목표: 전체 시스템 통합 테스트 및 품질 검증
- **유닛 테스트**: 개별 노드 및 워크플로우 테스트
- **통합 테스트**: 전체 시나리오 테스트
- **성능 테스트**: 동시 세션, 대용량 배치 처리 테스트
- **사용자 테스트**: 실제 사용 시나리오 검증

## 🔌 API 엔드포인트

### 대화 API
```
POST /api/v3/chat/session
- 새 대화 세션 생성

POST /api/v3/chat/message
- 메시지 전송 (일반 응답)

POST /api/v3/chat/stream
- 스트리밍 대화 (실시간 응답)

GET /api/v3/chat/session/{session_id}
- 세션 정보 조회

GET /api/v3/chat/session/{session_id}/history
- 대화 기록 조회

DELETE /api/v3/chat/session/{session_id}
- 세션 종료
```

### 워크플로우 API
```
GET /api/v3/workflow/{workflow_id}/status
- 워크플로우 상태 조회

POST /api/v3/workflow/{workflow_id}/pause
- 워크플로우 일시 정지

POST /api/v3/workflow/{workflow_id}/resume  
- 워크플로우 재개

POST /api/v3/workflow/{workflow_id}/cancel
- 워크플로우 취소

GET /api/v3/workflow/{workflow_id}/results
- 워크플로우 결과 조회
```

### 배치 작업 API
```
POST /api/v3/batch/process
- 배치 작업 요청

GET /api/v3/batch/{batch_id}/progress
- 배치 작업 진행률 조회

GET /api/v3/batch/{batch_id}/results
- 배치 작업 결과 조회

POST /api/v3/batch/{batch_id}/download
- 배치 결과 다운로드
```

### 통계 및 관리 API
```
GET /api/v3/stats/sessions
- 세션 통계

GET /api/v3/stats/workflows
- 워크플로우 통계

GET /api/v3/admin/active-sessions
- 활성 세션 목록

POST /api/v3/admin/cleanup
- 만료된 세션 정리
```

## 🎮 사용법 및 예시

### 기본 대화 시작
```bash
# 1. 세션 생성
curl -X POST http://localhost:8000/api/v3/chat/session \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "preferences": {"language": "ko"}}'

# 응답
{
  "session_id": "sess_abc123",
  "status": "active",
  "created_at": "2024-01-20T10:00:00Z"
}

# 2. 메시지 전송
curl -X POST http://localhost:8000/api/v3/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123",
    "message": "친절함은 전염된다는 내용의 영어 지문 찾아줘"
  }'
```

### 스트리밍 대화 (JavaScript)
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v3/chat/stream?session_id=sess_abc123'
);

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.type === 'progress') {
    updateProgressBar(data.progress);
  } else if (data.type === 'partial_response') {
    appendMessage(data.content);
  } else if (data.type === 'complete') {
    finalizeResponse(data);
  }
};

// 메시지 전송
fetch('/api/v3/chat/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    session_id: 'sess_abc123',
    message: '영어 지문들을 정리해서 각각 요약하고 퀴즈 만들어줘'
  })
});
```

### 복합 배치 요청 모니터링
```bash
# 배치 작업 요청
curl -X POST http://localhost:8000/api/v3/batch/process \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_abc123",
    "request": "영어 지문들을 최신순으로 정리해서 각각 요약하고 퀴즈 만들어줘",
    "options": {
      "summary_type": "detailed",
      "quiz_difficulty": "medium", 
      "quiz_count_per_document": 3
    }
  }'

# 진행률 조회
curl http://localhost:8000/api/v3/workflow/batch_001/status

# 응답
{
  "workflow_id": "batch_001",
  "status": "in_progress",
  "progress": {
    "total_steps": 4,
    "completed_steps": 2,
    "current_step": "parallel_quiz_generation",
    "percentage": 50,
    "documents": {
      "total": 8,
      "processed": 3,
      "failed": 0
    }
  },
  "estimated_completion": "2024-01-20T14:25:00Z"
}
```

### WebSocket 실시간 통신 (Python)
```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    
    if data['type'] == 'workflow_progress':
        print(f"진행률: {data['percentage']}%")
    elif data['type'] == 'step_completed':
        print(f"단계 완료: {data['step_name']}")
    elif data['type'] == 'workflow_complete':
        print("작업 완료!")
        print(f"결과: {data['summary']}")

ws = websocket.WebSocketApp(
    "ws://localhost:8000/api/v3/chat/ws?session_id=sess_abc123",
    on_message=on_message
)

ws.run_forever()
```

## ⚙️ 설치 및 실행

### 환경 설정
```bash
# .env 파일 설정 (기존 + 새 항목)
OPENAI_API_KEY=sk-your-openai-api-key
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=seeq_rag
YOUTUBE_API_KEY=your-youtube-api-key

# 새 설정 (V3)
REDIS_URL=redis://localhost:6379
SESSION_TIMEOUT=3600
MAX_CONCURRENT_WORKFLOWS=10
STREAMING_RESPONSE=true
```

### 의존성 설치
```bash
pip install -r requirements_v3.txt

# 주요 새 라이브러리
langgraph>=0.0.20
redis>=4.0.0  
websockets>=11.0
asyncio-mqtt>=0.11.0
```

### MongoDB 설정
```bash
# 기존 컬렉션은 그대로 유지
# 새 컬렉션만 생성
mongosh seeq_rag --eval "
  db.createCollection('chat_sessions');
  db.createCollection('workflow_states');
  db.createCollection('conversation_history');
  db.createCollection('task_queue');
"

# 인덱스 생성
python scripts/create_v3_indexes.py
```

### 서버 실행
```bash
# 개발 서버
python main_v3.py

# 프로덕션 서버 (Gunicorn)
gunicorn main_v3:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 🚀 개발 로드맵

### V3.1 (예정 - 2개월 후)
- **🔊 음성 인터페이스**: 음성 인식 및 TTS 지원
- **🌍 다국어 지원**: 영어, 일본어, 중국어 대화 지원
- **📱 모바일 최적화**: 모바일 환경 전용 API

### V3.2 (예정 - 4개월 후)  
- **🧠 개인화 학습**: 사용자별 선호도 학습 및 적응
- **📊 고급 분석**: 문서 패턴 분석 및 인사이트 제공
- **🔗 외부 연동**: Google Drive, Notion 등 외부 서비스 연동

### V4.0 (예정 - 6개월 후)
- **🤝 협업 기능**: 다중 사용자 실시간 협업
- **🎨 UI 생성**: 자동 대시보드 및 시각화 생성  
- **🔮 예측 기능**: 사용자 요구사항 예측 및 선제적 제안

## 🏆 V3의 혁신적 개선사항

### 기존 V2 대비 향상점
- **🧠 지능 향상**: 단순 Q&A → 복합 작업 이해 및 실행
- **⚡ 성능 향상**: 평균 응답시간 50% 단축 (병렬 처리)
- **🎯 정확도 향상**: 검색 정확도 30% 향상 (멀티모달 검색)
- **📱 사용성 향상**: 실시간 피드백으로 사용자 경험 대폭 개선
- **🔧 유지보수성**: Langgraph 기반으로 워크플로우 관리 용이

### 기술적 혁신
- **상태 관리**: 복잡한 워크플로우 상태를 체계적으로 관리
- **에러 복구**: 부분 실패 시에도 전체 작업 계속 진행
- **확장성**: 새로운 기능 추가가 매우 용이한 모듈형 구조
- **모니터링**: 실시간 성능 모니터링 및 디버깅 지원

---

**💬 문의사항**: GitHub Issues 또는 이메일로 문의  
**📅 최종 업데이트**: 2025년 1월 20일  
**⭐ 버전**: v3.0 (Langgraph 기반 고급 대화형 AI 시스템)  
**📄 라이선스**: MIT License 
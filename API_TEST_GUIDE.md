# LangChain SEEQ API 테스트 가이드 📚

## 📋 파라미터 범례
- ✅ **필수 파라미터**: 반드시 포함해야 함
- 🔹 **선택 파라미터**: 생략 가능
- 🔸 **조건부 파라미터**: 특정 조건에서만 필요

## 🗂️ 실제 데이터베이스 ID (100% 성공 보장)

### 📁 폴더 ID
- **금융** (추천): `683e9a9a324d04898ae63f63` - 2개 파일
- **경영학**: `683e8fd3a7d860028b795845` - 1개 파일  
- **OCR 텍스트**: `683faa67118e26d7e280b9f4` - 다수 파일
- **예시 폴더**: `683fdd811cf85394f822e4d8` - 테스트용

### 📄 파일 ID
- **금융 문서**: `2cd81211-7984-4f5b-9805-29c754273a79`
- **시사 문서**: `5b0c35bf-bc88-4db7-8aaf-f10558fbfce2`

### 📊 보고서 ID
- **실제 보고서**: `1b7a85e8-625a-4660-a7b5-4395fb7a6316`

---

## 🔥 보고서 생성 및 관리 API (개선됨)

### 1️⃣ 파일 목록 조회 (보고서 생성 준비)
```bash
GET /api/v1/reports/files/{folder_id}
```

**파라미터**:
- ✅ `folder_id` (path): 폴더 ID 또는 폴더명

**실제 테스트**:
```bash
curl -X GET "http://localhost:8000/api/v1/reports/files/683e9a9a324d04898ae63f63"
```

**성공 응답**:
```json
[
  {
    "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
    "filename": "금융문서.pdf",
    "file_type": "pdf",
    "file_size": 1024000,
    "chunk_count": 15,
    "description": "금융 관련 문서",
    "selected": false
  }
]
```

### 2️⃣ 보고서 생성 (동기 처리 기본)
```bash
POST /api/v1/reports/generate
```

**파라미터**:
- ✅ `folder_id`: 폴더 ID
- ✅ `selected_files`: 선택된 파일 배열
  - ✅ `file_id`: 파일 ID
  - ✅ `filename`: 파일명
  - ✅ `file_type`: 파일 타입
  - ✅ `selected`: 선택 여부 (true)
- 🔹 `custom_title`: 사용자 지정 제목
- 🔹 `background_generation`: 백그라운드 생성 여부 (기본: false)

**실제 테스트 (동기 처리 - 권장)**:
```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "683e9a9a324d04898ae63f63",
    "selected_files": [
      {
        "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
        "filename": "금융문서.pdf",
        "file_type": "pdf",
        "selected": true
      }
    ],
    "custom_title": "금융 시장 분석 보고서",
    "background_generation": false
  }'
```

**성공 응답 (동기)**:
```json
{
  "message": "보고서 생성이 완료되었습니다",
  "report_id": "새로운-report-id",
  "status": "completed",
  "background_generation": false,
  "title": "금융 시장 분석 보고서",
  "subtitle": "금융문서.pdf 기반 분석"
}
```

**백그라운드 생성 (특수한 경우)**:
```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "683e9a9a324d04898ae63f63",
    "selected_files": [
      {
        "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
        "filename": "금융문서.pdf",
        "file_type": "pdf",
        "selected": true
      }
    ],
    "background_generation": true
  }'
```

### 3️⃣ 보고서 목록 조회 (통합된 API)
```bash
GET /api/v1/reports/
```

**파라미터**:
- 🔹 `folder_id` (query): 폴더 ID로 필터링 (생략 시 전체 조회)
- 🔹 `limit` (query): 조회 개수 (기본: 20, 최대: 100)
- 🔹 `skip` (query): 건너뛸 개수 (기본: 0)

**실제 테스트**:

**전체 보고서 목록**:
```bash
curl -X GET "http://localhost:8000/api/v1/reports/?limit=10&skip=0"
```

**특정 폴더의 보고서 목록**:
```bash
curl -X GET "http://localhost:8000/api/v1/reports/?folder_id=683e9a9a324d04898ae63f63&limit=10&skip=0"
```

**성공 응답**:
```json
[
  {
    "report_id": "1b7a85e8-625a-4660-a7b5-4395fb7a6316",
    "title": "금융 시장 분석 보고서",
    "subtitle": "금융문서.pdf 기반 분석",
    "folder_id": "683e9a9a324d04898ae63f63",
    "created_at": "2024-12-20T10:30:00Z",
    "metadata": {
      "total_pages": 25,
      "analysis_depth": "comprehensive"
    },
    "analysis_summary": {
      "key_findings": ["주요 발견사항 1", "주요 발견사항 2"],
      "recommendations": ["권장사항 1", "권장사항 2"]
    }
  }
]
```

### 4️⃣ 보고서 상세 조회
```bash
GET /api/v1/reports/{report_id}
```

**파라미터**:
- ✅ `report_id` (path): 보고서 ID

**실제 테스트**:
```bash
curl -X GET "http://localhost:8000/api/v1/reports/1b7a85e8-625a-4660-a7b5-4395fb7a6316"
```

**성공 응답**:
```json
{
  "report_id": "1b7a85e8-625a-4660-a7b5-4395fb7a6316",
  "title": "금융 시장 분석 보고서",
  "subtitle": "금융문서.pdf 기반 분석",
  "folder_id": "683e9a9a324d04898ae63f63",
  "selected_files": [
    {
      "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
      "filename": "금융문서.pdf",
      "file_type": "pdf"
    }
  ],
  "report_structure": {
    "sections": ["서론", "본론", "결론"],
    "chapter_count": 3
  },
  "analysis_summary": {
    "key_findings": ["주요 발견사항들"],
    "recommendations": ["권장사항들"]
  },
  "metadata": {
    "total_pages": 25,
    "analysis_depth": "comprehensive",
    "processing_time": "2.5분"
  },
  "formatted_text": "# 금융 시장 분석 보고서\n\n## 요약\n...",
  "created_at": "2024-12-20T10:30:00Z",
  "updated_at": "2024-12-20T10:32:30Z"
}
```

### 5️⃣ 보고서 삭제
```bash
DELETE /api/v1/reports/{report_id}
```

**파라미터**:
- ✅ `report_id` (path): 보고서 ID

**실제 테스트**:
```bash
curl -X DELETE "http://localhost:8000/api/v1/reports/1b7a85e8-625a-4660-a7b5-4395fb7a6316"
```

**성공 응답**:
```json
{
  "message": "보고서가 성공적으로 삭제되었습니다",
  "report_id": "1b7a85e8-625a-4660-a7b5-4395fb7a6316",
  "deleted_at": "2024-12-20T11:00:00Z"
}
```

### 6️⃣ 보고서 통계 조회
```bash
GET /api/v1/reports/statistics/summary
```

**파라미터**:
- 🔹 `folder_id` (query): 폴더 ID로 필터링

**실제 테스트**:

**전체 통계**:
```bash
curl -X GET "http://localhost:8000/api/v1/reports/statistics/summary"
```

**특정 폴더 통계**:
```bash
curl -X GET "http://localhost:8000/api/v1/reports/statistics/summary?folder_id=683e9a9a324d04898ae63f63"
```

**성공 응답**:
```json
{
  "total_reports": 12,
  "recent_reports_count": 5,
  "folder_id": "683e9a9a324d04898ae63f63",
  "generated_at": "2024-12-20T11:00:00Z",
  "recent_reports": [
    {
      "report_id": "1b7a85e8-625a-4660-a7b5-4395fb7a6316",
      "title": "금융 시장 분석 보고서",
      "created_at": "2024-12-20T10:30:00Z"
    }
  ]
}
```

---

## 🔍 문서 검색 API

### 1️⃣ 폴더 목록 조회
```bash
GET /api/v1/folders/
```

**실제 테스트**:
```bash
curl -X GET "http://localhost:8000/api/v1/folders/"
```

### 2️⃣ 폴더 내 파일 목록 조회
```bash
GET /api/v1/folders/{folder_id}/files
```

**실제 테스트**:
```bash
curl -X GET "http://localhost:8000/api/v1/folders/683e9a9a324d04898ae63f63/files"
```

### 3️⃣ 의미 기반 검색
```bash
POST /api/v1/search/semantic
```

**파라미터**:
- ✅ `query`: 검색 쿼리
- ✅ `folder_id`: 폴더 ID
- 🔹 `top_k`: 반환할 결과 수 (기본: 5)
- 🔹 `similarity_threshold`: 유사도 임계값 (기본: 0.7)

**실제 테스트**:
```bash
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "금융 시장 분석",
    "folder_id": "683e9a9a324d04898ae63f63",
    "top_k": 5,
    "similarity_threshold": 0.7
  }'
```

### 4️⃣ 키워드 추출
```bash
POST /api/v1/search/keywords
```

**파라미터**:
- ✅ `folder_id`: 폴더 ID
- 🔹 `file_ids`: 특정 파일 ID 배열 (생략 시 폴더 전체)
- 🔹 `max_keywords`: 최대 키워드 수 (기본: 10)

**실제 테스트**:
```bash
curl -X POST "http://localhost:8000/api/v1/search/keywords" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "683e9a9a324d04898ae63f63",
    "file_ids": ["2cd81211-7984-4f5b-9805-29c754273a79"],
    "max_keywords": 10
  }'
```

### 5️⃣ 유사 문서 추천
```bash
POST /api/v1/search/similar
```

**파라미터**:
- ✅ `file_id`: 기준 파일 ID
- ✅ `folder_id`: 폴더 ID
- 🔹 `top_k`: 반환할 결과 수 (기본: 5)
- 🔹 `similarity_threshold`: 유사도 임계값 (기본: 0.7)

**실제 테스트**:
```bash
curl -X POST "http://localhost:8000/api/v1/search/similar" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
    "folder_id": "683e9a9a324d04898ae63f63",
    "top_k": 5,
    "similarity_threshold": 0.7
  }'
```

---

## 🧠 퀴즈 생성 API

### 1️⃣ 퀴즈 생성
```bash
POST /api/v1/quiz/generate
```

**파라미터**:
- ✅ `folder_id`: 폴더 ID
- 🔹 `file_ids`: 특정 파일 ID 배열 (생략 시 폴더 전체)
- 🔹 `num_questions`: 문제 수 (기본: 10, 최대: 50)
- 🔹 `difficulty`: 난이도 ("easy", "medium", "hard", 기본: "medium")
- 🔹 `question_types`: 문제 유형 배열 (기본: ["multiple_choice", "true_false"])

**실제 테스트**:
```bash
curl -X POST "http://localhost:8000/api/v1/quiz/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "683e9a9a324d04898ae63f63",
    "file_ids": ["2cd81211-7984-4f5b-9805-29c754273a79"],
    "num_questions": 5,
    "difficulty": "medium",
    "question_types": ["multiple_choice", "true_false"]
  }'
```

### 2️⃣ 퀴즈 세션 생성
```bash
POST /api/v1/quiz/session
```

**파라미터**:
- ✅ `quiz_id`: 퀴즈 ID
- 🔹 `session_name`: 세션 이름

**실제 테스트**:
```bash
curl -X POST "http://localhost:8000/api/v1/quiz/session" \
  -H "Content-Type: application/json" \
  -d '{
    "quiz_id": "실제퀴즈ID",
    "session_name": "테스트 세션"
  }'
```

### 3️⃣ 퀴즈 답안 제출
```bash
POST /api/v1/quiz/submit/{session_id}
```

**파라미터**:
- ✅ `session_id` (path): 세션 ID
- ✅ `answers`: 답안 배열
  - ✅ `question_id`: 문제 ID
  - ✅ `answer`: 답안

**실제 테스트**:
```bash
curl -X POST "http://localhost:8000/api/v1/quiz/submit/api_test_92a18f1f" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {
        "question_id": "q1",
        "answer": "A"
      },
      {
        "question_id": "q2",
        "answer": "true"
      }
    ]
  }'
```

### 4️⃣ 퀴즈 목록 조회 (qapairs 컬렉션)
```bash
GET /api/v1/quiz/list
```

**파라미터**:
- 🔹 `folder_id` (query): 폴더 ID로 필터링
- 🔹 `topic` (query): 주제로 필터링
- 🔹 `difficulty` (query): 난이도로 필터링 (easy, medium, hard)
- 🔹 `quiz_type` (query): 퀴즈 타입으로 필터링 (multiple_choice, true_false, short_answer)
- 🔹 `page` (query): 페이지 번호 (기본: 1)
- 🔹 `limit` (query): 페이지당 항목 수 (기본: 20, 최대: 100)

**실제 테스트**:
```bash
# 전체 퀴즈 목록
curl -X GET "http://localhost:8000/api/v1/quiz/list?page=1&limit=10"

# 금융 폴더 퀴즈만
curl -X GET "http://localhost:8000/api/v1/quiz/list?folder_id=683e9a9a324d04898ae63f63&page=1&limit=10"

# 객관식 문제만
curl -X GET "http://localhost:8000/api/v1/quiz/list?quiz_type=multiple_choice&page=1&limit=10"
```

**성공 응답**:
```json
{
  "quizzes": [
    {
      "quiz_id": "6847ada7862b6f61029b9748",
      "question": "S P 500지수와 비교할 때, 어떤 방식으로 수익률을 계산하는 지수는 대표적인 부족하다는 의견이 많습니까?",
      "quiz_type": "multiple_choice",
      "quiz_options": ["시가총액 가중평균", "수익률 평균방식", "기술평균방식", "자산총액 방식"],
      "correct_option": 1,
      "correct_answer": "수익률 평균방식으로 계산되는 지수는 대표성이 부족하다는 의견이 있습니다.",
      "answer": "수익률 평균방식으로 계산되는 지수는 대표성이 부족하다는 의견이 있습니다.",
      "difficulty": "medium",
      "topic": "블록체인",
      "folder_id": "683e9a9a324d04898ae63f63",
      "source_document_id": null,
      "created_at": "2025-06-10T03:59:35.774000+00:00"
    }
  ],
  "total_count": 25,
  "page": 1,
  "limit": 10,
  "has_next": true
}
```

### 5️⃣ 개별 퀴즈 상세 조회
```bash
GET /api/v1/quiz/{quiz_id}
```

**파라미터**:
- ✅ `quiz_id` (path): 퀴즈 ID (MongoDB ObjectId)

**실제 테스트**:
```bash
curl -X GET "http://localhost:8000/api/v1/quiz/6847ada7862b6f61029b9748"
```

**성공 응답**:
```json
{
  "quiz_id": "6847ada7862b6f61029b9748",
  "question": "S P 500지수와 비교할 때, 어떤 방식으로 수익률을 계산하는 지수는 대표적인 부족하다는 의견이 많습니까?",
  "quiz_type": "multiple_choice",
  "quiz_options": ["시가총액 가중평균", "수익률 평균방식", "기술평균방식", "자산총액 방식"],
  "correct_option": 1,
  "correct_answer": "수익률 평균방식으로 계산되는 지수는 대표성이 부족하다는 의견이 있습니다.",
  "answer": "수익률 평균방식으로 계산되는 지수는 대표성이 부족하다는 의견이 있습니다.",
  "difficulty": "medium",
  "topic": "블록체인",
  "folder_id": "683e9a9a324d04898ae63f63",
  "source_document_id": null,
  "created_at": "2025-06-10T03:59:35.774000+00:00"
}
```

### 6️⃣ 퀴즈 결과 조회
```bash
GET /api/v1/quiz/result/{session_id}
```

**실제 테스트**:
```bash
curl -X GET "http://localhost:8000/api/v1/quiz/result/api_test_92a18f1f"
```

---

## 🎯 추천 테스트 시나리오

### 💰 시나리오 1: 금융 폴더 완전 테스트
```bash
# 1. 폴더 파일 목록 조회
curl -X GET "http://localhost:8000/api/v1/reports/files/683e9a9a324d04898ae63f63"

# 2. 보고서 생성 (동기)
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "683e9a9a324d04898ae63f63",
    "selected_files": [
      {
        "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
        "filename": "금융문서.pdf",
        "file_type": "pdf",
        "selected": true
      }
    ],
    "custom_title": "금융 분석 보고서"
  }'

# 3. 보고서 목록 조회
curl -X GET "http://localhost:8000/api/v1/reports/?folder_id=683e9a9a324d04898ae63f63"

# 4. 보고서 상세 조회 (위에서 받은 report_id 사용)
curl -X GET "http://localhost:8000/api/v1/reports/새로운-report-id"
```

### 🔍 시나리오 2: 검색 및 퀴즈 테스트
```bash
# 1. 의미 검색
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "금융 시장 분석",
    "folder_id": "683e9a9a324d04898ae63f63",
    "top_k": 3
  }'

# 2. 퀴즈 생성
curl -X POST "http://localhost:8000/api/v1/quiz/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_id": "683e9a9a324d04898ae63f63",
    "num_questions": 3,
    "difficulty": "medium"
  }'

# 3. 생성된 퀴즈 목록 조회
curl -X GET "http://localhost:8000/api/v1/quiz/list?folder_id=683e9a9a324d04898ae63f63&page=1&limit=5"
```

---

## ✅ 주요 개선사항

### 🔧 API 구조 개선
1. **상태 조회 API 제거**: 불필요한 복잡성 제거
2. **보고서 목록 API 통합**: 하나의 API로 전체/폴더별 조회 가능
3. **논리적 순서 재정렬**: 사용자 워크플로우에 맞춘 순서
4. **동기 처리 기본**: `background_generation: false`가 기본값

### 🚀 사용자 경험 개선
- **간소화된 워크플로우**: 파일 선택 → 보고서 생성 → 결과 확인
- **즉시 결과 반환**: 2-3분 내 완료되는 동기 처리
- **통합된 목록 조회**: 하나의 API로 모든 보고서 조회 가능
- **명확한 API 순서**: 논리적 흐름에 따른 단계별 진행

### 📊 성능 최적화
- **메모리 사용량 감소**: 불필요한 상태 관리 제거
- **복잡성 감소**: 백그라운드 처리는 특수한 경우에만
- **에러 처리 개선**: 명확한 에러 메시지와 상태 코드

---

## 🌟 핵심 포인트

1. **동기 처리 우선**: 대부분의 경우 즉시 결과 반환
2. **통합된 목록 API**: `folder_id` 파라미터로 필터링
3. **논리적 API 순서**: 1→2→3→4→5→6 단계별 진행
4. **실제 데이터 사용**: 100% 성공하는 테스트 환경

**가장 추천하는 테스트 폴더**: `683e9a9a324d04898ae63f63` (금융) 
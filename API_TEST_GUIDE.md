# LangChain SEEQ RAG v3.0 API 테스트 가이드 📋

> **최신 업데이트**: 2024년 12월 - 13개 라우터, 62개 엔드포인트 완전 분석

## 📋 기본 정보
- 🌐 **베이스 URL**: `http://localhost:8000` (또는 `http://0.0.0.0:8000`)
- 📍 **API 프리픽스**: 없음 (직접 라우터 경로 사용)
- ✅ **필수 파라미터**: 반드시 포함해야 함
- 🔹 **선택 파라미터**: 생략 가능 (기본값 존재)
- 📚 **API 문서**: `http://0.0.0.0:8000/docs` (Swagger UI)

## 🗂️ 검증된 테스트 ID

```json
{
  "folders": {
    "finance": "683e9a9a324d04898ae63f63",
    "business": "683e8fd3a7d860028b795845", 
    "ocr": "683faa67118e26d7e280b9f4",
    "test": "683fdd811cf85394f822e4d8"
  },
  "files": {
    "finance_doc": "2cd81211-7984-4f5b-9805-29c754273a79",
    "news_doc": "5b0c35bf-bc88-4db7-8aaf-f10558fbfce2"
  },
  "reports": {
    "sample": "1b7a85e8-625a-4660-a7b5-4395fb7a6316"
  },
  "quiz": {
    "sample": "6847ada7862b6f61029b9748"
  }
}
```

---

## 📁 폴더 관리 API (folders.py)

### POST /folders/
```json
{
  "title": "API 테스트 폴더",
  "folder_type": "library",
  "cover_image_url": "https://example.com/cover.jpg"
}
```

### GET /folders/
**쿼리 파라미터**: `limit=20&skip=0`

### GET /folders/{folder_id}
**경로 파라미터**: `folder_id` (ObjectId)

### PUT /folders/{folder_id}
```json
{
  "title": "금융 분석 자료",
  "folder_type": "academic"
}
```

### DELETE /folders/{folder_id}
**쿼리 파라미터**: `force=true` (선택)

---

## 📤 파일 업로드 & 관리 API (upload.py)

### POST /upload/
**Form Data**:
```json
{
  "file": "@example.pdf",
  "folder_id": "683e9a9a324d04898ae63f63",
  "description": "테스트 문서"
}
```

### GET /api/v1/upload/status/{file_id}
**경로 파라미터**: `file_id`

### POST /api/v1/upload/search
```json
{
  "query": "금융",
  "folder_id": "683e9a9a324d04898ae63f63",
  "file_types": ["pdf"],
  "limit": 10
}
```

### GET /api/v1/upload/list
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&page=1&limit=10`

### GET /api/v1/upload/semantic-search
**쿼리 파라미터**: `query=금융%20시장&folder_id=683e9a9a324d04898ae63f63&top_k=3`

### PUT /api/v1/upload/{file_id}
```json
{
  "folder_id": "683e8fd3a7d860028b795845",
  "description": "업데이트된 설명"
}
```

### DELETE /api/v1/upload/{file_id}
**경로 파라미터**: `file_id`

### POST /upload/reprocess/{file_id}
```json
{
  "preserve_formatting": true,
  "use_original_file": true
}
```
**쿼리 파라미터**: `preserve_formatting=true&use_original_file=true`

### POST /upload/reprocess/folder/{folder_id}
```json
{
  "preserve_formatting": true
}
```
**쿼리 파라미터**: `preserve_formatting=true`

### GET /upload/reprocess/available/{file_id}
**경로 파라미터**: `file_id`

---

## 🔥 보고서 생성 및 관리 API (reports.py)

### GET /api/v1/reports/files/{folder_id}
**경로 파라미터**: `folder_id`

### POST /api/v1/reports/generate
```json
{
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
}
```

### GET /api/v1/reports/
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&limit=10&skip=0`

### GET /api/v1/reports/{report_id}
**경로 파라미터**: `report_id`

### DELETE /api/v1/reports/{report_id}
**경로 파라미터**: `report_id`

### GET /api/v1/reports/statistics/summary
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63`

---

## 🤖 하이브리드 RAG 쿼리 API (query.py)

### POST /api/v1/query/
```json
{
  "query": "금융 시장의 주요 동향은 무엇인가요?",
  "folder_id": "683e9a9a324d04898ae63f63",
  "session_id": "test_session_001",
  "use_context": true,
  "max_tokens": 500,
  "temperature": 0.2
}
```

### GET /api/v1/query/agent-info
**파라미터**: 없음

### GET /api/v1/query/sessions
**쿼리 파라미터**: `limit=10&skip=0`

### GET /api/v1/query/sessions/{session_id}
**경로 파라미터**: `session_id`

### DELETE /api/v1/query/sessions/{session_id}
**경로 파라미터**: `session_id`

### POST /api/v1/query/direct-tool
```json
{
  "tool_name": "도구명",
  "tool_input": "도구 입력 데이터"
}
```

### POST /api/v1/query/direct-chain
```json
{
  "chain_name": "체인명",
  "chain_input": "체인 입력 데이터"
}
```

---

## 📝 요약 생성 API (summary.py)

### POST /api/v1/summary/
```json
{
  "folder_id": "683e9a9a324d04898ae63f63",
  "file_ids": ["2cd81211-7984-4f5b-9805-29c754273a79"],
  "summary_type": "comprehensive",
  "max_length": 500
}
```

### GET /api/v1/summary/cached
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&limit=10`

### DELETE /api/v1/summary/cached/{cache_id}
**경로 파라미터**: `cache_id`

---

## 🗝️ 키워드 추출 API (keywords.py)

### POST /api/v1/keywords/
```json
{
  "folder_id": "683e9a9a324d04898ae63f63",
  "max_keywords": 15,
  "algorithm": "hybrid"
}
```

### POST /api/v1/keywords/from-file
```json
{
  "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
  "max_keywords": 10,
  "algorithm": "tfidf"
}
```

### POST /api/v1/keywords/from-folder
```json
{
  "folder_id": "683e9a9a324d04898ae63f63",
  "file_ids": ["2cd81211-7984-4f5b-9805-29c754273a79"],
  "max_keywords": 20,
  "include_frequency": true
}
```

---

## 🧠 퀴즈 생성 API (quiz.py)

### POST /api/v1/quiz/
```json
{
  "folder_id": "683e9a9a324d04898ae63f63",
  "file_ids": ["2cd81211-7984-4f5b-9805-29c754273a79"],
  "num_questions": 5,
  "difficulty": "medium",
  "question_types": ["multiple_choice", "true_false"]
}
```

### GET /api/v1/quiz/list
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&quiz_type=multiple_choice&page=1&limit=10`

### GET /api/v1/quiz/{quiz_id}
**경로 파라미터**: `quiz_id`

### GET /api/v1/quiz/history
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&limit=20`

### GET /api/v1/quiz/stats
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&period=30d`

### DELETE /api/v1/quiz/{quiz_id}
**경로 파라미터**: `quiz_id`

---

## 🎓 고급 퀴즈 QA 시스템 (quiz_qa.py)

### POST /api/v1/quiz-qa/submit
```json
{
  "session_id": "quiz_session_001",
  "answers": [
    {
      "question_id": "6847ada7862b6f61029b9748",
      "user_answer": "수익률 평균방식",
      "confidence_level": 4
    }
  ]
}
```

### GET /api/v1/quiz-qa/sessions/{session_id}
**경로 파라미터**: `session_id`

### GET /api/v1/quiz-qa/records
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&limit=10`

### GET /api/v1/quiz-qa/stats
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&period=30d`

### DELETE /api/v1/quiz-qa/sessions/{session_id}
**경로 파라미터**: `session_id`

### GET /api/v1/quiz-qa/analysis/detailed
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&analysis_type=comprehensive`

### GET /api/v1/quiz-qa/analysis/weekly
**쿼리 파라미터**: `weeks_back=8&folder_id=683e9a9a324d04898ae63f63`

### GET /api/v1/quiz-qa/analysis/recommendations
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&recommendation_type=adaptive`

---

## 🧠 마인드맵 생성 API (mindmap.py)

### POST /api/v1/mindmap/
```json
{
  "folder_id": "683e9a9a324d04898ae63f63",
  "file_ids": ["2cd81211-7984-4f5b-9805-29c754273a79"],
  "map_type": "hierarchical",
  "max_nodes": 30,
  "depth_level": 4
}
```

---

## 💡 추천 시스템 API (recommend.py)

### POST /api/v1/recommend/
```json
{
  "query": "금융 시장 분석 방법",
  "folder_id": "683e9a9a324d04898ae63f63",
  "recommendation_types": ["web", "youtube", "documents"],
  "max_results_per_type": 3
}
```

### POST /api/v1/recommend/from-file
```json
{
  "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
  "recommendation_types": ["web", "youtube"],
  "max_results_per_type": 5
}
```

### GET /api/v1/recommend/cached
**쿼리 파라미터**: `folder_id=683e9a9a324d04898ae63f63&limit=10`

### DELETE /api/v1/recommend/cached/{cache_id}
**경로 파라미터**: `cache_id`

---

## 📝 메모 관리 API (memos.py)

### POST /api/v1/memos/
```json
{
  "folder_id": "683e9a9a324d04898ae63f63",
  "title": "금융 시장 학습 노트",
  "content": "오늘 학습한 금융 시장 분석 방법들을 정리하면...",
  "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
  "tags": ["금융", "학습노트", "시장분석"]
}
```

### GET /api/v1/memos/folder/{folder_id}
**쿼리 파라미터**: `limit=10&skip=0`

### GET /api/v1/memos/{memo_id}
**경로 파라미터**: `memo_id`

### PUT /api/v1/memos/{memo_id}
```json
{
  "title": "업데이트된 금융 학습 노트",
  "content": "수정된 학습 내용...",
  "tags": ["금융", "학습노트", "업데이트"]
}
```

### DELETE /api/v1/memos/{memo_id}
**경로 파라미터**: `memo_id`

---

## 🔆 하이라이트 관리 API (highlights.py)

### POST /api/v1/highlights/
```json
{
  "folder_id": "683e9a9a324d04898ae63f63",
  "file_id": "2cd81211-7984-4f5b-9805-29c754273a79",
  "highlighted_text": "금융 시장의 변동성은 투자 결정에 중요한 요소이다",
  "context_before": "최근 연구에 따르면",
  "context_after": "따라서 신중한 분석이 필요하다",
  "color": "yellow",
  "note": "중요한 개념 - 복습 필요"
}
```

### GET /api/v1/highlights/file/{file_id}
**쿼리 파라미터**: `limit=20`

### GET /api/v1/highlights/folder/{folder_id}
**쿼리 파라미터**: `limit=20&skip=0`

### PUT /api/v1/highlights/{highlight_id}
```json
{
  "color": "green",
  "note": "매우 중요 - 시험 출제 예상"
}
```

### DELETE /api/v1/highlights/{highlight_id}
**경로 파라미터**: `highlight_id`

---

## 🔗 OCR 브릿지 API (ocr_bridge.py)

### GET /api/v1/ocr-bridge/stats
**파라미터**: 없음

### POST /api/v1/ocr-bridge/sync
```json
{
  "since_timestamp": "2024-12-20T00:00:00Z",
  "batch_size": 50
}
```

### POST /api/v1/ocr-bridge/sync/force
**파라미터**: 없음 (⚠️ 주의: 대용량 처리)

### GET /api/v1/ocr-bridge/status
**파라미터**: 없음

### GET /api/v1/ocr-bridge/folder/ocr
**파라미터**: 없음

### GET /api/v1/ocr-bridge/folders/list
**쿼리 파라미터**: `limit=20`

---

## 🎯 테스트 시나리오

### 시나리오 1: 완전한 RAG 워크플로우
1. **폴더 생성**: `POST /api/v1/folders/`
2. **파일 업로드**: `POST /api/v1/upload/`
3. **하이브리드 쿼리**: `POST /api/v1/query/`
4. **요약 생성**: `POST /api/v1/summary/`
5. **퀴즈 생성**: `POST /api/v1/quiz/`
6. **보고서 생성**: `POST /api/v1/reports/generate`

### 시나리오 2: 금융 폴더 활용
1. **폴더 조회**: `GET /api/v1/folders/683e9a9a324d04898ae63f63`
2. **질문 답변**: `POST /api/v1/query/`
3. **키워드 추출**: `POST /api/v1/keywords/`
4. **마인드맵**: `POST /api/v1/mindmap/`
5. **추천 시스템**: `POST /api/v1/recommend/`

### 시나리오 3: 고급 퀴즈 학습
1. **퀴즈 생성**: `POST /api/v1/quiz/`
2. **답안 제출**: `POST /api/v1/quiz-qa/submit`
3. **학습 통계**: `GET /api/v1/quiz-qa/stats`
4. **개인화 추천**: `GET /api/v1/quiz-qa/analysis/recommendations`

---

## ✅ 핵심 포인트

### 🥇 최우선 테스트 API
1. `POST /api/v1/upload/` - 파일 업로드
2. `POST /api/v1/query/` - 하이브리드 RAG 쿼리
3. `POST /api/v1/reports/generate` - 보고서 생성
4. `POST /api/v1/quiz/` - 퀴즈 생성

### 🎯 권장 테스트 ID
- **폴더**: `683e9a9a324d04898ae63f63` (금융)
- **파일**: `2cd81211-7984-4f5b-9805-29c754273a79`
- **퀴즈**: `6847ada7862b6f61029b9748`

**🎉 LangChain SEEQ RAG v3.0 - 13개 라우터, 62개 엔드포인트 완전 API 가이드** 
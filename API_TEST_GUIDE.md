# 🧪 RAG 백엔드 API 엔드포인트 테스트 가이드

**기본 정보:**
- 서버 URL: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs` (Swagger UI)
- 데이터베이스: `mongodb+srv://SeeQ:la5kFgpTy8xR52rr@cluster0.8lbrl0r.mongodb.net/rag_database`

---

## 1. 폴더 관리 (Folders) - `/folders`

### 1.1 폴더 생성
**POST** `/folders/`
```json
{
  "title": "AI 학습 자료",
  "folder_type": "academic",
  "cover_image_url": "https://example.com/image.jpg"
}
```

### 1.2 폴더 목록 조회
**GET** `/folders/`
```
Query: ?limit=50&skip=0
```

### 1.3 특정 폴더 조회
**GET** `/folders/{folder_id}`
```
Path: /folders/64f7b8a12345678901234567
```

### 1.4 폴더 정보 수정
**PUT** `/folders/{folder_id}`
```json
{
  "title": "수정된 폴더명",
  "folder_type": "research"
}
```

### 1.5 폴더 삭제
**DELETE** `/folders/{folder_id}`
```
Query: ?force=false
```

---

## 2. 파일 업로드 및 관리 (Upload) - `/upload`

### 2.1 파일 업로드 (folder_id 사용)
**POST** `/upload/`
```json
{
  "file": "업로드할 파일",
  "folder_id": "64f7b8a12345678901234567",
  "description": "AI 관련 연구 논문"
}
```

### 2.2 파일 업로드 (folder_title 사용)
**POST** `/upload/`
```json
{
  "file": "업로드할 파일",
  "folder_title": "AI 학습 자료",
  "description": "마케팅 관리 중간고사 정리 자료"
}
```

### 2.3 파일 상태 조회
**GET** `/upload/status/{file_id}`
```
Path: /upload/status/550e8400-e29b-41d4-a716-446655440000
```

### 2.4 파일 검색
**POST** `/upload/search`
```json
{
  "query": "머신러닝",
  "search_type": "both",
  "folder_id": "64f7b8a12345678901234567",
  "limit": 10,
  "skip": 0
}
```

### 2.5 파일 목록 조회
**GET** `/upload/list`
```
Query: ?folder_id=64f7b8a12345678901234567&limit=50&skip=0
```

### 2.6 시맨틱 검색
**GET** `/upload/semantic-search`
```
Query: ?q=머신러닝&k=5&folder_id=64f7b8a12345678901234567
```

### 2.7 파일 내용 조회
**GET** `/upload/content/{file_id}`
```
Path: /upload/content/550e8400-e29b-41d4-a716-446655440000
```

### 2.8 파일 정보 수정
**PUT** `/upload/{file_id}`
```json
{
  "filename": "새로운_파일명.pdf",
  "description": "수정된 설명",
  "folder_id": "64f7b8a12345678901234567"
}
```

### 2.9 파일 미리보기
**GET** `/upload/preview/{file_id}`
```
Query: ?max_length=500
```

### 2.10 파일 청크 미리보기
**GET** `/upload/preview/chunks/{file_id}`
```
Query: ?max_chunks=5
```

### 2.11 파일 삭제
**DELETE** `/upload/{file_id}`
```
Path: /upload/550e8400-e29b-41d4-a716-446655440000
```

---

## 3. 질의응답 (Query) - `/query`

### 3.1 질의 처리
**POST** `/query/`
```json
{
  "query": "머신러닝이란 무엇인가요?",
  "folder_id": "64f7b8a12345678901234567",
  "top_k": 5,
  "include_sources": true,
  "session_id": "optional_session_id"
}
```

### 3.2 에이전트 정보 조회
**GET** `/query/agent-info`
```
응답 확인용 (JSON 파라미터 없음)
```

### 3.3 모든 세션 조회
**GET** `/query/sessions`
```
응답 확인용 (JSON 파라미터 없음)
```

### 3.4 특정 세션 정보 조회
**GET** `/query/sessions/{session_id}`
```
Path: /query/sessions/session_id_example
```

### 3.5 세션 삭제
**DELETE** `/query/sessions/{session_id}`
```
Path: /query/sessions/session_id_example
```

---

## 4. 요약 (Summary) - `/summary`

### 4.1 요약 생성 (폴더 기반)
**POST** `/summary/`
```json
{
  "folder_id": "64f7b8a12345678901234567",
  "summary_type": "detailed"
}
```

### 4.2 요약 생성 (문서 기반)
**POST** `/summary/`
```json
{
  "document_ids": ["file1", "file2", "file3"],
  "summary_type": "brief"
}
```

### 4.3 캐시된 요약 목록 조회
**GET** `/summary/cached`
```
Query: ?folder_id=64f7b8a12345678901234567&limit=10
```

### 4.4 요약 캐시 삭제
**DELETE** `/summary/cached/{cache_id}`
```
Path: /summary/cached/cache_id_example
```

---

## 5. 퀴즈 (Quiz) - `/quiz`

### 5.1 퀴즈 생성
**POST** `/quiz/`
```json
{
  "topic": "머신러닝",
  "folder_id": "64f7b8a12345678901234567",
  "difficulty": "medium",
  "count": 5,
  "quiz_type": "multiple_choice"
}
```

### 5.2 퀴즈 히스토리 조회
**GET** `/quiz/history`
```
Query: ?folder_id=64f7b8a12345678901234567&limit=20
```

### 5.3 퀴즈 통계 조회
**GET** `/quiz/stats`
```
Query: ?folder_id=64f7b8a12345678901234567
```

### 5.4 퀴즈 삭제
**DELETE** `/quiz/{quiz_id}`
```
Path: /quiz/quiz_id_example
```

---

## 6. 퀴즈 QA 시스템 (Quiz QA) - `/quiz-qa`

### 6.1 퀴즈 답안 제출 및 채점
**POST** `/quiz-qa/submit`
```json
{
  "session_id": "unique_session_id",
  "folder_id": "64f7b8a12345678901234567",
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

### 6.2 퀴즈 세션 조회
**GET** `/quiz-qa/sessions/{session_id}`
```
Path: /quiz-qa/sessions/unique_session_id
```

### 6.3 퀴즈 기록 조회
**GET** `/quiz-qa/records`
```
Query: ?page=1&limit=10&folder_id=64f7b8a12345678901234567
```

### 6.4 개인 통계 조회
**GET** `/quiz-qa/stats`
```
Query: ?folder_id=64f7b8a12345678901234567
```

### 6.5 퀴즈 세션 삭제
**DELETE** `/quiz-qa/sessions/{session_id}`
```
Path: /quiz-qa/sessions/unique_session_id
```

### 6.6 상세 분석 보고서
**GET** `/quiz-qa/analysis/detailed`
```
Query: ?folder_id=64f7b8a12345678901234567&days=30
```

### 6.7 주간 성과 리포트
**GET** `/quiz-qa/analysis/weekly`
```
Query: ?folder_id=64f7b8a12345678901234567
```

### 6.8 개인화 추천
**GET** `/quiz-qa/analysis/recommendations`
```
Query: ?folder_id=64f7b8a12345678901234567&limit=5
```

---

## 7. 키워드 추출 (Keywords) - `/keywords`

### 7.1 텍스트에서 키워드 추출
**POST** `/keywords/`
```json
{
  "text": "머신러닝은 인공지능의 한 분야로, 컴퓨터가 명시적으로 프로그래밍되지 않고도 학습할 수 있는 능력을 제공합니다.",
  "max_keywords": 10
}
```

### 7.2 파일에서 키워드 추출
**POST** `/keywords/from-file`
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "max_keywords": 10,
  "use_chunks": true
}
```

### 7.3 폴더에서 키워드 추출
**POST** `/keywords/from-folder`
```json
{
  "folder_id": "64f7b8a12345678901234567",
  "max_keywords": 15,
  "use_chunks": false
}
```

### 7.4 폴더에서 키워드 추출 (간단 API)
**POST** `/keywords/from-folder`
```
Query: ?folder_id=64f7b8a12345678901234567&max_keywords=10&use_chunks=true
```

---

## 8. 마인드맵 (Mindmap) - `/mindmap`

### 8.1 마인드맵 생성
**POST** `/mindmap/`
```json
{
  "root_keyword": "머신러닝",
  "depth": 3,
  "max_nodes": 20,
  "folder_id": "64f7b8a12345678901234567"
}
```

---

## 9. 추천 (Recommend) - `/recommend`

### 9.1 키워드 기반 추천
**POST** `/recommend/`
```json
{
  "keywords": ["머신러닝", "딥러닝", "AI"],
  "content_types": ["book", "movie", "youtube_video"],
  "max_items": 10,
  "include_youtube": true,
  "youtube_max_per_keyword": 3,
  "folder_id": "64f7b8a12345678901234567"
}
```

### 9.2 파일 기반 자동 추천
**POST** `/recommend/from-file`
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "content_types": ["book", "youtube_video"],
  "max_items": 10,
  "include_youtube": true,
  "youtube_max_per_keyword": 3,
  "max_keywords": 5
}
```

### 9.3 폴더 기반 자동 추천 (from-file로 통합됨)
**POST** `/recommend/from-file`
```json
{
  "folder_id": "64f7b8a12345678901234567",
  "content_types": ["book", "movie"],
  "max_items": 8,
  "include_youtube": false,
  "max_keywords": 3
}
```

### 9.4 캐시된 추천 목록 조회
**GET** `/recommend/cached`
```
Query: ?folder_id=64f7b8a12345678901234567&limit=10
```

### 9.5 추천 캐시 삭제
**DELETE** `/recommend/cached/{cache_id}`
```
Path: /recommend/cached/cache_id_example
```

---

## 10. OCR 브릿지 (OCR Bridge) - `/ocr-bridge`

### 10.1 OCR 브릿지 홈
**GET** `/ocr-bridge/`
```
응답 확인용 (JSON 파라미터 없음)
```

### 10.2 OCR 통계 조회
**GET** `/ocr-bridge/stats`
```
응답 확인용 (JSON 파라미터 없음)
```

### 10.3 OCR 데이터 동기화
**POST** `/ocr-bridge/sync`
```json
{
  "force_resync": false
}
```

### 10.4 OCR 브릿지 상태 조회
**GET** `/ocr-bridge/status`
```
응답 확인용 (JSON 파라미터 없음)
```

### 10.5 OCR 폴더 조회
**GET** `/ocr-bridge/folder/ocr`
```
응답 확인용 (JSON 파라미터 없음)
```

---

## 11. 기본 정보 조회

### 11.1 루트 엔드포인트
**GET** `/`
```
응답 확인용 (JSON 파라미터 없음)
```

---

## 📝 테스트용 샘플 데이터

### 폴더 ID 예시
```
64f7b8a12345678901234567
```

### 파일 ID 예시
```
550e8400-e29b-41d4-a716-446655440000
```

### 테스트용 텍스트
```
"머신러닝은 인공지능의 한 분야로, 컴퓨터가 명시적으로 프로그래밍되지 않고도 학습할 수 있는 능력을 제공합니다. 딥러닝, 자연어처리, 컴퓨터비전 등이 주요 응용 분야입니다."
```

### 테스트용 키워드 배열
```
["머신러닝", "딥러닝", "AI", "인공지능", "자연어처리"]
```

---

## 🧪 빠른 테스트 시나리오

### 1. 기본 워크플로우
```bash
1. POST /folders/ (폴더 생성)
2. POST /upload/ (파일 업로드)
3. POST /query/ (질의응답)
4. POST /summary/ (요약 생성)
5. POST /quiz/ (퀴즈 생성)
```

### 2. 분석 워크플로우
```bash
1. POST /keywords/from-file (키워드 추출)
2. POST /mindmap/ (마인드맵 생성)
3. POST /recommend/from-file (추천 생성)
4. POST /quiz-qa/submit (퀴즈 답안 제출)
```

---

**💡 테스트 팁:**
- 먼저 폴더 생성 → 파일 업로드 → 기타 기능 테스트 순서로 진행
- 생성된 리소스의 ID를 기록하여 후속 테스트에 활용
- 한국어 검색어는 URL 인코딩 필요 (시맨틱 검색)
- Form Data 업로드 시 파일 첨부 필수
- 최신 업데이트: 퀴즈 QA 시스템, OCR 브릿지 통합 (2025-06-08) 
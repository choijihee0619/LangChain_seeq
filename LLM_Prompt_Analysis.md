# SEEQ RAG v3.0 시스템의 LLM 프롬프트 분석 및 설명

전체 코드를 분석한 결과, **SEEQ RAG v3.0**은 OpenAI GPT-4o-mini를 기반으로 다양한 기능별로 체계적으로 설계된 프롬프트 전략을 사용하고 있습니다. 주요 프롬프트 적용 부분을 분석해드리겠습니다.

---

## 📋 1. 기본 LLM 클라이언트 아키텍처

### `langchain_llm/ai_processing/llm_client.py`

기본 클라이언트에서는 **시스템 프롬프트와 사용자 프롬프트 분리** 구조를 사용합니다:

```python
class LLMClient:
    """LLM 클라이언트 클래스"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
```

```python
async def generate(
    self,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """LLM 응답 생성"""
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
```

**컨텍스트 기반 응답을 위한 기본 템플릿:**

```python
prompt = f"""다음 컨텍스트를 참고하여 질문에 답변해주세요.

컨텍스트:
{context}

질문: {query}

답변:"""
```

---

## 🎯 2. 하이브리드 응답 시스템 프롬프트

### `langchain_llm/seeq_langchain/agents/hybrid_responder.py`

가장 핵심적인 **3단계 응답 전략**을 구현합니다:
    < 전략별 유사도 임계값 >
    0.8 이상: 벡터 기반 응답 (데이터베이스 문서 직접 활용)
    0.3~0.8: 하이브리드 응답 (부분 문서 + 일반 지식)
    0.3 미만: 일반 지식 응답 (OpenAI 기본 지식)

### 2.1 벡터 기반 응답 (Vector-based)
```python
prompt = f"""
당신은 친근하고 도움이 되는 AI 어시스턴트입니다.
아래 문서 내용을 바탕으로 사용자의 질문에 답변해주세요.

참고 문서:
{context}

질문: {query}

답변 마지막에는 다음과 같이 출처를 명시해주세요:

📚 **참고 문서:**
{sources_text}
"""
```

### 2.2 하이브리드 응답 (Hybrid)
```python
prompt = f"""
당신은 친근하고 지식이 풍부한 AI 어시스턴트입니다.
제공된 문서에는 부분적인 관련 정보만 있습니다. 이 정보를 참고하되, 부족한 부분은 당신의 일반 지식으로 보완하여 완전한 답변을 제공해주세요.

부분적 관련 문서:
{context}

질문: {query}

답변 형식:
1. 문서에서 찾은 정보: [문서 내용 기반]
2. 추가 일반 정보: [일반 지식 기반]

📚 **참고한 문서:**
{sources_text}
"""
```

### 2.3 일반 지식 기반 응답 (General Knowledge)
```python
prompt = f"""
질문: {query}

❌ **데이터베이스 검색 결과:** 이 질문과 관련된 문서를 찾을 수 없었습니다.

💡 **일반 지식 기반 답변:**
당신의 일반적인 지식을 바탕으로 위 질문에 대해 정확하고 유용한 정보를 제공해주세요.
"""
```

---

## 🏷️ 3. 자동 라벨링 시스템 프롬프트

### `langchain_llm/ai_processing/auto_labeler.py`

**구조화된 JSON 출력**을 위한 상세 프롬프트:

```python
prompt = f"""다음 텍스트를 분석하여 JSON 형식으로 라벨링 정보를 제공해주세요.
{hint_text}

분석할 텍스트:
{text}

다음 형식으로 응답해주세요:
{{
    "tags": ["태그1", "태그2", "태그3"],
    "category": "카테고리",
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "confidence_score": 0.8
}}

카테고리는 다음 중 하나를 선택해주세요:
{', '.join(self.categories)}

**키워드 추출 가이드라인:**
- 일반적인 단어(데이터, 기술, 사회 등) 대신 구체적이고 전문적인 용어를 선택하세요
- 예시: "데이터" → "빅데이터", "머신러닝", "데이터마이닝"
- 예시: "기술" → "블록체인", "인공지능", "클라우드컴퓨팅"  
- 예시: "경제" → "핀테크", "디지털경제", "암호화폐"
- 브랜드명, 제품명, 기술명, 학술용어 등 구체적인 명사를 우선하세요
- 추상적이거나 포괄적인 단어는 피하세요

태그는 3-5개 정도로, 키워드는 3-7개 정도로 제한해주세요.
confidence_score는 0.0-1.0 사이의 분석 신뢰도입니다."""
```

---

## 🎓 4. 퀴즈 생성 시스템 프롬프트

### `langchain_llm/ai_processing/qa_generator.py`

### 4.1 QA 쌍 생성
```python
prompt = f"""다음 텍스트를 읽고 {num_pairs}개의 질문-답변 쌍을 생성해주세요.

텍스트:
{text}

다음 JSON 배열 형식으로 응답해주세요:
[
    {{
        "question": "질문 내용",
        "answer": "답변 내용",
        "question_type": "factoid|reasoning|summary 중 하나",
        "difficulty": "easy|medium|hard 중 하나"
    }}
]
"""
```

### 4.2 객관식 퀴즈 생성
```python
prompt = f"""다음 텍스트를 읽고 객관식 퀴즈를 생성해주세요.{difficulty_prompt}

텍스트:
{text}

다음 JSON 형식으로 응답해주세요:
{{
    "question": "퀴즈 질문",
    "options": ["선택지1", "선택지2", "선택지3", "선택지4"],
    "correct_option": 0,
    "explanation": "정답 설명",
    "difficulty": "{difficulty or 'medium'}"
}}

중요: 반드시 유효한 JSON 형식으로만 응답하세요."""
```

### 4.3 참/거짓 퀴즈 생성
```python
prompt = f"""다음 텍스트를 읽고 참/거짓 퀴즈를 생성해주세요.{difficulty_prompt}

텍스트:
{text}

다음 JSON 형식으로 응답해주세요:
{{
    "question": "참/거짓 질문",
    "options": ["참", "거짓"],
    "correct_option": 0,
    "explanation": "정답 설명",
    "difficulty": "{difficulty or 'medium'}"
}}

중요: 반드시 유효한 JSON 형식으로만 응답하세요."""
```

### 4.4 단답형 퀴즈 생성
```python
prompt = f"""다음 텍스트를 읽고 단답형 퀴즈를 생성해주세요.{difficulty_prompt}

텍스트:
{text}

다음 JSON 형식으로 응답해주세요:
{{
    "question": "단답형 질문",
    "correct_answer": "정답",
    "explanation": "정답 설명",
    "difficulty": "{difficulty or 'medium'}"
}}

중요: 반드시 유효한 JSON 형식으로만 응답하세요."""
```

### 4.5 빈 칸 채우기 퀴즈 생성
```python
prompt = f"""다음 텍스트를 읽고 빈 칸 채우기 퀴즈를 생성해주세요.{difficulty_prompt}

텍스트:
{text}

다음 JSON 형식으로 응답해주세요:
{{
    "question": "빈 칸이 포함된 문장 (빈 칸은 ___로 표시)",
    "correct_answer": "빈 칸에 들어갈 정답",
    "explanation": "정답 설명",
    "difficulty": "{difficulty or 'medium'}"
}}

중요: 반드시 유효한 JSON 형식으로만 응답하세요."""
```

---

## 📊 5. 학술 보고서 생성 프롬프트

### `langchain_llm/ai_processing/report_generator.py`

### 5.1 내용 분석 프롬프트
```python
prompt = f"""
다음 문서 내용을 분석하여 학술적 보고서 작성에 필요한 정보를 추출해주세요.

문서 내용:
{content}

분석 항목:
1. 주요 주제 (메인 주제 1개)
2. 핵심 키워드 (5-10개)
3. 주요 개념들 (3-5개)  
4. 문서의 전체적인 성격 (설명적, 분석적, 비교적 등)
5. 학문 분야 또는 도메인

JSON 형태로 답변해주세요:
{{
    "main_topic": "주요 주제",
    "keywords": ["키워드1", "키워드2", ...],
    "key_concepts": ["개념1", "개념2", ...],
    "document_nature": "문서 성격",
    "academic_domain": "학문 분야"
}}
"""
```

### 5.2 제목과 부제목 생성 프롬프트
```python
prompt = f"""
다음 분석 결과를 바탕으로 학술적 보고서의 제목과 부제목을 생성해주세요.

분석 결과:
- 주요 주제: {analysis['main_topic']}
- 키워드: {', '.join(analysis['keywords'])}
- 학문 분야: {analysis['academic_domain']}

요구사항:
- 제목: 간결하고 학술적이며 내용을 잘 표현하는 제목
- 부제목: 제목을 보완하고 구체적인 내용을 암시하는 부제목
- 한국어로 작성

JSON 형태로 답변:
{{
    "title": "보고서 제목",
    "subtitle": "보고서 부제목"
}}
"""
```

### 5.3 서론 생성 프롬프트
```python
prompt = f"""
다음 정보를 바탕으로 학술적 보고서의 서론을 작성해주세요.

보고서 제목: {title}
주요 주제: {analysis['main_topic']}
키워드: {', '.join(analysis['keywords'])}
학문 분야: {analysis['academic_domain']}

서론 작성 요구사항:
- 연구의 배경과 목적 제시
- 주요 주제의 중요성 설명
- 보고서의 구성과 범위 안내
- 학술적 톤앤매너 유지
- 3-4 문단, 300-500자 내외
- 한국어로 작성
"""
```

### 5.4 본론 구성 프롬프트 (3섹션 구조)
```python
prompt = f"""
다음 문서 내용과 분석 결과를 바탕으로 학술적 보고서의 본론을 3개 섹션으로 구성해주세요.

문서 내용:
{content[:8000]}  # 토큰 제한 고려

분석 결과:
- 주요 주제: {analysis['main_topic']}
- 핵심 개념: {', '.join(analysis['key_concepts'])}
- 문서 성격: {analysis['document_nature']}

본론 구성 요구사항:
- 섹션 1: 현황 및 배경 분석
- 섹션 2: 핵심 내용 및 주요 발견사항
- 섹션 3: 시사점 및 의미 해석
- 각 섹션별 500-800자 내외
- 논리적 흐름과 연결성 유지
- 구체적 내용과 예시 포함
- 학술적 표현 사용

JSON 형태로 답변:
{{
    "section_1": {{
        "title": "섹션1 제목",
        "content": "섹션1 내용"
    }},
    "section_2": {{
        "title": "섹션2 제목", 
        "content": "섹션2 내용"
    }},
    "section_3": {{
        "title": "섹션3 제목",
        "content": "섹션3 내용"
    }}
}}
"""
```

### 5.5 결론 생성 프롬프트
```python
prompt = f"""
다음 정보를 바탕으로 학술적 보고서의 결론을 작성해주세요.

보고서 제목: {title}
주요 주제: {analysis['main_topic']}
핵심 개념: {', '.join(analysis['key_concepts'])}

결론 작성 요구사항:
- 주요 발견사항 요약
- 핵심 메시지 강조
- 향후 과제나 제언 포함
- 보고서의 의의와 기여도 언급
- 3-4 문단, 300-500자 내외
- 학술적 톤앤매너 유지
- 한국어로 작성
"""
```

---

## 🔍 6. 질의응답 체인 프롬프트

### `langchain_llm/api/chains/query_chain.py`

**RAG 파이프라인의 기본 템플릿:**

```python
self.prompt_template = """다음 컨텍스트를 참고하여 사용자의 질문에 답변해주세요.
답변은 정확하고 도움이 되도록 작성하되, 컨텍스트에 없는 내용은 추측하지 마세요.

컨텍스트:
{context}

질문: {question}

답변:"""
```

---

## 🔗 7. LangChain 통합 프롬프트

### 7.1 대화형 검색 체인
```python
custom_prompt = PromptTemplate(
    template="""다음 컨텍스트를 기반으로 질문에 답변해주세요. 컨텍스트에 관련 정보가 없다면, 일반적인 지식을 활용하여 도움이 되는 답변을 제공해주세요.

컨텍스트:
{context}

채팅 기록:
{chat_history}

질문: {question}

답변을 작성할 때:
1. 컨텍스트의 정보를 최우선으로 활용하세요
2. 컨텍스트에 없는 내용이라도 질문에 도움이 되는 일반적인 정보를 제공하세요
3. 답변의 근거를 명확히 제시하세요
4. 한국어로 자연스럽고 친근하게 답변하세요

답변:""",
    input_variables=["context", "chat_history", "question"]
)
```

### 7.2 RetrievalQA 체인 프롬프트
```python
custom_prompt = PromptTemplate(
    template="""컨텍스트를 기반으로 질문에 정확하고 간결하게 답변해주세요. 
컨텍스트에 관련 정보가 없다면, 일반적인 지식을 활용하여 도움이 되는 답변을 제공하세요.

컨텍스트:
{context}

질문: {question}

답변 가이드라인:
- 컨텍스트의 정보를 최우선으로 활용
- 컨텍스트에 없어도 질문에 도움되는 일반 지식 제공
- 명확하고 구체적인 답변
- 한국어로 자연스럽게 작성

답변:""",
    input_variables=["context", "question"]
)
```

### 7.3 ReAct 에이전트 프롬프트
```python
react_prompt = PromptTemplate.from_template("""
다음 도구들을 사용하여 질문에 답변하세요. 도구를 사용할 때는 정확한 형식을 따르세요.

사용 가능한 도구들:
{tools}

도구 사용 형식:
```
Action: 도구명
Action Input: 도구에 전달할 입력
```

질문: {input}

생각 과정을 단계별로 설명하고 필요한 도구를 사용하세요.

{agent_scratchpad}
""")
```

### 7.4 MapReduce 체인 프롬프트
```python
# Map 단계 템플릿
map_template = """다음 문서의 핵심 내용을 요약해주세요:

문서:
{docs}

요약:"""

# Reduce 단계 템플릿  
reduce_template = """다음은 여러 문서의 요약들입니다. 이를 종합하여 전체적인 요약을 작성해주세요:

요약들:
{doc_summaries}

전체 요약:"""
```

### 7.5 Sequential 체인 프롬프트
```python
# 분석 단계 프롬프트
analysis_prompt = PromptTemplate(
    input_variables=["input"],
    template="다음 텍스트를 분석해주세요:\n\n{input}\n\n분석 결과:"
)

# 요약 단계 프롬프트
summary_prompt = PromptTemplate(
    input_variables=["analysis"],
    template="다음 분석 결과를 요약해주세요:\n\n{analysis}\n\n요약:"
)

# 결론 단계 프롬프트
conclusion_prompt = PromptTemplate(
    input_variables=["summary"],
    template="다음 요약을 바탕으로 결론을 도출해주세요:\n\n{summary}\n\n결론:"
)
```

---

## 📝 8. 요약 체인 프롬프트

### `langchain_llm/api/chains/summary_chain.py`

### 8.1 간단 요약 프롬프트
```python
prompt = f"다음 텍스트를 1-2문장으로 간단히 요약해주세요:\n\n{combined_text}"
```

### 8.2 상세 요약 프롬프트
```python
prompt = f"다음 텍스트를 상세하게 요약해주세요. 주요 내용과 핵심 포인트를 포함하여 작성해주세요:\n\n{combined_text}"
```

### 8.3 불릿 포인트 요약 프롬프트
```python
prompt = f"다음 텍스트의 핵심 내용을 불릿 포인트로 정리해주세요:\n\n{combined_text}"
```

---

## 💡 9. 키워드 추출 프롬프트

### `langchain_llm/ai_processing/auto_labeler.py`

### 9.1 포커스 키워드 기반 추출
```python
prompt = f"""다음 텍스트에서 '{focus_keyword}'와 직접적으로 관련된 핵심 키워드 {max_keywords}개를 추출해주세요.

텍스트:
{text}

요구사항:
- {focus_keyword}와 관련성이 높은 키워드만 선택
- 구체적이고 전문적인 용어 우선
- 중복 제거
- 한국어로 답변

키워드: [키워드1, 키워드2, ...]"""
```

### 9.2 일반 키워드 추출
```python
prompt = f"""다음 텍스트에서 핵심 키워드 {max_keywords}개를 추출해주세요.

텍스트:
{text}

키워드 추출 가이드라인:
- 구체적이고 의미 있는 단어 선택
- 추상적 개념보다는 명확한 개념 우선
- 전문 용어, 고유명사, 핵심 개념 포함
- 일반적인 단어(것, 이것, 그것 등) 제외
- 한국어로 답변

키워드: [키워드1, 키워드2, ...]"""
```

---

## 📈 시스템 프롬프트 특징 분석

### 🎯 1. **응답 전략별 프롬프트 분화**
- **벡터 기반**: 문서 중심 응답
- **하이브리드**: 문서 + 일반 지식 혼합
- **일반 지식**: 순수 AI 지식 활용

### 🎯 2. **구조화된 출력 제어**
- JSON 스키마 명시로 일관된 데이터 구조
- 예시와 가이드라인으로 품질 제어
- 유효성 검증 로직 포함

### 🎯 3. **한국어 최적화**
- 한국어 맥락과 뉘앙스 고려
- 학술적/친근한 톤앤매너 제어
- 문화적 적절성 반영

### 🎯 4. **토큰 효율성**
- 텍스트 길이 제한 (8000자, 3000자 등)
- 컨텍스트 우선순위 설정
- 핵심 정보 추출 전략

### 🎯 5. **오류 처리 및 대안**
- 파싱 실패 시 기본값 제공
- 다단계 검증 로직
- Fallback 메커니즘 구현

---

## 🔧 프롬프트 엔지니어링 전략

### 1. **역할 정의 (Role Definition)**
- "친근한 AI 어시스턴트"
- "학술적 보고서 작성자"
- "지식이 풍부한 전문가"

### 2. **출력 형식 강제 (Format Enforcement)**
- JSON 스키마 명시
- 구체적 예시 제공
- 구조화된 응답 템플릿

### 3. **품질 가이드라인 (Quality Guidelines)**
- 구체적 vs 추상적 키워드 구분
- 학술적 표현 요구사항
- 한국어 자연스러운 표현

### 4. **컨텍스트 우선순위 (Context Priority)**
- 문서 정보 > 일반 지식
- 출처 명시 의무화
- 확신도 표시

### 5. **오류 방지 전략 (Error Prevention)**
- 필수 필드 검증
- 기본값 설정
- 안전한 JSON 파싱

### 6. **토큰 최적화 (Token Optimization)**
- 길이 제한 설정
- 핵심 정보 우선 처리
- 단계별 정보 전달

---

## 📊 프롬프트 성능 최적화 요소

### 1. **Temperature 설정**
- 분석/분류: 0.1-0.3 (정확성 중시)
- 창작/생성: 0.5-0.7 (창의성 중시)
- 일반 응답: 0.7 (균형)

### 2. **Max Tokens 제한**
- 키워드 추출: 150 토큰
- 퀴즈 생성: 400 토큰
- 보고서 생성: 800-2500 토큰

### 3. **프롬프트 구조**
- 명확한 태스크 정의
- 단계별 지침 제공
- 예시 및 제약사항 명시

### 4. **품질 보장**
- 다단계 검증
- 오류 처리 로직
- 대안 시나리오 준비

---

## 🎯 결론

**SEEQ RAG v3.0**의 프롬프트 시스템은 다음과 같은 특징을 가집니다:

1. **모듈화된 설계**: 기능별 특화된 프롬프트 템플릿
2. **일관성 있는 출력**: JSON 스키마 기반 구조화
3. **한국어 최적화**: 자연스러운 한국어 표현 유도
4. **오류 방지**: 다중 검증 및 Fallback 메커니즘
5. **성능 최적화**: 토큰 효율성 및 응답 품질 균형

이러한 체계적인 프롬프트 설계를 통해 **SEEQ RAG v3.0**은 다양한 문서 분석 작업에서 일관되고 고품질의 결과를 생성할 수 있는 시스템을 구축했습니다.

---

**📅 문서 생성일**: 2025-06-16  
**🏷️ 버전**: v1.0  
**📝 작성자**: SEEQ RAG 시스템 분석 
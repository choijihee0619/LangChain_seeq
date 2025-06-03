"""
QA 생성 모듈
LLM을 사용한 질문-답변 쌍 및 퀴즈 생성
MODIFIED 2024-12-19: models 의존성 제거하여 단순화
"""
from typing import List, Dict, Optional
import json
from ai_processing.llm_client import LLMClient
from utils.logger import get_logger

logger = get_logger(__name__)

class QAGenerator:
    """QA 생성 클래스"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    async def generate_qa_pairs(
        self,
        text: str,
        num_pairs: int = 3
    ) -> List[Dict]:
        """텍스트에서 QA 쌍 생성"""
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
        
        try:
            response = await self.llm_client.generate(
                prompt,
                temperature=0.5,
                max_tokens=800
            )
            
            # JSON 파싱
            qa_pairs = json.loads(response)
            return qa_pairs
        except Exception as e:
            logger.error(f"QA 생성 실패: {e}")
            return []
    
    async def generate_quiz(
        self,
        text: str,
        quiz_type: str = "multiple_choice",
        difficulty: Optional[str] = None
    ) -> Dict:
        """퀴즈 생성"""
        
        # 텍스트 길이 체크
        if not text or len(text.strip()) < 50:
            logger.warning("텍스트가 너무 짧아 퀴즈 생성을 건너뜁니다.")
            return {}
        
        # 텍스트가 너무 긴 경우 제한
        if len(text) > 2000:
            text = text[:2000] + "..."
        
        difficulty_prompt = f" 난이도는 {difficulty}로 설정해주세요." if difficulty else ""
        
        # 퀴즈 타입별 프롬프트 생성
        if quiz_type == "multiple_choice":
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

        elif quiz_type == "true_false":
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

        elif quiz_type == "short_answer":
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

        elif quiz_type == "fill_in_blank":
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

        else:
            logger.error(f"지원하지 않는 퀴즈 타입: {quiz_type}")
            return {}
        
        try:
            response = await self.llm_client.generate(
                prompt,
                temperature=0.5,
                max_tokens=400
            )
            
            # JSON 파싱 시도
            try:
                quiz = json.loads(response.strip())
                
                # 퀴즈 타입별 필수 필드 검증
                if quiz_type == "multiple_choice":
                    required_fields = ["question", "options", "correct_option"]
                elif quiz_type == "true_false":
                    required_fields = ["question", "options", "correct_option"]
                elif quiz_type in ["short_answer", "fill_in_blank"]:
                    required_fields = ["question", "correct_answer"]
                else:
                    required_fields = ["question"]
                
                if all(field in quiz for field in required_fields):
                    # 기본값 설정
                    if "difficulty" not in quiz:
                        quiz["difficulty"] = difficulty or "medium"
                    if "explanation" not in quiz:
                        quiz["explanation"] = "설명이 제공되지 않았습니다."
                    
                    # 퀴즈 타입 추가
                    quiz["quiz_type"] = quiz_type
                    
                    logger.info(f"퀴즈 생성 성공 - 타입: {quiz_type}")
                    return quiz
                else:
                    logger.warning(f"필수 필드 누락: {required_fields}")
                    return {}
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.error(f"LLM 응답: {response}")
                return {}
            
        except Exception as e:
            logger.error(f"퀴즈 생성 실패: {e}")
            return {}

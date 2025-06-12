"""
JSON 파싱 유틸리티
LLM 응답에서 Markdown 코드블럭을 제거하여 안전한 JSON 파싱 제공
CREATED 2024-12-20: LLM JSON 응답 파싱 문제 해결
"""
import json
import re
from typing import Any, Dict, List, Union
from utils.logger import get_logger

logger = get_logger(__name__)

def clean_json_response(response: str) -> str:
    """
    LLM 응답에서 JSON 부분만 추출
    Markdown 코드블럭, 추가 텍스트 등을 제거
    """
    if not response:
        return response
    
    # 1. 기본 공백 제거
    response = response.strip()
    
    # 2. Markdown 코드블럭 제거 (```json ... ``` 또는 ``` ... ```)
    # 다양한 패턴 지원
    patterns = [
        r'```json\s*(.*?)\s*```',  # ```json ... ```
        r'```\s*(.*?)\s*```',      # ``` ... ```
        r'`(.*?)`',                # ` ... ` (단일 백틱)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            response = match.group(1).strip()
            logger.debug(f"코드블럭 제거 완료: {pattern}")
            break
    
    # 3. 추가적인 텍스트 제거 (JSON 객체/배열 앞뒤 텍스트)
    # JSON 객체 패턴 찾기
    json_object_match = re.search(r'(\{.*\})', response, re.DOTALL)
    if json_object_match:
        response = json_object_match.group(1)
        logger.debug("JSON 객체 추출 완료")
    else:
        # JSON 배열 패턴 찾기
        json_array_match = re.search(r'(\[.*\])', response, re.DOTALL)
        if json_array_match:
            response = json_array_match.group(1)
            logger.debug("JSON 배열 추출 완료")
    
    return response.strip()

def safe_json_loads(response: str, default: Any = None) -> Union[Dict, List, Any]:
    """
    안전한 JSON 파싱
    LLM 응답에서 코드블럭을 제거하고 JSON 파싱 시도
    
    Args:
        response: LLM 응답 문자열
        default: 파싱 실패 시 반환할 기본값
    
    Returns:
        파싱된 JSON 객체 또는 기본값
    """
    if not response:
        logger.warning("빈 응답으로 인한 JSON 파싱 실패")
        return default
    
    try:
        # 1차 시도: 원본 그대로
        return json.loads(response.strip())
    except json.JSONDecodeError:
        logger.debug("1차 JSON 파싱 실패, 코드블럭 제거 시도")
        
        try:
            # 2차 시도: 코드블럭 제거 후
            cleaned_response = clean_json_response(response)
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 최종 실패: {e}")
            logger.error(f"원본 응답: {response[:200]}...")
            logger.error(f"정제된 응답: {cleaned_response[:200] if 'cleaned_response' in locals() else '정제 실패'}")
            return default
        except Exception as e:
            logger.error(f"예상치 못한 파싱 오류: {e}")
            return default

def validate_quiz_json(quiz_data: Dict, quiz_type: str) -> bool:
    """
    퀴즈 JSON 데이터 유효성 검증
    
    Args:
        quiz_data: 검증할 퀴즈 데이터
        quiz_type: 퀴즈 타입 (multiple_choice, true_false, short_answer, fill_in_blank)
    
    Returns:
        유효성 검증 결과
    """
    if not isinstance(quiz_data, dict):
        return False
    
    # 공통 필수 필드
    if "question" not in quiz_data:
        logger.warning("퀴즈 질문이 없습니다")
        return False
    
    # 퀴즈 타입별 필수 필드 검증
    if quiz_type == "multiple_choice":
        required_fields = ["options", "correct_option"]
        if not all(field in quiz_data for field in required_fields):
            logger.warning(f"객관식 퀴즈 필수 필드 누락: {required_fields}")
            return False
        
        # 선택지와 정답 인덱스 검증
        options = quiz_data.get("options", [])
        correct_option = quiz_data.get("correct_option")
        
        if not isinstance(options, list) or len(options) < 2:
            logger.warning("선택지가 부족합니다 (최소 2개 필요)")
            return False
        
        if not isinstance(correct_option, int) or correct_option < 0 or correct_option >= len(options):
            logger.warning("정답 인덱스가 유효하지 않습니다")
            return False
    
    elif quiz_type == "true_false":
        required_fields = ["options", "correct_option"]
        if not all(field in quiz_data for field in required_fields):
            logger.warning(f"참/거짓 퀴즈 필수 필드 누락: {required_fields}")
            return False
    
    elif quiz_type in ["short_answer", "fill_in_blank"]:
        if "correct_answer" not in quiz_data:
            logger.warning("정답이 없습니다")
            return False
        
        if not quiz_data.get("correct_answer", "").strip():
            logger.warning("정답이 비어있습니다")
            return False
    
    return True 
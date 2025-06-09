"""
Response Coordinator
응답 조정 및 통합
"""
from typing import Dict, Any, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class ResponseCoordinator:
    """응답 조정자"""
    
    def __init__(self):
        pass
    
    async def coordinate_response(
        self,
        query: str,
        tool_results: List[Dict[str, Any]],
        agent_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """여러 도구 결과를 조정하여 통합 응답 생성"""
        try:
            # 기본 응답 구조
            coordinated_response = {
                "query": query,
                "primary_answer": "",
                "sources": [],
                "additional_info": {},
                "tool_results": tool_results,
                "confidence": 0.8
            }
            
            # 에이전트 결과가 있으면 우선 사용
            if agent_result and agent_result.get("status") == "success":
                coordinated_response["primary_answer"] = agent_result.get("answer", "")
                coordinated_response["sources"] = agent_result.get("sources", [])
                return coordinated_response
            
            # 도구 결과들을 통합
            primary_answers = []
            all_sources = []
            
            for tool_result in tool_results:
                if tool_result.get("status") == "success":
                    result_data = tool_result.get("result", "")
                    
                    # JSON 문자열인 경우 파싱
                    if isinstance(result_data, str):
                        try:
                            import json
                            parsed_result = json.loads(result_data)
                            
                            # 벡터 검색 결과 처리
                            if "documents" in parsed_result:
                                for doc in parsed_result["documents"][:3]:  # 상위 3개만
                                    primary_answers.append(doc.get("content", ""))
                                    all_sources.append({
                                        "source": doc.get("metadata", {}).get("source", ""),
                                        "content": doc.get("content", "")[:200] + "..."
                                    })
                            
                            # 요약 결과 처리
                            elif "summary" in parsed_result:
                                primary_answers.append(parsed_result["summary"])
                            
                            # 퀴즈 결과 처리
                            elif "quizzes" in parsed_result:
                                coordinated_response["additional_info"]["quizzes"] = parsed_result["quizzes"]
                            
                        except:
                            primary_answers.append(str(result_data)[:500])
                    else:
                        primary_answers.append(str(result_data)[:500])
            
            # 통합 답변 생성
            if primary_answers:
                coordinated_response["primary_answer"] = "\n\n".join(primary_answers[:2])  # 최대 2개 결합
            else:
                coordinated_response["primary_answer"] = "죄송합니다. 관련 정보를 찾을 수 없습니다."
                coordinated_response["confidence"] = 0.3
            
            coordinated_response["sources"] = all_sources[:5]  # 최대 5개 소스
            
            logger.info(f"응답 조정 완료: {len(tool_results)}개 도구 결과 통합")
            return coordinated_response
            
        except Exception as e:
            logger.error(f"응답 조정 실패: {e}")
            return {
                "query": query,
                "primary_answer": "응답 생성 중 오류가 발생했습니다.",
                "sources": [],
                "additional_info": {},
                "error": str(e),
                "confidence": 0.1
            }
    
    def format_final_response(self, coordinated_response: Dict[str, Any]) -> str:
        """최종 응답 포맷팅"""
        try:
            answer = coordinated_response.get("primary_answer", "")
            sources = coordinated_response.get("sources", [])
            
            formatted = answer
            
            # 소스 정보 추가
            if sources:
                formatted += "\n\n📚 **참고 자료:**\n"
                for i, source in enumerate(sources[:3], 1):
                    source_name = source.get("source", f"소스 {i}")
                    formatted += f"- {source_name}\n"
            
            # 추가 정보 (퀴즈 등)
            additional_info = coordinated_response.get("additional_info", {})
            if "quizzes" in additional_info:
                formatted += f"\n\n🧩 **관련 퀴즈 {len(additional_info['quizzes'])}개가 생성되었습니다.**"
            
            return formatted
            
        except Exception as e:
            logger.error(f"응답 포맷팅 실패: {e}")
            return coordinated_response.get("primary_answer", "응답 처리 중 오류가 발생했습니다.") 
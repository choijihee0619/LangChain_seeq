"""
자동 라벨링 모듈
문서 내용을 분석하여 태그, 카테고리, 키워드를 자동 생성
CREATED 2024-12-20: 문서 업로드 시 자동 라벨링 기능 추가
MODIFIED 2024-12-20: JSON 파싱 안정성 개선 - Markdown 코드블럭 처리 추가
"""
from typing import Dict, List
from ai_processing.llm_client import LLMClient
from utils.logger import get_logger
from utils.json_parser import safe_json_loads
import json
import re

logger = get_logger(__name__)

class AutoLabeler:
    """자동 라벨링 클래스"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        
        # 카테고리 정의
        self.categories = [
            "학술자료", "문학", "과학기술", "경제경영", "법률", "의학",
            "교육", "예술", "역사", "철학", "종교", "사회과학",
            "기술문서", "매뉴얼", "회의록", "보고서", "기타"
        ]
    
    async def analyze_document(self, text: str, filename: str = "") -> Dict:
        """문서 분석 및 라벨링"""
        try:
            # 텍스트가 너무 긴 경우 첫 2000자만 사용
            analysis_text = text[:2000] if len(text) > 2000 else text
            
            # 파일명에서 힌트 추출
            filename_hint = self._extract_filename_hints(filename)
            
            # LLM을 이용한 분석
            labels = await self._llm_analyze(analysis_text, filename_hint)
            
            # 기본 분석 결과와 합치기
            basic_labels = self._basic_analysis(analysis_text)
            
            # 결과 합치기
            final_labels = self._merge_labels(labels, basic_labels)
            
            logger.info(f"문서 라벨링 완료: {len(final_labels['tags'])}개 태그, 카테고리: {final_labels['category']}")
            
            return final_labels
            
        except Exception as e:
            logger.error(f"문서 라벨링 실패: {e}")
            # 실패 시 기본 라벨 반환
            return {
                "tags": ["문서"],
                "category": "기타",
                "keywords": [],
                "confidence_score": 0.1,
                "error": str(e)
            }
    
    def _extract_filename_hints(self, filename: str) -> List[str]:
        """파일명에서 힌트 추출"""
        hints = []
        
        if not filename:
            return hints
            
        # 확장자 제거
        name_without_ext = re.sub(r'\.[^.]+$', '', filename)
        
        # 특수문자를 공백으로 변경
        clean_name = re.sub(r'[_\-\.]', ' ', name_without_ext)
        
        # 한글, 영문 단어 추출
        words = re.findall(r'[가-힣a-zA-Z]+', clean_name)
        
        # 2글자 이상의 단어만 추가
        hints.extend([word for word in words if len(word) >= 2])
        
        return hints
    
    async def _llm_analyze(self, text: str, filename_hints: List[str]) -> Dict:
        """LLM을 이용한 고급 분석"""
        try:
            hint_text = f"파일명 힌트: {', '.join(filename_hints)}" if filename_hints else ""
            
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

태그는 3-5개 정도로, 키워드는 3-7개 정도로 제한해주세요.
confidence_score는 0.0-1.0 사이의 분석 신뢰도입니다."""

            response = await self.llm_client.generate(prompt, max_tokens=300)
            
            # 안전한 JSON 파싱 시도 (Markdown 코드블럭 제거)
            result = safe_json_loads(response, default={})
            
            if not result:
                logger.warning("LLM 응답에서 유효한 JSON을 찾을 수 없음")
                logger.error(f"LLM 응답: {response}")
                return self._fallback_analysis(text)
            
            # 결과 검증 및 정리
            return self._validate_llm_result(result)
                
        except Exception as e:
            logger.error(f"LLM 분석 실패: {e}")
            return self._fallback_analysis(text)
    
    def _basic_analysis(self, text: str) -> Dict:
        """기본 텍스트 분석"""
        basic_labels = {
            "tags": [],
            "category": "기타",
            "keywords": [],
            "confidence_score": 0.3
        }
        
        # 텍스트 길이별 분류
        if len(text) > 5000:
            basic_labels["tags"].append("장문")
        elif len(text) < 500:
            basic_labels["tags"].append("단문")
        
        # 숫자가 많으면 데이터/통계 관련
        number_count = len(re.findall(r'\d+', text))
        if number_count > 20:
            basic_labels["tags"].append("데이터")
            basic_labels["category"] = "보고서"
        
        # 자주 나오는 한국어 단어 추출
        korean_words = re.findall(r'[가-힣]{2,}', text)
        if korean_words:
            word_freq = {}
            for word in korean_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # 빈도순으로 정렬하여 상위 키워드 추출
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            basic_labels["keywords"] = [word for word, count in top_words if count > 1]
        
        return basic_labels
    
    def _validate_llm_result(self, result: Dict) -> Dict:
        """LLM 결과 검증 및 정리"""
        validated = {
            "tags": [],
            "category": "기타",
            "keywords": [],
            "confidence_score": 0.5
        }
        
        # 태그 검증
        if "tags" in result and isinstance(result["tags"], list):
            validated["tags"] = [str(tag)[:20] for tag in result["tags"][:5]]  # 최대 5개, 20자 제한
        
        # 카테고리 검증
        if "category" in result and result["category"] in self.categories:
            validated["category"] = result["category"]
        
        # 키워드 검증
        if "keywords" in result and isinstance(result["keywords"], list):
            validated["keywords"] = [str(kw)[:15] for kw in result["keywords"][:7]]  # 최대 7개, 15자 제한
        
        # 신뢰도 검증
        if "confidence_score" in result:
            try:
                score = float(result["confidence_score"])
                validated["confidence_score"] = max(0.0, min(1.0, score))
            except (ValueError, TypeError):
                pass
        
        return validated
    
    def _fallback_analysis(self, text: str) -> Dict:
        """LLM 실패 시 대안 분석"""
        fallback = {
            "tags": ["자동생성"],
            "category": "기타",
            "keywords": [],
            "confidence_score": 0.2
        }
        
        # 간단한 키워드 추출
        words = re.findall(r'[가-힣]{3,}', text[:1000])
        if words:
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            fallback["keywords"] = [word for word, count in top_words]
        
        return fallback
    
    def _merge_labels(self, llm_labels: Dict, basic_labels: Dict) -> Dict:
        """LLM 분석과 기본 분석 결과 합치기"""
        merged = {
            "tags": [],
            "category": llm_labels.get("category", basic_labels["category"]),
            "keywords": [],
            "confidence_score": max(llm_labels.get("confidence_score", 0), basic_labels["confidence_score"])
        }
        
        # 태그 합치기 (중복 제거)
        all_tags = llm_labels.get("tags", []) + basic_labels.get("tags", [])
        merged["tags"] = list(set(all_tags))[:5]  # 최대 5개
        
        # 키워드 합치기 (중복 제거)
        all_keywords = llm_labels.get("keywords", []) + basic_labels.get("keywords", [])
        merged["keywords"] = list(set(all_keywords))[:7]  # 최대 7개
        
        return merged

    async def extract_keywords(self, text: str, max_keywords: int = 10, focus_keyword: str = None) -> List[str]:
        """텍스트에서 키워드만 추출"""
        try:
            # 텍스트가 너무 긴 경우 첫 3000자만 사용
            analysis_text = text[:3000] if len(text) > 3000 else text
            
            logger.info(f"키워드 추출 시작 - 텍스트 길이: {len(analysis_text)}자, 최대 키워드: {max_keywords}개")
            
            # LLM을 이용한 키워드 추출
            llm_keywords = await self._llm_extract_keywords(analysis_text, max_keywords, focus_keyword)
            
            # 기본 분석으로 키워드 추출
            basic_keywords = self._extract_basic_keywords(analysis_text, max_keywords)
            
            # 두 결과를 합치고 중복 제거
            all_keywords = llm_keywords + basic_keywords
            unique_keywords = []
            seen = set()
            
            for keyword in all_keywords:
                if keyword not in seen and len(keyword) >= 2:
                    unique_keywords.append(keyword)
                    seen.add(keyword)
                    if len(unique_keywords) >= max_keywords:
                        break
            
            logger.info(f"키워드 추출 완료: {len(unique_keywords)}개 키워드")
            return unique_keywords
            
        except Exception as e:
            logger.error(f"키워드 추출 실패: {e}")
            # 실패 시 기본 키워드 추출만 사용
            return self._extract_basic_keywords(text, max_keywords)
    
    async def _llm_extract_keywords(self, text: str, max_keywords: int, focus_keyword: str = None) -> List[str]:
        """LLM을 이용한 키워드 추출"""
        try:
            # 디버깅: 입력 텍스트 확인
            logger.info(f"LLM에 전달되는 텍스트 (처음 200자): {text[:200]}...")
            
            if focus_keyword:
                prompt = f"""다음 텍스트에서 '{focus_keyword}'와 직접적으로 관련된 핵심 키워드 {max_keywords}개를 추출해주세요.
'{focus_keyword}' 자체는 제외하고, 이와 관련된 개념, 구성요소, 특징, 원인, 결과 등만 선택해주세요.

텍스트:
{text}

'{focus_keyword}'와 관련된 키워드만 {max_keywords}개, 쉼표로 구분하여 나열:"""
            else:
                prompt = f"""다음 텍스트에서 핵심 키워드 {max_keywords}개를 추출해주세요.
키워드는 명사나 핵심 개념 위주로 선택하고, 쉼표로 구분하여 나열해주세요.

텍스트:
{text}

키워드 (최대 {max_keywords}개, 쉼표로 구분):"""

            response = await self.llm_client.generate(prompt, max_tokens=150)
            
            # 디버깅: LLM 응답 로깅
            logger.info(f"LLM 키워드 추출 응답: {response}")
            
            # 응답에서 키워드 추출
            keywords = []
            if response:
                # 쉼표나 줄바꿈으로 분리
                raw_keywords = re.split(r'[,\n\r]+', response)
                
                logger.info(f"분리된 키워드들: {raw_keywords}")
                
                for keyword in raw_keywords:
                    # 정리: 앞뒤 공백 제거, 특수문자 제거
                    clean_keyword = re.sub(r'[^\w가-힣\s]', '', keyword.strip())
                    clean_keyword = clean_keyword.strip()
                    
                    # focus_keyword와 같은 키워드는 제외
                    if (clean_keyword and 
                        len(clean_keyword) >= 2 and 
                        len(clean_keyword) <= 20 and
                        (not focus_keyword or clean_keyword.lower() != focus_keyword.lower())):
                        keywords.append(clean_keyword)
                        
                        if len(keywords) >= max_keywords:
                            break
            
            logger.info(f"LLM 키워드 추출: {len(keywords)}개 - {keywords}")
            return keywords
            
        except Exception as e:
            logger.warning(f"LLM 키워드 추출 실패: {e}")
            return []
    
    def _extract_basic_keywords(self, text: str, max_keywords: int) -> List[str]:
        """기본 키워드 추출 (빈도 기반)"""
        try:
            # 한국어 단어 추출 (2글자 이상)
            korean_words = re.findall(r'[가-힣]{2,}', text)
            
            # 영어 단어 추출 (3글자 이상)
            english_words = re.findall(r'[a-zA-Z]{3,}', text)
            
            # 단어 빈도 계산
            word_freq = {}
            for word in korean_words + english_words:
                # 너무 긴 단어나 일반적인 단어 제외
                if len(word) <= 15 and word not in ['것이다', '하는', '있다', '없다', '그리고', '하지만']:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 빈도순으로 정렬
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            
            # 빈도가 2 이상인 단어들 중에서 상위 키워드 선택
            keywords = []
            for word, freq in sorted_words:
                if freq >= 2:  # 최소 2번 이상 나온 단어
                    keywords.append(word)
                    if len(keywords) >= max_keywords:
                        break
            
            logger.info(f"기본 키워드 추출: {len(keywords)}개")
            return keywords
            
        except Exception as e:
            logger.warning(f"기본 키워드 추출 실패: {e}")
            return [] 
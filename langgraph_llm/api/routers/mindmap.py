"""
마인드맵 API 라우터
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from database.connection import get_database
from ai_processing.auto_labeler import AutoLabeler
from ai_processing.llm_client import LLMClient
from retrieval.hybrid_search import HybridSearch
from utils.logger import get_logger
import json
import re

logger = get_logger(__name__)
router = APIRouter()

class MindmapRequest(BaseModel):
    """마인드맵 요청 모델"""
    root_keyword: str
    depth: int = 3
    max_nodes: int = 20
    folder_id: Optional[str] = None  # 특정 폴더의 문서만 대상으로 할 때

class MindmapNode(BaseModel):
    """마인드맵 노드 모델"""
    id: str
    label: str
    level: int
    children: List[str] = []

class MindmapEdge(BaseModel):
    """마인드맵 엣지 모델"""
    source: str
    target: str
    weight: float = 1.0

class MindmapResponse(BaseModel):
    """마인드맵 응답 모델"""
    nodes: List[MindmapNode]
    edges: List[MindmapEdge]
    root_id: str

@router.post("/", response_model=MindmapResponse)
async def generate_mindmap(request: MindmapRequest):
    """마인드맵 생성 엔드포인트"""
    try:
        db = await get_database()
        hybrid_search = HybridSearch(db)
        labeler = AutoLabeler()
        llm_client = LLMClient()
        
        # 1. 루트 키워드와 관련된 문서 검색
        search_results = await hybrid_search.search(
            query=request.root_keyword,
            k=min(10, request.max_nodes),
            folder_id=request.folder_id
        )
        
        # 2. 검색된 텍스트들에서 키워드 추출
        combined_text = ""
        relevant_text = ""
        
        for result in search_results[:5]:  # 상위 5개 결과만 사용
            chunk_text = result.get("chunk", {}).get("text", "")
            if chunk_text:
                combined_text += chunk_text + "\n\n"
                
                # 루트 키워드가 포함된 문장/문단만 추출
                # 여러 구분자로 분리 시도
                separators = ['\n\n', '\n', '.', '   ']  # 문단, 줄바꿈, 문장, 공백 구분
                
                for separator in separators:
                    segments = chunk_text.split(separator)
                    for segment in segments:
                        if request.root_keyword.lower() in segment.lower():
                            # 키워드가 포함된 세그먼트만 추가
                            clean_segment = segment.strip()
                            if clean_segment and clean_segment not in relevant_text:
                                relevant_text += clean_segment + ". "
                    
                    # 관련 텍스트를 찾았으면 더 세밀한 구분자는 시도하지 않음
                    if relevant_text.strip():
                        break
        
        logger.info(f"전체 텍스트: {len(combined_text)}자, 관련 텍스트: {len(relevant_text)}자")
        
        # 3. 키워드 추출 (문서가 있으면 문서 기반, 없으면 LLM 기반)
        if relevant_text.strip():
            logger.info(f"관련 텍스트 기반 마인드맵 생성: {len(relevant_text)}자")
            keywords = await labeler.extract_keywords(
                text=relevant_text,
                max_keywords=request.max_nodes - 1,  # 루트 제외
                focus_keyword=request.root_keyword
            )
        elif combined_text.strip() and request.root_keyword.lower() in combined_text.lower():
            logger.info(f"전체 텍스트 기반 마인드맵 생성: {len(combined_text)}자")
            keywords = await labeler.extract_keywords(
                text=combined_text,
                max_keywords=request.max_nodes - 1,  # 루트 제외
                focus_keyword=request.root_keyword
            )
        else:
            logger.info(f"LLM 기반 마인드맵 생성: {request.root_keyword}")
            
            # 먼저 fallback 키워드 확인
            fallback_keywords = _get_fallback_keywords(request.root_keyword)
            if fallback_keywords:
                logger.info(f"Fallback 키워드 사용: {fallback_keywords}")
                keywords = fallback_keywords[:request.max_nodes - 1]
            else:
                # fallback이 없으면 LLM 생성
                keywords = await _generate_llm_keywords(llm_client, request.root_keyword, request.max_nodes - 1)
                
                # LLM 키워드가 부족하면 기본 키워드 추가
                if len(keywords) < 3:
                    logger.info(f"LLM 키워드 부족 ({len(keywords)}개), 기본 키워드 추가")
                    additional_keywords = _get_fallback_keywords(request.root_keyword)
                    if additional_keywords:
                        keywords.extend(additional_keywords)
                        keywords = list(set(keywords))  # 중복 제거
                        keywords = keywords[:request.max_nodes - 1]  # 최대 개수 제한
        
        # 4. 마인드맵 구조 생성
        nodes = []
        edges = []
        
        # 루트 노드
        root_node = MindmapNode(
            id="root",
            label=request.root_keyword,
            level=0
        )
        nodes.append(root_node)
        
        # 5. 관련 키워드 노드들 추가
        for i, keyword in enumerate(keywords[:request.max_nodes-1]):
            if keyword.lower() == request.root_keyword.lower():
                continue  # 루트 키워드와 중복 제거
                
            node_id = f"node_{i}"
            
            # 노드 생성
            node = MindmapNode(
                id=node_id,
                label=keyword,
                level=1
            )
            nodes.append(node)
            
            # 엣지 생성 (루트와 연결) - 가중치 개선
            # 키워드 순서에 따라 1.0에서 0.2까지 선형적으로 감소
            weight = max(0.2, 1.0 - (i * 0.05))  # 음수 방지 및 최소값 보장
            edge = MindmapEdge(
                source="root",
                target=node_id,
                weight=weight
            )
            edges.append(edge)
        
        # 6. 2차 관계 생성 (depth > 1인 경우)
        if request.depth > 1 and len(keywords) > 3:
            if relevant_text.strip():
                await _add_secondary_connections(
                    nodes, edges, keywords, search_results, labeler, request.depth
                )
            else:
                await _add_llm_secondary_connections(
                    llm_client, nodes, edges, keywords, request.root_keyword, request.depth
                )
        
        logger.info(f"마인드맵 생성 완료: {len(nodes)}개 노드, {len(edges)}개 엣지")
        
        return MindmapResponse(
            nodes=nodes,
            edges=edges,
            root_id="root"
        )
        
    except Exception as e:
        logger.error(f"마인드맵 생성 실패: {e}")
        # 에러 발생 시 기본 마인드맵 반환
        return await _generate_enhanced_fallback_mindmap(request.root_keyword, request.max_nodes)

async def _generate_llm_keywords(llm_client: LLMClient, root_keyword: str, max_keywords: int) -> List[str]:
    """LLM을 이용한 키워드 생성"""
    try:
        prompt = f"""'{root_keyword}'에 대한 마인드맵을 만들기 위해 관련 키워드를 생성해주세요.

다음 지침을 따라주세요:
1. '{root_keyword}'와 직접적으로 관련된 개념만 선택
2. 하위 개념, 구성 요소, 관련 이론, 실제 사례 등을 포함
3. 각 키워드는 명확하고 구체적이어야 함
4. 일반적이거나 관련 없는 용어는 제외

예시 형식:
- 심리학 용어라면: 사회심리학, 집단역학, 동기이론 등
- 경제학 용어라면: 시장구조, 수요공급, 가격이론 등
- 과학 용어라면: 실험방법, 변인, 가설검증 등

'{root_keyword}'와 관련된 키워드 {max_keywords}개를 쉼표로 구분하여 나열해주세요:"""

        response = await llm_client.generate(prompt, max_tokens=200)
        
        # 응답에서 키워드 추출
        keywords = []
        if response:
            # 쉼표나 줄바꿈으로 분리
            raw_keywords = re.split(r'[,\n\r]+', response)
            
            for keyword in raw_keywords:
                # 정리: 앞뒤 공백 제거, 특수문자 제거
                clean_keyword = re.sub(r'[^\w가-힣\s]', '', keyword.strip())
                clean_keyword = clean_keyword.strip()
                
                # 키워드 품질 검증
                if (clean_keyword and 
                    len(clean_keyword) >= 2 and 
                    len(clean_keyword) <= 20 and
                    not clean_keyword.lower().startswith(('예', '등', '또는', '그리고'))):
                    keywords.append(clean_keyword)
                    
                    if len(keywords) >= max_keywords:
                        break
        
        # 키워드가 부족하면 기본 관련 용어 추가
        if len(keywords) < 3:
            fallback_keywords = _get_fallback_keywords(root_keyword)
            keywords.extend(fallback_keywords[:max_keywords - len(keywords)])
        
        logger.info(f"LLM 키워드 생성: {len(keywords)}개 - {keywords}")
        return keywords
        
    except Exception as e:
        logger.warning(f"LLM 키워드 생성 실패: {e}")
        return _get_fallback_keywords(root_keyword)

def _get_fallback_keywords(root_keyword: str) -> List[str]:
    """키워드별 기본 관련 개념들"""
    fallback_concepts = {
        # 심리학 관련
        "링겔만 효과": ["사회태만", "집단심리", "개인성과", "동기저하", "집단역학"],
        "사회심리학": ["집단행동", "사회인지", "태도변화", "편견", "동조"],
        "인지심리학": ["기억", "학습", "지각", "사고", "주의"],
        
        # 경제학 관련
        "시장경제": ["공급", "수요", "가격", "경쟁", "효율성"],
        "거시경제": ["GDP", "인플레이션", "실업률", "통화정책", "재정정책"],
        
        # 기술 관련
        "인공지능": ["머신러닝", "딥러닝", "자연어처리", "컴퓨터비전", "알고리즘"],
        "머신러닝": ["알고리즘", "훈련", "모델", "데이터", "예측"],
        "데이터베이스": ["테이블", "쿼리", "인덱스", "관계", "정규화"],
        "프로그래밍": ["변수", "함수", "조건문", "반복문", "객체지향"],
        
        # 과학 관련
        "물리학": ["역학", "열역학", "전자기학", "양자역학", "상대성이론"],
        "화학": ["원소", "분자", "반응", "주기율표", "화학결합"],
        
        # 경영 관련
        "경영전략": ["SWOT분석", "포터5힘", "가치사슬", "핵심역량", "블루오션"],
        "마케팅": ["4P", "STP", "브랜딩", "고객관리", "디지털마케팅"]
    }
    
    # 정확한 매칭 우선
    if root_keyword in fallback_concepts:
        return fallback_concepts[root_keyword]
    
    # 대소문자 무시 매칭
    for key, concepts in fallback_concepts.items():
        if key.lower() == root_keyword.lower():
            return concepts
    
    # 포함 관계 매칭 (더 엄격하게)
    for key, concepts in fallback_concepts.items():
        if (len(root_keyword) >= 3 and root_keyword in key) or (len(key) >= 3 and key in root_keyword):
            return concepts
    
    # 매칭되는 것이 없으면 빈 리스트 반환
    return []

async def _add_llm_secondary_connections(
    llm_client: LLMClient,
    nodes: List[MindmapNode], 
    edges: List[MindmapEdge], 
    keywords: List[str],
    root_keyword: str,
    depth: int
):
    """LLM을 이용한 2차 연결 관계 추가"""
    try:
        # 상위 키워드들 간의 관계 분석
        top_keywords = keywords[:5]
        
        prompt = f"""다음 키워드들이 '{root_keyword}'의 하위 개념으로 구성된 마인드맵에 있습니다.
키워드: {', '.join(top_keywords)}

이 키워드들 중에서 서로 직접적으로 연관이 있는 쌍을 찾아서 다음 형식으로 알려주세요:
키워드1-키워드2: 연관도(0.1-0.8)

예: 알고리즘-데이터구조: 0.7

최대 3개의 연관 쌍만 선택해주세요."""

        response = await llm_client.generate(prompt, max_tokens=150)
        
        if response:
            # 연관 관계 파싱
            connections = re.findall(r'([^-\n]+)-([^:]+):\s*([0-9.]+)', response)
            
            for keyword1, keyword2, weight_str in connections:
                keyword1 = keyword1.strip()
                keyword2 = keyword2.strip()
                
                try:
                    weight = float(weight_str)
                    weight = max(0.1, min(0.8, weight))  # 0.1-0.8 범위로 제한
                    
                    # 노드 ID 찾기
                    node1_id = None
                    node2_id = None
                    
                    for i, kw in enumerate(keywords):
                        if kw.lower().strip() == keyword1.lower():
                            node1_id = f"node_{i}"
                        elif kw.lower().strip() == keyword2.lower():
                            node2_id = f"node_{i}"
                    
                    if node1_id and node2_id:
                        edge = MindmapEdge(
                            source=node1_id,
                            target=node2_id,
                            weight=weight
                        )
                        edges.append(edge)
                        
                        logger.info(f"2차 연결 추가: {keyword1} - {keyword2} (가중치: {weight})")
                        
                except ValueError:
                    continue
                    
    except Exception as e:
        logger.warning(f"LLM 2차 연결 생성 실패: {e}")

async def _add_secondary_connections(
    nodes: List[MindmapNode], 
    edges: List[MindmapEdge], 
    keywords: List[str], 
    search_results: List[Dict],
    labeler: AutoLabeler,
    depth: int
):
    """2차 연결 관계 추가"""
    try:
        # 키워드 간 연관성 분석
        for i, keyword1 in enumerate(keywords[:5]):  # 상위 5개만
            for j, keyword2 in enumerate(keywords[:5]):
                if i >= j:  # 중복 방지
                    continue
                
                # 두 키워드가 함께 나타나는 텍스트 찾기
                co_occurrence_count = 0
                for result in search_results:
                    text = result.get("chunk", {}).get("text", "").lower()
                    if keyword1.lower() in text and keyword2.lower() in text:
                        co_occurrence_count += 1
                
                # 공출현이 2회 이상이면 연결
                if co_occurrence_count >= 2:
                    edge = MindmapEdge(
                        source=f"node_{i}",
                        target=f"node_{j}",
                        weight=min(0.8, co_occurrence_count * 0.2)
                    )
                    edges.append(edge)
                    
                    # 레벨 2 노드로 표시
                    for node in nodes:
                        if node.id == f"node_{j}":
                            node.level = 2
                            break
                    
    except Exception as e:
        logger.warning(f"2차 연결 생성 실패: {e}")

def _generate_fallback_mindmap(root_keyword: str) -> MindmapResponse:
    """기본 마인드맵 생성 (데이터가 없을 때)"""
    
    # 키워드별 기본 관련 개념들
    default_concepts = {
        "데이터베이스": ["테이블", "쿼리", "인덱스", "관계", "정규화"],
        "SQL": ["SELECT", "INSERT", "UPDATE", "DELETE", "JOIN"],
        "머신러닝": ["알고리즘", "훈련", "모델", "데이터", "예측"],
        "프로그래밍": ["변수", "함수", "조건문", "반복문", "객체"],
        "네트워크": ["프로토콜", "IP", "TCP", "HTTP", "라우터"]
    }
    
    # 기본 개념 선택
    concepts = default_concepts.get(
        root_keyword, 
        ["개념1", "개념2", "개념3", "개념4", "개념5"]
    )
    
    nodes = []
    edges = []
    
    # 루트 노드
    root_node = MindmapNode(
        id="root",
        label=root_keyword,
        level=0
    )
    nodes.append(root_node)
    
    # 관련 개념 노드들
    for i, concept in enumerate(concepts):
        node_id = f"node_{i}"
        
        node = MindmapNode(
            id=node_id,
            label=concept,
            level=1
        )
        nodes.append(node)
        
        edge = MindmapEdge(
            source="root",
            target=node_id,
            weight=1.0 - (i * 0.1)
        )
        edges.append(edge)
    
    return MindmapResponse(
        nodes=nodes,
        edges=edges,
        root_id="root"
    )

async def _generate_enhanced_fallback_mindmap(root_keyword: str, max_nodes: int) -> MindmapResponse:
    """향상된 기본 마인드맵 생성 (LLM 사용)"""
    try:
        llm_client = LLMClient()
        keywords = await _generate_llm_keywords(llm_client, root_keyword, max_nodes - 1)
        
        if not keywords:
            # LLM도 실패하면 기존 fallback 사용
            return _generate_fallback_mindmap(root_keyword)
        
        nodes = []
        edges = []
        
        # 루트 노드
        root_node = MindmapNode(
            id="root",
            label=root_keyword,
            level=0
        )
        nodes.append(root_node)
        
        # 관련 키워드 노드들
        for i, keyword in enumerate(keywords):
            node_id = f"node_{i}"
            
            node = MindmapNode(
                id=node_id,
                label=keyword,
                level=1
            )
            nodes.append(node)
            
            edge = MindmapEdge(
                source="root",
                target=node_id,
                weight=max(0.2, 1.0 - (i * 0.05))
            )
            edges.append(edge)
        
        return MindmapResponse(
            nodes=nodes,
            edges=edges,
            root_id="root"
        )
        
    except Exception as e:
        logger.error(f"향상된 fallback 마인드맵 생성 실패: {e}")
        return _generate_fallback_mindmap(root_keyword)

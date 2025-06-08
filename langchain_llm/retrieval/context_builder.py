"""
컨텍스트 빌더 모듈
검색 결과를 LLM용 컨텍스트로 변환
MODIFIED 2024-12-19: 청크 기반 검색 결과 처리로 업데이트
"""
from typing import List, Dict
from utils.logger import get_logger

logger = get_logger(__name__)

class ContextBuilder:
    """컨텍스트 빌더 클래스"""
    
    def build_context(
        self,
        search_results: List[Dict],
        max_tokens: int = 2000,
        include_metadata: bool = True
    ) -> str:
        """검색 결과를 컨텍스트로 변환 (청크 기반)"""
        context_parts = []
        current_tokens = 0
        
        for i, result in enumerate(search_results):
            chunk = result.get("chunk", {})
            document = result.get("document", {})
            score = result.get("score", 0.0)
            
            # 청크 텍스트
            chunk_text = chunk.get("text", "")
            if not chunk_text:
                continue
            
            # 문서 정보
            filename = document.get("original_filename", "알 수 없는 파일")
            file_type = document.get("file_type", "")
            sequence = chunk.get("sequence", 0)
            
            # 컨텍스트 포맷팅
            if include_metadata:
                chunk_context = f"""[문서 {i+1}] {filename} (청크 {sequence + 1}, 유사도: {score:.3f})
{chunk_text}
"""
            else:
                chunk_context = f"""[청크 {i+1}]
{chunk_text}
"""
            
            # 토큰 수 추정 (대략 4글자 = 1토큰)
            estimated_tokens = len(chunk_context) // 4
            
            if current_tokens + estimated_tokens > max_tokens:
                break
            
            context_parts.append(chunk_context)
            current_tokens += estimated_tokens
        
        return "\n".join(context_parts)
    
    def build_context_with_grouping(
        self,
        search_results: List[Dict],
        max_tokens: int = 2000,
        group_by_file: bool = True
    ) -> str:
        """파일별로 그룹화하여 컨텍스트 생성"""
        if not group_by_file:
            return self.build_context(search_results, max_tokens)
        
        # 파일별로 그룹화
        file_groups = {}
        for result in search_results:
            chunk = result.get("chunk", {})
            document = result.get("document", {})
            file_id = chunk.get("file_id", "unknown")
            
            if file_id not in file_groups:
                file_groups[file_id] = {
                    "document": document,
                    "chunks": []
                }
            
            file_groups[file_id]["chunks"].append(result)
        
        # 각 파일별로 컨텍스트 생성
        context_parts = []
        current_tokens = 0
        
        for file_id, group in file_groups.items():
            document = group["document"]
            chunks = group["chunks"]
            
            # 파일 헤더
            filename = document.get("original_filename", "알 수 없는 파일")
            file_header = f"\n=== {filename} ===\n"
            
            # 청크들을 시퀀스 순으로 정렬
            chunks.sort(key=lambda x: x.get("chunk", {}).get("sequence", 0))
            
            # 파일 내 청크들 결합
            file_context = file_header
            for j, result in enumerate(chunks):
                chunk = result.get("chunk", {})
                score = result.get("score", 0.0)
                sequence = chunk.get("sequence", 0)
                
                chunk_text = f"[청크 {sequence + 1}] (유사도: {score:.3f})\n{chunk.get('text', '')}\n"
                
                # 토큰 수 체크
                estimated_tokens = len(chunk_text) // 4
                if current_tokens + estimated_tokens > max_tokens:
                    break
                
                file_context += chunk_text
                current_tokens += estimated_tokens
            
            context_parts.append(file_context)
            
            if current_tokens >= max_tokens:
                break
        
        return "\n".join(context_parts)
    
    def build_qa_context(
        self,
        qa_pairs: List[Dict]
    ) -> str:
        """QA 쌍을 컨텍스트로 변환"""
        context_parts = []
        
        for qa in qa_pairs:
            qa_context = f"""Q: {qa['question']}
A: {qa['answer']}
"""
            context_parts.append(qa_context)
        
        return "\n".join(context_parts)
    
    def build_full_context(
        self,
        search_results: List[Dict],
        qa_pairs: List[Dict] = None,
        additional_info: Dict = None,
        group_by_file: bool = True
    ) -> str:
        """전체 컨텍스트 생성"""
        parts = []
        
        # 검색 결과 컨텍스트
        if search_results:
            parts.append("=== 관련 문서 ===")
            if group_by_file:
                parts.append(self.build_context_with_grouping(search_results))
            else:
                parts.append(self.build_context(search_results))
        
        # QA 컨텍스트
        if qa_pairs:
            parts.append("\n=== 관련 질의응답 ===")
            parts.append(self.build_qa_context(qa_pairs))
        
        # 추가 정보
        if additional_info:
            parts.append("\n=== 추가 정보 ===")
            for key, value in additional_info.items():
                parts.append(f"{key}: {value}")
        
        return "\n".join(parts)
    
    def get_context_summary(
        self,
        search_results: List[Dict]
    ) -> Dict:
        """컨텍스트 요약 정보 반환"""
        if not search_results:
            return {
                "total_chunks": 0,
                "unique_files": 0,
                "avg_score": 0.0,
                "file_list": []
            }
        
        # 통계 계산
        file_ids = set()
        scores = []
        file_info = {}
        
        for result in search_results:
            chunk = result.get("chunk", {})
            document = result.get("document", {})
            score = result.get("score", 0.0)
            
            file_id = chunk.get("file_id")
            if file_id:
                file_ids.add(file_id)
                if file_id not in file_info:
                    file_info[file_id] = {
                        "filename": document.get("original_filename", "알 수 없는 파일"),
                        "chunk_count": 0
                    }
                file_info[file_id]["chunk_count"] += 1
            
            scores.append(score)
        
        return {
            "total_chunks": len(search_results),
            "unique_files": len(file_ids),
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "file_list": [
                {
                    "file_id": fid,
                    "filename": info["filename"],
                    "chunk_count": info["chunk_count"]
                }
                for fid, info in file_info.items()
            ]
        }

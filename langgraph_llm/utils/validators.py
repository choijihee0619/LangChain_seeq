"""
검증 모듈
입력값 검증 유틸리티
"""
from typing import Any, Dict, Optional
import re

def validate_folder_name(name: str) -> bool:
    """폴더명 검증"""
    if not name or len(name) > 100:
        return False
    
    # 특수문자 제한
    pattern = r'^[가-힣a-zA-Z0-9\s_-]+$'
    return bool(re.match(pattern, name))

def validate_chunk_size(size: int) -> bool:
    """청크 크기 검증"""
    return 100 <= size <= 2000

def validate_top_k(k: int) -> bool:
    """검색 결과 수 검증"""
    return 1 <= k <= 20

def validate_difficulty(difficulty: str) -> bool:
    """난이도 검증"""
    return difficulty in ["easy", "medium", "hard"]

def validate_content_type(content_type: str) -> bool:
    """콘텐츠 타입 검증"""
    return content_type in ["book", "movie", "video", "youtube_video"]

def validate_file_extension(filename: str) -> bool:
    """파일 확장자 검증"""
    allowed_extensions = ['.pdf', '.txt', '.docx', '.html', '.htm']
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)

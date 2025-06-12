"""
전처리 모듈
텍스트 클린징 및 정규화
MODIFIED 2025-01-27: 줄바꿈 문자 보존을 위한 전처리 로직 개선
"""
import re
from typing import List
from utils.logger import get_logger

logger = get_logger(__name__)

class TextPreprocessor:
    """텍스트 전처리 클래스"""
    
    def __init__(self):
        # 제거할 패턴들 (정규표현식 수정)
        self.patterns = {
            'html_tags': re.compile(r'<[^>]+>'),
            'urls': re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'),
            'emails': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            'special_chars': re.compile(r'[^가-힣a-zA-Z0-9\s\.\,\!\?\(\)\[\]\-\:\;\"\'\/\\\n]'),  # 줄바꿈 포함
            'multiple_spaces': re.compile(r'[ \t]+'),  # 공백과 탭만 (줄바꿈 제외)
            'multiple_newlines': re.compile(r'\n{3,}'),  # 3개 이상 연속 줄바꿈만 정리
            'windows_line_endings': re.compile(r'\r\n'),  # Windows 줄바꿈 정규화
            'mac_line_endings': re.compile(r'\r')  # Mac 줄바꿈 정규화
        }
    
    def remove_html_tags(self, text: str) -> str:
        """HTML 태그 제거"""
        return self.patterns['html_tags'].sub('', text)
    
    def remove_urls(self, text: str) -> str:
        """URL 제거"""
        return self.patterns['urls'].sub('', text)
    
    def remove_emails(self, text: str) -> str:
        """이메일 주소 제거"""
        return self.patterns['emails'].sub('', text)
    
    def normalize_line_endings(self, text: str) -> str:
        """줄바꿈 문자 정규화 (Windows/Mac → Unix)"""
        # Windows CRLF → LF
        text = self.patterns['windows_line_endings'].sub('\n', text)
        # Mac CR → LF  
        text = self.patterns['mac_line_endings'].sub('\n', text)
        return text
    
    def normalize_whitespace(self, text: str) -> str:
        """공백 정규화 (줄바꿈 보존)"""
        # 연속된 공백/탭을 하나로 정리 (줄바꿈은 유지)
        text = self.patterns['multiple_spaces'].sub(' ', text)
        
        # 3개 이상 연속 줄바꿈을 2개로 정리 (문단 구분 유지)
        text = self.patterns['multiple_newlines'].sub('\n\n', text)
        
        return text.strip()
    
    def remove_special_characters(self, text: str) -> str:
        """특수문자 제거 (한글, 영문, 숫자, 기본 문장부호, 줄바꿈 유지)"""
        return self.patterns['special_chars'].sub(' ', text)
    
    def preserve_document_structure(self, text: str) -> str:
        """문서 구조 정보 보존"""
        # 빈 줄로 구분된 문단 구조 보존
        paragraphs = text.split('\n\n')
        cleaned_paragraphs = []
        
        for paragraph in paragraphs:
            # 각 문단 내 불필요한 공백 정리
            cleaned = paragraph.strip()
            if cleaned:  # 빈 문단 제거
                cleaned_paragraphs.append(cleaned)
        
        # 문단 사이에 빈 줄 하나씩 유지
        return '\n\n'.join(cleaned_paragraphs)
    
    async def preprocess(self, text: str) -> str:
        """전체 전처리 파이프라인 (줄바꿈 보존)"""
        logger.info(f"전처리 시작: {len(text)} 문자")
        
        # 1. 줄바꿈 문자 정규화
        text = self.normalize_line_endings(text)
        
        # 2. HTML 태그 제거
        text = self.remove_html_tags(text)
        
        # 3. URL 제거
        text = self.remove_urls(text)
        
        # 4. 이메일 제거
        text = self.remove_emails(text)
        
        # 5. 특수문자 제거 (줄바꿈 보존)
        text = self.remove_special_characters(text)
        
        # 6. 공백 정규화 (줄바꿈 보존)
        text = self.normalize_whitespace(text)
        
        # 7. 문서 구조 보존
        text = self.preserve_document_structure(text)
        
        logger.info(f"전처리 완료: {len(text)} 문자 (줄바꿈 보존)")
        
        # 디버깅: 첫 500자 출력 (줄바꿈 확인용)
        preview = text[:500].replace('\n', '\\n')
        logger.debug(f"전처리 결과 미리보기: {preview}")
        
        return text
    
    async def preprocess_minimal(self, text: str) -> str:
        """최소한의 전처리 (줄바꿈 최대 보존)"""
        logger.info(f"최소 전처리 시작: {len(text)} 문자")
        
        # 1. 줄바꿈 정규화만
        text = self.normalize_line_endings(text)
        
        # 2. 과도한 공백만 정리
        text = self.patterns['multiple_spaces'].sub(' ', text)
        
        # 3. 과도한 줄바꿈만 정리 (5개 이상 → 2개)
        text = re.sub(r'\n{5,}', '\n\n', text)
        
        logger.info(f"최소 전처리 완료: {len(text)} 문자")
        return text.strip()

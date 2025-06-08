"""
전처리 모듈
텍스트 클린징 및 정규화
"""
import re
from typing import List
from utils.logger import get_logger

logger = get_logger(__name__)

class TextPreprocessor:
    """텍스트 전처리 클래스"""
    
    def __init__(self):
        # 제거할 패턴들
        self.patterns = {
            'html_tags': re.compile(r'<[^>]+>'),
            'urls': re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'),
            'emails': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'),
            'special_chars': re.compile(r'[^가-힣a-zA-Z0-9\\s\\.\\,\\!\\?]'),
            'multiple_spaces': re.compile(r'\\s+'),
            'multiple_newlines': re.compile(r'\\n+')
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
    
    def normalize_whitespace(self, text: str) -> str:
        """공백 정규화"""
        text = self.patterns['multiple_spaces'].sub(' ', text)
        text = self.patterns['multiple_newlines'].sub('\\n', text)
        return text.strip()
    
    def remove_special_characters(self, text: str) -> str:
        """특수문자 제거 (한글, 영문, 숫자, 기본 문장부호만 유지)"""
        return self.patterns['special_chars'].sub(' ', text)
    
    async def preprocess(self, text: str) -> str:
        """전체 전처리 파이프라인"""
        # HTML 태그 제거
        text = self.remove_html_tags(text)
        
        # URL 제거
        text = self.remove_urls(text)
        
        # 이메일 제거
        text = self.remove_emails(text)
        
        # 특수문자 제거
        text = self.remove_special_characters(text)
        
        # 공백 정규화
        text = self.normalize_whitespace(text)
        
        logger.info(f"전처리 완료: {len(text)} 문자")
        return text

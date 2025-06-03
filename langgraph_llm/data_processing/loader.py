"""
문서 로더 모듈
다양한 포맷의 문서를 로드하는 기능
"""
from typing import List, Dict
from pathlib import Path
import pypdf
from docx import Document as DocxDocument
from bs4 import BeautifulSoup
from utils.logger import get_logger

logger = get_logger(__name__)

class DocumentLoader:
    """문서 로더 클래스"""
    
    @staticmethod
    async def load_pdf(file_path: Path) -> str:
        """PDF 파일 로드"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"PDF 로드 실패: {e}")
            raise
        return text
    
    @staticmethod
    async def load_docx(file_path: Path) -> str:
        """DOCX 파일 로드"""
        text = ""
        try:
            doc = DocxDocument(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"DOCX 로드 실패: {e}")
            raise
        return text
    
    @staticmethod
    async def load_txt(file_path: Path) -> str:
        """텍스트 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"TXT 로드 실패: {e}")
            raise
    
    @staticmethod
    async def load_html(file_path: Path) -> str:
        """HTML 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file.read(), 'html.parser')
                return soup.get_text()
        except Exception as e:
            logger.error(f"HTML 로드 실패: {e}")
            raise
    
    async def load_document(self, file_path: Path) -> Dict[str, str]:
        """파일 확장자에 따라 적절한 로더 선택"""
        ext = file_path.suffix.lower()
        
        if ext == '.pdf':
            text = await self.load_pdf(file_path)
        elif ext == '.docx':
            text = await self.load_docx(file_path)
        elif ext == '.txt':
            text = await self.load_txt(file_path)
        elif ext in ['.html', '.htm']:
            text = await self.load_html(file_path)
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {ext}")
        
        return {
            "text": text,
            "source": str(file_path),
            "file_type": ext[1:]
        }

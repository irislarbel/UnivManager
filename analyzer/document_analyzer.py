import fitz # PyMuPDF
import docx
import os
from config import DOWNLOAD_PATH

class DocumentAnalyzer:
    def extract_text_from_pdf(self, file_path):
        """PDF 파일에서 텍스트 추출"""
        if not os.path.exists(file_path):
            return ""

        print(f"Extracting text from PDF: {file_path}")
        text = ""
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    def extract_text_from_docx(self, file_path):
        """Word 파일에서 텍스트 추출"""
        if not os.path.exists(file_path):
            return ""

        print(f"Extracting text from DOCX: {file_path}")
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)

    def extract_text(self, file_path):
        """확장자에 따라 적절한 추출 방식 선택"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext == '.docx':
            return self.extract_text_from_docx(file_path)
        else:
            print(f"Unsupported file format: {ext}")
            return ""

if __name__ == "__main__":
    analyzer = DocumentAnalyzer()
    # test_text = analyzer.extract_text("sample.pdf")
    # print(test_text)

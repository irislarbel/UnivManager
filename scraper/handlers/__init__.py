from .base_handler import BaseHandler
from .assignment_handler import AssignmentHandler
from .exam_handler import ExamHandler
from .discussion_handler import DiscussionHandler
from .lti_handler import LtiHandler
from .folder_handler import FolderHandler
from .announcement_handler import AnnouncementHandler
from .default_handler import DefaultHandler

from .file_handler import FileHandler

def get_handler(item_type: str, href: str = "", title: str = "", aria_label: str = "") -> BaseHandler:
    item_type = item_type.lower() if item_type else ""
    href = href.lower() if href else ""
    title = title.lower() if title else ""
    aria_label = aria_label.lower() if aria_label else ""
    
    if "과제" in item_type or "assignment" in item_type:
        return AssignmentHandler()
    elif any(keyword in item_type for keyword in ["시험", "form", "quiz", "test", "assessment", "평가", "설문조사"]):
        return ExamHandler()
    elif "토론" in item_type or "discussion" in item_type:
        return DiscussionHandler()
    # LTI 도구, 외부 링크, 혹은 URL이 플레이스홀더(#)인 경우 LtiHandler로 유도 (클릭 시뮬레이션 필요)
    elif "lti" in item_type or "외부" in item_type or "콘텐츠" in item_type or href.endswith("#") or "javascript" in href:
        return LtiHandler()
    elif "폴더" in item_type or "folder" in item_type:
        return FolderHandler()
        
    # 다운로드 대상 파일 유형 검사
    file_types = ['pdf', 'hwp', 'hwpx', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip', 'rar', 'mp3', 'mp4']
    
    is_file = False
    if aria_label and ',' in aria_label:
        # aria-label 형태: "PDF, 아주인 1주차_오리엔테이션(X234).pdf"
        prefix = aria_label.split(',')[0].strip()
        if prefix in file_types:
            is_file = True
            
    if is_file:
        return FileHandler()
        
    return DefaultHandler()

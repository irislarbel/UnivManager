from .base_handler import BaseHandler
from .assignment_handler import AssignmentHandler
from .exam_handler import ExamHandler
from .discussion_handler import DiscussionHandler
from .lti_handler import LtiHandler
from .folder_handler import FolderHandler
from .announcement_handler import AnnouncementHandler
from .default_handler import DefaultHandler

def get_handler(item_type: str, href: str = "") -> BaseHandler:
    item_type = item_type.lower() if item_type else ""
    href = href.lower() if href else ""
    
    if "과제" in item_type or "assignment" in item_type:
        return AssignmentHandler()
    elif "시험" in item_type or "form" in item_type:
        return ExamHandler()
    elif "토론" in item_type or "discussion" in item_type:
        return DiscussionHandler()
    # LTI 도구, 외부 링크, 혹은 URL이 플레이스홀더(#)인 경우 LtiHandler로 유도 (클릭 시뮬레이션 필요)
    elif "lti" in item_type or "외부" in item_type or "콘텐츠" in item_type or href.endswith("#") or "javascript" in href:
        return LtiHandler()
    elif "폴더" in item_type or "folder" in item_type:
        return FolderHandler()
    else:
        return DefaultHandler()

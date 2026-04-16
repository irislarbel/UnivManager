from .base_handler import BaseHandler
from .assignment_handler import AssignmentHandler
from .exam_handler import ExamHandler
from .discussion_handler import DiscussionHandler
from .lti_handler import LtiHandler
from .folder_handler import FolderHandler
from .announcement_handler import AnnouncementHandler
from .default_handler import DefaultHandler

def get_handler(item_type: str) -> BaseHandler:
    item_type = item_type.lower() if item_type else ""
    if "과제" in item_type or "assignment" in item_type:
        return AssignmentHandler()
    elif "시험" in item_type or "form" in item_type:
        return ExamHandler()
    elif "토론" in item_type or "discussion" in item_type:
        return DiscussionHandler()
    elif "lti" in item_type:
        return LtiHandler()
    elif "폴더" in item_type or "folder" in item_type:
        return FolderHandler()
    else:
        return DefaultHandler()

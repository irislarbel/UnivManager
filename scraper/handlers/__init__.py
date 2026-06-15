from .base_handler import BaseHandler
from .assignment_handler import AssignmentHandler
from .exam_handler import ExamHandler
from .discussion_handler import DiscussionHandler
from .lti_handler import LtiHandler
from .folder_handler import FolderHandler
from .announcement_handler import AnnouncementHandler
from .default_handler import DefaultHandler

from .file_handler import FileHandler
from .audio_handler import AudioHandler

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
        
    # MP3 오디오 전담 핸들러 분기 (내장 뷰어 추출)
    elif "audio" in item_type or "오디오" in item_type or "mp3" in title or "mp3" in href or "mp3" in aria_label:
        return AudioHandler()
        
    # 다운로드 대상 파일 유형 검사
    file_types = ['pdf', 'hwp', 'hwpx', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip', 'rar', 'mp4']

    is_file = False

    # 1순위(가장 정확): 사이트가 제공하는 aria-label 형태 "PDF, 아주인 1주차_오리엔테이션(X234).pdf"
    if aria_label and ',' in aria_label:
        prefix = aria_label.split(',')[0].strip()
        if prefix in file_types:
            is_file = True

    # 2순위(폴백): aria-label이 비었거나 형식이 다른 경우, 제목/href가 알려진 파일 확장자로 끝나는지 검사.
    #   (Blackboard가 항상 aria-label을 주지는 않아, 확장자 기반으로 한 번 더 건집니다.)
    if not is_file:
        def _ends_with_known_ext(s):
            s = (s or "").split('?')[0].split('#')[0].strip()
            return any(s.endswith('.' + ext) for ext in file_types)

        if _ends_with_known_ext(title) or _ends_with_known_ext(href):
            is_file = True

    if is_file:
        return FileHandler()
        
    return DefaultHandler()

from .base_handler import BaseHandler

class DefaultHandler(BaseHandler):
    async def extract(self, detail_page, item: dict):
        full_path = item.get('fullPath', '')
        href = item.get('href', '#')
        
        # 문서, SCORM 영상 플레이어, 혹은 분류할 수 없는 항목들
        print(f"  📄 [기타 자료/문서]: {full_path} (URL: {href})")
        return {
            "type": "기타/문서",
            "title": item.get('title'),
            "href": href
        }

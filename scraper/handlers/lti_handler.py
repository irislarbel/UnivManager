from .base_handler import BaseHandler

class LtiHandler(BaseHandler):
    async def extract(self, detail_page, item: dict):
        full_path = item.get('fullPath', '')
        href = item.get('href', '#')
        
        # 외부/LTI 링크는 패널 열기 대신 외부 URL 링크로 기록만 함 (설정상 패널이 없거나 새 탭으로 열리는 경우가 많음)
        print(f"  🔗 [외부/LTI 링크]: {full_path} (URL: {href})")
        return {
            "type": "LTI/외부링크",
            "title": item.get('title'),
            "href": href
        }

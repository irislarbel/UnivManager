from .base_handler import BaseHandler

class DiscussionHandler(BaseHandler):
    async def extract(self, detail_page, item: dict):
        full_path = item.get('fullPath', '')
        s_id = item.get('scraperId', '')
        print(f"  🗣️ [토론 탐색]: {full_path}")
        
        opened = await self.open_panel_if_needed(detail_page, s_id)
        if not opened:
            return {"type": "토론", "title": item.get('title'), "error": "패널 진입 실패"}

        # 토론 전용 추출 로직 추후 구현
        print(f"    🏷️ [토론 제목]: {item['title']}")
        print(f"    (토론 내용은 아직 상세 추출 로직이 구현되지 않았습니다.)")
        
        await self.close_all_panels(detail_page)
        
        return {
            "type": "토론",
            "title": item.get('title'),
            "href": item.get('href'),
            "status": "not_implemented_yet"
        }

from .base_handler import BaseHandler

class FolderHandler(BaseHandler):
    async def extract(self, detail_page, item: dict):
        full_path = item.get('fullPath', '')
        # 폴더는 패널을 열 필요 없이 로깅만 남깁니다. 
        # (이미 스크래퍼 초반부에서 aria-expanded="false"를 이용해 모두 열어두었으므로 내부 진입은 재귀 리스트에서 알아서 처리됨)
        print(f"  📁 [폴더]: {full_path}")
        return {
            "type": "폴더",
            "title": item.get('title')
        }

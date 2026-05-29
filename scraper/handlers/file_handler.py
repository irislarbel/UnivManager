from .base_handler import BaseHandler

class FileHandler(BaseHandler):
    async def extract(self, detail_page, item: dict, save_dir: str = None):
        full_path = item.get('fullPath', '')
        href = item.get('href', '#')
        scraper_id = item.get('scraperId')
        item_title = item.get('title', '제목없음')
        
        print(f"  📄 [파일 다운로드]: {full_path}")
        
        # 물리적 파일 다운로드 시도
        downloaded_info = None
        download_status = "not_downloadable"
        
        if scraper_id and save_dir:
            download_result = await self.download_file(detail_page, scraper_id, save_dir)
            if download_result:
                download_status = download_result.get('status', 'not_downloadable')
                if download_status == "success":
                    downloaded_info = download_result
                    # 감지된 실제 다운로드 스트림 URL로 갱신
                    href = downloaded_info.get('url', href)
                
        return {
            "type": "파일",
            "title": item_title,
            "href": href,
            "downloaded_file": downloaded_info.get('filename') if downloaded_info else None,
            "download_status": download_status
        }

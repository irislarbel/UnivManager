from .base_handler import BaseHandler
import asyncio

class LtiHandler(BaseHandler):
    async def extract(self, detail_page, item: dict, save_dir: str = None):
        full_path = item.get('fullPath', '')
        scraper_id = item.get('scraperId')
        item_title = item.get('title', '제목없음')
        
        real_url = item.get('href', '#')
        
        if scraper_id:
            try:
                # 1. 요소 찾기
                target_selector = f'[data-scraper-id="{scraper_id}"]'
                element = await detail_page.query_selector(target_selector)
                
                if element:
                    print(f"    🖱️ [외부 링크 클릭 시도]: {item_title}")
                    
                    try:
                        # 새 탭이 열리는 경우와 패널이 열리는 경우를 동시에 감시하기 위해
                        # 새 페이지 이벤트를 먼저 등록한 뒤 클릭합니다.
                        async with detail_page.context.expect_page(timeout=5000) as page_info:
                            await element.click()
                            new_page = await page_info.value
                            
                        # 새 페이지가 열린 경우 (Case 1: XINICS 등)
                        if new_page:
                            await new_page.wait_for_load_state("domcontentloaded")
                            real_url = new_page.url
                            print(f"      ✨ 새 창 URL 감지: {real_url}")
                            await new_page.close()
                            
                    except Exception:
                        # 새 창이 열리지 않은 경우 (Timeout 등)
                        # Case 2: Peek 패널 등 내부에서 URL을 찾아야 합니다.
                        # 패널이나 iframe이 렌더링될 때까지 잠시 대기
                        await detail_page.wait_for_timeout(2000)
                        
                        # Peek 패널이나 내부 섹션에서 iframe 찾기
                        iframe_el = await detail_page.query_selector('div[class*="peekPanel"] iframe, .ultra-river-panel iframe, iframe[id*="lti"]')
                        if iframe_el:
                            real_url = await iframe_el.get_attribute('src')
                            if real_url:
                                print(f"      ✨ 패널 내 iframe URL 감지: {real_url}")
                        
                        # iframe이 없고 런처 버튼만 있는 경우
                        if not real_url or real_url == '#':
                            launch_btn = await detail_page.query_selector('button[id*="launch"], a[id*="launch"]')
                            if launch_btn:
                                real_url = await launch_btn.get_attribute('href')
                                if real_url:
                                    print(f"      ✨ 런처 버튼 URL 감지: {real_url}")

                        # 패널 닫기 (이후 다른 항목 탐색을 위해)
                        close_btn = await detail_page.query_selector('button[aria-label*="Close"], button[class*="close"]')
                        if close_btn:
                            await close_btn.click()
                            await detail_page.wait_for_timeout(500)
                
                else:
                    print(f"    ⚠️ 요소를 찾을 수 없어 기본 href를 사용합니다: {scraper_id}")
                    
            except Exception as e:
                print(f"    ❌ 세부 URL 추출 중 에러: {e}")

        print(f"  🔗 [외부/LTI 링크]: {full_path} (최종 URL: {real_url})")
        
        return {
            "type": "LTI/외부링크",
            "title": item_title,
            "href": real_url,
            "fullPath": full_path
        }

class BaseHandler:
    async def extract(self, detail_page, item: dict):
        """
        상속받은 클래스에서 구현해야 하는 메인 추출 로직입니다.
        detail_page: Playwright Page 객체
        item: 블랙보드 항목 딕셔너리 (title, href, fullPath, scraperId, itemType 등)
        """
        raise NotImplementedError("extract method must be implemented by subclasses.")

    async def open_panel_if_needed(self, detail_page, s_id: str):
        """
        현재 아이템의 노드를 클릭하여 사이드 패널을 엽니다.
        """
        try:
            node = detail_page.locator(f'[data-scraper-id="{s_id}"]')
            await node.scroll_into_view_if_needed()
            await node.click(force=True)
            await detail_page.wait_for_timeout(2500)
            return True
        except Exception as e:
            print(f"    ❌ 패널 진입 중 에러 발생: {e}")
            return False

    async def click_primary_action_buttons(self, detail_page):
        """
        '시작하기', '계속' 등의 동작 버튼을 클래스 기반으로 찾아 클릭합니다.
        """
        target_selector = "a.button-attempt, button.button-attempt, a[class*='button-attempt'], button[class*='button-attempt']"
        view_btns = await detail_page.query_selector_all(target_selector)
        
        for v_btn in view_btns:
            try:
                if await v_btn.is_visible() and not await v_btn.is_disabled():
                    await v_btn.click(force=True, timeout=3000)
                    await detail_page.wait_for_timeout(3500)
                    return True
            except:
                pass
        return False

    async def close_all_panels(self, detail_page):
        """
        열려있는 사이드 패널들을 안전하게 DOM에서 모두 삭제될 때까지 닫습니다.
        """
        for _ in range(4):
            close_icons = await detail_page.query_selector_all('button.bb-close, button[aria-label*="Close"], button[aria-label*="닫기"]')
            if close_icons:
                try:
                    await close_icons[-1].click(force=True)
                    await detail_page.wait_for_timeout(1000)
                except:
                    pass
            else:
                break
        
        # 패널이 DOM에서 모두 hidden 처리되었는지 확인 (다음 스크래핑 오염 방지)
        try:
            await detail_page.wait_for_selector('.bb-offcanvas-panel', state='hidden', timeout=3000)
        except:
            pass

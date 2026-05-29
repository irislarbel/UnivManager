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

    async def download_file(self, detail_page, s_id: str, save_dir: str):
        """
        아이템의 더보기 메뉴를 열고, 실제 원본 파일(.pdf, .ppt 등)을 물리적으로 로컬 디스크에 다운로드받아 보관합니다.
        """
        import os
        import re
        try:
            # 1. data-scraper-id를 기초로 하여 해당 행(Row 컨테이너) 내부의 더보기 버튼을 역추적해 찾습니다.
            row = detail_page.locator('li[role="listitem"], div[class*="outline-item"], div[class*="ListItem"]').filter(has=detail_page.locator(f'[data-scraper-id="{s_id}"]'))
            
            menu_btn = None
            if await row.count() > 0:
                menu_btn = row.first.locator('button[data-analytics-id*="overflowMenu.showMenu.button"], button[id^="content-item-overflow-menu-button-"], button[aria-label*="추가 옵션"], button[aria-label*="Options"]')
            
            if not menu_btn or await menu_btn.count() == 0:
                # Fallback: 전체 화면에서 data-analytics-id 기반으로 첫 번째 요소를 대기해 매칭해봅니다.
                menu_btn = detail_page.locator('button[data-analytics-id="components.directives.content-item-base.overflowMenu.showMenu.button"]').nth(0)
            
            if await menu_btn.count() > 0:
                print("    🖱️ [더보기 메뉴 클릭 시도]")
                await menu_btn.first.scroll_into_view_if_needed()
                await menu_btn.first.click(force=True)
                await detail_page.wait_for_timeout(800)
            else:
                print("    ⚠️ 더보기 메뉴 버튼을 탐색 영역 내에서 식별하지 못했습니다.")
                return {"status": "not_downloadable"}

            # 2. 팝업 메뉴가 열린 상태에서 제공해주신 data-analytics-id 다운로드 버튼을 100% 매칭해 다운로드 수신 감지를 시도합니다.
            download_selector = 'li[data-analytics-id="components.directives.content-item-base.overflowMenu.global.download.link"], li[role="menuitem"]:has-text("다운로드"), li[role="menuitem"]:has-text("Download")'
            
            try:
                # 파일 다운로드 비동기 감시 활성화
                async with detail_page.expect_download(timeout=5000) as download_info:
                    download_el = await detail_page.wait_for_selector(download_selector, timeout=3000, state="visible")
                    if download_el:
                        await download_el.click(force=True)
                        print("      💾 다운로드 버튼 클릭 완료. 파일 스트림을 획득 중입니다...")
                    else:
                        raise Exception("화면상에 활성화된 다운로드 메뉴 요소를 찾지 못했습니다.")
                
                # 3. 임시 바이너리 스트림을 본래 파일명 그대로 downloads 폴더 아래에 복사 저장합니다.
                download = await download_info.value
                suggested_filename = download.suggested_filename
                
                # 파일명 특수문자 치환
                clean_filename = re.sub(r'[\\/:*?"<>|]', '_', suggested_filename)
                final_filepath = os.path.join(save_dir, clean_filename)
                
                os.makedirs(save_dir, exist_ok=True)
                await download.save_as(final_filepath)
                print(f"      ✅ [물리 원본 다운로드 성공]: {clean_filename}")
                
                return {
                    "status": "success",
                    "filename": clean_filename,
                    "filepath": final_filepath,
                    "url": download.url
                }
            except Exception as inner_e:
                print(f"      ⚠️ 다운로드 실행 중 에러 발생: {inner_e}")
                # 예외 시 Escape로 오버플로우 팝업을 안전하게 정리
                await detail_page.keyboard.press("Escape")
                await detail_page.wait_for_timeout(500)
                return {"status": "failed"}
                
        except Exception as e:
            print(f"    ❌ 다운로드 헬퍼 시스템 구동 에러: {e}")
            return {"status": "failed"}

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

        overflow_selector = (
            'button[data-analytics-id*="overflowMenu.showMenu.button"], '
            'button[id^="content-item-overflow-menu-button-"], '
            'button[aria-label*="추가 옵션"], '
            'button[aria-label*="Options"]'
        )
        try:
            # 이전 파일에서 열어둔 더보기 메뉴가 DOM에 남아 있으면 다음 파일의 다운로드 링크 탐색을 오염시키므로,
            # 시작 시 Escape로 떠 있는 메뉴를 먼저 정리합니다. (1,1,1 재다운로드 방지)
            await detail_page.keyboard.press("Escape")
            await detail_page.wait_for_timeout(200)

            # 1. data-scraper-id를 기초로 하여 해당 항목 '한 줄(Row)'에 정확히 해당하는 컨테이너를 찾습니다.
            #    filter(has=...)는 해당 항목을 품은 '모든' 조상(리스트 전체 래퍼 포함)을 매칭하므로,
            #    여기에 '더보기 버튼도 함께 포함' 조건을 추가로 걸고 .last(문서 순서상 가장 안쪽=항목 자신의 행)를 취해
            #    리스트 전체가 아닌 바로 그 파일의 행으로 범위를 좁힙니다.
            #    (.first를 쓰면 가장 바깥 래퍼가 잡혀 항상 첫 번째 파일 버튼을 누르던 버그가 있었음)
            row = detail_page.locator(
                'li[role="listitem"], div[class*="outline-item"], div[class*="ListItem"]'
            ).filter(
                has=detail_page.locator(f'[data-scraper-id="{s_id}"]')
            ).filter(
                has=detail_page.locator(overflow_selector)
            )

            menu_btn = None
            if await row.count() > 0:
                menu_btn = row.last.locator(overflow_selector)

            if not menu_btn or await menu_btn.count() == 0:
                # 잘못된 파일을 받느니 이번 항목은 건너뜁니다. (전역 nth(0) 폴백은 항상 1번 파일을 받아 금지)
                print("    ⚠️ 이 항목의 더보기 메뉴 버튼을 행 범위 내에서 식별하지 못했습니다. (다음 스크랩 시 재시도)")
                return {"status": "not_downloadable"}

            print("    🖱️ [더보기 메뉴 클릭 시도]")
            await menu_btn.first.scroll_into_view_if_needed()
            await menu_btn.first.click(force=True)
            await detail_page.wait_for_timeout(800)

            # 2. 팝업 메뉴 안에 '다운로드' 항목이 실제로 존재하는지 먼저 확인합니다.
            download_selector = 'li[data-analytics-id="components.directives.content-item-base.overflowMenu.global.download.link"], li[role="menuitem"]:has-text("다운로드"), li[role="menuitem"]:has-text("Download")'

            download_el = None
            try:
                download_el = await detail_page.wait_for_selector(download_selector, timeout=3000, state="visible")
            except Exception:
                download_el = None

            if not download_el:
                # 더보기 메뉴는 열렸으나 '다운로드' 항목이 없음 = 애초에 내려받을 수 있는 파일이 아님.
                # 매 실행마다 무의미하게 재시도하지 않도록 영구적으로 '다운로드 불가'로 처리합니다.
                print("    ℹ️ 이 항목에는 다운로드 메뉴가 없어 파일이 아닌 것으로 판단합니다. (재시도 안 함)")
                await detail_page.keyboard.press("Escape")
                await detail_page.wait_for_timeout(300)
                return {"status": "not_downloadable"}

            try:
                # 다운로드 항목이 확인되었으므로, 클릭과 동시에 파일 스트림 수신을 감시합니다.
                async with detail_page.expect_download(timeout=15000) as download_info:
                    await download_el.click(force=True)
                    print("      💾 다운로드 버튼 클릭 완료. 파일 스트림을 획득 중입니다...")

                # 3. 임시 바이너리 스트림을 본래 파일명 그대로 downloads 폴더 아래에 복사 저장합니다.
                download = await download_info.value
                suggested_filename = download.suggested_filename
                
                # 파일명 특수문자 치환
                clean_filename = re.sub(r'[\\/:*?"<>|]', '_', suggested_filename)
                final_filepath = os.path.join(save_dir, clean_filename)
                
                os.makedirs(save_dir, exist_ok=True)
                await download.save_as(final_filepath)
                print(f"      ✅ [물리 원본 다운로드 성공]: {clean_filename}")

                # 성공 후에도 열린 메뉴를 닫아 다음 파일 처리 시 잔여 메뉴가 남지 않도록 정리합니다.
                await detail_page.keyboard.press("Escape")
                await detail_page.wait_for_timeout(300)

                return {
                    "status": "success",
                    "filename": clean_filename,
                    "filepath": final_filepath,
                    "url": download.url
                }
            except Exception as inner_e:
                # 다운로드 항목은 분명히 있었으나 전송이 실패/지연된 경우 = 일시적 오류이므로 다음 실행에 재시도합니다.
                print(f"      ⚠️ 다운로드 전송 실패(일시적 오류로 간주, 다음 스크랩 시 재시도): {inner_e}")
                await detail_page.keyboard.press("Escape")
                await detail_page.wait_for_timeout(500)
                return {"status": "failed"}
                
        except Exception as e:
            print(f"    ❌ 다운로드 헬퍼 시스템 구동 에러: {e}")
            return {"status": "failed"}

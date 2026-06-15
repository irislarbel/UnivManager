from .base_handler import BaseHandler

class AssignmentHandler(BaseHandler):
    async def extract(self, detail_page, item: dict, save_dir: str = None):
        full_path = item.get('fullPath', '')
        s_id = item.get('scraperId', '')
        print(f"  📝 [과제 탐색]: {full_path} (패널 내부 분석 중...)")
        
        opened = await self.open_panel_if_needed(detail_page, s_id)
        if not opened:
            return {"type": "과제", "title": item.get('title'), "error": "패널 진입 실패"}

        # 동작 버튼 클릭 (예: 시도 시작)
        await self.click_primary_action_buttons(detail_page)
        
        # 패널 내부 평가 내용 추출 공통 로직 (R-string으로 감싸 파이썬 이스케이프 오류 방지)
        panel_data = await detail_page.evaluate(r'''() => {
            // [버그 해결 핵심]: querySelector는 화면에 보이지 않는 이전 패널(닫혔으나 DOM에 남은 찌꺼기)을 계속 찾아냅니다.
            let potentialPanels = Array.from(document.querySelectorAll('.bb-offcanvas-panel.active:not(.hide-in-background), .panel-has-focus, [role="dialog"], aside, .offcanvas-inner, .peek-panel'));
            let activePanel = potentialPanels.reverse().find(p => p.getBoundingClientRect().width > 0 && window.getComputedStyle(p).display !== 'none');
            
            if (!activePanel) {
                return null;
            }
            
            const findValueNextToLabel = (labelText) => {
                const walker = document.createTreeWalker(activePanel, NodeFilter.SHOW_TEXT, null, false);
                let node;
                while (node = walker.nextNode()) {
                    let text = node.nodeValue.trim();
                    if (text === labelText) {
                        let el = node.parentElement;
                        if (el.nextElementSibling) {
                            let val = el.nextElementSibling.innerText.trim();
                            if (val) return val;
                        }
                        if (el.parentElement && el.parentElement.nextElementSibling) {
                            let val = el.parentElement.nextElementSibling.innerText.trim();
                            if (val) return val;
                        }
                        if (el.parentElement && el.parentElement.parentElement && el.parentElement.parentElement.nextElementSibling) {
                            let val = el.parentElement.parentElement.nextElementSibling.innerText.trim();
                            if (val) return val;
                        }
                    }
                }
                return "";
            };

            let deadline = findValueNextToLabel("기간") || findValueNextToLabel("평가 마감일") || findValueNextToLabel("Due Date") || findValueNextToLabel("마감일");
            
            const extractDate = (str) => {
                let match = str.match(/([0-9]{2,4}[./-]\s*[0-9]{1,2}[./-]\s*[0-9]{1,2}[^0-9]+[0-9]{1,2}:[0-9]{2}(?:\s*[apAP][mM])?(?:\s*\([^)]+\))?)/);
                if (match) {
                    return match[1].trim();
                }
                return str.replace(/[\r\n]+/g, ' ').trim();
            };

            if (deadline) {
                deadline = extractDate(deadline);
            } else {
                let ddNodes = activePanel.querySelectorAll('[id*="dueDate"], [class*="due-date"], .submission-details, [class*="date"]');
                for(let node of ddNodes) {
                    let t = node.innerText;
                    if(t.includes("마감") || t.includes("Due") || t.includes("기한") || /[0-9]{2}\/[0-9]{2}\/[0-9]{2}/.test(t)) {
                        deadline = extractDate(t);
                        break;
                    }
                }
            }
            
            let attempts = findValueNextToLabel("시도 횟수") || findValueNextToLabel("시도") || findValueNextToLabel("Attempts");
            if (!attempts && activePanel.innerText.includes("제한 없음")) attempts = "제한 없음";
            
            let maxScore = findValueNextToLabel("최고 점수") || findValueNextToLabel("Maximum points") || findValueNextToLabel("Maximum Score");

            let links = activePanel.querySelectorAll('a[href*="/file/"], a[href*="/bbcswebdav/"]');
            let files = Array.from(links).map(a => ({ title: a.innerText.trim() || a.getAttribute('aria-label') || "첨부파일", href: a.href }));
            
            let previewSpans = activePanel.querySelectorAll('div[aria-label*="파일 미리 보기"] span');
            for(let ps of previewSpans) {
                files.push({ title: ps.innerText.trim(), href: "" });
            }
            
            let uniqueFiles = [];
            let fileTitles = new Set();
            for(let f of files) {
                if (f.title && !fileTitles.has(f.title)) {
                    fileTitles.add(f.title);
                    uniqueFiles.push(f);
                }
            }
            
            let texts = [];
            let textBlocks = activePanel.querySelectorAll('#bb-editorassignment-attempt-authoring-instructions, .vtbegenerated, .prevent-copy-content, .js-description, [id*="description"], [class*="instruction"], .html-content, .document-components, bb-document-part, .content-viewer, .assessment-content, .rte-content, #assignment-attempt-authoring-instructions-summary + div p');
            textBlocks.forEach(tb => {
                let t = tb.innerText.trim().replace(/[\r\n]+/g, '\n');
                if (t && t.length > 5) {
                    if (texts.some(existing => existing.includes(t))) return;
                    texts = texts.filter(existing => !t.includes(existing));
                    texts.push(t);
                }
            });
            
            if (texts.length === 0) {
                activePanel.querySelectorAll('div.js-document-content p, div.document-content p, .bb-text-block, p').forEach(p => {
                    let t = p.innerText.trim().replace(/[\r\n]+/g, '\n');
                    if (t && t.length > 5) {
                        if (texts.some(existing => existing.includes(t))) return;
                        texts = texts.filter(existing => !t.includes(existing));
                        texts.push(t);
                    }
                });
            }
            return { 
                deadline: deadline, 
                attempts: attempts,
                maxScore: maxScore,
                instructions: texts, 
                files: uniqueFiles 
            };
        }''')
        
        panel_data = panel_data or {}
        panel_data['title'] = item.get('title')
        panel_data['type'] = item.get('itemType', '과제')
        panel_data['href'] = item.get('href', '')
        
        if 'files' not in panel_data:
            panel_data['files'] = []
            
        # [수정된 핵심 로직]: Playwright Python으로 첨부파일 더보기 버튼(Shadow DOM 통과)들을 찾고 직접 다운로드 수행
        if save_dir:
            import os
            import re
            try:
                option_btns = await detail_page.locator('.bb-offcanvas-panel.active button[data-analytics-id="fileViewer.action.menu"], .bb-offcanvas-panel.active button[aria-label*="에 대한 추가 옵션"]').all()
                for btn in option_btns:
                    try:
                        title_attr = await btn.get_attribute('title') or await btn.get_attribute('aria-label') or ""
                        filename = title_attr.replace('에 대한 추가 옵션', '').replace('Additional options for ', '').strip()
                        if not filename:
                            filename = "첨부파일"
                        
                        # JSON 목록에 아직 없다면 추가
                        existing_titles = [f.get('title') for f in panel_data['files']]
                        if filename not in existing_titles:
                            panel_data['files'].append({"title": filename, "href": "download_via_menu"})
                        
                        print(f"    🖱️ [{filename}] 더보기 메뉴 클릭 시도")
                        await btn.scroll_into_view_if_needed()
                        await btn.click(force=True)
                        await detail_page.wait_for_timeout(800)
                        
                        # 다운로드 버튼 클릭 (stale 메뉴 방지를 위해 visible 상태인 요소만 필터링)
                        download_selector = 'li[data-analytics-id="fileViewer.downloadFile"], li[role="menuitem"]:has-text("다운로드")'
                        all_download_els = await detail_page.locator(download_selector).all()
                        
                        download_el = None
                        for el in all_download_els:
                            if await el.is_visible():
                                download_el = el
                                break
                        
                        if download_el:
                            async with detail_page.expect_download(timeout=15000) as download_info:
                                await download_el.click(force=True)
                                print(f"      💾 [{filename}] 다운로드 버튼 클릭 완료. 파일 스트림 획득 중...")
                            
                            download = await download_info.value
                            clean_filename = re.sub(r'[\\/:*?"<>|]', '_', download.suggested_filename or filename)
                            final_filepath = os.path.join(save_dir, clean_filename)
                            
                            os.makedirs(save_dir, exist_ok=True)
                            await download.save_as(final_filepath)
                            print(f"      ✅ [물리 원본 다운로드 성공]: {clean_filename}")
                            
                            # 다운로드 성공 기록
                            for pf in panel_data['files']:
                                if pf['title'] == filename:
                                    pf['download_status'] = 'success'
                                    pf['filepath'] = final_filepath
                                    pf['href'] = download.url
                        else:
                            print(f"      ℹ️ [{filename}] 다운로드 메뉴가 없음.")
                        
                        # 메뉴 닫기 처리
                        await detail_page.keyboard.press("Escape")
                        await detail_page.wait_for_timeout(300)
                    except Exception as inner_e:
                        print(f"    ❌ [{filename}] 다운로드 중 에러: {inner_e}")
                        await detail_page.keyboard.press("Escape")
                        await detail_page.wait_for_timeout(300)
            except Exception as e:
                print(f"    ❌ 패널 내부 첨부파일 추출 중 에러: {e}")
        
        # 상세 결과 로깅
        print(f"    🏷️ [과제 제목]: {panel_data['title']}")
        if panel_data.get('deadline'): print(f"    🗓️ [과제 마감일]: {panel_data['deadline']}")
        if panel_data.get('attempts'): print(f"    🔄 [제출 횟수]: {panel_data['attempts']}")
        if panel_data.get('maxScore'): print(f"    💯 [과제 최고점수]: {panel_data['maxScore']}")
        
        if panel_data.get('instructions'):
            full_text = '\n'.join(panel_data['instructions'])
            formatted_text = full_text.replace('\n', '\n      ')
            print(f"    📝 [본문 내용 확보]:\n      {formatted_text}")
        else:
            print(f"    (본문 텍스트 없음)")

        if panel_data.get('files'):
            for p_file in panel_data['files']:
                print(f"    📎 [패널 첨부파일]: {p_file['title']}")

        # 추출 종료 후 패널 닫기
        await self.close_all_panels(detail_page)
        return panel_data

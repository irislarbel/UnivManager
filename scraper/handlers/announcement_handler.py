import asyncio
import re
from .base_handler import BaseHandler

class AnnouncementHandler(BaseHandler):
    async def extract(self, detail_page, skip_titles=None):
        print(f"  📢 [공지 사항 탐색 시작]")
        
        # 1. 상단바(Top Nav Bar) 공지 사항 탭으로 이동
        try:
            tab_selector = 'a.js-course-announcement-tool'
            ann_tab = await detail_page.wait_for_selector(tab_selector, timeout=5000)
            if ann_tab:
                await ann_tab.click()
                print("    🖱️ 상단 공지 사항 탭 클릭")
                await detail_page.wait_for_timeout(3000)
            else:
                print("    ⚠️ 상단 공지 사항 탭을 찾을 수 없습니다.")
                return []
        except Exception as e:
            print(f"    ⚠️ 상단바 경로 탐색 중 에러: {str(e)[:50]}")
            return []

        # 2. 공지 사항 목록 추출 및 상세 패널 탐색
        try:
            await detail_page.wait_for_selector('a.list-item-title, [class*="list-item-title"]', timeout=8000)
        except Exception:
            no_ann = await detail_page.query_selector('.no-announcements, [class*="no-data"]')
            if no_ann:
                print("    (공지 사항이 없습니다.)")
                return []
            print("    ⚠️ 공지 사항 리스트 로딩이 지연되었습니다.")

        title_elements = await detail_page.query_selector_all('a.list-item-title, [class*="list-item-title"]')
        
        if not title_elements:
            print(f"    (공지 사항 데이터가 검색되지 않았습니다.)")
            return []

        print(f"    총 {len(title_elements)}개의 공지 사항이 확인되었습니다. 상세 내용을 추출합니다.")

        final_data = []
        for i, title_el in enumerate(title_elements):
            try:
                # 1. 리스트 뷰에서 제목 및 날짜 추출
                title = await title_el.inner_text()
                title = title.strip()
                
                if skip_titles and title in skip_titles:
                    print(f"      ⏩ [스킵]: {title} (이미 처리됨)")
                    continue
                
                # 날짜 정보: 정규식 기반으로 텍스트 노드에서 직접 추출 (YY. M. D. 전용 대응 고도화)
                try:
                    row_handle = await detail_page.evaluate_handle('(el) => el.closest("li, [role=\'row\'], [class*=\'item\']") || el.parentElement', title_el)
                    row_text = await row_handle.inner_text()
                    # 연도(2~4자리), 월, 일 패턴 (예: 26. 4. 1. 또는 2024. 04. 01.)
                    date_match = re.search(r'(\d{2,4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.', row_text)
                    if date_match:
                        # 시:분 정보가 뒤에 더 있는지 확인
                        time_match = re.search(fr'{re.escape(date_match.group(0))}\s*(\d{{1,2}}:\d{{2}})', row_text)
                        date = f"{date_match.group(0)} {time_match.group(1)}" if time_match else date_match.group(0)
                    else:
                        date = ""
                except:
                    date = ""
                
                # 2. 공지 사항 클릭하여 상세 패널 열기
                await title_el.click()
                
                # 상세 패널이 나타날 때까지 대기
                panel_selector = '[data-automation-id="announcement-detail-view"], #announcement-detail-view, .side-panel-content'
                try:
                    await detail_page.wait_for_selector(panel_selector, timeout=5000)
                    await detail_page.wait_for_timeout(2000)
                except:
                    print(f"      ⚠️ [{title[:20]}...] 상세 패널이 열리지 않았습니다.")
                    continue
                
                # 3. 상세 패널에서 본문 및 첨부파일 추출
                content_data = await detail_page.evaluate(r'''async () => {
                    let panel = document.querySelector('[data-automation-id="announcement-detail-view"], #announcement-detail-view, .side-panel-content');
                    if (!panel) return { content: "(본문을 찾을 수 없음 - 패널 감지 실패)" };

                    // 본문 영역 타겟팅
                    let contentArea = panel.querySelector('.v-html-content-renderer, [data-automation-id="announcement-body"], .vtbegenerated, bb-message');
                    if (!contentArea) contentArea = panel.querySelector('.side-panel-content, .panel-content') || panel;

                    let clone = contentArea.cloneNode(true);
                    
                    // 불필요 요소 제거
                    let trash = clone.querySelectorAll('button, .bb-close, .metadata, .announcement-header, header, .nav-link');
                    trash.forEach(n => n.remove());

                    // 이미지 처리
                    clone.querySelectorAll('img').forEach(img => {
                        let src = img.getAttribute('src') || "";
                        if (src && !src.includes('avatar') && !src.startsWith('data:')) {
                            let placeholder = document.createTextNode(` [이미지 첨부: ${src}] `);
                            img.parentNode.replaceChild(placeholder, img);
                        } else {
                            img.remove();
                        }
                    });

                    // 링크 처리 (중복 방지 개선)
                    clone.querySelectorAll('a[href]').forEach(a => {
                        let href = a.getAttribute('href');
                        if (href && !href.startsWith('javascript:') && !href.startsWith('#')) {
                            let linkText = a.innerText.trim();
                            // 텍스트와 주소가 거의 같으면 (URL만 있는 경우 등) 하나만 출력
                            let cleanHref = href.replace(/\/$/, '').toLowerCase();
                            let cleanText = linkText.replace(/\/$/, '').toLowerCase();
                            
                            let outputText = (cleanText === cleanHref || cleanText.includes(cleanHref) || cleanHref.includes(cleanText)) 
                                ? ` [링크: ${href}] ` 
                                : ` [첨부/링크: ${linkText} (${href})] `;
                            let placeholder = document.createTextNode(outputText);
                            a.parentNode.replaceChild(placeholder, a);
                        }
                    });

                    let baseContent = clone.innerText.trim();

                    // 4. 숨겨진 첨부 파일(PDF 등) 탐색 강화
                    let attachments = [];
                    // 패널 전체에서 첨부 파일 관련 요소 전수 조사
                    panel.querySelectorAll('[data-automation-id*="attachment"], .attachment-item, li.file-item, div[data-bbtype="attachment"]').forEach(att => {
                        // 1. data-bbfile 파싱 시도 (가장 명확함)
                        if (att.hasAttribute('data-bbfile')) {
                            try {
                                let rawAttr = att.getAttribute('data-bbfile');
                                let bbfile = typeof rawAttr === 'string' ? JSON.parse(rawAttr) : rawAttr;
                                let name = bbfile.displayName || bbfile.fileName || bbfile.alternativeText;
                                let url = bbfile.resourceUrl;
                                if (name && url && !baseContent.includes(url)) {
                                    attachments.push(`[첨부파일: ${name} (${url})]`);
                                    return; // 파싱 성공시 다음 요소로
                                }
                            } catch(e) {}
                        }
                        
                        // 2. 기존 방식 구조 탐색
                        let nameEl = att.querySelector('.attachment-name, [class*="name"], span, a');
                        let linkEl = att.querySelector('a[href], [data-url], button[data-url]');
                        
                        if (nameEl) {
                            let name = nameEl.innerText.trim();
                            if (!name) name = nameEl.getAttribute('aria-label') || "";
                            
                            let url = "";
                            if (linkEl) {
                                url = linkEl.getAttribute('href') || linkEl.getAttribute('data-url') || "";
                            }
                            
                            // 파일 확장자가 포함된 경우 우선 채택
                            if (name && (name.includes('.') || url.includes('.')) && !baseContent.includes(url)) {
                                attachments.push(`[첨부파일: ${name} (${url || "주소 추출 불가"})]`);
                            }
                        }
                    });

                    if (attachments.length > 0) {
                        baseContent += "\n\n📎 첨부파일 목록:\n" + attachments.join("\n");
                    }

                    return { 
                        content: baseContent
                            .replace(/[ \t]+/g, ' ')
                            .replace(/\n\s*\n+/g, '\n\n')
                    };
                }''')
                
                print(f"      ✅ [{title[:30]}...] 완료")
                final_data.append({
                    "title": title,
                    "date": date,
                    "content": content_data.get('content', '')
                })
                
                # 4. 패널 닫기
                close_btn = await detail_page.query_selector('[data-automation-id="close-announcement-detail"], button.bb-close, button[aria-label*="Close"]');
                if (close_btn):
                    await close_btn.click()
                    await detail_page.wait_for_timeout(1000)
                else:
                    await detail_page.keyboard.press("Escape")
                    await detail_page.wait_for_timeout(1000)

            except Exception as e:
                print(f"      ❌ {i+1}번째 공지 추출 실패: {str(e)[:50]}")

        # 3. 다시 과목 콘텐츠(Outline) 탭으로 복귀
        try:
            outline_tab = await detail_page.wait_for_selector('a.js-course-outline-tool, [data-automation-id="course-outline-tab"]', timeout=3000)
            if outline_tab:
                await outline_tab.click()
                await detail_page.wait_for_timeout(2000)
        except Exception:
            pass

        return final_data

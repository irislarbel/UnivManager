from .base_handler import BaseHandler

class AssignmentHandler(BaseHandler):
    async def extract(self, detail_page, item: dict):
        full_path = item.get('fullPath', '')
        s_id = item.get('scraperId', '')
        print(f"  📝 [과제 탐색]: {full_path} (패널 내부 분석 중...)")
        
        opened = await self.open_panel_if_needed(detail_page, s_id)
        if not opened:
            return {"type": "과제", "title": item.get('title'), "error": "패널 진입 실패"}

        # 동작 버튼 클릭 (예: 시도 시작)
        await self.click_primary_action_buttons(detail_page)
        
        # 패널 내부 평가 내용 추출 공통 로직
        panel_data = await detail_page.evaluate('''() => {
            let activePanel = document.querySelector('.bb-offcanvas-panel.active:not(.hide-in-background), .panel-has-focus');
            if (!activePanel) {
                let potentialPanels = Array.from(document.querySelectorAll('.bb-offcanvas-panel.active, [role="dialog"], aside, .offcanvas-inner, .peek-panel'));
                activePanel = potentialPanels.reverse().find(p => p.offsetParent !== null);
            }
            if (!activePanel) {
                return null; // 배경 코스 수집 차단을 위해 활성 패널이 없으면 강제 취소
            }
            
            const findValueNextToLabel = (labelText) => {
                let spans = Array.from(activePanel.querySelectorAll('span'));
                for(let span of spans) {
                    if (span.innerText.trim() === labelText || span.innerText.includes(labelText)) {
                        let nextSib = span.nextElementSibling;
                        if (nextSib) return nextSib.innerText.trim();
                        if (span.parentElement && span.parentElement.nextElementSibling) {
                            return span.parentElement.nextElementSibling.innerText.trim();
                        }
                    }
                }
                let divs = Array.from(activePanel.querySelectorAll('div'));
                for(let div of divs) {
                    if ((div.innerText.trim() === labelText || div.innerText.includes(labelText)) && div.children.length === 0) {
                        let nextSib = div.nextElementSibling;
                        if (nextSib) return nextSib.innerText.trim();
                    }
                }
                return "";
            };

            let deadline = findValueNextToLabel("평가 마감일") || findValueNextToLabel("Due Date") || findValueNextToLabel("마감일");
            if (!deadline) {
                let ddNodes = activePanel.querySelectorAll('[id*="dueDate"], [class*="due-date"], .submission-details, [class*="date"]');
                for(let node of ddNodes) {
                    let t = node.innerText;
                    if(t.includes("마감") || t.includes("Due") || t.includes("기한") || /[0-9]{2}\\/[0-9]{2}\\/[0-9]{2}/.test(t)) {
                        deadline = t.trim().replace(/\\n/g, ' ');
                        break;
                    }
                }
            }
            
            let attempts = findValueNextToLabel("시도") || findValueNextToLabel("Attempts");
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
            let textBlocks = activePanel.querySelectorAll('.vtbegenerated, .prevent-copy-content, .js-description, [id*="description"], [class*="instruction"], .html-content, .document-components, bb-document-part, .content-viewer, .assessment-content, .rte-content, #assignment-attempt-authoring-instructions-summary + div p');
            textBlocks.forEach(tb => {
                let t = tb.innerText.trim();
                if (t && !texts.includes(t)) {
                    texts.push(t);
                }
            });
            if (texts.length === 0) {
                activePanel.querySelectorAll('div.js-document-content p, div.document-content p, .bb-text-block, p').forEach(p => {
                    let t = p.innerText.trim();
                    if (t && t.length > 5 && !texts.includes(t)) texts.push(t);
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
        
        # 상세 결과 로깅
        print(f"    🏷️ [과제 제목]: {panel_data['title']}")
        if panel_data.get('deadline'): print(f"    🗓️ [과제 마감일]: {panel_data['deadline']}")
        if panel_data.get('attempts'): print(f"    🔄 [제출 횟수]: {panel_data['attempts']}")
        if panel_data.get('maxScore'): print(f"    💯 [과제 최고점수]: {panel_data['maxScore']}")
        
        if panel_data.get('instructions'):
            preview_text = '\\n'.join(panel_data['instructions'])[:80].replace('\\n', ' ')
            print(f"    📝 [본문 내용 확보]: {preview_text} ...")
        else:
            print(f"    (본문 텍스트 없음)")

        if panel_data.get('files'):
            for p_file in panel_data['files']:
                print(f"    📎 [패널 첨부파일]: {p_file['title']}")

        # 추출 종료 후 패널 닫기
        await self.close_all_panels(detail_page)
        return panel_data

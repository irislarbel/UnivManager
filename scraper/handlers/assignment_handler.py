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
        
        # 패널 내부 평가 내용 추출 공통 로직 (R-string으로 감싸 파이썬 이스케이프 오류 방지)
        panel_data = await detail_page.evaluate(r'''() => {
            // [버그 해결 핵심]: querySelector는 화면에 보이지 않는 이전 패널(닫혔으나 DOM에 남은 찌꺼기)을 계속 찾아냅니다.
            // 모든 후보를 찾고 배열을 뒤집은 뒤(가장 마지막/최상위 팝업), 실제 화면 공간을 차지하는(getBoundingClientRect().width > 0) 요소만 활성 패널로 간주합니다.
            let potentialPanels = Array.from(document.querySelectorAll('.bb-offcanvas-panel.active:not(.hide-in-background), .panel-has-focus, [role="dialog"], aside, .offcanvas-inner, .peek-panel'));
            let activePanel = potentialPanels.reverse().find(p => p.getBoundingClientRect().width > 0 && window.getComputedStyle(p).display !== 'none');
            
            if (!activePanel) {
                return null; // 배경 코스 수집 차단을 위해 활성 패널이 없으면 강제 취소
            }
            
            const findValueNextToLabel = (labelText) => {
                // TreeWalker를 이용하여 DOM 트리의 모든 텍스트 노드를 순회하여 동적인 클래스명 변화에 구애받지 않음
                const walker = document.createTreeWalker(activePanel, NodeFilter.SHOW_TEXT, null, false);
                let node;
                while (node = walker.nextNode()) {
                    let text = node.nodeValue.trim();
                    if (text === labelText) {
                        let el = node.parentElement;
                        // 1. 텍스트를 감싸는 요소의 바로 다음 형제 (일반 구조)
                        if (el.nextElementSibling) {
                            let val = el.nextElementSibling.innerText.trim();
                            if (val) return val;
                        }
                        // 2. 부모 요소의 다음 형제 (MUI Grid, Box 등 레이아웃 분리 시 우회용)
                        if (el.parentElement && el.parentElement.nextElementSibling) {
                            let val = el.parentElement.nextElementSibling.innerText.trim();
                            if (val) return val;
                        }
                        // 3. 조부모 요소의 다음 형제 (깊게 트리 중첩된 경우)
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
                // "26. 3. 30. 23:59(UTC+9)" 또는 "10/24/25 11:59 PM" 형태의 날짜/시간 정규식 추출
                let match = str.match(/([0-9]{2,4}[./-]\s*[0-9]{1,2}[./-]\s*[0-9]{1,2}[^0-9]+[0-9]{1,2}:[0-9]{2}(?:\s*[apAP][mM])?(?:\s*\([^)]+\))?)/);
                if (match) {
                    return match[1].trim();
                }
                // 정규식 실패 시 기본적으로 줄바꿈만 없앰
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
                // UI 구조나 숨겨진 첨부파일 아이콘, 빈 div 때문에 \n이 수십 개씩 이어지는 것을 하나의 줄바꿈으로 압축
                let t = tb.innerText.trim().replace(/[\r\n]+/g, '\n');
                if (t && t.length > 5) {
                    // 1. 현재 텍스트(자식 노드)가 이미 저장된 기존 텍스트(부모 노드)에 완전히 포함되면 무시
                    if (texts.some(existing => existing.includes(t))) return;
                    
                    // 2. 반대로 현재 텍스트(부모 노드)가 이전에 파싱된 텍스트들을 모두 품고 있다면, 파편들을 버리고 본인으로 병합
                    texts = texts.filter(existing => !t.includes(existing));
                    
                    texts.push(t);
                }
            });
            
            // 만약 일치하는 요소가 아예 없었다면 최후의 보루(p태그 등) 탐색 시도
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
        
        # 상세 결과 로깅
        print(f"    🏷️ [과제 제목]: {panel_data['title']}")
        if panel_data.get('deadline'): print(f"    🗓️ [과제 마감일]: {panel_data['deadline']}")
        if panel_data.get('attempts'): print(f"    🔄 [제출 횟수]: {panel_data['attempts']}")
        if panel_data.get('maxScore'): print(f"    💯 [과제 최고점수]: {panel_data['maxScore']}")
        
        if panel_data.get('instructions'):
            full_text = '\n'.join(panel_data['instructions'])
            # 여러 줄의 본문이 콘솔에 이쁘게 출력되도록 내부 줄바꿈 앞에도 들여쓰기(공백 6칸)를 추가해주어 정렬합니다.
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

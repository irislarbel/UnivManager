from .base_handler import BaseHandler

class ExamHandler(BaseHandler):
    async def extract(self, detail_page, item: dict):
        full_path = item.get('fullPath', '')
        s_id = item.get('scraperId', '')
        print(f"  🚨 [시험/퀴즈 탐색 시작]: {full_path}")
        
        opened = await self.open_panel_if_needed(detail_page, s_id)
        if not opened:
            return {"type": "시험/퀴즈", "title": item.get('title'), "error": "패널 진입 실패"}

        # 시험지 열기 (동작 버튼 클릭)
        await self.click_primary_action_buttons(detail_page)
        
        # 패널 내부 시험 내용 추출 로직
        panel_data = await detail_page.evaluate(r'''() => {
            let potentialPanels = Array.from(document.querySelectorAll('.bb-offcanvas-panel.active:not(.hide-in-background), .panel-has-focus, [role="dialog"], aside, .offcanvas-inner, .peek-panel'));
            let activePanel = potentialPanels.reverse().find(p => p.getBoundingClientRect().width > 0 && window.getComputedStyle(p).display !== 'none');
            
            if (!activePanel) return null;
            
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
                    }
                }
                return "";
            };

            let deadline = findValueNextToLabel("마감일") || findValueNextToLabel("기간") || findValueNextToLabel("평가 마감일") || findValueNextToLabel("Due Date");
            const cleanDateString = (str) => {
                return str.replace(/(기한 초과|Late)/ig, '').replace(/(모든 새 시도는 늦은 것으로 표시됩니다|All new attempts will be marked late)\.?/ig, '').replace(/[\r\n]+/g, ' ').trim();
            };
            
            if (deadline) {
                let match = deadline.match(/([0-9]{2,4}[./-]\s*[0-9]{1,2}[./-]\s*[0-9]{1,2}[^0-9]+[0-9]{1,2}:[0-9]{2}(?:\s*[apAP][mM])?(?:\s*\([^)]+\))?)/);
                deadline = match ? match[1].trim() : cleanDateString(deadline);
            } else {
                let ddNodes = activePanel.querySelectorAll('[id*="dueDate"], [class*="due-date"], .submission-details, [class*="date"]');
                for(let node of ddNodes) {
                    let t = node.innerText;
                    if(t.includes("마감") || t.includes("Due") || t.includes("기한") || /[0-9]{2}\/[0-9]{2}\/[0-9]{2}/.test(t)) {
                        let match = t.match(/([0-9]{2,4}[./-]\s*[0-9]{1,2}[./-]\s*[0-9]{1,2}[^0-9]+[0-9]{1,2}:[0-9]{2}(?:\s*[apAP][mM])?(?:\s*\([^)]+\))?)/);
                        deadline = match ? match[1].trim() : cleanDateString(t);
                        break;
                    }
                }
            }
            
            let timeLimit = findValueNextToLabel("시간 제한") || findValueNextToLabel("제한 시간") || findValueNextToLabel("Time limit"); 
            let attempts = findValueNextToLabel("시도 횟수") || findValueNextToLabel("시도") || findValueNextToLabel("Attempts");
            let maxScore = findValueNextToLabel("최고 점수") || findValueNextToLabel("총점") || findValueNextToLabel("Maximum points") || findValueNextToLabel("Maximum Score");

            // --- 질문(Questions) 파싱 (bb-attempt-canvas 내부 조회) ---
            let questions = [];
            let instructions = []; // 본문/지문(Questions로 오인되는 텍스트) 분리
            let canvas = activePanel.querySelector('bb-attempt-canvas, [class*="assessment-canvas"]');
            
            if (canvas) {
                let rawQuestionBlocks = canvas.querySelectorAll('div[class*="assessment-question"], div.question, li, [role="listitem"], fieldset, bb-question');
                let questionBlocks = [];
                rawQuestionBlocks.forEach(qb => {
                    let isDescendant = questionBlocks.some(parent => parent.contains(qb));
                    if (!isDescendant) questionBlocks.push(qb);
                });
                
                let processedTexts = new Set();
                
                questionBlocks.forEach(qBlock => {
                    let qTextEl = qBlock.querySelector('.bb-editor-root p, .bb-editor-root, [class*="question-text"], legend');
                    if (!qTextEl) return; 
                    
                    let questionBody = qTextEl.innerText.trim();
                    if (!questionBody || processedTexts.has(questionBody)) return;
                    processedTexts.add(questionBody);
                    
                    // 문제 상단 헤더(문항 번호 및 배점 등 휴리스틱 탐색)
                    let headerText = "";
                    let pointEl = qBlock.querySelector('[class*="point"], [class*="badge"], .point-value');
                    if (pointEl && pointEl.innerText.match(/[0-9]/)) {
                        headerText = pointEl.innerText.replace(/[\r\n]+/g, ' ').trim();
                    } else {
                        let allText = qBlock.innerText.trim().split('\n');
                        for(let i=0; i<Math.min(3, allText.length); i++) {
                            let lower = allText[i].toLowerCase();
                            if ((lower.includes('점') || lower.includes('point') || lower.includes('문항')) && lower.match(/[0-9]/)) {
                                headerText += allText[i] + " ";
                            }
                        }
                    }
                    
                    let options = [];
                    let processedOptions = new Set();
                    
                    // 1. 라디오버튼/체크박스로 확실히 보기 탐색 (숨겨진 구조 파악)
                    let choiceInputs = qBlock.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                    choiceInputs.forEach(inp => {
                        let wrapper = inp.closest('label') || inp.parentElement;
                        if (!wrapper) return;
                        
                        let isSelected = inp.checked || wrapper.className.includes('selected') || wrapper.className.includes('checked');
                        let optVal = wrapper.innerText.trim().replace(/[\r\n]+/g, ' ');
                        
                        let optLabelNode = wrapper.querySelector('.option-label, .prefix');
                        let optTextNode = wrapper.querySelector('.bb-editor-root, .option-text');
                        if (optLabelNode && optTextNode) {
                             optVal = optLabelNode.innerText.trim() + " " + optTextNode.innerText.trim();
                        }
                        
                        if (optVal && optVal.length > 0 && optVal !== questionBody && !processedOptions.has(optVal)) {
                            processedOptions.add(optVal);
                            options.push(isSelected ? `✅ [선택됨] ${optVal}` : `🔳 [ ] ${optVal}`);
                        }
                    });
                    
                    // 2. 만약 input이 안 잡힌다면 범용적인 Fallback 탐색
                    if (options.length === 0) {
                        let fallbackNodes = qBlock.querySelectorAll('label, div[class*="option"], li[class*="option"]');
                        fallbackNodes.forEach(opt => {
                            if(opt.innerText.trim().length === 0) return;
                            
                            let optHtmlClass = (opt.className || "").toLowerCase();
                            // 확실히 answer이거나 option인 경우만 보기로 취급하여 오탐지 방지
                            if(!optHtmlClass.includes('option') && !optHtmlClass.includes('answer') && !optHtmlClass.includes('choice')) return;

                            let isSelected = optHtmlClass.includes('selected') || optHtmlClass.includes('checked');
                            let optVal = opt.innerText.trim().replace(/[\r\n]+/g, ' ');
                            
                            let optLabelNode = opt.querySelector('.option-label, .prefix');
                            let optTextNode = opt.querySelector('.bb-editor-root, .option-text');
                            if (optLabelNode && optTextNode) {
                                 optVal = optLabelNode.innerText.trim() + " " + optTextNode.innerText.trim();
                            }
                            
                            if (optVal && optVal.length > 0 && optVal !== questionBody && !processedOptions.has(optVal)) {
                                processedOptions.add(optVal);
                                options.push(isSelected ? `✅ [선택됨] ${optVal}` : `🔳 [ ] ${optVal}`);
                            }
                        });
                    }
                    
                    let isTextResponse = qBlock.querySelectorAll('textarea, input[type="text"]').length > 0;
                    if (options.length === 0 && isTextResponse) {
                        options.push("✍️ (서술/단답형 문항)");
                    }
                    
                    // 문항 판단 휴리스틱: 점수 표시가 없고, 옵션도 없고, 주관식 입력창도 없다면 이건 문제가 아니라 '공지사항/지문'임.
                    let isInstruction = options.length === 0 && !isTextResponse && !headerText.match(/[0-9]/);
                    
                    if (isInstruction) {
                        instructions.push(questionBody.replace(/[\r\n]+/g, '\n'));
                    } else {
                        questions.push({
                            header: headerText.trim(),
                            body: questionBody.replace(/[\r\n]+/g, '\n'),
                            options: options
                        });
                    }
                });
                
                // 만약 완전 파싱 실패했다면 텍스트를 묶어버림
                if (questions.length === 0 && instructions.length === 0) {
                    let tempText = [];
                    canvas.querySelectorAll('p, div.bb-editor-root').forEach(p => {
                        let pt = p.innerText.trim().replace(/[\r\n]+/g, '\n');
                        if (pt && pt.length > 5 && !tempText.includes(pt)) tempText.push(pt);
                    });
                    if (tempText.length > 0) instructions.push(tempText.join('\n\n'));
                }
            }
            
            return {
                deadline: deadline,
                timeLimit: timeLimit,
                attempts: attempts,
                maxScore: maxScore,
                instructions: instructions,
                questions: questions
            };
        }''')
        
        panel_data = panel_data or {}
        panel_data['title'] = item.get('title')
        panel_data['type'] = item.get('itemType', '시험/퀴즈')
        
        # 터미널 출력 및 확인
        print(f"    🏷️ [{panel_data['type']} 제목]: {panel_data['title']}")
        if panel_data.get('deadline'): print(f"    🗓️ [시험 마감일]: {panel_data['deadline']}")
        if panel_data.get('timeLimit'): print(f"    ⏱️ [제한 시간]: {panel_data['timeLimit']}")
        if panel_data.get('attempts'): print(f"    🔄 [제출 횟수]: {panel_data['attempts']}")
        if panel_data.get('maxScore'): print(f"    💯 [시험 총점]: {panel_data['maxScore']}")

        # 지문 영역 출력
        instructions = panel_data.get('instructions', [])
        if instructions:
            formatted_inst = '\n      '.join(instructions)
            print(f"    📖 [시험 지문/공지사항]:\n      {formatted_inst}")

        # 문제 영역 출력
        questions = panel_data.get('questions', [])
        if questions:
            print(f"    📝 [문제 추출 완료] (총 {len(questions)}문항 확인됨)")
            for i, q in enumerate(questions):
                header_str = f"({q['header']})" if q.get('header') else ""
                print(f"      Q{i+1}. {header_str} {q['body']}")
                for opt in q.get('options', []):
                    print(f"        - {opt}")
        else:
            print("    (문제 텍스트를 찾을 수 없거나 평가가 아직 열려있지 않습니다.)")

        # 패널 리소스를 모두 정리
        await self.close_all_panels(detail_page)
        return panel_data

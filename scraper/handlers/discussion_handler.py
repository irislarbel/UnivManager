from .base_handler import BaseHandler

class DiscussionHandler(BaseHandler):
    async def extract(self, detail_page, item: dict):
        full_path = item.get('fullPath', '')
        s_id = item.get('scraperId', '')
        print(f"  🗣️ [토론 탐색 시작]: {full_path}")
        
        opened = await self.open_panel_if_needed(detail_page, s_id)
        if not opened:
            return {"type": "토론", "title": item.get('title'), "error": "패널 진입 실패"}

        panel_data = await detail_page.evaluate(r'''async () => {
            let container = document.querySelector('#full-discussions');
            if (!container) return null;
            
            // 1. 끝단 로딩 (Infinite Scroll)
            let lastHeight = container.scrollHeight;
            let noChangeCount = 0;
            for(let i=0; i<50; i++) {
                container.scrollTo(0, container.scrollHeight);
                window.scrollBy(0, 500);
                await new Promise(r => setTimeout(r, 600));
                
                let newHeight = container.scrollHeight;
                if(newHeight === lastHeight) {
                    noChangeCount++;
                    if(noChangeCount >= 3) break;
                } else {
                    noChangeCount = 0;
                    lastHeight = newHeight;
                }
            }
            
            // 2. 답글 전개 (이미지 다운로드 메뉴 등의 부작용 제어를 위해 오직 특정 ID만 사용)
            let replyButtons = container.querySelectorAll('button[data-analytics-id="components.directives.discussion.commentControl.toggleReplies.button"]');
            let clickedAny = false;
            replyButtons.forEach(btn => {
                try {
                    btn.click();
                    clickedAny = true;
                } catch(e) {}
            });
            if (clickedAny) {
                await new Promise(r => setTimeout(r, 1200));
            }
            
            const getAuthorAndDate = (node) => {
                let name = "알 수 없음";
                let date = "";
                
                // 1. 이름 찾기
                // [가장 확실함]: bdi 태그는 보통 이름만 감싸고 있음
                let bdi = node.querySelector('.bb-ui-username bdi, bdi');
                if (bdi && bdi.innerText.trim()) {
                    name = bdi.innerText.trim();
                } else {
                    let authorEl = node.querySelector(`
                        .bb-ui-username, .usercard-trigger, .user-name, .name, 
                        [class*="author" i], [class*="username" i], h3, h4, 
                        .profile-handle, .display-name, [aria-label*="Author" i], [aria-label*="작성자" i]
                    `);
                    if (authorEl) {
                        name = authorEl.innerText.trim() || authorEl.getAttribute('aria-label') || authorEl.getAttribute('title') || "알 수 없음";
                    }
                }
                
                // [보조 문구 정제]: 하드코딩된 슬라이싱 대신 정규식으로 다국어 관용구 제거
                if (name && name !== "알 수 없음") {
                    name = name.replace(/^User card for\s+/i, '')
                               .replace(/\s*에 대한 사용자 카드$/, '')
                               .replace(/^작성자:\s*/, '')
                               .replace(/\s*에 대한 상세 정보$/, '')
                               .replace(/[.\s:]+$/, '') // 끝의 마침표/콜론 제거
                               .replace(/^[.\s:]+/, '') // 시작의 마침표/콜론 제거
                               .trim();
                }

                if (!name || name === "undefined") name = "알 수 없음";
                
                // 2. 날짜 찾기
                let dateEl = node.querySelector('.metadata, .date, .timestamp, [class*="date"], .time, .post-date, .v-timestamp');
                if (dateEl) {
                    let rawDate = dateEl.innerText.trim().replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ');
                    if(rawDate.length > 50) rawDate = "";
                    if(rawDate) date = rawDate;
                }
                
                // 3. 최종 이름 정제 (짧은 길이 검증 등)
                let finalName = name === "알 수 없음" ? "알 수 없음" : name.split('\n')[0].trim();
                if (finalName.length > 30) finalName = "알 수 없음";
                
                return { name: finalName, date: date };
            };
            
            // (1) 포럼 주제/안내문 (Instructor's Prompt)
            let opDict = { author: "", date: "", content: "" };
            let opContainer = container.querySelector('.entry.original.initial-post, .original-post, .discussion-topic-body, .discussion-comments > div:nth-child(2)');
            
            if (opContainer) {
                let meta = getAuthorAndDate(opContainer.parentElement || opContainer);
                opDict.author = meta.name;
                opDict.date = meta.date;
                
                // 실제 본문 텍스트가 담긴 요소만 타켓팅 (.ql-editor 가 주로 본문임)
                let contentEl = opContainer.querySelector('.vtbegenerated, .ql-editor, bb-message, .message, .content-area, .body-content');
                
                // [변경]: contentEl이 없을 때 opContainer로 무분별하게 넘어가지 않고,
                // 만약 contentEl이 없다면 opContainer 내부에서 메타데이터 요소를 제외한 순수 텍스트 영역만 찾거나, 없으면 빈 값 처리
                let targetArea = contentEl;
                if (!targetArea) {
                    // Fallback: opContainer를 그대로 쓰되, 아래에서 clone 후 메타데이터를 더 엄격하게 지움
                    targetArea = opContainer;
                }
                
                let clone = targetArea.cloneNode(true);
                
                let trashSelectors = [
                    '.metadata', '[class*="badge"]', '[class*="edited"]', '.new-post-text', '[class*="new"]',
                    'button', 'bb-user-role-badge', '[class*="role"]', '.profile-handle', '.user-info', '.post-date',
                    '.avatar', '.bb-close', '.reply-button', '.post-options', '.bb-ui-username'
                ];
                clone.querySelectorAll(trashSelectors.join(', ')).forEach(n => n.remove());
                
                clone.querySelectorAll('a[href]').forEach(a => {
                    let href = a.getAttribute('href');
                    if (href && !href.startsWith('javascript:') && !href.startsWith('#')) {
                        let linkText = a.innerText.trim() || "링크";
                        let placeholder = document.createTextNode(` [첨부/링크: ${linkText} (${href})] `);
                        a.parentNode.replaceChild(placeholder, a);
                    }
                });
                
                let imgIdx = 1;
                clone.querySelectorAll('img').forEach(img => {
                    let src = img.getAttribute('src') || "";
                    let className = img.className || "";
                    if (src.includes('avatar') || className.includes('avatar') || src.includes('profile') || src.startsWith('data:image')) {
                        img.remove();
                        return;
                    }
                    if (src) {
                        let placeholder = document.createTextNode(` [이미지 첨부 ${imgIdx}: ${src}] `);
                        img.parentNode.replaceChild(placeholder, img);
                        imgIdx++;
                    }
                });

                let contentText = clone.innerText.trim();
                
                // 날짜가 줄바꿈으로 끊어져 있을 것을 대비해 강력한 정규식 매치(Fallback Slice) 적용
                if (meta.date) {
                    let escapedDate = meta.date.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    let dateRgxStr = escapedDate.replace(/\s+/g, '\\s+');
                    let match = contentText.match(new RegExp(dateRgxStr));
                    
                    if (match && match.index < 50) {
                        let dateIdx = match.index;
                        let extractedName = contentText.substring(0, dateIdx).replace(/[.-]/g, '').trim();
                        if (extractedName && (!meta.name || meta.name === "알 수 없음")) {
                            meta.name = extractedName;
                        }
                        contentText = contentText.substring(dateIdx + match[0].length).trim();
                    }
                }
                
                contentText = contentText.replace(/[ \t]+/g, ' ');
                contentText = contentText.replace(/\n\s*\n+/g, '\n\n');
                
                // [강화]: 메타데이터(이름, 날짜)가 여전히 본문 영역의 앞부분에 포함되어 있다면 이를 제거합니다.
                // 시작점(^)에만 의존하지 않고, 초반부 텍스트에서 패턴 매칭을 시도합니다.
                if (meta.name && meta.name !== "알 수 없음") {
                    let escapedName = meta.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    // 이름 뒤에 줄바꿈이나 공백이 오는 경우까지 포함하여 제거
                    contentText = contentText.replace(new RegExp('^\\s*' + escapedName + '\\s*', 'i'), '').trim();
                }
                if (meta.date) {
                    // 날짜 내의 공백/줄바꿈을 유연하게 처리하는 정규식
                    let datePattern = meta.date.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s*');
                    // 본문 시작 부분 혹은 이름 제거 후 바로 다음에 날짜가 오는 경우 제거
                    contentText = contentText.replace(new RegExp('^\\s*' + datePattern + '\\s*', 'i'), '').trim();
                }
                
                // 만약 meta.date의 일부(날짜만 또는 시간만)가 여전히 남아있을 경우를 대비해 한 번 더 체크
                if (meta.date && meta.date.includes(' ')) {
                    let dateParts = meta.date.split(/\s+/);
                    dateParts.forEach(part => {
                        if (part.length > 3) {
                            let partPattern = part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                            contentText = contentText.replace(new RegExp('^\\s*' + partPattern + '\\s*', 'i'), '').trim();
                        }
                    });
                }
                
                contentText = contentText.replace(/^\(\.[^)]+함\)\s*/, '');
                contentText = contentText.replace(/^새 게시물\s*/, '');
                contentText = contentText.replace(/^NEW\s*/i, '').trim();
                
                // 만약 최종 결과가 meta 데이터와 완전히 같거나 너무 짧으면 본문 없음 처리
                if (contentText === meta.name || contentText === meta.date || contentText.length < 2) {
                    contentText = "";
                }
                
                opDict.author = meta.name;
                opDict.content = contentText;
            }
            
            // (2) 토론 본문 및 답글 (Student Responses & Replies)
            let comments = [];
            let allEntries = container.querySelectorAll('.entry, .discussion-post, bb-response, bb-reply');
            
            allEntries.forEach(cw => {
                let messageEl = cw.querySelector('.vtbegenerated, bb-message, .message-content, .content');
                if (!messageEl) return;
                
                let closestEntry = messageEl.closest('.entry, .discussion-post, bb-response, bb-reply');
                if (closestEntry !== cw) return;
                
                let isOP = cw.closest('.initial-post, .original-post, .discussion-topic-body') || (opContainer && cw === opContainer);
                if(isOP) return;
                
                let targetArea = messageEl ? messageEl : cw;
                let meta = getAuthorAndDate(cw);
                let clone = targetArea.cloneNode(true);
                
                let trashSelectors = [
                    '.metadata', '[class*="badge"]', '[class*="edited"]', '.new-post-text', '[class*="new"]',
                    'button', 'bb-user-role-badge', '[class*="role"]', '.profile-handle', '.user-info', '.post-date',
                    '.avatar', '.bb-close', '.reply-button', '.post-options', '.bb-ui-username'
                ];
                clone.querySelectorAll(trashSelectors.join(', ')).forEach(n => n.remove());
                
                clone.querySelectorAll('a[href]').forEach(a => {
                    let href = a.getAttribute('href');
                    if (href && !href.startsWith('javascript:') && !href.startsWith('#')) {
                        let linkText = a.innerText.trim() || "링크";
                        let placeholder = document.createTextNode(` [첨부/링크: ${linkText} (${href})] `);
                        a.parentNode.replaceChild(placeholder, a);
                    }
                });
                
                let imgIdx = 1;
                clone.querySelectorAll('img').forEach(img => {
                    let src = img.getAttribute('src') || "";
                    let className = img.className || "";
                    if (src.includes('avatar') || className.includes('avatar') || src.includes('profile') || src.startsWith('data:image')) {
                        img.remove();
                        return;
                    }
                    if (src) {
                        let placeholder = document.createTextNode(` [이미지 첨부 ${imgIdx}: ${src}] `);
                        img.parentNode.replaceChild(placeholder, img);
                        imgIdx++;
                    }
                });

                let contentText = clone.innerText.trim();
                
                // 날짜가 줄바꿈으로 끊어져 있을 것을 대비해 강력한 정규식 매치(Fallback Slice) 적용
                if (meta.date) {
                    let escapedDate = meta.date.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    let dateRgxStr = escapedDate.replace(/\s+/g, '\\s+');
                    let match = contentText.match(new RegExp(dateRgxStr));
                    
                    if (match && match.index < 50) {
                        let dateIdx = match.index;
                        let extractedName = contentText.substring(0, dateIdx).replace(/[.-]/g, '').trim();
                        if (extractedName && (!meta.name || meta.name === "알 수 없음")) {
                            meta.name = extractedName;
                        }
                        contentText = contentText.substring(dateIdx + match[0].length).trim();
                    }
                }
                
                contentText = contentText.replace(/[ \t]+/g, ' ');
                contentText = contentText.replace(/\n\s*\n+/g, '\n'); // 줄바꿈 최소화
                
                // [강화]: 메타데이터(이름, 날짜)가 여전히 본문 영역의 앞부분에 포함되어 있다면 이를 제거합니다.
                if (meta.name && meta.name !== "알 수 없음") {
                    // 이름 앞의 불필요한 마침표(.) 제거
                    meta.name = meta.name.replace(/^\.+/, '').trim();
                    let escapedName = meta.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    contentText = contentText.replace(new RegExp('^\\s*[.\\s]*' + escapedName + '\\s*', 'i'), '').trim();
                }
                if (meta.date) {
                    let datePattern = meta.date.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s*');
                    contentText = contentText.replace(new RegExp('^\\s*' + datePattern + '\\s*', 'i'), '').trim();
                }
                
                contentText = contentText.replace(/^\(\.[^)]+함\)\s*/, '');
                contentText = contentText.replace(/^새 게시물\s*/, '');
                contentText = contentText.replace(/^NEW\s*/i, '').trim();
                contentText = contentText.replace(/^\.+/, '').trim(); // 본문 시작의 마침표 제거
                
                if (contentText.length > 0) {
                    let parentEntry = cw.parentElement ? cw.parentElement.closest('.entry, .discussion-post, bb-response, bb-reply') : null;
                    let isReply = !!parentEntry;
                    
                    comments.push({
                        author: meta.name || "알 수 없음",
                        date: meta.date,
                        content: contentText,
                        isReply: !!isReply
                    });
                }
            });

            return {
                original_post: opDict,
                comments: comments
            };
        }''')
        
        panel_data = panel_data or {}
        panel_data['title'] = item['title']
        op = panel_data.get('original_post', {})
        cmts = panel_data.get('comments', [])
        
        print(f"    🏷️ [토론 주제]: {panel_data['title']}")
        if op.get('content'):
            author_str = op.get('author', '').strip()
            date_str = op.get('date', '').strip()
            
            if author_str and author_str != "알 수 없음":
                date_p = f" ({date_str})" if date_str else ""
                print(f"    ✍️ [작성자]: {author_str}{date_p}")
            elif date_str:
                print(f"    🗓️ [안내글 작성일]: {date_str}")
                
            print(f"    📖 [주제 본문]:\n      {op.get('content')}")
            
        if cmts:
            print(f"    💬 [참여자들의 글 모두 추출 완료] (총 {len(cmts)}개 확인됨)")
            for i, c in enumerate(cmts):
                prefix = "↳ (답글) " if c.get('isReply') else ""
                print(f"      {prefix}[{c['author']}] ({c['date']}): {c['content']}")
                if i >= 19 and len(cmts) > 20:
                    print(f"      ... (그 외 {len(cmts) - 20}개 토론/답글 생략)")
                    break
        else:
            print("    (작성된 토론 텍스트나 답글이 없습니다.)")

        await self.close_all_panels(detail_page)
        
        return panel_data

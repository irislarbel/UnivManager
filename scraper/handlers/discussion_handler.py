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
                let authorEl = node.querySelector('.bb-ui-username bdi, .bb-ui-username, .usercard-trigger, .user-name, .name, [class*="author"], h3, h4, bdi');
                let dateEl = node.querySelector('.metadata, .date, .timestamp, [class*="date"]');
                
                if (authorEl) name = authorEl.innerText.trim();
                
                if (dateEl) {
                    let rawDate = dateEl.innerText.trim().replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ');
                    if(rawDate.length > 50) rawDate = "";
                    if(rawDate) date = rawDate;
                }
                
                let finalName = name ? name.split('\n')[0].replace(/\s+\./g, '').trim() : "";
                
                return { name: finalName, date: date };
            };
            
            // (1) 포럼 주제/안내문 (Instructor's Prompt)
            let opDict = { author: "", date: "", content: "" };
            let opContainer = container.querySelector('.entry.original.initial-post, .original-post, .discussion-topic-body');
            
            if (opContainer) {
                let meta = getAuthorAndDate(opContainer.parentElement || opContainer);
                opDict.author = meta.name;
                opDict.date = meta.date;
                
                let contentEl = opContainer.querySelector('.vtbegenerated, .ql-editor, bb-message, .message');
                let targetArea = contentEl ? contentEl : opContainer;
                
                let clone = targetArea.cloneNode(true);
                
                let trashSelectors = [
                    '.metadata', '[class*="badge"]', '[class*="edited"]', '.new-post-text', '[class*="new"]',
                    'button', 'bb-user-role-badge', '[class*="role"]'
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
                
                contentText = contentText.replace(/^\(\.[^)]+함\)\s*/, '');
                contentText = contentText.replace(/^새 게시물\s*/, '');
                contentText = contentText.replace(/^NEW\s*/i, '').trim();
                
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
                
                let isOP = cw.closest('.initial-post, .original-post, .discussion-topic-body');
                if(isOP) return;
                
                let targetArea = messageEl ? messageEl : cw;
                let meta = getAuthorAndDate(cw);
                let clone = targetArea.cloneNode(true);
                
                let trashSelectors = [
                    '.metadata', '[class*="badge"]', '[class*="edited"]', '.new-post-text', '[class*="new"]',
                    'button', 'bb-user-role-badge', '[class*="role"]'
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
                
                contentText = contentText.replace(/^\(\.[^)]+함\)\s*/, '');
                contentText = contentText.replace(/^새 게시물\s*/, '');
                contentText = contentText.replace(/^NEW\s*/i, '').trim();
                
                if (contentText.length > 0) {
                    // 답글(대댓글)인지 확인: 자신을 감싸고 있는 윗선(부모)에 또 다른 '참여글(.entry, bb-response 등)'이 존재한다면, 이것은 무조건 누군가의 글에 달린 답글(대댓글)입니다.
                    // 애매한 래퍼 클래스 이름에 의존하지 않는 가장 완벽한 뎁스(Depth) 판단법입니다.
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

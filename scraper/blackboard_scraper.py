import json
import os
import sys
import asyncio

# 단독 파일 테스트 시를 위해 상위 폴더(루트 경로)를 sys.path에 추가합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright, TimeoutError
from playwright_stealth import Stealth
from config import BLACKBOARD_URL, BLACKBOARD_USER, BLACKBOARD_PASS, DATA_FILE, DOWNLOAD_PATH
from handlers import get_handler

class BlackboardScraper:
    def __init__(self):
        self.processed_items = self._load_processed_items()

    def _load_processed_items(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_processed_items(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.processed_items, f, ensure_ascii=False, indent=4)

    async def login(self, page):
        """환경변수의 계정 정보로 자동 로그인을 수행합니다 (SSO 지원)."""
        print(f"Connecting to {BLACKBOARD_URL}...")

        try:
            # 1. Blackboard 접속 (보통 여기서 SSO 페이지로 리다이렉트 됨)
            await page.goto(BLACKBOARD_URL)
            await page.wait_for_load_state("networkidle") # 초기 로딩 대기

            print("SSO 로그인 페이지 도착. 정보 입력 시도...")

            # -------------------------------------------------------------
            # [SSO 구조에 맞춘 입력 템플릿]
            # 사용자님 학교의 SSO 구조에 맞춰 아래 선택자(Selector)를 수정하세요.
            # -------------------------------------------------------------

            # 예시: SSO 로그인 창의 아이디, 비밀번호 입력
            await page.fill("#userId", BLACKBOARD_USER)
            await page.fill("#password", BLACKBOARD_PASS)

            # 예시: 로그인 버튼 클릭 (클릭과 동시에 리다이렉트 시작됨)
            await page.click("#loginSubmit")

            # -------------------------------------------------------------
            # [가장 중요한 부분: SSO 리다이렉트 후 최종 도착 대기]
            # 클릭 후 여러 번 화면이 바뀌다가, '최종 Blackboard 화면'에만 존재하는
            # 특정 요소를 하나 찾아서 그것이 나타날 때까지 대기해야 합니다.
            # -------------------------------------------------------------
            print("로그인 버튼 클릭. 최종 대시보드 진입 대기 중...")

            # 예시: Blackboard 메인 화면에 있는 '과목' 탭이나 사용자 프로필의 ID
            await page.wait_for_selector("#courses-overview-filter-search", timeout=30000) # 30초 한도

            print("로그인 완료 요소 감지됨! (현재는 템플릿 상태이므로 실제 선택자 적용 필요)")
            return True

        except TimeoutError:
            print("Login timeout. SSO 화면 구조가 다르거나 인증이 지연되었습니다.")
            return False
        except Exception as e:
            print(f"Login failed: {e}")
            return False


    async def run(self):
        async with async_playwright() as p:
            # ✅ 윈도우 개발 시 디버깅을 원하시면 headless=False 로 변경하세요!
            # 리눅스 서버에 올릴 때는 반드시 headless=True 여야 합니다.
            browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
            context = await browser.new_context()
            page = await context.new_page()

            # 봇 탐지 회피 (playwright-stealth)
            await Stealth().apply_stealth_async(page)

            # 자동 로그인 실행
            login_success = await self.login(page)
            
            if login_success:
                print("Login process finished. Proceeding to crawl courses...")
                
                # 강제 대기(네트워크 안정화)를 한 뒤 과목 탭으로 강제 이동합니다.
                await page.wait_for_timeout(3000)
                await page.goto("https://eclass2.ajou.ac.kr/ultra/course")
                
                try:
                    # 코스 카드의 뼈대(Skeleton)가 먼저 나타나므로, 데이터 바인딩이 끝난 요소(_ 가 포함된 고유ID)가 뜰 때까지 대기
                    await page.wait_for_selector("article[id*='course-list-course-_']", timeout=15000)
                    
                    print("코스 목록 페이지 접속 확인. 모든 과목을 불러오기 위해 화면을 스크롤합니다...")
                    # [과목 목록 전체 스크롤]
                    last_c_height = 0
                    for _ in range(10):
                        await page.mouse.wheel(0, 5000)
                        await page.wait_for_timeout(1000)
                        
                        # Load more 버튼이 있으면 클릭
                        load_more_btn = await page.query_selector('button:has-text("Load")')
                        if load_more_btn:
                            try:
                                await load_more_btn.click()
                                await page.wait_for_timeout(1500)
                            except:
                                pass
                                
                        new_c_height = await page.evaluate("document.body.scrollHeight")
                        if new_c_height == last_c_height:
                            break
                        last_c_height = new_c_height
                        
                    await page.wait_for_timeout(2000) # 바인딩 안정화 추가 대기
                    
                    # 뼈대(Skeleton) 요소를 제외하기 위해 ID에 밑줄(_)이 있는 실제 바인딩 된 태그만 선택
                    course_cards = await page.query_selector_all("article.course-element-card[id*='course-list-course-_']")
                    print(f"총 {len(course_cards)}개의 강의를 완전히 불러왔습니다.")
                    
                    # 페이지(SPA) 클릭 후 뒤로가기의 불안정성을 피하기 위해 과목 ID와 제목을 먼저 일괄 수집
                    course_info_list = []
                    for card in course_cards:
                        title_el = await card.query_selector("a.course-title h4")
                        if title_el:
                            course_title = (await title_el.inner_text()).strip()
                            card_id = await card.get_attribute("id")
                            if card_id and "course-list-course-_" in card_id:
                                internal_id = card_id.replace("course-list-course-", "")
                                if internal_id:  # 방어적 코드
                                    course_info_list.append((internal_id, course_title))

                    print("과목 정보를 전부 추출했습니다. 내부 탐색을 시작합니다.")

                    # 수집한 각 과목별로 새 탭을 열고 outline 페이지에 접속합니다.
                    for internal_id, course_title in course_info_list:
                        print(f"\n=============================================")
                        print(f"[과목 탐색] {course_title}")
                        
                        if course_title not in self.processed_items:
                            self.processed_items[course_title] = {}
                        
                        detail_url = f"https://eclass2.ajou.ac.kr/ultra/courses/{internal_id}/outline"
                        detail_page = await context.new_page()
                        
                        try:
                            await detail_page.goto(detail_url)
                            await detail_page.wait_for_timeout(3000) # 초기 로딩 확보
                            
                            # [팝업 제거] 공지사항 등 화면을 가리는 오버레이 강제 제거
                            try:
                                close_btn = await detail_page.query_selector('button[aria-label="Close new announcements modal"]')
                                if close_btn:
                                    print("  ⛔ 공지사항 팝업이 감지되었습니다. 화면 확보를 위해 닫습니다.")
                                    await close_btn.click()
                                    await detail_page.wait_for_timeout(1000)
                            except Exception:
                                pass

                            # [전체 스크롤 로딩] 하단 내용(지연 로딩)을 전부 로딩해오기 위해 무한 스크롤 및 로드 버튼 클릭
                            print("  - 페이지 하단까지 전체 데이터 로딩을 시도합니다...")
                            
                            no_change_count = 0
                            last_height = await detail_page.evaluate("document.body.scrollHeight")
                            
                            while True:
                                await detail_page.mouse.wheel(0, 8000)
                                await detail_page.wait_for_timeout(1500) # 네트워크 로딩을 기다림
                                
                                # '추가 콘텐츠 로드' 류의 버튼이 보이면 클릭
                                load_more = await detail_page.query_selector('button:has-text("Load")')
                                if load_more:
                                    try:
                                        await load_more.click()
                                        await detail_page.wait_for_timeout(2000)
                                    except:
                                        pass
                                
                                new_height = await detail_page.evaluate("document.body.scrollHeight")
                                if new_height == last_height:
                                    no_change_count += 1
                                else:
                                    no_change_count = 0  # 높이가 늘어났다면 카운터 초기화
                                    last_height = new_height
                                    
                                # 3번 연속(약 4.5초 대기) 높이 변화가 없으면 진짜 끝단으로 간주하고 탈출
                                if no_change_count >= 3:
                                    break

                            # [재귀적 폴더 펼치기] 닫혀 있는 모든 중첩 폴더를 끝까지 확장
                            expanded_count = 0
                            while True:
                                # 닫혀있는 폴더만 명확히 타겟팅 (Blackboard 내부 속성 사용)
                                closed_folders = await detail_page.query_selector_all('button[id^="folder-title-"][aria-expanded="false"]')
                                if not closed_folders:
                                    break
                                
                                for folder in closed_folders:
                                    try:
                                        await folder.click()
                                        expanded_count += 1
                                        await detail_page.wait_for_timeout(800) # 폴더가 열리는 애니메이션 대기
                                    except:
                                        pass
                                        
                            print(f"  - 총 {expanded_count}회의 숨겨진 중첩 폴더 확장을 완료했습니다.")

                            # 2단계: 내용물이 모두 펼쳐진 상태에서, 부모 폴더 경로를 추적하며 전체 항목 추출
                            extracted_items = await detail_page.evaluate('''() => {
                                let results = [];
                                // 파일, 영상 링크뿐만 아니라 폴더(button) 객체도 전부 타겟팅
                                const elements = document.querySelectorAll('a[class*="makeStylescontentItemTitle"], button[id^="folder-title-"]');
                                
                                let idCounter = 0;
                                for (const el of elements) {
                                    idCounter++;
                                    let scraperId = 'item_' + idCounter;
                                    el.setAttribute('data-scraper-id', scraperId);
                                    
                                    let name = el.innerText.trim().split('\\n')[0]; 
                                    let href = el.href || '';
                                    let isFolder = el.tagName.toLowerCase() === 'button';
                                    
                                    let path = [];
                                    let ownLi = el.closest('li');
                                    let currentLi = ownLi ? ownLi.parentElement.closest('li') : null;
                                    
                                    // HTML의 계층 구조(ul > li)를 타고 올라가며 부모 폴더들의 이름을 조립
                                    while (currentLi) {
                                        let folderBtn = currentLi.querySelector('button[id^="folder-title-"]');
                                        if (folderBtn) {
                                            path.unshift(folderBtn.innerText.trim().split('\\n')[0]);
                                        }
                                        currentLi = currentLi.parentElement.closest('li');
                                    }
                                    
                                    let fullPath = path.length > 0 ? path.join('/') + '/' + name : name;
                                    
                                    let itemType = 'Unknown';
                                    let container = el.closest('.MuiListItemroot-root, [role="listitem"], .outline-item');
                                    if (!container && el.parentElement && el.parentElement.parentElement) {
                                        container = el.parentElement.parentElement.parentElement;
                                    }
                                    if (container) {
                                        let icon = container.querySelector('svg[aria-label], img[aria-label], [role="img"][aria-label]');
                                        if (icon) {
                                            itemType = icon.getAttribute('aria-label');
                                        }
                                    }
                                    
                                    // 사용자의 요청: aria-label이 "폴더 열기"이면 폴더로 인식
                                    if (itemType.includes("폴더 열기")) {
                                        isFolder = true;
                                        itemType = "폴더";
                                    }
                                    
                                    results.push({
                                        title: name,
                                        href: href,
                                        isFolder: isFolder,
                                        fullPath: fullPath,
                                        scraperId: scraperId,
                                        itemType: itemType
                                    });
                                }
                                return results;
                            }''')

                            print(f"  - 총 {len(extracted_items)}개의 세부 자료(폴더 등 포함)를 스캔했습니다.")
                            
                            seen_items = set()
                            
                            for item in extracted_items:
                                i_href = item['href']
                                is_folder = item['isFolder']
                                full_path = item['fullPath']
                                s_id = item['scraperId']
                                
                                # 동일한 요소 이중 클릭/출력 방지
                                unique_key = (full_path, i_href, is_folder)
                                if unique_key in seen_items:
                                    continue
                                seen_items.add(unique_key)
                                
                                # --- 여기서부터는 모듈화된 (handlers) 개별 객체에 추출 책임을 위임합니다 ---
                                handler = get_handler(item.get('itemType', 'Unknown'))
                                try:
                                    extracted_data = await handler.extract(detail_page, item)
                                    
                                    if extracted_data:
                                        # 계층형 폴더 분리 로직 (예: "주차 1/강의자료/문서" -> 부모: "주차 1/강의자료")
                                        path_parts = full_path.split('/')
                                        folder_path = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else '/'
                                        
                                        if folder_path not in self.processed_items[course_title]:
                                            self.processed_items[course_title][folder_path] = []
                                            
                                        self.processed_items[course_title][folder_path].append(extracted_data)
                                        
                                except Exception as e:
                                    print(f"  ❌ [{item.get('itemType', 'Unknown')}] 항목 분석 중 에러: {e}")

                        except Exception as e:
                            print(f"과목 상세 로딩 중 에러: {e}")
                        
                        finally:
                            await detail_page.close()

                except TimeoutError:
                    print("과목 카드를 찾지 못했습니다. 페이지가 다르게 생겼거나 로딩이 지연되었습니다.")

                # 강제 대기 (눈으로 동작을 확인하기 위함, 나중에 삭제)
                await page.wait_for_timeout(5000)
            else:
                print("로그인에 실패하여 스크래핑을 중단합니다.")

            await browser.close()
            self._save_processed_items()

if __name__ == "__main__":
    scraper = BlackboardScraper()
    asyncio.run(scraper.run())

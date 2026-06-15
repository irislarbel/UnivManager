import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import BLACKBOARD_URL, BLACKBOARD_USER, BLACKBOARD_PASS

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        await page.goto(BLACKBOARD_URL)
        await page.wait_for_load_state("networkidle")
        await page.fill("#userId", BLACKBOARD_USER)
        await page.fill("#password", BLACKBOARD_PASS)
        await page.click("#loginSubmit")
        await page.wait_for_selector("#courses-overview-filter-search", timeout=30000)
        
        # 특정 과제 직접 이동
        await page.goto("https://eclass2.ajou.ac.kr/ultra/courses/_111078_1/outline/assessment/_2304079_1/overview?courseId=_111078_1")
        await page.wait_for_timeout(5000)
        
        # 패널 내부 클릭 대기 (평가보기 등)
        all_btns = await page.query_selector_all('button, a')
        clicked = False
        for btn in all_btns:
            try:
                v_text = (await btn.inner_text()).strip().replace(" ", "").lower()
                if "평가" in v_text or "시작" in v_text or "view" in v_text or "보기" in v_text:
                    print(f"Clicking: {v_text}")
                    await btn.click(force=True)
                    await page.wait_for_timeout(4000)
                    clicked = True
                    break
            except:
                pass
                
        if not clicked:
            print("No button clicked, maybe panel is already active.")
            
        panel_html = await page.evaluate("() => { let p = document.querySelector('.bb-offcanvas-panel.active:not(.hide-in-background)'); return p ? p.innerHTML : document.body.innerHTML; }")
        with open("panel_dump.html", "w", encoding="utf-8") as f:
            f.write(panel_html)
            
        print("Done downloading panel html.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())

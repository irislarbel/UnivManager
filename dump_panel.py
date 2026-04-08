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
        
        # 특정 과목 outline 이동
        await page.goto("https://eclass2.ajou.ac.kr/ultra/courses/_114238_1/outline")
        await page.wait_for_timeout(5000)
        
        # '과제 0' 요소가 보일 때까지 스크롤 
        for _ in range(5):
             await page.mouse.wheel(0, 5000)
             await page.wait_for_timeout(1000)
             
        item = await page.wait_for_selector('a:has-text("과제 0")', timeout=15000)
        await item.click(force=True)
        await page.wait_for_timeout(3000)
        
        # btn click 
        view_btns = await page.query_selector_all('button')
        for v_btn in view_btns:
            v_text = (await v_btn.inner_text()).strip()
            v_clean = v_text.replace(" ", "").lower()
            if any(kw in v_clean for kw in ["지시", "평가보기", "토론보기", "시작", "계속", "view", "start", "continue"]):
                await v_btn.click(force=True)
                await page.wait_for_timeout(3000)
                break
                
        panel_html = await page.evaluate("() => document.body.innerHTML")
        with open("panel_dump.html", "w", encoding="utf-8") as f:
            f.write(panel_html)
            
        print("Done downloading panel html.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())

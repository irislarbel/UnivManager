import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import BLACKBOARD_URL, BLACKBOARD_USER, BLACKBOARD_PASS

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        await page.goto(BLACKBOARD_URL)
        await page.wait_for_load_state("networkidle")
        await page.fill("#userId", BLACKBOARD_USER)
        await page.fill("#password", BLACKBOARD_PASS)
        await page.click("#loginSubmit")
        await page.wait_for_selector("#courses-overview-filter-search", timeout=30000)
        
        # 특정 과제로 바로 이동
        await page.goto("https://eclass2.ajou.ac.kr/ultra/courses/_111078_1/outline/assessment/_2304079_1/overview?courseId=_111078_1")
        await page.wait_for_timeout(5000)
        
        # Click any view buttons repeatedly to ensure all panels are open
        for _ in range(3):
            view_btns = await page.query_selector_all('button, a')
            clicked = False
            for v_btn in view_btns:
                try:
                    v_text = (await v_btn.inner_text()).strip().replace(" ", "").lower()
                    if any(kw in v_text for kw in ["지시사항보기", "평가보기", "토론보기", "시작", "계속", "view", "start", "continue", "평가시작"]):
                        await v_btn.click(force=True)
                        await page.wait_for_timeout(3000)
                        clicked = True
                        break
                except: pass
            if not clicked:
                break

        # Playwright's locator naturally pierces Shadow DOM!
        elements = await page.locator(':has-text("hwpx")').all()
        print(f"Found {len(elements)} elements containing 'hwpx'")
        if elements:
            # We want the most specific element (usually the last one in the hierarchy)
            # which has no child elements containing the text.
            for el in elements[-3:]:
                try:
                    tag = await el.evaluate("e => e.tagName")
                    outer = await el.evaluate("e => e.outerHTML")
                    print(f"--- TAG: {tag} ---")
                    print(outer[:1000]) # print first 1000 chars
                except: pass
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())

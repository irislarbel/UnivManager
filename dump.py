import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import BLACKBOARD_URL, BLACKBOARD_USER, BLACKBOARD_PASS

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await Stealth().apply_stealth_async(page)
        
        await page.goto(BLACKBOARD_URL)
        await page.wait_for_load_state("networkidle")
        await page.fill("#userId", BLACKBOARD_USER)
        await page.fill("#password", BLACKBOARD_PASS)
        await page.click("#loginSubmit")
        
        await page.wait_for_selector("#courses-overview-filter-search", timeout=30000)
        await page.wait_for_timeout(3000)
        await page.goto("https://eclass2.ajou.ac.kr/ultra/course")
        await page.wait_for_selector("article.course-element-card", timeout=15000)
        
        card = await page.query_selector("article.course-element-card")
        html = await card.inner_html()
        
        card_id = await card.get_attribute("id")
        print(f"CARD ID: {card_id}")
        
        with open("card_html.txt", "w", encoding="utf-8") as f:
            f.write(html)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())

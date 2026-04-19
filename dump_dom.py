import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

USER_ID = os.getenv('BLACKBOARD_USER')
USER_PW = os.getenv('BLACKBOARD_PASS')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Logging in...")
        await page.goto("https://sso.ajou.ac.kr/jsp/sso/ip/login_form.jsp", wait_until='networkidle')
        await page.fill('#userId', USER_ID)
        await page.fill('#password', USER_PW)
        await page.click('#loginSubmit')
        print("Login clicked, waiting...")
        await page.wait_for_timeout(3000)
        
        print("Going to course CAJO1113...")
        # Blackbord Ultra course CAJO1113 link (approximate, we'll just go to the dashboard and click it)
        await page.goto("https://eclass2.ajou.ac.kr/ultra/course")
        await page.wait_for_timeout(3000)
        
        # Click course
        course_link = await page.wait_for_selector('a:has-text("CAJO1113")')
        await course_link.click()
        await page.wait_for_timeout(5000)
        
        print("Expanding folders...")
        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(500)
            closed_folders = await page.query_selector_all('button[id^="folder-title-"][aria-expanded="false"]')
            if closed_folders:
                for f in closed_folders:
                    await f.scroll_into_view_if_needed()
                    await f.click(force=True)
                await page.wait_for_timeout(1000)
            else:
                break
                
        print("Dumping DOM...")
        html = await page.evaluate("document.querySelector('main, .course-content-container, body').outerHTML")
        with open("dom_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Done. Saved to dom_dump.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

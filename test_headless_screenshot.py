import asyncio
from playwright.async_api import async_playwright

async def test_headless_screenshot():
    print("🧪 Testing headless screenshot capability...")
    
    async with async_playwright() as p:
        # Launch in headless mode (no visible window)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("📱 Browser launched in headless mode")
        
        # Navigate to a website
        await page.goto('https://defi.space')
        await page.wait_for_load_state('domcontentloaded')
        
        print("🌐 Page loaded (invisibly)")
        
        # Take screenshot in headless mode!
        await page.screenshot(path='headless_screenshot.png', full_page=True)
        print("📸 Screenshot captured!")
        
        # Get page info to show it's actually working
        title = await page.title()
        url = page.url
        
        print(f"📄 Page title: {title}")
        print(f"🔗 URL: {url}")
        
        await browser.close()
        print("✅ Screenshot saved as 'headless_screenshot.png'")

if __name__ == "__main__":
    asyncio.run(test_headless_screenshot()) 
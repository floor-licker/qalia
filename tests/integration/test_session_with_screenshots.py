#!/usr/bin/env python3
"""
Test script to demonstrate session management with error screenshots.
"""

import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleWebTester:
    """Simple web tester with session management and error screenshots."""
    
    def __init__(self, url: str):
        self.url = url
        self.session_manager = SessionManager(url)
        self.browser = None
        self.page = None
        
    async def run_test(self):
        """Run the test with error handling and screenshots."""
        logger.info(f"🚀 Starting test session for {self.url}")
        
        try:
            # Setup browser
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            context = await self.browser.new_context()
            self.page = await context.new_page()
            
            # Test 1: Navigate to valid URL
            logger.info("Test 1: Normal navigation")
            await self.test_normal_navigation()
            
            # Test 2: Navigate to 404 page
            logger.info("Test 2: 404 Error test")
            await self.test_404_error()
            
            # Test 3: Test console errors
            logger.info("Test 3: Console error test") 
            await self.test_console_error()
            
            # Test 4: Test timeout
            logger.info("Test 4: Timeout test")
            await self.test_timeout()
            
            logger.info("✅ All tests completed")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            
            # Capture failure screenshot
            if self.page:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "test_failure",
                    str(e)[:50],
                    self.page.url if self.page else self.url
                )
                
        finally:
            if self.browser:
                await self.browser.close()
        
        # Generate test report
        test_results = {
            'test_url': self.url,
            'screenshots_taken': len(self.session_manager.screenshots_taken),
            'test_status': 'completed'
        }
        
        report_path = self.session_manager.save_session_report(test_results)
        logger.info(f"📁 Test session saved to: {self.session_manager.session_dir}")
        logger.info(f"📋 Report saved to: {report_path}")
        
        return test_results
        
    async def test_normal_navigation(self):
        """Test normal navigation (should not generate screenshots)."""
        try:
            response = await self.page.goto(self.url, timeout=10000)
            if response and response.status >= 400:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    f"{response.status}_error",
                    f"HTTP_{response.status}",
                    self.url
                )
            logger.info(f"✅ Normal navigation completed: {response.status if response else 'No response'}")
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            await self.session_manager.capture_error_screenshot(
                self.page,
                "navigation_error",
                str(e)[:50],
                self.url
            )
            
    async def test_404_error(self):
        """Test 404 error (should generate screenshot)."""
        test_url = self.url.rstrip('/') + '/nonexistent-page-404-test'
        try:
            response = await self.page.goto(test_url, timeout=10000)
            if response and response.status == 404:
                await self.session_manager.capture_error_screenshot(
                    self.page,
                    "404_not_found",
                    "page_not_found",
                    test_url
                )
                logger.info("✅ 404 error test completed - screenshot captured")
            else:
                logger.info(f"📝 404 test result: {response.status if response else 'No response'}")
        except Exception as e:
            logger.error(f"404 test failed: {e}")
            await self.session_manager.capture_error_screenshot(
                self.page,
                "404_test_error",
                str(e)[:50],
                test_url
            )
            
    async def test_console_error(self):
        """Test console error detection (inject JS error)."""
        try:
            # Go to a page first
            await self.page.goto(self.url)
            
            # Inject a JavaScript error
            await self.page.evaluate("console.error('Test console error for screenshot')")
            
            # Simulate capturing this as an error
            await self.session_manager.capture_error_screenshot(
                self.page,
                "console_error",
                "injected_test_error",
                self.page.url
            )
            
            logger.info("✅ Console error test completed - screenshot captured")
            
        except Exception as e:
            logger.error(f"Console error test failed: {e}")
            await self.session_manager.capture_error_screenshot(
                self.page,
                "console_test_error",
                str(e)[:50],
                self.page.url
            )
            
    async def test_timeout(self):
        """Test timeout scenario."""
        try:
            # Try to navigate with very short timeout to trigger timeout
            await self.page.goto(self.url, timeout=1)  # Very short timeout
            logger.info("✅ Timeout test completed (no timeout occurred)")
            
        except PlaywrightTimeoutError:
            logger.info("⏰ Timeout occurred as expected")
            await self.session_manager.capture_error_screenshot(
                self.page,
                "navigation_timeout",
                "1ms_timeout",
                self.url
            )
            logger.info("✅ Timeout test completed - screenshot captured")
            
        except Exception as e:
            logger.error(f"Timeout test failed: {e}")
            await self.session_manager.capture_error_screenshot(
                self.page,
                "timeout_test_error",
                str(e)[:50],
                self.url
            )

async def main():
    """Main test function."""
    # Test with a real website
    test_url = "https://httpstat.us/500"  # This will return a 500 error
    
    tester = SimpleWebTester(test_url)
    results = await tester.run_test()
    
    print("\n" + "="*50)
    print("🎯 TEST SESSION RESULTS")
    print("="*50)
    print(f"URL tested: {results['test_url']}")
    print(f"Screenshots captured: {results['screenshots_taken']}")
    print(f"Session directory: {tester.session_manager.session_dir}")
    print("="*50)
    
    # List screenshots taken
    if tester.session_manager.screenshots_taken:
        print("\n📸 Screenshots captured:")
        for i, screenshot in enumerate(tester.session_manager.screenshots_taken, 1):
            print(f"  {i}. {screenshot['filename']} - {screenshot['error_type']}")
    else:
        print("\n✅ No error screenshots taken - clean session!")

if __name__ == "__main__":
    asyncio.run(main()) 
"""
Browser Management Utility

Handles browser setup, cleanup, and event management for Playwright-based exploration.
Extracted from multiple explorer implementations to provide consistent browser handling.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Configuration for browser setup."""
    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str = 'Mozilla/5.0 (compatible; QA-Bot/1.0; Autonomous Testing Agent)'
    timeout: int = 30000
    args: List[str] = None
    
    def __post_init__(self):
        if self.args is None:
            self.args = ['--no-sandbox', '--disable-dev-shm-usage']


class BrowserManager:
    """
    Manages browser lifecycle and event handling for website exploration.
    
    Provides consistent browser setup, cleanup, and event management
    across different exploration strategies.
    """
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        
        # Browser instances
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Event handlers
        self.console_handlers: List[Callable] = []
        self.response_handlers: List[Callable] = []
        self.error_handlers: List[Callable] = []
        
        # State tracking
        self.is_setup = False
    
    async def setup(self) -> None:
        """Initialize browser with configuration."""
        if self.is_setup:
            logger.warning("Browser already setup")
            return
        
        try:
            logger.info("🚀 Setting up browser...")
            
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browser
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.headless,
                args=self.config.args
            )
            
            # Create context
            self.context = await self.browser.new_context(
                viewport={
                    'width': self.config.viewport_width,
                    'height': self.config.viewport_height
                },
                user_agent=self.config.user_agent
            )
            
            # Create page
            self.page = await self.context.new_page()
            
            # Set up event listeners
            await self._setup_event_listeners()
            
            self.is_setup = True
            logger.info("✅ Browser setup completed")
            
        except Exception as e:
            logger.error(f"Browser setup failed: {e}")
            await self.cleanup()
            raise
    
    async def _setup_event_listeners(self) -> None:
        """Set up event listeners on the page."""
        if not self.page:
            return
        
        # Console message handler
        async def console_handler(msg):
            for handler in self.console_handlers:
                try:
                    await handler(msg)
                except Exception as e:
                    logger.error(f"Console handler error: {e}")
        
        # Response handler
        async def response_handler(response):
            for handler in self.response_handlers:
                try:
                    await handler(response)
                except Exception as e:
                    logger.error(f"Response handler error: {e}")
        
        # Page error handler
        async def page_error_handler(error):
            for handler in self.error_handlers:
                try:
                    await handler(error)
                except Exception as e:
                    logger.error(f"Page error handler error: {e}")
        
        # Attach event listeners
        self.page.on('console', console_handler)
        self.page.on('response', response_handler)
        self.page.on('pageerror', page_error_handler)
    
    async def cleanup(self) -> None:
        """Clean up browser resources."""
        try:
            logger.info("🧹 Cleaning up browser...")
            
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            self.is_setup = False
            logger.info("✅ Browser cleanup completed")
            
        except Exception as e:
            logger.warning(f"Error during browser cleanup: {e}")
    
    def add_console_handler(self, handler: Callable) -> None:
        """Add a console message handler."""
        self.console_handlers.append(handler)
    
    def add_response_handler(self, handler: Callable) -> None:
        """Add a response handler."""
        self.response_handlers.append(handler)
    
    def add_error_handler(self, handler: Callable) -> None:
        """Add a page error handler."""
        self.error_handlers.append(handler)
    
    async def navigate(self, url: str, wait_until: str = 'domcontentloaded', timeout: int = None) -> bool:
        """
        Navigate to URL with error handling.
        
        Args:
            url: URL to navigate to
            wait_until: Wait condition ('domcontentloaded', 'load', 'networkidle')
            timeout: Navigation timeout in milliseconds
            
        Returns:
            True if navigation successful, False otherwise
        """
        if not self.page:
            raise RuntimeError("Browser not setup - call setup() first")
        
        timeout = timeout or self.config.timeout
        
        try:
            logger.info(f"🧭 Navigating to: {url}")
            
            response = await self.page.goto(
                url, 
                timeout=timeout,
                wait_until=wait_until
            )
            
            if response and response.status >= 400:
                logger.warning(f"Navigation returned {response.status}: {url}")
                return False
            
            # Brief wait for dynamic content
            await asyncio.sleep(1)
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
            return False
    
    async def wait_for_load_state(self, state: str = 'domcontentloaded', timeout: int = None) -> None:
        """Wait for page load state."""
        if not self.page:
            return
        
        timeout = timeout or self.config.timeout
        
        try:
            await self.page.wait_for_load_state(state, timeout=timeout)
        except Exception as e:
            logger.debug(f"Wait for load state failed: {e}")
    
    async def get_content(self) -> str:
        """Get current page HTML content."""
        if not self.page:
            return ""
        
        try:
            return await self.page.content()
        except Exception as e:
            logger.error(f"Failed to get page content: {e}")
            return ""
    
    def get_current_url(self) -> str:
        """Get current page URL."""
        if not self.page:
            return ""
        
        try:
            return self.page.url
        except:
            return ""
    
    async def take_screenshot(self, path: str = None, full_page: bool = False) -> Optional[bytes]:
        """Take a screenshot of the current page."""
        if not self.page:
            return None
        
        try:
            if path:
                await self.page.screenshot(path=path, full_page=full_page)
                return None
            else:
                return await self.page.screenshot(full_page=full_page)
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    def is_ready(self) -> bool:
        """Check if browser is ready for use."""
        return self.is_setup and self.page is not None
    
    async def evaluate_js(self, js_code: str) -> Any:
        """Execute JavaScript code on the page."""
        if not self.page:
            return None
        
        try:
            return await self.page.evaluate(js_code)
        except Exception as e:
            logger.error(f"JavaScript evaluation failed: {e}")
            return None
    
    async def wait_for_selector(self, selector: str, timeout: int = None) -> bool:
        """Wait for a selector to appear on the page."""
        if not self.page:
            return False
        
        timeout = timeout or self.config.timeout
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"Wait for selector failed: {e}")
            return False
    
    def get_locator(self, selector: str):
        """Get a Playwright locator for the given selector."""
        if not self.page:
            return None
        
        return self.page.locator(selector) 
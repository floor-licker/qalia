"""
Browser Event Handling

Centralized event management for browser interactions.
"""

import logging
from typing import Callable, Dict, Any, List
from dataclasses import dataclass
from playwright.async_api import Page, Response

logger = logging.getLogger(__name__)


@dataclass
class EventConfig:
    """Configuration for event handling."""
    capture_console: bool = True
    capture_network: bool = True
    capture_responses: bool = True
    log_level: str = 'INFO'


class EventHandler:
    """Centralized browser event handler."""
    
    def __init__(self, config: EventConfig = None):
        self.config = config or EventConfig()
        self.console_handlers: List[Callable] = []
        self.response_handlers: List[Callable] = []
        self.error_handlers: List[Callable] = []
        
    def add_console_handler(self, handler: Callable):
        """Add a console message handler."""
        self.console_handlers.append(handler)
        
    def add_response_handler(self, handler: Callable):
        """Add an HTTP response handler."""
        self.response_handlers.append(handler)
        
    def add_error_handler(self, handler: Callable):
        """Add an error handler."""
        self.error_handlers.append(handler)
        
    def attach_to_page(self, page: Page):
        """Attach event handlers to a page."""
        if self.config.capture_console:
            page.on('console', self._handle_console)
            page.on('pageerror', self._handle_page_error)
            
        if self.config.capture_network:
            page.on('requestfailed', self._handle_request_failed)
            
        if self.config.capture_responses:
            page.on('response', self._handle_response)
            
        logger.info("Event handlers attached to page")
        
    async def _handle_console(self, msg):
        """Handle console messages."""
        try:
            for handler in self.console_handlers:
                await handler(msg)
        except Exception as e:
            logger.error(f"Error in console handler: {e}")
            
    async def _handle_response(self, response: Response):
        """Handle HTTP responses."""
        try:
            for handler in self.response_handlers:
                await handler(response)
        except Exception as e:
            logger.error(f"Error in response handler: {e}")
            
    async def _handle_page_error(self, error):
        """Handle page errors."""
        try:
            for handler in self.error_handlers:
                await handler(error)
        except Exception as e:
            logger.error(f"Error in page error handler: {e}")
            
    async def _handle_request_failed(self, request):
        """Handle failed requests."""
        try:
            for handler in self.error_handlers:
                await handler(request)
        except Exception as e:
            logger.error(f"Error in request failed handler: {e}") 
"""
Modal Handler Utility

Handles modal detection, interaction, and dismissal for comprehensive modal exploration.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ModalHandler:
    """
    Handles modal detection and interaction during website exploration.
    
    Provides modal detection, dismissal, and interaction capabilities
    for comprehensive modal testing.
    """
    
    def __init__(self, page):
        self.page = page
        
        # Modal detection selectors
        self.modal_selectors = [
            '[role="dialog"]',
            '[aria-modal="true"]',
            '.modal',
            '.dialog',
            '.popup',
            '.overlay'
        ]
        
        self.discovered_modals: List[Dict[str, Any]] = []
    
    async def detect_modals(self) -> List[Dict[str, Any]]:
        """Detect visible modals on the page."""
        detected = []
        
        for selector in self.modal_selectors:
            try:
                modals = await self.page.locator(selector).all()
                for modal in modals:
                    if await modal.is_visible():
                        modal_info = {
                            'selector': selector,
                            'visible': True,
                            'timestamp': time.time()
                        }
                        detected.append(modal_info)
            except:
                continue
        
        return detected
    
    async def dismiss_modal(self, modal_selector: str = None) -> bool:
        """Attempt to dismiss modal using various methods."""
        try:
            # Try ESC key
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # Check if modal is gone
            if not await self._has_visible_modals():
                return True
            
            # Try close buttons
            close_selectors = [
                'button:has-text("Close")',
                'button:has-text("✕")',
                '[aria-label="Close"]'
            ]
            
            for selector in close_selectors:
                try:
                    close_btn = self.page.locator(selector).first
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await asyncio.sleep(0.5)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Modal dismissal failed: {e}")
            return False
    
    async def _has_visible_modals(self) -> bool:
        """Check if any modals are currently visible."""
        for selector in self.modal_selectors:
            try:
                modal = self.page.locator(selector).first
                if await modal.is_visible():
                    return True
            except:
                continue
        return False 
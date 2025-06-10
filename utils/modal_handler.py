"""
Modal Handler Utility

Handles modal detection, interaction, and dismissal for comprehensive modal exploration.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass  
class ModalActionResult:
    """Result of a modal interaction."""
    success: bool
    action_type: str = 'click'
    element_info: Dict[str, Any] = None
    duration: float = 0.0
    error_message: Optional[str] = None
    modal_context: bool = True
    modal_selector: str = ''
    url_changed: bool = False
    modal_state_changed: bool = False
    modal_dismissed: bool = False
    state_changes: List[Any] = None  # Compatibility with ActionResult interface
    success_assessment: Dict[str, Any] = None  # Compatibility with ActionResult interface
    baseline_state: Dict[str, Any] = None  # Compatibility with ActionResult interface
    final_state: Dict[str, Any] = None  # Compatibility with ActionResult interface
    
    def __post_init__(self):
        if self.state_changes is None:
            self.state_changes = []
        if self.success_assessment is None:
            self.success_assessment = {
                'confidence': 0.8,
                'reasoning': 'Modal element interaction completed',
                'evidence': ['Modal content detected and interacted with'],
                'modal_interaction': True
            }
        if self.baseline_state is None:
            self.baseline_state = {
                'modal_interaction': True,
                'baseline_captured': False
            }
        if self.final_state is None:
            self.final_state = {
                'modal_interaction': True,
                'final_captured': False
            }


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
        self.modal_interactions_performed: List[Dict[str, Any]] = []
    
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
    
    async def explore_modal_content(self) -> List[Dict[str, Any]]:
        """
        Extract and explore interactive elements within visible modals.
        
        Returns:
            List of interaction results from modal content
        """
        interaction_results = []
        
        try:
            # Find all visible modals
            modals = await self.detect_modals()
            
            if not modals:
                return interaction_results
            
            logger.info(f"🎭 Found {len(modals)} modal(s), exploring content...")
            
            for modal_info in modals:
                modal_selector = modal_info['selector']
                
                # Extract interactive elements from within this modal
                modal_elements = await self._extract_modal_elements(modal_selector)
                
                if modal_elements:
                    logger.info(f"   📝 Found {len(modal_elements)} interactive elements in modal")
                    
                    # Test each element in the modal
                    for element in modal_elements:
                        try:
                            result = await self._test_modal_element(element, modal_selector)
                            if result:
                                interaction_results.append(result)
                                self.modal_interactions_performed.append(result)
                                
                                # Brief pause between modal interactions
                                await asyncio.sleep(0.5)
                                
                        except Exception as e:
                            logger.warning(f"   ⚠️ Failed to test modal element {element.get('text', 'unknown')}: {e}")
                            continue
                
        except Exception as e:
            logger.error(f"❌ Modal content exploration failed: {e}")
        
        return interaction_results
    
    async def _extract_modal_elements(self, modal_selector: str) -> List[Dict[str, Any]]:
        """Extract interactive elements from within a specific modal."""
        try:
            modal_elements = await self.page.evaluate(f"""
                (modalSelector) => {{
                    const modal = document.querySelector(modalSelector);
                    if (!modal) return [];
                    
                    const elements = [];
                    
                    // Find traditional buttons within modal
                    modal.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]').forEach((el, index) => {{
                        if (el.offsetParent !== null && !el.disabled) {{
                            const text = el.textContent?.trim() || el.value || '';
                            if (text) {{
                                elements.push({{
                                    type: 'button',
                                    text: text,
                                    selector: `${{modalSelector}} button:has-text("${{text}}")`,
                                    id: el.id || '',
                                    class: el.className || '',
                                    modal_context: true
                                }});
                            }}
                        }}
                    }});
                    
                    // Find traditional links within modal
                    modal.querySelectorAll('a[href]').forEach((el, index) => {{
                        if (el.offsetParent !== null && el.href) {{
                            const text = el.textContent?.trim() || '';
                            if (text) {{
                                elements.push({{
                                    type: 'link',
                                    text: text,
                                    href: el.href,
                                    selector: `${{modalSelector}} a:has-text("${{text}}")`,
                                    id: el.id || '',
                                    class: el.className || '',
                                    modal_context: true
                                }});
                            }}
                        }}
                    }});
                    
                    // Find form inputs within modal
                    modal.querySelectorAll('input, textarea, select').forEach((el, index) => {{
                        if (el.offsetParent !== null && !el.disabled) {{
                            const inputName = el.name || el.id || el.placeholder || 'input';
                            elements.push({{
                                type: el.tagName.toLowerCase() === 'select' ? 'select' : 'input',
                                input_type: el.type || 'text',
                                name: el.name || '',
                                placeholder: el.placeholder || '',
                                selector: `${{modalSelector}} ${{el.tagName.toLowerCase()}}${{el.id ? '#' + el.id : ''}}`,
                                id: el.id || '',
                                modal_context: true
                            }});
                        }}
                    }});
                    
                    // ENHANCED: Find clickable elements (divs, spans) with cursor pointer
                    const allElements = modal.querySelectorAll('*');
                    allElements.forEach((el, index) => {{
                        if (el.offsetParent !== null) {{
                            const style = window.getComputedStyle(el);
                            const text = el.textContent?.trim();
                            
                            // Check if element is clickable (has pointer cursor)
                            if (style.cursor === 'pointer' && text && text.length > 0 && text.length < 100) {{
                                // Avoid duplicates
                                const isDuplicate = elements.some(existing => existing.text === text);
                                
                                if (!isDuplicate) {{
                                    elements.push({{
                                        type: 'clickable_element',
                                        element_tag: el.tagName.toLowerCase(),
                                        text: text,
                                        selector: `${{modalSelector}} :text("${{text}}")`,
                                        id: el.id || '',
                                        class: el.className || '',
                                        cursor: style.cursor,
                                        modal_context: true
                                    }});
                                }}
                            }}
                        }}
                    }});
                    
                    return elements;
                }}
            """, modal_selector)
            
            return modal_elements or []
            
        except Exception as e:
            logger.error(f"❌ Failed to extract modal elements: {e}")
            return []
    
    async def _test_modal_element(self, element: Dict[str, Any], modal_selector: str) -> Optional[Dict[str, Any]]:
        """
        Test clicking an element within a modal.
        
        Args:
            element: Element information
            modal_selector: Selector of the containing modal
            
        Returns:
            Result of the interaction or None if failed
        """
        element_text = element.get('text', 'unknown')
        element_selector = element.get('selector', '')
        
        try:
            logger.info(f"   🖱️ Testing modal element: {element_text}")
            
            # Verify element still exists and is clickable
            locator = self.page.locator(element_selector).first
            
            # Check if element is visible and enabled
            if not await locator.is_visible():
                logger.warning(f"   ⚠️ Modal element not visible: {element_text}")
                return None
            
            if element['type'] == 'button' and await locator.is_disabled():
                logger.warning(f"   ⚠️ Modal button is disabled: {element_text}")
                return None
            
            # Capture state before interaction
            url_before = self.page.url
            modal_present_before = len(await self.detect_modals()) > 0
            
            # Perform the click
            start_time = time.time()
            
            await locator.click(timeout=3000)
            
            # Wait a moment for any changes to occur
            await asyncio.sleep(1.0)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Capture state after interaction
            url_after = self.page.url
            modal_present_after = len(await self.detect_modals()) > 0
            
            # Determine what happened
            url_changed = url_before != url_after
            modal_state_changed = modal_present_before != modal_present_after
            
            result = ModalActionResult(
                success=True,
                action_type='click',
                element_info=element,
                duration=duration,
                modal_context=True,
                modal_selector=modal_selector,
                url_changed=url_changed,
                modal_state_changed=modal_state_changed,
                modal_dismissed=modal_present_before and not modal_present_after
            )
            
            # Log the result
            if url_changed:
                logger.info(f"   ✅ Modal element click caused navigation: {element_text}")
            elif modal_state_changed:
                logger.info(f"   ✅ Modal element click changed modal state: {element_text}")
            else:
                logger.info(f"   ⚠️ Modal element click - no observable change: {element_text}")
            
            return result
            
        except Exception as e:
            logger.warning(f"   ❌ Failed to test modal element {element_text}: {e}")
            return ModalActionResult(
                success=False,
                action_type='click',
                element_info=element,
                modal_context=True,
                modal_selector=modal_selector,
                error_message=str(e)
            )
    
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
    
    def get_modal_interaction_summary(self) -> Dict[str, Any]:
        """Get summary of all modal interactions performed."""
        successful_interactions = [r for r in self.modal_interactions_performed if r.success]
        failed_interactions = [r for r in self.modal_interactions_performed if not r.success]
        
        return {
            'total_modal_interactions': len(self.modal_interactions_performed),
            'successful_interactions': len(successful_interactions),
            'failed_interactions': len(failed_interactions),
            'modals_explored': len(set(r.modal_selector for r in self.modal_interactions_performed if hasattr(r, 'modal_selector'))),
            'interactions': self.modal_interactions_performed
        } 
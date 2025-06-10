#!/usr/bin/env python3
"""
Modal Explorer - Comprehensive Modal Detection and Exploration System
Handles nested modals, modal state tracking, and exhaustive modal UI exploration
"""

import asyncio
import logging
import hashlib
import time
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ModalState:
    """Represents the state of a detected modal."""
    modal_hash: str
    modal_selector: str
    modal_type: str  # 'dialog', 'overlay', 'popup', 'drawer'
    content_hash: str
    elements_found: int
    fully_explored: bool = False
    dismissal_methods: List[str] = field(default_factory=list)
    parent_modal: Optional[str] = None  # For nested modals
    discovery_timestamp: float = field(default_factory=time.time)

@dataclass 
class ModalExplorer:
    """
    Comprehensive modal detection and exploration system.
    Handles nested modals with recursive exploration.
    """
    
    page = None  # Playwright page instance
    session_manager = None
    
    # Modal state tracking
    discovered_modals: Dict[str, ModalState] = field(default_factory=dict)
    modal_stack: List[str] = field(default_factory=list)  # Current modal hierarchy
    modal_exploration_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Modal selectors (comprehensive list)
    modal_selectors: List[str] = field(default_factory=lambda: [
        # Standard modal selectors
        '[role="dialog"]',
        '[aria-modal="true"]', 
        '.modal',
        '.dialog',
        '.popup',
        '.overlay',
        '.lightbox',
        
        # Framework-specific selectors
        '.modal-dialog',    # Bootstrap
        '.ui-dialog',       # jQuery UI
        '.ant-modal',       # Ant Design
        '.chakra-modal',    # Chakra UI
        '.mantine-modal',   # Mantine
        '.modal-container', # Generic
        
        # Custom selectors for modern apps
        '[data-testid*="modal"]',
        '[data-cy*="modal"]',
        '[class*="Modal"]',
        '[class*="Dialog"]',
        '[class*="Popup"]',
        
        # High z-index detection (dynamic)
        # Will be computed at runtime
    ])

    async def detect_modals(self) -> List[Dict[str, Any]]:
        """
        Detect all modals currently visible on the page.
        Returns list of modal information.
        """
        detected_modals = []
        
        try:
            # Check each selector
            for selector in self.modal_selectors:
                try:
                    modals = await self.page.locator(selector).all()
                    for i, modal in enumerate(modals):
                        if await modal.is_visible():
                            modal_info = await self._analyze_modal(modal, selector, i)
                            if modal_info:
                                detected_modals.append(modal_info)
                except Exception as e:
                    logger.debug(f"Error checking selector {selector}: {e}")
            
            # Dynamic z-index detection
            high_z_modals = await self._detect_high_zindex_elements()
            detected_modals.extend(high_z_modals)
            
            # Remove duplicates
            unique_modals = self._deduplicate_modals(detected_modals)
            
            if unique_modals:
                logger.info(f"🎭 Detected {len(unique_modals)} modal(s)")
                for modal in unique_modals:
                    logger.info(f"   - {modal['type']}: {modal['modal_hash']}")
            
            return unique_modals
            
        except Exception as e:
            logger.error(f"Error detecting modals: {e}")
            return []

    async def _analyze_modal(self, modal_element, selector: str, index: int) -> Optional[Dict[str, Any]]:
        """Analyze a modal element and extract metadata."""
        try:
            # Get modal content for hashing
            content = await modal_element.inner_html()
            content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
            
            # Create unique modal identifier
            bounding_box = await modal_element.bounding_box()
            modal_signature = f"{selector}_{index}_{content_hash}"
            modal_hash = hashlib.md5(modal_signature.encode()).hexdigest()[:12]
            
            # Determine modal type
            modal_type = await self._determine_modal_type(modal_element, selector)
            
            # Count interactive elements within modal
            elements_count = await self._count_modal_elements(modal_element)
            
            # Create unique selector for this modal
            unique_selector = f"{selector}:nth-of-type({index + 1})"
            
            return {
                'modal_hash': modal_hash,
                'modal_selector': unique_selector,
                'modal_type': modal_type,
                'content_hash': content_hash,
                'elements_found': elements_count,
                'bounding_box': bounding_box,
                'base_selector': selector
            }
            
        except Exception as e:
            logger.debug(f"Error analyzing modal: {e}")
            return None

    async def _determine_modal_type(self, modal_element, selector: str) -> str:
        """Determine the type of modal based on attributes and selector."""
        try:
            # Check role attribute
            role = await modal_element.get_attribute('role')
            if role == 'dialog':
                return 'dialog'
            
            # Check aria attributes
            aria_modal = await modal_element.get_attribute('aria-modal')
            if aria_modal == 'true':
                return 'dialog'
            
            # Check class names for type hints
            class_name = await modal_element.get_attribute('class') or ''
            class_lower = class_name.lower()
            
            if 'drawer' in class_lower or 'sidebar' in class_lower:
                return 'drawer'
            elif 'popup' in class_lower or 'popover' in class_lower:
                return 'popup'
            elif 'lightbox' in class_lower:
                return 'lightbox'
            elif 'overlay' in class_lower:
                return 'overlay'
            else:
                return 'modal'
                
        except:
            return 'unknown'

    async def _count_modal_elements(self, modal_element) -> int:
        """Count interactive elements within a modal."""
        try:
            interactive_selectors = [
                'button', 'input', 'select', 'textarea', 'a[href]',
                '[role="button"]', '[tabindex]', '[onclick]'
            ]
            
            total_count = 0
            for selector in interactive_selectors:
                try:
                    elements = await modal_element.locator(selector).all()
                    visible_count = 0
                    for elem in elements:
                        if await elem.is_visible():
                            visible_count += 1
                    total_count += visible_count
                except:
                    continue
            
            return total_count
            
        except:
            return 0

    async def _detect_high_zindex_elements(self) -> List[Dict[str, Any]]:
        """Detect elements with high z-index that might be modals."""
        try:
            # JavaScript to find high z-index elements
            js_code = """
            () => {
                const elements = Array.from(document.querySelectorAll('*'));
                const highZElements = [];
                
                elements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    const zIndex = parseInt(style.zIndex);
                    const position = style.position;
                    
                    // High z-index + positioned + visible = likely modal
                    if (zIndex > 1000 && 
                        ['fixed', 'absolute'].includes(position) && 
                        style.display !== 'none' &&
                        style.visibility !== 'hidden') {
                        
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 100 && rect.height > 100) {
                            highZElements.push({
                                selector: el.tagName + (el.id ? '#' + el.id : '') + 
                                         (el.className ? '.' + el.className.split(' ').join('.') : ''),
                                zIndex: zIndex,
                                position: position,
                                rect: {
                                    width: rect.width,
                                    height: rect.height,
                                    x: rect.x,
                                    y: rect.y
                                }
                            });
                        }
                    }
                });
                
                return highZElements.slice(0, 5); // Limit results
            }
            """
            
            high_z_elements = await self.page.evaluate(js_code)
            
            modal_candidates = []
            for elem_data in high_z_elements:
                try:
                    # Try to locate the element
                    selector = elem_data['selector']
                    element = self.page.locator(selector).first
                    
                    if await element.is_visible():
                        modal_info = await self._analyze_modal(element, selector, 0)
                        if modal_info:
                            modal_info['detection_method'] = 'high_zindex'
                            modal_info['z_index'] = elem_data['zIndex']
                            modal_candidates.append(modal_info)
                except:
                    continue
            
            return modal_candidates
            
        except Exception as e:
            logger.debug(f"Error detecting high z-index elements: {e}")
            return []

    def _deduplicate_modals(self, modals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate modal detections based on content hash and position."""
        seen_hashes = set()
        unique_modals = []
        
        for modal in modals:
            # Create deduplication key from content hash and position
            content_hash = modal['content_hash']
            bbox = modal.get('bounding_box')
            
            if bbox:
                position_key = f"{bbox['x']:.0f}_{bbox['y']:.0f}_{bbox['width']:.0f}_{bbox['height']:.0f}"
            else:
                position_key = "no_bbox"
            
            dedup_key = f"{content_hash}_{position_key}"
            
            if dedup_key not in seen_hashes:
                seen_hashes.add(dedup_key)
                unique_modals.append(modal)
        
        return unique_modals

    async def explore_modal_recursively(self, modal_info: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """
        Recursively explore a modal and all nested modals it may spawn.
        """
        modal_hash = modal_info['modal_hash']
        modal_selector = modal_info['modal_selector']
        
        logger.info(f"🎭 {'  ' * depth}Exploring modal: {modal_hash} (depth: {depth})")
        
        # Track modal in stack
        self.modal_stack.append(modal_hash)
        
        exploration_result = {
            'modal_hash': modal_hash,
            'modal_info': modal_info,
            'depth': depth,
            'start_time': time.time(),
            'elements_tested': [],
            'nested_modals_found': [],
            'errors': [],
            'screenshots': [],
            'dismissal_successful': False
        }
        
        try:
            # Focus on modal
            modal_element = self.page.locator(modal_selector).first
            await modal_element.scroll_into_view_if_needed()
            
            # Extract interactive elements within modal
            modal_elements = await self._extract_modal_elements(modal_element)
            
            logger.info(f"🎯 {'  ' * depth}Found {len(modal_elements)} interactive elements in modal")
            
            # Test each element in the modal
            for i, element in enumerate(modal_elements):
                try:
                    logger.info(f"⚡ {'  ' * depth}Testing modal element {i+1}/{len(modal_elements)}: {element.get('text', element.get('name', 'unnamed'))[:50]}")
                    
                    # Execute action on modal element
                    action_result = await self._execute_modal_action(element, modal_element)
                    exploration_result['elements_tested'].append(action_result)
                    
                    # Check if action opened a new modal
                    await asyncio.sleep(1)  # Wait for potential modal
                    new_modals = await self.detect_modals()
                    
                    # Filter out current modal and already seen modals
                    truly_new_modals = []
                    for new_modal in new_modals:
                        if (new_modal['modal_hash'] != modal_hash and 
                            new_modal['modal_hash'] not in self.discovered_modals and
                            new_modal['modal_hash'] not in [m['modal_hash'] for m in exploration_result['nested_modals_found']]):
                            truly_new_modals.append(new_modal)
                    
                    # Recursively explore new modals
                    for new_modal in truly_new_modals:
                        logger.info(f"🆕 {'  ' * depth}New modal detected: {new_modal['modal_hash']}")
                        nested_result = await self.explore_modal_recursively(new_modal, depth + 1)
                        exploration_result['nested_modals_found'].append(nested_result)
                        
                        # After exploring nested modal, we should be back to current modal
                        # Verify current modal is still present
                        if not await modal_element.is_visible():
                            logger.warning(f"⚠️ {'  ' * depth}Parent modal disappeared after nested exploration")
                            break
                    
                except Exception as e:
                    error_info = {
                        'element': element,
                        'error': str(e),
                        'timestamp': time.time()
                    }
                    exploration_result['errors'].append(error_info)
                    logger.warning(f"❌ {'  ' * depth}Error testing modal element: {e}")
                    
                    # Capture error screenshot
                    if self.session_manager:
                        screenshot_path = await self.session_manager.capture_error_screenshot(
                            self.page,
                            "modal_action_error",
                            f"depth_{depth}_{str(e)[:30]}",
                            self.page.url
                        )
                        exploration_result['screenshots'].append(screenshot_path)
            
            # Mark modal as fully explored
            modal_state = ModalState(
                modal_hash=modal_hash,
                modal_selector=modal_selector,
                modal_type=modal_info['modal_type'],
                content_hash=modal_info['content_hash'],
                elements_found=len(modal_elements),
                fully_explored=True,
                parent_modal=self.modal_stack[-2] if len(self.modal_stack) > 1 else None
            )
            
            self.discovered_modals[modal_hash] = modal_state
            
            # Try to dismiss the modal
            dismissal_success = await self._dismiss_modal(modal_element, modal_info)
            exploration_result['dismissal_successful'] = dismissal_success
            
            exploration_result['end_time'] = time.time()
            exploration_result['duration'] = exploration_result['end_time'] - exploration_result['start_time']
            
            logger.info(f"✅ {'  ' * depth}Modal exploration completed: {modal_hash} ({exploration_result['duration']:.1f}s)")
            
            return exploration_result
            
        except Exception as e:
            logger.error(f"💥 {'  ' * depth}Modal exploration failed: {e}")
            exploration_result['fatal_error'] = str(e)
            return exploration_result
            
        finally:
            # Remove from modal stack
            if modal_hash in self.modal_stack:
                self.modal_stack.remove(modal_hash)

    async def _extract_modal_elements(self, modal_element) -> List[Dict[str, Any]]:
        """Extract interactive elements specifically within a modal."""
        elements = []
        
        try:
            # Button elements
            buttons = await modal_element.locator('button, input[type="button"], input[type="submit"], [role="button"]').all()
            for i, button in enumerate(buttons):
                if await button.is_visible():
                    text = await button.inner_text() or await button.get_attribute('value') or f"modal_button_{i}"
                    elements.append({
                        'type': 'modal_button',
                        'text': text.strip()[:100],
                        'selector': f'button:nth-of-type({i+1})',
                        'context': 'modal'
                    })
            
            # Input elements
            inputs = await modal_element.locator('input, textarea').all()
            for i, input_elem in enumerate(inputs):
                if await input_elem.is_visible():
                    input_type = await input_elem.get_attribute('type') or 'text'
                    name = await input_elem.get_attribute('name') or f"modal_input_{i}"
                    elements.append({
                        'type': 'modal_input',
                        'input_type': input_type,
                        'name': name,
                        'selector': f'input:nth-of-type({i+1})',
                        'context': 'modal'
                    })
            
            # Links within modal
            links = await modal_element.locator('a[href]').all()
            for i, link in enumerate(links):
                if await link.is_visible():
                    href = await link.get_attribute('href')
                    text = await link.inner_text() or href
                    elements.append({
                        'type': 'modal_link',
                        'text': text.strip()[:100],
                        'href': href,
                        'selector': f'a:nth-of-type({i+1})',
                        'context': 'modal'
                    })
            
            # Close buttons (special handling)
            close_selectors = [
                '[aria-label*="close"]',
                '[aria-label*="Close"]', 
                '.close',
                '.modal-close',
                '[data-dismiss]',
                '[data-testid*="close"]'
            ]
            
            for selector in close_selectors:
                try:
                    close_buttons = await modal_element.locator(selector).all()
                    for i, close_btn in enumerate(close_buttons):
                        if await close_btn.is_visible():
                            text = await close_btn.inner_text() or 'Close'
                            elements.append({
                                'type': 'modal_close',
                                'text': text.strip()[:100],
                                'selector': f'{selector}:nth-of-type({i+1})',
                                'context': 'modal',
                                'special': 'close_button'
                            })
                except:
                    continue
            
            return elements
            
        except Exception as e:
            logger.error(f"Error extracting modal elements: {e}")
            return []

    async def _execute_modal_action(self, element: Dict[str, Any], modal_element) -> Dict[str, Any]:
        """Execute action on modal element with modal-specific handling."""
        result = {
            'element': element,
            'timestamp': time.time(),
            'success': False,
            'context': 'modal'
        }
        
        try:
            element_type = element['type']
            selector = element['selector']
            
            # Use modal_element as context for locator
            locator = modal_element.locator(selector).first
            await locator.wait_for(timeout=3000)  # Shorter timeout for modal elements
            
            if element_type == 'modal_button':
                await locator.click(timeout=3000)
                result['action'] = 'click'
                
            elif element_type == 'modal_input':
                input_type = element.get('input_type', 'text')
                if input_type in ['text', 'email', 'search', 'password']:
                    test_value = f"modal_test_{int(time.time())}"
                    await locator.fill(test_value, timeout=3000)
                    result['action'] = 'fill'
                    result['value'] = test_value
                else:
                    result['action'] = 'skipped_input_type'
                    result['success'] = True
                    return result
                    
            elif element_type == 'modal_link':
                # For modal links, be careful about navigation
                href = element.get('href', '')
                if href.startswith('#') or href.startswith('javascript:'):
                    # Internal link or JS, safe to click
                    await locator.click(timeout=3000)
                    result['action'] = 'click'
                else:
                    # External link, might navigate away
                    result['action'] = 'skipped_external'
                    result['success'] = True
                    return result
                    
            elif element_type == 'modal_close':
                # Close buttons are important to test
                await locator.click(timeout=3000)
                result['action'] = 'close_click'
                result['special'] = 'modal_dismissed'
            
            result['success'] = True
            await asyncio.sleep(0.5)  # Brief wait for modal state changes
            
        except Exception as e:
            result['error'] = str(e)
            logger.debug(f"Modal action failed: {e}")
        
        return result

    async def _dismiss_modal(self, modal_element, modal_info: Dict[str, Any]) -> bool:
        """Try various methods to dismiss a modal."""
        modal_hash = modal_info['modal_hash']
        
        # Check if modal is already dismissed
        try:
            if not await modal_element.is_visible():
                logger.info(f"✅ Modal {modal_hash} already dismissed")
                return True
        except:
            return True  # Element no longer exists
        
        dismissal_methods = []
        
        # Method 1: ESC key
        try:
            logger.info(f"🔑 Trying ESC key to dismiss modal {modal_hash}")
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            if not await modal_element.is_visible():
                dismissal_methods.append('escape_key')
                logger.info(f"✅ Modal dismissed with ESC key")
                return True
        except Exception as e:
            logger.debug(f"ESC key dismissal failed: {e}")
        
        # Method 2: Click close button
        try:
            close_selectors = [
                '[aria-label*="close"]', '.close', '.modal-close', 
                '[data-dismiss]', 'button:has-text("✕")', 'button:has-text("×")'
            ]
            
            for selector in close_selectors:
                try:
                    close_btn = modal_element.locator(selector).first
                    if await close_btn.is_visible():
                        logger.info(f"🖱️ Trying close button: {selector}")
                        await close_btn.click(timeout=3000)
                        await asyncio.sleep(1)
                        
                        if not await modal_element.is_visible():
                            dismissal_methods.append(f'close_button_{selector}')
                            logger.info(f"✅ Modal dismissed with close button")
                            return True
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Close button dismissal failed: {e}")
        
        # Method 3: Click outside modal (backdrop)
        try:
            logger.info(f"🖱️ Trying backdrop click to dismiss modal {modal_hash}")
            
            # Get modal bounding box
            bbox = await modal_element.bounding_box()
            if bbox:
                # Click slightly outside the modal
                outside_x = bbox['x'] - 50
                outside_y = bbox['y'] - 50
                
                # Ensure coordinates are within viewport
                viewport = self.page.viewport_size
                if outside_x < 0:
                    outside_x = bbox['x'] + bbox['width'] + 50
                if outside_y < 0:
                    outside_y = bbox['y'] + bbox['height'] + 50
                    
                if outside_x < viewport['width'] and outside_y < viewport['height']:
                    await self.page.mouse.click(outside_x, outside_y)
                    await asyncio.sleep(1)
                    
                    if not await modal_element.is_visible():
                        dismissal_methods.append('backdrop_click')
                        logger.info(f"✅ Modal dismissed with backdrop click")
                        return True
                        
        except Exception as e:
            logger.debug(f"Backdrop click dismissal failed: {e}")
        
        # Method 4: Browser back (for route-based modals)
        try:
            logger.info(f"⬅️ Trying browser back to dismiss modal {modal_hash}")
            await self.page.go_back(timeout=3000)
            await asyncio.sleep(1)
            
            if not await modal_element.is_visible():
                dismissal_methods.append('browser_back')
                logger.info(f"✅ Modal dismissed with browser back")
                return True
        except Exception as e:
            logger.debug(f"Browser back dismissal failed: {e}")
        
        # Update modal state with attempted dismissal methods
        if modal_hash in self.discovered_modals:
            self.discovered_modals[modal_hash].dismissal_methods = dismissal_methods
        
        logger.warning(f"⚠️ Could not dismiss modal {modal_hash} - tried {len(dismissal_methods)} methods")
        return False

    async def should_explore_modal(self, modal_info: Dict[str, Any]) -> bool:
        """Determine if a modal should be explored based on our exploration history."""
        modal_hash = modal_info['modal_hash']
        
        # Check if we've already fully explored this modal
        if modal_hash in self.discovered_modals:
            modal_state = self.discovered_modals[modal_hash]
            if modal_state.fully_explored:
                logger.info(f"⏭️ Skipping already explored modal: {modal_hash}")
                return False
        
        # Check if modal is currently in our exploration stack (avoid infinite recursion)
        if modal_hash in self.modal_stack:
            logger.warning(f"🔄 Modal {modal_hash} already in exploration stack - avoiding recursion")
            return False
        
        # Check element count - skip empty modals
        if modal_info.get('elements_found', 0) == 0:
            logger.info(f"📭 Skipping empty modal: {modal_hash}")
            return False
        
        return True

    async def quick_dismiss_known_modal(self, modal_info: Dict[str, Any]) -> bool:
        """Quickly dismiss a modal we've already explored using known methods."""
        modal_hash = modal_info['modal_hash']
        
        if modal_hash not in self.discovered_modals:
            return False
        
        modal_state = self.discovered_modals[modal_hash]
        
        logger.info(f"⚡ Quick dismissing known modal: {modal_hash}")
        
        # Try previously successful dismissal methods first
        for method in modal_state.dismissal_methods:
            try:
                if method == 'escape_key':
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(0.5)
                    
                elif method.startswith('close_button_'):
                    selector = method.replace('close_button_', '')
                    await self.page.locator(selector).first.click(timeout=2000)
                    await asyncio.sleep(0.5)
                    
                elif method == 'backdrop_click':
                    # Click in top-left corner as backdrop
                    await self.page.mouse.click(50, 50)
                    await asyncio.sleep(0.5)
                
                # Check if dismissal worked
                modal_element = self.page.locator(modal_info['modal_selector']).first
                if not await modal_element.is_visible():
                    logger.info(f"✅ Quick dismissal successful with method: {method}")
                    return True
                    
            except Exception as e:
                logger.debug(f"Quick dismissal method {method} failed: {e}")
                continue
        
        logger.warning(f"⚠️ Quick dismissal failed for modal: {modal_hash}")
        return False

    def get_exploration_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of modal exploration results."""
        total_modals = len(self.discovered_modals)
        fully_explored = len([m for m in self.discovered_modals.values() if m.fully_explored])
        
        return {
            'total_modals_discovered': total_modals,
            'modals_fully_explored': fully_explored,
            'exploration_results': self.modal_exploration_results,
            'modal_states': {hash: {
                'type': state.modal_type,
                'elements_found': state.elements_found,
                'fully_explored': state.fully_explored,
                'dismissal_methods': state.dismissal_methods
            } for hash, state in self.discovered_modals.items()}
        } 
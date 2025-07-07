"""
Action Execution Utility

Handles execution of various types of actions on web elements with
comprehensive error handling, retry logic, and adaptive timeouts.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class ActionConfig:
    """Configuration for action execution."""
    default_timeout: int = 5000
    retry_attempts: int = 2
    wait_after_action: float = 1.0
    modal_timeout: int = 2000
    form_timeout: int = 10000


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    action: Dict[str, Any]
    element: Dict[str, Any]
    timestamp: float
    duration: float
    error: Optional[str] = None
    retry_count: int = 0
    screenshots: list = None
    
    def __post_init__(self):
        if self.screenshots is None:
            self.screenshots = []


class ActionExecutor:
    """
    Executes actions on web elements with intelligent error handling and retry logic.
    
    Provides consistent action execution across different exploration strategies
    with adaptive timeouts and comprehensive error recovery.
    """
    
    def __init__(self, page, config: Optional[ActionConfig] = None):
        self.page = page
        self.config = config or ActionConfig()
        
        # Test value generators
        self.test_values = {
            'text': 'Test Input',
            'email': 'test@example.com',
            'password': 'TestPass123',
            'search': 'search test',
            'tel': '555-1234',
            'url': 'https://example.com',
            'number': '123'
        }
        
        # Action history for learning
        self.action_history: list = []
        self.error_handler: Optional[Callable] = None
        self.screenshot_handler: Optional[Callable] = None
    
    def set_error_handler(self, handler: Callable) -> None:
        """Set error handler for action failures."""
        self.error_handler = handler
    
    def set_screenshot_handler(self, handler: Callable) -> None:
        """Set screenshot handler for capturing action states."""
        self.screenshot_handler = handler
    
    async def execute_action(self, element: Dict[str, Any], action_type: str = None, value: str = None) -> ActionResult:
        """
        Execute action on element with comprehensive error handling.
        
        Args:
            element: Element dictionary with selector and metadata
            action_type: Override action type (auto-detected if None)
            value: Override value for input actions
            
        Returns:
            ActionResult with execution details
        """
        start_time = time.time()
        
        # Determine action type
        if action_type is None:
            action_type = self._determine_action_type(element)
        
        # Create action object
        action = {
            'action': action_type,
            'target': element['selector'],
            'value': value or self._get_test_value(element),
            'element_type': element['type']
        }
        
        result = ActionResult(
            success=False,
            action=action,
            element=element,
            timestamp=start_time,
            duration=0
        )
        
        # Execute with retries
        for attempt in range(self.config.retry_attempts + 1):
            try:
                result.retry_count = attempt
                
                logger.info(f"🎯 Executing {action_type} on {element['type']}: {element.get('text', element.get('name', 'unnamed'))[:50]}")
                
                # Capture before state if screenshot handler available
                if self.screenshot_handler and attempt == 0:
                    screenshot = await self.screenshot_handler("before_action", action)
                    if screenshot:
                        result.screenshots.append(screenshot)
                
                # Execute the specific action
                await self._execute_specific_action(action, element)
                
                # Wait after action
                await asyncio.sleep(self.config.wait_after_action)
                
                # Action succeeded
                result.success = True
                result.duration = time.time() - start_time
                
                logger.info(f"✅ Action completed successfully: {action_type}")
                
                # Record successful action
                self._record_action_result(action, element, True, None)
                
                return result
                
            except PlaywrightTimeoutError as e:
                error_msg = f"Timeout: {str(e)}"
                logger.warning(f"⏰ Action timeout (attempt {attempt + 1}): {error_msg}")
                
                # Handle timeout-specific retry logic
                if attempt < self.config.retry_attempts:
                    await self._handle_timeout_retry(action, element, attempt)
                else:
                    result.error = error_msg
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Action failed (attempt {attempt + 1}): {error_msg}")
                
                # Handle general error retry logic
                if attempt < self.config.retry_attempts:
                    retry_success = await self._handle_error_retry(action, element, e, attempt)
                    if not retry_success:
                        result.error = error_msg
                        break
                else:
                    result.error = error_msg
        
        # Action failed after all retries
        result.duration = time.time() - start_time
        
        # Capture failure screenshot
        if self.screenshot_handler:
            screenshot = await self.screenshot_handler("action_failed", action, result.error)
            if screenshot:
                result.screenshots.append(screenshot)
        
        # Record failed action
        self._record_action_result(action, element, False, result.error)
        
        # Call error handler if available
        if self.error_handler:
            await self.error_handler(action, element, result.error)
        
        return result
    
    async def _execute_specific_action(self, action: Dict[str, Any], element: Dict[str, Any]) -> None:
        """Execute the specific action based on action type."""
        action_type = action['action']
        selector = action['target']
        value = action.get('value', '')
        
        # Get appropriate timeout
        timeout = self._get_adaptive_timeout(action_type, element)
        
        # Wait for element
        await self.page.wait_for_selector(selector, timeout=timeout)
        locator = self.page.locator(selector).first
        
        # Execute based on action type
        if action_type == 'click':
            await locator.click(timeout=timeout)
            
        elif action_type == 'fill':
            await locator.fill(value, timeout=timeout)
            
        elif action_type == 'type':
            await locator.fill('')  # Clear first
            await locator.type(value, timeout=timeout)
            
        elif action_type == 'select':
            await locator.select_option(value, timeout=timeout)
            
        elif action_type == 'hover':
            await locator.hover(timeout=timeout)
            
        elif action_type == 'focus':
            await locator.focus(timeout=timeout)
            
        elif action_type == 'check':
            await locator.check(timeout=timeout)
            
        elif action_type == 'uncheck':
            await locator.uncheck(timeout=timeout)
            
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def _determine_action_type(self, element: Dict[str, Any]) -> str:
        """Determine appropriate action type for element."""
        element_type = element['type']
        
        if element_type == 'button':
            return 'click'
        elif element_type == 'link':
            return 'click'
        elif element_type == 'input':
            input_type = element.get('input_type', 'text')
            if input_type in ['text', 'email', 'password', 'search', 'tel', 'url', 'number']:
                return 'fill'
            elif input_type == 'checkbox':
                return 'check'
            elif input_type == 'radio':
                return 'check'
            else:
                return 'click'
        elif element_type == 'select':
            return 'select'
        elif element_type == 'textarea':
            return 'fill'
        else:
            return 'click'  # Default fallback
    
    def _get_test_value(self, element: Dict[str, Any]) -> str:
        """Get appropriate test value for element."""
        element_type = element['type']
        
        if element_type == 'input':
            input_type = element.get('input_type', 'text')
            return self.test_values.get(input_type, 'test')
        elif element_type == 'textarea':
            return 'Test textarea content'
        elif element_type == 'select':
            options = element.get('options', [])
            if len(options) > 1:
                # Choose second option to avoid default
                return options[1].get('value', options[1].get('text', ''))
            return ''
        else:
            return ''
    
    def _get_adaptive_timeout(self, action_type: str, element: Dict[str, Any]) -> int:
        """Get adaptive timeout based on action type and element context."""
        base_timeout = self.config.default_timeout
        
        # Adjust based on action type
        if action_type in ['fill', 'type']:
            return self.config.form_timeout
        elif action_type == 'click':
            # Check if element might trigger modal
            text = element.get('text', '').lower()
            if any(keyword in text for keyword in ['login', 'sign', 'connect', 'modal']):
                return self.config.modal_timeout
        
        # Check action history for this element type
        similar_actions = [
            h for h in self.action_history[-20:]  # Last 20 actions
            if h['element_type'] == element['type'] and h['action'] == action_type
        ]
        
        if similar_actions:
            avg_duration = sum(h['duration'] for h in similar_actions) / len(similar_actions)
            # Add buffer to average duration
            adaptive_timeout = int(avg_duration * 1000 * 2)  # Convert to ms and double
            return max(base_timeout, min(adaptive_timeout, 15000))  # Cap at 15s
        
        return base_timeout
    
    async def _handle_timeout_retry(self, action: Dict[str, Any], element: Dict[str, Any], attempt: int) -> None:
        """Handle timeout-specific retry logic."""
        logger.info(f"🔄 Handling timeout retry (attempt {attempt + 1})")
        
        # Check for modals that might be blocking
        modal_detected = await self._check_for_blocking_modals()
        if modal_detected:
            logger.info("🎭 Modal detected, attempting to dismiss")
            await self._attempt_modal_dismissal()
        
        # Brief wait before retry
        await asyncio.sleep(1)
    
    async def _handle_error_retry(self, action: Dict[str, Any], element: Dict[str, Any], 
                                error: Exception, attempt: int) -> bool:
        """
        Handle general error retry logic.
        
        Returns:
            True if retry should continue, False if should abort
        """
        error_msg = str(error).lower()
        
        logger.info(f"🔄 Handling error retry (attempt {attempt + 1}): {error_msg[:50]}")
        
        # Handle specific error types
        if "strict mode violation" in error_msg and "resolved to" in error_msg:
            # Multiple elements found - modify selector
            return await self._handle_selector_ambiguity(action, element)
            
        elif "intercepts pointer events" in error_msg:
            # Element blocked by overlay
            return await self._handle_element_blocked(action, element)
            
        elif "not attached to the dom" in error_msg:
            # Element disappeared
            logger.warning("Element no longer in DOM, skipping retry")
            return False
            
        else:
            # General error - wait and retry
            await asyncio.sleep(2)
            return True
    
    async def _handle_selector_ambiguity(self, action: Dict[str, Any], element: Dict[str, Any]) -> bool:
        """Handle selector ambiguity by making selector more specific."""
        original_selector = action['target']
        
        if ':has-text(' in original_selector:
            # Make selector more specific by adding .first
            action['target'] = f"({original_selector}).first"
            logger.info(f"📍 Using more specific selector: {action['target']}")
            return True
        
        return False
    
    async def _handle_element_blocked(self, action: Dict[str, Any], element: Dict[str, Any]) -> bool:
        """Handle element blocked by overlay."""
        logger.info("🚧 Element blocked, attempting to clear overlays")
        
        # Try to dismiss modals/overlays
        modal_dismissed = await self._attempt_modal_dismissal()
        if modal_dismissed:
            await asyncio.sleep(1)
            return True
        
        # Try scrolling element into view
        try:
            locator = self.page.locator(action['target']).first
            await locator.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            return True
        except:
            pass
        
        return False
    
    async def _check_for_blocking_modals(self) -> bool:
        """Check for modals that might be blocking interactions."""
        modal_selectors = [
            '[role="dialog"]',
            '[aria-modal="true"]',
            '.modal',
            '.popup',
            '.overlay'
        ]
        
        for selector in modal_selectors:
            try:
                modal = self.page.locator(selector).first
                if await modal.is_visible():
                    return True
            except:
                continue
        
        return False
    
    async def _attempt_modal_dismissal(self) -> bool:
        """Attempt to dismiss blocking modals."""
        try:
            # Try ESC key
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # Check if modal is gone
            if not await self._check_for_blocking_modals():
                logger.info("✅ Modal dismissed with ESC key")
                return True
            
            # Try clicking close buttons
            close_selectors = [
                'button:has-text("Close")',
                'button:has-text("✕")',
                'button:has-text("×")',
                '[aria-label="Close"]'
            ]
            
            for selector in close_selectors:
                try:
                    close_btn = self.page.locator(selector).first
                    if await close_btn.is_visible():
                        await close_btn.click(timeout=2000)
                        await asyncio.sleep(0.5)
                        
                        if not await self._check_for_blocking_modals():
                            logger.info(f"✅ Modal dismissed with close button: {selector}")
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Modal dismissal failed: {e}")
            return False
    
    def _record_action_result(self, action: Dict[str, Any], element: Dict[str, Any], 
                            success: bool, error: Optional[str]) -> None:
        """Record action result for learning and optimization."""
        result_record = {
            'action': action['action'],
            'element_type': element['type'],
            'success': success,
            'error': error,
            'timestamp': time.time(),
            'duration': 0  # Would be filled by caller
        }
        
        self.action_history.append(result_record)
        
        # Keep history manageable
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-50:]
    
    def get_action_success_rate(self, action_type: str = None, element_type: str = None) -> float:
        """Get success rate for specific action/element combinations."""
        if not self.action_history:
            return 0.0
        
        filtered_actions = self.action_history
        
        if action_type:
            filtered_actions = [a for a in filtered_actions if a['action'] == action_type]
        
        if element_type:
            filtered_actions = [a for a in filtered_actions if a['element_type'] == element_type]
        
        if not filtered_actions:
            return 0.0
        
        successes = sum(1 for a in filtered_actions if a['success'])
        return successes / len(filtered_actions)
    
    def get_action_stats(self) -> Dict[str, Any]:
        """Get comprehensive action execution statistics."""
        if not self.action_history:
            return {'total_actions': 0, 'success_rate': 0.0}
        
        total = len(self.action_history)
        successes = sum(1 for a in self.action_history if a['success'])
        
        # Group by action type
        action_stats = {}
        for action in self.action_history:
            action_type = action['action']
            if action_type not in action_stats:
                action_stats[action_type] = {'total': 0, 'successes': 0}
            
            action_stats[action_type]['total'] += 1
            if action['success']:
                action_stats[action_type]['successes'] += 1
        
        # Calculate success rates
        for action_type, stats in action_stats.items():
            stats['success_rate'] = stats['successes'] / stats['total']
        
        return {
            'total_actions': total,
            'success_rate': successes / total,
            'action_breakdown': action_stats
        } 